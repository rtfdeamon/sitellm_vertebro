"""
Enhanced Redis cache manager with configurable TTLs for different data types.

Provides caching decorators for:
- LLM results (1 hour)
- Embeddings (24 hours)
- Search queries (15 minutes)
"""

from __future__ import annotations

import os
import hashlib
from functools import wraps
from typing import Any, Awaitable, Callable, Coroutine
import json
import importlib
from types import SimpleNamespace
import dataclasses

from redis.asyncio import ConnectionPool, Redis
import structlog

try:
    from backend.settings import get_settings
except ModuleNotFoundError:  # pragma: no cover - fallback for tests
    from settings import get_settings

from backend.cache import _get_redis, _serialize, _deserialize

logger = structlog.get_logger(__name__)

# Cache TTL configuration (in seconds)
CACHE_TTL_LLM_RESULTS = int(os.getenv("CACHE_TTL_LLM_RESULTS", "3600"))  # 1 hour
CACHE_TTL_EMBEDDINGS = int(os.getenv("CACHE_TTL_EMBEDDINGS", "86400"))  # 24 hours
CACHE_TTL_SEARCH = int(os.getenv("CACHE_TTL_SEARCH", "900"))  # 15 minutes
CACHE_TTL_QUERY_REWRITE = int(os.getenv("CACHE_TTL_QUERY_REWRITE", "86400"))  # 24 hours


def cache_llm_result(
    ttl: int | None = None,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Coroutine[Any, Any, Any]]]:
    """Cache LLM generation results in Redis.
    
    Parameters
    ----------
    ttl:
        Time-to-live in seconds (default: 1 hour).
    
    Returns
    -------
    Decorator function for caching LLM results.
    """
    ttl = ttl or CACHE_TTL_LLM_RESULTS
    
    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract question/query text for cache key
            question: str | None = None
            if "question" in kwargs and isinstance(kwargs["question"], str):
                question = kwargs["question"]
            elif "query" in kwargs and isinstance(kwargs["query"], str):
                question = kwargs["query"]
            elif "text" in kwargs and isinstance(kwargs["text"], str):
                question = kwargs["text"]
            else:
                for arg in args:
                    if isinstance(arg, str):
                        question = arg
                        break
                    if isinstance(arg, list) and arg and isinstance(arg[-1], dict):
                        msg = arg[-1]
                        text = msg.get("content") or msg.get("text") or msg.get("question")
                        if isinstance(text, str):
                            question = text
                            break
            
            if not question:
                # No cache key available, skip caching
                return await func(*args, **kwargs)
            
            # Generate cache key
            cache_key = f"llm:{hashlib.sha256(question.lower().encode()).hexdigest()}"
            
            try:
                redis = _get_redis()
                cached = await redis.get(cache_key)
                if cached is not None:
                    logger.info("cache_hit_llm", key=cache_key)
                    data = cached.decode() if isinstance(cached, (bytes, bytearray)) else cached
                    return _deserialize(json.loads(data))
                
                # Cache miss - execute function
                result = await func(*args, **kwargs)
                
                # Store in cache
                serialized = json.dumps(_serialize(result), ensure_ascii=False)
                await redis.setex(cache_key, ttl, serialized)
                logger.info("cache_store_llm", key=cache_key, ttl=ttl)
                
                return result
            except Exception as exc:  # noqa: BLE001
                # Degrade gracefully - return result without caching
                logger.warning("cache_error_llm", error=str(exc))
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def cache_embedding(
    ttl: int | None = None,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Coroutine[Any, Any, Any]]]:
    """Cache embedding vectors in Redis.
    
    Parameters
    ----------
    ttl:
        Time-to-live in seconds (default: 24 hours).
    
    Returns
    -------
    Decorator function for caching embeddings.
    """
    ttl = ttl or CACHE_TTL_EMBEDDINGS
    
    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract text for cache key
            text: str | None = None
            if "text" in kwargs and isinstance(kwargs["text"], str):
                text = kwargs["text"]
            elif "query" in kwargs and isinstance(kwargs["query"], str):
                text = kwargs["query"]
            else:
                for arg in args:
                    if isinstance(arg, str):
                        text = arg
                        break
            
            if not text:
                # No cache key available, skip caching
                return await func(*args, **kwargs)
            
            # Generate cache key (include model if available)
            model = kwargs.get("model", "default")
            cache_key = f"embedding:{model}:{hashlib.sha256(text.lower().encode()).hexdigest()}"
            
            try:
                redis = _get_redis()
                cached = await redis.get(cache_key)
                if cached is not None:
                    logger.info("cache_hit_embedding", key=cache_key)
                    data = json.loads(cached.decode() if isinstance(cached, (bytes, bytearray)) else cached)
                    # Embeddings are typically lists/arrays
                    return data if isinstance(data, list) else _deserialize(data)
                
                # Cache miss - execute function
                result = await func(*args, **kwargs)
                
                # Store in cache
                serialized = json.dumps(_serialize(result), ensure_ascii=False)
                await redis.setex(cache_key, ttl, serialized)
                logger.info("cache_store_embedding", key=cache_key, ttl=ttl)
                
                return result
            except Exception as exc:  # noqa: BLE001
                # Degrade gracefully - return result without caching
                logger.warning("cache_error_embedding", error=str(exc))
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def cache_search_result(
    ttl: int | None = None,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Coroutine[Any, Any, Any]]]:
    """Cache search query results in Redis.
    
    Parameters
    ----------
    ttl:
        Time-to-live in seconds (default: 15 minutes).
    
    Returns
    -------
    Decorator function for caching search results.
    """
    ttl = ttl or CACHE_TTL_SEARCH
    
    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract query for cache key
            query: str | None = None
            if "query" in kwargs and isinstance(kwargs["query"], str):
                query = kwargs["query"]
            else:
                for arg in args:
                    if isinstance(arg, str):
                        query = arg
                        break
            
            if not query:
                # No cache key available, skip caching
                return await func(*args, **kwargs)
            
            # Generate cache key (include k/top if available)
            k = kwargs.get("k", kwargs.get("top", 10))
            cache_key = f"search:{hashlib.sha256(query.lower().encode()).hexdigest()}:k{k}"
            
            try:
                redis = _get_redis()
                cached = await redis.get(cache_key)
                if cached is not None:
                    logger.info("cache_hit_search", key=cache_key)
                    data = cached.decode() if isinstance(cached, (bytes, bytearray)) else cached
                    return _deserialize(json.loads(data))
                
                # Cache miss - execute function
                result = await func(*args, **kwargs)
                
                # Store in cache
                serialized = json.dumps(_serialize(result), ensure_ascii=False)
                await redis.setex(cache_key, ttl, serialized)
                logger.info("cache_store_search", key=cache_key, ttl=ttl)
                
                return result
            except Exception as exc:  # noqa: BLE001
                # Degrade gracefully - return result without caching
                logger.warning("cache_error_search", error=str(exc))
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


async def invalidate_cache_pattern(pattern: str) -> int:
    """Invalidate cache entries matching a pattern.
    
    Parameters
    ----------
    pattern:
        Redis key pattern (e.g., "llm:*", "embedding:*").
    
    Returns
    -------
    Number of keys deleted.
    """
    try:
        redis = _get_redis()
        keys = []
        async for key in redis.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            deleted = await redis.delete(*keys)
            logger.info("cache_invalidated", pattern=pattern, count=deleted)
            return deleted
        return 0
    except Exception as exc:  # noqa: BLE001
        logger.warning("cache_invalidation_failed", pattern=pattern, error=str(exc))
        return 0





