"""Projects management router.

Provides endpoints for project CRUD operations, configuration, and bot management.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import ORJSONResponse

from typing import TYPE_CHECKING, Any

from app.services.auth import require_admin, require_super_admin
from pydantic import BaseModel

if TYPE_CHECKING:
    from tg_bot.bot import TelegramHub
    from max_bot.config import MaxHub
    from vk_bot.config import VkHub
    from models import Project

router = APIRouter(prefix="/api/v1/admin", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    title: str | None = None
    domain: str | None = None
    admin_username: str | None = None
    admin_password: str | None = None
    llm_model: str | None = None
    llm_prompt: str | None = None
    llm_emotions_enabled: bool | None = None
    llm_voice_enabled: bool | None = None
    llm_voice_model: str | None = None
    llm_sources_enabled: bool | None = None
    debug_enabled: bool | None = None
    debug_info_enabled: bool | None = None
    knowledge_image_caption_enabled: bool | None = None
    bitrix_enabled: bool | None = None
    bitrix_webhook_url: str | None = None
    telegram_token: str | None = None
    telegram_auto_start: bool | None = None
    max_token: str | None = None
    max_auto_start: bool | None = None
    vk_token: str | None = None
    vk_auto_start: bool | None = None
    widget_url: str | None = None
    mail_enabled: bool | None = None
    mail_imap_host: str | None = None
    mail_imap_port: int | None = None
    mail_imap_ssl: bool | None = None
    mail_smtp_host: str | None = None
    mail_smtp_port: int | None = None
    mail_smtp_tls: bool | None = None
    mail_username: str | None = None
    mail_password: str | None = None
    mail_from: str | None = None
    mail_signature: str | None = None


# Bot configuration models
class TelegramConfig(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class TelegramAction(BaseModel):
    token: str | None = None


class ProjectTelegramConfig(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class ProjectTelegramAction(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class MaxConfig(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class MaxAction(BaseModel):
    token: str | None = None


class ProjectMaxConfig(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class ProjectMaxAction(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class VkConfig(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class VkAction(BaseModel):
    token: str | None = None


class ProjectVkConfig(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class ProjectVkAction(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


# Helper functions
def _build_token_preview(token: str | None) -> str | None:
    """Build a preview of a token showing first 4 and last 2 characters."""
    if not token:
        return None
    token = token.strip()
    if not token:
        return None
    return f"{token[:4]}…{token[-2:]}" if len(token) > 6 else "***"


def _project_telegram_payload(
    project: "Project",
    controller: "TelegramHub | None" = None,
) -> dict[str, Any]:
    """Build Telegram bot status payload for a project."""
    token_value = (
        project.telegram_token.strip() or None
        if isinstance(project.telegram_token, str)
        else None
    )
    running = controller.is_project_running(project.name) if controller else False
    last_error = controller.get_last_error(project.name) if controller else None
    return {
        "project": project.name,
        "running": running,
        "token_set": bool(token_value),
        "token_preview": _build_token_preview(token_value),
        "auto_start": bool(project.telegram_auto_start) if project.telegram_auto_start is not None else False,
        "last_error": last_error,
    }


def _project_max_payload(
    project: "Project",
    controller: "MaxHub | None" = None,
) -> dict[str, Any]:
    """Build MAX bot status payload for a project."""
    token_value = (
        project.max_token.strip() or None
        if isinstance(project.max_token, str)
        else None
    )
    running = controller.is_project_running(project.name) if controller else False
    last_error = controller.get_last_error(project.name) if controller else None
    return {
        "project": project.name,
        "running": running,
        "token_set": bool(token_value),
        "token_preview": _build_token_preview(token_value),
        "auto_start": bool(project.max_auto_start) if project.max_auto_start is not None else False,
        "last_error": last_error,
    }


def _project_vk_payload(
    project: "Project",
    controller: "VkHub | None" = None,
) -> dict[str, Any]:
    """Build VK bot status payload for a project."""
    token_value = (
        project.vk_token.strip() or None
        if isinstance(project.vk_token, str)
        else None
    )
    running = controller.is_project_running(project.name) if controller else False
    last_error = controller.get_last_error(project.name) if controller else None
    return {
        "project": project.name,
        "running": running,
        "token_set": bool(token_value),
        "token_preview": _build_token_preview(token_value),
        "auto_start": bool(project.vk_auto_start) if project.vk_auto_start is not None else False,
        "last_error": last_error,
    }


@router.get("/projects", response_class=ORJSONResponse)
async def admin_projects(request: Request) -> ORJSONResponse:
    """Return configured projects."""
    # Import here to avoid circular dependency
    from app import _require_admin, _get_mongo_client, _project_response
    
    identity = _require_admin(request)
    mongo_client = _get_mongo_client(request)
    projects = await mongo_client.list_projects()
    if not identity.is_super:
        allowed = {proj.strip().lower() for proj in identity.projects if proj}
        projects = [project for project in projects if project.name in allowed]
    serialized = [_project_response(project) for project in projects]
    return ORJSONResponse({"projects": serialized})


@router.get("/projects/names", response_class=ORJSONResponse)
async def admin_project_names(request: Request, limit: int = 100) -> ORJSONResponse:
    """Return a list of known project identifiers."""
    # Import here to avoid circular dependency
    from app import _require_admin, _get_mongo_client, _normalize_project
    from settings import MongoSettings
    
    identity = require_admin(request)
    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)
    mongo_client = _get_mongo_client(request)
    names = await mongo_client.list_project_names(collection, limit=limit)
    if not identity.is_super:
        allowed = {proj.strip().lower() for proj in identity.projects if proj}
        names = [name for name in names if name in allowed]
        default_name = identity.primary_project
    else:
        default_name = _normalize_project(None)
    if default_name and default_name not in names:
        names.insert(0, default_name)
    return ORJSONResponse({"projects": names})


@router.get("/projects/storage", response_class=ORJSONResponse)
async def admin_projects_storage(request: Request) -> ORJSONResponse:
    """Return aggregated storage usage per project (Mongo/GridFS/Redis)."""
    # Import here to avoid circular dependency
    from app import _require_admin, _get_mongo_client, _redis_project_usage
    from settings import MongoSettings
    
    identity = require_admin(request)
    mongo_cfg = MongoSettings()
    documents_collection = getattr(request.state, "documents_collection", mongo_cfg.documents)
    contexts_collection = getattr(request.state, "contexts_collection", mongo_cfg.contexts)

    mongo_client = _get_mongo_client(request)
    storage = await mongo_client.aggregate_project_storage(documents_collection, contexts_collection)
    redis_usage = await _redis_project_usage()

    if not identity.is_super:
        allowed = {proj.strip().lower() for proj in identity.projects if proj}
        storage = {key: value for key, value in storage.items() if key in allowed}
        redis_usage = {key: value for key, value in redis_usage.items() if key in allowed}
    else:
        allowed = None

    combined_keys = set(storage.keys()) | set(redis_usage.keys())
    if allowed is not None:
        combined_keys = {key for key in combined_keys if key in allowed}
    combined: dict[str, dict[str, float | int]] = {}
    for key in combined_keys:
        doc_stats = storage.get(key, {})
        redis_stats = redis_usage.get(key, {})
        documents_bytes = int(doc_stats.get("documents_bytes", 0) or 0)
        binary_bytes = int(doc_stats.get("binary_bytes", 0) or 0)
        text_bytes = max(documents_bytes - binary_bytes, 0)
        combined[key] = {
            "documents_bytes": documents_bytes,
            "binary_bytes": binary_bytes,
            "text_bytes": text_bytes,
            "document_count": int(doc_stats.get("document_count", 0)),
            "context_bytes": int(doc_stats.get("context_bytes", 0) or 0),
            "context_count": int(doc_stats.get("context_count", 0)),
            "redis_bytes": float(redis_stats.get("redis_bytes", 0)),
            "redis_keys": int(redis_stats.get("redis_keys", 0)),
        }

    return ORJSONResponse({"projects": combined})


@router.get("/projects/{project}/test", response_class=ORJSONResponse)
async def admin_test_project(project: str, request: Request) -> ORJSONResponse:
    """Test project connectivity and configuration."""
    # Import here to avoid circular dependency
    from app import _resolve_admin_project, _get_mongo_client, _mongo_check, _redis_check, _qdrant_check
    
    project_name = _resolve_admin_project(request, project, required=True)

    mongo_ok, mongo_err = _mongo_check()
    redis_ok, redis_err = _redis_check()
    qdrant_ok, qdrant_err = _qdrant_check()

    mongo_client = _get_mongo_client(request)
    project_obj = await mongo_client.get_project(project_name)

    return ORJSONResponse({
        "name": project_name,
        "mongo": {"ok": mongo_ok, "error": mongo_err},
        "redis": {"ok": redis_ok, "error": redis_err},
        "qdrant": {"ok": qdrant_ok, "error": qdrant_err},
    })


@router.post("/projects", response_class=ORJSONResponse, status_code=201)
async def admin_create_project(request: Request, payload: ProjectCreate) -> ORJSONResponse:
    """Create or update a project (domain)."""
    # Import here to avoid circular dependency
    # The full implementation is still in app.py (very large function ~300 LOC)
    # TODO: Move full implementation to this router in future iteration
    from app import admin_create_project as _create_project_impl
    return await _create_project_impl(request, payload)


@router.delete("/projects/{domain}", response_class=ORJSONResponse)
async def admin_delete_project(domain: str, request: Request) -> ORJSONResponse:
    """Delete a project and all its data."""
    # Import here to avoid circular dependency
    from app import _require_admin, _get_mongo_client, _normalize_project, _purge_vector_entries
    from settings import MongoSettings
    from tg_bot.bot import TelegramHub
    from max_bot.config import MaxHub
    from vk_bot.config import VkHub
    
    identity = _require_admin(request)
    domain_value = _normalize_project(domain)
    if not domain_value:
        raise HTTPException(status_code=400, detail="name is required")
    if not identity.is_super:
        allowed = {proj.strip().lower() for proj in identity.projects if proj}
        if domain_value not in allowed:
            raise HTTPException(status_code=403, detail="Access to project is forbidden")
    mongo_client = _get_mongo_client(request)
    mongo_cfg = MongoSettings()
    documents_collection = getattr(request.state, "documents_collection", mongo_cfg.documents)
    contexts_collection = getattr(request.state, "contexts_collection", mongo_cfg.contexts)
    summary = await mongo_client.delete_project(
        domain_value,
        documents_collection=documents_collection,
        contexts_collection=contexts_collection,
        stats_collection=mongo_client.stats_collection,
    )
    file_ids = summary.pop("file_ids", [])
    await _purge_vector_entries(file_ids)
    hub: TelegramHub | None = getattr(request.app.state, "telegram", None)
    if isinstance(hub, TelegramHub):
        await hub.stop_project(domain_value, forget_sessions=True)
    max_hub: MaxHub | None = getattr(request.app.state, "max", None)
    if isinstance(max_hub, MaxHub):
        await max_hub.stop_project(domain_value, forget_sessions=True)
    vk_hub: VkHub | None = getattr(request.app.state, "vk", None)
    if isinstance(vk_hub, VkHub):
        await vk_hub.stop_project(domain_value, forget_sessions=True)
    return ORJSONResponse({"status": "deleted", "project": domain_value, "removed": summary})


# Telegram bot endpoints (default project)
@router.get("/telegram", response_class=ORJSONResponse)
async def telegram_status(request: Request) -> ORJSONResponse:
    """Get Telegram bot status for default project."""
    require_super_admin(request)
    from app import _normalize_project
    from models import Project
    from tg_bot.bot import TelegramHub
    
    hub: TelegramHub = request.app.state.telegram
    default_project = _normalize_project(None)
    project: Project | None = None
    if default_project:
        project = await request.state.mongo.get_project(default_project)
    token = (
        project.telegram_token if project and isinstance(project.telegram_token, str) else None
    )
    preview = _build_token_preview(token)
    auto_start = bool(project.telegram_auto_start) if project else False
    running = hub.is_project_running(default_project)
    last_error = hub.get_last_error(default_project) if default_project else None
    return ORJSONResponse(
        {
            "running": running,
            "token_set": bool(token),
            "token_preview": preview,
            "auto_start": auto_start,
            "project": default_project,
            "last_error": last_error,
        }
    )


@router.post("/telegram/config", response_class=ORJSONResponse)
async def telegram_config(request: Request, payload: TelegramConfig) -> ORJSONResponse:
    """Configure Telegram bot for default project."""
    require_super_admin(request)
    from app import _normalize_project
    from models import Project
    from tg_bot.bot import TelegramHub
    
    hub: TelegramHub = request.app.state.telegram
    default_project = _normalize_project(None)
    if not default_project:
        raise HTTPException(status_code=400, detail="Default project is not configured")

    existing = await request.state.mongo.get_project(default_project)
    data = existing.model_dump() if existing else {"name": default_project}
    if payload.token is not None:
        value = payload.token.strip()
        data["telegram_token"] = value or None
    if payload.auto_start is not None:
        data["telegram_auto_start"] = bool(payload.auto_start)

    project = Project(**data)
    saved = await request.state.mongo.upsert_project(project)
    await hub.ensure_runner(saved)
    return ORJSONResponse({"ok": True})


@router.post("/telegram/start", response_class=ORJSONResponse)
async def telegram_start(request: Request, payload: TelegramAction) -> ORJSONResponse:
    """Start Telegram bot for default project."""
    require_super_admin(request)
    from app import _normalize_project
    from models import Project
    from tg_bot.bot import TelegramHub
    
    hub: TelegramHub = request.app.state.telegram
    default_project = _normalize_project(None)
    if not default_project:
        raise HTTPException(status_code=400, detail="Default project is not configured")

    existing = await request.state.mongo.get_project(default_project)
    data = existing.model_dump() if existing else {"name": default_project}
    token_value = payload.token.strip() if isinstance(payload.token, str) else None
    if token_value:
        data["telegram_token"] = token_value
    project = Project(**data)
    saved = await request.state.mongo.upsert_project(project)
    await hub.start_project(saved)
    return ORJSONResponse({"running": True})


@router.post("/telegram/stop", response_class=ORJSONResponse)
async def telegram_stop(request: Request) -> ORJSONResponse:
    """Stop Telegram bot for default project."""
    require_super_admin(request)
    from app import _normalize_project
    from tg_bot.bot import TelegramHub
    
    hub: TelegramHub = request.app.state.telegram
    default_project = _normalize_project(None)
    if not default_project:
        raise HTTPException(status_code=400, detail="Default project is not configured")
    await hub.stop_project(default_project)
    return ORJSONResponse({"running": False})


# MAX bot endpoints (default project)
@router.get("/max", response_class=ORJSONResponse)
async def max_status(request: Request) -> ORJSONResponse:
    """Get MAX bot status for default project."""
    require_super_admin(request)
    from app import _normalize_project, _get_mongo_client
    from models import Project
    from max_bot.config import MaxHub
    
    hub: MaxHub = request.app.state.max
    mongo_client = _get_mongo_client(request)
    default_project = _normalize_project(None)
    project: Project | None = None
    if default_project:
        project = await mongo_client.get_project(default_project)
    token_value = (
        project.max_token.strip() if project and isinstance(project.max_token, str) else None
    )
    response = {
        "project": default_project,
        "running": hub.is_project_running(default_project),
        "token_set": bool(token_value),
        "token_preview": _build_token_preview(token_value),
        "auto_start": bool(project.max_auto_start) if project and project.max_auto_start is not None else False,
        "last_error": hub.get_last_error(default_project) if default_project else None,
    }
    return ORJSONResponse(response)


@router.post("/max/config", response_class=ORJSONResponse)
async def max_config(request: Request, payload: MaxConfig) -> ORJSONResponse:
    """Configure MAX bot for default project."""
    require_super_admin(request)
    from app import _normalize_project, _get_mongo_client
    from models import Project
    from max_bot.config import MaxHub
    
    hub: MaxHub = request.app.state.max
    mongo_client = _get_mongo_client(request)
    default_project = _normalize_project(None)
    if not default_project:
        raise HTTPException(status_code=400, detail="Default project is not configured")

    existing = await mongo_client.get_project(default_project)
    data = existing.model_dump() if existing else {"name": default_project}
    if payload.token is not None:
        value = payload.token.strip()
        data["max_token"] = value or None
    if payload.auto_start is not None:
        data["max_auto_start"] = bool(payload.auto_start)

    project = Project(**data)
    saved = await mongo_client.upsert_project(project)
    await hub.ensure_runner(saved)
    return ORJSONResponse({"ok": True})


@router.post("/max/start", response_class=ORJSONResponse)
async def max_start(request: Request, payload: MaxAction) -> ORJSONResponse:
    """Start MAX bot for default project."""
    require_super_admin(request)
    from app import _normalize_project, _get_mongo_client
    from models import Project
    from max_bot.config import MaxHub
    
    hub: MaxHub = request.app.state.max
    mongo_client = _get_mongo_client(request)
    default_project = _normalize_project(None)
    if not default_project:
        raise HTTPException(status_code=400, detail="Default project is not configured")

    existing = await mongo_client.get_project(default_project)
    data = existing.model_dump() if existing else {"name": default_project}
    token_value = payload.token.strip() if isinstance(payload.token, str) else None
    if token_value:
        data["max_token"] = token_value
    project = Project(**data)
    saved = await mongo_client.upsert_project(project)
    await hub.start_project(saved)
    return ORJSONResponse({"running": True})


@router.post("/max/stop", response_class=ORJSONResponse)
async def max_stop(request: Request) -> ORJSONResponse:
    """Stop MAX bot for default project."""
    require_super_admin(request)
    from app import _normalize_project
    from max_bot.config import MaxHub
    
    hub: MaxHub = request.app.state.max
    default_project = _normalize_project(None)
    if not default_project:
        raise HTTPException(status_code=400, detail="Default project is not configured")
    await hub.stop_project(default_project)
    return ORJSONResponse({"running": False})


# VK bot endpoints (default project)
@router.get("/vk", response_class=ORJSONResponse)
async def vk_status(request: Request) -> ORJSONResponse:
    """Get VK bot status for default project."""
    require_super_admin(request)
    from app import _normalize_project, _get_mongo_client
    from models import Project
    from vk_bot.config import VkHub
    
    hub: VkHub = request.app.state.vk
    mongo_client = _get_mongo_client(request)
    default_project = _normalize_project(None)
    project: Project | None = None
    if default_project:
        project = await mongo_client.get_project(default_project)
    token_value = (
        project.vk_token.strip() if project and isinstance(project.vk_token, str) else None
    )
    response = {
        "project": default_project,
        "running": hub.is_project_running(default_project),
        "token_set": bool(token_value),
        "token_preview": _build_token_preview(token_value),
        "auto_start": bool(project.vk_auto_start) if project and project.vk_auto_start is not None else False,
        "last_error": hub.get_last_error(default_project) if default_project else None,
    }
    return ORJSONResponse(response)


@router.post("/vk/config", response_class=ORJSONResponse)
async def vk_config(request: Request, payload: VkConfig) -> ORJSONResponse:
    """Configure VK bot for default project."""
    require_super_admin(request)
    from app import _normalize_project, _get_mongo_client
    from models import Project
    from vk_bot.config import VkHub
    
    hub: VkHub = request.app.state.vk
    mongo_client = _get_mongo_client(request)
    default_project = _normalize_project(None)
    if not default_project:
        raise HTTPException(status_code=400, detail="Default project is not configured")

    existing = await mongo_client.get_project(default_project)
    data = existing.model_dump() if existing else {"name": default_project}
    if payload.token is not None:
        value = payload.token.strip()
        data["vk_token"] = value or None
    if payload.auto_start is not None:
        data["vk_auto_start"] = bool(payload.auto_start)

    project = Project(**data)
    saved = await mongo_client.upsert_project(project)
    await hub.ensure_runner(saved)
    return ORJSONResponse({"ok": True})


@router.post("/vk/start", response_class=ORJSONResponse)
async def vk_start(request: Request, payload: VkAction) -> ORJSONResponse:
    """Start VK bot for default project."""
    require_super_admin(request)
    from app import _normalize_project, _get_mongo_client
    from models import Project
    from vk_bot.config import VkHub
    
    hub: VkHub = request.app.state.vk
    mongo_client = _get_mongo_client(request)
    default_project = _normalize_project(None)
    if not default_project:
        raise HTTPException(status_code=400, detail="Default project is not configured")

    existing = await mongo_client.get_project(default_project)
    data = existing.model_dump() if existing else {"name": default_project}
    token_value = payload.token.strip() if isinstance(payload.token, str) else None
    if token_value:
        data["vk_token"] = token_value
    project = Project(**data)
    saved = await mongo_client.upsert_project(project)
    await hub.start_project(saved)
    return ORJSONResponse({"running": True})


@router.post("/vk/stop", response_class=ORJSONResponse)
async def vk_stop(request: Request) -> ORJSONResponse:
    """Stop VK bot for default project."""
    require_super_admin(request)
    from app import _normalize_project
    from vk_bot.config import VkHub
    
    hub: VkHub = request.app.state.vk
    default_project = _normalize_project(None)
    if not default_project:
        raise HTTPException(status_code=400, detail="Default project is not configured")
    await hub.stop_project(default_project)
    return ORJSONResponse({"running": False})


# Project-specific bot endpoints
@router.get("/projects/{project}/telegram", response_class=ORJSONResponse)
async def admin_project_telegram_status(project: str, request: Request) -> ORJSONResponse:
    """Get Telegram bot status for a specific project."""
    from app import _resolve_admin_project, _get_mongo_client
    from models import Project
    from tg_bot.bot import TelegramHub
    
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        raise HTTPException(status_code=404, detail="project not found")

    hub: TelegramHub = request.app.state.telegram
    payload = _project_telegram_payload(existing, hub)
    return ORJSONResponse(payload)


@router.post("/projects/{project}/telegram/config", response_class=ORJSONResponse)
async def admin_project_telegram_config(
    project: str,
    request: Request,
    payload: ProjectTelegramConfig,
) -> ORJSONResponse:
    """Configure Telegram bot for a specific project."""
    from app import _resolve_admin_project, _get_mongo_client
    from models import Project
    from tg_bot.bot import TelegramHub
    from max_bot.config import MaxHub
    from vk_bot.config import VkHub
    
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        existing = Project(name=project_name)

    provided_fields = getattr(payload, "model_fields_set", set())

    if "token" in provided_fields:
        if isinstance(payload.token, str):
            token_value = payload.token.strip() or None
        else:
            token_value = None
    else:
        token_value = existing.telegram_token

    if "auto_start" in provided_fields:
        auto_start_value = (
            bool(payload.auto_start)
            if payload.auto_start is not None
            else None
        )
    else:
        auto_start_value = existing.telegram_auto_start

    project_payload = Project(
        name=project_name,
        title=existing.title,
        domain=existing.domain,
        admin_username=existing.admin_username,
        admin_password_hash=existing.admin_password_hash,
        llm_model=existing.llm_model,
        llm_prompt=existing.llm_prompt,
        llm_emotions_enabled=existing.llm_emotions_enabled if existing.llm_emotions_enabled is not None else True,
        telegram_token=token_value,
        telegram_auto_start=auto_start_value,
        max_token=existing.max_token,
        max_auto_start=existing.max_auto_start,
        vk_token=existing.vk_token,
        vk_auto_start=existing.vk_auto_start,
        widget_url=existing.widget_url,
        debug_enabled=existing.debug_enabled,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: TelegramHub = request.app.state.telegram
    await hub.ensure_runner(saved)
    response = _project_telegram_payload(saved, hub)
    max_hub: MaxHub | None = getattr(request.app.state, "max", None)
    if isinstance(max_hub, MaxHub):
        await max_hub.ensure_runner(saved)
    vk_hub: VkHub | None = getattr(request.app.state, "vk", None)
    if isinstance(vk_hub, VkHub):
        await vk_hub.ensure_runner(saved)
    return ORJSONResponse(response)


@router.post("/projects/{project}/telegram/start", response_class=ORJSONResponse)
async def admin_project_telegram_start(
    project: str,
    request: Request,
    payload: ProjectTelegramAction,
) -> ORJSONResponse:
    """Start Telegram bot for a specific project."""
    from app import _resolve_admin_project, _get_mongo_client
    from models import Project
    from tg_bot.bot import TelegramHub
    from max_bot.config import MaxHub
    from vk_bot.config import VkHub
    
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        raise HTTPException(status_code=404, detail="project not found")

    provided_fields = getattr(payload, "model_fields_set", set())

    if "token" in provided_fields:
        if isinstance(payload.token, str):
            token_value = payload.token.strip() or None
        else:
            token_value = None
    else:
        token_value = (
            existing.telegram_token.strip() or None
            if isinstance(existing.telegram_token, str)
            else None
        )

    if not token_value:
        raise HTTPException(status_code=400, detail="Telegram token is not configured")

    if "auto_start" in provided_fields:
        auto_start_value = (
            bool(payload.auto_start)
            if payload.auto_start is not None
            else None
        )
    else:
        auto_start_value = existing.telegram_auto_start

    project_payload = Project(
        name=existing.name,
        title=existing.title,
        domain=existing.domain,
        admin_username=existing.admin_username,
        admin_password_hash=existing.admin_password_hash,
        llm_model=existing.llm_model,
        llm_prompt=existing.llm_prompt,
        llm_emotions_enabled=existing.llm_emotions_enabled if existing.llm_emotions_enabled is not None else True,
        telegram_token=token_value,
        telegram_auto_start=auto_start_value,
        max_token=existing.max_token,
        max_auto_start=existing.max_auto_start,
        vk_token=existing.vk_token,
        vk_auto_start=existing.vk_auto_start,
        widget_url=existing.widget_url,
        debug_enabled=existing.debug_enabled,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: TelegramHub = request.app.state.telegram
    await hub.start_project(saved, auto_start=auto_start_value if "auto_start" in provided_fields else None)
    response = _project_telegram_payload(saved, hub)
    max_hub: MaxHub | None = getattr(request.app.state, "max", None)
    if isinstance(max_hub, MaxHub):
        await max_hub.ensure_runner(saved)
    vk_hub: VkHub | None = getattr(request.app.state, "vk", None)
    if isinstance(vk_hub, VkHub):
        await vk_hub.ensure_runner(saved)
    return ORJSONResponse(response)


@router.post("/projects/{project}/telegram/stop", response_class=ORJSONResponse)
async def admin_project_telegram_stop(
    project: str,
    request: Request,
    payload: ProjectTelegramAction | None = None,
) -> ORJSONResponse:
    """Stop Telegram bot for a specific project."""
    from app import _resolve_admin_project, _get_mongo_client
    from models import Project
    from tg_bot.bot import TelegramHub
    from max_bot.config import MaxHub
    from vk_bot.config import VkHub
    
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        raise HTTPException(status_code=404, detail="project not found")

    provided_fields = getattr(payload, "model_fields_set", set()) if payload else set()
    if payload and "auto_start" in provided_fields:
        auto_start_value = (
            bool(payload.auto_start)
            if payload.auto_start is not None
            else None
        )
    else:
        auto_start_value = existing.telegram_auto_start

    project_payload = Project(
        name=existing.name,
        title=existing.title,
        domain=existing.domain,
        llm_model=existing.llm_model,
        llm_prompt=existing.llm_prompt,
        llm_emotions_enabled=existing.llm_emotions_enabled if existing.llm_emotions_enabled is not None else True,
        telegram_token=existing.telegram_token,
        telegram_auto_start=auto_start_value,
        widget_url=existing.widget_url,
        admin_username=existing.admin_username,
        admin_password_hash=existing.admin_password_hash,
        max_token=existing.max_token,
        max_auto_start=existing.max_auto_start,
        vk_token=existing.vk_token,
        vk_auto_start=existing.vk_auto_start,
        debug_enabled=existing.debug_enabled,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: TelegramHub = request.app.state.telegram
    await hub.stop_project(saved.name, auto_start=auto_start_value if payload and "auto_start" in provided_fields else None)
    response = _project_telegram_payload(saved, hub)
    max_hub: MaxHub | None = getattr(request.app.state, "max", None)
    if isinstance(max_hub, MaxHub):
        await max_hub.ensure_runner(saved)
    vk_hub: VkHub | None = getattr(request.app.state, "vk", None)
    if isinstance(vk_hub, VkHub):
        await vk_hub.ensure_runner(saved)
    return ORJSONResponse(response)


@router.get("/projects/{project}/max", response_class=ORJSONResponse)
async def admin_project_max_status(project: str, request: Request) -> ORJSONResponse:
    """Get MAX bot status for a specific project."""
    from app import _resolve_admin_project, _get_mongo_client
    from models import Project
    from max_bot.config import MaxHub
    
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        raise HTTPException(status_code=404, detail="project not found")

    hub: MaxHub = request.app.state.max
    payload = _project_max_payload(existing, hub)
    return ORJSONResponse(payload)


@router.post("/projects/{project}/max/config", response_class=ORJSONResponse)
async def admin_project_max_config(
    project: str,
    request: Request,
    payload: ProjectMaxConfig,
) -> ORJSONResponse:
    """Configure MAX bot for a specific project."""
    from app import _resolve_admin_project, _get_mongo_client
    from models import Project
    from max_bot.config import MaxHub
    from tg_bot.bot import TelegramHub
    from vk_bot.config import VkHub
    
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        existing = Project(name=project_name)

    provided_fields = getattr(payload, "model_fields_set", set())

    if "token" in provided_fields:
        if isinstance(payload.token, str):
            token_value = payload.token.strip() or None
        else:
            token_value = None
    else:
        token_value = existing.max_token

    if "auto_start" in provided_fields:
        auto_start_value = (
            bool(payload.auto_start)
            if payload.auto_start is not None
            else None
        )
    else:
        auto_start_value = existing.max_auto_start

    project_payload = Project(
        name=project_name,
        title=existing.title,
        domain=existing.domain,
        admin_username=existing.admin_username,
        admin_password_hash=existing.admin_password_hash,
        llm_model=existing.llm_model,
        llm_prompt=existing.llm_prompt,
        llm_emotions_enabled=existing.llm_emotions_enabled if existing.llm_emotions_enabled is not None else True,
        telegram_token=existing.telegram_token,
        telegram_auto_start=existing.telegram_auto_start,
        max_token=token_value,
        max_auto_start=auto_start_value,
        vk_token=existing.vk_token,
        vk_auto_start=existing.vk_auto_start,
        widget_url=existing.widget_url,
        debug_enabled=existing.debug_enabled,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: MaxHub = request.app.state.max
    await hub.ensure_runner(saved)
    response = _project_max_payload(saved, hub)
    telegram_hub: TelegramHub | None = getattr(request.app.state, "telegram", None)
    if isinstance(telegram_hub, TelegramHub):
        await telegram_hub.ensure_runner(saved)
    vk_hub: VkHub | None = getattr(request.app.state, "vk", None)
    if isinstance(vk_hub, VkHub):
        await vk_hub.ensure_runner(saved)
    return ORJSONResponse(response)


@router.post("/projects/{project}/max/start", response_class=ORJSONResponse)
async def admin_project_max_start(
    project: str,
    request: Request,
    payload: ProjectMaxAction,
) -> ORJSONResponse:
    """Start MAX bot for a specific project."""
    from app import _resolve_admin_project, _get_mongo_client
    from models import Project
    from max_bot.config import MaxHub
    from tg_bot.bot import TelegramHub
    from vk_bot.config import VkHub
    
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        raise HTTPException(status_code=404, detail="project not found")

    provided_fields = getattr(payload, "model_fields_set", set())

    if "token" in provided_fields:
        if isinstance(payload.token, str):
            token_value = payload.token.strip() or None
        else:
            token_value = None
    else:
        token_value = (
            existing.max_token.strip() or None
            if isinstance(existing.max_token, str)
            else None
        )

    if not token_value:
        raise HTTPException(status_code=400, detail="MAX token is not configured")

    if "auto_start" in provided_fields:
        auto_start_value = (
            bool(payload.auto_start)
            if payload.auto_start is not None
            else None
        )
    else:
        auto_start_value = existing.max_auto_start

    project_payload = Project(
        name=existing.name,
        title=existing.title,
        domain=existing.domain,
        admin_username=existing.admin_username,
        admin_password_hash=existing.admin_password_hash,
        llm_model=existing.llm_model,
        llm_prompt=existing.llm_prompt,
        llm_emotions_enabled=existing.llm_emotions_enabled if existing.llm_emotions_enabled is not None else True,
        telegram_token=existing.telegram_token,
        telegram_auto_start=existing.telegram_auto_start,
        max_token=token_value,
        max_auto_start=auto_start_value,
        vk_token=existing.vk_token,
        vk_auto_start=existing.vk_auto_start,
        widget_url=existing.widget_url,
        debug_enabled=existing.debug_enabled,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: MaxHub = request.app.state.max
    await hub.start_project(saved, auto_start=auto_start_value if "auto_start" in provided_fields else None)
    response = _project_max_payload(saved, hub)
    telegram_hub: TelegramHub | None = getattr(request.app.state, "telegram", None)
    if isinstance(telegram_hub, TelegramHub):
        await telegram_hub.ensure_runner(saved)
    vk_hub: VkHub | None = getattr(request.app.state, "vk", None)
    if isinstance(vk_hub, VkHub):
        await vk_hub.ensure_runner(saved)
    return ORJSONResponse(response)


@router.post("/projects/{project}/max/stop", response_class=ORJSONResponse)
async def admin_project_max_stop(
    project: str,
    request: Request,
    payload: ProjectMaxAction | None = None,
) -> ORJSONResponse:
    """Stop MAX bot for a specific project."""
    from app import _resolve_admin_project, _get_mongo_client
    from models import Project
    from max_bot.config import MaxHub
    from tg_bot.bot import TelegramHub
    from vk_bot.config import VkHub
    
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        raise HTTPException(status_code=404, detail="project not found")

    provided_fields = getattr(payload, "model_fields_set", set()) if payload else set()
    if payload and "auto_start" in provided_fields:
        auto_start_value = (
            bool(payload.auto_start)
            if payload.auto_start is not None
            else None
        )
    else:
        auto_start_value = existing.max_auto_start

    project_payload = Project(
        name=existing.name,
        title=existing.title,
        domain=existing.domain,
        llm_model=existing.llm_model,
        llm_prompt=existing.llm_prompt,
        llm_emotions_enabled=existing.llm_emotions_enabled if existing.llm_emotions_enabled is not None else True,
        telegram_token=existing.telegram_token,
        telegram_auto_start=existing.telegram_auto_start,
        max_token=existing.max_token,
        max_auto_start=auto_start_value,
        vk_token=existing.vk_token,
        vk_auto_start=existing.vk_auto_start,
        widget_url=existing.widget_url,
        admin_username=existing.admin_username,
        admin_password_hash=existing.admin_password_hash,
        debug_enabled=existing.debug_enabled,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: MaxHub = request.app.state.max
    await hub.stop_project(saved.name, auto_start=auto_start_value if payload and "auto_start" in provided_fields else None)
    response = _project_max_payload(saved, hub)
    telegram_hub: TelegramHub | None = getattr(request.app.state, "telegram", None)
    if isinstance(telegram_hub, TelegramHub):
        await telegram_hub.ensure_runner(saved)
    vk_hub: VkHub | None = getattr(request.app.state, "vk", None)
    if isinstance(vk_hub, VkHub):
        await vk_hub.ensure_runner(saved)
    return ORJSONResponse(response)


@router.get("/projects/{project}/vk", response_class=ORJSONResponse)
async def admin_project_vk_status(project: str, request: Request) -> ORJSONResponse:
    """Get VK bot status for a specific project."""
    from app import _resolve_admin_project, _get_mongo_client
    from models import Project
    from vk_bot.config import VkHub
    
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        raise HTTPException(status_code=404, detail="project not found")

    hub: VkHub = request.app.state.vk
    payload = _project_vk_payload(existing, hub)
    return ORJSONResponse(payload)


@router.post("/projects/{project}/vk/config", response_class=ORJSONResponse)
async def admin_project_vk_config(
    project: str,
    request: Request,
    payload: ProjectVkConfig,
) -> ORJSONResponse:
    """Configure VK bot for a specific project."""
    from app import _resolve_admin_project, _get_mongo_client
    from models import Project
    from vk_bot.config import VkHub
    from tg_bot.bot import TelegramHub
    from max_bot.config import MaxHub
    
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        existing = Project(name=project_name)

    provided_fields = getattr(payload, "model_fields_set", set())

    if "token" in provided_fields:
        if isinstance(payload.token, str):
            token_value = payload.token.strip() or None
        else:
            token_value = None
    else:
        token_value = existing.vk_token

    if "auto_start" in provided_fields:
        auto_start_value = (
            bool(payload.auto_start)
            if payload.auto_start is not None
            else None
        )
    else:
        auto_start_value = existing.vk_auto_start

    project_payload = Project(
        name=project_name,
        title=existing.title,
        domain=existing.domain,
        admin_username=existing.admin_username,
        admin_password_hash=existing.admin_password_hash,
        llm_model=existing.llm_model,
        llm_prompt=existing.llm_prompt,
        llm_emotions_enabled=existing.llm_emotions_enabled if existing.llm_emotions_enabled is not None else True,
        telegram_token=existing.telegram_token,
        telegram_auto_start=existing.telegram_auto_start,
        max_token=existing.max_token,
        max_auto_start=existing.max_auto_start,
        vk_token=token_value,
        vk_auto_start=auto_start_value,
        widget_url=existing.widget_url,
        debug_enabled=existing.debug_enabled,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: VkHub = request.app.state.vk
    await hub.ensure_runner(saved)
    response = _project_vk_payload(saved, hub)
    telegram_hub: TelegramHub | None = getattr(request.app.state, "telegram", None)
    if isinstance(telegram_hub, TelegramHub):
        await telegram_hub.ensure_runner(saved)
    max_hub: MaxHub | None = getattr(request.app.state, "max", None)
    if isinstance(max_hub, MaxHub):
        await max_hub.ensure_runner(saved)
    return ORJSONResponse(response)


@router.post("/projects/{project}/vk/start", response_class=ORJSONResponse)
async def admin_project_vk_start(
    project: str,
    request: Request,
    payload: ProjectVkAction,
) -> ORJSONResponse:
    """Start VK bot for a specific project."""
    from app import _resolve_admin_project, _get_mongo_client
    from models import Project
    from vk_bot.config import VkHub
    from tg_bot.bot import TelegramHub
    from max_bot.config import MaxHub
    
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        raise HTTPException(status_code=404, detail="project not found")

    provided_fields = getattr(payload, "model_fields_set", set())

    if "token" in provided_fields:
        if isinstance(payload.token, str):
            token_value = payload.token.strip() or None
        else:
            token_value = None
    else:
        token_value = (
            existing.vk_token.strip() or None
            if isinstance(existing.vk_token, str)
            else None
        )

    if not token_value:
        raise HTTPException(status_code=400, detail="VK token is not configured")

    if "auto_start" in provided_fields:
        auto_start_value = (
            bool(payload.auto_start)
            if payload.auto_start is not None
            else None
        )
    else:
        auto_start_value = existing.vk_auto_start

    project_payload = Project(
        name=existing.name,
        title=existing.title,
        domain=existing.domain,
        admin_username=existing.admin_username,
        admin_password_hash=existing.admin_password_hash,
        llm_model=existing.llm_model,
        llm_prompt=existing.llm_prompt,
        llm_emotions_enabled=existing.llm_emotions_enabled if existing.llm_emotions_enabled is not None else True,
        telegram_token=existing.telegram_token,
        telegram_auto_start=existing.telegram_auto_start,
        max_token=existing.max_token,
        max_auto_start=existing.max_auto_start,
        vk_token=token_value,
        vk_auto_start=auto_start_value,
        widget_url=existing.widget_url,
        debug_enabled=existing.debug_enabled,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: VkHub = request.app.state.vk
    await hub.start_project(saved, auto_start=auto_start_value if "auto_start" in provided_fields else None)
    response = _project_vk_payload(saved, hub)
    telegram_hub: TelegramHub | None = getattr(request.app.state, "telegram", None)
    if isinstance(telegram_hub, TelegramHub):
        await telegram_hub.ensure_runner(saved)
    max_hub: MaxHub | None = getattr(request.app.state, "max", None)
    if isinstance(max_hub, MaxHub):
        await max_hub.ensure_runner(saved)
    return ORJSONResponse(response)


@router.post("/projects/{project}/vk/stop", response_class=ORJSONResponse)
async def admin_project_vk_stop(
    project: str,
    request: Request,
    payload: ProjectVkAction | None = None,
) -> ORJSONResponse:
    """Stop VK bot for a specific project."""
    from app import _resolve_admin_project, _get_mongo_client
    from models import Project
    from vk_bot.config import VkHub
    from tg_bot.bot import TelegramHub
    from max_bot.config import MaxHub
    
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        raise HTTPException(status_code=404, detail="project not found")

    provided_fields = getattr(payload, "model_fields_set", set()) if payload else set()
    if payload and "auto_start" in provided_fields:
        auto_start_value = (
            bool(payload.auto_start)
            if payload.auto_start is not None
            else None
        )
    else:
        auto_start_value = existing.vk_auto_start

    project_payload = Project(
        name=existing.name,
        title=existing.title,
        domain=existing.domain,
        llm_model=existing.llm_model,
        llm_prompt=existing.llm_prompt,
        llm_emotions_enabled=existing.llm_emotions_enabled if existing.llm_emotions_enabled is not None else True,
        telegram_token=existing.telegram_token,
        telegram_auto_start=existing.telegram_auto_start,
        max_token=existing.max_token,
        max_auto_start=existing.max_auto_start,
        vk_token=existing.vk_token,
        vk_auto_start=auto_start_value,
        widget_url=existing.widget_url,
        admin_username=existing.admin_username,
        admin_password_hash=existing.admin_password_hash,
        debug_enabled=existing.debug_enabled,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: VkHub = request.app.state.vk
    await hub.stop_project(saved.name, auto_start=auto_start_value if payload and "auto_start" in provided_fields else None)
    response = _project_vk_payload(saved, hub)
    telegram_hub: TelegramHub | None = getattr(request.app.state, "telegram", None)
    if isinstance(telegram_hub, TelegramHub):
        await telegram_hub.ensure_runner(saved)
    max_hub: MaxHub | None = getattr(request.app.state, "max", None)
    if isinstance(max_hub, MaxHub):
        await max_hub.ensure_runner(saved)
    return ORJSONResponse(response)

