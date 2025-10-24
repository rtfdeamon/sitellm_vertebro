"""Integration-style tests for the reading endpoint and service."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

from models import ReadingPage


@pytest.fixture()
def api_module(monkeypatch):
    """Load the API module with light stubs so we can exercise the endpoint."""

    # Stub ``mongo`` module with minimal client/exception.
    mongo_mod = types.ModuleType("mongo")

    class NotFound(Exception):
        pass

    class DummyMongoClient:
        ...

    mongo_mod.MongoClient = DummyMongoClient
    mongo_mod.NotFound = NotFound
    monkeypatch.setitem(sys.modules, "mongo", mongo_mod)

    # Backend package stubs
    backend_pkg = types.ModuleType("backend")
    backend_pkg.__path__ = []
    monkeypatch.setitem(sys.modules, "backend", backend_pkg)

    backend_cache = types.ModuleType("backend.cache")
    backend_cache._get_redis = lambda: None
    monkeypatch.setitem(sys.modules, "backend.cache", backend_cache)

    backend_settings = types.ModuleType("backend.settings")
    backend_settings.settings = types.SimpleNamespace(
        ollama_base_url=None,
        mongo_uri="mongodb://localhost:27017",
    )
    backend_settings.get_settings = lambda: backend_settings.settings
    monkeypatch.setitem(sys.modules, "backend.settings", backend_settings)

    llm_client = types.ModuleType("backend.llm_client")
    llm_client.MODEL_NAME = "stub"
    llm_client.DEVICE = "cpu"
    llm_client.OLLAMA_BASE = None

    async def _generate(prompt: str, *, model: str | None = None):
        yield ""

    llm_client.generate = _generate
    monkeypatch.setitem(sys.modules, "backend.llm_client", llm_client)

    # Settings module used across the API.
    settings_mod = types.ModuleType("settings")

    class DummyMongoSettings:
        def __init__(self):
            self.host = "localhost"
            self.port = 27017
            self.username = None
            self.password = None
            self.database = "testdb"
            self.auth = "admin"
            self.contexts = "contexts"
            self.presets = "presets"
            self.documents = "documents"
            self.voice_samples = "voiceSamples"
            self.voice_jobs = "voiceJobs"

    settings_mod.MongoSettings = DummyMongoSettings
    settings_mod.get_settings = lambda: types.SimpleNamespace(
        redis_url="redis://",
        project_name=None,
        domain=None,
    )
    settings_mod.settings = types.SimpleNamespace(
        use_gpu=False,
        llm_model="stub",
        project_name=None,
        domain=None,
        debug=False,
    )
    monkeypatch.setitem(sys.modules, "settings", settings_mod)

    # Worker stub to satisfy imports.
    worker_mod = types.ModuleType("worker")
    worker_mod.voice_train_model = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, "worker", worker_mod)

    # Qdrant client is referenced but not exercised in these tests.
    qdrant_mod = types.ModuleType("qdrant_client")
    qdrant_mod.QdrantClient = object
    monkeypatch.setitem(sys.modules, "qdrant_client", qdrant_mod)

    module_path = Path(__file__).resolve().parents[1] / "api.py"
    spec = importlib.util.spec_from_file_location("api_reading_under_test", module_path)
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    # Ensure Pydantic models referencing each other are initialised.
    api.ReadingPagesResponse.model_rebuild(_types_namespace={"ReadingPage": ReadingPage})
    return api


@pytest.mark.asyncio
async def test_reading_pages_endpoint_strips_html(monkeypatch, api_module):
    """Ensure the /reading/pages endpoint serialises data with the service."""

    class FakeMongo:
        async def get_reading_pages(self, collection, project_name, limit, offset, url=None):
            return [
                ReadingPage(
                    url="https://example.com/chapter-1",
                    order=1,
                    title="Chapter 1",
                    text="Some detailed content for the page.",
                    html="<p>HTML body</p>",
                )
            ]

        async def count_reading_pages(self, collection, project_name):
            return 1

    mongo = FakeMongo()
    request = types.SimpleNamespace(
        state=types.SimpleNamespace(mongo=mongo),
        app=types.SimpleNamespace(state=types.SimpleNamespace(mongo=mongo)),
    )

    response = await api_module.reading_pages(
        request,
        project="demo",
        limit=2,
        offset=0,
        url=None,
        include_html=False,
    )
    payload = json.loads(response.body)

    assert payload == {
        "pages": [
            {
                "url": "https://example.com/chapter-1",
                "order": 1,
                "title": "Chapter 1",
                "project": None,
                "fileId": None,
                "text": "Some detailed content for the page.",
                "html": None,
                "segments": [],
                "images": [],
                "segmentCount": None,
                "imageCount": None,
                "updatedAt": None,
            }
        ],
        "total": 1,
        "limit": 2,
        "offset": 0,
        "has_more": False,
    }


def test_collect_reading_items_limits_to_three(api_module):
    """Collecting reading snippets should truncate to at most three entries."""

    snippets = []
    for idx in range(5):
        snippets.append(
            {
                "id": f"s{idx}",
                "name": f"Doc {idx}",
                "source": "mongo",
                "reading": {
                    "pages": [{"order": 1, "title": f"Chapter {idx}"}],
                    "project": "demo",
                },
            }
        )

    items = api_module.reading_service.collect_reading_items(snippets)
    assert len(items) == 3
    assert [item["id"] for item in items] == ["s0", "s1", "s2"]
