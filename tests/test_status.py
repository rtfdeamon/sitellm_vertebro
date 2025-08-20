import importlib
import sys
import types
import pytest


class DummyLogger:
    def __init__(self):
        self.warnings = []
        self.exceptions = []

    def warning(self, msg, **kw):
        self.warnings.append((msg, kw))

    def exception(self, msg, **kw):
        self.exceptions.append((msg, kw))


class RedisStub:
    def __init__(self, *a, **k):
        pass

    def get(self, key):
        return None


class MongoStub:
    def __init__(self, *a, **k):
        pass

    def __getitem__(self, name):
        class DB:
            def list_collection_names(self):
                return []

            def __getitem__(self, col):
                class Coll:
                    def estimated_document_count(self):
                        return 0

                return Coll()

        return DB()


class QdrantStub:
    def __init__(self, *a, **k):
        pass

    def get_collection(self, coll):
        class Info:
            vectors_count = 0

        return Info()


@pytest.mark.parametrize("service", ["redis", "mongo", "qdrant"])
def test_status_logs_when_service_unavailable(monkeypatch, service):
    monkeypatch.setenv("REDIS_HOST", "redis-test")
    monkeypatch.setenv("REDIS_PORT", "1234")
    monkeypatch.setenv("MONGO_URI", "mongodb://mongotest:27017")
    monkeypatch.setenv("MONGO_DB", "dbtest")
    monkeypatch.setenv("QDRANT_HOST", "qdranttest")
    monkeypatch.setenv("QDRANT_PORT", "4321")
    monkeypatch.setenv("QDRANT_COLLECTION", "colltest")

    fake_pymongo = types.ModuleType("pymongo")
    fake_pymongo.MongoClient = object
    sys.modules["pymongo"] = fake_pymongo

    fake_redis_mod = types.ModuleType("redis")
    fake_redis_mod.Redis = object
    sys.modules["redis"] = fake_redis_mod

    fake_qdrant_mod = types.ModuleType("qdrant_client")
    fake_qdrant_mod.QdrantClient = object
    sys.modules["qdrant_client"] = fake_qdrant_mod

    import core.status as status
    importlib.reload(status)

    dummy = DummyLogger()
    monkeypatch.setattr(status, "logger", dummy)

    if service == "redis":
        class FailRedis:
            def __init__(self, *a, **k):
                raise RuntimeError("redis down")

        monkeypatch.setattr(status, "Redis", FailRedis)
        monkeypatch.setattr(status, "MongoClient", MongoStub)
        monkeypatch.setattr(status, "QdrantClient", QdrantStub)
    elif service == "mongo":
        monkeypatch.setattr(status, "Redis", RedisStub)
        class FailMongo:
            def __init__(self, *a, **k):
                raise RuntimeError("mongo down")

        monkeypatch.setattr(status, "MongoClient", FailMongo)
        monkeypatch.setattr(status, "QdrantClient", QdrantStub)
    else:  # qdrant
        monkeypatch.setattr(status, "Redis", RedisStub)
        monkeypatch.setattr(status, "MongoClient", MongoStub)
        class FailQdrant:
            def __init__(self, *a, **k):
                raise RuntimeError("qdrant down")

        monkeypatch.setattr(status, "QdrantClient", FailQdrant)

    result = status.status_dict()

    assert isinstance(result, dict)
    assert dummy.warnings or dummy.exceptions

    if service == "redis":
        kwargs = dummy.warnings[0][1]
        assert kwargs["host"] == "redis-test"
        assert kwargs["port"] == 1234
    elif service == "mongo":
        kwargs = dummy.warnings[0][1]
        assert kwargs["uri"] == "mongodb://mongotest:27017"
        assert kwargs["db"] == "dbtest"
    else:
        kwargs = dummy.warnings[0][1]
        assert kwargs["host"] == "qdranttest"
        assert kwargs["port"] == 4321
        assert kwargs["collection"] == "colltest"
