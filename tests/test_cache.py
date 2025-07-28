"""Tests for Redis caching decorator."""

import importlib.util
import sys
from pathlib import Path
import types
import pytest

module_path = Path(__file__).resolve().parents[1] / "backend" / "cache.py"
spec = importlib.util.spec_from_file_location("backend.cache", module_path)
cache = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cache
fake_redis = types.ModuleType("redis.asyncio")
fake_redis.ConnectionPool = object
fake_redis.Redis = object
sys.modules["redis.asyncio"] = fake_redis
fake_settings = types.ModuleType("settings")
fake_settings.get_settings = lambda: types.SimpleNamespace(redis_url="redis://")
sys.modules["settings"] = fake_settings
spec.loader.exec_module(cache)


class FakeRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        val = self.store.get(key)
        return None if val is None else val

    async def setex(self, key, ttl, value):
        self.store[key] = value.encode() if isinstance(value, str) else value


@pytest.mark.asyncio
async def test_cache_decorator(monkeypatch):
    """Result should be stored and reused."""
    redis = FakeRedis()
    monkeypatch.setattr(cache, "_get_redis", lambda: redis)

    calls = []

    @cache.cache_response
    async def func(q):
        calls.append(q)
        return q + "!"

    first = await func("hi")
    second = await func("hi")

    assert first == "hi!"
    assert second == "hi!"
    assert len(calls) == 1
