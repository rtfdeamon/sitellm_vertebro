"""Ensure errors log session identifiers."""

import importlib.util
import sys
import types
import uuid
from pathlib import Path
import enum

import pytest


@pytest.mark.asyncio
async def test_session_id_logged_on_error(monkeypatch):
    logs = []

    # Structlog stub capturing logs
    def get_logger(*a, **k):
        return types.SimpleNamespace(
            info=lambda *args, **kw: logs.append(("info", args, kw)),
            warning=lambda *args, **kw: logs.append(("warning", args, kw)),
            error=lambda *args, **kw: logs.append(("error", args, kw)),
            exception=lambda *args, **kw: logs.append(("exception", args, kw)),
        )

    fake_structlog = types.ModuleType("structlog")
    fake_structlog.get_logger = get_logger
    monkeypatch.setitem(sys.modules, "structlog", fake_structlog)

    # Minimal FastAPI stubs
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

    # mongo and models stubs
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
        def __init__(self, session_id):
            self.session_id = session_id

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

    models_mod.RoleEnum = RoleEnum
    models_mod.LLMRequest = LLMRequest
    models_mod.LLMResponse = LLMResponse
    modules["models"] = models_mod

    for name, mod in modules.items():
        monkeypatch.setitem(sys.modules, name, mod)

    # Import api after stubbing dependencies
    module_path = Path(__file__).resolve().parents[1] / "api.py"
    spec = importlib.util.spec_from_file_location("api", module_path)
    api = importlib.util.module_from_spec(spec)
    sys.modules["api"] = api
    spec.loader.exec_module(api)

    # Dummy mongo to trigger NotFound
    class DummyMongo:
        async def get_context_preset(self, collection):
            yield types.SimpleNamespace(role=RoleEnum.user, text="preset")

        async def get_sessions(self, collection, session_id):
            raise NotFound
            yield  # pragma: no cover

    request = types.SimpleNamespace(
        state=types.SimpleNamespace(
            mongo=DummyMongo(),
            contexts_collection="ctx",
            context_presets_collection="preset",
            llm=types.SimpleNamespace(respond=lambda *a, **k: None),
        )
    )

    session = uuid.uuid4()
    llm_request = LLMRequest(session)

    with pytest.raises(HTTPException) as exc:
        await api.ask_llm(request, llm_request)

    assert exc.value.status_code == 404
    assert any(
        entry[2].get("session") == str(session) and entry[0] == "warning"
        for entry in logs
    )
