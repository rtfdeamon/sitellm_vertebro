<<<<<<< HEAD
"""Celery worker tasks for updating the Redis vector store and voice models."""
=======
"""Celery worker tasks for updating the Qdrant vector store, backups, and voice models."""
>>>>>>> 724ba43 (WIP. Fix broken worker)

import asyncio
import os
import re
import time
from collections.abc import Generator
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Dict
from urllib.parse import quote_plus

from bson import ObjectId
from gridfs import GridFS
from pymongo import MongoClient as SyncMongoClient
from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_ready

import structlog

from backup import (
    BackupError,
    build_mongo_uri,
    normalize_remote_folder,
    perform_backup,
    perform_restore,
    should_run_backup,
)
from models import BackupOperation, BackupStatus, Document, VoiceTrainingStatus
from mongo import MongoClient as AsyncMongoClient
from settings import Settings
from vectors import DocumentsParser
from yallm import YaLLMEmbeddings
from core.status import status_dict
from observability.logging import configure_logging



configure_logging()

settings = Settings()

logger = structlog.get_logger(__name__)

VOICE_MIN_SAMPLE_COUNT = int(os.getenv("VOICE_MIN_SAMPLE_COUNT", "3"))

BACKUP_DUMP_BINARY = os.getenv("MONGODUMP_BIN", "mongodump")
BACKUP_RESTORE_BINARY = os.getenv("MONGORESTORE_BIN", "mongorestore")
try:
    BACKUP_TIMEOUT_SECONDS = float(os.getenv("BACKUP_TIMEOUT_SECONDS", "900"))
except (TypeError, ValueError):  # pragma: no cover - fallback to sensible default
    BACKUP_TIMEOUT_SECONDS = 900.0

celery = Celery(__name__)
celery.conf.broker_url = settings.celery.broker
celery.conf.result_backend = settings.celery.result
celery.autodiscover_tasks(["crawler", "knowledge"])
celery.conf.beat_schedule = {
    "update-vector-store-biweekly": {
        "task": "worker.periodic_update",
        "schedule": crontab(day_of_week=[3, 6]),
    },
    "status-report-every-30s": {
        "task": "status.report",
        "schedule": 30.0,
    },
    "backup-scheduler": {
        "task": "backup.scheduler",
        "schedule": 300.0,
    },
}


def update_vector_store():
    """Parse new or updated documents from MongoDB into the vector store."""

    logger.info("updating vector store")
    vector_store = get_document_parser()
    mongo_client = get_mongo_client()
    try:
        db = mongo_client[settings.mongo.database]
        documents_collection = db[settings.mongo.documents]
        settings_collection = db[settings.mongo.settings]

        cleanup_stats = prune_knowledge_collection(db, documents_collection)
        if cleanup_stats["removed"]:
            logger.info(
                "knowledge_pruned",
                removed=cleanup_stats["removed"],
                duplicates=cleanup_stats["duplicates"],
                low_value=cleanup_stats["low_value"],
            )

        try:
            documents_collection.create_index("ts", name="documents_ts")
        except Exception as exc:
            logger.debug(
                "mongo_index_create_failed",
                collection=settings.mongo.documents,
                index="documents_ts",
                error=str(exc),
            )

        state_key = "vector_store_state"
        state = settings_collection.find_one({"_id": state_key}) or {}
        last_ts_raw = state.get("last_ts")
        try:
            last_ts = float(last_ts_raw)
        except (TypeError, ValueError):
            last_ts = 0.0

        filter_query: Dict[str, object] | None = None
        mode = "incremental"
        if last_ts > 0:
            filter_query = {"ts": {"$gt": last_ts}}
            logger.info("vector store incremental", since=last_ts)
        else:
            mode = "full"
            logger.info("vector store full rebuild")

        processed = 0
        latest_ts = last_ts

        for document, data in get_documents_sync(
            mongo_client, filter_query=filter_query
        ):
            logger.info("embedding", document=document.name)
            vector_store.parse_document(document.name, document.fileId, data)
            processed += 1
            if document.ts is not None:
                try:
                    latest_ts = max(latest_ts, float(document.ts))
                except (TypeError, ValueError):
                    pass

        state_payload = {
            "last_ts": latest_ts if processed else last_ts,
            "updated_at": time.time(),
            "last_processed": processed,
            "mode": mode,
        }
        settings_collection.update_one(
            {"_id": state_key},
            {"$set": state_payload},
            upsert=True,
        )
        logger.info(
            "vector store update complete",
            processed=processed,
            since=last_ts if last_ts > 0 else None,
        )
    finally:
        mongo_client.close()
        del vector_store


