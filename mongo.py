"""MongoDB client helpers used by the application."""

from collections.abc import AsyncGenerator
from urllib.parse import quote_plus
import hashlib
import json

import structlog
from bson import ObjectId
from gridfs import AsyncGridFS
from pymongo import AsyncMongoClient

from backend.cache import _get_redis
from models import ContextMessage, ContextPreset, Document

logger = structlog.get_logger(__name__)


class NotFound(Exception):
    """Raised when a query to MongoDB yields no results."""

    pass


class MongoClient:
    """Wrapper around the asynchronous MongoDB client.

    Accepts optional ``username``/``password`` and builds a proper MongoDB URI
    whether authentication is configured or not.
    """
    def __init__(
        self,
        host: str,
        port: int,
        username: str | None,
        password: str | None,
        database: str,
        auth_database: str,
    ):
        """Create asynchronous client and GridFS connection.

        Parameters
        ----------
        host, port, username, password:
            Connection settings for the Mongo instance.
        database:
            Main database used by the application.
        auth_database:
            Database used for authentication.
        """
        # Build connection URL with or without credentials
        # Be tolerant to non-string env types (e.g., parsed as bool/int/Secret)
        has_user = username is not None and str(username) != ""
        has_pass = password is not None and str(password) != ""
        if has_user and has_pass:
            u = quote_plus(str(username))
            p = quote_plus(str(password))
            auth_part = f"{u}:{p}@"
            auth_db = f"/{auth_database}"
        else:
            auth_part = ""
            auth_db = ""

        self.url = f"mongodb://{auth_part}{host}:{port}{auth_db}"
        self.client = AsyncMongoClient(self.url)
        self.database_name = database
        self.db = self.client[database]
        self.gridfs = AsyncGridFS(self.db)

    async def is_query_empty(self, collection: str, query: dict) -> bool:
        """Return ``True`` if no documents match ``query`` in ``collection``.

        This helper allows raising :class:`NotFound` before performing a full
        query.
        """

        return await self.db[collection].count_documents(query) == 0

    async def get_sessions(
        self, collection: str, session_id: str
    ) -> AsyncGenerator[ContextMessage]:
        """Yield messages for a given ``session_id`` ordered by ``number``.

        Raises
        ------
        NotFound
            If the session does not exist.
        """
        query = {"sessionId": session_id}

        if await self.is_query_empty(collection, query):
            raise NotFound

        cursor = self.db[collection].find(query, {"_id": False})

        async for message in cursor.sort({"number": 1}):
            yield ContextMessage(**message)

    async def get_context_preset(
        self, collection: str
    ) -> AsyncGenerator[ContextPreset]:
        """Yield preset context messages stored in ``collection``.

        Raises
        ------
        NotFound
            If the collection is empty.
        """
        query = {}

        if await self.is_query_empty(collection, query):
            raise NotFound

        cursor = self.db[collection].find(query, {"_id": False})

        async for message in cursor.sort({"number": 1}):
            yield ContextPreset(**message)

    async def get_documents(self, collection: str) -> AsyncGenerator[Document]:
        """Yield document metadata from ``collection``.

        Raises
        ------
        NotFound
            When no documents are found.
        """
        query = {}

        if await self.is_query_empty(collection, query):
            raise NotFound

        cursor = self.db[collection].find(query, {"_id": False})
        async for message in cursor:
            yield Document(**message)

    async def search_documents(self, collection: str, query: str) -> list[Document]:
        """Return documents from ``collection`` whose fields match ``query`` (cached)."""
        # Use a text index on 'name' or 'description' for keyword search
        search_query = {"$text": {"$search": query}}
        key = "prefilter:" + hashlib.sha1(query.lower().encode()).hexdigest()
        redis = _get_redis()
        cached = await redis.get(key)
        if cached:
            logger.info("cache hit", key=key)
            docs_data = json.loads(cached.decode())
            return [Document(**d) for d in docs_data]
        cursor = self.db[collection].find(
            search_query, {"_id": False, "score": {"$meta": "textScore"}}
        )
        cursor = cursor.sort([("score", {"$meta": "textScore"})]).limit(50)
        documents = [Document(**doc) async for doc in cursor]
        # Cache the search results as a list of document dicts
        docs_data = [doc.model_dump() for doc in documents]
        await redis.setex(key, 86400, json.dumps(docs_data, ensure_ascii=False))
        logger.info("cache store", key=key)
        return documents

    async def get_gridfs_file(self, file_id: str) -> bytes:
        """Return file contents from GridFS by ``file_id``."""
        file = await self.gridfs.get(ObjectId(file_id))
        return await file.read()

    async def upload_document(
        self, file_name: str, file: bytes, documents_collection: str
    ) -> str:
        """Upload ``file`` to GridFS and store metadata in ``documents_collection``.

        Returns
        -------
        str
            The generated GridFS ``file_id``.
        """
        f_id = await self.gridfs.put(file)
        document = Document(name=file_name, description="", fileId=str(f_id))
        await self.db[documents_collection].insert_one(document.model_dump())

        return str(f_id)
