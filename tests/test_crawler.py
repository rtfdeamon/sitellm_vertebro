from __future__ import annotations

import sys
import types


pymongo_stub = types.ModuleType("pymongo")
pymongo_stub.MongoClient = object  # type: ignore[attr-defined]
pymongo_stub.UpdateOne = object  # type: ignore[attr-defined]
sys.modules.setdefault("pymongo", pymongo_stub)

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

from crawler import run_crawl


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
