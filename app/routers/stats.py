"""Statistics and logging router.

Provides endpoints for request statistics, logs, and session management.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import ORJSONResponse, StreamingResponse

from observability.logging import get_recent_logs
from app.services.auth import require_admin, require_super_admin


router = APIRouter(prefix="/api/v1/admin", tags=["stats"])


def _parse_stats_date(value: str | None) -> datetime | None:
    """Parse date string into datetime object."""
    if not value:
        return None
    try:
        # Try ISO format first
        if "T" in value or "Z" in value:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)
        # Try YYYY-MM-DD format
        dt = datetime.strptime(value, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _resolve_session_identifiers(
    request: Request,
    project: str | None,
    session_id: str | None,
) -> tuple[str | None, str]:
    """Resolve session identifiers from request."""
    # Import here to avoid circular dependency
    from app import _normalize_project
    
    project_name = _normalize_project(project)
    base = (
        session_id
        or request.headers.get("X-Session-Id")
        or request.headers.get("X-Client-Session")
    )
    if not base:
        base = request.cookies.get("chat_session")
    if not base:
        base = uuid4().hex
    base = base.strip().lower()
    if project_name:
        return project_name, f"{project_name}::{base}"
    return project_name, base


@router.get("/stats/requests", response_class=ORJSONResponse)
async def admin_request_stats(
    request: Request,
    project: str | None = None,
    start: str | None = None,
    end: str | None = None,
    channel: str | None = None,
) -> ORJSONResponse:
    """Get request statistics for the admin UI."""
    # Import here to avoid circular dependency
    from app import _resolve_admin_project, _get_mongo_client
    
    project_name = _resolve_admin_project(request, project)
    start_dt = _parse_stats_date(start)
    end_dt = _parse_stats_date(end)
    if end_dt:
        end_dt = end_dt + timedelta(days=1)
    mongo_client = _get_mongo_client(request)
    stats = await mongo_client.aggregate_request_stats(
        project=project_name,
        start=start_dt,
        end=end_dt,
        channel=channel,
    )
    return ORJSONResponse({"stats": stats})


@router.get("/stats/requests/export")
async def admin_request_stats_export(
    request: Request,
    project: str | None = None,
    start: str | None = None,
    end: str | None = None,
    channel: str | None = None,
) -> StreamingResponse:
    """Export request statistics as CSV."""
    # Import here to avoid circular dependency
    from app import _resolve_admin_project, _get_mongo_client
    
    project_name = _resolve_admin_project(request, project)
    start_dt = _parse_stats_date(start)
    end_dt = _parse_stats_date(end)
    if end_dt:
        end_dt = end_dt + timedelta(days=1)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "timestamp",
        "date",
        "project",
        "channel",
        "question",
        "response_chars",
        "attachments",
        "prompt_chars",
        "session_id",
        "user_id",
        "error",
    ])

    mongo_client = _get_mongo_client(request)
    async for item in mongo_client.iter_request_stats(
        project=project_name,
        start=start_dt,
        end=end_dt,
        channel=channel,
    ):
        ts = item.get("ts")
        if isinstance(ts, datetime):
            ts_str = ts.astimezone(timezone.utc).isoformat()
        else:
            ts_str = str(ts)
        day = item.get("date")
        if isinstance(day, datetime):
            day_str = day.date().isoformat()
        else:
            day_str = str(day)
        writer.writerow([
            ts_str,
            day_str,
            item.get("project"),
            item.get("channel"),
            item.get("question"),
            item.get("response_chars"),
            item.get("attachments"),
            item.get("prompt_chars"),
            item.get("session_id"),
            item.get("user_id"),
            item.get("error"),
        ])

    output.seek(0)
    filename = "request_stats.csv"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
    }
    return StreamingResponse(
        iter([output.getvalue().encode("utf-8")]),
        media_type="text/csv",
        headers=headers,
    )


@router.get("/logs", response_class=ORJSONResponse)
def admin_logs(request: Request, limit: int = 200) -> ORJSONResponse:
    """Return recent application logs for the admin UI.

    Parameters
    ----------
    limit:
        Maximum number of lines to return (default 200).
    """
    require_super_admin(request)
    try:
        limit = max(1, min(int(limit), 1000))
    except Exception:
        limit = 200
    lines = get_recent_logs(limit)
    return ORJSONResponse({"lines": lines})


@router.get("/session", response_class=ORJSONResponse)
async def admin_session(request: Request) -> ORJSONResponse:
    """Get current admin session information."""
    identity = require_admin(request)
    payload = {
        "username": identity.username,
        "is_super": identity.is_super,
        "projects": list(identity.projects),
        "primary_project": identity.primary_project,
        "can_manage_projects": identity.is_super,
    }
    return ORJSONResponse(payload)

