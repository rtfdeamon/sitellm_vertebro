"""Utilities for parsing documents and storing vectors in Redis."""

import os
import tempfile
from pathlib import Path

from langchain_core.embeddings import Embeddings
from langchain_redis import RedisVectorStore, RedisConfig
from redis.exceptions import ResponseError
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader

from redis import Redis


class DocumentsParser:
    """Parse documents and store embeddings in a Redis vector store."""
    def __init__(
        self,
        embeddings: Embeddings,
        index_name: str,
        redis_host: str,
        redis_port: int,
        redis_db: int = 0,
        redis_password: str = None,
        redis_secure: bool = False,
    ):
        """Create a vector store in Redis and ensure index exists."""
        url = f"redis{'s' if redis_secure else ''}://{':' + redis_password + '@' if redis_password else ''}{redis_host}:{redis_port}/{redis_db}"
        self.embeddings = embeddings

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

        tempfolder = tempfile.gettempdir()
        saved_file = Path(tempfolder) / name
        with saved_file.open("wb") as tmp:
            tmp.write(data)

        match file_extension:
            case ".txt":
                parser = TextLoader(saved_file)
            case ".docx":
                parser = Docx2txtLoader(saved_file)
            case ".pdf":
                parser = PyPDFLoader(file_path=tmp.name, mode="single")
            case _:
                raise ValueError("Unsupported file extension")

        document = parser.load()
        self.redis_store.add_documents(document, ids=[document_id])
