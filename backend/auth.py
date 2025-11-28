"""Authentication and authorization logic."""

import hashlib
import hmac
import os

from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from backend.dependencies import get_mongo_client
from backend.middleware.admin import AdminIdentity
from backend.utils.project import normalize_project

ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")


def resolve_admin_password_digest(raw_value: str | None) -> bytes:
    """Resolve admin password digest from environment variable."""
    candidate = (raw_value or "").strip()
    if not candidate:
        candidate = hashlib.sha256(b"admin").hexdigest()

    lowered = candidate.lower()
    if lowered.startswith("sha256:"):
        lowered = lowered.split(":", 1)[1]

    try:
        digest = bytes.fromhex(lowered)
        if len(digest) == hashlib.sha256().digest_size:
            return digest
    except ValueError:
        pass

    return hashlib.sha256(candidate.encode()).digest()


ADMIN_PASSWORD_DIGEST = resolve_admin_password_digest(os.getenv("ADMIN_PASSWORD"))


def get_admin_identity(request: Request) -> AdminIdentity | None:
    """Get admin identity from request state."""
    identity = getattr(request.state, "admin", None)
    return identity if isinstance(identity, AdminIdentity) else None


def require_admin(request: Request) -> AdminIdentity:
    """Require admin authentication."""
    identity = get_admin_identity(request)
    if identity is None:
        raise HTTPException(status_code=401, detail="Admin authentication required")
    return identity


def require_super_admin(request: Request) -> AdminIdentity:
    """Require super admin privileges."""
    identity = require_admin(request)
    if not identity.is_super:
        raise HTTPException(status_code=403, detail="Super admin privileges required")
    return identity


def resolve_admin_project(
    request: Request,
    project_name: str | None,
    *,
    required: bool = False,
) -> str | None:
    """Resolve project context for admin actions."""
    identity = get_admin_identity(request)
    normalized = normalize_project(project_name)
    if identity and not identity.is_super:
        normalized_allowed: list[str] = []
        for proj in identity.projects:
            if not proj:
                continue
            cleaned = proj.strip().lower()
            if cleaned and cleaned not in normalized_allowed:
                normalized_allowed.append(cleaned)
        if not normalized_allowed:
            raise HTTPException(status_code=403, detail="Project administrator has no assigned project")
        if normalized and normalized not in normalized_allowed:
            raise HTTPException(status_code=403, detail="Access to project is forbidden")
        normalized = normalized or normalized_allowed[0]
        if not normalized:
            raise HTTPException(status_code=403, detail="Project scope is required")
    if required and not normalized:
        raise HTTPException(status_code=400, detail="Project identifier is required")
    return normalized


def admin_logout_response(request: Request) -> PlainTextResponse:
    """Return response to clear admin session."""
    response = PlainTextResponse("Logged out")
    response.delete_cookie("admin_session")
    return response
