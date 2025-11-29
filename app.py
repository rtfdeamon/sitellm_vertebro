"""FastAPI application setup and lifespan management (Ollama-only)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from typing import Any, Dict, Literal
from uuid import uuid4
import random
import json
from datetime import datetime, timezone, timedelta
import csv
import io
import base64
import hashlib
import hmac
import os
import time
import asyncio
import asyncio.subprocess as asyncio_subprocess
import httpx
import structlog
import subprocess
import shutil
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from openpyxl import load_workbook

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse, PlainTextResponse
from starlette.routing import NoMatchFound
from fastapi.responses import ORJSONResponse, FileResponse, StreamingResponse

from backend.rate_limiting import RateLimitingMiddleware
from observability.logging import configure_logging, get_recent_logs
from observability.metrics import MetricsMiddleware, metrics_app

from api import (
    llm_router,
    crawler_router,
    reading_router,
    voice_router,
    _DEFAULT_KNOWLEDGE_PRIORITY,
    _KNOWN_KNOWLEDGE_SOURCES,
)
from mongo import MongoClient, NotFound
from models import BackupJob, BackupOperation, BackupStatus, Document, Project, OllamaServer
from settings import MongoSettings, Settings
from backend.settings import settings as base_settings
from backend.cache import _get_redis
from core.build import get_build_info
from backend import llm_client
from backend.ollama import (
    list_installed_models,
    popular_models_with_size,
    ollama_available,
)
from backend.ollama_cluster import init_cluster, reload_cluster, get_cluster_manager, shutdown_cluster
from pymongo import MongoClient as SyncMongoClient
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from gridfs import GridFS
from bson import ObjectId
from retrieval import encode as retrieval_encode, search as retrieval_search
from backend.bots.max import MaxHub, MaxRunner
from backend.bots.vk import VkHub, VkRunner
import redis
import requests
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from worker import backup_execute
from uuid import uuid4, UUID

from backend.adapters import OllamaLLM, QdrantSearchAdapter as _QdrantSearchAdapter
from backend.auth import (
    ADMIN_PASSWORD_DIGEST,
    ADMIN_USER,
    admin_logout_response as _admin_logout_response,
    get_admin_identity as _get_admin_identity,
    require_admin as _require_admin,
    require_super_admin as _require_super_admin,
    resolve_admin_password_digest as _resolve_admin_password_digest,
    resolve_admin_project as _resolve_admin_project,
)
from backend.desktop import (
    DESKTOP_BUILD_ARTIFACTS,
    DESKTOP_BUILD_COMMANDS,
    DESKTOP_BUILD_LOCKS,
    DESKTOP_BUILD_ROOT,
    prepare_desktop_artifact_blocking as _prepare_desktop_artifact_blocking,
)
from backend.middleware.admin import AdminIdentity
from backend.middleware.auth import BasicAuthMiddleware
from backend.utils.project import normalize_project as _normalize_project
from backend.api.utils import (
    build_content_disposition as _build_content_disposition,
    build_download_url as _build_download_url,
    build_token_preview as _build_token_preview,
    parse_stats_date as _parse_stats_date,
    project_response as _project_response,
    redis_project_usage as _redis_project_usage,
)
from backend.bots.session_provider import HubSessionProvider as _HubSessionProvider
from backend.bots.utils import (
    project_max_payload as _project_max_payload,
    project_telegram_payload as _project_telegram_payload,
    project_vk_payload as _project_vk_payload,
)
from backend.ollama.installer import (
    OLLAMA_INSTALL_LOCK,
    OLLAMA_PROGRESS_RE,
    run_ollama_install as _run_ollama_install,
    schedule_ollama_install as _schedule_ollama_install,
    snapshot_install_jobs as _snapshot_install_jobs,
    update_install_job as _update_install_job,
)
from backend.bots.schemas import (
    MaxAction,
    MaxConfig,
    ProjectMaxAction,
    ProjectMaxConfig,
    ProjectTelegramAction,
    ProjectTelegramConfig,
    ProjectVkAction,
    ProjectVkConfig,
    TelegramAction,
    TelegramConfig,
    VkAction,
    VkConfig,
)
from backend.admin.api import router as admin_router
from backend.backup.api import router as backup_router
from backend.desktop.api import router as desktop_router
from backend.knowledge.api import router as knowledge_router
from backend.projects.api import router as projects_router
from backend.system.api import router as system_router


_FEEDBACK_STATUS_VALUES = {"open", "in_progress", "done", "dismissed"}



configure_logging()

settings = Settings()
logger = structlog.get_logger(__name__)


_PROCESS_CPU_SAMPLE: dict[str, float] | None = None

BUILD_INFO = get_build_info()

# Import Telegram bot components
from backend.bots.telegram import TelegramRunner, TelegramHub
from backend.bots.session_provider import HubSessionProvider as _HubSessionProvider



async def _get_project_context(
    request: Request,
    project_name: str | None,
) -> tuple[str | None, Project | None, MongoClient, bool]:
    """Resolve project configuration and Mongo client for a given project name.

    Parameters
    ----------
    request:
        Active FastAPI request containing ``mongo`` client in state.
    project_name:
        Optional project slug provided by the caller.

    Returns
    -------
    tuple
        ``(normalized_project, project_model, mongo_client, owns_client)`` where
        ``owns_client`` indicates whether the caller must close the client.
    """

    normalized = _resolve_admin_project(request, project_name)

    mongo_client = _get_mongo_client(request)

    project: Project | None = None
    if normalized:
        try:
            project = await mongo_client.get_project(normalized)
        except Exception as exc:  # noqa: BLE001
            logger.error("project_lookup_failed", project=normalized, error=str(exc))
            raise HTTPException(status_code=500, detail="Failed to read project configuration") from exc
    return normalized, project, mongo_client, False


async def _fetch_qa_document(mongo_client: MongoClient, pair_id: str) -> dict | None:
    """Return raw QA document for ``pair_id`` or ``None`` when missing."""

    try:
        oid = ObjectId(pair_id)
    except Exception:
        return None

    try:
        return await mongo_client.db[mongo_client.qa_collection].find_one({"_id": oid})
    except Exception as exc:  # noqa: BLE001
        logger.error("qa_document_lookup_failed", pair_id=pair_id, error=str(exc))
        return None





@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[dict[str, Any], None]:
    """Initialize and clean up application resources.

    Yields
    ------
    dict[str, Any]
        Mapping with initialized ``llm`` instance, Mongo client,
        context collection names and the Redis vector store.
    """
    # Only Ollama is supported as LLM backend
    llm = OllamaLLM()
    embeddings = None

    qdrant_client = QdrantClient(url=base_settings.qdrant_url)
    qdrant_collection = getattr(base_settings, "qdrant_collection", "documents")
    qdrant_adapter = _QdrantSearchAdapter(qdrant_client, qdrant_collection)
    retrieval_search.qdrant = qdrant_adapter

    mongo_cfg = MongoSettings()
    mongo_client = MongoClient(
        mongo_cfg.host,
        mongo_cfg.port,
        mongo_cfg.username,
        mongo_cfg.password,
        mongo_cfg.database,
        mongo_cfg.auth,
    )
    # await mongo_client.ensure_indexes()
    contexts_collection = mongo_cfg.contexts
    context_presets_collection = mongo_cfg.presets
    documents_collection = mongo_cfg.documents
    reading_collection = os.getenv("MONGO_READING_COLLECTION", "reading_pages")
    voice_samples_collection = mongo_cfg.voice_samples
    voice_jobs_collection = mongo_cfg.voice_jobs

    vector_store = None

    telegram_hub = TelegramHub(mongo_client)
    max_hub = MaxHub(mongo_client)
    vk_hub = VkHub(mongo_client)

    app.state.telegram = telegram_hub
    app.state.max = max_hub
    app.state.vk = vk_hub
    app.state.mongo = mongo_client
    app.state.contexts_collection = contexts_collection
    app.state.context_presets_collection = context_presets_collection
    app.state.documents_collection = documents_collection
    app.state.reading_collection = reading_collection
    app.state.voice_samples_collection = voice_samples_collection
    app.state.voice_jobs_collection = voice_jobs_collection
    app.state.pending_attachments = {}
    app.state.pending_attachments_lock = asyncio.Lock()

    # cluster = await init_cluster(
    #     mongo_client,
    #     default_base=getattr(base_settings, "ollama_base_url", None),
    # )
    # app.state.ollama_cluster = cluster
    app.state.ollama_cluster = None

    # Warm-up runners based on stored configuration
    # try:
    #     await telegram_hub.refresh()
    # except Exception as exc:  # noqa: BLE001
    #     logger.warning("telegram_hub_refresh_failed", error=str(exc))
    # try:
    #     await max_hub.refresh()
    # except Exception as exc:  # noqa: BLE001
    #     logger.warning("max_hub_refresh_failed", error=str(exc))
    # try:
    #     await vk_hub.refresh()
    # except Exception as exc:  # noqa: BLE001
    #     logger.warning("vk_hub_refresh_failed", error=str(exc))

    yield {
        "llm": llm,
        "mongo": mongo_client,
        "contexts_collection": contexts_collection,
        "context_presets_collection": context_presets_collection,
        "documents_collection": documents_collection,
        "vector_store": vector_store,
    }

    del llm
    with suppress(Exception):
        await telegram_hub.stop_all()
    with suppress(Exception):
        await max_hub.stop_all()
    with suppress(Exception):
        await vk_hub.stop_all()
    with suppress(Exception):
        await shutdown_cluster()
    mongo_client.client.close()
    qdrant_adapter.close()
    retrieval_search.qdrant = None
    with suppress(AttributeError):
        del app.state.mongo
        del app.state.contexts_collection
        del app.state.context_presets_collection
        del app.state.documents_collection
        del app.state.reading_collection
        del app.state.voice_samples_collection
        del app.state.voice_jobs_collection
        del app.state.telegram
        del app.state.max
        del app.state.vk
        del app.state.ollama_cluster


def _ssl_enabled() -> bool:
    cert = os.getenv("APP_SSL_CERT")
    key = os.getenv("APP_SSL_KEY")
    if not cert or not key:
        return False
    return os.path.exists(cert) and os.path.exists(key)


def _parse_cors_origins(raw: str | list[str] | tuple[str, ...]) -> list[str]:
    """Return a list of CORS origins from a raw env value."""

    if isinstance(raw, (list, tuple)):
        values = [str(item).strip() for item in raw if str(item).strip()]
    else:
        values = [item.strip() for item in str(raw or "").split(",") if item.strip()]
    return values or ["*"]


cors_origins = _parse_cors_origins(getattr(settings, "cors_origins", "*"))
allow_all_origins = "*" in cors_origins

app = FastAPI(lifespan=lifespan, debug=settings.debug)
if _ssl_enabled():
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# CORS: Allow all origins for widget embedding
# The widget is designed to be embedded on any third-party website,
# so we need to allow requests from any domain. This is intentional.
# Additional security is provided by:
# - Rate limiting (protects from abuse)
# - Admin authentication (protects sensitive endpoints)
# - CSRF protection where applicable
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Rate limiting middleware - protects API from abuse
app.add_middleware(RateLimitingMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(BasicAuthMiddleware)
app.mount("/metrics", metrics_app)
app.include_router(
    llm_router,
    prefix="/api/v1",
)
app.include_router(
    crawler_router,
    prefix="/api/v1",
)
app.include_router(
    reading_router,
    prefix="/api/v1",
)
app.include_router(
    voice_router,
    prefix="/api/v1",
)
app.include_router(
    backup_router,
    prefix="/api/v1",
)
app.include_router(
    desktop_router,
    prefix="/api/v1",
)
app.include_router(
    admin_router,
    prefix="/api/v1",
)
app.include_router(
    knowledge_router,
    prefix="/api/v1",
)
app.include_router(projects_router)
app.include_router(system_router)
app.mount("/widget", StaticFiles(directory="widget", html=True), name="widget")
app.mount("/admin", StaticFiles(directory="admin", html=True), name="admin")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redirect the root URL to the web chat widget.

    Opening http://localhost:8000 now lands at ``/widget/`` instead of 404.
    """
    return RedirectResponse(url="/widget/")


