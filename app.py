"""FastAPI application setup and lifespan management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from observability.logging import configure_logging
from observability.metrics import MetricsMiddleware, metrics_app

from api import llm_router
from mongo import MongoClient
from vectors import DocumentsParser
from yallm import YaLLM, YaLLMEmbeddings
from settings import Settings
from core.status import status_dict
from backend.settings import settings as base_settings
from pymongo import MongoClient as SyncMongoClient
from qdrant_client import QdrantClient
from retrieval import search as retrieval_search
import redis
import requests


configure_logging()

settings = Settings()


@asynccontextmanager
async def lifespan(_) -> AsyncGenerator[dict[str, Any], None]:
    """Initialize and clean up application resources.

    Yields
    ------
    dict[str, Any]
        Mapping with initialized ``llm`` instance, Mongo client,
        context collection names and the Redis vector store.
    """
    llm = YaLLM()
    embeddings = YaLLMEmbeddings()

    qdrant_client = QdrantClient(url=base_settings.qdrant_url)
    retrieval_search.qdrant = qdrant_client

    mongo_client = MongoClient(
        settings.mongo.host,
        settings.mongo.port,
        settings.mongo.username,
        settings.mongo.password,
        settings.mongo.database,
        settings.mongo.auth,
    )
    contexts_collection = settings.mongo.contexts
    context_presets_collection = settings.mongo.presets

    vector_store = DocumentsParser(
        embeddings.get_embeddings_model(),
        settings.redis.vector,
        settings.redis.host,
        settings.redis.port,
        0,
        settings.redis.password,
        settings.redis.secure,
    )

    yield {
        "llm": llm,
        "mongo": mongo_client,
        "contexts_collection": contexts_collection,
        "context_presets_collection": context_presets_collection,
        "vector_store": vector_store,
    }

    del llm
    await mongo_client.client.close()
    qdrant_client.close()


app = FastAPI(lifespan=lifespan, debug=settings.debug)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])
app.add_middleware(MetricsMiddleware)
app.mount("/metrics", metrics_app)
app.include_router(
    llm_router,
    prefix="/api/v1",
)
app.mount("/widget", StaticFiles(directory="widget", html=True), name="widget")


def _mongo_ok() -> bool:
    try:
        mc = SyncMongoClient(base_settings.mongo_uri, serverSelectionTimeoutMS=500)
        mc.admin.command("ping")
        return True
    except Exception:
        return False


def _redis_ok() -> bool:
    try:
        r = redis.from_url(base_settings.redis_url, socket_connect_timeout=0.5)
        return bool(r.ping())
    except Exception:
        return False


def _qdrant_ok() -> bool:
    try:
        resp = requests.get(f"{base_settings.qdrant_url}/healthz", timeout=0.8)
        return resp.ok
    except Exception:
        return False


@app.get("/health", include_in_schema=False)
def health() -> dict[str, object]:
    """Health check with external service probes."""
    checks = {
        "mongo": _mongo_ok(),
        "redis": _redis_ok(),
        "qdrant": _qdrant_ok(),
    }
    status = "ok" if all(checks.values()) else "degraded"
    return {"status": status, **checks}

@app.get("/status")
def status() -> dict[str, object]:
    """Return aggregated crawler and database status."""
    return status_dict()
