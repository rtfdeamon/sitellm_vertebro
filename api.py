"""FastAPI routers for interacting with the LLM and crawler."""

from pathlib import Path
import subprocess
import sys
import os
import signal
import urllib.parse as urlparse
from typing import Any

from fastapi import APIRouter, Request, HTTPException
try:
    from fastapi import BackgroundTasks
except ImportError:  # pragma: no cover - fallback for test stubs
    class BackgroundTasks:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass
from fastapi.responses import ORJSONResponse, StreamingResponse
import asyncio

import redis.asyncio as redis

import structlog

from backend import llm_client
from backend.settings import settings as backend_settings
from retrieval import search as retrieval_search

from models import Document, LLMResponse, LLMRequest, RoleEnum, Project
from mongo import NotFound
from pydantic import BaseModel

from core.status import status_dict
from settings import MongoSettings

logger = structlog.get_logger(__name__)


def _normalize_project(value: str | None) -> str | None:
    candidate = (value or "").strip().lower()
    if candidate:
        return candidate
    fallback = backend_settings.project_name or backend_settings.domain
    if fallback:
        return fallback.strip().lower() or None
    return None


_KNOWLEDGE_SNIPPET_CHARS = 480
_MAX_DIALOG_TURNS = 10


def _truncate_text(text: str, limit: int = _KNOWLEDGE_SNIPPET_CHARS) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    truncated = cleaned[:limit].rsplit(" ", 1)[0].strip()
    if not truncated:
        truncated = cleaned[:limit]
    return truncated.rstrip(". ") + "…"


