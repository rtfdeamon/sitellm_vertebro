"""
CSRF protection utilities for forms and API requests.

Provides CSRF token generation, validation, and middleware integration.
"""

from __future__ import annotations

import os
import secrets
import hmac
import hashlib
from typing import Any
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from backend.cache import _get_redis

logger = structlog.get_logger(__name__)

# CSRF configuration
CSRF_TOKEN_LENGTH = int(os.getenv("CSRF_TOKEN_LENGTH", "32"))
CSRF_TOKEN_TTL = int(os.getenv("CSRF_TOKEN_TTL", "3600"))  # 1 hour
CSRF_SECRET_KEY = os.getenv("CSRF_SECRET_KEY", os.urandom(32).hex())


def generate_csrf_token() -> str:
    """Generate a secure CSRF token."""
    return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)


def verify_csrf_token(token: str, stored_token: str | None) -> bool:
    """Verify CSRF token against stored value."""
    if not token or not stored_token:
        return False
    
    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(token.encode(), stored_token.encode())


async def get_csrf_token(request: Request) -> str:
    """Get or generate CSRF token for the current session."""
    # Try to get token from session cookie
    session_id = request.cookies.get("session_id")
    if not session_id:
        # Generate new session ID
        session_id = secrets.token_urlsafe(32)
    
    # Try to get token from Redis
    try:
        redis_client = _get_redis()
        cache_key = f"csrf_token:{session_id}"
        stored_token = await redis_client.get(cache_key)
        if stored_token:
            return stored_token.decode() if isinstance(stored_token, bytes) else stored_token
    except Exception:  # noqa: BLE001
        # Degrade gracefully if Redis fails
        logger.warning("csrf_redis_get_failed")
    
    # Generate new token
    token = generate_csrf_token()
    
    # Store in Redis
    try:
        redis_client = _get_redis()
        cache_key = f"csrf_token:{session_id}"
        await redis_client.setex(cache_key, CSRF_TOKEN_TTL, token)
    except Exception:  # noqa: BLE001
        logger.warning("csrf_redis_set_failed")
    
    return token


async def validate_csrf_token(request: Request, token: str | None) -> bool:
    """Validate CSRF token from request."""
    if not token:
        return False
    
    # Get session ID from cookie
    session_id = request.cookies.get("session_id")
    if not session_id:
        return False
    
    # Get stored token from Redis
    try:
        redis_client = _get_redis()
        cache_key = f"csrf_token:{session_id}"
        stored_token = await redis_client.get(cache_key)
        if not stored_token:
            return False
        
        stored_token = stored_token.decode() if isinstance(stored_token, bytes) else stored_token
        return verify_csrf_token(token, stored_token)
    except Exception:  # noqa: BLE001
        logger.warning("csrf_redis_validation_failed")
        # Degrade gracefully - allow request if Redis fails
        return True


class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware for CSRF protection on state-changing requests."""
    
    # Safe methods that don't require CSRF protection
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    
    # Paths that don't require CSRF protection
    EXCLUDED_PATHS = {
        "/health",
        "/healthz",
        "/status",
        "/metrics",
    }
    
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Process request and check CSRF token for state-changing methods."""
        
        # Skip CSRF check for safe methods
        if request.method in self.SAFE_METHODS:
            return await call_next(request)
        
        # Skip CSRF check for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Get CSRF token from header or form data
        csrf_token = (
            request.headers.get("X-CSRF-Token")
            or request.headers.get("X-Csrf-Token")
            or (await request.form()).get("csrf_token")
        )
        
        # Validate CSRF token
        if not await validate_csrf_token(request, csrf_token):
            logger.warning(
                "csrf_validation_failed",
                path=request.url.path,
                method=request.method,
                ip=request.client.host if request.client else "unknown",
            )
            response = Response(
                content="CSRF token validation failed",
                status_code=status.HTTP_403_FORBIDDEN,
            )
            return response
        
        # Process request
        response = await call_next(request)
        
        # Add CSRF token to response headers if available
        try:
            from backend.csrf import get_csrf_token
            token = await get_csrf_token(request)
            response.headers["X-CSRF-Token"] = token
        except Exception:  # noqa: BLE001
            pass
        
        return response


def add_csrf_token_to_response(response: Response, token: str) -> None:
    """Add CSRF token to response headers."""
    response.headers["X-CSRF-Token"] = token

