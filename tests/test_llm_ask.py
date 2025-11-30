"""Test /api/v1/llm/ask endpoint to ensure caching doesn't raise errors."""

import importlib.util
import json
import sys
import types
import uuid
from pathlib import Path

import pytest

if sys.version_info < (3, 10):  # pragma: no cover - tooling compatibility
    pytest.skip("LLM API tests require Python 3.10+ for modern typing syntax", allow_module_level=True)

from packages import backend.cache as cache


class FakeRedis:
    """Simple in-memory Redis replacement."""

    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def setex(self, key, ttl, value):
        self.store[key] = value


@pytest.mark.asyncio
async def test_ask_llm(monkeypatch):
    """Calling the ask endpoint twice should use cache without AttributeError."""
    modules: dict[str, types.ModuleType] = {}

    mongo = types.ModuleType("mongo")

    class NotFound(Exception):
        pass

    class DummyMongoClient:
        ...

    mongo.NotFound = NotFound
    mongo.MongoClient = DummyMongoClient
    modules["mongo"] = mongo

    import importlib

    models_mod = importlib.import_module("models")
    modules["models"] = models_mod

    for name, mod in modules.items():
        monkeypatch.setitem(sys.modules, name, mod)

    qdrant_stub = types.ModuleType("qdrant_client")
    qdrant_stub.QdrantClient = object
    monkeypatch.setitem(sys.modules, "qdrant_client", qdrant_stub)

    settings_stub = types.ModuleType("settings")
    settings_stub.MongoSettings = lambda: types.SimpleNamespace(
        host="localhost",
        port=27017,
        username=None,
        password=None,
        database="testdb",
        auth="admin",
        documents="documents",
    )
    settings_stub.get_settings = lambda: types.SimpleNamespace(
        redis_url="redis://",
        project_name=None,
        domain=None,
        debug=False,
    )
    settings_stub.settings = types.SimpleNamespace(
        use_gpu=False,
        llm_model="stub",
        project_name=None,
        domain=None,
        debug=False,
    )
    monkeypatch.setitem(sys.modules, "settings", settings_stub)

    eval_stub = types.ModuleType("eval_type_backport")
    import typing as _typing

    def _eval_type_backport(value, globalns=None, localns=None, type_params=None):
        if hasattr(value, "__forward_arg__"):
            expr = value.__forward_arg__.replace(" ", "")
            if expr == "str|None":
                return _typing.Optional[str]
            return _typing.Any
        return _typing.Any

    eval_stub.eval_type_backport = _eval_type_backport
    monkeypatch.setitem(sys.modules, "eval_type_backport", eval_stub)

    module_path = Path(__file__).resolve().parents[1] / "api.py"
    spec = importlib.util.spec_from_file_location("api", module_path)
    api = importlib.util.module_from_spec(spec)
    sys.modules["api"] = api
    spec.loader.exec_module(api)

    redis = FakeRedis()
    monkeypatch.setattr(cache, "_get_redis", lambda: redis)

    async def fake_generate(prompt: str, *, model: str | None = None):
        yield "answer"

    monkeypatch.setattr("backend.llm_client.generate", fake_generate)

    class DummyMongo:
        async def get_context_preset(self, collection):
            yield types.SimpleNamespace(role=models_mod.RoleEnum.user, text="preset")

        async def get_sessions(self, collection, session_id):
            yield types.SimpleNamespace(role=models_mod.RoleEnum.user, text="question")

        async def get_project(self, project_name):
            return None

        async def upsert_project(self, project):
            return project

        async def log_request_stat(self, **kwargs):
            return None

        async def get_knowledge_priority(self, project):
            return []

        async def search_qa_pairs(self, question, project, limit):
            return []

    mongo_instance = DummyMongo()
    request = types.SimpleNamespace(
        state=types.SimpleNamespace(
            mongo=mongo_instance,
            contexts_collection="ctx",
            context_presets_collection="preset",
        ),
        query_params={},
        app=types.SimpleNamespace(state=types.SimpleNamespace(mongo=mongo_instance)),
    )

    llm_request = models_mod.LLMRequest(sessionId=uuid.uuid4())

    resp1 = await api.ask_llm(request, llm_request)
    payload1 = json.loads(resp1.body)
    assert payload1["text"] == "answer"
    assert payload1["attachments"] == []

    resp2 = await api.ask_llm(request, llm_request)
    payload2 = json.loads(resp2.body)
    assert payload2["text"] == "answer"
    assert payload2["attachments"] == []
