"""Tests for the asynchronous LLM client."""
import importlib
import sys
import types
import asyncio
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class FakeStream:
    def __init__(self, lines):
        self._lines = list(lines)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._lines:
            raise StopAsyncIteration
        return self._lines.pop(0).encode()


class FakeResponse:
    def __init__(self, lines, status=200):
        self.lines = lines
        self.status = status
        self.content = FakeStream(lines)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    def raise_for_status(self):
        if self.status >= 400:
            raise ClientResponseError(status=self.status, request_info=None, history=None)


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    def post(self, url, json):
        self.calls.append((url, json))
        return self.responses.pop(0)


class ClientResponseError(Exception):
    def __init__(self, status=500, request_info=None, history=None):
        self.status = status
        self.request_info = request_info
        self.history = history
        super().__init__("error")


async def _collect(iterator):
    return [token async for token in iterator]


def setup_module(module):
    fake_aiohttp = types.ModuleType("aiohttp")
    fake_aiohttp.ClientResponseError = ClientResponseError
    fake_aiohttp.ClientSession = None  # placeholder
    sys.modules["aiohttp"] = fake_aiohttp


def test_generate_success(monkeypatch):
    """Streaming should yield tokens from successful response."""
    from backend import llm_client
    responses = [FakeResponse(["data: one", "x", "data: two"])]
    session = FakeSession(responses)
    sys.modules["aiohttp"].ClientSession = lambda: session
    importlib.reload(llm_client)

    result = asyncio.run(_collect(llm_client.generate("hi")))
    assert result == ["one", "two"]
    assert session.calls == [("http://localhost:8000", {"prompt": "hi", "stream": True})]


def test_generate_retry(monkeypatch):
    """Errors trigger retries before succeeding."""
    from backend import llm_client
    responses = [FakeResponse([], status=500), FakeResponse(["data: ok"])]
    session = FakeSession(responses)
    sys.modules["aiohttp"].ClientSession = lambda: session
    importlib.reload(llm_client)

    sleeps = []

    async def fake_sleep(t):
        sleeps.append(t)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    result = asyncio.run(_collect(llm_client.generate("hi")))
    assert result == ["ok"]
    assert len(session.calls) == 2
    assert sleeps == [0.5]


def test_generate_failure(monkeypatch):
    """After all retries fail an exception is raised."""
    from backend import llm_client
    responses = [FakeResponse([], status=500)] * 4
    session = FakeSession(responses)
    sys.modules["aiohttp"].ClientSession = lambda: session
    importlib.reload(llm_client)

    async def fake_sleep(t):
        pass
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    with pytest.raises(ClientResponseError):
        asyncio.run(_collect(llm_client.generate("hi")))
    assert len(session.calls) == 4
