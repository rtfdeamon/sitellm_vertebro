"""Knowledge base management router.

Provides endpoints for knowledge documents, Q&A pairs, and knowledge service configuration.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import ORJSONResponse, Response

from app.services.auth import require_admin, require_super_admin
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/admin", tags=["knowledge"])


# Pydantic models for knowledge endpoints
class KnowledgeCreate(BaseModel):
    name: str | None = None
    content: str
    domain: str | None = None
    project: str | None = None
    description: str | None = None
    url: str | None = None


class KnowledgeUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    description: str | None = None
    url: str | None = None
    project: str | None = None
    domain: str | None = None
    status: str | None = None
    status_message: str | None = None


class KnowledgeDeduplicate(BaseModel):
    project: str | None = None


class KnowledgePriorityPayload(BaseModel):
    order: list[str]


class KnowledgeQAPayload(BaseModel):
    question: str
    answer: str
    priority: int | None = 0


class KnowledgeQAReorderPayload(BaseModel):
    order: list[str]


class KnowledgeUnansweredClearPayload(BaseModel):
    project: str | None = None


class KnowledgeServiceConfig(BaseModel):
    enabled: bool
    idle_threshold_seconds: int | None = None
    poll_interval_seconds: int | None = None
    cooldown_seconds: int | None = None
    mode: str | None = None
    processing_prompt: str | None = None


class KnowledgeServiceRunRequest(BaseModel):
    reason: str | None = None


@router.get("/knowledge", response_class=ORJSONResponse)
async def admin_knowledge(
    request: Request,
    q: str | None = None,
    limit: int = 50,
    domain: str | None = None,
    project: str | None = None,
) -> ORJSONResponse:
    """Return knowledge base documents for the admin UI."""
    # Import here to avoid circular dependency
    # The full implementation is still in app.py (complex function with many dependencies)
    # TODO: Move full implementation to this router in future iteration
    from app import _admin_knowledge_impl
    return await _admin_knowledge_impl(request, q=q, limit=limit, domain=domain, project=project)


@router.get("/knowledge/documents/{file_id}")
async def admin_download_document(request: Request, file_id: str) -> Response:
    """Return the raw contents of a document from GridFS."""
    # Import here to avoid circular dependency
    # The implementation is still in app.py (complex function with GridFS dependencies)
    # TODO: Move full implementation to this router in future iteration
    from app import admin_download_document as _download_doc_impl
    return await _download_doc_impl(request, file_id)


# Knowledge document management endpoints
@router.post("/knowledge", response_class=ORJSONResponse, status_code=201)
async def admin_create_knowledge(request: Request, payload: KnowledgeCreate) -> ORJSONResponse:
    """Create or update a text document in the knowledge base."""
    from app import _get_project_context, logger
    from models import Project
    from knowledge.tasks import queue_auto_description
    from settings import MongoSettings
    from uuid import uuid4
    
    require_super_admin(request)
    
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Content is empty")

    name = (payload.name or "").strip()
    if not name:
        name = f"doc-{uuid4().hex[:8]}"

    project_name, project, mongo_client, owns_client = await _get_project_context(
        request, payload.project or payload.domain
    )
    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)

    description_input = (payload.description or "").strip()
    auto_description_pending = False
    status_message = None

    if description_input:
        description_value = description_input
    else:
        description_value = ""
        auto_description_pending = True
        status_message = "Автоописание в очереди"

    try:
        domain_value = payload.domain or (project.domain if project else None)
        file_id = await mongo_client.upsert_text_document(
            name=name,
            content=payload.content,
            documents_collection=collection,
            description=description_value,
            project=project_name,
            domain=domain_value,
            url=payload.url,
        )
        await mongo_client.db[collection].update_one(
            {"fileId": file_id},
            {
                "$set": {
                    "autoDescriptionPending": auto_description_pending,
                }
            },
            upsert=False,
        )
        if auto_description_pending:
            await mongo_client.update_document_status(
                collection,
                file_id,
                "pending_auto_description",
                status_message,
            )
            queue_auto_description(file_id, project_name)
        else:
            await mongo_client.update_document_status(
                collection,
                file_id,
                "ready",
                "Описание задано вручную",
            )
        if project_name:
            project_payload = Project(
                name=project.name if project else project_name,
                title=project.title if project else None,
                domain=domain_value,
                admin_username=project.admin_username if project else None,
                admin_password_hash=project.admin_password_hash if project else None,
                llm_model=project.llm_model if project else None,
                llm_prompt=project.llm_prompt if project else None,
                llm_emotions_enabled=project.llm_emotions_enabled if project else True,
                telegram_token=project.telegram_token if project else None,
                telegram_auto_start=project.telegram_auto_start if project else None,
                max_token=project.max_token if project else None,
                max_auto_start=project.max_auto_start if project else None,
                vk_token=project.vk_token if project else None,
                vk_auto_start=project.vk_auto_start if project else None,
                widget_url=project.widget_url if project else None,
                debug_enabled=project.debug_enabled if project and project.debug_enabled is not None else None,
            )
            await request.state.mongo.upsert_project(project_payload)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if owns_client:
            await mongo_client.close()

    return ORJSONResponse({
        "file_id": file_id,
        "name": name,
        "project": project_name,
        "domain": domain_value,
        "description": description_value,
        "auto_description_pending": auto_description_pending,
        "status": "pending_auto_description" if auto_description_pending else "ready",
        "status_message": status_message,
    })


@router.post("/knowledge/upload", response_class=ORJSONResponse, status_code=201)
async def admin_upload_knowledge(
    request: Request,
    project: str = Form(...),
    description: str | None = Form(None),
    name: str | None = Form(None),
    url: str | None = Form(None),
    file: UploadFile = File(...),
) -> ORJSONResponse:
    """Upload a binary document to GridFS and store metadata."""
    from app import _get_project_context, _build_download_url, logger
    from backend.validators import validate_upload_file
    from knowledge.tasks import queue_auto_description
    from settings import MongoSettings
    import asyncio
    
    project_name, project_model, mongo_client, owns_client = await _get_project_context(
        request, project
    )
    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)

    filename = (name or file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="File name is required")

    # Comprehensive file validation with timeout
    try:
        payload = await asyncio.wait_for(
            validate_upload_file(file, max_size=100 * 1024 * 1024, check_magic=True),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408,
            detail="Превышено время ожидания загрузки файла (30 сек)",
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_upload_validation_failed", filename=filename, error=str(exc))
        raise HTTPException(status_code=400, detail="Ошибка валидации файла") from exc

    if not payload:
        raise HTTPException(status_code=400, detail="File is empty")

    description_input = (description or "").strip()
    auto_description_pending = False
    status_message = None
    if description_input:
        description_value = description_input
    else:
        description_value = ""
        auto_description_pending = True
        status_message = "Автоописание в очереди"

    try:
        file_id = await mongo_client.upload_document(
            file_name=filename,
            file=payload,
            documents_collection=collection,
            description=description_value,
            url=url,
            content_type=file.content_type,
            project=project_name,
            domain=project_model.domain if project_model else None,
        )
        download_url = _build_download_url(request, file_id)
        await mongo_client.db[collection].update_one(
            {"fileId": file_id},
            {"$set": {"url": download_url, "content_type": file.content_type}},
            upsert=False,
        )
        await mongo_client.db[collection].update_one(
            {"fileId": file_id},
            {
                "$set": {
                    "autoDescriptionPending": auto_description_pending,
                }
            },
            upsert=False,
        )
        if auto_description_pending:
            await mongo_client.update_document_status(
                collection,
                file_id,
                "pending_auto_description",
                status_message,
            )
            queue_auto_description(file_id, project_name)
        else:
            await mongo_client.update_document_status(
                collection,
                file_id,
                "ready",
                "Описание задано вручную",
            )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if owns_client:
            await mongo_client.close()

    return ORJSONResponse(
        {
            "file_id": file_id,
            "name": filename,
            "project": project_name,
            "download_url": download_url,
            "content_type": file.content_type,
            "description": description_value,
            "auto_description_pending": auto_description_pending,
            "status": "pending_auto_description" if auto_description_pending else "ready",
            "status_message": status_message,
        }
    )


@router.post("/knowledge/deduplicate", response_class=ORJSONResponse)
async def admin_deduplicate_knowledge(request: Request, payload: KnowledgeDeduplicate) -> ORJSONResponse:
    """Deduplicate knowledge documents for a project."""
    from app import _get_project_context, logger
    from settings import MongoSettings
    
    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)
    project_name, _, _, _ = await _get_project_context(request, payload.project)
    try:
        summary = await request.state.mongo.deduplicate_documents(collection, project_name)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ORJSONResponse({"project": project_name, **summary})


@router.post("/knowledge/reindex", response_class=ORJSONResponse)
async def admin_reindex_documents(request: Request) -> ORJSONResponse:
    """Trigger vector store reindexing."""
    from app.services.auth import require_super_admin
    import asyncio
    
    require_super_admin(request)
    loop = asyncio.get_running_loop()

    def _run_update() -> None:
        from worker import update_vector_store
        update_vector_store()

    loop.run_in_executor(None, _run_update)
    return ORJSONResponse({"status": "queued"})


@router.delete("/knowledge", response_class=ORJSONResponse)
async def admin_clear_knowledge(request: Request, project: str | None = None) -> ORJSONResponse:
    """Remove documents from the knowledge base (optionally scoped to a project)."""
    from app import _get_project_context, logger
    from settings import MongoSettings
    import asyncio
    
    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)
    project_name, _, mongo_client, _ = await _get_project_context(request, project)
    summary = await mongo_client.delete_documents(collection, project_name)

    loop = asyncio.get_running_loop()

    def _refresh() -> None:
        from worker import update_vector_store
        update_vector_store()

    loop.run_in_executor(None, _refresh)
    return ORJSONResponse({"project": project_name, **summary})


@router.get("/knowledge/priority", response_class=ORJSONResponse)
async def admin_get_knowledge_priority(request: Request, project: str | None = None) -> ORJSONResponse:
    """Get knowledge source priority order for a project."""
    from app import _get_project_context, logger
    from api import _KNOWN_KNOWLEDGE_SOURCES, _DEFAULT_KNOWLEDGE_PRIORITY
    
    project_name, _, mongo_client, _ = await _get_project_context(request, project)
    try:
        stored_order = await mongo_client.get_knowledge_priority(project_name)
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_priority_fetch_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to load knowledge priority") from exc

    available_sources = list(_KNOWN_KNOWLEDGE_SOURCES)
    normalized = []
    for entry in stored_order or []:
        candidate = str(entry).strip()
        if candidate in available_sources and candidate not in normalized:
            normalized.append(candidate)
    if not normalized:
        normalized = [source for source in _DEFAULT_KNOWLEDGE_PRIORITY if source in available_sources]
    if not normalized:
        normalized = available_sources

    return ORJSONResponse(
        {
            "order": normalized,
            "available": available_sources,
            "project": project_name,
        }
    )


@router.post("/knowledge/priority", response_class=ORJSONResponse)
async def admin_set_knowledge_priority(
    request: Request,
    payload: KnowledgePriorityPayload,
    project: str | None = None,
) -> ORJSONResponse:
    """Set knowledge source priority order for a project."""
    from app import _get_project_context, logger
    from api import _KNOWN_KNOWLEDGE_SOURCES, _DEFAULT_KNOWLEDGE_PRIORITY
    
    project_name, _, mongo_client, _ = await _get_project_context(request, project)

    available_sources = list(_KNOWN_KNOWLEDGE_SOURCES)
    lookup = {source.lower(): source for source in available_sources}
    normalized: list[str] = []
    for entry in payload.order or []:
        candidate = lookup.get(str(entry or "").strip().lower())
        if candidate and candidate not in normalized:
            normalized.append(candidate)

    for fallback in _DEFAULT_KNOWLEDGE_PRIORITY:
        if fallback in available_sources and fallback not in normalized:
            normalized.append(fallback)

    if not normalized:
        normalized = available_sources

    try:
        await mongo_client.set_knowledge_priority(project_name, normalized)
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_priority_save_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to save knowledge priority") from exc

    return ORJSONResponse({"order": normalized, "project": project_name})


@router.delete("/knowledge/{file_id}", response_class=ORJSONResponse)
async def admin_delete_knowledge_document(
    request: Request,
    file_id: str,
    project: str | None = None,
) -> ORJSONResponse:
    """Delete a single knowledge document and its binary payload."""
    from app import _get_mongo_client, _resolve_admin_project, _normalize_project, logger
    from settings import MongoSettings
    import asyncio
    
    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)
    desired_project = _resolve_admin_project(request, project)
    mongo_client = _get_mongo_client(request)

    try:
        document = await mongo_client.db[collection].find_one({"fileId": file_id})
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_document_lookup_failed", file_id=file_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to load document metadata") from exc

    if not document:
        raise HTTPException(status_code=404, detail="document_not_found")

    document_project = _normalize_project(
        document.get("project") or document.get("domain")
    )
    if desired_project and document_project and desired_project != document_project:
        raise HTTPException(status_code=403, detail="document_forbidden")

    try:
        await mongo_client.delete_document(collection, file_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Failed to delete document") from exc

    loop = asyncio.get_running_loop()

    def _refresh_vectors() -> None:
        from worker import update_vector_store
        update_vector_store()

    loop.run_in_executor(None, _refresh_vectors)

    return ORJSONResponse({
        "removed": True,
        "file_id": file_id,
        "project": document_project or desired_project,
    })


# Q&A endpoints
@router.get("/knowledge/qa", response_class=ORJSONResponse)
async def admin_list_knowledge_qa(
    request: Request,
    project: str | None = None,
    limit: int = 500,
) -> ORJSONResponse:
    """List Q&A pairs for a project."""
    from app import _get_project_context, logger
    from api import _KNOWN_KNOWLEDGE_SOURCES, _DEFAULT_KNOWLEDGE_PRIORITY
    
    try:
        safe_limit = max(1, min(int(limit), 1000))
    except Exception:
        safe_limit = 500

    project_name, _, mongo_client, _ = await _get_project_context(request, project)

    try:
        items = await mongo_client.list_qa_pairs(project_name, limit=safe_limit)
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_qa_list_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to load QA pairs") from exc

    try:
        stored_order = await mongo_client.get_knowledge_priority(project_name)
    except Exception:
        stored_order = []

    available_sources = list(_KNOWN_KNOWLEDGE_SOURCES)
    normalized_priority = [item for item in stored_order if item in available_sources]
    if not normalized_priority:
        normalized_priority = [src for src in _DEFAULT_KNOWLEDGE_PRIORITY if src in available_sources]
    if not normalized_priority:
        normalized_priority = available_sources

    return ORJSONResponse(
        {
            "items": items,
            "priority": normalized_priority,
            "project": project_name,
        }
    )


@router.post("/knowledge/qa/upload", response_class=ORJSONResponse, status_code=201)
async def admin_import_knowledge_qa_file(
    request: Request,
    project: str = Form(...),
    file: UploadFile = File(...),
    refine: str | None = Form(None),
) -> ORJSONResponse:
    """Upload and import Q&A pairs from CSV file."""
    from app import _get_project_context, _read_qa_upload, _refine_qa_with_llm, logger
    
    project_name, project_model, mongo_client, _ = await _get_project_context(request, project)

    try:
        pairs = await _read_qa_upload(file)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_qa_import_parse_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=400, detail="Failed to read QA file") from exc

    if not pairs:
        return ORJSONResponse(
            {"inserted": 0, "updated": 0, "skipped": 0, "total": 0, "project": project_name},
            status_code=201,
        )

    refine_flag = False
    if refine is not None:
        refine_flag = str(refine).strip().lower() in {"1", "true", "yes", "on"}

    if refine_flag:
        try:
            pairs = await _refine_qa_with_llm(pairs, project_model=project_model)
        except Exception as exc:  # noqa: BLE001
            logger.warning("knowledge_qa_import_refine_failed", project=project_name, error=str(exc))

    normalized: list[dict[str, object]] = []
    skipped = 0
    for pair in pairs:
        # Text is already validated and normalized in _read_qa_upload
        question = str(pair.get("question") or "").strip()
        answer = str(pair.get("answer") or "").strip()
        if not question or not answer:
            skipped += 1
            continue
        priority_value = 0
        if "priority" in pair and pair.get("priority") not in (None, ""):
            raw_priority = str(pair.get("priority")).replace(",", ".").strip()
            try:
                priority_value = int(float(raw_priority))
            except Exception:
                priority_value = 0
        normalized.append(
            {
                "question": question,
                "answer": answer,
                "priority": priority_value,
            }
        )

    if not normalized:
        return ORJSONResponse(
            {
                "inserted": 0,
                "updated": 0,
                "skipped": skipped or len(pairs),
                "total": len(pairs),
                "project": project_name,
            },
            status_code=201,
        )

    try:
        result = await mongo_client.insert_qa_pairs(project_name, normalized)
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_qa_import_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to import QA pairs") from exc

    # Combine skipped count from normalization and import
    total_skipped = skipped + int(result.get("skipped", 0))
    file_duplicates = int(result.get("file_duplicates", 0))
    db_duplicates = int(result.get("db_duplicates", 0))
    
    summary: dict[str, object] = {
        "inserted": int(result.get("inserted", 0)),
        "updated": int(result.get("updated", 0)),
        "skipped": total_skipped,
        "file_duplicates": file_duplicates,
        "db_duplicates": db_duplicates,
        "total": len(pairs),
        "project": project_name,
    }
    return ORJSONResponse(summary, status_code=201)


@router.post("/knowledge/qa", response_class=ORJSONResponse, status_code=201)
async def admin_create_knowledge_qa(
    request: Request,
    payload: KnowledgeQAPayload,
    project: str | None = None,
) -> ORJSONResponse:
    """Create a new Q&A pair."""
    from app import _get_project_context, logger
    
    project_name, _, mongo_client, _ = await _get_project_context(request, project)

    question = payload.question.strip()
    answer = payload.answer.strip()
    if not question or not answer:
        raise HTTPException(status_code=400, detail="question_and_answer_required")

    try:
        result = await mongo_client.insert_qa_pairs(
            project_name,
            [
                {
                    "question": question,
                    "answer": answer,
                    "priority": payload.priority,
                }
            ],
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_qa_insert_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to save QA pair") from exc

    return ORJSONResponse({**result, "project": project_name})


@router.put("/knowledge/qa/{pair_id}", response_class=ORJSONResponse)
async def admin_update_knowledge_qa(
    request: Request,
    pair_id: str,
    payload: KnowledgeQAPayload,
) -> ORJSONResponse:
    """Update an existing Q&A pair."""
    from app import _get_mongo_client, _fetch_qa_document, _resolve_admin_project, _normalize_project, logger
    
    mongo_client = _get_mongo_client(request)
    existing = await _fetch_qa_document(mongo_client, pair_id)
    if not existing:
        raise HTTPException(status_code=404, detail="qa_not_found")

    project_scope = _resolve_admin_project(request, existing.get("project"))

    question = payload.question.strip()
    answer = payload.answer.strip()
    if not question or not answer:
        raise HTTPException(status_code=400, detail="question_and_answer_required")

    try:
        updated = await mongo_client.update_qa_pair(
            pair_id,
            question=question,
            answer=answer,
            priority=payload.priority,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_qa_update_failed", pair_id=pair_id, project=project_scope, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to update QA pair") from exc

    if not updated:
        raise HTTPException(status_code=404, detail="qa_not_found")

    if project_scope:
        doc_project = _normalize_project(updated.get("project"))
        if doc_project and doc_project != project_scope:
            raise HTTPException(status_code=403, detail="project_forbidden")

    return ORJSONResponse(updated)


@router.delete("/knowledge/qa/{pair_id}", response_class=ORJSONResponse)
async def admin_delete_knowledge_qa(request: Request, pair_id: str) -> ORJSONResponse:
    """Delete a Q&A pair."""
    from app import _get_mongo_client, _fetch_qa_document, _resolve_admin_project, logger
    
    mongo_client = _get_mongo_client(request)
    existing = await _fetch_qa_document(mongo_client, pair_id)
    if not existing:
        raise HTTPException(status_code=404, detail="qa_not_found")

    project_scope = _resolve_admin_project(request, existing.get("project"))

    try:
        removed = await mongo_client.delete_qa_pair(pair_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_qa_delete_failed", pair_id=pair_id, project=project_scope, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to delete QA pair") from exc

    if not removed:
        raise HTTPException(status_code=404, detail="qa_not_found")

    return ORJSONResponse({"removed": True, "id": pair_id})


@router.post("/knowledge/qa/reorder", response_class=ORJSONResponse)
async def admin_reorder_knowledge_qa(
    request: Request,
    payload: KnowledgeQAReorderPayload,
    project: str | None = None,
) -> ORJSONResponse:
    """Reorder Q&A pairs by priority."""
    from app import _get_project_context, logger
    
    project_name, _, mongo_client, _ = await _get_project_context(request, project)
    order = [str(item).strip() for item in payload.order or [] if str(item).strip()]
    try:
        await mongo_client.reorder_qa_pairs(project_name, order)
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_qa_reorder_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to reorder QA pairs") from exc

    return ORJSONResponse({"order": order, "project": project_name})


# Unanswered questions endpoints
@router.get("/knowledge/unanswered", response_class=ORJSONResponse)
async def admin_list_unanswered(
    request: Request,
    project: str | None = None,
    limit: int = 500,
) -> ORJSONResponse:
    """List unanswered questions for a project."""
    from app import _get_project_context, logger
    
    try:
        safe_limit = max(1, min(int(limit), 5000))
    except Exception:
        safe_limit = 500

    project_name, _, mongo_client, _ = await _get_project_context(request, project)

    try:
        items = await mongo_client.list_unanswered_questions(project_name, limit=safe_limit)
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_unanswered_list_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to load unanswered questions") from exc

    return ORJSONResponse({"items": items, "project": project_name})


@router.post("/knowledge/unanswered/clear", response_class=ORJSONResponse)
async def admin_clear_unanswered(
    request: Request,
    payload: KnowledgeUnansweredClearPayload,
) -> ORJSONResponse:
    """Clear unanswered questions for a project."""
    from app import _get_project_context, logger
    
    project_hint = payload.project
    project_name, _, mongo_client, _ = await _get_project_context(request, project_hint)

    try:
        removed = await mongo_client.clear_unanswered_questions(project_name)
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_unanswered_clear_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to clear unanswered questions") from exc

    return ORJSONResponse({"removed": removed, "project": project_name})


@router.get("/knowledge/unanswered/export")
async def admin_export_unanswered(
    request: Request,
    project: str | None = None,
    limit: int = 1000,
) -> Response:
    """Export unanswered questions as CSV."""
    from app import _get_project_context, logger
    
    try:
        safe_limit = max(1, min(int(limit), 5000))
    except Exception:
        safe_limit = 1000

    project_name, _, mongo_client, _ = await _get_project_context(request, project)

    try:
        items = await mongo_client.list_unanswered_questions(project_name, limit=safe_limit)
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_unanswered_export_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to export unanswered questions") from exc

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["question", "hits", "updated_at", "project"])
    for item in items:
        updated_at = item.get("updated_at")
        if isinstance(updated_at, (int, float)):
            updated_iso = datetime.utcfromtimestamp(updated_at).isoformat()
        else:
            updated_iso = str(updated_at or "")
        writer.writerow([
            item.get("question", ""),
            item.get("hits", 0),
            updated_iso,
            item.get("project") or (project_name or ""),
        ])

    filename = f"unanswered-{(project_name or 'all')}.csv"
    content = buffer.getvalue().encode("utf-8")
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return Response(content, media_type="text/csv", headers=headers)


# Knowledge service endpoints
@router.get("/knowledge/service", response_class=ORJSONResponse)
async def admin_knowledge_service_status(request: Request) -> ORJSONResponse:
    """Get knowledge service status and configuration."""
    require_super_admin(request)
    from app import _knowledge_service_status_impl
    return await _knowledge_service_status_impl(request)


@router.post("/knowledge/service", response_class=ORJSONResponse)
async def admin_knowledge_service_update(
    request: Request,
    payload: KnowledgeServiceConfig,
) -> ORJSONResponse:
    """Update knowledge service configuration."""
    require_super_admin(request)
    from app import _knowledge_service_update_impl
    return await _knowledge_service_update_impl(request, payload)


@router.post("/knowledge/service/run", response_class=ORJSONResponse)
async def admin_knowledge_service_run(
    request: Request,
    payload: KnowledgeServiceRunRequest | None = None,
) -> ORJSONResponse:
    """Manually trigger knowledge service processing."""
    require_super_admin(request)
    from app import _knowledge_service_run_impl
    return await _knowledge_service_run_impl(request, payload)

