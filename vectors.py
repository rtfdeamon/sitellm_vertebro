"""Helpers for parsing documents and storing vectors in Qdrant."""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path
from typing import Iterable

from uuid import UUID, uuid4

from langchain_core.embeddings import Embeddings
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from PIL import Image

from models import Document
from knowledge.text import extract_doc_text, extract_xls_text, extract_xlsx_text


class DocumentsParser:
    """Parse documents and store embeddings in a Qdrant collection."""

    def __init__(self, embeddings: Embeddings, collection: str, url: str) -> None:
        self.embeddings = embeddings
        self.collection = collection or "documents"
        self._client = QdrantClient(url=url)
        self._ensure_collection()

    def close(self) -> None:
        """Close the underlying Qdrant client."""

        try:
            self._client.close()
        except Exception:  # pragma: no cover - best effort cleanup
            pass

    def _ensure_collection(self) -> None:
        """Create collection and payload indexes if missing."""

        if self._client.collection_exists(self.collection):
            return

        sample_vector = self.embeddings.embed_query("warmup")
        vector_size = len(sample_vector)

        vectors_config = qmodels.VectorParams(
            size=vector_size,
            distance=qmodels.Distance.COSINE,
        )

        self._client.recreate_collection(
            collection_name=self.collection,
            vectors_config=vectors_config,
        )

        try:
            self._client.create_payload_index(
                collection_name=self.collection,
                field_name="text",
                field_schema=qmodels.PayloadSchemaType.TEXT,
            )
        except Exception:  # pragma: no cover - index already exists / unsupported
            pass

        try:
            self._client.create_payload_index(
                collection_name=self.collection,
                field_name="project",
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )
        except Exception:  # pragma: no cover - index already exists / unsupported
            pass

    def parse_document(self, document: Document, data: bytes) -> None:
        """Embed ``document`` contents and upsert into Qdrant."""

        text = self._extract_text(document, data)
        if not text.strip():
            raise ValueError("Document does not contain extractable text")

        vector = self.embeddings.embed_documents([text])[0]
        payload = {
            "text": text,
            "name": document.name,
            "description": document.description,
            "project": document.project,
            "url": document.url,
            "file_id": document.fileId,
            "content_type": document.content_type,
        }

        if document.project:
            payload.setdefault("project", str(document.project).strip())

        if document.content_type:
            content_type = document.content_type.lower()
        else:
            content_type = ""

        if content_type.startswith("image/"):
            img = Image.open(io.BytesIO(data))
            width, height = img.size
            payload["image_width"] = width
            payload["image_height"] = height

        # Remove None values from payload to keep Qdrant schema tidy
        payload_clean = {key: value for key, value in payload.items() if value not in (None, "")}

        point_id = document.fileId
        if point_id is None:
            raise ValueError("Document missing fileId for vector upsert")

        qdrant_id: UUID
        raw_id = str(point_id).strip()
        try:
            qdrant_id = UUID(raw_id)
        except Exception:
            hex_id = ''.join(ch for ch in raw_id if ch.isalnum()).lower()
            if not hex_id:
                qdrant_id = uuid4()
            else:
                if len(hex_id) < 32:
                    hex_id = (hex_id + "0" * 32)[:32]
                else:
                    hex_id = hex_id[:32]
                try:
                    qdrant_id = UUID(hex=hex_id)
                except Exception:
                    qdrant_id = uuid4()

        self._client.upsert(
            collection_name=self.collection,
            points=[
                qmodels.PointStruct(
                    id=str(qdrant_id),  # Qdrant expects string or integer identifiers
                    vector=list(vector),
                    payload=payload_clean,
                )
            ],
        )

    def _extract_text(self, document: Document, data: bytes) -> str:
        """Return concatenated textual content for ``document``."""

        _, file_extension = os.path.splitext(document.name)
        file_extension = file_extension.lower()

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
            tmp.write(data)
            saved_file = Path(tmp.name)

        extra_path: Path | None = None
        try:
            loader, extra_path = self._select_loader(file_extension, saved_file)
            if loader is None:
                raise ValueError(f"Unsupported file extension: {file_extension}")

            pages = loader.load()
            contents = [page.page_content.strip() for page in _ensure_iterable(pages)]
        finally:
            saved_file.unlink(missing_ok=True)
            if extra_path is not None:
                extra_path.unlink(missing_ok=True)

        text_parts = [part for part in contents if part]
        if document.description:
            text_parts.insert(0, document.description.strip())

        text = "\n\n".join(text_parts).strip()
        return text

    def _select_loader(self, suffix: str, path: Path):
        """Return loader and optional temporary path for ``suffix``."""

        match suffix:
            case ".txt":
                return TextLoader(path), None
            case ".docx":
                return Docx2txtLoader(path), None
            case ".doc":
                text = extract_doc_text(path.read_bytes())
                if not text.strip():
                    raise ValueError("Unsupported DOC document")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp_txt:
                    tmp_txt.write(text.encode("utf-8"))
                    tmp_txt_path = Path(tmp_txt.name)
                return TextLoader(tmp_txt_path), tmp_txt_path
            case ".pdf":
                return PyPDFLoader(file_path=str(path), mode="single"), None
            case ".xlsx" | ".xlsm" | ".xltx" | ".xltm" | ".xlsb":
                text = extract_xlsx_text(path.read_bytes())
                if not text.strip():
                    raise ValueError("Unsupported XLSX document")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp_txt:
                    tmp_txt.write(text.encode("utf-8"))
                    tmp_txt_path = Path(tmp_txt.name)
                return TextLoader(tmp_txt_path), tmp_txt_path
            case ".xls" | ".xlt" | ".xlm" | ".xla" | ".xlw":
                text = extract_xls_text(path.read_bytes())
                if not text.strip():
                    raise ValueError("Unsupported XLS document")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp_txt:
                    tmp_txt.write(text.encode("utf-8"))
                    tmp_txt_path = Path(tmp_txt.name)
                return TextLoader(tmp_txt_path), tmp_txt_path
            case _:
                return None, None


def _ensure_iterable(result) -> Iterable:
    if isinstance(result, list):
        return result
    return [result]
