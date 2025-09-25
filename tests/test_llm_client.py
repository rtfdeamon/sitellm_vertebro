"""Tests for the high-level llm_client wrapper."""

import asyncio
import importlib

import pytest


class DummyManager:
    def __init__(self, tokens=None, error=None):
        self._tokens = tokens or []
        self._error = error

    async def generate(self, prompt: str, *, model: str | None = None):
        if self._error:
            raise self._error
        for token in list(self._tokens):
            yield token


async def _async_collect(async_iterable):
    return [chunk async for chunk in async_iterable]


def _collect(async_iterable):
    return asyncio.run(_async_collect(async_iterable))


def _setup(monkeypatch, manager: DummyManager):
    from backend import llm_client

    importlib.reload(llm_client)
    monkeypatch.setattr(llm_client, "get_cluster_manager", lambda: manager)
    return llm_client


def test_generate_delegates_to_cluster(monkeypatch):
    manager = DummyManager(tokens=["a", "b", "c"])
    llm_client = _setup(monkeypatch, manager)
    tokens = _collect(llm_client.generate("prompt"))
    assert tokens == ["a", "b", "c"]


def test_generate_propagates_errors(monkeypatch):
    manager = DummyManager(error=RuntimeError("boom"))
    llm_client = _setup(monkeypatch, manager)
    with pytest.raises(RuntimeError):
        _collect(llm_client.generate("prompt"))


def test_model_not_found_error_reexport():
    from backend import llm_client
    from backend.ollama_cluster import ModelNotFoundError

    assert llm_client.ModelNotFoundError is ModelNotFoundError
