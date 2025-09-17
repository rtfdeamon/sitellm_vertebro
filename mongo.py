"""MongoDB client helpers used by the application."""

from collections.abc import AsyncGenerator
from urllib.parse import quote_plus
import hashlib
import json
import os
import time

import structlog
from bson import ObjectId
from gridfs import AsyncGridFS
from pymongo import AsyncMongoClient
from pymongo.errors import ConfigurationError

from backend.cache import _get_redis
from models import ContextMessage, ContextPreset, Document
try:
    from models import Project
except ImportError:  # pragma: no cover - fallback for test stubs
    class Project:  # type: ignore
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        def model_dump(self):
            return self.__dict__.copy()

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
        *,
        uri: str | None = None,
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
        if uri:
            self.url = uri
            self.client = AsyncMongoClient(uri)
            try:
                db = self.client.get_default_database()
            except ConfigurationError:
                db = self.client[database]
            self.database_name = db.name
            self.db = db
        else:
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
        self.projects_collection = os.getenv("MONGO_PROJECTS", "projects")
        self.settings_collection = os.getenv("MONGO_SETTINGS", "app_settings")

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

    async def search_documents(
        self, collection: str, query: str, project: str | None = None
    ) -> list[Document]:
        """Return documents from ``collection`` whose fields match ``query`` (cached)."""
        # Use a text index on 'name' or 'description' for keyword search
        search_query: dict = {"$text": {"$search": query}}
        if project:
            search_query["project"] = project
        key_parts = [
            "prefilter",
            project or "__global__",
            hashlib.sha1(query.lower().encode()).hexdigest(),
        ]
        key = ":".join(key_parts)
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

    async def get_document_with_content(
        self, collection: str, file_id: str
    ) -> tuple[dict, bytes]:
        """Return metadata and raw contents for ``file_id``."""

        doc = await self.db[collection].find_one({"fileId": file_id}, {"_id": False})
        if not doc:
            raise NotFound
        payload = await self.get_gridfs_file(file_id)
        return doc, payload

    async def delete_document(self, collection: str, file_id: str) -> None:
        """Remove document metadata and GridFS payload."""

        await self.db[collection].delete_one({"fileId": file_id})
        try:
            await self.gridfs.delete(ObjectId(file_id))
        except Exception:
            pass

    async def upload_document(
        self,
        file_name: str,
        file: bytes,
        documents_collection: str,
        *,
        description: str | None = None,
        url: str | None = None,
        content_type: str | None = None,
        project: str | None = None,
        domain: str | None = None,
    ) -> str:
        """Upload ``file`` to GridFS and store metadata in ``documents_collection``.

        Returns
        -------
        str
            The generated GridFS ``file_id``.
        """
        f_id = await self.gridfs.put(file)
        project_key = (project or "default").strip().lower()
        document = Document(
            name=file_name,
            description=description or "",
            fileId=str(f_id),
            url=url,
            ts=time.time(),
            content_type=content_type,
            domain=domain or project_key,
            project=project_key,
        )
        await self.db[documents_collection].insert_one(document.model_dump())

        return str(f_id)

    async def upsert_text_document(
        self,
        *,
        name: str,
        content: str,
        documents_collection: str,
        description: str | None = None,
        project: str | None = None,
        domain: str | None = None,
        url: str | None = None,
    ) -> str:
        """Upsert a plain-text document under ``domain``."""

        payload = content.encode("utf-8")
        description = description or content.replace("\n", " ").strip()[:200]
        project_key = (project or "default").strip().lower()
        existing = await self.db[documents_collection].find_one(
            {"name": name, "project": project_key},
            {"fileId": 1},
        )
        if existing and existing.get("fileId"):
            try:
                await self.gridfs.delete(ObjectId(existing["fileId"]))
            except Exception as exc:  # noqa: BLE001
                logger.warning("gridfs_delete_failed", file_id=existing["fileId"], error=str(exc))

        file_id = await self.gridfs.put(
            payload,
            filename=name,
            content_type="text/plain",
            encoding="utf-8",
        )

        doc = Document(
            name=name,
            description=description,
            fileId=str(file_id),
            url=url,
            ts=time.time(),
            content_type="text/plain",
            domain=domain or project_key,
            project=project_key,
        ).model_dump()

        await self.db[documents_collection].update_one(
            {"name": name, "project": project_key},
            {"$set": doc},
            upsert=True,
        )

        return str(file_id)

    async def list_project_names(self, documents_collection: str, limit: int = 100) -> list[str]:
        """Return a list of known project identifiers."""

        names: set[str] = set()
        async for item in (
            self.db[self.projects_collection]
            .find({}, {"_id": False, "name": 1})
            .limit(limit)
        ):
            if item.get("name"):
                names.add(item["name"])

        cursor = self.db[documents_collection].aggregate(
            [
                {"$match": {"project": {"$ne": None}}},
                {"$group": {"_id": "$project"}},
                {"$limit": limit},
            ]
        )
        async for item in cursor:
            if item.get("_id"):
                names.add(item["_id"])
        # Legacy documents keyed by domain only
        cursor_domain = self.db[documents_collection].aggregate(
            [
                {"$match": {"project": {"$exists": False}, "domain": {"$ne": None}}},
                {"$group": {"_id": "$domain"}},
                {"$limit": limit},
            ]
        )
        async for item in cursor_domain:
            if item.get("_id"):
                names.add(item["_id"])
        return sorted(names)

    def _project_from_doc(self, doc: dict | None) -> Project | None:
        if not doc:
            return None
        data = doc.copy()
        name = data.get("name") or data.get("domain")
        if not name:
            return None
        data.setdefault("name", name)
        data["name"] = str(data["name"]).strip().lower()
        if data.get("domain") == "":
            data["domain"] = None
        return Project(**data)

    async def list_projects(self) -> list[Project]:
        cursor = self.db[self.projects_collection].find({}, {"_id": False})
        projects: list[Project] = []
        async for item in cursor:
            project = self._project_from_doc(item)
            if project:
                projects.append(project)
        return projects

    async def upsert_project(self, project: Project) -> Project:
        data = project.model_dump()
        if not data.get("name"):
            raise ValueError("project name is required")
        data["name"] = str(data["name"]).strip().lower()
        await self.db[self.projects_collection].update_one(
            {"name": data["name"]},
            {"$set": data},
            upsert=True,
        )
        stored = await self.db[self.projects_collection].find_one(
            {"name": data["name"]},
            {"_id": False},
        )
        return self._project_from_doc(stored) or project

    async def delete_project(self, domain: str) -> None:
        await self.db[self.projects_collection].delete_one({"name": domain})
        await self.db[self.projects_collection].delete_one({"domain": domain})

    async def get_project(self, domain: str) -> Project | None:
        doc = await self.db[self.projects_collection].find_one(
            {"name": domain},
            {"_id": False},
        )
        if not doc:
            doc = await self.db[self.projects_collection].find_one(
                {"domain": domain},
                {"_id": False},
            )
        return self._project_from_doc(doc)

    async def get_setting(self, key: str) -> dict | None:
        return await self.db[self.settings_collection].find_one({"_id": key}, {"_id": False})

    async def set_setting(self, key: str, value: dict) -> None:
        value = value.copy()
        await self.db[self.settings_collection].update_one(
            {"_id": key},
            {"$set": value},
            upsert=True,
        )

    async def close(self) -> None:
        await self.client.close()
