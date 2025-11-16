"""Backup management router.

Security: All endpoints require super admin access as backup operations
access ALL database data across all projects, including sensitive credentials.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel, ConfigDict, Field

from models import BackupJob, BackupOperation, BackupStatus
from worker import backup_execute


router = APIRouter(prefix="/api/v1/backup", tags=["backup"])


class BackupSettingsPayload(BaseModel):
    enabled: bool | None = None
    hour: int | None = None
    minute: int | None = None
    timezone: str | None = None
    ya_disk_folder: str | None = Field(default=None, alias="yaDiskFolder")
    token: str | None = None
    clear_token: bool | None = Field(default=None, alias="clearToken")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class BackupRestoreRequest(BaseModel):
    remote_path: str = Field(alias="remotePath")
    source_job_id: str | None = Field(default=None, alias="sourceJobId")

    model_config = ConfigDict(populate_by_name=True)


class BackupRunRequest(BaseModel):
    note: str | None = None


def _serialize_backup_job(job: BackupJob | None) -> dict[str, Any] | None:
    """Serialize backup job to dict."""
    if not job:
        return None
    return job.model_dump(by_alias=True)


@router.get("/status", response_class=ORJSONResponse)
async def backup_status(request: Request, limit: int = 10) -> ORJSONResponse:
    """
    Get backup system status and job history.

    Security: Super admin only. Backup operations access ALL database data across
    all projects, including sensitive credentials and data that regular admins
    should not have access to.
    """
    # Use auth helper to avoid circular dependency
    from app.services.auth import require_super_admin as _require_super_admin
    
    _require_super_admin(request)
    try:
        safe_limit = max(1, min(int(limit), 50))
    except Exception:
        safe_limit = 10
    settings_model = await request.state.mongo.get_backup_settings()
    active_job = await request.state.mongo.find_active_backup_job()
    jobs = await request.state.mongo.list_backup_jobs(limit=safe_limit)
    payload = {
        "settings": settings_model.model_dump(by_alias=True),
        "activeJob": _serialize_backup_job(active_job),
        "jobs": [_serialize_backup_job(job) for job in jobs],
    }
    return ORJSONResponse(payload)


@router.post("/settings", response_class=ORJSONResponse)
async def backup_update_settings(
    request: Request,
    payload: BackupSettingsPayload
) -> ORJSONResponse:
    """
    Update backup configuration and Yandex Disk credentials.

    Security: Super admin only. This endpoint manages cloud storage credentials
    (Yandex Disk token) that provide access to all backup files. Compromise of
    these credentials could expose all historical database backups.
    """
    # Use auth helper to avoid circular dependency
    from app.services.auth import require_super_admin as _require_super_admin
    
    _require_super_admin(request)
    updates: dict[str, Any] = {}
    if payload.enabled is not None:
        updates["enabled"] = bool(payload.enabled)
    if payload.hour is not None:
        updates["hour"] = int(payload.hour)
    if payload.minute is not None:
        updates["minute"] = int(payload.minute)
    if payload.timezone is not None:
        updates["timezone"] = payload.timezone
    if payload.ya_disk_folder is not None:
        updates["yaDiskFolder"] = payload.ya_disk_folder

    extra_kwargs: dict[str, Any] = {}
    if payload.token is not None:
        extra_kwargs["token"] = payload.token

    settings_model = await request.state.mongo.update_backup_settings(
        updates,
        clear_token=bool(payload.clear_token),
        **extra_kwargs,
    )
    return ORJSONResponse(settings_model.model_dump(by_alias=True))


@router.post("/run", response_class=ORJSONResponse)
async def backup_run(
    request: Request,
    payload: BackupRunRequest | None = None
) -> ORJSONResponse:
    """
    Trigger immediate database backup to cloud storage.

    Security: Super admin only. This operation creates a complete dump of ALL
    database collections, including user data, credentials, API keys, and other
    sensitive information across all projects. The backup file contains data
    that regular project administrators should not have access to.
    """
    # Use auth helper to avoid circular dependency
    from app.services.auth import require_super_admin as _require_super_admin
    
    identity = _require_super_admin(request)
    active_job = await request.state.mongo.find_active_backup_job()
    if active_job:
        raise HTTPException(status_code=409, detail="backup_job_in_progress")
    token = await request.state.mongo.get_backup_token()
    if not token:
        raise HTTPException(status_code=400, detail="ya_disk_token_missing")

    triggered = getattr(identity, "username", None) or "admin"
    job = await request.state.mongo.create_backup_job(
        operation=BackupOperation.backup,
        status=BackupStatus.queued,
        triggered_by=f"admin:{triggered}",
    )
    backup_execute.delay(job.id)
    return ORJSONResponse({"job": _serialize_backup_job(job)})


@router.post("/restore", response_class=ORJSONResponse)
async def backup_restore(
    request: Request,
    payload: BackupRestoreRequest
) -> ORJSONResponse:
    """
    Restore database from a cloud storage backup.

    Security: Super admin only. This is the MOST DANGEROUS operation in the system.
    It completely overwrites the current database with backup data, affecting ALL
    projects and users. Unauthorized use could result in:
    - Complete data loss (if wrong backup selected)
    - Privilege escalation (restoring old admin credentials)
    - Data corruption or system compromise
    Regular administrators must never have access to this capability.
    """
    # Use auth helper to avoid circular dependency
    from app.services.auth import require_super_admin as _require_super_admin
    
    identity = _require_super_admin(request)
    remote_path = (payload.remote_path or "").strip()
    if not remote_path:
        raise HTTPException(status_code=400, detail="remote_path_required")

    active_job = await request.state.mongo.find_active_backup_job()
    if active_job:
        raise HTTPException(status_code=409, detail="backup_job_in_progress")

    token = await request.state.mongo.get_backup_token()
    if not token:
        raise HTTPException(status_code=400, detail="ya_disk_token_missing")

    triggered = getattr(identity, "username", None) or "admin"
    job = await request.state.mongo.create_backup_job(
        operation=BackupOperation.restore,
        status=BackupStatus.queued,
        triggered_by=f"admin:{triggered}",
        remote_path=remote_path,
        source_job_id=payload.source_job_id,
    )
    backup_execute.delay(job.id)
    return ORJSONResponse({"job": _serialize_backup_job(job)})

