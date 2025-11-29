"""API utility functions."""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from urllib.parse import quote

from fastapi import Request
from starlette.responses import Response

from models import Project
from backend.cache import _get_redis


def project_response(project: Project) -> dict[str, Any]:
    """Format project model for API response."""
    data = project.model_dump()
    data.pop("admin_password_hash", None)
    data.pop("telegram_token", None)
    data.pop("max_token", None)
    data.pop("vk_token", None)
    data.pop("mail_password", None)
    data["admin_password_set"] = bool(project.admin_password_hash)
    data["telegram_token_set"] = bool(project.telegram_token)
    data["max_token_set"] = bool(project.max_token)
    data["vk_token_set"] = bool(project.vk_token)
    data["mail_password_set"] = bool(project.mail_password)
    return data


def parse_stats_date(value: str | None) -> datetime | None:
    """Parse date string for stats filtering."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def build_download_url(request: Request, file_id: str) -> str:
    """Build absolute download URL for a file."""
    return str(request.url_for("download_file", file_id=file_id))


def build_content_disposition(filename: str) -> str:
    """Build Content-Disposition header value."""
    try:
        filename.encode("ascii")
        return f'attachment; filename="{filename}"'
    except UnicodeEncodeError:
        encoded = quote(filename)
        return f"attachment; filename*=utf-8''{encoded}"


def build_token_preview(token: str | None) -> str | None:
    """Return a masked preview of a token."""
    if not token or len(token) < 8:
        return None
    return f"{token[:4]}...{token[-4:]}"


async def redis_project_usage() -> dict[str, dict[str, float | int]]:
    """Collect Redis usage statistics per project."""
    import structlog
    from backend.cache import _get_redis

    logger = structlog.get_logger(__name__)
    redis = _get_redis()
    usage: dict[str, dict[str, float | int]] = {}
    try:
        async for key in redis.scan_iter(match="crawler:progress:*"):
            project_key = "__default__"
            try:
                project_value = await redis.hget(key, "project")
                if project_value:
                    decoded = project_value.decode().strip().lower()
                    if decoded:
                        project_key = decoded
            except Exception:  # noqa: BLE001
                pass
            try:
                size = await redis.memory_usage(key)
            except Exception:  # noqa: BLE001
                size = None
            entry = usage.setdefault(
                project_key,
                {
                    "redis_bytes": 0.0,
                    "redis_keys": 0,
                },
            )
            entry["redis_keys"] += 1
            entry["redis_bytes"] += float(size or 0)
    except Exception as exc:  # noqa: BLE001
        logger.warning("redis_usage_failed", error=str(exc))
    return usage
