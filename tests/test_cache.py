"""Tests for Redis caching decorator."""

import importlib.util
import sys
from pathlib import Path
import types
import json
from dataclasses import dataclass
import pytest

module_path = Path(__file__).resolve().parents[1] / "backend" / "cache.py"
spec = importlib.util.spec_from_file_location("backend.cache", module_path)
cache = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cache
old_redis = sys.modules.get("redis.asyncio")
fake_redis = types.ModuleType("redis.asyncio")
fake_redis.ConnectionPool = object
fake_redis.Redis = object
sys.modules["redis.asyncio"] = fake_redis
fake_settings = types.ModuleType("settings")
fake_settings.get_settings = lambda: types.SimpleNamespace(redis_url="redis://")
old_settings = sys.modules.get("settings")
sys.modules["settings"] = fake_settings
spec.loader.exec_module(cache)
if old_settings is None:
    del sys.modules["settings"]
else:
    sys.modules["settings"] = old_settings
if old_redis is None:
    del sys.modules["redis.asyncio"]
else:
    sys.modules["redis.asyncio"] = old_redis

from redis.asyncio import ConnectionPool as _RealConnectionPool, Redis as _RealRedis

cache.ConnectionPool = _RealConnectionPool
cache.Redis = _RealRedis


class FakeRedis:
    """Minimal in-memory Redis replacement used in tests."""
    def __init__(self):
        self.store = {}

    async def get(self, key):
        val = self.store.get(key)
        return None if val is None else val.encode()

    async def setex(self, key, ttl, value):
        self.store[key] = value


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
    stored = next(iter(redis.store.values()))
    assert json.loads(stored) == "hi!"


@dataclass
class Sample:
    x: int


@pytest.mark.asyncio
async def test_cache_serializes_dataclass(monkeypatch):
    """Dataclasses should round-trip through cache."""
    redis = FakeRedis()
    monkeypatch.setattr(cache, "_get_redis", lambda: redis)

    calls: list[str] = []

    @cache.cache_response
    async def func(q: str) -> Sample:
        calls.append(q)
        return Sample(x=1)

    first = await func("hi")
    second = await func("hi")

    assert first == Sample(x=1)
    assert second == Sample(x=1)
    assert len(calls) == 1
    stored = next(iter(redis.store.values()))
    data = json.loads(stored)
    assert data["__cls__"].endswith("Sample")
    assert data["x"] == 1
