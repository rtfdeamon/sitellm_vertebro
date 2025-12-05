"""Simple per-IP rate limiting middleware backed by Redis."""

from __future__ import annotations

import os
import time
from typing import Iterable

import structlog
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from backend.cache import _get_redis

logger = structlog.get_logger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    """Return a boolean from environment variable ``name``."""

    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "off", "no"}


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Redis-backed sliding window rate limiter."""

    def __init__(
        self,
        app,
        *,
        max_requests: int | None = None,
        window_seconds: int | None = None,
        exempt_paths: Iterable[str] | None = None,
        redis: Redis | None = None,
    ) -> None:
        super().__init__(app)
        self.enabled = _env_bool("RATE_LIMIT_ENABLED", True)
        self.bypass_authenticated = _env_bool("RATE_LIMIT_BYPASS_AUTHENTICATED", True)
        self.max_requests = max(
            1, int(max_requests or os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "120"))
        )
        self.window_seconds = max(
            1, int(window_seconds or os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
        )
        raw_exempt = exempt_paths or os.getenv(
            "RATE_LIMIT_EXEMPT_PATHS",
            "/healthz,/health,/metrics,/admin,/static,/assets,/favicon.ico",
        ).split(",")
        self.exempt_paths = tuple(path.strip() for path in raw_exempt if path.strip())
        self._redis = redis
        logger.info(
            "rate limit init",
            enabled=self.enabled,
            bypass_authenticated=self.bypass_authenticated,
            max_requests=self.max_requests,
            window_seconds=self.window_seconds,
            exempt_paths=self.exempt_paths,
        )

    def _is_exempt(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self.exempt_paths)

    def _is_authenticated(self, request: Request) -> bool:
        if request.cookies.get("admin_session"):
            return True
        auth_header = request.headers.get("Authorization", "")
        return auth_header.startswith("Basic ") or auth_header.startswith("Bearer ")

    def _key(self, request: Request) -> str:
        client = request.client.host if request.client else "unknown"
        return f"ratelimit:{client}"

    async def dispatch(self, request: Request, call_next) -> Response:
        if (
            not self.enabled
            or self._is_exempt(request.url.path)
            or (self.bypass_authenticated and self._is_authenticated(request))
        ):
            return await call_next(request)

        redis = self._redis or _get_redis()
        try:
            allowed, retry_after = await self._try_acquire(redis, self._key(request))
        except Exception as exc:  # pragma: no cover - safety fallback
            logger.warning("rate limit check failed; allowing request", error=str(exc))
            return await call_next(request)
        if allowed:
            return await call_next(request)

        headers = {"Retry-After": str(retry_after)}
        return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429, headers=headers)

    async def _try_acquire(self, redis: Redis, key: str) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""

        now = time.time()
        window_start = now - self.window_seconds

        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, self.window_seconds)
        pipe.zcard(key)
        _, count_before, _, _, count_after = await pipe.execute()

        if int(count_after or 0) <= self.max_requests:
            return True, 0

        oldest = await redis.zrange(key, 0, 0, withscores=True)
        retry_after = 1
        if oldest:
            retry_after = max(1, int(oldest[0][1] + self.window_seconds - now))
        return False, retry_after


__all__ = ["RateLimitingMiddleware"]
