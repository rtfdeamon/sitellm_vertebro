"""Unit tests for the Ollama streaming client."""

import asyncio
import importlib

import pytest


class FakeResponse:
    def __init__(self, lines=None, raise_status=None):
        self._lines = lines or []
        self._raise_status = raise_status

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        if self._raise_status:
            raise self._raise_status

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class FakeClient:
    def __init__(self, responses):
        self._responses = responses

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def stream(self, *args, **kwargs):
        if not self._responses:
            raise RuntimeError("no more responses")
        resp = self._responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp


def _collect(async_iterable):
    return asyncio.run(_async_collect(async_iterable))


async def _async_collect(async_iterable):
    return [token async for token in async_iterable]


def _setup(monkeypatch, factory):
    from backend import llm_client

    importlib.reload(llm_client)
    monkeypatch.setattr(llm_client, "_http_client_factory", factory)
    return llm_client


def test_generate_success(monkeypatch):
    lines = ["{\"response\": \"a\"}", "{\"response\": \"b\", \"done\": true}"]

    def factory(**kwargs):
        return FakeClient([FakeResponse(lines=lines)])

    llm_client = _setup(monkeypatch, factory)
    tokens = _collect(llm_client.generate("hi"))
    assert tokens == ["a", "b"]


def test_generate_retry(monkeypatch):
    lines = ["{\"response\": \"ok\", \"done\": true}"]
    attempts = {"count": 0}

    def factory(**kwargs):
        if attempts["count"] == 0:
            attempts["count"] += 1
            raise RuntimeError("connection failed")
        return FakeClient([FakeResponse(lines=lines)])

    llm_client = _setup(monkeypatch, factory)
    tokens = _collect(llm_client.generate("hi"))
    assert tokens == ["ok"]


def test_generate_failure(monkeypatch):
    def factory(**kwargs):
        raise RuntimeError("persistent failure")

    llm_client = _setup(monkeypatch, factory)
    with pytest.raises(RuntimeError):
        _collect(llm_client.generate("hi"))
