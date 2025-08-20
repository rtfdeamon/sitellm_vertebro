"""Redis cache utilities for chat responses."""

from __future__ import annotations

import hashlib
from functools import wraps
from typing import Any, Awaitable, Callable, Coroutine
import json
import importlib
from types import SimpleNamespace

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
            return _deserialize(json.loads(cached))
        answer = await func(*args, **kwargs)
        serialized = json.dumps(_serialize(answer))
        await redis.setex(key, 86400, serialized)
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


def _serialize(obj: Any) -> Any:
    """Recursively convert objects to JSON-serializable structures."""
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _serialize(val) for key, val in obj.items()}
    if isinstance(obj, SimpleNamespace):
        return {"__cls__": "types.SimpleNamespace", **_serialize(obj.__dict__)}
    if hasattr(obj, "model_dump"):
        return {
            "__cls__": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
            **_serialize(obj.model_dump()),
        }
    if hasattr(obj, "__dict__"):
        return {
            "__cls__": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
            **_serialize(obj.__dict__),
        }
    return obj


def _deserialize(obj: Any) -> Any:
    """Reconstruct objects previously serialized with :func:`_serialize`."""
    if isinstance(obj, list):
        return [_deserialize(item) for item in obj]
    if isinstance(obj, dict):
        cls_name = obj.get("__cls__")
        if cls_name:
            payload = {k: _deserialize(v) for k, v in obj.items() if k != "__cls__"}
            if cls_name == "types.SimpleNamespace":
                return SimpleNamespace(**payload)
            module_name, _, class_name = cls_name.rpartition(".")
            try:
                module = importlib.import_module(module_name)
                cls = getattr(module, class_name)
                if hasattr(cls, "model_validate"):
                    return cls.model_validate(payload)  # type: ignore[call-arg]
                return cls(**payload)
            except Exception:  # pragma: no cover - fallback on failure
                return payload
        return {k: _deserialize(v) for k, v in obj.items()}
    return obj
