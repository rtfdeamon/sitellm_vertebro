"""Ensure errors log session identifiers."""

import importlib.util
import sys
import types
import uuid
from pathlib import Path

from fastapi import HTTPException

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

    modules: dict[str, types.ModuleType] = {}

    # mongo and models stubs
    mongo = types.ModuleType("mongo")

    class NotFound(Exception):
        pass

    class DummyMongoClient:  # minimal placeholder for import wiring
        ...

    mongo.NotFound = NotFound
    mongo.MongoClient = DummyMongoClient
    modules["mongo"] = mongo

    import importlib

    models_mod = importlib.import_module("models")
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
            yield types.SimpleNamespace(role=models_mod.RoleEnum.user, text="preset")

        async def get_sessions(self, collection, session_id):
            raise NotFound
            yield  # pragma: no cover

    mongo_instance = DummyMongo()
    request = types.SimpleNamespace(
        state=types.SimpleNamespace(
            mongo=mongo_instance,
            contexts_collection="ctx",
            context_presets_collection="preset",
            llm=types.SimpleNamespace(respond=lambda *a, **k: None),
        ),
        app=types.SimpleNamespace(state=types.SimpleNamespace(mongo=mongo_instance)),
    )

    session = uuid.uuid4()
    llm_request = models_mod.LLMRequest(sessionId=session)

    with pytest.raises(HTTPException) as exc:
        await api.ask_llm(request, llm_request)

    assert exc.value.status_code == 404
    assert any(
        entry[2].get("session") == str(session) and entry[0] == "warning"
        for entry in logs
    )
