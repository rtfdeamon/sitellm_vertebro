"""Celery worker tasks for updating the Redis vector store."""

from collections.abc import Generator
from urllib.parse import quote_plus

from bson import ObjectId
from gridfs import GridFS
from pymongo import MongoClient
from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_ready

import structlog
import logging
import os
from datetime import datetime

from models import Document
from settings import Settings
from vectors import DocumentsParser
from yallm import YaLLMEmbeddings


# Создаем уникальный лог-файл для каждого запуска воркера
log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)
log_filename = f"worker_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_path = os.path.join(log_dir, log_filename)

# Настройка structlog для записи в файл
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.FileHandler(log_path), logging.StreamHandler()]
)
structlog.configure(
    processors=[structlog.processors.JSONRenderer()],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

settings = Settings()

logger = structlog.get_logger(__name__)

celery = Celery(__name__)
celery.conf.broker_url = settings.celery.broker
celery.conf.result_backend = settings.celery.result
celery.conf.beat_schedule = {
    "update-vector-store-biweekly": {
        "task": "worker.periodic_update",
        "schedule": crontab(day_of_week=[3, 6]),
    }
}


def update_vector_store():
    """Parse all documents from MongoDB and update the vector store.

    All existing documents stored in GridFS are retrieved and parsed
    into vectors which are then added to Redis.
    """
    logger.info("updating vector store")
    vector_store = get_document_parser()
    mongo_client = get_mongo_client()

    for document, data in get_documents_sync(mongo_client):
        logger.info("embedding", document=document.name)
        vector_store.parse_document(document.name, document.fileId, data)

    del vector_store


def get_documents_sync(
    mongo_client: MongoClient,
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
    for document in mongo_client[settings.mongo.database][
        settings.mongo.documents
    ].find({}, {"_id": False}):
        document = Document(**document)
        gridfs = GridFS(mongo_client[settings.mongo.database])
        file = gridfs.get(ObjectId(document.fileId))

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
