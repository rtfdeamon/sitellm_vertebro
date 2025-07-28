import asyncio
import types
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest


class DummyStreamer:
    def __init__(self):
        self._queue = []

    def put(self, token):
        self._queue.append(token)

    def __iter__(self):
        while self._queue:
            yield self._queue.pop(0)

    async def __aiter__(self):
        for token in list(self._queue):
            yield token


class DummyModel:
    def __init__(self, tokens, fail_times=0):
        self.tokens = list(tokens)
        self.fail_times = fail_times
        self.calls = 0

    def generate(self, **kwargs):
        if self.calls < self.fail_times:
            self.calls += 1
            raise RuntimeError("fail")
        streamer = kwargs["streamer"]
        for t in self.tokens:
            streamer.put(t)


class DummyTokenizer:
    def __call__(self, text, return_tensors=None):
        return {}


async def _async_collect(it):
    return [token async for token in it]


def _collect(it):
    return asyncio.run(_async_collect(it))


def _setup(monkeypatch, model, fails=0):
    from backend import llm_client
    importlib.reload(llm_client)
    monkeypatch.setattr(llm_client, "_tokenizer", DummyTokenizer())
    monkeypatch.setattr(llm_client, "_model", model)
    counter = {"n": 0}

    def fake_load():
        if counter["n"] < fails:
            counter["n"] += 1
            raise RuntimeError("fail")

    monkeypatch.setattr(llm_client, "_load", fake_load)
    monkeypatch.setattr(
        llm_client, "TextIteratorStreamer", lambda *a, **k: DummyStreamer()
    )
    return llm_client


def test_generate_success(monkeypatch):
    model = DummyModel(["a", "b"])
    llm_client = _setup(monkeypatch, model)
    tokens = _collect(llm_client.generate("hi"))
    assert tokens == ["a", "b"]


def test_generate_retry(monkeypatch):
    model = DummyModel(["ok"])
    llm_client = _setup(monkeypatch, model, fails=1)
    tokens = _collect(llm_client.generate("hi"))
    assert tokens == ["ok"]


def test_generate_failure(monkeypatch):
    model = DummyModel(["x"], fail_times=4)
    llm_client = _setup(monkeypatch, model, fails=4)
    with pytest.raises(RuntimeError):
        _collect(llm_client.generate("hi"))
