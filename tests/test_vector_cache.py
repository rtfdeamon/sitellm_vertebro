"""Tests for vector search caching."""

import importlib.util
import sys
from pathlib import Path
import types
import pytest

# Prepare module for import with stubbed dependencies
module_path = Path(__file__).resolve().parents[1] / "retrieval" / "search.py"
spec = importlib.util.spec_from_file_location("search", module_path)
search = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = search

fake_redis_mod = types.ModuleType("redis.asyncio")
fake_redis_mod.ConnectionPool = object
fake_redis_mod.Redis = object
sys.modules["redis.asyncio"] = fake_redis_mod

fake_settings = types.ModuleType("settings")
fake_settings.get_settings = lambda: types.SimpleNamespace(redis_url="redis://")
old_settings = sys.modules.get("settings")
sys.modules["settings"] = fake_settings
spec.loader.exec_module(search)
if old_settings is None:
    del sys.modules["settings"]
else:
    sys.modules["settings"] = old_settings


class FakeRedis:
    """Minimal in-memory Redis replacement used in tests."""

    def __init__(self):
        self.store = {}

    async def get(self, key):
        val = self.store.get(key)
        return None if val is None else val

    async def setex(self, key, ttl, value):
        self.store[key] = value.encode() if isinstance(value, str) else value


class FakeQdrant:
    """Mock qdrant client capturing similarity calls."""

    def __init__(self):
        self.calls = 0

    def similarity(self, query, top, method):
        self.calls += 1

        class R:
            def __init__(self, id):
                self.id = id
                self.payload = None
                self.score = 1.0

        return [R("A")]


@pytest.mark.asyncio
async def test_vector_search_cache(monkeypatch):
    """Second call should be served from cache without hitting qdrant."""

    redis = FakeRedis()
    monkeypatch.setattr(search, "_get_redis", lambda: redis)
    qdrant = FakeQdrant()
    search.qdrant = qdrant

    first = await search.vector_search("hi", k=1)
    second = await search.vector_search("hi", k=1)

    assert [doc.id for doc in first] == ["A"]
    assert [doc.id for doc in second] == ["A"]
    assert qdrant.calls == 1
