import base64
import importlib.util
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture()
def client(monkeypatch):
    # Remove test stubs for fastapi and app modules
    monkeypatch.delitem(sys.modules, "fastapi", raising=False)
    monkeypatch.delitem(sys.modules, "fastapi.testclient", raising=False)
    monkeypatch.delitem(sys.modules, "app", raising=False)

    from fastapi import APIRouter
    from fastapi.testclient import TestClient

    # Stub external dependencies required by app.py
    monkeypatch.setitem(
        sys.modules,
        "observability.logging",
        types.SimpleNamespace(configure_logging=lambda: None),
    )

    from starlette.middleware.base import BaseHTTPMiddleware

    class DummyMetricsMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            return await call_next(request)

    metrics_mod = types.SimpleNamespace(
        MetricsMiddleware=DummyMetricsMiddleware,
        metrics_app=object(),
    )
    monkeypatch.setitem(sys.modules, "observability.metrics", metrics_mod)

    api_mod = types.SimpleNamespace(
        llm_router=APIRouter(),
        crawler_router=APIRouter(),
    )
    monkeypatch.setitem(sys.modules, "api", api_mod)

    class DummyMongoClient:
        def __init__(self, *a, **k):
            class _Client:
                async def close(self):
                    pass
            self.client = _Client()

    monkeypatch.setitem(sys.modules, "mongo", types.SimpleNamespace(MongoClient=DummyMongoClient))

    class DummyDocumentsParser:
        def __init__(self, *a, **k):
            pass

    monkeypatch.setitem(sys.modules, "vectors", types.SimpleNamespace(DocumentsParser=DummyDocumentsParser))

    class DummyYaLLM:
        pass

    class DummyYaLLMEmbeddings:
        def get_embeddings_model(self):
            return None

    monkeypatch.setitem(
        sys.modules,
        "yallm",
        types.SimpleNamespace(YaLLM=DummyYaLLM, YaLLMEmbeddings=DummyYaLLMEmbeddings),
    )

    class DummySettings:
        debug = False

        class mongo:
            host = ""
            port = 0
            username = ""
            password = ""
            database = ""
            auth = None
            contexts = "ctx"
            presets = "preset"

        class redis:
            vector = ""
            host = ""
            port = 0
            password = ""
            secure = False

    monkeypatch.setitem(sys.modules, "settings", types.SimpleNamespace(Settings=DummySettings))
    monkeypatch.setitem(sys.modules, "core.status", types.SimpleNamespace(status_dict=lambda: {}))
    monkeypatch.setitem(
        sys.modules,
        "backend.settings",
        types.SimpleNamespace(settings=types.SimpleNamespace(qdrant_url="", mongo_uri="", redis_url="")),
    )
    monkeypatch.setitem(sys.modules, "pymongo", types.SimpleNamespace(MongoClient=object))

    class DummyQdrantClient:
        def __init__(self, *a, **k):
            pass

        def close(self):
            pass

    monkeypatch.setitem(
        sys.modules, "qdrant_client", types.SimpleNamespace(QdrantClient=DummyQdrantClient)
    )
    monkeypatch.setitem(
        sys.modules,
        "redis",
        types.SimpleNamespace(
            from_url=lambda *a, **k: types.SimpleNamespace(ping=lambda: True)
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "requests",
        types.SimpleNamespace(get=lambda *a, **k: types.SimpleNamespace(ok=True)),
    )

    retrieval_pkg = types.ModuleType("retrieval")
    search_mod = types.SimpleNamespace(qdrant=None)
    retrieval_pkg.search = search_mod
    monkeypatch.setitem(sys.modules, "retrieval", retrieval_pkg)
    monkeypatch.setitem(sys.modules, "retrieval.search", search_mod)

    spec = importlib.util.spec_from_file_location(
        "app_real", Path(__file__).resolve().parents[1] / "app.py"
    )
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)
    return TestClient(app_module.app)


def test_admin_requires_auth(client):
    response = client.get("/admin")
    assert response.status_code == 401


def test_admin_with_basic_auth(client):
    token = base64.b64encode(b"admin:admin").decode()
    response = client.get("/admin", headers={"Authorization": f"Basic {token}"})
    assert response.status_code == 200
