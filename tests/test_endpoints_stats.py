"""Smoke tests for stats endpoints using patched dependencies."""

from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys

import pytest
from httpx import AsyncClient

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
APP_SPEC = importlib.util.spec_from_file_location("app_stats", APP_PATH)
app_module = importlib.util.module_from_spec(APP_SPEC)
sys.modules["app_stats"] = app_module
APP_SPEC.loader.exec_module(app_module)


class _FakeClient:
    def close(self):
        return None


class _FakeMongo:
    def __init__(self, *args, **kwargs):
        self.client = _FakeClient()
        self._stats = [
            {
                "ts": datetime(2024, 5, 1, 12, 0, tzinfo=timezone.utc),
                "date": datetime(2024, 5, 1, tzinfo=timezone.utc),
                "project": "demo",
                "channel": "api",
                "question": "hello",
                "response_chars": 42,
                "attachments": 1,
                "prompt_chars": 120,
                "session_id": "sess-1",
                "user_id": "user-1",
                "error": None,
            }
        ]

    async def ensure_indexes(self):
        return None

    async def list_projects(self):
        return []

    async def aggregate_request_stats(self, *, project=None, start=None, end=None, channel=None):
        return [
            {
                "date": "2024-05-01",
                "count": len(self._stats),
                "attachments": sum(s.get("attachments", 0) for s in self._stats),
                "response_chars": sum(s.get("response_chars", 0) for s in self._stats),
            }
        ]

    async def iter_request_stats(self, *, project=None, start=None, end=None, channel=None):
        for item in self._stats:
            yield item

    async def log_request_stat(self, **kwargs):
        return None


class _FakeQdrantClient:
    def __init__(self, *args, **kwargs):
        pass

    def close(self):
        return None


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setattr(app_module, "MongoClient", _FakeMongo, raising=False)
    monkeypatch.setattr(app_module, "QdrantClient", _FakeQdrantClient, raising=False)
    async with AsyncClient(app=app_module.app, base_url="http://test") as async_client:
        yield async_client


@pytest.mark.anyio
async def test_request_stats_summary(client):
    response = await client.get("/api/v1/admin/stats/requests")
    assert response.status_code == 200
    payload = response.json()
    assert payload["stats"][0]["count"] == 1


@pytest.mark.anyio
async def test_request_stats_export(client):
    response = await client.get("/api/v1/admin/stats/requests/export")
    assert response.status_code == 200
    body = response.text
    assert "timestamp" in body
    assert "demo" in body