def get_documents_sync(
    mongo_client: SyncMongoClient,
    *,
    filter_query: Dict[str, object] | None = None,
) -> Generator[tuple[Document, bytes], None]:
    """Yield documents and their data from GridFS synchronously.

    Parameters
    ----------
    mongo_client:
        Active connection to MongoDB used to fetch documents and files.

    Yields
    ------
    tuple[Document, bytes]
        Parsed ``Document`` metadata along with the binary file contents.
    """
    db = mongo_client[settings.mongo.database]
    collection = db[settings.mongo.documents]
    gridfs = GridFS(db)
    query = filter_query or {}
    cursor = collection.find(query, {"_id": False}).sort("ts", 1).batch_size(50)

    for raw_doc in cursor:
        document = Document(**raw_doc)
        try:
            file = gridfs.get(ObjectId(document.fileId))
        except Exception as exc:
            logger.warning("gridfs_fetch_failed", file_id=document.fileId, error=str(exc))
            continue

        yield document, file.read()


def get_mongo_client() -> SyncMongoClient:
    """Return a synchronous MongoDB client using configured credentials if provided."""

    username = os.getenv("MONGO_USERNAME", settings.mongo.username or "")
    password = os.getenv("MONGO_PASSWORD", settings.mongo.password or "")
    host = os.getenv("MONGO_HOST", settings.mongo.host or "localhost")
    port = int(os.getenv("MONGO_PORT", settings.mongo.port or 27017))
    auth_db = os.getenv("MONGO_AUTH", settings.mongo.auth or "admin")

    if username and password:
        credentials = f"{quote_plus(username)}:{quote_plus(password)}@"
    else:
        credentials = ""

    url = f"mongodb://{credentials}{host}:{port}/{auth_db}"
    logger.info("connect mongo", host=host)
    return SyncMongoClient(url)


def get_document_parser() -> DocumentsParser:
    """Construct a ``DocumentsParser`` using YaLLM embeddings.

    The parser is configured to store vectors in Redis using the parameters
    defined in :class:`Settings`.
    """
    logger.info("create document parser")
    embeddings = YaLLMEmbeddings()
    return DocumentsParser(
        embeddings.get_embeddings_model(),
        settings.redis.vector,
        settings.redis.host,
        settings.redis.port,
        0,
        settings.redis.password,
        settings.redis.secure,
    )


def _create_async_mongo() -> AsyncMongoClient:
    cfg = settings.mongo
    return AsyncMongoClient(
        cfg.host,
        cfg.port,
        cfg.username,
        cfg.password,
        cfg.database,
        cfg.auth,
    )


def _resolve_zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except Exception:  # noqa: BLE001 - default to UTC on invalid tz specification
        return ZoneInfo("UTC")


BREADCRUMB_SEPARATORS = re.compile(r"\s*[>/\\»|-]+\s*")
NAV_KEYWORDS = {
    "главная",
    "контакты",
    "о компании",
    "о нас",
    "услуги",
    "партнёры",
    "клиенты",
    "новости",
    "карта сайта",
    "help",
    "support",
    "docs",
    "documentation",
    "download",
}
FOOTER_KEYWORDS = {
    "все права защищены",
    "all rights reserved",
    "политика конфиденциальности",
    "privacy policy",
    "terms of use",
    "соглашение",
    "copyright",
    "©",
}


