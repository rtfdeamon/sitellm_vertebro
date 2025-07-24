"""MongoDB client helpers used by the application."""

from collections.abc import AsyncGenerator
from urllib.parse import quote_plus

from bson import ObjectId
from gridfs import AsyncGridFS
from pymongo import AsyncMongoClient

from models import ContextMessage, ContextPreset, Document


class NotFound(Exception):
    """Raised when a query to MongoDB yields no results."""

    pass


class MongoClient:
    """Wrapper around the asynchronous MongoDB client."""
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
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

        self.url = (
            f"mongodb://{quote_plus(username)}:{quote_plus(password)}@{host}:{port}/{auth_database}"
        )
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

        return f_id
