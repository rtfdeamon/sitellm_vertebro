"""Tests for :meth:`MongoClient.search_documents` caching behaviour."""

import importlib
import importlib.util
import sys
from pathlib import Path
import types

import pytest

module_path = Path(__file__).resolve().parents[1] / "mongo.py"
spec = importlib.util.spec_from_file_location("mongo", module_path)
mongo = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mongo
REAL_MODELS = importlib.import_module("models")

# Stub external dependencies required by ``mongo``.
fake_bson = types.ModuleType("bson")
fake_bson.ObjectId = type("ObjectId", (), {})
sys.modules["bson"] = fake_bson

try:
    import gridfs as real_gridfs  # type: ignore  # noqa: E402
except Exception:
    fake_gridfs = types.ModuleType("gridfs")
    fake_gridfs.AsyncGridFS = type("AsyncGridFS", (), {})
    fake_gridfs.GridFS = type("GridFS", (), {})
    sys.modules["gridfs"] = fake_gridfs
else:
    sys.modules["gridfs"] = real_gridfs

try:
    import pymongo as real_pymongo  # type: ignore  # noqa: E402
except Exception:
    fake_pymongo = types.ModuleType("pymongo")
    fake_pymongo.AsyncMongoClient = type("AsyncMongoClient", (), {})
    fake_pymongo.MongoClient = type("MongoClient", (), {})
    fake_pymongo.errors = types.SimpleNamespace(ConfigurationError=Exception)
    sys.modules["pymongo"] = fake_pymongo
    sys.modules.setdefault("pymongo.errors", fake_pymongo.errors)
else:
    sys.modules["pymongo"] = real_pymongo

# Minimal ``models`` module with ``Document`` dataclass replacement.
fake_models = types.ModuleType("models")

class Document:
    def __init__(self, name: str, description: str, fileId: str):
        self.name = name
        self.description = description
        self.fileId = fileId

    def model_dump(self, *, by_alias: bool = False):
        return {"name": self.name, "description": self.description, "fileId": self.fileId}

fake_models.ContextMessage = object
fake_models.ContextPreset = object
fake_models.Document = Document
class Project:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def model_dump(self):
        return self.__dict__.copy()

fake_models.Project = Project
fake_models.BackupJob = type("BackupJob", (), {})
fake_models.BackupOperation = type("BackupOperation", (), {})
fake_models.BackupSettings = type("BackupSettings", (), {})
fake_models.BackupStatus = type("BackupStatus", (), {})
fake_models.OllamaServer = type("OllamaServer", (), {})
fake_models.ReadingPage = type("ReadingPage", (), {})
fake_models.VoiceSample = type("VoiceSample", (), {})
fake_models.VoiceTrainingJob = type("VoiceTrainingJob", (), {})

class _VoiceTrainingStatus:
    queued = "queued"
    running = "running"
    failed = "failed"
    completed = "completed"


fake_models.VoiceTrainingStatus = _VoiceTrainingStatus
sys.modules["models"] = fake_models

spec.loader.exec_module(mongo)
sys.modules["models"] = REAL_MODELS


class FakeRedis:
    """Minimal in-memory Redis replacement."""

    def __init__(self):
        self.store: dict[str, bytes] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self.store[key] = value.encode()


class FakeCursor:
    """Async cursor returning predefined documents."""

    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, *args, **kwargs):  # noqa: D401 - match Motor API
        return self

    def limit(self, *args, **kwargs):
        return self

    def __aiter__(self):
        self._iter = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


class FakeCollection:
    def __init__(self, docs):
        self.docs = docs
        self.calls = 0

    def find(self, *args, **kwargs):
        self.calls += 1
        return FakeCursor(self.docs)


@pytest.mark.asyncio
async def test_search_documents_cache(monkeypatch):
    """Second search should be served from cache without hitting the DB."""
    redis = FakeRedis()
    monkeypatch.setattr(mongo, "_get_redis", lambda: redis)

    docs = [{"name": "doc", "description": "desc", "fileId": "1"}]
    collection = FakeCollection(docs)

    client = mongo.MongoClient.__new__(mongo.MongoClient)
    client.db = {"docs": collection}

    first = await mongo.MongoClient.search_documents(client, "docs", "hello")
    second = await mongo.MongoClient.search_documents(client, "docs", "hello")

    assert [d.name for d in first] == ["doc"]
    assert [d.name for d in second] == ["doc"]
    assert collection.calls == 1
