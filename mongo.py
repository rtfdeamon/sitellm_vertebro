"""MongoDB client helpers used by the application."""

from collections.abc import AsyncGenerator
from contextlib import suppress
from urllib.parse import quote_plus
import hashlib
import json
import os
import time

import structlog
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
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

    Parameters
    ----------
    host, port, username, password, database, auth_database:
        Connection parameters used when an explicit ``uri`` is not provided.
    uri:
        Optional full MongoDB URI. When supplied, connection parameters are
        derived from it.

    Notes
    -----
    The client wraps :class:`motor.motor_asyncio.AsyncIOMotorClient` and exposes convenience
    helpers tailored to the application (documents, projects, GridFS, etc.).
    All database operations log exceptions before re-raising so the caller can
    surface actionable diagnostics to the end user.
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
        try:
            if uri:
                self.url = uri
                self.client = AsyncIOMotorClient(uri)
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
                self.client = AsyncIOMotorClient(self.url)
                self.database_name = database
                self.db = self.client[database]
        except Exception as exc:
            logger.error("mongo_client_init_failed", uri=uri or getattr(self, "url", uri), error=str(exc))
            raise
        self.gridfs = AsyncIOMotorGridFSBucket(self.db)
        self.projects_collection = os.getenv("MONGO_PROJECTS", "projects")
        self.settings_collection = os.getenv("MONGO_SETTINGS", "app_settings")
        self.documents_collection = os.getenv("MONGO_DOCUMENTS", "documents")
        self._indexes_ready = False

    async def is_query_empty(self, collection: str, query: dict) -> bool:
        """Return ``True`` if no documents match ``query`` in ``collection``.

        This helper allows raising :class:`NotFound` before performing a full
        query.
        """

        try:
            return await self.db[collection].count_documents(query) == 0
        except Exception as exc:
            logger.error("mongo_count_failed", collection=collection, query=query, error=str(exc))
            raise

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

        try:
            if await self.is_query_empty(collection, query):
                raise NotFound

            cursor = self.db[collection].find(query, {"_id": False})

            async for message in cursor.sort({"number": 1}):
                yield ContextMessage(**message)
        except NotFound:
            raise
        except Exception as exc:
            logger.error("mongo_get_sessions_failed", collection=collection, session_id=session_id, error=str(exc))
            raise

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

        try:
            if await self.is_query_empty(collection, query):
                raise NotFound

            cursor = self.db[collection].find(query, {"_id": False})

            async for message in cursor.sort({"number": 1}):
                yield ContextPreset(**message)
        except NotFound:
            raise
        except Exception as exc:
            logger.error("mongo_get_presets_failed", collection=collection, error=str(exc))
            raise

    async def get_documents(self, collection: str) -> AsyncGenerator[Document]:
        """Yield document metadata from ``collection``.

        Raises
        ------
        NotFound
            When no documents are found.
        """
        query = {}

        try:
            if await self.is_query_empty(collection, query):
                raise NotFound

            cursor = self.db[collection].find(query, {"_id": False})
            async for message in cursor:
                yield Document(**message)
        except NotFound:
            raise
        except Exception as exc:
            logger.error("mongo_get_documents_failed", collection=collection, error=str(exc))
            raise

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
        try:
            cached = await redis.get(key)
            if cached:
                logger.info("cache_hit", key=key)
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
            logger.info("cache_store", key=key, matched=len(documents))
            return documents
        except Exception as exc:
            logger.error("mongo_search_failed", collection=collection, query=query, project=project, error=str(exc))
            raise

    async def get_gridfs_file(self, file_id: str) -> bytes:
        """Return file contents from GridFS by ``file_id``."""
        try:
            download_stream = await self.gridfs.open_download_stream(ObjectId(file_id))
            try:
                return await download_stream.read()
            finally:
                with suppress(Exception):
                    download_stream.close()
        except Exception as exc:
            logger.error("gridfs_read_failed", file_id=file_id, error=str(exc))
            raise

    async def get_document_with_content(
        self, collection: str, file_id: str
    ) -> tuple[dict, bytes]:
        """Return metadata and raw contents for ``file_id``."""

        try:
            doc = await self.db[collection].find_one({"fileId": file_id}, {"_id": False})
            if not doc:
                raise NotFound
            payload = await self.get_gridfs_file(file_id)
            return doc, payload
        except NotFound:
            raise
        except Exception as exc:
            logger.error("mongo_get_document_with_content_failed", collection=collection, file_id=file_id, error=str(exc))
            raise

    async def delete_document(self, collection: str, file_id: str) -> None:
        """Remove document metadata and GridFS payload."""

        try:
            await self.db[collection].delete_one({"fileId": file_id})
            with suppress(Exception):
                await self.gridfs.delete(ObjectId(file_id))
        except Exception as exc:
            logger.error("mongo_delete_document_failed", collection=collection, file_id=file_id, error=str(exc))
            raise

    async def update_document_status(
        self, collection: str, file_id: str, status: str, message: str | None = None
    ) -> None:
        """Persist processing status for a document."""

        update = {"status": status, "statusMessage": message, "statusUpdatedAt": time.time()}
        await self.db[collection].update_one(
            {"fileId": file_id},
            {"$set": update},
            upsert=False,
        )

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
        try:
            f_id = await self.gridfs.upload_from_stream(
                file_name or "document",
                file,
            )
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
            ).model_dump()
            await self.db[documents_collection].insert_one(document)
            return str(f_id)
        except Exception as exc:
            logger.error("mongo_upload_document_failed", collection=documents_collection, name=file_name, project=project, error=str(exc))
            raise

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

        try:
            payload = content.encode("utf-8")
            description = description or content.replace("\n", " ").strip()[:200]
            project_key = (project or "default").strip().lower()
            existing = await self.db[documents_collection].find_one(
                {"name": name, "project": project_key},
                {"fileId": 1},
            )
            if existing and existing.get("fileId"):
                with suppress(Exception):
                    await self.gridfs.delete(ObjectId(existing["fileId"]))

            file_id = await self.gridfs.upload_from_stream(
                name or "document",
                payload,
                metadata={
                    "content_type": "text/plain",
                    "encoding": "utf-8",
                },
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
        except Exception as exc:
            logger.error("mongo_upsert_text_document_failed", collection=documents_collection, name=name, project=project, error=str(exc))
            raise

    async def list_project_names(self, documents_collection: str, limit: int = 100) -> list[str]:
        """Return a list of known project identifiers."""

        names: set[str] = set()
        try:
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
        except Exception as exc:
            logger.error("mongo_list_project_names_failed", limit=limit, error=str(exc))
            raise

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
        try:
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
        except Exception as exc:
            logger.error("mongo_upsert_project_failed", project=data.get("name"), error=str(exc))
            raise

    async def delete_project(self, domain: str) -> None:
        try:
            await self.db[self.projects_collection].delete_one({"name": domain})
            await self.db[self.projects_collection].delete_one({"domain": domain})
        except Exception as exc:
            logger.error("mongo_delete_project_failed", project=domain, error=str(exc))
            raise

    async def get_project(self, domain: str) -> Project | None:
        try:
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
        except Exception as exc:
            logger.error("mongo_get_project_failed", project=domain, error=str(exc))
            raise

    async def get_setting(self, key: str) -> dict | None:
        try:
            return await self.db[self.settings_collection].find_one({"_id": key}, {"_id": False})
        except Exception as exc:
            logger.error("mongo_get_setting_failed", key=key, error=str(exc))
            raise

    async def set_setting(self, key: str, value: dict) -> None:
        try:
            value = value.copy()
            await self.db[self.settings_collection].update_one(
                {"_id": key},
                {"$set": value},
                upsert=True,
            )
        except Exception as exc:
            logger.error("mongo_set_setting_failed", key=key, error=str(exc))
            raise

    async def close(self) -> None:
        self.client.close()

    async def ensure_indexes(self) -> None:
        """Create required Mongo indexes if they are missing."""

        if self._indexes_ready:
            return

        try:
            await self.db[self.projects_collection].create_index(
                "name",
                name="project_name_unique",
                unique=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "mongo_index_create_failed",
                collection=self.projects_collection,
                index="project_name_unique",
                error=str(exc),
            )

        try:
            await self.db[self.documents_collection].create_index(
                [("project", 1), ("name", 1)],
                name="documents_project_name_unique",
                unique=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "mongo_index_create_failed",
                collection=self.documents_collection,
                index="documents_project_name_unique",
                error=str(exc),
            )

        try:
            await self.db[self.documents_collection].create_index(
                [("name", "text"), ("description", "text")],
                name="documents_text_search",
                default_language="russian",
            )
            logger.info(
                "mongo_text_index_ready",
                collection=self.documents_collection,
                index="documents_text_search",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "mongo_index_create_failed",
                collection=self.documents_collection,
                index="documents_text_search",
                error=str(exc),
            )

        self._indexes_ready = True
