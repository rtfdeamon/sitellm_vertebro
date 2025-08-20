import pytest

from textnorm import rewrite_query
from backend import cache as cache_mod
from backend import llm_client


class FakeRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return None

    async def setex(self, key, ttl, value):
        self.store[key] = value


@pytest.mark.asyncio
async def test_rewrite_changes_text(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(cache_mod, "_get_redis", lambda: redis)

    async def fake_generate(prompt: str):
        yield "rewritten"

    monkeypatch.setattr(llm_client, "generate", fake_generate)

    original = "some query"
    rewritten = await rewrite_query(original)
    assert rewritten == "rewritten"
    assert rewritten != original
