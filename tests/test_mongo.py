"""Tests for MongoDB helpers."""

import sys
import types
import uuid
import pytest
from bson import ObjectId

# Ensure any test stubs for ``mongo`` are cleared before importing the real module.
sys.modules.pop("mongo", None)
from packages.core.mongo import MongoClient
from packages.core.models import Project, OllamaServer


class _FakeGridFS:
    """Minimal GridFS stub returning a predefined id."""

    def __init__(self, f_id: ObjectId):
        self._id = f_id
        self.deleted: ObjectId | None = None

    async def put(self, _file: bytes):  # pragma: no cover - simple stub
        return self._id

    async def delete(self, file_id: ObjectId):  # pragma: no cover - simple stub
        self.deleted = file_id

    async def upload_from_stream(self, filename: str, payload: bytes, metadata: dict | None = None):
        return self._id


class _FakeCollection:
    def __init__(self):
        self.inserted = None
        self.updated = None
        self.existing: dict | None = None

    async def insert_one(self, doc: dict):  # pragma: no cover - simple stub
        self.inserted = doc

    async def find_one(self, _filter: dict, _projection: dict | None = None):  # pragma: no cover
        return self.existing

    async def update_one(self, filter: dict, update: dict, upsert: bool = False):  # pragma: no cover
        self.updated = (filter, update, upsert)


class _FakeDB:
    def __init__(self, collection: _FakeCollection):
        self._collection = collection

    def __getitem__(self, _name: str) -> _FakeCollection:  # pragma: no cover
        return self._collection


class _AsyncCursor:
    def __init__(self, docs):
        self._docs = list(docs)
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._docs):
            raise StopAsyncIteration
        value = self._docs[self._index]
        self._index += 1
        return value


class _OllamaCollection:
    def __init__(self):
        self.items: dict[str, dict] = {}

    def find(self, _filter, _projection=None):
        return _AsyncCursor([item.copy() for item in self.items.values()])

    async def find_one(self, filter, _projection=None):
        name = filter.get('name')
        if name is None:
            return None
        item = self.items.get(name)
        return item.copy() if item else None

    async def update_one(self, filter, update, upsert=False):
        name = filter.get('name')
        if name is None:
            raise ValueError('name is required')
        payload = update.get('$set', {}) if isinstance(update, dict) else {}
        existing = self.items.get(name, {}).copy()
        existing.update(payload)
        self.items[name] = existing

    async def delete_one(self, filter):
        name = filter.get('name')
        existed = self.items.pop(name, None)

        class _Result:
            deleted_count = 1 if existed else 0

        return _Result()


class _OllamaDB:
    def __init__(self, collection: _OllamaCollection):
        self._collection = collection

    def __getitem__(self, name: str):
        if name == 'ollama_servers':
            return self._collection
        raise KeyError(name)


@pytest.mark.asyncio
async def test_upload_document_returns_str() -> None:
    """``upload_document`` should return the file id as string."""

    f_id = ObjectId()
    mc = MongoClient.__new__(MongoClient)
    mc.gridfs = _FakeGridFS(f_id)
    collection = _FakeCollection()
    mc.db = _FakeDB(collection)

    result = await MongoClient.upload_document(
        mc, "file.txt", b"data", "documents", project="demo"
    )

    assert isinstance(result, str)
    assert result == str(f_id)
    assert collection.inserted["fileId"] == str(f_id)
    assert collection.inserted["project"] == "demo"
    assert collection.inserted["size_bytes"] == len(b"data")


@pytest.mark.asyncio
async def test_upsert_text_document_sets_domain_and_description() -> None:
    f_id = ObjectId()
    mc = MongoClient.__new__(MongoClient)
    mc.gridfs = _FakeGridFS(f_id)
    collection = _FakeCollection()
    mc.db = _FakeDB(collection)
    mc.db._collection.existing = None

    file_id = await MongoClient.upsert_text_document(
        mc,
        name="note.txt",
        content="hello world",
        documents_collection="documents",
        description="test",
        project="demo",
        domain="example.com",
        url="https://example.com/doc",
    )

    assert file_id == str(f_id)
    assert collection.updated is not None
    filter_doc, update_doc, upsert_flag = collection.updated
    assert filter_doc == {"name": "note.txt", "project": "demo"}
    assert upsert_flag is True
    stored = update_doc["$set"]
    assert stored["domain"] == "example.com"
    assert stored["project"] == "demo"
    assert stored["description"] == "test"
    assert stored["content_type"] == "text/plain"
    assert stored["url"] == "https://example.com/doc"
    assert "ts" in stored
    assert stored["size_bytes"] == len("hello world".encode("utf-8"))