def _looks_like_navigation_snippet(text: str) -> bool:
    candidate = text.strip().lower()
    if not candidate:
        return True
    parts = [part.strip() for part in BREADCRUMB_SEPARATORS.split(candidate) if part.strip()]
    if parts and all(part in NAV_KEYWORDS for part in parts):
        return True
    if len(candidate) <= 60 and candidate.count(" ") <= 6:
        tokens = [token for token in re.split(r"\W+", candidate) if token]
        if tokens and all(token in NAV_KEYWORDS for token in tokens):
            return True
    for marker in FOOTER_KEYWORDS:
        if marker in candidate and len(candidate) <= 160:
            return True
    return False


def _delete_document(collection, gridfs: GridFS, file_id: str) -> None:
    collection.delete_one({"fileId": file_id})
    try:
        gridfs.delete(ObjectId(file_id))
    except Exception:
        logger.debug("gridfs_delete_skip", file_id=file_id)


def prune_knowledge_collection(db, collection) -> dict[str, int]:
    """Remove duplicate and low-value knowledge documents before processing."""

    gridfs = GridFS(db)
    seen_hashes: dict[str, set[str]] = {}
    removed = duplicates = low_value = 0
    try:
        cursor = collection.find(
            {},
            {
                "fileId": 1,
                "content_hash": 1,
                "description": 1,
                "project": 1,
                "autoDescriptionPending": 1,
            },
        )
        for doc in cursor:
            file_id = doc.get("fileId")
            if not file_id:
                continue
            project_key = (doc.get("project") or "default").strip().lower()
            bucket = seen_hashes.setdefault(project_key, set())
            content_hash = doc.get("content_hash")
            description = (doc.get("description") or "").strip()

            if content_hash and content_hash in bucket:
                _delete_document(collection, gridfs, file_id)
                duplicates += 1
                removed += 1
                continue

            skip_low_value = False
            if description:
                if len(description) < 60 or _looks_like_navigation_snippet(description):
                    skip_low_value = True
            else:
                skip_low_value = True

            if skip_low_value and not bool(doc.get("autoDescriptionPending")):
                _delete_document(collection, gridfs, file_id)
                low_value += 1
                removed += 1
                continue

            if content_hash:
                bucket.add(content_hash)
    except Exception as exc:  # noqa: BLE001
        logger.warning("knowledge_prune_failed", error=str(exc))

    return {"removed": removed, "duplicates": duplicates, "low_value": low_value}

@worker_ready.connect
def on_startup(*args, **kwargs):
    """Update the vector store when the worker starts.

    This hook ensures that the latest documents are embedded as soon as the
    worker process is ready to accept tasks.
    """
    logger.info("worker ready")
    update_vector_store()


@celery.task
def periodic_update():
    """Celery beat task that updates the vector store.

    Scheduled twice a week via ``beat_schedule`` to keep the Redis index in
    sync with MongoDB.
    """
    logger.info("scheduled update")
    update_vector_store()


@celery.task(name="status.report")
def status_report():
    """Log a short status summary."""
    s = status_dict()
    logger.info(
        "status",
        fill=s["fill_percent"],
        mongo=s["db"]["mongo_docs"],
        qdrant=s["db"]["qdrant_points"],
        queued=s["crawler"]["queued"],
        in_progress=s["crawler"]["in_progress"],
        done=s["crawler"]["done"],
        failed=s["crawler"]["failed"],
        last=s["crawler"]["last_url"],
    )


