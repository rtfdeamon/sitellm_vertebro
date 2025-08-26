"""Tests for vectors.DocumentsParser.parse_document."""

import importlib.util
import sys
from pathlib import Path
import tempfile
import types
from unittest.mock import MagicMock

import pytest

# Load vectors module with stubbed dependencies
module_path = Path(__file__).resolve().parents[1] / "vectors.py"
spec = importlib.util.spec_from_file_location("vectors", module_path)
vectors = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = vectors

# Stub external dependencies required by vectors.py
# langchain_core.embeddings
core_embeddings = types.ModuleType("langchain_core.embeddings")
class Embeddings:  # minimal placeholder
    pass
core_embeddings.Embeddings = Embeddings
sys.modules["langchain_core.embeddings"] = core_embeddings

# langchain_redis
redis_module = types.ModuleType("langchain_redis")
class RedisVectorStore:
    def __init__(self, *_, **__):
        pass
    def add_documents(self, *args, **kwargs):  # pragma: no cover - replaced in tests
        pass
class RedisConfig:
    def __init__(self, *_, **__):
        pass
redis_module.RedisVectorStore = RedisVectorStore
redis_module.RedisConfig = RedisConfig
sys.modules["langchain_redis"] = redis_module

# redis and exceptions
redis_root = types.ModuleType("redis")
class Redis:  # minimal placeholder
    pass
redis_root.Redis = Redis
redis_exceptions = types.ModuleType("redis.exceptions")
class ResponseError(Exception):
    pass
redis_exceptions.ResponseError = ResponseError
redis_root.exceptions = redis_exceptions
sys.modules["redis"] = redis_root
sys.modules["redis.exceptions"] = redis_exceptions

# document loaders
loaders = types.ModuleType("langchain_community.document_loaders")
loaders.Docx2txtLoader = object  # replaced in tests
loaders.PyPDFLoader = object
loaders.TextLoader = object
sys.modules["langchain_community.document_loaders"] = loaders

# Execute module
spec.loader.exec_module(vectors)
DocumentsParser = vectors.DocumentsParser


def _parser_with_mock(monkeypatch):
    """Create DocumentsParser instance with mocked Redis store."""
    mock_add = MagicMock()
    monkeypatch.setattr(vectors.RedisVectorStore, "add_documents", mock_add)
    parser = DocumentsParser.__new__(DocumentsParser)
    parser.redis_store = vectors.RedisVectorStore()
    return parser, mock_add


@pytest.mark.parametrize(
    "filename, loader_attr",
    [
        ("sample.txt", "TextLoader"),
        ("sample.docx", "Docx2txtLoader"),
        ("sample.pdf", "PyPDFLoader"),
    ],
)
def test_parse_document_selects_loader_and_cleans_tmp(monkeypatch, filename, loader_attr):
    """`parse_document` should use correct loader and remove temp file."""
    parser, mock_add = _parser_with_mock(monkeypatch)

    called = {}

    class FakeLoader:
        def __init__(self, *args, **kwargs):
            path = args[0] if args else kwargs.get("file_path")
            called["path"] = Path(path)
        def load(self):
            return []

    monkeypatch.setattr(vectors, loader_attr, FakeLoader)

    orig_named_tmp = tempfile.NamedTemporaryFile
    tmp_holder = {}

    def fake_named_tmp(*args, **kwargs):
        tmp = orig_named_tmp(*args, **kwargs)
        tmp_holder["path"] = Path(tmp.name)
        return tmp

    monkeypatch.setattr(vectors.tempfile, "NamedTemporaryFile", fake_named_tmp)

    parser.parse_document(filename, "doc-id", b"data")

    assert called["path"].suffix == Path(filename).suffix
    assert not tmp_holder["path"].exists()
    assert mock_add.called


def test_parse_document_unknown_extension(monkeypatch):
    """Unsupported extension should raise ValueError."""
    parser, mock_add = _parser_with_mock(monkeypatch)

    with pytest.raises(ValueError):
        parser.parse_document("file.unknown", "doc-id", b"data")

    assert not mock_add.called
