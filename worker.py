"""Celery worker tasks for updating the Redis vector store."""

from collections.abc import Generator
from urllib.parse import quote_plus

from bson import ObjectId
from gridfs import GridFS
from pymongo import MongoClient
from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_ready

from models import Document
from settings import Settings
from vectors import DocumentsParser
from yallm import YaLLMEmbeddings

settings = Settings()

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
    """Parse all documents from MongoDB and update the vector store."""
    vector_store = get_document_parser()
    mongo_client = get_mongo_client()

    for document, data in get_documents_sync(mongo_client):
        print(document.name)
        vector_store.parse_document(document.name, document.fileId, data)

    del vector_store


def get_documents_sync(
    mongo_client: MongoClient,
) -> Generator[tuple[Document, bytes], None]:
    """Yield documents and their data from GridFS synchronously."""
    for document in mongo_client[settings.mongo.database][
        settings.mongo.documents
    ].find({}, {"_id": False}):
        document = Document(**document)
        gridfs = GridFS(mongo_client[settings.mongo.database])
        file = gridfs.get(ObjectId(document.fileId))

        yield document, file.read()


def get_mongo_client() -> MongoClient:
    """Return a synchronous MongoDB client."""
    url = f"mongodb://{quote_plus(settings.mongo.username)}:{quote_plus(settings.mongo.password)}@{settings.mongo.host}:{settings.mongo.port}/{settings.mongo.auth}"
    return MongoClient(url)


def get_document_parser() -> DocumentsParser:
    """Construct a ``DocumentsParser`` using YaLLM embeddings."""
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
    """Update the vector store when the worker starts."""
    update_vector_store()


@celery.task
def periodic_update():
    """Celery beat task that updates the vector store."""
    update_vector_store()
