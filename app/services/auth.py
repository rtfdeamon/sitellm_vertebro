"""Authentication and authorization helpers for routers."""

from __future__ import annotations

from dataclasses import dataclass
from fastapi import HTTPException, Request
import structlog
from datetime import datetime, timezone

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class AdminIdentity:
    """Represents authenticated admin context."""

    username: str
    is_super: bool
    projects: tuple[str, ...] = ()

    def can_access_project(self, project: str | None) -> bool:
        """Check if identity can access the given project."""
        if self.is_super:
            return True
        if not project:
            return False
        normalized = project.strip().lower()
        return normalized in self.projects

    @property
    def primary_project(self) -> str | None:
        """Get primary project for this identity."""
        return self.projects[0] if self.projects else None


def _get_admin_identity(request: Request) -> AdminIdentity | None:
    """Get admin identity from request state."""
    identity = getattr(request.state, "admin", None)
    return identity if isinstance(identity, AdminIdentity) else None


def require_admin(request: Request) -> AdminIdentity:
    """Require admin authentication, raise 401 if not authenticated."""
    identity = _get_admin_identity(request)
    if identity is None:
        raise HTTPException(status_code=401, detail="Admin authentication required")
    return identity


def require_super_admin(request: Request) -> AdminIdentity:
    """Require super admin privileges, raise 403 if not super admin."""
    identity = require_admin(request)
    if not identity.is_super:
        # Log unauthorized access attempt for security audit
        from backend.security import get_client_ip
        client_ip = get_client_ip(request)
        logger.warning(
            "unauthorized_super_admin_access_attempt",
            username=identity.username,
            path=request.url.path,
            method=request.method,
            ip=client_ip,
            user_agent=request.headers.get("User-Agent", "unknown"),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        raise HTTPException(status_code=403, detail="Super admin privileges required")
    
    # Log successful super admin access for audit trail
    logger.info(
        "super_admin_access_granted",
        username=identity.username,
        path=request.url.path,
        method=request.method,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return identity

