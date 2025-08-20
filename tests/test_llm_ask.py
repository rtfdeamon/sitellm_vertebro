"""Test /api/v1/llm/ask endpoint to ensure caching doesn't raise errors."""

import importlib.util
import sys
import types
import uuid
from pathlib import Path

import pytest

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
        def __init__(self, text):
            self.text = text

        def model_dump(self):
            return {"text": self.text}

    models_mod.RoleEnum = RoleEnum
    models_mod.LLMRequest = LLMRequest
    models_mod.LLMResponse = LLMResponse
    modules["models"] = models_mod

    for name, mod in modules.items():
        monkeypatch.setitem(sys.modules, name, mod)

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

    resp2 = await api.ask_llm(request, llm_request)
    assert resp2.content["text"] == "answer"
    assert request.state.llm.calls == 1
