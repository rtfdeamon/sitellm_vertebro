"""Redis cache utilities for chat responses."""

from __future__ import annotations

import hashlib
from functools import wraps
from typing import Any, Awaitable, Callable, Coroutine
import pickle

from redis.asyncio import ConnectionPool, Redis
import structlog

try:
    from backend.settings import get_settings
except ModuleNotFoundError:  # pragma: no cover - fallback for tests
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


def cache_response(
    func: Callable[..., Awaitable[Any]]
) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Cache decorated coroutine results in Redis for 24h."""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        question: str | None = None
        if "question" in kwargs and isinstance(kwargs["question"], str):
            question = kwargs["question"]
        else:
            for arg in args:
                if isinstance(arg, str):
                    question = arg
                    break
                if (
                    isinstance(arg, list)
                    and arg
                    and isinstance(arg[-1], dict)
                ):
                    msg = arg[-1]
                    text = msg.get("content") or msg.get("text")
                    if isinstance(text, str):
                        question = text
                        break
        if question is None:
            raise ValueError("No question string found for caching")
        key = hashlib.sha1(question.lower().encode()).hexdigest()
        redis = _get_redis()
        cached = await redis.get(key)
        if cached is not None:
            logger.info("cache hit", key=key)
            return pickle.loads(cached)
        answer = await func(*args, **kwargs)
        await redis.setex(key, 86400, pickle.dumps(answer))
        logger.info("cache store", key=key)
        return answer

    return wrapper


def cache_query_rewrite(
    func: Callable[..., Awaitable[str]]
) -> Callable[..., Coroutine[Any, Any, str]]:
    """Cache query rewrite results in Redis for 24h."""

    @wraps(func)
    async def wrapper(query: str, *args: Any, **kwargs: Any) -> str:
        key = "rewrite:" + hashlib.sha1(query.lower().encode()).hexdigest()
        redis = _get_redis()
        cached = await redis.get(key)
        if cached is not None:
            logger.info("cache hit", key=key)
            return cached.decode()
        rewritten = await func(query, *args, **kwargs)
        await redis.setex(key, 86400, rewritten)
        logger.info("cache store", key=key)
        return rewritten

    return wrapper


__all__ = ["cache_response", "cache_query_rewrite"]
