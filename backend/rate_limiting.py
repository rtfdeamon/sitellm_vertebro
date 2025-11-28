"""
Rate limiting middleware for FastAPI.

Provides Redis-backed rate limiting with configurable limits per endpoint.
"""

from __future__ import annotations

import os
from typing import Any

import structlog
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from backend.security import RateLimiter, get_client_ip
from backend.cache import _get_redis

logger = structlog.get_logger(__name__)

# Rate limiting enabled flag
RATE_LIMITING_ENABLED = os.getenv("RATE_LIMITING_ENABLED", "true").lower() == "true"


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests."""
    
    def __init__(self, app: Any):
        super().__init__(app)
        self.rate_limiter = None
        self._init_rate_limiter()
    
    def _init_rate_limiter(self) -> None:
        """Initialize rate limiter with Redis connection."""
        try:
            if RATE_LIMITING_ENABLED:
                redis_client = _get_redis()
                self.rate_limiter = RateLimiter(redis_client)
                logger.info("rate_limiting_middleware_initialized", enabled=True)
            else:
                logger.info("rate_limiting_middleware_initialized", enabled=False)
        except Exception as exc:  # noqa: BLE001
            logger.warning("rate_limiting_init_failed", error=str(exc))
            # Degrade gracefully - allow requests if Redis fails
            self.rate_limiter = None
    
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Process request and check rate limits."""
        
        # Skip rate limiting for health checks and metrics
        if request.url.path in {"/health", "/healthz", "/status", "/metrics"}:
            return await call_next(request)
        
        # Skip rate limiting if disabled
        if not RATE_LIMITING_ENABLED or not self.rate_limiter:
            return await call_next(request)
        
        # Get client IP
        client_ip = get_client_ip(request)
        if client_ip == "unknown":
            # If we can't determine IP, allow request but log
            logger.warning("unknown_client_ip", path=request.url.path)
            return await call_next(request)
        
        # Check rate limits based on HTTP method
        is_read = request.method in {"GET", "HEAD", "OPTIONS"}
        is_write = request.method in {"POST", "PUT", "PATCH", "DELETE"}
        
        if is_read:
            allowed, retry_after = await self.rate_limiter.check_read_limit(client_ip)
        elif is_write:
            allowed, retry_after = await self.rate_limiter.check_write_limit(client_ip)
        else:
            # Allow other methods without rate limiting
            return await call_next(request)
        
        if not allowed:
            # Rate limit exceeded
            logger.warning(
                "rate_limit_exceeded",
                ip=client_ip,
                method=request.method,
                path=request.url.path,
                retry_after=retry_after,
            )
            
            response = Response(
                content=f"Rate limit exceeded. Please retry after {retry_after} seconds.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            response.headers["Retry-After"] = str(retry_after)
            response.headers["X-RateLimit-Limit"] = str(
                os.getenv("RATE_LIMIT_READ_PER_MIN", "100") if is_read
                else os.getenv("RATE_LIMIT_WRITE_PER_MIN", "10")
            )
            response.headers["X-RateLimit-Retry-After"] = str(retry_after)
            return response
        
        # Process request if rate limit not exceeded
        return await call_next(request)

