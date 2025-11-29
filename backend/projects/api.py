"""Project management API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import ORJSONResponse

from backend.auth import require_admin, require_super_admin, resolve_admin_project
from backend.bots.schemas import (
    MaxAction,
    MaxConfig,
    ProjectMaxAction,
    ProjectMaxConfig,
    ProjectTelegramAction,
    ProjectTelegramConfig,
    ProjectVkAction,
    ProjectVkConfig,
    TelegramAction,
    TelegramConfig,
    VkAction,
    VkConfig,
)
from backend.bots.utils import (
    project_max_payload,
    project_telegram_payload,
    project_vk_payload,
)
from backend.projects.schemas import (
    FeedbackCreatePayload,
    FeedbackUpdatePayload,
    OllamaInstallRequest,
    OllamaServerPayload,
    FeedbackUpdatePayload,
    OllamaInstallRequest,
    OllamaServerPayload,
    ProjectCreate,
    ProjectUpdate,
    PromptGenerationRequest,
)
from backend.utils.project import normalize_project as _normalize_project
from backend.api.utils import (
    build_download_url,
    project_response,
    redis_project_usage,
)
from backend.bots.max import MaxHub
from backend.bots.telegram import TelegramHub
from backend.bots.vk import VkHub
from backend.ollama import ollama_available
from backend.ollama.installer import (
    schedule_ollama_install,
    snapshot_install_jobs,
    update_install_job,
)
from backend.ollama_cluster import get_cluster_manager
from knowledge.text import (
    extract_doc_text,
    extract_docx_text,
    extract_pdf_text,
    extract_xls_text,
    extract_xlsx_text,
)
from knowledge.summary import generate_document_summary
from knowledge.tasks import queue_auto_description
from knowledge.tasks import queue_auto_description
from observability.logging import get_recent_logs, get_logger
from backend import llm_client
from backend.projects.constants import DEFAULT_PROMPT_ROLE, PROMPT_RESPONSE_CHAR_LIMIT
from backend.utils.web import normalize_source_url, download_page_text, build_prompt_from_role
from backend.system.health import mongo_check, redis_check, qdrant_check

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["projects"])  # Root prefix for legacy compatibility


@router.get("/api/v1/admin/projects", response_class=ORJSONResponse)
async def admin_projects(
    request: Request,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    """Return configured projects."""
    projects = await request.state.mongo.list_projects()
    return ORJSONResponse({"projects": [project_response(p) for p in projects]})


@router.get("/api/v1/admin/projects/storage", response_class=ORJSONResponse)
async def admin_projects_storage(
    request: Request,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    """Return aggregated storage usage per project (Mongo/GridFS/Redis)."""
    mongo = request.state.mongo
    projects = await mongo.list_projects()
    
    # Mongo stats
    mongo_stats = {}
    for p in projects:
        try:
            stats = await mongo.db.command("collStats", f"knowledge_{p.name}")
            mongo_stats[p.name] = stats.get("size", 0) + stats.get("totalIndexSize", 0)
        except Exception:
            mongo_stats[p.name] = 0

    # GridFS stats
    fs_stats = {}
    try:
        pipeline = [
            {"$group": {"_id": "$metadata.project", "totalSize": {"$sum": "$length"}}}
        ]
        async for doc in mongo.db["fs.files"].aggregate(pipeline):
            project = doc.get("_id") or "__default__"
            fs_stats[project] = doc.get("totalSize", 0)
    except Exception:
        pass

    redis_stats = await redis_project_usage()

    result = []
    for p in projects:
        r_stats = redis_stats.get(p.name, {})
        result.append({
            "name": p.name,
            "mongo_bytes": mongo_stats.get(p.name, 0),
            "fs_bytes": fs_stats.get(p.name, 0),
            "redis_bytes": r_stats.get("redis_bytes", 0),
            "redis_keys": r_stats.get("redis_keys", 0),
        })
    
    return ORJSONResponse({"projects": result})


@router.post("/api/v1/admin/projects", response_class=ORJSONResponse)
async def admin_create_project(
    request: Request,
    payload: ProjectCreate,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    """Create or update a project (domain)."""
    
    def _resolve_mail_text(field_name: str, existing_value: str | None) -> str | None:
        val = getattr(payload, field_name)
        if val is not None:
            return val if val.strip() else None
        return existing_value

    mongo: MongoClient = request.state.mongo

    normalized_name = _normalize_project(payload.name)

    if not normalized_name:
        raise HTTPException(status_code=400, detail="Project name required")

    existing = await mongo.get_project(normalized_name)
    
    # Prepare update data
    update_data = {}
    
    if payload.title is not None:
        update_data["title"] = payload.title
    if payload.domain is not None:
        update_data["domain"] = payload.domain
    if payload.admin_username is not None:
        update_data["admin_username"] = payload.admin_username
    if payload.admin_password:
        from backend.auth import resolve_admin_password_digest
        update_data["admin_password_hash"] = resolve_admin_password_digest(payload.admin_password)
    
    if payload.llm_model is not None:
        update_data["llm_model"] = payload.llm_model
    if payload.llm_prompt is not None:
        update_data["llm_prompt"] = payload.llm_prompt

    # Bot settings
    if payload.telegram_token is not None:
        update_data["telegram_token"] = payload.telegram_token or None
    if payload.telegram_auto_start is not None:
        update_data["telegram_auto_start"] = payload.telegram_auto_start
        
    if payload.max_token is not None:
        update_data["max_token"] = payload.max_token or None
    if payload.max_auto_start is not None:
        update_data["max_auto_start"] = payload.max_auto_start
        
    if payload.vk_token is not None:
        update_data["vk_token"] = payload.vk_token or None
    if payload.vk_auto_start is not None:
        update_data["vk_auto_start"] = payload.vk_auto_start

    # Mail settings
    current_mail_pass = existing.mail_password if existing else None
    
    if payload.mail_smtp_host is not None:
        update_data["mail_smtp_host"] = payload.mail_smtp_host
    if payload.mail_smtp_port is not None:
        update_data["mail_smtp_port"] = payload.mail_smtp_port
    if payload.mail_smtp_tls is not None:
        update_data["mail_smtp_tls"] = payload.mail_smtp_tls
    if payload.mail_username is not None:
        update_data["mail_username"] = payload.mail_username
        
    mail_pass = _resolve_mail_text("mail_password", current_mail_pass)
    if mail_pass is not None:
        update_data["mail_password"] = mail_pass
        
    if payload.mail_from is not None:
        update_data["mail_from"] = payload.mail_from
    if payload.mail_signature is not None:
        update_data["mail_signature"] = payload.mail_signature

    # Perform update/create
    if existing:
        project = await mongo.update_project(normalized_name, update_data)
    else:
        project = await mongo.create_project(normalized_name, **update_data)

    # Handle bot restarts if tokens changed
    # Handle bot restarts/starts
    # Telegram
    if payload.telegram_token is not None:
        # Check if token changed or it's a new project with token
        token_changed = not existing or payload.telegram_token != existing.telegram_token
        if token_changed and project.telegram_token:
            hub = TelegramHub.get_instance()
            if existing:
                await hub.stop_project(normalized_name)
            if project.telegram_auto_start:
                await hub.start_project(normalized_name, project.telegram_token)
    
    # MAX
    if payload.max_token is not None:
        token_changed = not existing or payload.max_token != existing.max_token
        if token_changed and project.max_token:
            hub = MaxHub.get_instance()
            if existing:
                await hub.stop_project(normalized_name)
            if project.max_auto_start:
                await hub.start_project(normalized_name, project.max_token)
            
    # VK
    if payload.vk_token is not None:
        token_changed = not existing or payload.vk_token != existing.vk_token
        if token_changed and project.vk_token:
            hub = VkHub.get_instance()
            if existing:
                await hub.stop_project(normalized_name)
            if project.vk_auto_start:
                await hub.start_project(normalized_name, project.vk_token)

    return ORJSONResponse(project_response(project))


@router.put("/api/v1/admin/projects/{domain}", response_class=ORJSONResponse)
async def admin_update_project(
    request: Request,
    domain: str,
    payload: ProjectUpdate,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    """Update an existing project."""
    mongo = request.state.mongo
    existing = await mongo.get_project(domain)
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = payload.model_dump(exclude_unset=True)
    
    # Handle password hashing
    if "admin_password" in update_data and update_data["admin_password"]:
        from backend.auth import resolve_admin_password_digest
        update_data["admin_password_hash"] = resolve_admin_password_digest(update_data.pop("admin_password"))
    
    # Perform update
    project = await mongo.update_project(domain, update_data)
    
    # Handle bot restarts/starts
    # Telegram
    if payload.telegram_token is not None:
        token_changed = payload.telegram_token != existing.telegram_token
        if token_changed and project.telegram_token:
            hub = TelegramHub.get_instance()
            await hub.stop_project(domain)
            if project.telegram_auto_start:
                await hub.start_project(domain, project.telegram_token)
    
    # MAX
    if payload.max_token is not None:
        token_changed = payload.max_token != existing.max_token
        if token_changed and project.max_token:
            hub = MaxHub.get_instance()
            await hub.stop_project(domain)
            if project.max_auto_start:
                await hub.start_project(domain, project.max_token)
            
    # VK
    if payload.vk_token is not None:
        token_changed = payload.vk_token != existing.vk_token
        if token_changed and project.vk_token:
            hub = VkHub.get_instance()
            await hub.stop_project(domain)
            if project.vk_auto_start:
                await hub.start_project(domain, project.vk_token)

    return ORJSONResponse(project_response(project))


@router.delete("/api/v1/admin/projects/{domain}", response_class=ORJSONResponse)
async def admin_delete_project(
    request: Request,
    domain: str,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    """Delete a project and stop its bots."""
    mongo = request.state.mongo
    project = await mongo.get_project(domain)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Stop bots
    await TelegramHub.get_instance().stop_project(domain)
    await MaxHub.get_instance().stop_project(domain)
    await VkHub.get_instance().stop_project(domain)

    # Delete data
    await mongo.delete_project(domain)
    
    return ORJSONResponse({"status": "deleted", "name": domain})


@router.get("/api/v1/admin/project-names", response_class=ORJSONResponse)
async def admin_project_names(
    request: Request,
    limit: int = 100,
    _: Any = Depends(require_admin),
) -> ORJSONResponse:
    """Return a list of known project identifiers."""
    projects = await request.state.mongo.list_projects(limit=limit)
    return ORJSONResponse({"names": [p.name for p in projects]})


# LLM & Ollama Management

@router.get("/api/v1/admin/llm/models", response_class=ORJSONResponse)
async def admin_llm_models() -> ORJSONResponse:
    """Return available LLM model identifiers."""
    # This would ideally come from config or dynamic discovery
    models = ["llama3", "mistral", "gemma"] 
    return ORJSONResponse({"models": models})


@router.get("/api/v1/admin/llm/availability", response_class=ORJSONResponse)
async def admin_llm_availability(
    request: Request,
    _: Any = Depends(require_admin),
) -> ORJSONResponse:
    """Expose a simple availability flag for the LLM cluster."""
    try:
        manager = get_cluster_manager()
        available = await manager.is_available()
        return ORJSONResponse({"available": available})
    except Exception:
        return ORJSONResponse({"available": False})


@router.get("/api/v1/admin/ollama/catalog", response_class=ORJSONResponse)
async def admin_ollama_catalog(
    request: Request,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    snapshot = await snapshot_install_jobs()
    return ORJSONResponse({"jobs": snapshot})


@router.get("/api/v1/admin/ollama/servers", response_class=ORJSONResponse)
async def admin_ollama_servers(
    request: Request,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    try:
        manager = get_cluster_manager()
        snapshot = await manager.describe()
        return ORJSONResponse({"servers": snapshot})
    except RuntimeError:
        return ORJSONResponse({"servers": []})


@router.post("/api/v1/admin/ollama/servers", response_class=ORJSONResponse)
async def admin_ollama_server_upsert(
    request: Request,
    payload: OllamaServerPayload,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    manager = get_cluster_manager()
    await manager.upsert_server(
        name=payload.name,
        base_url=payload.base_url,
        enabled=payload.enabled,
    )
    return ORJSONResponse({"status": "ok", "name": payload.name})


@router.delete("/api/v1/admin/ollama/servers/{name}", response_class=ORJSONResponse)
async def admin_ollama_server_delete(
    request: Request,
    name: str,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    manager = get_cluster_manager()
    await manager.remove_server(name)
    return ORJSONResponse({"status": "deleted", "name": name})


@router.post("/api/v1/admin/ollama/install", response_class=ORJSONResponse)
async def admin_ollama_install(
    request: Request,
    payload: OllamaInstallRequest,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    job = await schedule_ollama_install(payload.model)
    return ORJSONResponse(job)


# Feedback

@router.post("/api/v1/feedback", response_class=ORJSONResponse)
async def submit_feedback(
    request: Request,
    payload: FeedbackCreatePayload,
) -> ORJSONResponse:
    item = await request.state.mongo.create_feedback(
        message=payload.message,
        name=payload.name,
        contact=payload.contact,
        page=payload.page,
        project=payload.project,
        source=payload.source,
    )
    return ORJSONResponse(item.model_dump(by_alias=True))


@router.get("/api/v1/admin/feedback", response_class=ORJSONResponse)
async def admin_feedback_list(
    request: Request,
    limit: int = 100,
    _: Any = Depends(require_admin),
) -> ORJSONResponse:
    items = await request.state.mongo.list_feedback(limit=limit)
    return ORJSONResponse({"items": [item.model_dump(by_alias=True) for item in items]})


@router.patch("/api/v1/admin/feedback/{task_id}", response_class=ORJSONResponse)
async def admin_feedback_update(
    request: Request,
    task_id: str,
    payload: FeedbackUpdatePayload,
    _: Any = Depends(require_admin),
) -> ORJSONResponse:
    item = await request.state.mongo.update_feedback(
        task_id,
        status=payload.status,
        note=payload.note,
    )
    if not item:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return ORJSONResponse(item.model_dump(by_alias=True))


# Bot Management Endpoints

@router.get("/api/v1/admin/telegram/status", response_class=ORJSONResponse)
async def telegram_status(
    request: Request,
    _: Any = Depends(require_admin),
) -> ORJSONResponse:
    project_name = resolve_admin_project(request, None, required=True)
    project = await request.state.mongo.get_project(project_name)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ORJSONResponse(project_telegram_payload(project, TelegramHub.get_instance()))


@router.post("/api/v1/admin/telegram/config", response_class=ORJSONResponse)
async def telegram_config(
    request: Request,
    payload: TelegramConfig,
    _: Any = Depends(require_admin),
) -> ORJSONResponse:
    project_name = resolve_admin_project(request, None, required=True)
    update = {}
    if payload.token is not None:
        token = payload.token.strip() if payload.token else None
        update["telegram_token"] = token or None
    if payload.auto_start is not None:
        update["telegram_auto_start"] = payload.auto_start
        
    project = await request.state.mongo.update_project(project_name, update)
    return ORJSONResponse(project_telegram_payload(project, TelegramHub.get_instance()))


@router.post("/api/v1/admin/telegram/start", response_class=ORJSONResponse)
async def telegram_start(
    request: Request,
    payload: TelegramAction,
    _: Any = Depends(require_admin),
) -> ORJSONResponse:
    project_name = resolve_admin_project(request, None, required=True)
    project = await request.state.mongo.get_project(project_name)
    token = payload.token or project.telegram_token
    
    if not token:
        raise HTTPException(status_code=400, detail="Token required")
        
    hub = TelegramHub.get_instance()
    await hub.start_project(project_name, token)
    
    # Update token if provided and different
    if payload.token and payload.token != project.telegram_token:
        project = await request.state.mongo.update_project(project_name, {"telegram_token": payload.token})
        
    return ORJSONResponse(project_telegram_payload(project, hub))


@router.post("/api/v1/admin/telegram/stop", response_class=ORJSONResponse)
async def telegram_stop(
    request: Request,
    _: Any = Depends(require_admin),
) -> ORJSONResponse:
    project_name = resolve_admin_project(request, None, required=True)
    hub = TelegramHub.get_instance()
    await hub.stop_project(project_name)
    
    project = await request.state.mongo.get_project(project_name)
    return ORJSONResponse(project_telegram_payload(project, hub))


# MAX Bot Endpoints

@router.get("/api/v1/admin/max/status", response_class=ORJSONResponse)
async def max_status(
    request: Request,
    _: Any = Depends(require_admin),
) -> ORJSONResponse:
    project_name = resolve_admin_project(request, None, required=True)
    project = await request.state.mongo.get_project(project_name)
    return ORJSONResponse(project_max_payload(project, MaxHub.get_instance()))


@router.post("/api/v1/admin/max/config", response_class=ORJSONResponse)
async def max_config(
    request: Request,
    payload: MaxConfig,
    _: Any = Depends(require_admin),
) -> ORJSONResponse:
    project_name = resolve_admin_project(request, None, required=True)
    update = {}
    if payload.token is not None:
        update["max_token"] = payload.token or None
    if payload.auto_start is not None:
        update["max_auto_start"] = payload.auto_start
        
    project = await request.state.mongo.update_project(project_name, update)
    return ORJSONResponse(project_max_payload(project, MaxHub.get_instance()))


@router.post("/api/v1/admin/max/start", response_class=ORJSONResponse)
async def max_start(
    request: Request,
    payload: MaxAction,
    _: Any = Depends(require_admin),
) -> ORJSONResponse:
    project_name = resolve_admin_project(request, None, required=True)
    project = await request.state.mongo.get_project(project_name)
    token = payload.token or project.max_token
    
    if not token:
        raise HTTPException(status_code=400, detail="Token required")
        
    hub = MaxHub.get_instance()
    await hub.start_project(project_name, token)
    
    if payload.token and payload.token != project.max_token:
        project = await request.state.mongo.update_project(project_name, {"max_token": payload.token})
        
    return ORJSONResponse(project_max_payload(project, hub))


@router.post("/api/v1/admin/max/stop", response_class=ORJSONResponse)
async def max_stop(
    request: Request,
    _: Any = Depends(require_admin),
) -> ORJSONResponse:
    project_name = resolve_admin_project(request, None, required=True)
    hub = MaxHub.get_instance()
    await hub.stop_project(project_name)
    
    project = await request.state.mongo.get_project(project_name)
    return ORJSONResponse(project_max_payload(project, hub))


# VK Bot Endpoints

@router.get("/api/v1/admin/vk/status", response_class=ORJSONResponse)
async def vk_status(
    request: Request,
    _: Any = Depends(require_admin),
) -> ORJSONResponse:
    project_name = resolve_admin_project(request, None, required=True)
    project = await request.state.mongo.get_project(project_name)
    return ORJSONResponse(project_vk_payload(project, VkHub.get_instance()))


@router.post("/api/v1/admin/vk/config", response_class=ORJSONResponse)
async def vk_config(
    request: Request,
    payload: VkConfig,
    _: Any = Depends(require_admin),
) -> ORJSONResponse:
    project_name = resolve_admin_project(request, None, required=True)
    update = {}
    if payload.token is not None:
        update["vk_token"] = payload.token or None
    if payload.auto_start is not None:
        update["vk_auto_start"] = payload.auto_start
        
    project = await request.state.mongo.update_project(project_name, update)
    return ORJSONResponse(project_vk_payload(project, VkHub.get_instance()))


@router.post("/api/v1/admin/vk/start", response_class=ORJSONResponse)
async def vk_start(
    request: Request,
    payload: VkAction,
    _: Any = Depends(require_admin),
) -> ORJSONResponse:
    project_name = resolve_admin_project(request, None, required=True)
    project = await request.state.mongo.get_project(project_name)
    token = payload.token or project.vk_token
    
    if not token:
        raise HTTPException(status_code=400, detail="Token required")
        
    hub = VkHub.get_instance()
    await hub.start_project(project_name, token)
    
    if payload.token and payload.token != project.vk_token:
        project = await request.state.mongo.update_project(project_name, {"vk_token": payload.token})
        
    return ORJSONResponse(project_vk_payload(project, hub))


@router.post("/api/v1/admin/vk/stop", response_class=ORJSONResponse)
async def vk_stop(
    request: Request,
    _: Any = Depends(require_admin),
) -> ORJSONResponse:
    project_name = resolve_admin_project(request, None, required=True)
    hub = VkHub.get_instance()
    await hub.stop_project(project_name)
    
    project = await request.state.mongo.get_project(project_name)
    return ORJSONResponse(project_vk_payload(project, hub))


# Super Admin Project Bot Management

@router.get("/api/v1/admin/projects/{project}/telegram/status", response_class=ORJSONResponse)
async def admin_project_telegram_status(
    project: str,
    request: Request,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    proj = await request.state.mongo.get_project(project)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return ORJSONResponse(project_telegram_payload(proj, TelegramHub.get_instance()))


@router.post("/api/v1/admin/projects/{project}/telegram/config", response_class=ORJSONResponse)
async def admin_project_telegram_config(
    project: str,
    request: Request,
    payload: ProjectTelegramConfig,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    update = {}
    if payload.token is not None:
        token = payload.token.strip() if payload.token else None
        update["telegram_token"] = token or None
    if payload.auto_start is not None:
        update["telegram_auto_start"] = payload.auto_start
        
    proj = await request.state.mongo.update_project(project, update)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return ORJSONResponse(project_telegram_payload(proj, TelegramHub.get_instance()))


@router.post("/api/v1/admin/projects/{project}/telegram/start", response_class=ORJSONResponse)
async def admin_project_telegram_start(
    project: str,
    request: Request,
    payload: ProjectTelegramAction,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    proj = await request.state.mongo.get_project(project)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
        
    token = payload.token or proj.telegram_token
    if not token:
        raise HTTPException(status_code=400, detail="Token required")
        
    hub = TelegramHub.get_instance()
    await hub.start_project(project, token)
    
    if payload.token and payload.token != proj.telegram_token:
        proj = await request.state.mongo.update_project(project, {"telegram_token": payload.token})
        
    return ORJSONResponse(project_telegram_payload(proj, hub))


@router.post("/api/v1/admin/projects/{project}/telegram/stop", response_class=ORJSONResponse)
async def admin_project_telegram_stop(
    project: str,
    request: Request,
    payload: ProjectTelegramAction | None = None,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    hub = TelegramHub.get_instance()
    await hub.stop_project(project)
    
    proj = await request.state.mongo.get_project(project)
    return ORJSONResponse(project_telegram_payload(proj, hub))


@router.get("/api/v1/admin/projects/{project}/max/status", response_class=ORJSONResponse)
async def admin_project_max_status(
    project: str,
    request: Request,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    proj = await request.state.mongo.get_project(project)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return ORJSONResponse(project_max_payload(proj, MaxHub.get_instance()))


@router.post("/api/v1/admin/projects/{project}/max/config", response_class=ORJSONResponse)
async def admin_project_max_config(
    project: str,
    request: Request,
    payload: ProjectMaxConfig,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    update = {}
    if payload.token is not None:
        update["max_token"] = payload.token or None
    if payload.auto_start is not None:
        update["max_auto_start"] = payload.auto_start
        
    proj = await request.state.mongo.update_project(project, update)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return ORJSONResponse(project_max_payload(proj, MaxHub.get_instance()))


@router.post("/api/v1/admin/projects/{project}/max/start", response_class=ORJSONResponse)
async def admin_project_max_start(
    project: str,
    request: Request,
    payload: ProjectMaxAction,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    proj = await request.state.mongo.get_project(project)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
        
    token = payload.token or proj.max_token
    if not token:
        raise HTTPException(status_code=400, detail="Token required")
        
    hub = MaxHub.get_instance()
    await hub.start_project(project, token)
    
    if payload.token and payload.token != proj.max_token:
        proj = await request.state.mongo.update_project(project, {"max_token": payload.token})
        
    return ORJSONResponse(project_max_payload(proj, hub))


@router.post("/api/v1/admin/projects/{project}/max/stop", response_class=ORJSONResponse)
async def admin_project_max_stop(
    project: str,
    request: Request,
    payload: ProjectMaxAction | None = None,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    hub = MaxHub.get_instance()
    await hub.stop_project(project)
    
    proj = await request.state.mongo.get_project(project)
    return ORJSONResponse(project_max_payload(proj, hub))


@router.get("/api/v1/admin/projects/{project}/vk/status", response_class=ORJSONResponse)
async def admin_project_vk_status(
    project: str,
    request: Request,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    proj = await request.state.mongo.get_project(project)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return ORJSONResponse(project_vk_payload(proj, VkHub.get_instance()))


@router.post("/api/v1/admin/projects/{project}/vk/config", response_class=ORJSONResponse)
async def admin_project_vk_config(
    project: str,
    request: Request,
    payload: ProjectVkConfig,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    update = {}
    if payload.token is not None:
        update["vk_token"] = payload.token or None
    if payload.auto_start is not None:
        update["vk_auto_start"] = payload.auto_start
        
    proj = await request.state.mongo.update_project(project, update)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return ORJSONResponse(project_vk_payload(proj, VkHub.get_instance()))


@router.post("/api/v1/admin/projects/{project}/vk/start", response_class=ORJSONResponse)
async def admin_project_vk_start(
    project: str,
    request: Request,
    payload: ProjectVkAction,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    proj = await request.state.mongo.get_project(project)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
        
    token = payload.token or proj.vk_token
    if not token:
        raise HTTPException(status_code=400, detail="Token required")
        
    hub = VkHub.get_instance()
    await hub.start_project(project, token)
    
    if payload.token and payload.token != proj.vk_token:
        proj = await request.state.mongo.update_project(project, {"vk_token": payload.token})
        
    return ORJSONResponse(project_vk_payload(proj, hub))


@router.post("/api/v1/admin/projects/{project}/vk/stop", response_class=ORJSONResponse)
async def admin_project_vk_stop(
    project: str,
    request: Request,
    payload: ProjectVkAction | None = None,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    hub = VkHub.get_instance()
    await hub.stop_project(project)
    
    proj = await request.state.mongo.get_project(project)
    return ORJSONResponse(project_vk_payload(proj, hub))


# Stats

@router.get("/api/v1/admin/stats", response_class=ORJSONResponse)
async def admin_request_stats(
    request: Request,
    project: str | None = None,
    start: str | None = None,
    end: str | None = None,
    channel: str | None = None,
    _: Any = Depends(require_admin),
) -> ORJSONResponse:
    from backend.api.utils import parse_stats_date
    
    project_scope = resolve_admin_project(request, project)
    start_dt = parse_stats_date(start)
    end_dt = parse_stats_date(end)
    
    stats = await request.state.mongo.get_request_stats(
        project=project_scope,
        start_date=start_dt,
        end_date=end_dt,
        channel=channel,
    )
    return ORJSONResponse({"stats": stats})


@router.get("/api/v1/admin/stats/export", response_class=ORJSONResponse)
async def admin_request_stats_export(
    request: Request,
    project: str | None = None,
    start: str | None = None,
    end: str | None = None,
    channel: str | None = None,
    _: Any = Depends(require_admin),
) -> ORJSONResponse:
    from backend.api.utils import parse_stats_date
    
    project_scope = resolve_admin_project(request, project)
    start_dt = parse_stats_date(start)
    end_dt = parse_stats_date(end)
    
    data = await request.state.mongo.export_request_stats(
        project=project_scope,
        start_date=start_dt,
        end_date=end_dt,
        channel=channel,
    )
    return ORJSONResponse({"data": data})
    return ORJSONResponse({"data": data})


@router.post("/api/v1/admin/projects/prompt", response_class=ORJSONResponse)
async def admin_generate_project_prompt(
    request: Request,
    payload: PromptGenerationRequest,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    try:
        normalized_url = normalize_source_url(payload.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    page_text = await download_page_text(normalized_url)
    prompt_body, role_key, role_label = build_prompt_from_role(payload.role or DEFAULT_PROMPT_ROLE, normalized_url, page_text)

    chunks: list[str] = []
    try:
        async for token in llm_client.generate(prompt_body):
            chunks.append(token)
            if len("".join(chunks)) >= PROMPT_RESPONSE_CHAR_LIMIT:
                break
    except Exception as exc:
        logger.error("prompt_generate_failed", url=normalized_url, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to generate prompt") from exc

    return ORJSONResponse(
        {
            "prompt": "".join(chunks),
            "role": role_key,
            "role_label": role_label,
            "url": normalized_url,
        }
    )


@router.get("/api/v1/admin/projects/{domain}/test", response_class=ORJSONResponse)
async def admin_test_project(
    domain: str,
    request: Request,
    _: Any = Depends(require_super_admin),
) -> ORJSONResponse:
    domain_value = resolve_admin_project(request, domain, required=True)

    mongo_ok, mongo_err = mongo_check()
    redis_ok, redis_err = redis_check()
    qdrant_ok, qdrant_err = qdrant_check()

    # Verify project existence
    await request.state.mongo.get_project(domain_value)

    return ORJSONResponse(
        {
            "name": domain_value,
            "mongo": {"ok": mongo_ok, "error": mongo_err},
            "redis": {"ok": redis_ok, "error": redis_err},
            "qdrant": {"ok": qdrant_ok, "error": qdrant_err},
        }
    )
