from __future__ import annotations

import sys
import types


pymongo_stub = types.ModuleType("pymongo")
pymongo_stub.MongoClient = object  # type: ignore[attr-defined]
pymongo_stub.UpdateOne = object  # type: ignore[attr-defined]
pymongo_stub.ASCENDING = 1  # type: ignore[attr-defined]
sys.modules.setdefault("pymongo", pymongo_stub)
pymongo_errors_stub = types.ModuleType("pymongo.errors")
pymongo_errors_stub.PyMongoError = Exception  # type: ignore[attr-defined]
pymongo_errors_stub.InvalidOperation = Exception  # type: ignore[attr-defined]
pymongo_errors_stub.ConfigurationError = Exception  # type: ignore[attr-defined]
sys.modules.setdefault("pymongo.errors", pymongo_errors_stub)
pymongo_common_stub = types.ModuleType("pymongo.common")
pymongo_common_stub.MAX_MESSAGE_SIZE = 16 * 1024 * 1024  # type: ignore[attr-defined]
sys.modules.setdefault("pymongo.common", pymongo_common_stub)

redis_stub = types.ModuleType("redis")

class _Redis:
    def __init__(self, *args, **kwargs):
        pass


redis_stub.Redis = _Redis  # type: ignore[attr-defined]
sys.modules.setdefault("redis", redis_stub)

obs_pkg = types.ModuleType("observability")
obs_logging = types.ModuleType("observability.logging")
obs_logging.configure_logging = lambda: None
obs_pkg.logging = obs_logging
sys.modules.setdefault("observability", obs_pkg)
sys.modules.setdefault("observability.logging", obs_logging)

gridfs_stub = types.ModuleType("gridfs")
gridfs_stub.GridFS = object  # type: ignore[attr-defined]
sys.modules.setdefault("gridfs", gridfs_stub)

settings_stub = types.ModuleType("settings")


class _MongoSettings:
    def __init__(self) -> None:
        self.host = "localhost"
        self.port = 27017
        self.username = None
        self.password = None
        self.database = "testdb"
        self.auth = "admin"
        self.documents = "documents"


settings_stub.MongoSettings = _MongoSettings  # type: ignore[attr-defined]
sys.modules.setdefault("settings", settings_stub)

from packages.crawler import run_crawl


class _BinaryResponse:
    headers = {"content-type": "application/pdf"}
    content = b"%PDF-1.4"
    text = ""

    def raise_for_status(self) -> None:  # pragma: no cover - simple stub
        return None


def _fake_get(url: str, headers: dict, timeout: float) -> _BinaryResponse:
    return _BinaryResponse()


def test_fetch_converts_pdf(monkeypatch) -> None:
    monkeypatch.setattr(run_crawl.requests, "get", _fake_get)
    monkeypatch.setattr(run_crawl, "pdf_to_text", lambda data: "PDF TEXT")

    html, ctype = run_crawl.fetch("http://example.com/file.pdf")

    assert html == "PDF TEXT"
    assert ctype == "application/pdf"
