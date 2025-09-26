"""Tests for Qdrant-backed DocumentsParser."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from models import Document
import vectors


class FakeEmbeddings:
    def embed_query(self, _: str) -> list[float]:
        return [0.0, 0.1, 0.2]

    def embed_documents(self, texts):
        return [[len(texts[0]), 0.2, 0.3]]


class DummyLoader:
    def __init__(self, path, **kwargs):
        self.path = Path(path)

    def load(self):
        return [SimpleNamespace(page_content="loader content")]


class FakeQdrantClient:
    def __init__(self, *_, **__):
        self.created = False
        self.points = []

    def collection_exists(self, name):
        return self.created

    def recreate_collection(self, *_, **__):
        self.created = True

    def create_payload_index(self, *_, **__):
        return None

    def upsert(self, *, collection_name, points):
        self.collection = collection_name
        self.points.extend(points)

    def close(self):
        pass


@pytest.fixture
def parser(monkeypatch):
    monkeypatch.setattr(vectors, "QdrantClient", FakeQdrantClient)
    monkeypatch.setattr(vectors, "TextLoader", DummyLoader)
    monkeypatch.setattr(vectors, "Docx2txtLoader", DummyLoader)
    monkeypatch.setattr(vectors, "PyPDFLoader", DummyLoader)
    embeddings = FakeEmbeddings()
    parser = vectors.DocumentsParser(embeddings, "test-collection", "http://qdrant")
    return parser


def test_parse_document_upserts_payload(parser, tmp_path):
    doc = Document(
        name="example.txt",
        description="Sample description",
        fileId="doc-1",
    )

    parser.parse_document(doc, b"dummy")

    assert isinstance(parser._client, FakeQdrantClient)
    assert parser._client.collection == "test-collection"
    assert parser._client.points
    point = parser._client.points[0]
    assert point.id == "doc-1"
    assert "text" in point.payload
    assert "Sample description" in point.payload["text"]


def test_parse_document_unsupported_extension(parser):
    doc = Document(name="example.xyz", description="Nope", fileId="doc-2")
    with pytest.raises(ValueError):
        parser.parse_document(doc, b"dummy")
