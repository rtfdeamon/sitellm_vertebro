"""Redis cache utilities for chat responses."""

from __future__ import annotations

import hashlib
from functools import wraps
from typing import Any, Awaitable, Callable, Coroutine

from redis.asyncio import ConnectionPool, Redis
import structlog

from settings import get_settings

logger = structlog.get_logger(__name__)

_POOL: ConnectionPool | None = None


def _get_redis() -> Redis:
    """Return a Redis client using a global connection pool."""

    global _POOL
    if _POOL is None:
        _POOL = ConnectionPool.from_url(str(get_settings().redis_url))
        logger.info("init redis pool")
    return Redis(connection_pool=_POOL)


def cache_response(func: Callable[..., Awaitable[str]]) -> Callable[..., Coroutine[Any, Any, str]]:
    """Cache decorated coroutine results in Redis for 24h."""

    @wraps(func)
    async def wrapper(question: str, *args: Any, **kwargs: Any) -> str:
        key = hashlib.sha1(question.lower().encode()).hexdigest()
        redis = _get_redis()
        cached = await redis.get(key)
        if cached is not None:
            logger.info("cache hit", key=key)
            return cached.decode()
        answer = await func(question, *args, **kwargs)
        await redis.setex(key, 86400, answer)
        logger.info("cache store", key=key)
        return answer

    return wrapper

__all__ = ["cache_response"]
