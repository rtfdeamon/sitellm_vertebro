"""Backup API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.auth import require_super_admin
from models import BackupOperation, BackupStatus
from worker import backup_execute

router = APIRouter(prefix="/backup", tags=["backup"])


class BackupSettingsPayload(BaseModel):
    yandex_disk_token: str | None = None
    backup_auto_enabled: bool | None = None
    backup_schedule: str | None = None  # cron expression


class BackupRunRequest(BaseModel):
    comment: str | None = None


class BackupRestoreRequest(BaseModel):
    backup_id: str


@router.get("/status", response_model=BackupStatus)
async def backup_status(
    request: Request,
    limit: int = 10,
    _: Any = Depends(require_super_admin),
):
    """
    Get backup system status and job history.

    Security: Super admin only. Backup operations access ALL database data across
    all projects, including sensitive credentials and data that regular admins
    should not have access to.
    """
    mongo = request.state.mongo
    settings_doc = await mongo.get_backup_settings()
    
    # Get recent jobs
    jobs = await mongo.list_backup_jobs(limit=limit)
    
    return BackupStatus(
        enabled=bool(settings_doc.get("backup_auto_enabled")),
        schedule=settings_doc.get("backup_schedule"),
        yandex_disk_connected=bool(settings_doc.get("yandex_disk_token")),
        last_backup=jobs[0].created_at if jobs else None,
        jobs=jobs,
    )


@router.post("/settings")
async def backup_update_settings(
    request: Request,
    payload: BackupSettingsPayload,
    _: Any = Depends(require_super_admin),
):
    """
    Update backup configuration and Yandex Disk credentials.

    Security: Super admin only. This endpoint manages cloud storage credentials
    (Yandex Disk token) that provide access to all backup files. Compromise of
    these credentials could expose all historical database backups.
    """
    mongo = request.state.mongo
    update = {}
    if payload.yandex_disk_token is not None:
        update["yandex_disk_token"] = payload.yandex_disk_token
    if payload.backup_auto_enabled is not None:
        update["backup_auto_enabled"] = payload.backup_auto_enabled
    if payload.backup_schedule is not None:
        update["backup_schedule"] = payload.backup_schedule
        
    if update:
        await mongo.upsert_backup_settings(update)
        
    return {"status": "ok"}


@router.post("/run")
async def backup_run(
    request: Request,
    payload: BackupRunRequest | None = None,
    _: Any = Depends(require_super_admin),
):
    """
    Trigger immediate database backup to cloud storage.

    Security: Super admin only. This operation creates a complete dump of ALL
    database collections, including user data, credentials, API keys, and other
    sensitive information across all projects. The backup file contains data
    that regular project administrators should not have access to.
    """
    comment = payload.comment if payload else None
    job_id = await backup_execute(BackupOperation.BACKUP, comment=comment)
    return {"status": "started", "job_id": job_id}


@router.post("/restore")
async def backup_restore(
    request: Request,
    payload: BackupRestoreRequest,
    _: Any = Depends(require_super_admin),
):
    """
    Restore database from a cloud storage backup.

    Security: Super admin only. This is the MOST DANGEROUS operation in the system.
    It completely overwrites the current database with backup data, affecting ALL
    projects and users. Malicious use could lead to:
    - Data loss (overwriting current data)
    - Privilege escalation (restoring old admin credentials)
    - Data corruption or system compromise
    Regular administrators must never have access to this capability.
    """
    job_id = await backup_execute(BackupOperation.RESTORE, backup_id=payload.backup_id)
    return {"status": "started", "job_id": job_id}
