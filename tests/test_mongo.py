"""Tests for MongoDB helpers."""

import sys
import uuid
import pytest

# Ensure any test stubs for ``mongo`` are cleared before importing the real module.
sys.modules.pop("mongo", None)
from mongo import MongoClient


class _FakeGridFS:
    """Minimal GridFS stub returning a predefined id."""

    def __init__(self, f_id: uuid.UUID):
        self._id = f_id

    async def put(self, _file: bytes):  # pragma: no cover - simple stub
        return self._id


class _FakeCollection:
    def __init__(self):
        self.inserted = None

    async def insert_one(self, doc: dict):  # pragma: no cover - simple stub
        self.inserted = doc


class _FakeDB:
    def __init__(self, collection: _FakeCollection):
        self._collection = collection

    def __getitem__(self, _name: str) -> _FakeCollection:  # pragma: no cover
        return self._collection


@pytest.mark.asyncio
async def test_upload_document_returns_str() -> None:
    """``upload_document`` should return the file id as string."""

    f_id = uuid.uuid4()
    mc = MongoClient.__new__(MongoClient)
    mc.gridfs = _FakeGridFS(f_id)
    collection = _FakeCollection()
    mc.db = _FakeDB(collection)

    result = await MongoClient.upload_document(
        mc, "file.txt", b"data", "documents"
    )

    assert isinstance(result, str)
    assert result == str(f_id)
    assert collection.inserted["fileId"] == str(f_id)

