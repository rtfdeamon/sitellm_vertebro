"""Celery tasks for post-processing knowledge documents."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog
from bson import ObjectId
from gridfs import GridFS
from pymongo import MongoClient

from apps.worker.main import celery, get_mongo_client, settings as worker_settings
from packages.core.models import Project
from packages.knowledge.summary import generate_document_summary
from packages.knowledge.text import extract_best_effort_text
from packages.backend.ollama_cluster import get_cluster_manager

logger = structlog.get_logger(__name__)


def _build_mongo_client() -> MongoClient:
    return get_mongo_client()


def _update_status(collection, file_id: str, status: str, message: str | None) -> None:
    collection.update_one(
        {"fileId": file_id},
        {
            "$set": {
                "status": status,
                "statusMessage": message,
                "statusUpdatedAt": time.time(),
            }
        },
        upsert=False,
    )


def _resolve_project(db, doc: dict[str, Any], explicit: str | None) -> Project | None:
    projects_collection = worker_settings.mongo.projects
    project_name = (explicit or doc.get("project") or "").strip().lower()
    raw: dict[str, Any] | None = None
    if project_name:
        raw = db[projects_collection].find_one({"name": project_name})
    if not raw:
        domain = (doc.get("domain") or "").strip().lower()
        if domain:
            raw = db[projects_collection].find_one({"domain": domain})
    if raw:
        try:
            return Project(**raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning("auto_description_project_parse_failed", project=project_name or raw.get("name"), error=str(exc))
    return None


@celery.task(name="knowledge.generate_auto_description", bind=True, max_retries=None)
def generate_auto_description(self, file_id: str, project: str | None = None) -> None:
    """Generate a concise description for a document and update its metadata."""

    logger.info("auto_description_queued", file_id=file_id, project=project)
    client = _build_mongo_client()
    try:
        db = client[worker_settings.mongo.database]
        collection = db[worker_settings.mongo.documents]
        doc = collection.find_one({"fileId": file_id})
        if not doc:
            logger.warning("auto_description_missing_doc", file_id=file_id)
            return
        pending_message = "Ожидаем доступной LLM модели"
        try:
            cluster = get_cluster_manager()
        except RuntimeError as exc:
            logger.warning(
                "auto_description_cluster_uninitialized",
                file_id=file_id,
                project=project,
                error=str(exc),
            )
            _update_status(collection, file_id, "pending_auto_description", pending_message)
            collection.update_one(
                {"fileId": file_id},
                {"$set": {"autoDescriptionPending": True}},
            )
            raise self.retry(countdown=60, exc=exc)
        if not cluster.has_available():
            logger.info(
                "auto_description_wait_llm",
                file_id=file_id,
                project=project,
            )
            _update_status(collection, file_id, "pending_auto_description", pending_message)
            collection.update_one(
                {"fileId": file_id},
                {"$set": {"autoDescriptionPending": True}},
            )
            raise self.retry(countdown=60, exc=RuntimeError("LLM cluster unavailable"))
        gridfs = GridFS(db)
        _update_status(collection, file_id, "auto_description_in_progress", "Формируем описание")
        try:
            payload = gridfs.get(ObjectId(file_id)).read()
        except Exception as exc:  # noqa: BLE001
            logger.error("auto_description_gridfs_failed", file_id=file_id, error=str(exc))
            _update_status(collection, file_id, "auto_description_failed", "Не удалось прочитать файл")
            collection.update_one(
                {"fileId": file_id},
                {"$set": {"autoDescriptionPending": False}},
            )
            return

        name = doc.get("name") or f"document-{file_id}"
        content_type = str(doc.get("content_type") or "").lower()
        text = extract_best_effort_text(name, content_type, payload)
        project_model = _resolve_project(db, doc, project)

        try:
            summary = asyncio.run(generate_document_summary(name, text or None, project_model))
        except Exception as exc:  # noqa: BLE001
            logger.error("auto_description_generation_failed", file_id=file_id, error=str(exc))
            _update_status(collection, file_id, "auto_description_failed", "Ошибка генерации описания")
            collection.update_one(
                {"fileId": file_id},
                {
                    "$set": {
                        "autoDescriptionPending": False,
                        "autoDescriptionGeneratedAt": None,
                    }
                },
            )
            return

        summary_clean = summary.strip() if isinstance(summary, str) else ""
        now_ts = time.time()
        collection.update_one(
            {"fileId": file_id},
            {
                "$set": {
                    "description": summary_clean or doc.get("description") or f"Документ «{name}».",
                    "autoDescriptionPending": False,
                    "autoDescriptionGeneratedAt": now_ts,
                }
            },
        )
        _update_status(collection, file_id, "auto_description_ready", "Описание обновлено")
        logger.info("auto_description_ready", file_id=file_id)
    finally:
        client.close()


def queue_auto_description(file_id: str, project: str | None = None) -> None:
    """Schedule asynchronous auto-description generation for ``file_id``."""

    try:
        generate_auto_description.delay(file_id, project)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "auto_description_schedule_failed",
            file_id=file_id,
            error=str(exc),
        )
