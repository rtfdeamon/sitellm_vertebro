"""Celery worker tasks for updating the Redis vector store."""

import time
from collections.abc import Generator
from typing import Dict
from urllib.parse import quote_plus

from bson import ObjectId
from gridfs import GridFS
from pymongo import MongoClient
from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_ready

import structlog

from models import Document
from settings import Settings
from vectors import DocumentsParser
from yallm import YaLLMEmbeddings
from core.status import status_dict
from observability.logging import configure_logging



configure_logging()

settings = Settings()

logger = structlog.get_logger(__name__)

celery = Celery(__name__)
celery.conf.broker_url = settings.celery.broker
celery.conf.result_backend = settings.celery.result
celery.autodiscover_tasks(["crawler"])
celery.conf.beat_schedule = {
    "update-vector-store-biweekly": {
        "task": "worker.periodic_update",
        "schedule": crontab(day_of_week=[3, 6]),
    },
    "status-report-every-30s": {
        "task": "status.report",
        "schedule": 30.0,
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
    mongo_client: MongoClient,
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


def get_mongo_client() -> MongoClient:
    """Return a synchronous MongoDB client.

    Uses credentials from :class:`Settings` to construct the connection URL.
    """
    url = f"mongodb://{quote_plus(settings.mongo.username)}:{quote_plus(settings.mongo.password)}@{settings.mongo.host}:{settings.mongo.port}/{settings.mongo.auth}"
    logger.info("connect mongo", host=settings.mongo.host)
    return MongoClient(url)


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