@pytest.mark.asyncio
async def test_upsert_project_merges_existing(monkeypatch) -> None:
    mc = MongoClient.__new__(MongoClient)
    collection = _FakeCollection()

    mc.projects_collection = "projects"

    class _FakeProjects:
        def __init__(self):
            self.updated = None
            self.stored = {
                "name": "demo",
                "domain": "example.com",
                "title": "Old",
                "telegram_token": "oldtoken",
                "telegram_auto_start": True,
                "widget_url": "https://old.example/widget",
            }

        async def update_one(self, filter, update, upsert=False):
            self.updated = (filter, update, upsert)
            if isinstance(update, dict) and "$set" in update:
                payload = update["$set"]
            else:
                payload = {}
            merged = self.stored.copy()
            merged.update(payload)
            self.stored = merged

        async def find_one(self, filter, projection=None):
            return self.stored

    projects = _FakeProjects()

    class _FakeDB:
        def __getitem__(self, name):
            if name == "projects":
                return projects
            raise KeyError(name)

    mc.db = _FakeDB()

    project = Project(
        name="demo",
        domain="example.com",
        title="New",
        telegram_token="newtoken",
        telegram_auto_start=False,
        widget_url="https://demo.example/widget",
    )
    result = await MongoClient.upsert_project(mc, project)

    assert result.name == "demo"
    assert projects.updated is not None
    filter_doc, update_doc, upsert_flag = projects.updated
    assert filter_doc == {"name": "demo"}
    assert upsert_flag is True
    stored = update_doc["$set"]
    assert stored["telegram_token"] == "newtoken"
    assert stored["telegram_auto_start"] is False
    assert stored["widget_url"] == "https://demo.example/widget"
    assert result.telegram_token == "newtoken"
    assert result.telegram_auto_start is False
    assert result.widget_url == "https://demo.example/widget"
    assert result.llm_voice_enabled is True


def test_project_from_doc_trims_optional_fields() -> None:
    mc = MongoClient.__new__(MongoClient)
    raw = {
        "name": " Demo ",
        "telegram_token": " token123 ",
        "widget_url": " https://demo.example/widget ",
    }
    project = MongoClient._project_from_doc(mc, raw)
    assert project is not None
    assert project.name == "demo"
    assert project.telegram_token == "token123"
    assert project.widget_url == "https://demo.example/widget"
    assert project.llm_emotions_enabled is True
    assert project.llm_voice_enabled is True


@pytest.mark.asyncio
async def test_ollama_server_crud() -> None:
    mc = MongoClient.__new__(MongoClient)
    collection = _OllamaCollection()
    mc.ollama_servers_collection = 'ollama_servers'
    mc.db = _OllamaDB(collection)

    server = OllamaServer(name='primary', base_url='http://localhost:11434', enabled=True)
    stored = await MongoClient.upsert_ollama_server(mc, server)
    assert stored.name == 'primary'
    assert stored.base_url == 'http://localhost:11434'
    assert stored.enabled is True

    servers = await MongoClient.list_ollama_servers(mc)
    assert len(servers) == 1
    assert servers[0].name == 'primary'

    await MongoClient.update_ollama_server_stats(
        mc,
        'primary',
        avg_latency_ms=2200.0,
        requests_last_hour=5,
        total_duration_ms=11000.0,
    )
    updated = await MongoClient.list_ollama_servers(mc)
    assert updated[0].stats["avg_latency_ms"] == 2200.0
    assert updated[0].stats["requests_last_hour"] == 5

    deleted = await MongoClient.delete_ollama_server(mc, 'primary')
    assert deleted is True
    assert await MongoClient.list_ollama_servers(mc) == []
