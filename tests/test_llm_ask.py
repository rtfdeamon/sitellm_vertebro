"""Test /api/v1/llm/ask endpoint to ensure caching doesn't raise errors."""

import importlib.util
import sys
import types
import uuid
from pathlib import Path

import pytest

if sys.version_info < (3, 10):  # pragma: no cover - tooling compatibility
    pytest.skip("LLM API tests require Python 3.10+ for modern typing syntax", allow_module_level=True)

import backend.cache as cache


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
    import enum
    fastapi = types.ModuleType("fastapi")

    class Request:
        def __init__(self, state):
            self.state = state

    class HTTPException(Exception):
        def __init__(self, status_code, detail):
            self.status_code = status_code
            self.detail = detail

    class APIRouter:
        def __init__(self, *a, **k):
            pass

        def post(self, *a, **k):
            def decorator(func):
                return func

            return decorator

        def get(self, *a, **k):
            def decorator(func):
                return func

            return decorator

    fastapi.APIRouter = APIRouter
    fastapi.Request = Request
    fastapi.HTTPException = HTTPException
    fastapi.UploadFile = object
    fastapi.File = lambda *a, **k: None
    fastapi.Form = lambda *a, **k: None
    class BackgroundTasks:
        def add_task(self, *a, **k):
            pass
    fastapi.BackgroundTasks = BackgroundTasks

    responses = types.ModuleType("fastapi.responses")

    class ORJSONResponse:
        def __init__(self, content, *a, **k):
            self.content = content

    class StreamingResponse:
        def __init__(self, *a, **k):
            pass

    responses.ORJSONResponse = ORJSONResponse
    responses.StreamingResponse = StreamingResponse
    fastapi.responses = responses

    modules = {
        "fastapi": fastapi,
        "fastapi.responses": responses,
    }

    mongo = types.ModuleType("mongo")

    class NotFound(Exception):
        pass

    mongo.NotFound = NotFound
    modules["mongo"] = mongo

    models_mod = types.ModuleType("models")

    class RoleEnum(str, enum.Enum):
        assistant = "assistant"
        user = "user"

    class LLMRequest:
        def __init__(self, sessionId):
            self.session_id = sessionId

    class LLMResponse:
        def __init__(self, text, attachments=None, emotions_enabled=None):
            self.text = text
            self.attachments = attachments or []
            self.emotions_enabled = emotions_enabled

        def model_dump(self):
            data = {"text": self.text, "attachments": self.attachments}
            if self.emotions_enabled is not None:
                data["emotions_enabled"] = self.emotions_enabled
            return data

    class Document:
        def __init__(self, **data):
            self.__dict__.update(data)

        def model_dump(self):
            return self.__dict__.copy()

    class Project:
        def __init__(self, **data):
            self.__dict__.update(data)

    models_mod.RoleEnum = RoleEnum
    models_mod.LLMRequest = LLMRequest
    models_mod.LLMResponse = LLMResponse
    models_mod.Document = Document
    models_mod.Project = Project
    models_mod.Attachment = lambda **data: data
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

    class DummyLLM:
        def __init__(self):
            self.calls = 0

        @cache.cache_response
        async def respond(self, session, prompt):
            self.calls += 1
            return [types.SimpleNamespace(speaker="assistant", text="answer")]

    class DummyMongo:
        async def get_context_preset(self, collection):
            yield types.SimpleNamespace(role=RoleEnum.user, text="preset")

        async def get_sessions(self, collection, session_id):
            yield types.SimpleNamespace(role=RoleEnum.user, text="question")

    request = types.SimpleNamespace(
        state=types.SimpleNamespace(
            llm=DummyLLM(),
            mongo=DummyMongo(),
            contexts_collection="ctx",
            context_presets_collection="preset",
        )
    )

    llm_request = LLMRequest(sessionId=uuid.uuid4())

    resp1 = await api.ask_llm(request, llm_request)
    assert resp1.content["text"] == "answer"
    assert resp1.content["attachments"] == []

    resp2 = await api.ask_llm(request, llm_request)
    assert resp2.content["text"] == "answer"
    assert resp2.content["attachments"] == []
    assert request.state.llm.calls == 1
