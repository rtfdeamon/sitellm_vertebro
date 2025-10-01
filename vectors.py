"""Utilities for parsing documents and storing vectors in Redis."""

import os
import tempfile
from pathlib import Path

from langchain_core.embeddings import Embeddings
from langchain_redis import RedisVectorStore, RedisConfig
from redis.exceptions import ResponseError
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader

from redis import Redis

from knowledge.text import extract_doc_text, extract_xls_text, extract_xlsx_text


class DocumentsParser:
    """Parse documents and store embeddings in a Redis vector store."""
    def __init__(
        self,
        embeddings: Embeddings,
        index_name: str,
        redis_host: str | None = None,
        redis_port: int | None = None,
        redis_db: int = 0,
        redis_password: str | None = None,
        redis_secure: bool = False,
        redis_url: str | None = None,
    ):
        """Create a vector store in Redis and ensure index exists."""
        if redis_url:
            url = redis_url
        else:
            redis_host = redis_host or "localhost"
            redis_port = int(redis_port or 6379)
            url = f"redis{'s' if redis_secure else ''}://{':' + redis_password + '@' if redis_password else ''}{redis_host}:{redis_port}/{redis_db}"
        self.embeddings = embeddings

        if redis_url:
            client = Redis.from_url(redis_url)
        else:
            client = Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                ssl=redis_secure,
            )
        exists = True
        try:
            client.ft(index_name).info()
        except ResponseError:
            exists = False
        client.close()

        config = RedisConfig(index_name=index_name, redis_url=url, from_existing=exists)

        self.redis_store = RedisVectorStore(embeddings, config)

    def parse_document(self, name: str, document_id: str, data: bytes):
        """Load ``data`` into Redis vector store under ``document_id``.

        Parameters
        ----------
        name:
            Name of the uploaded file used to infer its format.
        document_id:
            Unique identifier to store the vectors under.
        data:
            Raw file contents to embed.
        """
        _, file_extension = os.path.splitext(name)
        file_extension = file_extension.lower()

        # use a dedicated temporary file to avoid name collisions
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
            tmp.write(data)
            saved_file = Path(tmp.name)

        try:
            match file_extension:
                case ".txt":
                    parser = TextLoader(saved_file)
                case ".docx":
                    parser = Docx2txtLoader(saved_file)
                case ".doc":
                    text = extract_doc_text(saved_file.read_bytes())
                    if not text.strip():
                        raise ValueError("Unsupported DOC document")
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp_txt:
                        tmp_txt.write(text.encode("utf-8"))
                        tmp_txt_path = Path(tmp_txt.name)
                    try:
                        parser = TextLoader(tmp_txt_path)
                        document = parser.load()
                        self.redis_store.add_documents(document, ids=[document_id])
                    finally:
                        tmp_txt_path.unlink(missing_ok=True)
                    return
                case ".pdf":
                    parser = PyPDFLoader(file_path=str(saved_file), mode="single")
                case ".xlsx" | ".xlsm" | ".xltx" | ".xltm" | ".xlsb":
                    text = extract_xlsx_text(saved_file.read_bytes())
                    if not text.strip():
                        raise ValueError("Unsupported XLSX document")
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp_txt:
                        tmp_txt.write(text.encode("utf-8"))
                        tmp_txt_path = Path(tmp_txt.name)
                    try:
                        parser = TextLoader(tmp_txt_path)
                        document = parser.load()
                        self.redis_store.add_documents(document, ids=[document_id])
                    finally:
                        tmp_txt_path.unlink(missing_ok=True)
                    return
                case ".xls" | ".xlt" | ".xlm" | ".xla" | ".xlw":
                    text = extract_xls_text(saved_file.read_bytes())
                    if not text.strip():
                        raise ValueError("Unsupported XLS document")
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp_txt:
                        tmp_txt.write(text.encode("utf-8"))
                        tmp_txt_path = Path(tmp_txt.name)
                    try:
                        parser = TextLoader(tmp_txt_path)
                        document = parser.load()
                        self.redis_store.add_documents(document, ids=[document_id])
                    finally:
                        tmp_txt_path.unlink(missing_ok=True)
                    return
                case _:
                    raise ValueError("Unsupported file extension")

            document = parser.load()
            self.redis_store.add_documents(document, ids=[document_id])
        finally:
            saved_file.unlink(missing_ok=True)
