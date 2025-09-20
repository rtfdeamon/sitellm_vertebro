"""Tests for tg_bot.client."""

import importlib.util
import sys
import types
import asyncio
from pathlib import Path
import pytest

module_path = Path(__file__).resolve().parents[2] / "tg_bot" / "client.py"
spec = importlib.util.spec_from_file_location("tg_bot.client", module_path)
client = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = client

fake_structlog = types.ModuleType("structlog");
fake_structlog.get_logger = lambda *a, **k: types.SimpleNamespace(
    info=lambda *x, **y: None,
    warning=lambda *x, **y: None,
    debug=lambda *x, **y: None,
)
sys.modules["structlog"] = fake_structlog
fake_httpx = types.ModuleType("httpx")
fake_httpx.AsyncClient = None  # to be set
fake_httpx.HTTPError = Exception
sys.modules["httpx"] = fake_httpx

fake_config = types.ModuleType("tg_bot.config")
fake_config.get_settings = lambda: types.SimpleNamespace(
    backend_url="http://backend", request_timeout=10
)
sys.modules["tg_bot.config"] = fake_config

pkg = types.ModuleType("tg_bot")
pkg.__path__ = [str(Path(__file__).resolve().parents[2] / "tg_bot")]
sys.modules["tg_bot"] = pkg

fake_safety = types.ModuleType("safety")
fake_safety.safety_check = lambda text: False
sys.modules["safety"] = fake_safety

spec.loader.exec_module(client)


class FakeStream:
    """Yield predefined lines and support context manager API."""
    def __init__(self, lines, status=200):
        self.lines = lines
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def aiter_lines(self):
        for line in self.lines:
            yield line

    def raise_for_status(self):
        if self.status >= 400:
            raise fake_httpx.HTTPError()


class FakeClient:
    """Return ``FakeStream`` objects for ``stream`` calls."""
    def __init__(self, streams):
        self.streams = list(streams)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    def stream(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.streams.pop(0)


def test_rag_answer_success(monkeypatch):
    """Successful request should concatenate SSE data."""
    stream = FakeStream(["data: foo", "data: bar"])
    fake_httpx.AsyncClient = lambda timeout: FakeClient([stream])
    importlib.reload(client)

    result = asyncio.run(client.rag_answer("hi"))
    assert isinstance(result, dict)
    assert result.get("text") == "foobar"
    assert result.get("attachments") == []


def test_rag_answer_safety(monkeypatch):
    """safety_check triggers ValueError."""
    stream = FakeStream(["data: bad"])
    fake_httpx.AsyncClient = lambda timeout: FakeClient([stream])
    fake_safety.safety_check = lambda text: True
    importlib.reload(client)

    with pytest.raises(ValueError):
        asyncio.run(client.rag_answer("hi"))
