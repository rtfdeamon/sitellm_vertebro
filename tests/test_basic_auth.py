import base64
import hashlib
import importlib.util
import sys
import types
from pathlib import Path

import pytest


def _build_client(monkeypatch, *, admin_password: str):
    monkeypatch.delitem(sys.modules, "fastapi", raising=False)
    monkeypatch.delitem(sys.modules, "fastapi.testclient", raising=False)
    monkeypatch.delitem(sys.modules, "app", raising=False)

    from fastapi import APIRouter
    from fastapi.testclient import TestClient
    from starlette.middleware.base import BaseHTTPMiddleware

    monkeypatch.setitem(
        sys.modules,
        "observability.logging",
        types.SimpleNamespace(
            configure_logging=lambda: None,
            get_recent_logs=lambda *a, **k: [],
        ),
    )

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
        reading_router=APIRouter(),
        voice_router=APIRouter(),
    )
    monkeypatch.setitem(sys.modules, "api", api_mod)

    class DummyMongoClient:
        def __init__(self, *a, **k):
            class _Client:
                async def close(self):
                    pass

            self.client = _Client()

        async def ensure_indexes(self):
            return None

        async def get_project_by_admin_username(self, username):
            return None

    monkeypatch.setitem(sys.modules, "mongo", types.SimpleNamespace(MongoClient=DummyMongoClient, NotFound=Exception))

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
            documents = "documents"

        class redis:
            vector = ""
            host = ""
            port = 0
            password = ""
            secure = False

    class DummyMongoSettings:
        host = ""
        port = 0
        username = ""
        password = ""
        database = ""
        auth = ""
        contexts = "ctx"
        presets = "preset"
        documents = "documents"
        vectors = "vectors"

    monkeypatch.setitem(
        sys.modules,
        "settings",
        types.SimpleNamespace(Settings=DummySettings, MongoSettings=DummyMongoSettings),
    )
    monkeypatch.setitem(sys.modules, "core.status", types.SimpleNamespace(status_dict=lambda: {}))
    monkeypatch.setitem(
        sys.modules,
        "core.build",
        types.SimpleNamespace(get_build_info=lambda: {}),
    )
    monkeypatch.setitem(
        sys.modules,
        "backend.settings",
        types.SimpleNamespace(settings=types.SimpleNamespace(qdrant_url="", mongo_uri="", redis_url="")),
    )
    monkeypatch.setitem(
        sys.modules,
        "backend.cache",
        types.SimpleNamespace(_get_redis=lambda *a, **k: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "backend.llm_client",
        types.SimpleNamespace(generate=lambda *a, **k: iter(())),
    )
    monkeypatch.setitem(
        sys.modules,
        "backend.ollama",
        types.SimpleNamespace(
            list_installed_models=lambda *a, **k: [],
            popular_models_with_size=lambda *a, **k: [],
            ollama_available=lambda *a, **k: False,
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "backend.ollama_cluster",
        types.SimpleNamespace(
            init_cluster=lambda *a, **k: types.SimpleNamespace(),
            reload_cluster=lambda *a, **k: None,
            get_cluster_manager=lambda *a, **k: None,
            shutdown_cluster=lambda *a, **k: None,
        ),
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
            from_url=lambda *a, **k: types.SimpleNamespace(ping=lambda: True, close=lambda: None)
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "requests",
        types.SimpleNamespace(get=lambda *a, **k: types.SimpleNamespace(ok=True)),
    )
    monkeypatch.setitem(sys.modules, "gridfs", types.SimpleNamespace(GridFS=object))
    monkeypatch.setitem(
        sys.modules,
        "knowledge.summary",
        types.SimpleNamespace(generate_document_summary=lambda *a, **k: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "knowledge.tasks",
        types.SimpleNamespace(queue_auto_description=lambda *a, **k: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "knowledge.text",
        types.SimpleNamespace(
            extract_doc_text=lambda *a, **k: "",
            extract_docx_text=lambda *a, **k: "",
            extract_pdf_text=lambda *a, **k: "",
            extract_best_effort_text=lambda *a, **k: "",
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "integrations.bitrix",
        types.SimpleNamespace(BitrixError=Exception, call_bitrix_webhook=lambda *a, **k: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "max_bot.config",
        types.SimpleNamespace(get_settings=lambda: types.SimpleNamespace()),
    )
    monkeypatch.setitem(
        sys.modules,
        "vk_bot.config",
        types.SimpleNamespace(get_settings=lambda: types.SimpleNamespace()),
    )
    monkeypatch.setitem(
        sys.modules,
        "openpyxl",
        types.SimpleNamespace(load_workbook=lambda *a, **k: None),
    )
    knowledge_pkg = types.ModuleType("knowledge")
    knowledge_pkg.summary = sys.modules["knowledge.summary"]
    knowledge_pkg.tasks = sys.modules["knowledge.tasks"]
    knowledge_pkg.text = sys.modules["knowledge.text"]
    monkeypatch.setitem(sys.modules, "knowledge", knowledge_pkg)

    retrieval_pkg = types.ModuleType("retrieval")
    search_mod = types.SimpleNamespace(qdrant=None)
    retrieval_pkg.search = search_mod
    monkeypatch.setitem(sys.modules, "retrieval", retrieval_pkg)
    monkeypatch.setitem(sys.modules, "retrieval.search", search_mod)

    monkeypatch.setitem(
        sys.modules,
        "uvicorn.middleware.proxy_headers",
        types.SimpleNamespace(ProxyHeadersMiddleware=types.SimpleNamespace),
    )

    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", admin_password)

    spec = importlib.util.spec_from_file_location(
        "app_real", Path(__file__).resolve().parents[1] / "app.py"
    )
    app_module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = app_module
    spec.loader.exec_module(app_module)
    return TestClient(app_module.app)


@pytest.fixture()
def client(monkeypatch):
    return _build_client(monkeypatch, admin_password=hashlib.sha256(b"admin").hexdigest())


def test_admin_requires_auth(client):
    response = client.get("/admin")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Basic"


def test_admin_with_basic_auth(client):
    token = base64.b64encode(b"admin:admin").decode()
    response = client.get("/admin", headers={"Authorization": f"Basic {token}"})
    assert response.status_code == 200


def test_admin_plaintext_env_password(monkeypatch):
    test_client = _build_client(monkeypatch, admin_password="123456")
    token = base64.b64encode(b"admin:123456").decode()
    response = test_client.get("/admin", headers={"Authorization": f"Basic {token}"})
    assert response.status_code == 200