async def _schedule_backup_if_needed() -> None:
    client = _create_async_mongo()
    try:
        settings_model = await client.get_backup_settings()
        if not should_run_backup(settings_model):
            return

        token = await client.get_backup_token()
        if not token:
            logger.warning("backup_schedule_token_absent")
            return

        active = await client.find_active_backup_job()
        if active:
            logger.debug("backup_job_already_queued", job_id=active.id)
            return

        job = await client.create_backup_job(
            operation=BackupOperation.backup,
            status=BackupStatus.queued,
            triggered_by="scheduler",
        )
        zone = _resolve_zone(settings_model.timezone)
        today_label = datetime.now(zone).date().isoformat()
        await client.record_backup_runtime(last_attempt_date=today_label)
        backup_execute.delay(job.id)
        logger.info(
            "backup_job_scheduled",
            job_id=job.id,
            folder=settings_model.ya_disk_folder,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("backup_schedule_failed", error=str(exc))
    finally:
        await client.close()


async def _execute_backup_job(job_id: str) -> None:
    client = _create_async_mongo()
    try:
        job = await client.get_backup_job(job_id)
        if not job:
            logger.warning("backup_job_missing", job_id=job_id)
            return

        settings_model = await client.get_backup_settings()
        token = await client.get_backup_token()
        if not token:
            raise BackupError("ya_disk_token_missing")

        mongo_cfg = settings.mongo
        mongo_uri = build_mongo_uri(
            mongo_cfg.host,
            mongo_cfg.port,
            mongo_cfg.username,
            mongo_cfg.password,
            mongo_cfg.auth,
        )

        now_ts = time.time()
        await client.update_backup_job(
            job_id,
            {
                "status": BackupStatus.running,
                "started_at": now_ts,
            },
        )
        zone = _resolve_zone(settings_model.timezone)
        await client.record_backup_runtime(
            last_run_at=now_ts,
            last_attempt_date=datetime.now(zone).date().isoformat(),
        )

        try:
            if job.operation is BackupOperation.backup or job.operation == BackupOperation.backup:
                folder = normalize_remote_folder(settings_model.ya_disk_folder)
                result = perform_backup(
                    mongo_uri=mongo_uri,
                    database=mongo_cfg.database,
                    token=token,
                    remote_folder=folder,
                    dump_binary=BACKUP_DUMP_BINARY,
                    timeout=BACKUP_TIMEOUT_SECONDS,
                )
                await client.update_backup_job(
                    job_id,
                    {
                        "status": BackupStatus.completed,
                        "finished_at": time.time(),
                        "remote_path": result.remote_path,
                        "size_bytes": result.size_bytes,
                    },
                )
                await client.record_backup_runtime(last_success_at=time.time())
                logger.info(
                    "backup_job_completed",
                    job_id=job_id,
                    remote_path=result.remote_path,
                    size=result.size_bytes,
                )
            elif job.operation is BackupOperation.restore or job.operation == BackupOperation.restore:
                if not job.remote_path:
                    raise BackupError("restore_remote_path_missing")
                perform_restore(
                    mongo_uri=mongo_uri,
                    database=mongo_cfg.database,
                    token=token,
                    remote_path=job.remote_path,
                    restore_binary=BACKUP_RESTORE_BINARY,
                    timeout=BACKUP_TIMEOUT_SECONDS,
                )
                await client.update_backup_job(
                    job_id,
                    {
                        "status": BackupStatus.completed,
                        "finished_at": time.time(),
                    },
                )
                logger.info(
                    "backup_restore_completed",
                    job_id=job_id,
                    remote_path=job.remote_path,
                )
            else:  # pragma: no cover - defensive guard
                raise BackupError(f"unsupported_operation:{job.operation}")
        except BackupError as exc:
            await client.update_backup_job(
                job_id,
                {
                    "status": BackupStatus.failed,
                    "finished_at": time.time(),
                    "error": str(exc),
                },
            )
            logger.error("backup_job_failed", job_id=job_id, error=str(exc))
        except Exception as exc:  # noqa: BLE001
            await client.update_backup_job(
                job_id,
                {
                    "status": BackupStatus.failed,
                    "finished_at": time.time(),
                    "error": str(exc),
                },
            )
            logger.exception("backup_job_exception", job_id=job_id)
    finally:
        await client.close()


@celery.task(name="backup.scheduler")
def backup_scheduler() -> None:
    try:
        asyncio.run(_schedule_backup_if_needed())
    except Exception as exc:  # noqa: BLE001
        logger.exception("backup_scheduler_unhandled", error=str(exc))


@celery.task(name="backup.execute")
def backup_execute(job_id: str) -> None:
    try:
        asyncio.run(_execute_backup_job(job_id))
    except Exception as exc:  # noqa: BLE001
        logger.exception("backup_execute_unhandled", job_id=job_id, error=str(exc))


def _voice_job_update(collection, job_oid: ObjectId, *, status: VoiceTrainingStatus | None = None, progress: float | None = None, message: str | None = None, started: bool = False, finished: bool = False) -> None:
    now = time.time()
    payload: dict[str, object] = {
        "updatedAt": now,
        "updatedAtIso": datetime.utcfromtimestamp(now).isoformat(),
    }
    if status is not None:
        payload["status"] = status.value if isinstance(status, VoiceTrainingStatus) else str(status)
    if progress is not None:
        payload["progress"] = float(progress)
    if message is not None:
        payload["message"] = message
    if started:
        payload["startedAt"] = now
        payload["startedAtIso"] = datetime.utcfromtimestamp(now).isoformat()
    if finished:
        payload["finishedAt"] = now
        payload["finishedAtIso"] = datetime.utcfromtimestamp(now).isoformat()

    collection.update_one({"_id": job_oid}, {"$set": payload})


@celery.task(name="voice.train_model")
def voice_train_model(job_id: str) -> None:
    """Simulate voice fine-tuning for the given project job."""

    try:
        job_oid = ObjectId(job_id)
    except Exception:
        logger.warning("voice_train_invalid_job", job_id=job_id)
        return

    client = get_mongo_client()
    try:
        db = client[settings.mongo.database]
        samples_collection = db[settings.mongo.voice_samples]
        jobs_collection = db[settings.mongo.voice_jobs]

        job_doc = jobs_collection.find_one({"_id": job_oid})
        if not job_doc:
            logger.warning("voice_train_missing_job", job_id=job_id)
            return

        project = job_doc.get("project")
        if not project:
            logger.warning("voice_train_missing_project", job_id=job_id)
            _voice_job_update(
                jobs_collection,
                job_oid,
                status=VoiceTrainingStatus.failed,
                message="Не указан проект",
                finished=True,
            )
            return

        sample_count = samples_collection.count_documents({"project": project})
        if sample_count < VOICE_MIN_SAMPLE_COUNT:
            logger.info(
                "voice_train_insufficient_samples",
                project=project,
                samples=sample_count,
                required=VOICE_MIN_SAMPLE_COUNT,
            )
            _voice_job_update(
                jobs_collection,
                job_oid,
                status=VoiceTrainingStatus.failed,
                progress=0.0,
                message=f"Недостаточно дорожек ({sample_count}/{VOICE_MIN_SAMPLE_COUNT})",
                finished=True,
            )
            return

        logger.info("voice_train_started", project=project, job_id=job_id, samples=sample_count)
        _voice_job_update(
            jobs_collection,
            job_oid,
            status=VoiceTrainingStatus.preparing,
            progress=0.05,
            message="Готовим набор примеров",
            started=True,
        )
        time.sleep(1.0)

        _voice_job_update(
            jobs_collection,
            job_oid,
            status=VoiceTrainingStatus.training,
            progress=0.6,
            message="Обучаем голосовую модель",
        )
        time.sleep(1.5)

        _voice_job_update(
            jobs_collection,
            job_oid,
            status=VoiceTrainingStatus.validating,
            progress=0.85,
            message="Проверяем результат",
        )
        time.sleep(1.2)

        _voice_job_update(
            jobs_collection,
            job_oid,
            status=VoiceTrainingStatus.completed,
            progress=1.0,
            message="Голосовой профиль готов",
            finished=True,
        )
        logger.info("voice_train_completed", project=project, job_id=job_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("voice_train_failed", job_id=job_id, error=str(exc))
        db = client[settings.mongo.database]
        jobs_collection = db[settings.mongo.voice_jobs]
        _voice_job_update(
            jobs_collection,
            job_oid,
            status=VoiceTrainingStatus.failed,
            progress=0.0,
            message="Ошибка при обучении",
            finished=True,
        )
    finally:
        client.close()
