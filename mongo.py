from collections.abc import AsyncGenerator
from urllib.parse import quote_plus

from bson import ObjectId
from gridfs import AsyncGridFS
from pymongo import AsyncMongoClient

from models import ContextMessage, ContextPreset, Document


class NotFound(Exception):
    pass


class MongoClient:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        database: str,
        auth_database: str,
    ):
        self.url = f"mongodb://{quote_plus(username)}:{quote_plus(password)}@{host}:{port}/{auth_database}"
        self.client = AsyncMongoClient(self.url)
        self.database_name = database
        self.db = self.client[database]
        self.gridfs = AsyncGridFS(self.db)

    async def is_query_empty(self, collection: str, query: dict) -> bool:
        return await self.db[collection].count_documents(query) == 0

    async def get_sessions(
        self, collection: str, session_id: str
    ) -> AsyncGenerator[ContextMessage]:
        query = {"sessionId": session_id}

        if await self.is_query_empty(collection, query):
            raise NotFound

        cursor = self.db[collection].find(query, {"_id": False})

        async for message in cursor.sort({"number": 1}):
            yield ContextMessage(**message)

    async def get_context_preset(
        self, collection: str
    ) -> AsyncGenerator[ContextPreset]:
        query = {}

        if await self.is_query_empty(collection, query):
            raise NotFound

        cursor = self.db[collection].find(query, {"_id": False})

        async for message in cursor.sort({"number": 1}):
            yield ContextPreset(**message)

    async def get_documents(self, collection: str) -> AsyncGenerator[Document]:
        query = {}

        if await self.is_query_empty(collection, query):
            raise NotFound

        cursor = self.db[collection].find(query, {"_id": False})
        async for message in cursor:
            yield Document(**message)

    async def get_gridfs_file(self, file_id: str) -> bytes:
        file = await self.gridfs.get(ObjectId(file_id))
        return await file.read()

    async def upload_document(
        self, file_name: str, file: bytes, documents_collection: str
    ) -> str:
        f_id = await self.gridfs.put(file)
        document = Document(name=file_name, description="", fileId=str(f_id))
        await self.db[documents_collection].insert_one(document.model_dump())

        return f_id
