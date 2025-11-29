"""Admin API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse

from backend.auth import admin_logout_response, require_admin
from observability.logging import get_recent_logs

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/logout")
def admin_logout(request: Request) -> PlainTextResponse:
    return admin_logout_response(request)


@router.get("/logout")
def admin_logout_get(request: Request) -> PlainTextResponse:
    return admin_logout_response(request)


@router.get("/session")
def admin_session(
    request: Request,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """Return current admin session info."""
    identity = request.state.admin
    return {
        "username": identity.username,
        "is_super": identity.is_super,
        "projects": identity.projects,
    }


@router.get("/logs")
async def admin_logs(
    request: Request,
    limit: int = 200,
    _: Any = Depends(require_admin),
) -> dict[str, Any]:
    """
    Return recent application logs for the admin UI.

    Parameters
    ----------
    limit:
        Maximum number of lines to return (default 200).
    """
    return {"logs": get_recent_logs(limit)}


@router.get("/csrf-token")
async def get_csrf_token_endpoint(request: Request) -> dict[str, str]:
    """Return CSRF token for the current session."""
    from backend.csrf import get_csrf_token
    token = await get_csrf_token(request)
    return {"csrf_token": token}
