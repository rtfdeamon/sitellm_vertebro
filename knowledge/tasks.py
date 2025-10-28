"""Celery tasks for post-processing knowledge documents."""

from __future__ import annotations

import os
import time
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any

import structlog
from bson import ObjectId
from gridfs import GridFS
from pymongo import MongoClient

from worker import (
    LLM_GENERATION_TIMEOUT,
    celery,
    ensure_ollama_cluster_ready,
    get_mongo_client,
    run_async,
    settings as worker_settings,
)
from models import Project
from knowledge.summary import generate_document_summary, select_summary_model
from knowledge.text import extract_best_effort_text
from backend.ollama_cluster import get_cluster_manager
from backend import llm_client

try:
    AUTO_DESCRIPTION_MAX_RETRIES = int(os.getenv("AUTO_DESCRIPTION_MAX_RETRIES", "2"))
except (TypeError, ValueError):
    AUTO_DESCRIPTION_MAX_RETRIES = 2

if AUTO_DESCRIPTION_MAX_RETRIES < 1:
    AUTO_DESCRIPTION_MAX_RETRIES = 1

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
    projects_collection = getattr(worker_settings.mongo, "projects", None)
    if not projects_collection:
        projects_collection = os.getenv("MONGO_PROJECTS", "projects")
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
            logger.warning(
                "auto_description_project_parse_failed",
                project=project_name or raw.get("name"),
                error=str(exc),
            )
    return None


def _apply_fallback_description(
    collection,
    file_id: str,
    doc: dict[str, Any],
    name: str,
    *,
    status_message: str,
    reason: str,
    attempts: int,
) -> None:
    """Store a deterministic fallback description when LLM attempts keep failing."""

    existing = (doc.get("description") or "").strip()
    summary = existing or f"Документ «{name}»."

    now_ts = time.time()
    collection.update_one(
        {"fileId": file_id},
        {
            "$set": {
                "description": summary,
                "autoDescriptionPending": False,
                "autoDescriptionGeneratedAt": now_ts,
            }
        },
    )
    _update_status(collection, file_id, "auto_description_ready", status_message)
    logger.warning(
        "auto_description_fallback_applied",
        file_id=file_id,
        reason=reason,
        attempts=attempts,
    )


@celery.task(name="knowledge.generate_auto_description", bind=True, max_retries=None)
def generate_auto_description(self, file_id: str, project: str | None = None) -> None:
    """Generate a concise description for a document and update its metadata."""

    logger.info("auto_description_queued", file_id=file_id, project=project)
    client = _build_mongo_client()
    try:
        db = client[worker_settings.mongo.database]
        collection = db[worker_settings.mongo.documents]
        logger.info("auto_description_fetch_doc", file_id=file_id, project=project)
        doc = collection.find_one({"fileId": file_id})
        if not doc:
            logger.warning("auto_description_missing_doc", file_id=file_id)
            return

        attempt = int(getattr(self.request, "retries", 0) or 0)
        pending_message = "Ожидаем доступной LLM модели"

        if not ensure_ollama_cluster_ready():
            logger.warning(
                "auto_description_cluster_init_pending",
                file_id=file_id,
                project=project,
            )
            _update_status(collection, file_id, "pending_auto_description", pending_message)
            collection.update_one(
                {"fileId": file_id},
                {"$set": {"autoDescriptionPending": True}},
            )
            raise self.retry(countdown=60, exc=RuntimeError("LLM cluster initialization pending"))

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
            logger.info(
                "auto_description_payload_loaded",
                file_id=file_id,
                project=project,
                payload_bytes=len(payload),
            )
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
        logger.info(
            "auto_description_text_extracted",
            file_id=file_id,
            project=project,
            content_type=content_type,
            text_chars=len(text or ""),
        )
        project_model = _resolve_project(db, doc, project)
        selected_project = None
        if project_model is not None:
            selected_project = getattr(project_model, "name", None)
        logger.info(
            "auto_description_project_resolved",
            file_id=file_id,
            project=project,
            selected_project=selected_project,
        )

        start_ts = time.time()
        summary_model = select_summary_model(project_model)
        effective_model = summary_model or llm_client.MODEL_NAME
        text_length = len(text or "")
        logger.info(
            "summary_generation_start",
            file_id=file_id,
            project=project,
            attempt=attempt + 1,
            model=effective_model,
            text_chars=text_length,
        )
        logger.info(
            "auto_description_generation_start",
            file_id=file_id,
            project=project,
        )
        try:
            summary = run_async(
                generate_document_summary(name, text or None, project_model),
                timeout=LLM_GENERATION_TIMEOUT,
            )
        except FutureTimeoutError:
            attempts_total = attempt + 1
            if attempts_total >= AUTO_DESCRIPTION_MAX_RETRIES:
                _apply_fallback_description(
                    collection,
                    file_id,
                    doc,
                    name,
                    status_message="Использовано стандартное описание",
                    reason="llm_timeout",
                    attempts=attempts_total,
                )
                return

            logger.warning(
                "auto_description_generation_timeout",
                file_id=file_id,
                project=project,
                timeout=LLM_GENERATION_TIMEOUT,
                attempts=attempts_total,
            )
            logger.warning(
                "summary_generation_timeout",
                file_id=file_id,
                project=project,
                model=effective_model,
                attempts=attempts_total,
                timeout=LLM_GENERATION_TIMEOUT,
                duration=time.time() - start_ts,
            )
            _update_status(collection, file_id, "pending_auto_description", "Ожидаем ответ от LLM")
            collection.update_one(
                {"fileId": file_id},
                {"$set": {"autoDescriptionPending": True}},
            )
            raise self.retry(
                countdown=120,
                exc=RuntimeError("LLM generation timed out"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("auto_description_generation_failed", file_id=file_id, error=str(exc))
            logger.error(
                "summary_generation_failed",
                file_id=file_id,
                project=project,
                model=effective_model,
                error=str(exc),
                duration=time.time() - start_ts,
            )
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
        else:
            logger.info(
                "auto_description_generation_done",
                file_id=file_id,
                project=project,
                duration=time.time() - start_ts,
            )
            logger.info(
                "summary_generation_done",
                file_id=file_id,
                project=project,
                model=effective_model,
                duration=time.time() - start_ts,
                summary_chars=len(summary.strip()) if isinstance(summary, str) else 0,
            )

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