def _extract_payload_text(payload: Any) -> str:
    if not payload:
        return ""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        for key in ("text", "content", "body", "chunk"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
        meta = payload.get("metadata")
        if isinstance(meta, dict):
            return _extract_payload_text(meta)
    return ""


def _extract_payload_name(payload: Any, default: str | None = None) -> str | None:
    if isinstance(payload, dict):
        for key in ("title", "name", "source", "document", "file_name"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        url = payload.get("url")
        if isinstance(url, str) and url.strip():
            return url.strip()
    return default


def _extract_payload_url(payload: Any) -> str | None:
    if isinstance(payload, dict):
        url = payload.get("url")
        if isinstance(url, str) and url.strip():
            return url.strip()
    return None


async def _collect_knowledge_snippets(
    request: Request,
    question: str,
    project: str | None,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    question = (question or "").strip()
    if not question:
        return []

    snippets: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    try:
        docs = await asyncio.to_thread(retrieval_search.hybrid_search, question, limit * 2)
    except Exception as exc:  # noqa: BLE001
        logger.debug("knowledge_hybrid_failed", error=str(exc))
        docs = []

    for doc in docs:
        payload = getattr(doc, "payload", None)
        text = _extract_payload_text(payload)
        if not text:
            continue
        doc_id = str(getattr(doc, "id", "")) or None
        if doc_id and doc_id in seen_ids:
            continue
        snippets.append(
            {
                "id": doc_id,
                "name": _extract_payload_name(payload, default=doc_id),
                "text": text,
                "score": getattr(doc, "score", None),
                "url": _extract_payload_url(payload),
                "source": "qdrant",
            }
        )
        if doc_id:
            seen_ids.add(doc_id)
        if len(snippets) >= limit:
            break

    if len(snippets) >= limit:
        return snippets[:limit]

    mongo_client = getattr(request.state, "mongo", None)
    if not mongo_client or not hasattr(mongo_client, "search_documents"):
        return snippets[:limit]

    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)

    try:
        candidates = await mongo_client.search_documents(
            collection, question, project=project
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("knowledge_mongo_search_failed", error=str(exc))
        candidates = []

    if not candidates:
        try:
            query: dict[str, Any] = {}
            if project:
                query["project"] = project
            cursor = (
                mongo_client.db[collection]
                .find(query, {"_id": False})
                .sort("ts", -1)
                .limit(limit * 2)
            )
            candidates = [Document(**doc) async for doc in cursor]
        except Exception as exc:  # noqa: BLE001
            logger.debug("knowledge_mongo_fallback_failed", error=str(exc))
            candidates = []

    for doc in candidates:
        if len(snippets) >= limit:
            break
        file_id = getattr(doc, "fileId", None)
        if file_id and file_id in seen_ids:
            continue
        text = ""
        try:
            _meta, payload = await mongo_client.get_document_with_content(
                collection, doc.fileId
            )
            text = payload.decode("utf-8", errors="ignore")
        except Exception as exc:  # noqa: BLE001
            logger.debug("knowledge_content_fetch_failed", file_id=file_id, error=str(exc))
            text = doc.description or ""
        if not text.strip():
            continue
        snippets.append(
            {
                "id": file_id,
                "name": doc.name,
                "text": text,
                "score": getattr(doc, "ts", None),
                "url": doc.url,
                "source": "mongo",
            }
        )
        if file_id:
            seen_ids.add(file_id)

    return snippets[:limit]


def _compose_knowledge_message(snippets: list[dict[str, Any]]) -> str:
    if not snippets:
        return ""
    blocks: list[str] = []
    for idx, item in enumerate(snippets, 1):
        name = item.get("name") or f"Источник {idx}"
        snippet_text = _truncate_text(item.get("text", ""))
        blocks.append(f"Источник {idx} ({name}):\n{snippet_text}")
    return (
        "Используй приведённые ниже выдержки из базы знаний при ответе."
        "\n\n" + "\n\n".join(blocks)
    )


def _limit_dialog_history(messages: list[dict[str, Any]], max_turns: int = _MAX_DIALOG_TURNS) -> list[dict[str, Any]]:
    """Return ``messages`` trimmed to the last ``max_turns`` user requests."""

    if max_turns <= 0 or len(messages) <= 2 * max_turns:
        return messages

    kept: list[dict[str, Any]] = []
    user_seen = 0

    for msg in reversed(messages):
        role = str(msg.get("role", "")).lower()
        if role == RoleEnum.user.value:
            user_seen += 1
        kept.append(msg)
        if user_seen >= max_turns:
            break

    return list(reversed(kept))


llm_router = APIRouter(
    prefix="/llm",
    tags=["llm"],
    responses={
        200: {"description": "LLM response"},
        404: {"description": "Can't find specified sessionId"},
        500: {"description": "Internal Server Error"},
    },
)

crawler_router = APIRouter(
    prefix="/crawler",
    tags=["crawler"],
)


@llm_router.post("/ask", response_class=ORJSONResponse, response_model=LLMResponse)
async def ask_llm(request: Request, llm_request: LLMRequest) -> ORJSONResponse:
    """Return a response from the language model for the given session.

    Parameters
    ----------
    request:
        Incoming request used to access application state.
    llm_request:
        Input payload specifying the ``session_id`` and optional project slug.

    Raises
    ------
    HTTPException
        If the session or preset cannot be found or if generation fails.
    """

    try:
        mongo_client = request.state.mongo
    except Exception as exc:
        logger.error("mongo_client_missing", error=str(exc))
        raise HTTPException(status_code=500, detail="Mongo client unavailable") from exc
    project_name = _normalize_project(llm_request.project)
    project: Project | None = None
    if project_name:
        try:
            project = await request.state.mongo.get_project(project_name)
            if project is None:
                project = await request.state.mongo.upsert_project(Project(name=project_name))
        except Exception as exc:
            logger.error("project_resolve_failed", project=project_name, error=str(exc))
            raise HTTPException(status_code=500, detail="Failed to resolve project") from exc
    logger.info("ask", session=str(llm_request.session_id), project=project_name)
    context = []

    try:
        preset = [
            {"role": message.role, "content": message.text}
            async for message in mongo_client.get_context_preset(
                request.state.context_presets_collection
            )
        ]
    except NotFound:
        logger.warning("preset_not_found", session=str(llm_request.session_id))
        raise HTTPException(status_code=404, detail="Preset not found")
    except Exception as exc:
        logger.error("preset_load_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to load preset") from exc
    try:
        async for message in mongo_client.get_sessions(
            request.state.contexts_collection, str(llm_request.session_id)
        ):
            context.append({"role": str(message.role), "content": message.text})
    except NotFound:
        logger.warning("session_not_found", session=str(llm_request.session_id))
        raise HTTPException(status_code=404, detail="Can't find specified sessionId")
    except Exception as exc:
        logger.error("session_load_failed", session=str(llm_request.session_id), error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to load session history") from exc

    if not context:
        raise HTTPException(status_code=400, detail="No conversation history provided")

    context = _limit_dialog_history(context)

    if context[-1]["role"] == RoleEnum.assistant:
        logger.error(
            "incorrect session state", session=str(llm_request.session_id)
        )
        raise HTTPException(
            status_code=400, detail="Last message role cannot be assistant"
        )

    knowledge_snippets: list[dict[str, Any]] = []
    knowledge_message = ""
    try:
        question_text = context[-1].get("content", "")
        knowledge_snippets = await _collect_knowledge_snippets(
            request, question_text, project_name
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "knowledge_lookup_failed",
            session=str(llm_request.session_id),
            project=project_name,
            error=str(exc),
        )
    else:
        knowledge_message = _compose_knowledge_message(knowledge_snippets)
        if knowledge_message:
            preset = preset + [{"role": "system", "content": knowledge_message}]
            logger.info(
                "knowledge_context_attached",
                session=str(llm_request.session_id),
                project=project_name,
                docs=[
                    {
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "source": item.get("source"),
                        "url": item.get("url"),
                        "chars": len(item.get("text", "")),
                        "score": item.get("score"),
                    }
                    for item in knowledge_snippets
                ],
            )

    if project and project.llm_prompt:
        prompt_text = project.llm_prompt.strip()
        if prompt_text:
            preset = [{"role": "system", "content": prompt_text}] + preset

    # Build a prompt similar to the HTTPModelClient/YaLLM formatting
    prompt_parts: list[str] = []
    for m in preset + context:
        role = m.get("role", "user")
        text = m.get("content", "")
        prompt_parts.append(f"{role}: {text}")
    prompt = "\n".join(prompt_parts)

    chunks: list[str] = []
    model_override = None
    if project and project.llm_model:
        trimmed_model = project.llm_model.strip()
        if trimmed_model:
            model_override = trimmed_model
    try:
        async for token in llm_client.generate(prompt, model=model_override):
            chunks.append(token)
    except Exception as exc:
        logger.error("llm_generate_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="LLM generation failed") from exc
    text = "".join(chunks)
    logger.info("llm answered", length=len(text))

    return ORJSONResponse(LLMResponse(text=text).model_dump())


@llm_router.get("/chat")
async def chat(request: Request, question: str, project: str | None = None) -> StreamingResponse:
    """Stream tokens from the language model using server-sent events.

    Parameters
    ----------
    question:
        Text sent as a query parameter. Example: ``/chat?question=hi``.
    """

    project_name = _normalize_project(project)
    project_obj: Project | None = None
    if project_name:
        project_obj = await request.state.mongo.get_project(project_name)
        if project_obj is None:
            project_obj = await request.state.mongo.upsert_project(Project(name=project_name))

    prompt_base = question
    if project_obj and project_obj.llm_prompt:
        prompt_text = project_obj.llm_prompt.strip()
        if prompt_text:
            prompt_base = f"{prompt_text}\n\n{question}"
    model_override = None
    if project_obj and project_obj.llm_model:
        model_text = project_obj.llm_model.strip()
        if model_text:
            model_override = model_text

    logger.info("chat", question=question, project=project_name)

    knowledge_snippets: list[dict[str, Any]] = []
    try:
        knowledge_snippets = await _collect_knowledge_snippets(
            request, question, project_name
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "knowledge_lookup_failed",
            project=project_name,
            error=str(exc),
            mode="stream",
        )
    else:
        knowledge_message = _compose_knowledge_message(knowledge_snippets)
        if knowledge_message:
            prompt_base = "\n\n".join([knowledge_message, f"Вопрос: {prompt_base}", "Ответ:"])
            logger.info(
                "knowledge_context_attached",
                project=project_name,
                mode="stream",
                docs=[
                    {
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "source": item.get("source"),
                        "url": item.get("url"),
                        "chars": len(item.get("text", "")),
                        "score": item.get("score"),
                    }
                    for item in knowledge_snippets
                ],
            )

    async def event_stream():
        try:
            async for token in llm_client.generate(prompt_base, model=model_override):
                yield f"data: {token}\n\n"
        except Exception as exc:  # keep connection graceful for the widget
            logger.warning("sse_generate_failed", error=str(exc))
            yield "event: llm_error\ndata: generation_failed\n\n"
        finally:
            # Signal the client that stream has completed
            yield "event: end\ndata: [DONE]\n\n"

    model_header = model_override or getattr(llm_client, "MODEL_NAME", "unknown")
    headers = {"X-Model-Name": model_header}
    response = StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)
    return response


class CrawlRequest(BaseModel):
    start_url: str
    max_pages: int = 500
    max_depth: int = 3
    project: str | None = None
    domain: str | None = None


crawler_router = APIRouter(prefix="/crawler", tags=["crawler"])


def _spawn_crawler(
    start_url: str,
    max_pages: int,
    max_depth: int,
    *,
    project: str | None,
    domain: str | None,
    mongo_uri: str | None,
) -> None:
    script = Path(__file__).resolve().parent / "crawler" / "run_crawl.py"
    cmd = [
        sys.executable,
        str(script),
        "--url",
        start_url,
        "--max-pages",
        str(max_pages),
        "--max-depth",
        str(max_depth),
    ]
    if project:
        cmd.extend(["--project", project])
    if domain:
        cmd.extend(["--domain", domain])
    if mongo_uri:
        cmd.extend(["--mongo-uri", mongo_uri])
    proc = subprocess.Popen(cmd)
    try:
        (Path("/tmp") / "crawler.pid").write_text(str(proc.pid), encoding="utf-8")
    except Exception:
        pass


@crawler_router.post("/run", status_code=202)
async def run_crawler(
    req: CrawlRequest, background_tasks: BackgroundTasks, request: Request
) -> dict[str, str]:
    """Start the crawler in a background task."""

    parsed_host = urlparse.urlsplit(req.start_url).netloc
    allowed_domain = (req.domain or parsed_host or "").lower()
    project_name = _normalize_project(req.project) or _normalize_project(allowed_domain)
    if not project_name:
        raise HTTPException(status_code=400, detail="project is required")

    project = await request.state.mongo.get_project(project_name)
    if project is None:
        project = await request.state.mongo.upsert_project(
            Project(name=project_name, domain=allowed_domain or None)
        )

    background_tasks.add_task(
        _spawn_crawler,
        req.start_url,
        req.max_pages,
        req.max_depth,
        project=project_name,
        domain=allowed_domain or None,
        mongo_uri=backend_settings.mongo_uri,
    )
    return {
        "status": "started",
        "project": project_name,
        "domain": allowed_domain or None,
    }


@crawler_router.get("/status")
async def crawler_status(project: str | None = None) -> dict[str, object]:
    """Return current crawler and database status."""

    return status_dict(_normalize_project(project))


@crawler_router.post("/stop", status_code=202)
async def stop_crawler() -> dict[str, str]:
    """Attempt to stop the last started crawler process by PID file."""
    pid_path = Path("/tmp") / "crawler.pid"
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
    except Exception:
        return {"status": "unknown"}
    try:
        os.kill(pid, signal.SIGTERM)
        return {"status": "stopping", "pid": pid}
    except ProcessLookupError:
        return {"status": "not_running"}
    except Exception:
        return {"status": "error"}


@llm_router.get("/info")
def llm_info() -> dict[str, object]:
    """Expose basic LLM runtime details for the admin panel."""
    device = getattr(llm_client, "DEVICE", "unknown")
    model = getattr(llm_client, "MODEL_NAME", None)
    ollama = getattr(llm_client, "OLLAMA_BASE", None)
    backend = "ollama" if ollama else (device or "local")
    return {
        "model": model,
        "device": device,
        "backend": backend,
        "ollama_base": ollama,
    }


class LLMConfig(BaseModel):
    ollama_base: str | None = None
    model: str | None = None


@llm_router.post("/config", response_class=ORJSONResponse)
def llm_set_config(cfg: LLMConfig) -> ORJSONResponse:
    """Update LLM runtime parameters at runtime.

    This does not persist across process restarts; intended for quick ops.
    """
    if cfg.ollama_base is not None:
        llm_client.OLLAMA_BASE = cfg.ollama_base or None
    if cfg.model:
        llm_client.MODEL_NAME = cfg.model
    return ORJSONResponse(llm_info())


@llm_router.get("/ping")
async def llm_ping() -> dict[str, object]:
    """Ping the configured LLM backend.

    - If Ollama base is set, checks ``/api/tags``.
    - Otherwise returns enabled=False.
    """
    base = getattr(llm_client, "OLLAMA_BASE", None)
    if not base:
        return {"enabled": False, "reachable": None}
    import httpx
    url = f"{base.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            resp = await client.get(url)
            ok = bool(resp.status_code == 200)
            return {"enabled": True, "reachable": ok, "status": resp.status_code}
    except Exception as exc:
        return {"enabled": True, "reachable": False, "error": str(exc)}
