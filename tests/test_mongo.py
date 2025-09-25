"""Tests for MongoDB helpers."""

import sys
import types
import uuid
import pytest
from bson import ObjectId

# Ensure any test stubs for ``mongo`` are cleared before importing the real module.
sys.modules.pop("mongo", None)
from mongo import MongoClient
from models import Project


class _FakeGridFS:
    """Minimal GridFS stub returning a predefined id."""

    def __init__(self, f_id: ObjectId):
        self._id = f_id
        self.deleted: ObjectId | None = None

    async def put(self, _file: bytes):  # pragma: no cover - simple stub
        return self._id

    async def delete(self, file_id: ObjectId):  # pragma: no cover - simple stub
        self.deleted = file_id


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
