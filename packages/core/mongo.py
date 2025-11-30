"""MongoDB client helpers used by the application."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from datetime import datetime, timezone, timedelta
from contextlib import suppress
from urllib.parse import quote_plus
import hashlib
import json
import os
import time
from difflib import SequenceMatcher

import structlog
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from pymongo.errors import ConfigurationError

from packages.backend.cache import _get_redis
from packages.core.models import (
    BackupJob,
    BackupOperation,
    BackupSettings,
    BackupStatus,
    ContextMessage,
    ContextPreset,
    Document,
    OllamaServer,
    ReadingPage,
    VoiceSample,
    VoiceTrainingJob,
    VoiceTrainingStatus,
)
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

TOKEN_UNSET: object = object()


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
        self.stats_collection = os.getenv("MONGO_STATS", "request_stats")
        self.ollama_servers_collection = os.getenv("MONGO_OLLAMA_SERVERS", "ollama_servers")
        self.qa_collection = os.getenv("MONGO_QA", "knowledge_qa")
        self.unanswered_collection = os.getenv("MONGO_UNANSWERED", "knowledge_unanswered")
        self.feedback_collection = os.getenv("MONGO_FEEDBACK", "feedback_tasks")
        self.unanswered_collection = os.getenv("MONGO_UNANSWERED", "unanswered_questions")
        self.voice_samples_collection = os.getenv("MONGO_VOICE_SAMPLES", "voice_samples")
        self.voice_jobs_collection = os.getenv("MONGO_VOICE_JOBS", "voice_training_jobs")
        self.backup_jobs_collection = os.getenv("MONGO_BACKUPS", "backup_jobs")
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

    async def get_reading_pages(
        self,
        collection: str,
        project: str,
        *,
        limit: int = 20,
        offset: int = 0,
        url: str | None = None,
    ) -> list[ReadingPage]:
        """Return reading-mode pages for ``project`` sorted by ``order``."""

        query: dict[str, Any] = {"project": project}
        if url:
            query["url"] = url

        try:
            cursor = (
                self.db[collection]
                .find(query, {"_id": False})
                .sort([("order", 1), ("updatedAt", -1)])
            )
            if offset:
                cursor = cursor.skip(offset)
            if limit:
                cursor = cursor.limit(limit)
            return [ReadingPage(**doc) async for doc in cursor]
        except Exception as exc:
            logger.error(
                "mongo_get_reading_pages_failed",
                collection=collection,
                project=project,
                error=str(exc),
            )
            raise

    async def count_reading_pages(self, collection: str, project: str) -> int:
        """Return total number of reading-mode pages for ``project``."""

        try:
            return await self.db[collection].count_documents({"project": project})
        except Exception as exc:
            logger.error(
                "mongo_count_reading_pages_failed",
                collection=collection,
                project=project,
                error=str(exc),
            )
            raise

    async def add_voice_sample(
        self,
        project: str,
        filename: str,
        payload: bytes,
        content_type: str | None,
        *,
        duration: float | None = None,
    ) -> VoiceSample:
        now = time.time()
        uploaded_at_iso = datetime.utcfromtimestamp(now).isoformat()
        try:
            file_id = await self.gridfs.upload_from_stream(  # type: ignore[attr-defined]
                filename,
                payload,
                metadata={
                    "project": project,
                    "contentType": content_type,
                    "uploadedAt": now,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("voice_sample_gridfs_failed", project=project, error=str(exc))
            raise

        doc = {
            "project": project,
            "fileId": str(file_id),
            "filename": filename,
            "contentType": content_type,
            "sizeBytes": len(payload),
            "durationSeconds": duration,
            "uploadedAt": now,
            "uploadedAtIso": uploaded_at_iso,
        }
        result = await self.db[self.voice_samples_collection].insert_one(doc)
        doc["id"] = str(result.inserted_id)
        return VoiceSample(**doc)

    async def list_voice_samples(self, project: str) -> list[VoiceSample]:
        try:
            cursor = (
                self.db[self.voice_samples_collection]
                .find({"project": project}, {"_id": True, "project": True, "fileId": True, "filename": True, "contentType": True, "sizeBytes": True, "durationSeconds": True, "uploadedAt": True})
                .sort("uploadedAt", -1)
            )
            samples: list[VoiceSample] = []
            async for doc in cursor:
                doc = dict(doc)
                doc["id"] = str(doc.pop("_id"))
                samples.append(VoiceSample(**doc))
            return samples
        except Exception as exc:
            logger.error("mongo_voice_samples_list_failed", project=project, error=str(exc))
            raise

    async def delete_voice_sample(self, project: str, sample_id: str) -> bool:
        try:
            oid = ObjectId(sample_id)
        except Exception:
            return False
        doc = await self.db[self.voice_samples_collection].find_one({"_id": oid, "project": project})
        if not doc:
            return False
        file_id = doc.get("fileId")
        try:
            await self.db[self.voice_samples_collection].delete_one({"_id": oid})
        except Exception as exc:
            logger.error("mongo_voice_sample_delete_failed", sample_id=sample_id, error=str(exc))
            raise
        if file_id:
            try:
                await self.gridfs.delete(ObjectId(file_id))  # type: ignore[attr-defined]
            except Exception as exc:  # noqa: BLE001
                logger.warning("voice_sample_gridfs_delete_failed", file_id=file_id, error=str(exc))
        return True

    async def create_voice_training_job(
        self,
        project: str,
        *,
        status: VoiceTrainingStatus = VoiceTrainingStatus.queued,
        message: str | None = None,
    ) -> VoiceTrainingJob:
        now = time.time()
        payload = {
            "project": project,
            "status": status.value,
            "progress": 0.0,
            "message": message,
            "createdAt": now,
            "createdAtIso": datetime.utcfromtimestamp(now).isoformat(),
            "updatedAt": now,
        }
        result = await self.db[self.voice_jobs_collection].insert_one(payload)
        payload["id"] = str(result.inserted_id)
        payload["status"] = status
        return VoiceTrainingJob(**payload)

    async def update_voice_training_job(
        self,
        job_id: str,
        *,
        status: VoiceTrainingStatus | None = None,
        progress: float | None = None,
        message: str | None = None,
        started_at: float | None = None,
        finished_at: float | None = None,
    ) -> VoiceTrainingJob | None:
        try:
            oid = ObjectId(job_id)
        except Exception:
            return None
        updates: dict[str, object] = {"updatedAt": time.time()}
        if status is not None:
            updates["status"] = status.value
        if progress is not None:
            updates["progress"] = float(progress)
        if message is not None:
            updates["message"] = message
        if started_at is not None:
            updates["startedAt"] = started_at
            updates["startedAtIso"] = datetime.utcfromtimestamp(started_at).isoformat()
        if finished_at is not None:
            updates["finishedAt"] = finished_at
            updates["finishedAtIso"] = datetime.utcfromtimestamp(finished_at).isoformat()

        result = await self.db[self.voice_jobs_collection].find_one_and_update(
            {"_id": oid},
            {"$set": updates},
            return_document=True,
        )
        if not result:
            return None
        result = dict(result)
        result["id"] = str(result.pop("_id"))
        status_value = result.get("status", VoiceTrainingStatus.queued.value)
        try:
            result["status"] = VoiceTrainingStatus(status_value)
        except Exception:
            result["status"] = VoiceTrainingStatus.queued
        return VoiceTrainingJob(**result)

    async def list_voice_training_jobs(self, project: str, *, limit: int = 10) -> list[VoiceTrainingJob]:
        try:
            cursor = (
                self.db[self.voice_jobs_collection]
                .find({"project": project}, {"_id": True, "project": True, "status": True, "progress": True, "message": True, "createdAt": True, "startedAt": True, "finishedAt": True})
                .sort("createdAt", -1)
                .limit(limit)
            )
            jobs: list[VoiceTrainingJob] = []
            async for doc in cursor:
                doc = dict(doc)
                doc["id"] = str(doc.pop("_id"))
                doc_status = doc.get("status", VoiceTrainingStatus.queued.value)
                try:
                    doc["status"] = VoiceTrainingStatus(doc_status)
                except Exception:
                    doc["status"] = VoiceTrainingStatus.queued
                jobs.append(VoiceTrainingJob(**doc))
            return jobs
        except Exception as exc:
            logger.error("mongo_voice_jobs_list_failed", project=project, error=str(exc))
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
            docs_data = [doc.model_dump(by_alias=True) for doc in documents]
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
            description_value = "" if description is None else description
            size_bytes = len(file) if isinstance(file, (bytes, bytearray)) else None
            document = Document(
                name=file_name,
                description=description_value,
                fileId=str(f_id),
                url=url,
                ts=time.time(),
                content_type=content_type,
                domain=domain or project_key,
                project=project_key,
                size_bytes=size_bytes,
            ).model_dump()
            await self.db[documents_collection].insert_one(document)
            return str(f_id)
        except Exception as exc:
            logger.error("mongo_upload_document_failed", collection=documents_collection, name=file_name, project=project, error=str(exc))
            raise

    async def deduplicate_documents(
        self,
        documents_collection: str,
        project: str | None = None,
    ) -> dict[str, object]:
        """Remove duplicate documents based on content hash within ``project``."""

        filter_query: dict[str, object] = {}
        if project:
            filter_query["project"] = project

        seen: dict[str, str] = {}
        removed: list[str] = []
        checked = 0

        cursor = self.db[documents_collection].find(filter_query, {"_id": False, "fileId": 1, "project": 1, "domain": 1})
        async for doc in cursor:
            file_id = doc.get("fileId")
            if not file_id:
                continue
            checked += 1
            try:
                _meta, payload = await self.get_document_with_content(documents_collection, file_id)
            except NotFound:
                with suppress(Exception):
                    await self.db[documents_collection].delete_one({"fileId": file_id})
                removed.append(file_id)
                continue
            except Exception as exc:  # noqa: BLE001
                logger.warning("mongo_deduplicate_fetch_failed", file_id=file_id, error=str(exc))
                continue

            digest = hashlib.sha1(payload).hexdigest()
            project_key = (_meta.get("project") or _meta.get("domain") or "").strip().lower()
            key = f"{project_key}:{digest}"
            if key in seen:
                try:
                    await self.delete_document(documents_collection, file_id)
                    removed.append(file_id)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("mongo_deduplicate_delete_failed", file_id=file_id, error=str(exc))
            else:
                seen[key] = file_id

        return {
            "checked": checked,
            "kept": len(seen),
            "removed": len(removed),
            "removed_ids": removed,
        }

    async def append_session_message(
        self,
        collection: str,
        session_id: str,
        role: str,
        text: str,
        *,
        project: str | None = None,
        keep: int = 10,
    ) -> ContextMessage:
        """Append a message to a conversation session."""

        try:
            last = await self.db[collection].find_one(
                {"sessionId": session_id},
                {"number": 1},
                sort=[("number", -1)],
            )
            next_number = int(last.get("number", -1)) + 1 if last else 0
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "mongo_session_next_number_failed",
                collection=collection,
                session=session_id,
                error=str(exc),
            )
            raise

        message = ContextMessage(
            sessionId=session_id,
            role=role,
            number=next_number,
            text=text,
            project=(project or None),
        )
        payload = message.model_dump(by_alias=True)
        try:
            await self.db[collection].insert_one(payload)
            if keep > 0:
                total = await self.db[collection].count_documents({"sessionId": session_id})
                if total > keep:
                    async for outdated in (
                        self.db[collection]
                        .find({"sessionId": session_id}, {"_id": 1})
                        .sort("number", 1)
                        .limit(total - keep)
                    ):
                        oid = outdated.get("_id")
                        if oid:
                            await self.db[collection].delete_one({"_id": oid})
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "mongo_append_session_failed",
                collection=collection,
                session=session_id,
                error=str(exc),
            )
            raise
        return message

    async def clear_session(self, collection: str, session_id: str) -> None:
        """Remove all messages for ``session_id``."""

        try:
            await self.db[collection].delete_many({"sessionId": session_id})
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "mongo_clear_session_failed",
                collection=collection,
                session=session_id,
                error=str(exc),
            )
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
            if description is None:
                description_value = content.replace("\n", " ").strip()[:200]
            else:
                description_value = description
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
                description=description_value,
                fileId=str(file_id),
                url=url,
                ts=time.time(),
                content_type="text/plain",
                domain=domain or project_key,
                project=project_key,
                size_bytes=len(payload),
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

    async def list_qa_pairs(self, project: str | None, *, limit: int = 1000) -> list[dict]:
        """Return FAQ pairs for ``project`` ordered by priority and recency."""

        query: dict[str, object] = {}
        if project:
            query["project"] = project
        try:
            cursor = (
                self.db[self.qa_collection]
                .find(query, {"_id": True, "question": True, "answer": True, "priority": True, "project": True, "updated_at": True, "created_at": True})
                .sort([("priority", -1), ("updated_at", -1)])
                .limit(max(10, min(int(limit), 5000)))
            )
            items: list[dict] = []
            async for doc in cursor:
                items.append(
                    {
                        "id": str(doc.get("_id")),
                        "question": doc.get("question", ""),
                        "answer": doc.get("answer", ""),
                        "priority": int(doc.get("priority", 0)),
                        "project": doc.get("project"),
                        "created_at": doc.get("created_at"),
                        "updated_at": doc.get("updated_at"),
                    }
                )
            return items
        except Exception as exc:
            logger.error("mongo_qa_list_failed", project=project, error=str(exc))
            raise

    async def insert_qa_pairs(self, project: str | None, items: list[dict[str, object]]) -> dict[str, int]:
        """Bulk insert/update QA pairs returning counters."""

        if not items:
            return {"inserted": 0, "updated": 0}

        now = time.time()
        inserted = 0
        updated = 0
        for item in items:
            question = str(item.get("question") or "").strip()
            answer = str(item.get("answer") or "").strip()
            if not question or not answer:
                continue
            priority = item.get("priority")
            try:
                priority_value = int(priority)
            except Exception:
                priority_value = 0
            payload = {
                "question": question,
                "answer": answer,
                "priority": priority_value,
                "project": project,
                "updated_at": now,
            }
            payload.setdefault("created_at", now)
            try:
                result = await self.db[self.qa_collection].update_one(
                    {"project": project, "question": question},
                    {"$set": payload, "$setOnInsert": {"created_at": now}},
                    upsert=True,
                )
                if result.upserted_id is not None:
                    inserted += 1
                elif result.modified_count:
                    updated += 1
            except Exception as exc:
                logger.warning(
                    "mongo_qa_upsert_failed",
                    project=project,
                    question=question,
                    error=str(exc),
                )
        return {"inserted": inserted, "updated": updated}

    async def update_qa_pair(self, pair_id: str, updates: dict[str, object]) -> dict | None:
        """Update single QA pair by ``pair_id`` and return updated document."""

        try:
            oid = ObjectId(pair_id)
        except Exception:
            return None

        payload: dict[str, object] = {"updated_at": time.time()}
        if "question" in updates:
            payload["question"] = str(updates["question"]).strip()
        if "answer" in updates:
            payload["answer"] = str(updates["answer"]).strip()
        if "priority" in updates and updates["priority"] is not None:
            try:
                payload["priority"] = int(updates["priority"])
            except Exception:
                payload["priority"] = 0
        try:
            doc = await self.db[self.qa_collection].find_one_and_update(
                {"_id": oid},
                {"$set": payload},
                return_document=True,
            )
            if not doc:
                return None
            return {
                "id": str(doc.get("_id")),
                "question": doc.get("question", ""),
                "answer": doc.get("answer", ""),
                "priority": int(doc.get("priority", 0)),
                "project": doc.get("project"),
                "created_at": doc.get("created_at"),
                "updated_at": doc.get("updated_at"),
            }
        except Exception as exc:
            logger.error("mongo_qa_update_failed", pair_id=pair_id, error=str(exc))
            raise

    async def delete_qa_pair(self, pair_id: str) -> bool:
        """Remove QA pair by ``pair_id``."""

        try:
            oid = ObjectId(pair_id)
        except Exception:
            return False
        try:
            result = await self.db[self.qa_collection].delete_one({"_id": oid})
            return bool(result.deleted_count)
        except Exception as exc:
            logger.error("mongo_qa_delete_failed", pair_id=pair_id, error=str(exc))
            raise

    async def reorder_qa_pairs(self, project: str | None, ordered_ids: list[str]) -> None:
        """Assign descending priority according to ``ordered_ids`` order."""

        if not ordered_ids:
            return
        priority = len(ordered_ids)
        for pair_id in ordered_ids:
            try:
                oid = ObjectId(pair_id)
            except Exception:
                continue
            try:
                await self.db[self.qa_collection].update_one(
                    {"_id": oid, "project": project},
                    {"$set": {"priority": priority, "updated_at": time.time()}},
                )
            except Exception as exc:
                logger.warning(
                    "mongo_qa_reorder_failed",
                    pair_id=pair_id,
                    project=project,
                    error=str(exc),
                )
            priority -= 1

    async def search_qa_pairs(
        self,
        query: str,
        project: str | None,
        *,
        limit: int = 10,
    ) -> list[dict[str, object]]:
        """Search QA pairs by text relevance."""

        cleaned = (query or "").strip()
        if not cleaned:
            return []
        filter_query: dict[str, object] = {}
        if project:
            filter_query["project"] = project
        projection = {
            "question": True,
            "answer": True,
            "priority": True,
            "project": True,
            "updated_at": True,
            "score": {"$meta": "textScore"},
        }
        try:
            cursor = (
                self.db[self.qa_collection]
                .find({"$and": [filter_query, {"$text": {"$search": cleaned}}]}, projection)
                .sort([
                    ("score", {"$meta": "textScore"}),
                    ("priority", -1),
                    ("updated_at", -1),
                ])
                .limit(max(5, min(int(limit), 50)))
            )
        except Exception as exc:
            logger.debug("mongo_qa_text_search_failed", error=str(exc), project=project)
            cursor = (
                self.db[self.qa_collection]
                .find(filter_query, {"question": True, "answer": True, "priority": True, "project": True, "updated_at": True})
                .sort([("priority", -1), ("updated_at", -1)])
                .limit(max(5, min(int(limit), 50)))
            )

        results: list[dict[str, object]] = []
        async for doc in cursor:
                results.append(
                    {
                        "id": str(doc.get("_id")),
                        "question": doc.get("question", ""),
                        "answer": doc.get("answer", ""),
                        "priority": int(doc.get("priority", 0)),
                        "project": doc.get("project"),
                        "score": doc.get("score"),
                        "updated_at": doc.get("updated_at"),
                    }
                )

        if results:
            return results[:limit]

        # Fallback: perform lightweight similarity scoring when text index misses.
        try:
            cursor = (
                self.db[self.qa_collection]
                .find(
                    filter_query,
                    {
                        "_id": True,
                        "question": True,
                        "answer": True,
                        "priority": True,
                        "project": True,
                        "updated_at": True,
                    },
                )
                .sort([("priority", -1), ("updated_at", -1)])
                .limit(200)
            )
            candidates = [self._serialize_qa(doc) async for doc in cursor]
        except Exception as exc:
            logger.debug("mongo_qa_similarity_fallback_failed", project=project, error=str(exc))
            return []

        if not candidates:
            return []

        scored: list[dict[str, object]] = []
        cleaned_lower = cleaned.lower()
        for doc in candidates:
            question_text = str(doc.get("question") or "")
            ratio = SequenceMatcher(None, question_text.lower(), cleaned_lower).ratio()
            if ratio < 0.35:
                continue
            enriched = doc | {"score": ratio}
            scored.append(enriched)

        scored.sort(key=lambda item: (item.get("score") or 0, item.get("priority") or 0), reverse=True)
        return scored[:limit]

    async def record_unanswered_question(
        self,
        *,
        project: str | None,
        question: str,
        metadata: dict[str, object] | None = None,
        ttl_seconds: int = 30 * 24 * 60 * 60,
    ) -> None:
        """Store unanswered ``question`` for statistics with TTL cleanup."""

        cleaned = (question or "").strip()
        if not cleaned:
            return
        now = time.time()
        payload = {
            "question": cleaned,
            "project": project,
            "metadata": metadata or {},
            "updated_at": now,
        }
        ttl_threshold = now - max(3600, int(ttl_seconds))
        try:
            await self.db[self.unanswered_collection].update_one(
                {"project": project, "question": cleaned},
                {
                    "$set": payload,
                    "$setOnInsert": {
                        "created_at": now,
                        "hits": 0,
                    },
                    "$inc": {"hits": 1},
                },
                upsert=True,
            )
            await self.db[self.unanswered_collection].delete_many({"updated_at": {"$lt": ttl_threshold}})
        except Exception as exc:
            logger.warning("mongo_unanswered_record_failed", project=project, error=str(exc))

    async def list_unanswered_questions(
        self,
        project: str | None,
        *,
        limit: int = 1000,
    ) -> list[dict[str, object]]:
        """Return unanswered questions for ``project`` sorted by recency."""

        query: dict[str, object] = {}
        if project:
            query["project"] = project
        try:
            cursor = (
                self.db[self.unanswered_collection]
                .find(query, {"_id": True, "question": True, "project": True, "hits": True, "created_at": True, "updated_at": True})
                .sort([("updated_at", -1)])
                .limit(max(10, min(int(limit), 5000)))
            )
            items: list[dict[str, object]] = []
            async for doc in cursor:
                items.append(
                    {
                        "id": str(doc.get("_id")),
                        "question": doc.get("question", ""),
                        "project": doc.get("project"),
                        "hits": int(doc.get("hits", 1)),
                        "created_at": doc.get("created_at"),
                        "updated_at": doc.get("updated_at"),
                    }
                )
            return items
        except Exception as exc:
            logger.error("mongo_unanswered_list_failed", project=project, error=str(exc))
            raise

    async def clear_unanswered_questions(self, project: str | None) -> int:
        """Remove unanswered statistics for ``project`` (or all when ``None``)."""

        query: dict[str, object] = {}
        if project:
            query["project"] = project
        try:
            result = await self.db[self.unanswered_collection].delete_many(query)
            return int(result.deleted_count or 0)
        except Exception as exc:
            logger.error("mongo_unanswered_clear_failed", project=project, error=str(exc))
            raise

    async def purge_stale_unanswered(self, older_than: float) -> int:
        """Remove unanswered entries with ``updated_at`` older than timestamp."""

        try:
            result = await self.db[self.unanswered_collection].delete_many({"updated_at": {"$lt": older_than}})
            return int(result.deleted_count or 0)
        except Exception as exc:
            logger.error("mongo_unanswered_purge_failed", older_than=older_than, error=str(exc))
            raise

    async def get_knowledge_priority(self, project: str | None) -> list[str]:
        """Return knowledge source priority order for ``project``."""

        key = f"knowledge_priority::{project or 'default'}"
        try:
            doc = await self.get_setting(key) or {}
        except Exception:
            doc = {}
        order = doc.get("order") if isinstance(doc, dict) else None
        if isinstance(order, list) and all(isinstance(item, str) for item in order):
            return order
        return []

    async def set_knowledge_priority(self, project: str | None, order: list[str]) -> None:
        """Persist knowledge source priority order for ``project``."""

        cleaned = [str(item).strip() for item in order if str(item).strip()]
        key = f"knowledge_priority::{project or 'default'}"
        payload = {
            "order": cleaned,
            "updated_at": time.time(),
        }
        await self.set_setting(key, payload)

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
        admin_username = data.get("admin_username")
        if isinstance(admin_username, str):
            admin_username = admin_username.strip().lower()
            data["admin_username"] = admin_username or None
        elif admin_username is None:
            data["admin_username"] = None
        else:
            data["admin_username"] = str(admin_username).strip().lower() or None
        admin_password_hash = data.get("admin_password_hash")
        if isinstance(admin_password_hash, str):
            data["admin_password_hash"] = admin_password_hash.strip() or None
        else:
            data["admin_password_hash"] = None
        for field in ("title", "llm_model", "llm_prompt", "llm_voice_model", "telegram_token", "max_token", "vk_token", "widget_url"):
            value = data.get(field)
            if isinstance(value, str):
                stripped = value.strip()
                data[field] = stripped or None
        emotions_value = data.get("llm_emotions_enabled")
        if isinstance(emotions_value, str):
            lowered = emotions_value.strip().lower()
            if lowered in {"false", "0", "off", "no"}:
                data["llm_emotions_enabled"] = False
            elif lowered in {"true", "1", "on", "yes"}:
                data["llm_emotions_enabled"] = True
            else:
                data["llm_emotions_enabled"] = True
        elif emotions_value is None:
            data["llm_emotions_enabled"] = True
        else:
            data["llm_emotions_enabled"] = bool(emotions_value)
        voice_value = data.get("llm_voice_enabled")
        if isinstance(voice_value, str):
            lowered = voice_value.strip().lower()
            if lowered in {"false", "0", "off", "no"}:
                data["llm_voice_enabled"] = False
            elif lowered in {"true", "1", "on", "yes"}:
                data["llm_voice_enabled"] = True
            else:
                data["llm_voice_enabled"] = True
        elif voice_value is None:
            data["llm_voice_enabled"] = True
        else:
            data["llm_voice_enabled"] = bool(voice_value)
        sources_value = data.get("llm_sources_enabled")
        if isinstance(sources_value, str):
            lowered = sources_value.strip().lower()
            if lowered in {"true", "1", "on", "yes"}:
                data["llm_sources_enabled"] = True
            elif lowered in {"false", "0", "off", "no", ""}:
                data["llm_sources_enabled"] = False
            else:
                data["llm_sources_enabled"] = False
        elif sources_value is None:
            data["llm_sources_enabled"] = False
        else:
            data["llm_sources_enabled"] = bool(sources_value)
        debug_value = data.get("debug_enabled")
        if isinstance(debug_value, str):
            lowered = debug_value.strip().lower()
            if lowered in {"true", "1", "on", "yes"}:
                data["debug_enabled"] = True
            elif lowered in {"false", "0", "off", "no"}:
                data["debug_enabled"] = False
            else:
                data["debug_enabled"] = False
        elif debug_value is None:
            data["debug_enabled"] = False
        else:
            data["debug_enabled"] = bool(debug_value)
        debug_info_value = data.get("debug_info_enabled")
        if isinstance(debug_info_value, str):
            lowered = debug_info_value.strip().lower()
            if lowered in {"true", "1", "on", "yes"}:
                data["debug_info_enabled"] = True
            elif lowered in {"false", "0", "off", "no"}:
                data["debug_info_enabled"] = False
            else:
                data["debug_info_enabled"] = False
        elif debug_info_value is None:
            data["debug_info_enabled"] = True
        else:
            data["debug_info_enabled"] = bool(debug_info_value)
        captions_value = data.get("knowledge_image_caption_enabled")
        if isinstance(captions_value, str):
            lowered = captions_value.strip().lower()
            if lowered in {"true", "1", "on", "yes"}:
                data["knowledge_image_caption_enabled"] = True
            elif lowered in {"false", "0", "off", "no"}:
                data["knowledge_image_caption_enabled"] = False
            else:
                data["knowledge_image_caption_enabled"] = True
        elif captions_value is None:
            data["knowledge_image_caption_enabled"] = True
        else:
            data["knowledge_image_caption_enabled"] = bool(captions_value)
        for field in ("telegram_auto_start", "max_auto_start", "vk_auto_start"):
            auto_value = data.get(field)
            if isinstance(auto_value, str):
                lowered = auto_value.strip().lower()
                if lowered in {"true", "1", "on", "yes"}:
                    data[field] = True
                elif lowered in {"false", "0", "off", "no"}:
                    data[field] = False
                else:
                    data[field] = None
            elif auto_value is None:
                data[field] = None
            else:
                data[field] = bool(auto_value)
        bitrix_enabled_value = data.get("bitrix_enabled")
        if isinstance(bitrix_enabled_value, str):
            lowered = bitrix_enabled_value.strip().lower()
            if lowered in {"true", "1", "on", "yes"}:
                data["bitrix_enabled"] = True
            elif lowered in {"false", "0", "off", "no", ""}:
                data["bitrix_enabled"] = False
            else:
                data["bitrix_enabled"] = None
        elif bitrix_enabled_value is None:
            data["bitrix_enabled"] = False
        else:
            data["bitrix_enabled"] = bool(bitrix_enabled_value)

        if isinstance(data.get("bitrix_webhook_url"), str):
            data["bitrix_webhook_url"] = data["bitrix_webhook_url"].strip() or None

        mail_enabled_value = data.get("mail_enabled")
        if isinstance(mail_enabled_value, str):
            lowered = mail_enabled_value.strip().lower()
            if lowered in {"true", "1", "on", "yes"}:
                data["mail_enabled"] = True
            elif lowered in {"false", "0", "off", "no", ""}:
                data["mail_enabled"] = False
            else:
                data["mail_enabled"] = None
        elif mail_enabled_value is None:
            data["mail_enabled"] = False
        else:
            data["mail_enabled"] = bool(mail_enabled_value)

        for field in ("mail_imap_ssl", "mail_smtp_tls"):
            raw = data.get(field)
            if isinstance(raw, str):
                lowered = raw.strip().lower()
                if lowered in {"true", "1", "on", "yes"}:
                    data[field] = True
                elif lowered in {"false", "0", "off", "no", ""}:
                    data[field] = False
                else:
                    data[field] = None
            elif raw is not None:
                data[field] = bool(raw)

        for field in ("mail_imap_port", "mail_smtp_port"):
            raw_port = data.get(field)
            if isinstance(raw_port, str):
                try:
                    data[field] = int(raw_port)
                except ValueError:
                    data[field] = None
            elif isinstance(raw_port, (int, float)):
                data[field] = int(raw_port)
            elif raw_port is None:
                data[field] = None

        for field in (
            "mail_imap_host",
            "mail_smtp_host",
            "mail_username",
            "mail_password",
            "mail_from",
            "mail_signature",
        ):
            if isinstance(data.get(field), str):
                data[field] = data[field].strip() or None

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
        if data.get("admin_username"):
            data["admin_username"] = str(data["admin_username"]).strip().lower() or None
        for field in ("telegram_token", "max_token", "vk_token"):
            if data.get(field):
                data[field] = str(data[field]).strip() or None
        if data.get("bitrix_webhook_url"):
            data["bitrix_webhook_url"] = str(data["bitrix_webhook_url"]).strip() or None
        if "bitrix_enabled" in data and data["bitrix_enabled"] is not None:
            data["bitrix_enabled"] = bool(data["bitrix_enabled"])
        for field in ("telegram_auto_start", "max_auto_start", "vk_auto_start"):
            if field in data and data[field] is not None:
                data[field] = bool(data[field])
        if "llm_voice_enabled" in data and data["llm_voice_enabled"] is not None:
            data["llm_voice_enabled"] = bool(data["llm_voice_enabled"])
        if "llm_sources_enabled" in data and data["llm_sources_enabled"] is not None:
            data["llm_sources_enabled"] = bool(data["llm_sources_enabled"])
        if data.get("llm_voice_model"):
            data["llm_voice_model"] = str(data["llm_voice_model"]).strip() or None
        if "knowledge_image_caption_enabled" in data and data["knowledge_image_caption_enabled"] is not None:
            data["knowledge_image_caption_enabled"] = bool(data["knowledge_image_caption_enabled"])
        if "mail_enabled" in data and data["mail_enabled"] is not None:
            data["mail_enabled"] = bool(data["mail_enabled"])
        for field in ("mail_imap_ssl", "mail_smtp_tls"):
            if field in data and data[field] is not None:
                data[field] = bool(data[field])
        for field in ("mail_imap_port", "mail_smtp_port"):
            if data.get(field) is not None:
                try:
                    data[field] = int(data[field])
                except (TypeError, ValueError):
                    data[field] = None
        for field in (
            "mail_imap_host",
            "mail_smtp_host",
            "mail_username",
            "mail_password",
            "mail_from",
            "mail_signature",
        ):
            if isinstance(data.get(field), str):
                data[field] = data[field].strip() or None
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

    async def delete_project(
        self,
        domain: str,
        *,
        documents_collection: str,
        contexts_collection: str,
        stats_collection: str | None = None,
    ) -> dict[str, int]:
        """Remove project metadata, knowledge documents and related data."""

        project_key = (domain or "").strip().lower()
        summary = {
            "documents": 0,
            "files": 0,
            "contexts": 0,
            "stats": 0,
            "projects": 0,
        }

        if not project_key:
            return summary

        # Collect knowledge documents for the project and remove them together
        doc_query = {
            "$or": [
                {"project": project_key},
                {"domain": project_key},
            ]
        }

        file_ids: list[str] = []
        orphan_ids: list[ObjectId] = []
        try:
            cursor = self.db[documents_collection].find(doc_query, {"fileId": 1, "_id": 1})
            async for doc in cursor:
                file_id = doc.get("fileId")
                if file_id:
                    file_ids.append(str(file_id))
                else:
                    oid = doc.get("_id")
                    if isinstance(oid, ObjectId):
                        orphan_ids.append(oid)
        except Exception as exc:
            logger.error("mongo_list_project_documents_failed", project=project_key, error=str(exc))
            raise

        for file_id in file_ids:
            try:
                await self.delete_document(documents_collection, file_id)
                summary["documents"] += 1
                summary["files"] += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "mongo_delete_project_document_failed",
                    project=project_key,
                    file_id=file_id,
                    error=str(exc),
                )

        if orphan_ids:
            try:
                result = await self.db[documents_collection].delete_many({"_id": {"$in": orphan_ids}})
                summary["documents"] += int(result.deleted_count or 0)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "mongo_delete_project_orphans_failed",
                    project=project_key,
                    error=str(exc),
                )

        # Delete chat contexts linked to the project
        try:
            result = await self.db[contexts_collection].delete_many({"project": project_key})
            summary["contexts"] = int(result.deleted_count or 0)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "mongo_delete_project_contexts_failed",
                project=project_key,
                error=str(exc),
            )

        # Remove request statistics for the project
        stats_coll = stats_collection or self.stats_collection
        try:
            result = await self.db[stats_coll].delete_many({"project": project_key})
            summary["stats"] = int(result.deleted_count or 0)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "mongo_delete_project_stats_failed",
                project=project_key,
                error=str(exc),
            )

        # Finally remove the project metadata entries
        try:
            projects_removed = 0
            for field in ("name", "domain"):
                result = await self.db[self.projects_collection].delete_many({field: project_key})
                projects_removed += int(result.deleted_count or 0)
            summary["projects"] = projects_removed
        except Exception as exc:
            logger.error("mongo_delete_project_failed", project=project_key, error=str(exc))
            raise

        summary["file_ids"] = file_ids
        return summary

    async def list_ollama_servers(self) -> list[OllamaServer]:
        try:
            cursor = self.db[self.ollama_servers_collection].find({}, {"_id": False})
            servers: list[OllamaServer] = []
            async for item in cursor:
                try:
                    servers.append(OllamaServer(**item))
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "mongo_ollama_server_parse_failed",
                        server=item,
                        error=str(exc),
                    )
            return servers
        except Exception as exc:
            logger.error("mongo_list_ollama_servers_failed", error=str(exc))
            raise

    async def get_ollama_server(self, name: str) -> OllamaServer | None:
        try:
            doc = await self.db[self.ollama_servers_collection].find_one(
                {"name": name.strip().lower()},
                {"_id": False},
            )
            return OllamaServer(**doc) if doc else None
        except Exception as exc:
            logger.error("mongo_get_ollama_server_failed", name=name, error=str(exc))
            raise

    async def upsert_ollama_server(self, server: OllamaServer) -> OllamaServer:
        payload = server.model_dump()
        payload["name"] = server.name.strip().lower()
        payload["base_url"] = server.base_url.rstrip('/')
        now = time.time()
        payload.setdefault("created_at", now)
        payload["updated_at"] = now
        try:
            await self.db[self.ollama_servers_collection].update_one(
                {"name": payload["name"]},
                {"$set": payload},
                upsert=True,
            )
            stored = await self.db[self.ollama_servers_collection].find_one(
                {"name": payload["name"]},
                {"_id": False},
            )
            return OllamaServer(**stored) if stored else server
        except Exception as exc:
            logger.error("mongo_upsert_ollama_server_failed", name=server.name, error=str(exc))
            raise

    async def delete_ollama_server(self, name: str) -> bool:
        key = name.strip().lower()
        try:
            result = await self.db[self.ollama_servers_collection].delete_one({"name": key})
            return bool(result.deleted_count)
        except Exception as exc:
            logger.error("mongo_delete_ollama_server_failed", name=key, error=str(exc))
            raise

    async def update_ollama_server_stats(
        self,
        name: str,
        *,
        avg_latency_ms: float,
        requests_last_hour: int,
        total_duration_ms: float,
    ) -> None:
        key = name.strip().lower()
        stats_payload = {
            "avg_latency_ms": float(avg_latency_ms),
            "requests_last_hour": int(requests_last_hour),
            "total_duration_ms": float(total_duration_ms),
            "updated_at": time.time(),
        }
        try:
            await self.db[self.ollama_servers_collection].update_one(
                {"name": key},
                {
                    "$set": {
                        "stats": stats_payload,
                        "updated_at": time.time(),
                    }
                },
            )
        except Exception as exc:
            logger.debug(
                "mongo_update_ollama_server_stats_failed",
                name=key,
                error=str(exc),
            )

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

    async def get_project_by_admin_username(self, username: str) -> Project | None:
        normalized = (username or "").strip().lower()
        if not normalized:
            return None
        try:
            doc = await self.db[self.projects_collection].find_one(
                {"admin_username": normalized},
                {"_id": False},
            )
            return self._project_from_doc(doc)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "mongo_get_project_by_admin_failed",
                username=normalized,
                error=str(exc),
            )
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

    async def get_backup_settings(self) -> BackupSettings:
        stored = await self.get_setting("backup_settings") or {}
        return self._serialize_backup_settings(stored)

    async def get_backup_token(self) -> str | None:
        stored = await self.get_setting("backup_settings") or {}
        token = stored.get("ya_disk_token")
        if isinstance(token, str):
            cleaned = token.strip()
            return cleaned or None
        return None

    async def update_backup_settings(
        self,
        updates: dict[str, Any],
        *,
        token: str | object = TOKEN_UNSET,
        clear_token: bool = False,
    ) -> BackupSettings:
        stored = await self.get_setting("backup_settings") or {}

        if "enabled" in updates:
            stored["enabled"] = bool(updates.get("enabled"))

        if "hour" in updates:
            try:
                stored["hour"] = max(0, min(23, int(updates["hour"])))
            except (TypeError, ValueError):
                stored["hour"] = stored.get("hour", 3)

        if "minute" in updates:
            try:
                stored["minute"] = max(0, min(59, int(updates["minute"])))
            except (TypeError, ValueError):
                stored["minute"] = stored.get("minute", 0)

        if "timezone" in updates:
            tz_raw = updates.get("timezone")
            if tz_raw in (None, ""):
                stored["timezone"] = "UTC"
            else:
                stored["timezone"] = str(tz_raw).strip()

        folder_value = updates.get("ya_disk_folder")
        if folder_value is None and "yaDiskFolder" in updates:
            folder_value = updates.get("yaDiskFolder")
        if folder_value is not None:
            folder_clean = str(folder_value).strip().strip("/")
            stored["ya_disk_folder"] = folder_clean or "sitellm-backups"

        if token is not TOKEN_UNSET:
            if token in (None, ""):
                stored["ya_disk_token"] = None
            else:
                stored["ya_disk_token"] = str(token).strip()
        elif clear_token:
            stored["ya_disk_token"] = None

        stored["updated_at"] = time.time()

        await self.set_setting("backup_settings", stored)
        return self._serialize_backup_settings(stored)

    async def record_backup_runtime(
        self,
        *,
        last_run_at: float | None = None,
        last_success_at: float | None = None,
        last_attempt_date: str | None = None,
    ) -> BackupSettings:
        stored = await self.get_setting("backup_settings") or {}
        if last_run_at is not None:
            stored["last_run_at"] = float(last_run_at)
        if last_success_at is not None:
            stored["last_success_at"] = float(last_success_at)
        if last_attempt_date is not None:
            stored["last_attempt_date"] = str(last_attempt_date)
        stored["updated_at"] = time.time()
        await self.set_setting("backup_settings", stored)
        return self._serialize_backup_settings(stored)

    def _serialize_backup_settings(self, stored: dict[str, Any]) -> BackupSettings:
        payload: dict[str, Any] = {}
        payload["enabled"] = bool(stored.get("enabled"))
        try:
            payload["hour"] = max(0, min(23, int(stored.get("hour", 3))))
        except (TypeError, ValueError):
            payload["hour"] = 3
        try:
            payload["minute"] = max(0, min(59, int(stored.get("minute", 0))))
        except (TypeError, ValueError):
            payload["minute"] = 0
        tz_value = stored.get("timezone") or "UTC"
        payload["timezone"] = str(tz_value).strip() or "UTC"
        folder = stored.get("ya_disk_folder") or "sitellm-backups"
        payload["yaDiskFolder"] = str(folder).strip().strip("/") or "sitellm-backups"
        payload["tokenSet"] = bool(stored.get("ya_disk_token"))

        last_run = stored.get("last_run_at")
        if isinstance(last_run, (int, float)):
            payload["lastRunAt"] = float(last_run)
            payload["lastRunAtIso"] = datetime.fromtimestamp(float(last_run), timezone.utc).isoformat()
        last_success = stored.get("last_success_at")
        if isinstance(last_success, (int, float)):
            payload["lastSuccessAt"] = float(last_success)
            payload["lastSuccessAtIso"] = datetime.fromtimestamp(float(last_success), timezone.utc).isoformat()
        attempt_date = stored.get("last_attempt_date")
        if isinstance(attempt_date, str) and attempt_date:
            payload["lastAttemptDate"] = attempt_date

        return BackupSettings.model_validate(payload, from_attributes=False)

    def _serialize_backup_job(self, doc: dict[str, Any] | None) -> BackupJob | None:
        if not doc:
            return None
        payload = doc.copy()
        payload["id"] = str(payload.pop("_id"))
        payload.setdefault("createdAt", payload.get("created_at", time.time()))
        payload.setdefault("createdAtIso", payload.get("created_at_iso"))
        payload.setdefault("startedAt", payload.get("started_at"))
        payload.setdefault("startedAtIso", payload.get("started_at_iso"))
        payload.setdefault("finishedAt", payload.get("finished_at"))
        payload.setdefault("finishedAtIso", payload.get("finished_at_iso"))
        payload.setdefault("remotePath", payload.get("remote_path"))
        payload.setdefault("sizeBytes", payload.get("size_bytes"))
        payload.setdefault("triggeredBy", payload.get("triggered_by"))
        payload.setdefault("sourceJobId", payload.get("source_job_id"))
        payload["operation"] = BackupOperation(payload.get("operation", "backup"))
        payload["status"] = BackupStatus(payload.get("status", "queued"))
        return BackupJob.model_validate(payload, from_attributes=False)

    async def create_backup_job(
        self,
        *,
        operation: BackupOperation,
        status: BackupStatus,
        triggered_by: str | None = None,
        remote_path: str | None = None,
        size_bytes: int | None = None,
        source_job_id: str | None = None,
    ) -> BackupJob:
        now = time.time()
        doc: dict[str, Any] = {
            "operation": operation.value,
            "status": status.value,
            "remote_path": remote_path,
            "size_bytes": size_bytes,
            "triggered_by": triggered_by,
            "created_at": now,
            "created_at_iso": datetime.fromtimestamp(now, timezone.utc).isoformat(),
            "source_job_id": source_job_id,
        }
        result = await self.db[self.backup_jobs_collection].insert_one(doc)
        doc["_id"] = result.inserted_id
        return self._serialize_backup_job(doc)

    async def update_backup_job(self, job_id: str, updates: dict[str, Any]) -> BackupJob | None:
        try:
            obj_id = ObjectId(job_id)
        except Exception:
            return None

        payload = updates.copy()
        for field in ("started_at", "finished_at", "created_at"):
            if field in payload and isinstance(payload[field], (int, float)):
                suffix = f"{field}_iso"
                payload[suffix] = datetime.fromtimestamp(float(payload[field]), timezone.utc).isoformat()
        if "status" in payload and isinstance(payload["status"], BackupStatus):
            payload["status"] = payload["status"].value
        if "operation" in payload and isinstance(payload["operation"], BackupOperation):
            payload["operation"] = payload["operation"].value

        await self.db[self.backup_jobs_collection].update_one(
            {"_id": obj_id},
            {"$set": payload},
        )
        doc = await self.db[self.backup_jobs_collection].find_one({"_id": obj_id})
        return self._serialize_backup_job(doc)

    async def get_backup_job(self, job_id: str) -> BackupJob | None:
        try:
            obj_id = ObjectId(job_id)
        except Exception:
            return None
        doc = await self.db[self.backup_jobs_collection].find_one({"_id": obj_id})
        return self._serialize_backup_job(doc)

    async def list_backup_jobs(self, limit: int = 20) -> list[BackupJob]:
        cursor = (
            self.db[self.backup_jobs_collection]
            .find({}, sort=[("created_at", -1)])
            .limit(max(1, min(limit, 100)))
        )
        jobs: list[BackupJob] = []
        async for doc in cursor:
            job = self._serialize_backup_job(doc)
            if job is not None:
                jobs.append(job)
        return jobs

    async def find_active_backup_job(self) -> BackupJob | None:
        doc = await self.db[self.backup_jobs_collection].find_one(
            {"status": {"$in": [BackupStatus.queued.value, BackupStatus.running.value]}},
            sort=[("created_at", -1)],
        )
        return self._serialize_backup_job(doc)

    def _serialize_feedback_task(self, doc: dict | None) -> dict | None:
        if not doc:
            return None
        payload: dict[str, object] = {
            "id": str(doc.get("_id")),
            "message": doc.get("message"),
            "name": doc.get("name"),
            "contact": doc.get("contact"),
            "page": doc.get("page"),
            "project": doc.get("project"),
            "source": doc.get("source"),
            "status": doc.get("status", "open"),
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at"),
            "created_at_iso": doc.get("created_at_iso"),
            "updated_at_iso": doc.get("updated_at_iso"),
            "note": doc.get("note"),
        }
        count = doc.get("count")
        if count is not None:
            payload["count"] = count
        return payload

    async def create_feedback_task(self, payload: dict[str, object]) -> dict:
        now = time.time()
        document = {
            "message": str(payload.get("message") or "").strip(),
            "name": (str(payload.get("name")).strip() or None) if payload.get("name") else None,
            "contact": (str(payload.get("contact")).strip() or None) if payload.get("contact") else None,
            "page": (str(payload.get("page")).strip() or None) if payload.get("page") else None,
            "project": (str(payload.get("project")).strip().lower() or None) if payload.get("project") else None,
            "source": (str(payload.get("source")) or "web").strip().lower(),
            "status": "open",
            "count": int(payload.get("count") or 1),
            "created_at": now,
            "updated_at": now,
            "created_at_iso": datetime.utcfromtimestamp(now).isoformat(),
            "updated_at_iso": datetime.utcfromtimestamp(now).isoformat(),
        }
        try:
            result = await self.db[self.feedback_collection].insert_one(document)
            document["_id"] = result.inserted_id
            return self._serialize_feedback_task(document) or {}
        except Exception as exc:
            logger.error("mongo_feedback_create_failed", error=str(exc))
            raise

    async def list_feedback_tasks(self, *, limit: int = 100) -> list[dict]:
        try:
            cursor = (
                self.db[self.feedback_collection]
                .find({}, {"_id": True, "message": True, "name": True, "contact": True, "page": True, "project": True, "source": True, "status": True, "created_at": True, "updated_at": True, "created_at_iso": True, "updated_at_iso": True, "note": True, "count": True})
                .sort("created_at", -1)
                .limit(max(10, min(int(limit), 200)))
            )
            tasks: list[dict] = []
            async for doc in cursor:
                serialized = self._serialize_feedback_task(doc)
                if serialized:
                    tasks.append(serialized)
            return tasks
        except Exception as exc:
            logger.error("mongo_feedback_list_failed", error=str(exc))
            raise

    async def update_feedback_task(self, task_id: str, updates: dict[str, object]) -> dict | None:
        try:
            oid = ObjectId(task_id)
        except Exception:
            return None
        payload: dict[str, object] = {}
        if "status" in updates:
            payload["status"] = str(updates["status"])
        if "note" in updates and updates["note"] is not None:
            payload["note"] = str(updates["note"])
        now = time.time()
        payload["updated_at"] = now
        payload["updated_at_iso"] = datetime.utcfromtimestamp(now).isoformat()
        try:
            result = await self.db[self.feedback_collection].find_one_and_update(
                {"_id": oid},
                {"$set": payload},
                return_document=True,
            )
            return self._serialize_feedback_task(result)
        except Exception as exc:
            logger.error("mongo_feedback_update_failed", task_id=task_id, error=str(exc))
            raise

    async def bulk_insert_qa(self, project: str, pairs: list[dict[str, object]], *, default_priority: int = 0) -> int:
        if not project:
            raise ValueError("project is required")
        now = time.time()
        documents = []
        for idx, pair in enumerate(pairs):
            question = str(pair.get("question") or "").strip()
            answer = str(pair.get("answer") or "").strip()
            if not question or not answer:
                continue
            documents.append(
                {
                    "project": project,
                    "question": question,
                    "answer": answer,
                    "priority": int(pair.get("priority") or default_priority),
                    "created_at": now + idx * 0.001,
                    "updated_at": now + idx * 0.001,
                }
            )
        if not documents:
            return 0
        try:
            result = await self.db[self.qa_collection].insert_many(documents)
            return len(result.inserted_ids)
        except Exception as exc:
            logger.error("mongo_qa_bulk_insert_failed", project=project, error=str(exc))
            raise

    async def create_qa_pair(self, project: str, question: str, answer: str, *, priority: int = 0) -> dict:
        if not project:
            raise ValueError("project is required")
        question = question.strip()
        answer = answer.strip()
        if not question or not answer:
            raise ValueError("question and answer are required")
        now = time.time()
        doc = {
            "project": project,
            "question": question,
            "answer": answer,
            "priority": int(priority),
            "created_at": now,
            "updated_at": now,
        }
        try:
            result = await self.db[self.qa_collection].insert_one(doc)
            doc["_id"] = result.inserted_id
            return self._serialize_qa(doc)
        except Exception as exc:
            logger.error("mongo_qa_create_failed", project=project, error=str(exc))
            raise

    def _serialize_qa(self, doc: dict | None) -> dict:
        if not doc:
            return {}
        return {
            "id": str(doc.get("_id")),
            "project": doc.get("project"),
            "question": doc.get("question"),
            "answer": doc.get("answer"),
            "priority": int(doc.get("priority") or 0),
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at"),
            "created_at_iso": doc.get("created_at_iso"),
            "updated_at_iso": doc.get("updated_at_iso"),
        }

    async def list_qa_pairs(self, project: str, *, limit: int = 500) -> list[dict]:
        if not project:
            return []
        try:
            cursor = (
                self.db[self.qa_collection]
                .find({"project": project}, {"_id": True, "question": True, "answer": True, "priority": True, "created_at": True, "updated_at": True})
                .sort([("priority", -1), ("updated_at", -1)])
                .limit(max(10, min(int(limit), 1000)))
            )
            pairs = [self._serialize_qa(doc) async for doc in cursor]
            return pairs
        except Exception as exc:
            logger.error("mongo_qa_list_failed", project=project, error=str(exc))
            raise

    async def update_qa_pair(self, qa_id: str, *, question: str | None = None, answer: str | None = None, priority: int | None = None) -> dict | None:
        try:
            oid = ObjectId(qa_id)
        except Exception:
            return None
        updates: dict[str, object] = {}
        if question is not None:
            updates["question"] = question.strip()
        if answer is not None:
            updates["answer"] = answer.strip()
        if priority is not None:
            updates["priority"] = int(priority)
        updates["updated_at"] = time.time()
        try:
            result = await self.db[self.qa_collection].find_one_and_update(
                {"_id": oid},
                {"$set": updates},
                return_document=True,
            )
            return self._serialize_qa(result)
        except Exception as exc:
            logger.error("mongo_qa_update_failed", qa_id=qa_id, error=str(exc))
            raise

    async def delete_qa_pair(self, qa_id: str) -> bool:
        try:
            oid = ObjectId(qa_id)
        except Exception:
            return False
        try:
            result = await self.db[self.qa_collection].delete_one({"_id": oid})
            return bool(result.deleted_count)
        except Exception as exc:
            logger.error("mongo_qa_delete_failed", qa_id=qa_id, error=str(exc))
            raise

    async def reorder_qa_pairs(self, project: str, ordered_ids: list[str]) -> None:
        if not project or not ordered_ids:
            return
        try:
            bulk = self.db[self.qa_collection].initialize_unordered_bulk_op()
        except AttributeError:
            # PyMongo 4 removed bulk API; fallback to manual updates
            new_priority = len(ordered_ids)
            for qa_id in ordered_ids:
                try:
                    await self.update_qa_pair(qa_id, priority=new_priority)
                except Exception:
                    continue
                new_priority -= 1
            return
        new_priority = len(ordered_ids)
        for qa_id in ordered_ids:
            try:
                oid = ObjectId(qa_id)
            except Exception:
                continue
            bulk.find({"_id": oid, "project": project}).update({"$set": {"priority": new_priority, "updated_at": time.time()}})
            new_priority -= 1
        try:
            bulk.execute()
        except Exception as exc:
            logger.debug("mongo_qa_reorder_failed", project=project, error=str(exc))

    async def log_unanswered_question(self, *, project: str | None, question: str, channel: str | None, session_id: str | None) -> None:
        question = (question or "").strip()
        if not question:
            return
        normalized_project = (project or "").strip().lower() or None
        question_hash = hashlib.sha1(question.lower().encode("utf-8", "ignore")).hexdigest()
        now = time.time()
        payload = {
            "question": question,
            "hash": question_hash,
            "project": normalized_project,
            "channel": (channel or "widget").strip().lower(),
            "session_id": session_id,
            "updated_at": now,
            "updated_at_iso": datetime.utcfromtimestamp(now).isoformat(),
        }
        try:
            await self.db[self.unanswered_collection].update_one(
                {"hash": question_hash, "project": normalized_project},
                {
                    "$set": payload,
                    "$setOnInsert": {
                        "created_at": now,
                        "created_at_iso": datetime.utcfromtimestamp(now).isoformat(),
                        "count": 0,
                    },
                    "$inc": {"count": 1},
                },
                upsert=True,
            )
        except Exception as exc:
            logger.debug("mongo_unanswered_log_failed", question=question[:32], error=str(exc))
        cutoff = time.time() - 30 * 86400
        try:
            await self.db[self.unanswered_collection].delete_many({"updated_at": {"$lt": cutoff}})
        except Exception:  # noqa: BLE001
            pass

    def _serialize_feedback_task(self, doc: dict | None) -> dict | None:
        if not doc:
            return None
        payload: dict[str, object] = {
            "id": str(doc.get("_id")),
            "message": doc.get("message"),
            "name": doc.get("name"),
            "contact": doc.get("contact"),
            "page": doc.get("page"),
            "project": doc.get("project"),
            "source": doc.get("source"),
            "status": doc.get("status", "open"),
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at"),
            "created_at_iso": doc.get("created_at_iso"),
            "updated_at_iso": doc.get("updated_at_iso"),
        }
        return payload

    async def create_feedback_task(self, payload: dict[str, object]) -> dict:
        now = time.time()
        document = {
            "message": str(payload.get("message") or "").strip(),
            "name": (str(payload.get("name")).strip() or None) if payload.get("name") else None,
            "contact": (str(payload.get("contact")).strip() or None) if payload.get("contact") else None,
            "page": (str(payload.get("page")).strip() or None) if payload.get("page") else None,
            "project": (str(payload.get("project")).strip() or None) if payload.get("project") else None,
            "source": (str(payload.get("source")) or "web").strip(),
            "status": "open",
            "created_at": now,
            "updated_at": now,
            "created_at_iso": datetime.utcfromtimestamp(now).isoformat(),
            "updated_at_iso": datetime.utcfromtimestamp(now).isoformat(),
        }
        try:
            result = await self.db[self.feedback_collection].insert_one(document)
            document["_id"] = result.inserted_id
            return self._serialize_feedback_task(document) or {}
        except Exception as exc:
            logger.error("mongo_feedback_create_failed", error=str(exc))
            raise

    async def list_feedback_tasks(self, *, limit: int = 100) -> list[dict]:
        try:
            cursor = (
                self.db[self.feedback_collection]
                .find({}, {"_id": True, "message": True, "name": True, "contact": True, "page": True, "project": True, "source": True, "status": True, "created_at": True, "updated_at": True, "created_at_iso": True, "updated_at_iso": True})
                .sort("created_at", -1)
                .limit(max(10, min(int(limit), 200)))
            )
            tasks: list[dict] = []
            async for doc in cursor:
                serialized = self._serialize_feedback_task(doc)
                if serialized:
                    tasks.append(serialized)
            return tasks
        except Exception as exc:
            logger.error("mongo_feedback_list_failed", error=str(exc))
            raise

    async def update_feedback_task(self, task_id: str, updates: dict[str, object]) -> dict | None:
        try:
            oid = ObjectId(task_id)
        except Exception:
            return None
        payload: dict[str, object] = {}
        if "status" in updates:
            payload["status"] = str(updates["status"])
        if "note" in updates and updates["note"] is not None:
            payload["note"] = str(updates["note"])
        now = time.time()
        payload["updated_at"] = now
        payload["updated_at_iso"] = datetime.utcfromtimestamp(now).isoformat()
        try:
            result = await self.db[self.feedback_collection].find_one_and_update(
                {"_id": oid},
                {"$set": payload},
                return_document=True,
            )
            return self._serialize_feedback_task(result)
        except Exception as exc:
            logger.error("mongo_feedback_update_failed", task_id=task_id, error=str(exc))
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
            await self.db[self.qa_collection].create_index(
                [
                    ("project", 1),
                    ("priority", -1),
                    ("created_at", -1),
                ],
                name="qa_project_priority",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "mongo_index_create_failed",
                collection=self.qa_collection,
                index="qa_project_priority",
                error=str(exc),
            )
        try:
            await self.db[self.qa_collection].create_index(
                [("project", 1), ("question", 1)],
                name="qa_project_question_unique",
                unique=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "mongo_index_create_failed",
                collection=self.qa_collection,
                index="qa_project_question_unique",
                error=str(exc),
            )

        try:
            await self.db[self.qa_collection].create_index(
                [
                    ("question", "text"),
                    ("answer", "text"),
                ],
                name="qa_text_index",
                default_language="russian",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "mongo_index_create_failed",
                collection=self.qa_collection,
                index="qa_text_index",
                error=str(exc),
            )

        try:
            await self.db[self.unanswered_collection].create_index(
                [("project", 1), ("updated_at", -1)],
                name="unanswered_project_updated",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "mongo_index_create_failed",
                collection=self.unanswered_collection,
                index="unanswered_project_updated",
                error=str(exc),
            )
        try:
            await self.db[self.unanswered_collection].create_index(
                "updated_at",
                name="unanswered_updated_at",
                expireAfterSeconds=int(os.getenv("KNOWLEDGE_UNANSWERED_TTL", 45 * 24 * 60 * 60)),
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "mongo_index_create_failed",
                collection=self.unanswered_collection,
                index="unanswered_updated_at",
                error=str(exc),
            )

        try:
            await self.db[self.unanswered_collection].create_index(
                [("project", 1), ("hash", 1)],
                name="unanswered_project_hash",
                unique=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "mongo_index_create_failed",
                collection=self.unanswered_collection,
                index="unanswered_project_hash",
                error=str(exc),
            )

        try:
            await self.db[self.qa_collection].create_index(
                [
                    ("project", 1),
                    ("priority", -1),
                    ("created_at", -1),
                ],
                name="qa_project_priority",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "mongo_index_create_failed",
                collection=self.qa_collection,
                index="qa_project_priority",
                error=str(exc),
            )
        try:
            await self.db[self.qa_collection].create_index(
                [
                    ("question", "text"),
                    ("answer", "text"),
                ],
                name="qa_text_index",
                default_language="russian",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "mongo_index_create_failed",
                collection=self.qa_collection,
                index="qa_text_index",
                error=str(exc),
            )

        try:
            await self.db[self.projects_collection].create_index(
                "admin_username",
                name="project_admin_username_unique",
                unique=True,
                sparse=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "mongo_index_create_failed",
                collection=self.projects_collection,
                index="project_admin_username_unique",
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

        try:
            await self.db[self.stats_collection].create_index(
                [("project", 1), ("date", 1)],
                name="request_stats_project_date",
            )
            await self.db[self.stats_collection].create_index(
                "date",
                name="request_stats_date",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "mongo_index_create_failed",
                collection=self.stats_collection,
                index="request_stats_project_date",
                error=str(exc),
            )
        try:
            await self.db[self.stats_collection].create_index(
                "ts",
                name="request_stats_ts_ttl",
                expireAfterSeconds=60 * 60 * 24 * 3,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "mongo_index_create_failed",
                collection=self.stats_collection,
                index="request_stats_ts_ttl",
                error=str(exc),
            )

        try:
            await self.db[self.ollama_servers_collection].create_index(
                "name",
                name="ollama_server_name_unique",
                unique=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "mongo_index_create_failed",
                collection=self.ollama_servers_collection,
                index="ollama_server_name_unique",
                error=str(exc),
            )

        try:
            await self.db[self.voice_samples_collection].create_index(
                [("project", 1), ("uploadedAt", -1)],
                name="voice_samples_project_uploaded",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "mongo_index_create_failed",
                collection=self.voice_samples_collection,
                index="voice_samples_project_uploaded",
                error=str(exc),
            )

        try:
            await self.db[self.voice_jobs_collection].create_index(
                [("project", 1), ("createdAt", -1)],
                name="voice_jobs_project_created",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "mongo_index_create_failed",
                collection=self.voice_jobs_collection,
                index="voice_jobs_project_created",
                error=str(exc),
            )

        try:
            await self.db[self.backup_jobs_collection].create_index(
                [("created_at", -1)],
                name="backup_jobs_created_at",
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "mongo_index_create_failed",
                collection=self.backup_jobs_collection,
                index="backup_jobs_created_at",
                error=str(exc),
            )

        self._indexes_ready = True

    async def log_request_stat(
        self,
        *,
        project: str | None,
        question: str | None,
        response_chars: int | None,
        attachments: int | None,
        prompt_chars: int | None,
        channel: str,
        session_id: str | None,
        user_id: str | None,
        error: str | None = None,
    ) -> None:
        """Persist a single request statistic entry."""

        try:
            now = datetime.now(timezone.utc)
            day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            doc = {
                "ts": now,
                "date": day,
                "project": (project or "__default__").strip().lower(),
                "question": question[:1024] if question else None,
                "response_chars": int(response_chars or 0),
                "attachments": int(attachments or 0),
                "prompt_chars": int(prompt_chars or 0) if prompt_chars is not None else None,
                "channel": channel,
                "session_id": session_id,
                "user_id": user_id,
                "error": error,
            }
            await self.db[self.stats_collection].insert_one(doc)
        except Exception as exc:  # noqa: BLE001
            logger.debug("stats_log_failed", project=project, error=str(exc))

    async def aggregate_project_storage(
        self,
        documents_collection: str,
        contexts_collection: str,
    ) -> dict[str, dict[str, float | int]]:
        """Return storage metrics per project for documents and contexts."""

        result: dict[str, dict[str, float | int]] = {}

        def _ensure(project_key: str) -> dict[str, float | int]:
            return result.setdefault(
                project_key,
                {
                    "documents_bytes": 0.0,
                    "document_count": 0,
                    "binary_bytes": 0.0,
                    "context_bytes": 0.0,
                    "context_count": 0,
                },
            )

        project_expr = {
            "$ifNull": [
                {
                    "$cond": [
                        {"$gt": [{"$strLenCP": {"$ifNull": ["$project", ""]}}, 0]},
                        {"$toLower": "$project"},
                        {
                            "$cond": [
                                {"$gt": [{"$strLenCP": {"$ifNull": ["$domain", ""]}}, 0]},
                                {"$toLower": "$domain"},
                                "__default__",
                            ]
                        },
                    ]
                },
                "__default__",
            ]
        }

        docs_pipeline = [
            {
                "$project": {
                    "project": project_expr,
                    "size": {
                        "$ifNull": [
                            "$size_bytes",
                            {"$bsonSize": "$$ROOT"},
                        ]
                    },
                    "is_binary": {
                        "$cond": [
                            {
                                "$and": [
                                    {"$ne": ["$content_type", None]},
                                    {"$ne": ["$content_type", ""]},
                                    {
                                        "$not": [
                                            {
                                                "$regexMatch": {
                                                    "input": {"$toLower": "$content_type"},
                                                    "regex": "^text/",
                                                }
                                            }
                                        ]
                                    },
                                ]
                            },
                            True,
                            False,
                        ]
                    },
                }
            },
            {
                "$group": {
                    "_id": "$project",
                    "documents_bytes": {"$sum": "$size"},
                    "document_count": {"$sum": 1},
                    "binary_bytes": {
                        "$sum": {
                            "$cond": ["$is_binary", "$size", 0]
                        }
                    },
                }
            },
        ]

        contexts_pipeline = [
            {
                "$project": {
                    "project": project_expr,
                    "size": {"$bsonSize": "$$ROOT"},
                }
            },
            {
                "$group": {
                    "_id": "$project",
                    "context_bytes": {"$sum": "$size"},
                    "context_count": {"$sum": 1},
                }
            },
        ]

        try:
            async for item in self.db[documents_collection].aggregate(docs_pipeline):
                project_key = item.get("_id") or "__default__"
                entry = _ensure(project_key)
                entry["documents_bytes"] = int(item.get("documents_bytes", 0) or 0)
                entry["document_count"] = int(item.get("document_count", 0) or 0)
                entry["binary_bytes"] = int(item.get("binary_bytes", 0) or 0)
        except Exception as exc:  # noqa: BLE001
            logger.warning("mongo_aggregate_documents_failed", error=str(exc))

        try:
            async for item in self.db[contexts_collection].aggregate(contexts_pipeline):
                project_key = item.get("_id") or "__default__"
                entry = _ensure(project_key)
                entry["context_bytes"] = int(item.get("context_bytes", 0) or 0)
                entry["context_count"] = int(item.get("context_count", 0) or 0)
        except Exception as exc:  # noqa: BLE001
            logger.warning("mongo_aggregate_contexts_failed", error=str(exc))

        return result

    async def aggregate_request_stats(
        self,
        *,
        project: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        channel: str | None = None,
    ) -> list[dict[str, object]]:
        match: dict[str, object] = {}
        if project:
            match["project"] = project.strip().lower()
        if channel:
            match["channel"] = channel
        if start or end:
            bounds: dict[str, object] = {}
            if start:
                bounds["$gte"] = start
            if end:
                bounds["$lt"] = end
            match["date"] = bounds

        pipeline: list[dict[str, object]] = []
        if match:
            pipeline.append({"$match": match})
        pipeline.extend(
            [
                {
                    "$group": {
                        "_id": "$date",
                        "count": {"$sum": 1},
                        "attachments": {"$sum": {"$ifNull": ["$attachments", 0]}},
                        "response_chars": {"$sum": {"$ifNull": ["$response_chars", 0]}},
                    }
                },
                {"$sort": {"_id": 1}},
            ]
        )
        cursor = self.db[self.stats_collection].aggregate(pipeline)
        results: list[dict[str, object]] = []
        async for item in cursor:
            day: datetime = item.get("_id")
            results.append(
                {
                    "date": day.date().isoformat() if isinstance(day, datetime) else str(day),
                    "count": item.get("count", 0),
                    "attachments": item.get("attachments", 0),
                    "response_chars": item.get("response_chars", 0),
                }
            )
        return results

    async def iter_request_stats(
        self,
        *,
        project: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        channel: str | None = None,
    ) -> AsyncGenerator[dict[str, object], None]:
        match: dict[str, object] = {}
        if project:
            match["project"] = project.strip().lower()
        if channel:
            match["channel"] = channel
        if start or end:
            bounds: dict[str, object] = {}
            if start:
                bounds["$gte"] = start
            if end:
                bounds["$lt"] = end
            match["date"] = bounds

        cursor = self.db[self.stats_collection].find(match, {"_id": False}).sort("ts", 1)
        async for item in cursor:
            yield item
