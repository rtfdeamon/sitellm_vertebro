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
import urllib.parse as urlparse
from urllib.parse import quote
import re
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
from bs4 import BeautifulSoup

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
from core.status import status_dict
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
from knowledge.summary import generate_document_summary
from knowledge.tasks import queue_auto_description
from knowledge.text import (
    extract_doc_text,
    extract_docx_text,
    extract_pdf_text,
    extract_xls_text,
    extract_xlsx_text,
)
from knowledge_service.configuration import (
    ALLOWED_MODES as KNOWLEDGE_SERVICE_ALLOWED_MODES,
    DEFAULT_MODE as KNOWLEDGE_SERVICE_DEFAULT_MODE,
    DEFAULT_PROCESSING_PROMPT as KNOWLEDGE_SERVICE_DEFAULT_PROMPT,
    MANUAL_MODE_MESSAGE as KNOWLEDGE_SERVICE_MANUAL_MESSAGE,
)
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
from backend.dependencies import get_mongo_client as _get_mongo_client
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
    OLLAMA_INSTALL_JOBS,
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
from api.admin import router as admin_router
from api.backup import router as backup_router
from api.desktop import router as desktop_router


_FEEDBACK_STATUS_VALUES = {"open", "in_progress", "done", "dismissed"}



configure_logging()

settings = Settings()
logger = structlog.get_logger(__name__)


_PROCESS_CPU_SAMPLE: dict[str, float] | None = None

BUILD_INFO = get_build_info()

PROMPT_ROLE_TEMPLATES = {
    "friendly_expert": {
        "label": "Дружелюбный эксперт",
        "instruction": (
            "Выступай дружелюбным экспертом компании: общайся приветливо, поддерживай клиента,"
            " подсказывай решения и действуй в интересах пользователя, сохраняя эмпатию."
        ),
    },
    "formal_consultant": {
        "label": "Формальный консультант",
        "instruction": (
            "Держи официальный, деловой стиль: давай точные формулировки, опирайся на факты и регламенты,"
            " избегай разговорных оборотов и лишних эмоций."
        ),
    },
    "sales_manager": {
        "label": "Активный менеджер",
        "instruction": (
            "Работай как проактивный менеджер по продукту: подчеркивай выгоды, предлагай релевантные услуги"
            " и мягко направляй собеседника к целевым действиям."
        ),
    },
}

DEFAULT_PROMPT_ROLE = "friendly_expert"
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
    await mongo_client.ensure_indexes()
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

    cluster = await init_cluster(
        mongo_client,
        default_base=getattr(base_settings, "ollama_base_url", None),
    )
    app.state.ollama_cluster = cluster

    # Warm-up runners based on stored configuration
    try:
        await telegram_hub.refresh()
    except Exception as exc:  # noqa: BLE001
        logger.warning("telegram_hub_refresh_failed", error=str(exc))
    try:
        await max_hub.refresh()
    except Exception as exc:  # noqa: BLE001
        logger.warning("max_hub_refresh_failed", error=str(exc))
    try:
        await vk_hub.refresh()
    except Exception as exc:  # noqa: BLE001
        logger.warning("vk_hub_refresh_failed", error=str(exc))

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
app.mount("/widget", StaticFiles(directory="widget", html=True), name="widget")
app.mount("/admin", StaticFiles(directory="admin", html=True), name="admin")


def _mongo_check(mongo_uri: str | None = None) -> tuple[bool, str | None]:
    """Best-effort Mongo probe with short retries."""

    cfg = MongoSettings()
    uri = mongo_uri or f"mongodb://{cfg.username}:{cfg.password}@{cfg.host}:{cfg.port}/{cfg.auth}"
    error: str | None = None
    for timeout in (0.5, 1.5, 3.0):
        try:
            mc = SyncMongoClient(uri, serverSelectionTimeoutMS=int(timeout * 1000))
            mc.admin.command("ping")
            mc.close()
            return True, None
        except Exception as exc:
            error = str(exc)
            continue
    return False, error


def _redis_check(redis_url: str | None = None) -> tuple[bool, str | None]:
    error: str | None = None
    for timeout in (0.5, 1.0):
        try:
            url = redis_url or base_settings.redis_url
            r = redis.from_url(url, socket_connect_timeout=timeout)
            ok = bool(r.ping())
            try:
                r.close()
            except Exception:
                pass
            return ok, None if ok else "Ping failed"
        except Exception as exc:
            error = str(exc)
            continue
    return False, error


def _qdrant_check(qdrant_url: str | None = None) -> tuple[bool, str | None]:
    error: str | None = None
    for timeout in (0.8, 1.5):
        try:
            base_url = qdrant_url or base_settings.qdrant_url
            resp = requests.get(f"{base_url}/healthz", timeout=timeout)
            if resp.ok:
                return True, None
            error = f"HTTP {resp.status_code}"
        except Exception as exc:
            error = str(exc)
            continue
    return False, error


@app.get("/health", include_in_schema=False)
def health() -> dict[str, object]:
    """Health check with external service probes."""
    mongo_ok, mongo_err = _mongo_check()
    redis_ok, redis_err = _redis_check()
    qdrant_ok, qdrant_err = _qdrant_check()

    checks = {
        "mongo": {"ok": mongo_ok, "error": mongo_err},
        "redis": {"ok": redis_ok, "error": redis_err},
        "qdrant": {"ok": qdrant_ok, "error": qdrant_err},
    }
    status = "ok" if all(item["ok"] for item in checks.values()) else "degraded"
    return {
        "status": status,
        "mongo": mongo_ok,
        "redis": redis_ok,
        "qdrant": qdrant_ok,
        "details": checks,
    }


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    """Lightweight liveness probe used by container healthchecks."""
    return {"status": "ok"}


@app.get("/status")
def status(domain: str | None = None, project: str | None = None) -> dict[str, object]:
    """Return aggregated crawler and database status."""
    chosen = project or domain
    return status_dict(_normalize_project(chosen))




class KnowledgeCreate(BaseModel):
    name: str | None = None
    content: str
    domain: str | None = None
    project: str | None = None
    description: str | None = None
    url: str | None = None


class KnowledgeUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    description: str | None = None
    url: str | None = None
    project: str | None = None
    domain: str | None = None
    status: str | None = None
    status_message: str | None = None


class KnowledgeDeduplicate(BaseModel):
    project: str | None = None


class KnowledgePriorityPayload(BaseModel):
    order: list[str]


class KnowledgeQAPayload(BaseModel):
    question: str
    answer: str
    priority: int | None = 0


class KnowledgeQAReorderPayload(BaseModel):
    order: list[str]


class KnowledgeUnansweredClearPayload(BaseModel):
    project: str | None = None


class FeedbackCreatePayload(BaseModel):
    message: str
    name: str | None = None
    contact: str | None = None
    page: str | None = None
    project: str | None = None
    source: str | None = None


class FeedbackUpdatePayload(BaseModel):
    status: str | None = None
    note: str | None = None


class KnowledgeServiceConfig(BaseModel):
    enabled: bool
    idle_threshold_seconds: int | None = None
    poll_interval_seconds: int | None = None
    cooldown_seconds: int | None = None
    mode: Literal["auto", "manual"] | None = None
    processing_prompt: str | None = None


KNOWLEDGE_SERVICE_KEY = "knowledge_service"


class KnowledgeServiceRunRequest(BaseModel):
    reason: str | None = None


class IntelligentProcessingPromptPayload(BaseModel):
    enabled: bool | None = None
    mode: Literal["auto", "manual"] | None = None
    processing_prompt: str | None = None

QA_SUPPORTED_EXTENSIONS = {".xlsx", ".xlsm", ".xltx", ".xltm", ".csv"}


class KnowledgeQaItem(BaseModel):
    question: str
    answer: str
    priority: int | None = None


class KnowledgeQaUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    priority: int | None = None


class KnowledgeQaReorder(BaseModel):
    order: list[str]


class KnowledgePriorityUpdate(BaseModel):
    order: list[str]


class KnowledgeUnansweredClear(BaseModel):
    project: str | None = None


def _detect_qa_columns(header: list[str]) -> tuple[int, int, int]:
    question_idx = -1
    answer_idx = -1
    priority_idx = -1
    for idx, title in enumerate(header):
        lowered = title.lower()
        if question_idx == -1 and any(token in lowered for token in ("вопрос", "question", "q:")):
            question_idx = idx
        if answer_idx == -1 and any(token in lowered for token in ("ответ", "answer", "a:")):
            answer_idx = idx
        if priority_idx == -1 and any(token in lowered for token in ("priority", "приоритет", "prio")):
            priority_idx = idx
    if question_idx == -1 and len(header) >= 1:
        question_idx = 0
    if answer_idx == -1 and len(header) >= 2:
        answer_idx = 1
    if question_idx == answer_idx:
        answer_idx = answer_idx + 1 if answer_idx + 1 < len(header) else -1
    if priority_idx == question_idx or priority_idx == answer_idx:
        priority_idx = -1
    return question_idx, answer_idx, priority_idx


async def _read_qa_upload(file: UploadFile) -> list[dict[str, str]]:
    """Parse uploaded Excel/CSV into question-answer pairs."""

    filename = file.filename or "qa.xlsx"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in QA_SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Формат файла не поддерживается")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Файл пустой")

    rows: list[list[str]] = []
    if ext == ".csv":
        try:
            text = payload.decode("utf-8-sig", errors="ignore")
        except Exception:
            text = payload.decode("cp1251", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        for raw in reader:
            rows.append([str(cell).strip() for cell in raw])
    else:
        wb = load_workbook(filename=io.BytesIO(payload), read_only=True, data_only=True)
        sheet = wb.active
        for row in sheet.iter_rows(values_only=True):
            rows.append(["" if cell is None else str(cell).strip() for cell in row])

    if not rows:
        return []

    header = rows[0]
    has_header = any(cell for cell in header)
    if has_header:
        q_idx, a_idx, p_idx = _detect_qa_columns(header)
        data_rows = rows[1:]
    else:
        q_idx = 0
        a_idx = 1 if len(header) > 1 else -1
        p_idx = 2 if len(header) > 2 else -1
        data_rows = rows

    pairs: list[dict[str, str]] = []
    for row in data_rows:
        if q_idx >= len(row) or q_idx < 0:
            continue
        question = (row[q_idx] or "").strip()
        answer = (row[a_idx] or "").strip() if 0 <= a_idx < len(row) else ""
        if not question or not answer:
            continue
        priority_value: str | None = None
        if 0 <= p_idx < len(row):
            priority_cell = (row[p_idx] or "").strip()
            if priority_cell != "":
                priority_value = priority_cell
        if priority_value is not None:
            pairs.append({"question": question, "answer": answer, "priority": priority_value})
        else:
            pairs.append({"question": question, "answer": answer})
    return pairs


async def _refine_qa_with_llm(
    pairs: list[dict[str, str]],
    *,
    project_model: Project | None,
) -> list[dict[str, str]]:
    """Use LLM to normalize QA pairs when possible."""

    if not pairs:
        return []
    sample = pairs[: min(len(pairs), 80)]
    prompt = (
        "Ты обрабатываешь справочник вопросов и ответов."
        " Отформатируй данные в компактный JSON-массив."
        " На входе — список объектов JSON с полями question и answer."
        " Приведи каждый вопрос и ответ к аккуратной форме (одно предложение)."
        " Проверь, что ответы содержат информативный текст и нет пустых значений."
        " Верни только JSON массив без комментариев.\n\n"
        f"Входные данные:\n{json.dumps(sample, ensure_ascii=False)}\n\nJSON:"
    )

    chunks: list[str] = []
    try:
        model_override = None
        if project_model and isinstance(project_model.llm_model, str):
            trimmed = project_model.llm_model.strip()
            if trimmed:
                model_override = trimmed
        async for token in llm_client.generate(prompt, model=model_override):
            chunks.append(token)
            if len("".join(chunks)) >= 16000:
                break
        raw = "".join(chunks).strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("qa_llm_refine_failed", error=str(exc))
        return pairs

    if not raw:
        return pairs

    try:
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1:
            raw = raw[start : end + 1]
        parsed = json.loads(raw)
        refined: list[dict[str, str]] = []
        for item in parsed:
            question = str(item.get("question", "")).strip()
            answer = str(item.get("answer", "")).strip()
            if question and answer:
                refined.append({"question": question, "answer": answer})
        return refined or pairs
    except Exception as exc:  # noqa: BLE001
        logger.warning("qa_llm_parse_failed", error=str(exc))
        return pairs


class PromptGenerationRequest(BaseModel):
    url: str
    role: str | None = None



async def _knowledge_service_status_impl(request: Request) -> ORJSONResponse:
    doc = await request.state.mongo.get_setting(KNOWLEDGE_SERVICE_KEY) or {}
    enabled = bool(doc.get("enabled", False))
    idle = int(doc.get("idle_threshold_seconds") or 300)
    poll = int(doc.get("poll_interval_seconds") or 60)
    cooldown = int(doc.get("cooldown_seconds") or 900)
    raw_mode = str(doc.get("mode") or "").strip().lower()
    if raw_mode not in KNOWLEDGE_SERVICE_ALLOWED_MODES:
        raw_mode = "auto" if enabled else KNOWLEDGE_SERVICE_DEFAULT_MODE
    prompt_value = doc.get("processing_prompt")
    if not isinstance(prompt_value, str) or not prompt_value.strip():
        prompt_value = KNOWLEDGE_SERVICE_DEFAULT_PROMPT
    else:
        prompt_value = prompt_value.strip()
    manual_reason = doc.get("manual_reason")
    if isinstance(manual_reason, str):
        manual_reason = manual_reason.strip() or None
        if manual_reason and len(manual_reason) > 120:
            manual_reason = manual_reason[:120]
    else:
        manual_reason = None
    message_value = doc.get("message")
    if not message_value and raw_mode == "manual":
        message_value = KNOWLEDGE_SERVICE_MANUAL_MESSAGE
    payload = {
        "enabled": enabled,
        "running": bool(doc.get("running", False)),
        "idle_threshold_seconds": max(60, idle),
        "poll_interval_seconds": max(15, poll),
        "cooldown_seconds": max(60, cooldown),
        "last_run_ts": doc.get("last_run_ts"),
        "last_reason": doc.get("last_reason"),
        "last_queue": doc.get("last_queue"),
        "idle_seconds": doc.get("idle_seconds"),
        "last_seen_ts": doc.get("last_seen_ts"),
        "updated_at": doc.get("updated_at"),
        "last_error": doc.get("last_error"),
        "message": message_value,
        "mode": raw_mode,
        "processing_prompt": prompt_value,
        "manual_reason": manual_reason,
    }
    return ORJSONResponse(payload)


async def _knowledge_service_update_impl(request: Request, payload: "KnowledgeServiceConfig") -> ORJSONResponse:
    current = await request.state.mongo.get_setting(KNOWLEDGE_SERVICE_KEY) or {}
    updated = current.copy()
    updated["enabled"] = bool(payload.enabled)
    if payload.idle_threshold_seconds is not None:
        updated["idle_threshold_seconds"] = max(60, int(payload.idle_threshold_seconds))
    if payload.poll_interval_seconds is not None:
        updated["poll_interval_seconds"] = max(15, int(payload.poll_interval_seconds))
    if payload.cooldown_seconds is not None:
        updated["cooldown_seconds"] = max(60, int(payload.cooldown_seconds))
    if payload.mode is not None:
        mode_value = str(payload.mode).strip().lower()
        if mode_value in KNOWLEDGE_SERVICE_ALLOWED_MODES:
            updated["mode"] = mode_value
    if payload.processing_prompt is not None:
        prompt_value = payload.processing_prompt.strip()
        updated["processing_prompt"] = prompt_value or KNOWLEDGE_SERVICE_DEFAULT_PROMPT
    updated["updated_at"] = time.time()
    await request.state.mongo.set_setting(KNOWLEDGE_SERVICE_KEY, updated)
    return ORJSONResponse(
        {
            "status": "ok",
            "enabled": updated["enabled"],
            "mode": updated.get("mode", KNOWLEDGE_SERVICE_DEFAULT_MODE),
        }
    )


async def _knowledge_service_run_impl(
    request: Request,
    payload: "KnowledgeServiceRunRequest" | None,
) -> ORJSONResponse:
    current = await request.state.mongo.get_setting(KNOWLEDGE_SERVICE_KEY) or {}
    reason_raw = (payload.reason if payload else None) or "manual"
    manual_reason = str(reason_raw).strip() or "manual"
    if len(manual_reason) > 120:
        manual_reason = manual_reason[:120]
    normalized_reason = "manual"
    started_at = time.time()

    state = current.copy()
    state.update(
        {
            "last_reason": normalized_reason,
            "manual_reason": manual_reason,
            "message": (
                "Интеллектуальная обработка: выполняем ручной запуск"
                if manual_reason == "manual"
                else f"Интеллектуальная обработка: выполняем ручной запуск (причина: {manual_reason})"
            ),
            "last_seen_ts": started_at,
            "idle_seconds": 0.0,
            "updated_at": started_at,
        }
    )
    await request.state.mongo.set_setting(KNOWLEDGE_SERVICE_KEY, state)

    def _run_update() -> str | None:
        try:
            from worker import update_vector_store

            update_vector_store()
            return None
        except Exception as exc:  # noqa: BLE001
            logger.exception("knowledge_service_manual_run_failed", error=str(exc))
            return str(exc)

    loop = asyncio.get_running_loop()
    error_text = await loop.run_in_executor(None, _run_update)

    finished_at = time.time()
    completion_message = (
        "Интеллектуальная обработка завершена успешно"
        if not error_text
        else f"Интеллектуальная обработка завершена с ошибкой: {error_text}"
    )
    if manual_reason != "manual":
        completion_message = f"{completion_message} (причина: {manual_reason})"
    state.update(
        {
            "last_run_ts": finished_at,
            "last_error": error_text,
            "message": completion_message,
            "updated_at": finished_at,
            "last_seen_ts": finished_at,
            "idle_seconds": 0.0,
        }
    )
    await request.state.mongo.set_setting(KNOWLEDGE_SERVICE_KEY, state)
    return ORJSONResponse({"status": "ok", "error": error_text})





FEEDBACK_ALLOWED_STATUSES = {"open", "in_progress", "done", "dismissed"}


class FeedbackCreatePayload(BaseModel):
    message: str
    name: str | None = None
    contact: str | None = None
    page: str | None = None
    project: str | None = None
    source: str | None = None


class FeedbackUpdatePayload(BaseModel):
    status: Literal["open", "in_progress", "done", "dismissed"]
    note: str | None = None


class OllamaInstallRequest(BaseModel):
    model: str


class OllamaServerPayload(BaseModel):
    name: str
    base_url: str
    enabled: bool = True




async def _ensure_ollama_reachable(base_url: str, timeout: float = 2.5) -> None:
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = f"Сервер ответил ошибкой HTTP {exc.response.status_code}"
        raise HTTPException(status_code=400, detail=detail) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=400, detail=f"Не удалось подключиться: {exc}") from exc





class ProjectCreate(BaseModel):
    name: str
    title: str | None = None
    domain: str | None = None
    admin_username: str | None = None
    admin_password: str | None = None
    llm_model: str | None = None
    llm_prompt: str | None = None
    llm_emotions_enabled: bool | None = None
    llm_voice_enabled: bool | None = None
    llm_voice_model: str | None = None
    llm_sources_enabled: bool | None = None
    debug_enabled: bool | None = None
    debug_info_enabled: bool | None = None
    knowledge_image_caption_enabled: bool | None = None
    bitrix_enabled: bool | None = None
    bitrix_webhook_url: str | None = None
    telegram_token: str | None = None
    telegram_auto_start: bool | None = None
    max_token: str | None = None
    max_auto_start: bool | None = None
    vk_token: str | None = None
    vk_auto_start: bool | None = None
    widget_url: str | None = None
    mail_enabled: bool | None = None
    mail_imap_host: str | None = None
    mail_imap_port: int | None = None
    mail_imap_ssl: bool | None = None
    mail_smtp_host: str | None = None
    mail_smtp_port: int | None = None
    mail_smtp_tls: bool | None = None
    mail_username: str | None = None
    mail_password: str | None = None
    mail_from: str | None = None
    mail_signature: str | None = None


@app.get("/api/v1/admin/knowledge", response_class=ORJSONResponse)
async def admin_knowledge(
    request: Request,
    q: str | None = None,
    limit: int = 50,
    domain: str | None = None,
    project: str | None = None,
) -> ORJSONResponse:
    """Return knowledge base documents for the admin UI."""

    try:
        limit = max(1, min(int(limit), 1000))
    except Exception:  # noqa: BLE001
        limit = 50

    selector = project or domain
    project_name, project, mongo_client, owns_client = await _get_project_context(
        request, selector
    )

    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)
    filter_query = {"project": project_name} if project_name else {}

    count_future: asyncio.Future[int] | None = None
    try:
        if q:
            docs_models = await mongo_client.search_documents(
                collection, q, project=project_name
            )
            matched = len(docs_models)
            total = matched
            has_more = matched >= limit
        else:
            count_future = mongo_client.db[collection].count_documents(filter_query or {})
            cursor = (
                mongo_client.db[collection]
                .find(filter_query, {"_id": False})
                .sort([("ts", -1), ("name", 1)])
                .limit(limit + 1)
            )
            docs_models = [doc async for doc in cursor]
            has_more = len(docs_models) > limit
            if has_more:
                docs_models = docs_models[:limit]
            total = await count_future
            matched = total
            count_future = None

        documents: list[dict[str, Any]] = []
        for item in docs_models:
            if isinstance(item, Document):
                documents.append(item.model_dump(by_alias=True))
                continue

            raw = dict(item)
            if "fileId" not in raw and "file_id" in raw:
                raw["fileId"] = raw.pop("file_id")
            raw.setdefault("name", "")
            raw.setdefault("description", "")
            raw.setdefault("project", project_name)
            raw.setdefault("domain", project.domain if project else None)
            if raw.get("fileId") is not None:
                raw["fileId"] = str(raw["fileId"])
            if raw.get("ts") is not None:
                try:
                    raw["ts"] = float(raw["ts"])
                except (TypeError, ValueError):
                    raw["ts"] = None
            try:
                documents.append(Document(**raw).model_dump(by_alias=True))
            except ValidationError as exc:
                logger.debug("document_deserialize_failed", error=str(exc), keys=list(raw.keys()))
                documents.append(raw)
        for doc in documents:
            file_id = doc.get("fileId")
            if file_id:
                doc["downloadUrl"] = _build_download_url(request, file_id)
    except Exception as exc:  # noqa: BLE001
        if count_future is not None and not count_future.done():
            with suppress(Exception):
                await count_future
        raise HTTPException(status_code=503, detail=f"MongoDB query failed: {exc}") from exc
    finally:
        if count_future is not None and not count_future.done():
            with suppress(Exception):
                await count_future
        if owns_client:
            await mongo_client.close()

    logger.info(
        "admin_knowledge_docs",
        project=project_name,
        documents=len(documents),
        query=q or None,
    )

    return ORJSONResponse(
        {
            "documents": documents,
            "query": q or None,
            "limit": limit,
            "matched": matched,
            "total": total,
            "has_more": has_more,
            "project": project_name,
        }
    )


@app.post("/api/v1/admin/knowledge", response_class=ORJSONResponse, status_code=201)
async def admin_create_knowledge(request: Request, payload: KnowledgeCreate) -> ORJSONResponse:
    """Create or update a text document in the knowledge base."""

    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Content is empty")

    name = (payload.name or "").strip()
    if not name:
        name = f"doc-{uuid4().hex[:8]}"

    project_name, project, mongo_client, owns_client = await _get_project_context(
        request, payload.project or payload.domain
    )
    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)

    description_input = (payload.description or "").strip()
    auto_description_pending = False
    status_message = None

    if description_input:
        description_value = description_input
    else:
        description_value = ""
        auto_description_pending = True
        status_message = "Автоописание в очереди"

    try:
        domain_value = payload.domain or (project.domain if project else None)
        file_id = await mongo_client.upsert_text_document(
            name=name,
            content=payload.content,
            documents_collection=collection,
            description=description_value,
            project=project_name,
            domain=domain_value,
            url=payload.url,
        )
        await mongo_client.db[collection].update_one(
            {"fileId": file_id},
            {
                "$set": {
                    "autoDescriptionPending": auto_description_pending,
                }
            },
            upsert=False,
        )
        if auto_description_pending:
            await mongo_client.update_document_status(
                collection,
                file_id,
                "pending_auto_description",
                status_message,
            )
            queue_auto_description(file_id, project_name)
        else:
            await mongo_client.update_document_status(
                collection,
                file_id,
                "ready",
                "Описание задано вручную",
            )
        if project_name:
            project_payload = Project(
                name=project.name if project else project_name,
                title=project.title if project else None,
                domain=domain_value,
                admin_username=project.admin_username if project else None,
                admin_password_hash=project.admin_password_hash if project else None,
                llm_model=project.llm_model if project else None,
                llm_prompt=project.llm_prompt if project else None,
                llm_emotions_enabled=project.llm_emotions_enabled if project else True,
                telegram_token=project.telegram_token if project else None,
                telegram_auto_start=project.telegram_auto_start if project else None,
                max_token=project.max_token if project else None,
                max_auto_start=project.max_auto_start if project else None,
                vk_token=project.vk_token if project else None,
                vk_auto_start=project.vk_auto_start if project else None,
                widget_url=project.widget_url if project else None,
                debug_enabled=project.debug_enabled if project and project.debug_enabled is not None else None,
            )
            await request.state.mongo.upsert_project(project_payload)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if owns_client:
            await mongo_client.close()

    return ORJSONResponse({
        "file_id": file_id,
        "name": name,
        "project": project_name,
        "domain": domain_value,
        "description": description_value,
        "auto_description_pending": auto_description_pending,
        "status": "pending_auto_description" if auto_description_pending else "ready",
        "status_message": status_message,
    })


@app.post("/api/v1/admin/knowledge/upload", response_class=ORJSONResponse, status_code=201)
async def admin_upload_knowledge(
    request: Request,
    project: str = Form(...),
    description: str | None = Form(None),
    name: str | None = Form(None),
    url: str | None = Form(None),
    file: UploadFile = File(...),
) -> ORJSONResponse:
    """Upload a binary document to GridFS and store metadata."""

    project_name, project_model, mongo_client, owns_client = await _get_project_context(
        request, project
    )
    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)

    filename = (name or file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="File name is required")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="File is empty")

    content_type = (file.content_type or "").lower()
    description_input = (description or "").strip()
    auto_description_pending = False
    status_message = None
    if description_input:
        description_value = description_input
    else:
        description_value = ""
        auto_description_pending = True
        status_message = "Автоописание в очереди"

    try:
        file_id = await mongo_client.upload_document(
            file_name=filename,
            file=payload,
            documents_collection=collection,
            description=description_value,
            url=url,
            content_type=file.content_type,
            project=project_name,
            domain=project_model.domain if project_model else None,
        )
        download_url = _build_download_url(request, file_id)
        await mongo_client.db[collection].update_one(
            {"fileId": file_id},
            {"$set": {"url": download_url, "content_type": file.content_type}},
            upsert=False,
        )
        await mongo_client.db[collection].update_one(
            {"fileId": file_id},
            {
                "$set": {
                    "autoDescriptionPending": auto_description_pending,
                }
            },
            upsert=False,
        )
        if auto_description_pending:
            await mongo_client.update_document_status(
                collection,
                file_id,
                "pending_auto_description",
                status_message,
            )
            queue_auto_description(file_id, project_name)
        else:
            await mongo_client.update_document_status(
                collection,
                file_id,
                "ready",
                "Описание задано вручную",
            )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if owns_client:
            await mongo_client.close()

    return ORJSONResponse(
        {
            "file_id": file_id,
            "name": filename,
            "project": project_name,
            "download_url": download_url,
            "content_type": file.content_type,
            "description": description_value,
            "auto_description_pending": auto_description_pending,
            "status": "pending_auto_description" if auto_description_pending else "ready",
            "status_message": status_message,
        }
    )


@app.post("/api/v1/admin/knowledge/deduplicate", response_class=ORJSONResponse)
async def admin_deduplicate_knowledge(request: Request, payload: KnowledgeDeduplicate) -> ORJSONResponse:
    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)
    project_name, _, _, _ = await _get_project_context(request, payload.project)
    try:
        summary = await request.state.mongo.deduplicate_documents(collection, project_name)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ORJSONResponse({"project": project_name, **summary})


@app.post("/api/v1/admin/knowledge/reindex", response_class=ORJSONResponse)
async def admin_reindex_documents(request: Request) -> ORJSONResponse:
    _require_super_admin(request)
    loop = asyncio.get_running_loop()

    def _run_update() -> None:
        from worker import update_vector_store

        update_vector_store()

    loop.run_in_executor(None, _run_update)
    return ORJSONResponse({"status": "queued"})

@app.delete("/api/v1/admin/knowledge", response_class=ORJSONResponse)
async def admin_clear_knowledge(request: Request, project: str | None = None) -> ORJSONResponse:
    """Remove documents from the knowledge base (optionally scoped to a project)."""

    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)
    project_name, _, mongo_client, _ = await _get_project_context(request, project)
    summary = await mongo_client.delete_documents(collection, project_name)

    loop = asyncio.get_running_loop()

    def _refresh() -> None:
        from worker import update_vector_store

        update_vector_store()

    loop.run_in_executor(None, _refresh)
    return ORJSONResponse({"project": project_name, **summary})


@app.get("/api/v1/admin/knowledge/priority", response_class=ORJSONResponse)
async def admin_get_knowledge_priority(request: Request, project: str | None = None) -> ORJSONResponse:
    project_name, _, mongo_client, _ = await _get_project_context(request, project)
    try:
        stored_order = await mongo_client.get_knowledge_priority(project_name)
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_priority_fetch_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to load knowledge priority") from exc

    available_sources = list(_KNOWN_KNOWLEDGE_SOURCES)
    normalized = []
    for entry in stored_order or []:
        candidate = str(entry).strip()
        if candidate in available_sources and candidate not in normalized:
            normalized.append(candidate)
    if not normalized:
        normalized = [source for source in _DEFAULT_KNOWLEDGE_PRIORITY if source in available_sources]
    if not normalized:
        normalized = available_sources

    return ORJSONResponse(
        {
            "order": normalized,
            "available": available_sources,
            "project": project_name,
        }
    )


@app.post("/api/v1/admin/knowledge/priority", response_class=ORJSONResponse)
async def admin_set_knowledge_priority(
    request: Request,
    payload: KnowledgePriorityPayload,
    project: str | None = None,
) -> ORJSONResponse:
    project_name, _, mongo_client, _ = await _get_project_context(request, project)

    available_sources = list(_KNOWN_KNOWLEDGE_SOURCES)
    lookup = {source.lower(): source for source in available_sources}
    normalized: list[str] = []
    for entry in payload.order or []:
        candidate = lookup.get(str(entry or "").strip().lower())
        if candidate and candidate not in normalized:
            normalized.append(candidate)

    for fallback in _DEFAULT_KNOWLEDGE_PRIORITY:
        if fallback in available_sources and fallback not in normalized:
            normalized.append(fallback)

    if not normalized:
        normalized = available_sources

    try:
        await mongo_client.set_knowledge_priority(project_name, normalized)
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_priority_save_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to save knowledge priority") from exc

    return ORJSONResponse({"order": normalized, "project": project_name})


@app.delete("/api/v1/admin/knowledge/{file_id}", response_class=ORJSONResponse)
async def admin_delete_knowledge_document(
    request: Request,
    file_id: str,
    project: str | None = None,
) -> ORJSONResponse:
    """Delete a single knowledge document and its binary payload."""

    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)
    desired_project = _resolve_admin_project(request, project)
    mongo_client = _get_mongo_client(request)

    try:
        document = await mongo_client.db[collection].find_one({"fileId": file_id})
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_document_lookup_failed", file_id=file_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to load document metadata") from exc

    if not document:
        raise HTTPException(status_code=404, detail="document_not_found")

    document_project = _normalize_project(
        document.get("project") or document.get("domain")
    )
    if desired_project and document_project and desired_project != document_project:
        raise HTTPException(status_code=403, detail="document_forbidden")

    try:
        await mongo_client.delete_document(collection, file_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Failed to delete document") from exc

    loop = asyncio.get_running_loop()

    def _refresh_vectors() -> None:
        from worker import update_vector_store

        update_vector_store()

    loop.run_in_executor(None, _refresh_vectors)

    return ORJSONResponse(
        {
            "removed": True,
            "file_id": file_id,
            "project": document_project or desired_project,
        }
    )


@app.get("/api/v1/admin/knowledge/qa", response_class=ORJSONResponse)
async def admin_list_knowledge_qa(
    request: Request,
    project: str | None = None,
    limit: int = 500,
) -> ORJSONResponse:
    try:
        safe_limit = max(1, min(int(limit), 1000))
    except Exception:
        safe_limit = 500

    project_name, _, mongo_client, _ = await _get_project_context(request, project)

    try:
        items = await mongo_client.list_qa_pairs(project_name, limit=safe_limit)
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_qa_list_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to load QA pairs") from exc

    try:
        stored_order = await mongo_client.get_knowledge_priority(project_name)
    except Exception:
        stored_order = []

    available_sources = list(_KNOWN_KNOWLEDGE_SOURCES)
    normalized_priority = [item for item in stored_order if item in available_sources]
    if not normalized_priority:
        normalized_priority = [src for src in _DEFAULT_KNOWLEDGE_PRIORITY if src in available_sources]
    if not normalized_priority:
        normalized_priority = available_sources

    return ORJSONResponse(
        {
            "items": items,
            "priority": normalized_priority,
            "project": project_name,
        }
    )


@app.post("/api/v1/admin/knowledge/qa/upload", response_class=ORJSONResponse, status_code=201)
async def admin_import_knowledge_qa_file(
    request: Request,
    project: str = Form(...),
    file: UploadFile = File(...),
    refine: str | None = Form(None),
) -> ORJSONResponse:
    project_name, project_model, mongo_client, _ = await _get_project_context(request, project)

    try:
        pairs = await _read_qa_upload(file)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_qa_import_parse_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=400, detail="Failed to read QA file") from exc

    if not pairs:
        return ORJSONResponse(
            {"inserted": 0, "updated": 0, "skipped": 0, "total": 0, "project": project_name},
            status_code=201,
        )

    refine_flag = False
    if refine is not None:
        refine_flag = str(refine).strip().lower() in {"1", "true", "yes", "on"}

    if refine_flag:
        try:
            pairs = await _refine_qa_with_llm(pairs, project_model=project_model)
        except Exception as exc:  # noqa: BLE001
            logger.warning("knowledge_qa_import_refine_failed", project=project_name, error=str(exc))

    normalized: list[dict[str, object]] = []
    skipped = 0
    for pair in pairs:
        question = str(pair.get("question") or "").strip()
        answer = str(pair.get("answer") or "").strip()
        if not question or not answer:
            skipped += 1
            continue
        priority_value = 0
        if "priority" in pair and pair.get("priority") not in (None, ""):
            raw_priority = str(pair.get("priority")).replace(",", ".").strip()
            try:
                priority_value = int(float(raw_priority))
            except Exception:
                priority_value = 0
        normalized.append(
            {
                "question": question,
                "answer": answer,
                "priority": priority_value,
            }
        )

    if not normalized:
        return ORJSONResponse(
            {
                "inserted": 0,
                "updated": 0,
                "skipped": skipped or len(pairs),
                "total": len(pairs),
                "project": project_name,
            },
            status_code=201,
        )

    try:
        result = await mongo_client.insert_qa_pairs(project_name, normalized)
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_qa_import_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to import QA pairs") from exc

    summary: dict[str, object] = {
        "inserted": int(result.get("inserted", 0)),
        "updated": int(result.get("updated", 0)),
        "skipped": skipped,
        "total": len(pairs),
        "project": project_name,
    }
    return ORJSONResponse(summary, status_code=201)


@app.post("/api/v1/admin/knowledge/qa", response_class=ORJSONResponse, status_code=201)
async def admin_create_knowledge_qa(
    request: Request,
    payload: KnowledgeQAPayload,
    project: str | None = None,
) -> ORJSONResponse:
    project_name, _, mongo_client, _ = await _get_project_context(request, project)

    question = payload.question.strip()
    answer = payload.answer.strip()
    if not question or not answer:
        raise HTTPException(status_code=400, detail="question_and_answer_required")

    try:
        result = await mongo_client.insert_qa_pairs(
            project_name,
            [
                {
                    "question": question,
                    "answer": answer,
                    "priority": payload.priority,
                }
            ],
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_qa_insert_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to save QA pair") from exc

    return ORJSONResponse({**result, "project": project_name})


@app.put("/api/v1/admin/knowledge/qa/{pair_id}", response_class=ORJSONResponse)
async def admin_update_knowledge_qa(
    request: Request,
    pair_id: str,
    payload: KnowledgeQAPayload,
) -> ORJSONResponse:
    mongo_client = _get_mongo_client(request)
    existing = await _fetch_qa_document(mongo_client, pair_id)
    if not existing:
        raise HTTPException(status_code=404, detail="qa_not_found")

    project_scope = _resolve_admin_project(request, existing.get("project"))

    question = payload.question.strip()
    answer = payload.answer.strip()
    if not question or not answer:
        raise HTTPException(status_code=400, detail="question_and_answer_required")

    try:
        updated = await mongo_client.update_qa_pair(
            pair_id,
            question=question,
            answer=answer,
            priority=payload.priority,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_qa_update_failed", pair_id=pair_id, project=project_scope, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to update QA pair") from exc

    if not updated:
        raise HTTPException(status_code=404, detail="qa_not_found")

    if project_scope:
        doc_project = _normalize_project(updated.get("project"))
        if doc_project and doc_project != project_scope:
            raise HTTPException(status_code=403, detail="project_forbidden")

    return ORJSONResponse(updated)


@app.delete("/api/v1/admin/knowledge/qa/{pair_id}", response_class=ORJSONResponse)
async def admin_delete_knowledge_qa(request: Request, pair_id: str) -> ORJSONResponse:
    mongo_client = _get_mongo_client(request)
    existing = await _fetch_qa_document(mongo_client, pair_id)
    if not existing:
        raise HTTPException(status_code=404, detail="qa_not_found")

    project_scope = _resolve_admin_project(request, existing.get("project"))

    try:
        removed = await mongo_client.delete_qa_pair(pair_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_qa_delete_failed", pair_id=pair_id, project=project_scope, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to delete QA pair") from exc

    if not removed:
        raise HTTPException(status_code=404, detail="qa_not_found")

    return ORJSONResponse({"removed": True, "id": pair_id})


@app.post("/api/v1/admin/knowledge/qa/reorder", response_class=ORJSONResponse)
async def admin_reorder_knowledge_qa(
    request: Request,
    payload: KnowledgeQAReorderPayload,
    project: str | None = None,
) -> ORJSONResponse:
    project_name, _, mongo_client, _ = await _get_project_context(request, project)
    order = [str(item).strip() for item in payload.order or [] if str(item).strip()]
    try:
        await mongo_client.reorder_qa_pairs(project_name, order)
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_qa_reorder_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to reorder QA pairs") from exc

    return ORJSONResponse({"order": order, "project": project_name})


@app.get("/api/v1/admin/knowledge/unanswered", response_class=ORJSONResponse)
async def admin_list_unanswered(
    request: Request,
    project: str | None = None,
    limit: int = 500,
) -> ORJSONResponse:
    try:
        safe_limit = max(1, min(int(limit), 5000))
    except Exception:
        safe_limit = 500

    project_name, _, mongo_client, _ = await _get_project_context(request, project)

    try:
        items = await mongo_client.list_unanswered_questions(project_name, limit=safe_limit)
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_unanswered_list_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to load unanswered questions") from exc

    return ORJSONResponse({"items": items, "project": project_name})


@app.post("/api/v1/admin/knowledge/unanswered/clear", response_class=ORJSONResponse)
async def admin_clear_unanswered(
    request: Request,
    payload: KnowledgeUnansweredClearPayload,
) -> ORJSONResponse:
    project_hint = payload.project
    project_name, _, mongo_client, _ = await _get_project_context(request, project_hint)

    try:
        removed = await mongo_client.clear_unanswered_questions(project_name)
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_unanswered_clear_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to clear unanswered questions") from exc

    return ORJSONResponse({"removed": removed, "project": project_name})


@app.get("/api/v1/admin/knowledge/unanswered/export")
async def admin_export_unanswered(
    request: Request,
    project: str | None = None,
    limit: int = 1000,
) -> Response:
    try:
        safe_limit = max(1, min(int(limit), 5000))
    except Exception:
        safe_limit = 1000

    project_name, _, mongo_client, _ = await _get_project_context(request, project)

    try:
        items = await mongo_client.list_unanswered_questions(project_name, limit=safe_limit)
    except Exception as exc:  # noqa: BLE001
        logger.error("knowledge_unanswered_export_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to export unanswered questions") from exc

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["question", "hits", "updated_at", "project"])
    for item in items:
        updated_at = item.get("updated_at")
        if isinstance(updated_at, (int, float)):
            updated_iso = datetime.utcfromtimestamp(updated_at).isoformat()
        else:
            updated_iso = str(updated_at or "")
        writer.writerow([
            item.get("question", ""),
            item.get("hits", 0),
            updated_iso,
            item.get("project") or (project_name or ""),
        ])

    filename = f"unanswered-{(project_name or 'all')}.csv"
    content = buffer.getvalue().encode("utf-8")
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return Response(content, media_type="text/csv", headers=headers)


@app.post("/api/v1/feedback", response_class=ORJSONResponse, status_code=201)
async def submit_feedback(feedback: FeedbackCreatePayload, request: Request) -> ORJSONResponse:
    message = (feedback.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="feedback_message_required")

    mongo_client = _get_mongo_client(request)
    project_name = _normalize_project(feedback.project)
    payload = {
        "message": message,
        "name": (feedback.name or "").strip() or None,
        "contact": (feedback.contact or "").strip() or None,
        "page": (feedback.page or "").strip() or None,
        "project": project_name,
        "source": (feedback.source or "web").strip().lower() or "web",
    }
    try:
        task = await mongo_client.create_feedback_task(payload)
    except Exception as exc:  # noqa: BLE001
        logger.error("feedback_create_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to submit feedback") from exc

    return ORJSONResponse({"task": task})


@app.get("/api/v1/admin/feedback", response_class=ORJSONResponse)
async def admin_list_feedback(request: Request, limit: int = 100) -> ORJSONResponse:
    _require_super_admin(request)
    try:
        safe_limit = max(1, min(int(limit), 200))
    except Exception:
        safe_limit = 100

    try:
        tasks = await request.state.mongo.list_feedback_tasks(limit=safe_limit)
    except Exception as exc:  # noqa: BLE001
        logger.error("feedback_list_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to load feedback") from exc

    return ORJSONResponse({"tasks": tasks})


@app.patch("/api/v1/admin/feedback/{task_id}", response_class=ORJSONResponse)
async def admin_update_feedback(
    request: Request,
    task_id: str,
    payload: FeedbackUpdatePayload,
) -> ORJSONResponse:
    _require_super_admin(request)

    updates: dict[str, object] = {}
    if payload.status is not None:
        status_value = payload.status.strip().lower()
        if status_value not in _FEEDBACK_STATUS_VALUES:
            raise HTTPException(status_code=400, detail="invalid_status")
        updates["status"] = status_value
    if payload.note is not None:
        note_value = payload.note.strip()
        updates["note"] = note_value

    if not updates:
        raise HTTPException(status_code=400, detail="no_updates_provided")

    try:
        result = await request.state.mongo.update_feedback_task(task_id, updates)
    except Exception as exc:  # noqa: BLE001
        logger.error("feedback_update_failed", task_id=task_id, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to update feedback task") from exc

    if not result:
        raise HTTPException(status_code=404, detail="feedback_not_found")

    return ORJSONResponse(result)


@app.get("/api/v1/admin/knowledge/service", response_class=ORJSONResponse)
async def admin_knowledge_service_status(request: Request) -> ORJSONResponse:
    _require_super_admin(request)
    return await _knowledge_service_status_impl(request)


@app.post("/api/v1/admin/knowledge/service", response_class=ORJSONResponse)
async def admin_knowledge_service_update(
    request: Request, payload: KnowledgeServiceConfig
) -> ORJSONResponse:
    _require_super_admin(request)
    return await _knowledge_service_update_impl(request, payload)


@app.get("/api/v1/knowledge/service", response_class=ORJSONResponse)
async def knowledge_service_status_alias(request: Request) -> ORJSONResponse:
    """Backward-compatible alias for knowledge service status."""

    return await _knowledge_service_status_impl(request)


@app.post("/api/v1/knowledge/service", response_class=ORJSONResponse)
async def knowledge_service_update_alias(
    request: Request, payload: KnowledgeServiceConfig
) -> ORJSONResponse:
    """Backward-compatible alias for knowledge service updates."""

    return await _knowledge_service_update_impl(request, payload)


@app.post("/api/v1/admin/knowledge/service/run", response_class=ORJSONResponse)
async def admin_knowledge_service_run(
    request: Request,
    payload: KnowledgeServiceRunRequest | None = None,
) -> ORJSONResponse:
    _require_super_admin(request)
    return await _knowledge_service_run_impl(request, payload)


@app.post("/api/v1/knowledge/service/run", response_class=ORJSONResponse)
async def knowledge_service_run_alias(
    request: Request,
    payload: KnowledgeServiceRunRequest | None = None,
) -> ORJSONResponse:
    """Backward-compatible alias for manual knowledge service runs."""

    return await _knowledge_service_run_impl(request, payload)


@app.get("/api/intelligent-processing/state", response_class=ORJSONResponse)
async def intelligent_processing_state(request: Request) -> ORJSONResponse:
    identity = _require_super_admin(request)
    logger.info(
        "intelligent_processing_state_requested",
        username=identity.username,
        is_super=identity.is_super,
    )
    return await _knowledge_service_status_impl(request)


@app.post("/api/intelligent-processing/prompt", response_class=ORJSONResponse)
async def intelligent_processing_save_prompt(
    request: Request,
    payload: IntelligentProcessingPromptPayload,
) -> ORJSONResponse:
    identity = _require_super_admin(request)
    current = await request.state.mongo.get_setting(KNOWLEDGE_SERVICE_KEY) or {}
    config = KnowledgeServiceConfig(
        enabled=bool(payload.enabled)
        if payload.enabled is not None
        else bool(current.get("enabled", False)),
        mode=payload.mode if payload.mode is not None else current.get("mode"),
        processing_prompt=(
            payload.processing_prompt
            if payload.processing_prompt is not None
            else current.get("processing_prompt")
        ),
    )
    logger.info(
        "intelligent_processing_prompt_update",
        username=identity.username,
        is_super=identity.is_super,
        enabled=config.enabled,
        mode=config.mode,
        has_prompt=bool(config.processing_prompt),
    )
    return await _knowledge_service_update_impl(request, config)


@llm_router.get("/admin/knowledge/service", response_class=ORJSONResponse)
async def llm_knowledge_service_status(request: Request) -> ORJSONResponse:
    return await _knowledge_service_status_impl(request)


@llm_router.post("/admin/knowledge/service", response_class=ORJSONResponse)
async def llm_knowledge_service_update(
    request: Request, payload: KnowledgeServiceConfig
) -> ORJSONResponse:
    return await _knowledge_service_update_impl(request, payload)


@llm_router.post("/admin/knowledge/service/run", response_class=ORJSONResponse)
async def llm_knowledge_service_run(
    request: Request,
    payload: KnowledgeServiceRunRequest | None = None,
) -> ORJSONResponse:
    return await _knowledge_service_run_impl(request, payload)

@app.get("/api/v1/admin/projects/names", response_class=ORJSONResponse)
async def admin_project_names(request: Request, limit: int = 100) -> ORJSONResponse:
    """Return a list of known project identifiers."""

    identity = _require_admin(request)
    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)
    mongo_client = _get_mongo_client(request)
    names = await mongo_client.list_project_names(collection, limit=limit)
    if not identity.is_super:
        allowed = {proj.strip().lower() for proj in identity.projects if proj}
        names = [name for name in names if name in allowed]
        default_name = identity.primary_project
    else:
        default_name = _normalize_project(None)
    if default_name and default_name not in names:
        names.insert(0, default_name)
    return ORJSONResponse({"projects": names})


@app.get("/api/v1/admin/llm/models", response_class=ORJSONResponse)
def admin_llm_models() -> ORJSONResponse:
    """Return available LLM model identifiers."""

    models = base_settings.get_available_llm_models()
    return ORJSONResponse({"models": models})


@app.get("/api/v1/admin/llm/availability", response_class=ORJSONResponse)
async def admin_llm_availability(request: Request) -> ORJSONResponse:
    """Expose a simple availability flag for the LLM cluster."""

    _require_admin(request)
    available = False
    try:
        cluster = get_cluster_manager()
    except RuntimeError:
        available = False
    else:
        try:
            available = bool(cluster.has_available())
        except Exception:
            available = False
    return ORJSONResponse({"available": available})


@app.get("/api/v1/admin/ollama/catalog", response_class=ORJSONResponse)
async def admin_ollama_catalog(request: Request) -> ORJSONResponse:
    _require_super_admin(request)

    cli_available = ollama_available()
    remote_available = False
    try:
        cluster = get_cluster_manager()
    except RuntimeError:
        cluster = None
    if cluster is not None:
        try:
            remote_available = bool(cluster.has_available())
        except Exception:
            remote_available = False

    # Get installed models from both local and remote sources
    from backend.ollama import list_installed_models_async
    all_models = await list_installed_models_async(cluster=cluster)

    installed_models = [
        {
            "name": model.name,
            "size_bytes": model.size_bytes,
            "size_human": model.size_human,
            "modified_at": model.modified_at,
            "digest": model.digest,
        }
        for model in all_models
    ]
    installed_names = {item["name"] for item in installed_models}
    popular = popular_models_with_size()
    for item in popular:
        item["installed"] = item.get("name") in installed_names
    jobs = await _snapshot_install_jobs()
    default_model = installed_models[0]["name"] if installed_models else None
    return ORJSONResponse(
        {
            "available": bool(cli_available or remote_available),
            "cli_available": cli_available,
            "remote_available": remote_available,
            "installed": installed_models,
            "popular": popular,
            "jobs": jobs,
            "default_model": default_model,
        }
    )


@app.get("/api/v1/admin/ollama/servers", response_class=ORJSONResponse)
async def admin_ollama_servers(request: Request) -> ORJSONResponse:
    _require_super_admin(request)
    cluster = get_cluster_manager()
    servers = await cluster.describe()
    return ORJSONResponse({"servers": servers})


@app.post("/api/v1/admin/ollama/servers", response_class=ORJSONResponse)
async def admin_ollama_server_upsert(request: Request, payload: OllamaServerPayload) -> ORJSONResponse:
    _require_super_admin(request)
    name = (payload.name or "").strip().lower()
    base_url = (payload.base_url or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if not base_url:
        raise HTTPException(status_code=400, detail="base_url is required")
    try:
        if payload.enabled:
            await _ensure_ollama_reachable(base_url)
        server = OllamaServer(name=name, base_url=base_url, enabled=payload.enabled)
        stored = await _get_mongo_client(request).upsert_ollama_server(server)
        await reload_cluster()
        cluster = get_cluster_manager()
        servers = await cluster.describe()
        data = next((item for item in servers if item.get("name") == stored.name), None)
        return ORJSONResponse({"server": data})
    except Exception as exc:  # noqa: BLE001
        logger.error("admin_ollama_server_upsert_failed", name=name, error=str(exc))
        raise


@app.delete("/api/v1/admin/ollama/servers/{name}", response_class=ORJSONResponse)
async def admin_ollama_server_delete(request: Request, name: str) -> ORJSONResponse:
    _require_super_admin(request)
    key = (name or "").strip().lower()
    if not key:
        raise HTTPException(status_code=400, detail="name is required")
    removed = await _get_mongo_client(request).delete_ollama_server(key)
    if not removed:
        raise HTTPException(status_code=404, detail="server_not_found")
    await reload_cluster()
    cluster = get_cluster_manager()
    servers = await cluster.describe()
    return ORJSONResponse({"servers": servers})


@app.post("/api/v1/admin/ollama/install", response_class=ORJSONResponse)
async def admin_ollama_install(request: Request, payload: "OllamaInstallRequest") -> ORJSONResponse:
    _require_super_admin(request)
    model = (payload.model or "").strip()
    if not model:
        raise HTTPException(status_code=400, detail="model is required")

    try:
        job = await _schedule_ollama_install(model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    snapshot = await _snapshot_install_jobs()
    return ORJSONResponse(
        {
            "status": job.get("status"),
            "model": model,
            "job": snapshot.get(model),
        }
    )


@app.post("/api/v1/feedback", response_class=ORJSONResponse)
async def submit_feedback(request: Request, payload: FeedbackCreatePayload) -> ORJSONResponse:
    message = (payload.message or "").strip()
    if len(message) < 3:
        raise HTTPException(status_code=400, detail="message is too short")
    if len(message) > 4000:
        message = message[:4000]

    mongo = _get_mongo_client(request)
    doc = await mongo.create_feedback_task(
        {
            "message": message,
            "name": (payload.name or "").strip() or None,
            "contact": (payload.contact or "").strip() or None,
            "page": payload.page,
            "project": payload.project,
            "source": payload.source or "widget",
        }
    )
    return ORJSONResponse({"status": "ok", "task": doc})


@app.get("/api/v1/admin/feedback", response_class=ORJSONResponse)
async def admin_feedback_list(request: Request, limit: int = 100) -> ORJSONResponse:
    _require_super_admin(request)
    mongo = _get_mongo_client(request)
    safe_limit = max(1, min(int(limit or 100), 500))
    tasks = await mongo.list_feedback_tasks(limit=safe_limit)
    return ORJSONResponse({"tasks": tasks})


@app.patch("/api/v1/admin/feedback/{task_id}", response_class=ORJSONResponse)
async def admin_feedback_update(request: Request, task_id: str, payload: FeedbackUpdatePayload) -> ORJSONResponse:
    _require_super_admin(request)
    status = payload.status
    if status not in FEEDBACK_ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail="invalid_status")

    mongo = _get_mongo_client(request)
    doc = await mongo.update_feedback_task(
        task_id,
        {
            "status": status,
            "note": payload.note,
        },
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="feedback_not_found")
    return ORJSONResponse({"task": doc})


@app.get("/api/v1/admin/telegram", response_class=ORJSONResponse)
async def telegram_status(request: Request) -> ORJSONResponse:
    _require_super_admin(request)
    hub: TelegramHub = request.app.state.telegram
    default_project = _normalize_project(None)
    project: Project | None = None
    if default_project:
        project = await request.state.mongo.get_project(default_project)
    token = (
        project.telegram_token if project and isinstance(project.telegram_token, str) else None
    )
    preview = _build_token_preview(token)
    auto_start = bool(project.telegram_auto_start) if project else False
    running = hub.is_project_running(default_project)
    last_error = hub.get_last_error(default_project) if default_project else None
    return ORJSONResponse(
        {
            "running": running,
            "token_set": bool(token),
            "token_preview": preview,
            "auto_start": auto_start,
            "project": default_project,
            "last_error": last_error,
        }
    )


@app.post("/api/v1/admin/telegram/config", response_class=ORJSONResponse)
async def telegram_config(request: Request, payload: TelegramConfig) -> ORJSONResponse:
    _require_super_admin(request)
    hub: TelegramHub = request.app.state.telegram
    default_project = _normalize_project(None)
    if not default_project:
        raise HTTPException(status_code=400, detail="Default project is not configured")

    existing = await request.state.mongo.get_project(default_project)
    data = existing.model_dump() if existing else {"name": default_project}
    if payload.token is not None:
        value = payload.token.strip()
        data["telegram_token"] = value or None
    if payload.auto_start is not None:
        data["telegram_auto_start"] = bool(payload.auto_start)

    project = Project(**data)
    saved = await request.state.mongo.upsert_project(project)
    await hub.ensure_runner(saved)
    return ORJSONResponse({"ok": True})


@app.post("/api/v1/admin/telegram/start", response_class=ORJSONResponse)
async def telegram_start(request: Request, payload: TelegramAction) -> ORJSONResponse:
    _require_super_admin(request)
    hub: TelegramHub = request.app.state.telegram
    default_project = _normalize_project(None)
    if not default_project:
        raise HTTPException(status_code=400, detail="Default project is not configured")

    existing = await request.state.mongo.get_project(default_project)
    data = existing.model_dump() if existing else {"name": default_project}
    token_value = payload.token.strip() if isinstance(payload.token, str) else None
    if token_value:
        data["telegram_token"] = token_value
    project = Project(**data)
    saved = await request.state.mongo.upsert_project(project)
    await hub.start_project(saved)
    return ORJSONResponse({"running": True})


@app.post("/api/v1/admin/telegram/stop", response_class=ORJSONResponse)
async def telegram_stop(request: Request) -> ORJSONResponse:
    _require_super_admin(request)
    hub: TelegramHub = request.app.state.telegram
    default_project = _normalize_project(None)
    if not default_project:
        raise HTTPException(status_code=400, detail="Default project is not configured")
    await hub.stop_project(default_project)
    return ORJSONResponse({"running": False})


@app.get("/api/v1/admin/max", response_class=ORJSONResponse)
async def max_status(request: Request) -> ORJSONResponse:
    _require_super_admin(request)
    hub: MaxHub = request.app.state.max
    mongo_client = _get_mongo_client(request)
    default_project = _normalize_project(None)
    project: Project | None = None
    if default_project:
        project = await mongo_client.get_project(default_project)
    token_value = (
        project.max_token.strip() if project and isinstance(project.max_token, str) else None
    )
    response = {
        "project": default_project,
        "running": hub.is_project_running(default_project),
        "token_set": bool(token_value),
        "token_preview": _build_token_preview(token_value),
        "auto_start": bool(project.max_auto_start) if project and project.max_auto_start is not None else False,
        "last_error": hub.get_last_error(default_project) if default_project else None,
    }
    return ORJSONResponse(response)


@app.post("/api/v1/admin/max/config", response_class=ORJSONResponse)
async def max_config(request: Request, payload: MaxConfig) -> ORJSONResponse:
    _require_super_admin(request)
    hub: MaxHub = request.app.state.max
    mongo_client = _get_mongo_client(request)
    default_project = _normalize_project(None)
    if not default_project:
        raise HTTPException(status_code=400, detail="Default project is not configured")

    existing = await mongo_client.get_project(default_project)
    data = existing.model_dump() if existing else {"name": default_project}
    if payload.token is not None:
        value = payload.token.strip()
        data["max_token"] = value or None
    if payload.auto_start is not None:
        data["max_auto_start"] = bool(payload.auto_start)

    project = Project(**data)
    saved = await mongo_client.upsert_project(project)
    await hub.ensure_runner(saved)
    return ORJSONResponse({"ok": True})


@app.post("/api/v1/admin/max/start", response_class=ORJSONResponse)
async def max_start(request: Request, payload: MaxAction) -> ORJSONResponse:
    _require_super_admin(request)
    hub: MaxHub = request.app.state.max
    mongo_client = _get_mongo_client(request)
    default_project = _normalize_project(None)
    if not default_project:
        raise HTTPException(status_code=400, detail="Default project is not configured")

    existing = await mongo_client.get_project(default_project)
    data = existing.model_dump() if existing else {"name": default_project}
    token_value = payload.token.strip() if isinstance(payload.token, str) else None
    if token_value:
        data["max_token"] = token_value
    project = Project(**data)
    saved = await mongo_client.upsert_project(project)
    await hub.start_project(saved)
    return ORJSONResponse({"running": True})


@app.post("/api/v1/admin/max/stop", response_class=ORJSONResponse)
async def max_stop(request: Request) -> ORJSONResponse:
    _require_super_admin(request)
    hub: MaxHub = request.app.state.max
    default_project = _normalize_project(None)
    if not default_project:
        raise HTTPException(status_code=400, detail="Default project is not configured")
    await hub.stop_project(default_project)
    return ORJSONResponse({"running": False})


@app.get("/api/v1/admin/vk", response_class=ORJSONResponse)
async def vk_status(request: Request) -> ORJSONResponse:
    _require_super_admin(request)
    hub: VkHub = request.app.state.vk
    mongo_client = _get_mongo_client(request)
    default_project = _normalize_project(None)
    project: Project | None = None
    if default_project:
        project = await mongo_client.get_project(default_project)
    token_value = (
        project.vk_token.strip() if project and isinstance(project.vk_token, str) else None
    )
    response = {
        "project": default_project,
        "running": hub.is_project_running(default_project),
        "token_set": bool(token_value),
        "token_preview": _build_token_preview(token_value),
        "auto_start": bool(project.vk_auto_start) if project and project.vk_auto_start is not None else False,
        "last_error": hub.get_last_error(default_project) if default_project else None,
    }
    return ORJSONResponse(response)


@app.post("/api/v1/admin/vk/config", response_class=ORJSONResponse)
async def vk_config(request: Request, payload: VkConfig) -> ORJSONResponse:
    _require_super_admin(request)
    hub: VkHub = request.app.state.vk
    mongo_client = _get_mongo_client(request)
    default_project = _normalize_project(None)
    if not default_project:
        raise HTTPException(status_code=400, detail="Default project is not configured")

    existing = await mongo_client.get_project(default_project)
    data = existing.model_dump() if existing else {"name": default_project}
    if payload.token is not None:
        value = payload.token.strip()
        data["vk_token"] = value or None
    if payload.auto_start is not None:
        data["vk_auto_start"] = bool(payload.auto_start)

    project = Project(**data)
    saved = await mongo_client.upsert_project(project)
    await hub.ensure_runner(saved)
    return ORJSONResponse({"ok": True})


@app.post("/api/v1/admin/vk/start", response_class=ORJSONResponse)
async def vk_start(request: Request, payload: VkAction) -> ORJSONResponse:
    _require_super_admin(request)
    hub: VkHub = request.app.state.vk
    mongo_client = _get_mongo_client(request)
    default_project = _normalize_project(None)
    if not default_project:
        raise HTTPException(status_code=400, detail="Default project is not configured")

    existing = await mongo_client.get_project(default_project)
    data = existing.model_dump() if existing else {"name": default_project}
    token_value = payload.token.strip() if isinstance(payload.token, str) else None
    if token_value:
        data["vk_token"] = token_value
    project = Project(**data)
    saved = await mongo_client.upsert_project(project)
    await hub.start_project(saved)
    return ORJSONResponse({"running": True})


@app.post("/api/v1/admin/vk/stop", response_class=ORJSONResponse)
async def vk_stop(request: Request) -> ORJSONResponse:
    _require_super_admin(request)
    hub: VkHub = request.app.state.vk
    default_project = _normalize_project(None)
    if not default_project:
        raise HTTPException(status_code=400, detail="Default project is not configured")
    await hub.stop_project(default_project)
    return ORJSONResponse({"running": False})


@app.get("/api/v1/admin/projects/{project}/telegram", response_class=ORJSONResponse)
async def admin_project_telegram_status(project: str, request: Request) -> ORJSONResponse:
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        raise HTTPException(status_code=404, detail="project not found")

    hub: TelegramHub = request.app.state.telegram
    payload = _project_telegram_payload(existing, hub)
    return ORJSONResponse(payload)


@app.post("/api/v1/admin/projects/{project}/telegram/config", response_class=ORJSONResponse)
async def admin_project_telegram_config(
    project: str,
    request: Request,
    payload: ProjectTelegramConfig,
) -> ORJSONResponse:
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        existing = Project(name=project_name)

    provided_fields = getattr(payload, "model_fields_set", set())

    if "token" in provided_fields:
        if isinstance(payload.token, str):
            token_value = payload.token.strip() or None
        else:
            token_value = None
    else:
        token_value = existing.telegram_token

    if "auto_start" in provided_fields:
        auto_start_value = (
            bool(payload.auto_start)
            if payload.auto_start is not None
            else None
        )
    else:
        auto_start_value = existing.telegram_auto_start

    project_payload = Project(
        name=project_name,
        title=existing.title,
        domain=existing.domain,
        admin_username=existing.admin_username,
        admin_password_hash=existing.admin_password_hash,
        llm_model=existing.llm_model,
        llm_prompt=existing.llm_prompt,
        llm_emotions_enabled=existing.llm_emotions_enabled if existing.llm_emotions_enabled is not None else True,
        telegram_token=token_value,
        telegram_auto_start=auto_start_value,
        max_token=existing.max_token,
        max_auto_start=existing.max_auto_start,
        vk_token=existing.vk_token,
        vk_auto_start=existing.vk_auto_start,
        widget_url=existing.widget_url,
        debug_enabled=existing.debug_enabled,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: TelegramHub = request.app.state.telegram
    await hub.ensure_runner(saved)
    response = _project_telegram_payload(saved, hub)
    max_hub: MaxHub | None = getattr(request.app.state, "max", None)
    if isinstance(max_hub, MaxHub):
        await max_hub.ensure_runner(saved)
    vk_hub: VkHub | None = getattr(request.app.state, "vk", None)
    if isinstance(vk_hub, VkHub):
        await vk_hub.ensure_runner(saved)
    return ORJSONResponse(response)


@app.post("/api/v1/admin/projects/{project}/telegram/start", response_class=ORJSONResponse)
async def admin_project_telegram_start(
    project: str,
    request: Request,
    payload: ProjectTelegramAction,
) -> ORJSONResponse:
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        raise HTTPException(status_code=404, detail="project not found")

    provided_fields = getattr(payload, "model_fields_set", set())

    if "token" in provided_fields:
        if isinstance(payload.token, str):
            token_value = payload.token.strip() or None
        else:
            token_value = None
    else:
        token_value = (
            existing.telegram_token.strip() or None
            if isinstance(existing.telegram_token, str)
            else None
        )

    if not token_value:
        raise HTTPException(status_code=400, detail="Telegram token is not configured")

    if "auto_start" in provided_fields:
        auto_start_value = (
            bool(payload.auto_start)
            if payload.auto_start is not None
            else None
        )
    else:
        auto_start_value = existing.telegram_auto_start

    project_payload = Project(
        name=existing.name,
        title=existing.title,
        domain=existing.domain,
        admin_username=existing.admin_username,
        admin_password_hash=existing.admin_password_hash,
        llm_model=existing.llm_model,
        llm_prompt=existing.llm_prompt,
        llm_emotions_enabled=existing.llm_emotions_enabled if existing.llm_emotions_enabled is not None else True,
        telegram_token=token_value,
        telegram_auto_start=auto_start_value,
        max_token=existing.max_token,
        max_auto_start=existing.max_auto_start,
        vk_token=existing.vk_token,
        vk_auto_start=existing.vk_auto_start,
        widget_url=existing.widget_url,
        debug_enabled=existing.debug_enabled,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: TelegramHub = request.app.state.telegram
    await hub.start_project(saved, auto_start=auto_start_value if "auto_start" in provided_fields else None)
    response = _project_telegram_payload(saved, hub)
    max_hub: MaxHub | None = getattr(request.app.state, "max", None)
    if isinstance(max_hub, MaxHub):
        await max_hub.ensure_runner(saved)
    vk_hub: VkHub | None = getattr(request.app.state, "vk", None)
    if isinstance(vk_hub, VkHub):
        await vk_hub.ensure_runner(saved)
    return ORJSONResponse(response)


@app.post("/api/v1/admin/projects/{project}/telegram/stop", response_class=ORJSONResponse)
async def admin_project_telegram_stop(
    project: str,
    request: Request,
    payload: ProjectTelegramAction | None = None,
) -> ORJSONResponse:
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        raise HTTPException(status_code=404, detail="project not found")

    provided_fields = getattr(payload, "model_fields_set", set()) if payload else set()
    if payload and "auto_start" in provided_fields:
        auto_start_value = (
            bool(payload.auto_start)
            if payload.auto_start is not None
            else None
        )
    else:
        auto_start_value = existing.telegram_auto_start

    project_payload = Project(
        name=existing.name,
        title=existing.title,
        domain=existing.domain,
        llm_model=existing.llm_model,
        llm_prompt=existing.llm_prompt,
        llm_emotions_enabled=existing.llm_emotions_enabled if existing.llm_emotions_enabled is not None else True,
        telegram_token=existing.telegram_token,
        telegram_auto_start=auto_start_value,
        widget_url=existing.widget_url,
        admin_username=existing.admin_username,
        admin_password_hash=existing.admin_password_hash,
        max_token=existing.max_token,
        max_auto_start=existing.max_auto_start,
        vk_token=existing.vk_token,
        vk_auto_start=existing.vk_auto_start,
        debug_enabled=existing.debug_enabled,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: TelegramHub = request.app.state.telegram
    await hub.stop_project(saved.name, auto_start=auto_start_value if payload and "auto_start" in provided_fields else None)
    response = _project_telegram_payload(saved, hub)
    max_hub: MaxHub | None = getattr(request.app.state, "max", None)
    if isinstance(max_hub, MaxHub):
        await max_hub.ensure_runner(saved)
    vk_hub: VkHub | None = getattr(request.app.state, "vk", None)
    if isinstance(vk_hub, VkHub):
        await vk_hub.ensure_runner(saved)
    return ORJSONResponse(response)


@app.get("/api/v1/admin/projects/{project}/max", response_class=ORJSONResponse)
async def admin_project_max_status(project: str, request: Request) -> ORJSONResponse:
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        raise HTTPException(status_code=404, detail="project not found")

    hub: MaxHub = request.app.state.max
    payload = _project_max_payload(existing, hub)
    return ORJSONResponse(payload)


@app.post("/api/v1/admin/projects/{project}/max/config", response_class=ORJSONResponse)
async def admin_project_max_config(
    project: str,
    request: Request,
    payload: ProjectMaxConfig,
) -> ORJSONResponse:
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        existing = Project(name=project_name)

    provided_fields = getattr(payload, "model_fields_set", set())

    if "token" in provided_fields:
        if isinstance(payload.token, str):
            token_value = payload.token.strip() or None
        else:
            token_value = None
    else:
        token_value = existing.max_token

    if "auto_start" in provided_fields:
        auto_start_value = (
            bool(payload.auto_start)
            if payload.auto_start is not None
            else None
        )
    else:
        auto_start_value = existing.max_auto_start

    project_payload = Project(
        name=project_name,
        title=existing.title,
        domain=existing.domain,
        admin_username=existing.admin_username,
        admin_password_hash=existing.admin_password_hash,
        llm_model=existing.llm_model,
        llm_prompt=existing.llm_prompt,
        llm_emotions_enabled=existing.llm_emotions_enabled if existing.llm_emotions_enabled is not None else True,
        telegram_token=existing.telegram_token,
        telegram_auto_start=existing.telegram_auto_start,
        max_token=token_value,
        max_auto_start=auto_start_value,
        vk_token=existing.vk_token,
        vk_auto_start=existing.vk_auto_start,
        widget_url=existing.widget_url,
        debug_enabled=existing.debug_enabled,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: MaxHub = request.app.state.max
    await hub.ensure_runner(saved)
    response = _project_max_payload(saved, hub)
    telegram_hub: TelegramHub | None = getattr(request.app.state, "telegram", None)
    if isinstance(telegram_hub, TelegramHub):
        await telegram_hub.ensure_runner(saved)
    vk_hub: VkHub | None = getattr(request.app.state, "vk", None)
    if isinstance(vk_hub, VkHub):
        await vk_hub.ensure_runner(saved)
    return ORJSONResponse(response)


@app.post("/api/v1/admin/projects/{project}/max/start", response_class=ORJSONResponse)
async def admin_project_max_start(
    project: str,
    request: Request,
    payload: ProjectMaxAction,
) -> ORJSONResponse:
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        raise HTTPException(status_code=404, detail="project not found")

    provided_fields = getattr(payload, "model_fields_set", set())

    if "token" in provided_fields:
        if isinstance(payload.token, str):
            token_value = payload.token.strip() or None
        else:
            token_value = None
    else:
        token_value = (
            existing.max_token.strip() or None
            if isinstance(existing.max_token, str)
            else None
        )

    if not token_value:
        raise HTTPException(status_code=400, detail="MAX token is not configured")

    if "auto_start" in provided_fields:
        auto_start_value = (
            bool(payload.auto_start)
            if payload.auto_start is not None
            else None
        )
    else:
        auto_start_value = existing.max_auto_start

    project_payload = Project(
        name=existing.name,
        title=existing.title,
        domain=existing.domain,
        admin_username=existing.admin_username,
        admin_password_hash=existing.admin_password_hash,
        llm_model=existing.llm_model,
        llm_prompt=existing.llm_prompt,
        llm_emotions_enabled=existing.llm_emotions_enabled if existing.llm_emotions_enabled is not None else True,
        telegram_token=existing.telegram_token,
        telegram_auto_start=existing.telegram_auto_start,
        max_token=token_value,
        max_auto_start=auto_start_value,
        vk_token=existing.vk_token,
        vk_auto_start=existing.vk_auto_start,
        widget_url=existing.widget_url,
        debug_enabled=existing.debug_enabled,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: MaxHub = request.app.state.max
    await hub.start_project(saved, auto_start=auto_start_value if "auto_start" in provided_fields else None)
    response = _project_max_payload(saved, hub)
    telegram_hub: TelegramHub | None = getattr(request.app.state, "telegram", None)
    if isinstance(telegram_hub, TelegramHub):
        await telegram_hub.ensure_runner(saved)
    vk_hub: VkHub | None = getattr(request.app.state, "vk", None)
    if isinstance(vk_hub, VkHub):
        await vk_hub.ensure_runner(saved)
    return ORJSONResponse(response)


@app.post("/api/v1/admin/projects/{project}/max/stop", response_class=ORJSONResponse)
async def admin_project_max_stop(
    project: str,
    request: Request,
    payload: ProjectMaxAction | None = None,
) -> ORJSONResponse:
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        raise HTTPException(status_code=404, detail="project not found")

    provided_fields = getattr(payload, "model_fields_set", set()) if payload else set()
    if payload and "auto_start" in provided_fields:
        auto_start_value = (
            bool(payload.auto_start)
            if payload.auto_start is not None
            else None
        )
    else:
        auto_start_value = existing.max_auto_start

    project_payload = Project(
        name=existing.name,
        title=existing.title,
        domain=existing.domain,
        llm_model=existing.llm_model,
        llm_prompt=existing.llm_prompt,
        llm_emotions_enabled=existing.llm_emotions_enabled if existing.llm_emotions_enabled is not None else True,
        telegram_token=existing.telegram_token,
        telegram_auto_start=existing.telegram_auto_start,
        max_token=existing.max_token,
        max_auto_start=auto_start_value,
        vk_token=existing.vk_token,
        vk_auto_start=existing.vk_auto_start,
        widget_url=existing.widget_url,
        admin_username=existing.admin_username,
        admin_password_hash=existing.admin_password_hash,
        debug_enabled=existing.debug_enabled,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: MaxHub = request.app.state.max
    await hub.stop_project(saved.name, auto_start=auto_start_value if payload and "auto_start" in provided_fields else None)
    response = _project_max_payload(saved, hub)
    telegram_hub: TelegramHub | None = getattr(request.app.state, "telegram", None)
    if isinstance(telegram_hub, TelegramHub):
        await telegram_hub.ensure_runner(saved)
    vk_hub: VkHub | None = getattr(request.app.state, "vk", None)
    if isinstance(vk_hub, VkHub):
        await vk_hub.ensure_runner(saved)
    return ORJSONResponse(response)


@app.get("/api/v1/admin/projects/{project}/vk", response_class=ORJSONResponse)
async def admin_project_vk_status(project: str, request: Request) -> ORJSONResponse:
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        raise HTTPException(status_code=404, detail="project not found")

    hub: VkHub = request.app.state.vk
    payload = _project_vk_payload(existing, hub)
    return ORJSONResponse(payload)


@app.post("/api/v1/admin/projects/{project}/vk/config", response_class=ORJSONResponse)
async def admin_project_vk_config(
    project: str,
    request: Request,
    payload: ProjectVkConfig,
) -> ORJSONResponse:
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        existing = Project(name=project_name)

    provided_fields = getattr(payload, "model_fields_set", set())

    if "token" in provided_fields:
        if isinstance(payload.token, str):
            token_value = payload.token.strip() or None
        else:
            token_value = None
    else:
        token_value = existing.vk_token

    if "auto_start" in provided_fields:
        auto_start_value = (
            bool(payload.auto_start)
            if payload.auto_start is not None
            else None
        )
    else:
        auto_start_value = existing.vk_auto_start

    project_payload = Project(
        name=project_name,
        title=existing.title,
        domain=existing.domain,
        admin_username=existing.admin_username,
        admin_password_hash=existing.admin_password_hash,
        llm_model=existing.llm_model,
        llm_prompt=existing.llm_prompt,
        llm_emotions_enabled=existing.llm_emotions_enabled if existing.llm_emotions_enabled is not None else True,
        telegram_token=existing.telegram_token,
        telegram_auto_start=existing.telegram_auto_start,
        max_token=existing.max_token,
        max_auto_start=existing.max_auto_start,
        vk_token=token_value,
        vk_auto_start=auto_start_value,
        widget_url=existing.widget_url,
        debug_enabled=existing.debug_enabled,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: VkHub = request.app.state.vk
    await hub.ensure_runner(saved)
    response = _project_vk_payload(saved, hub)
    telegram_hub: TelegramHub | None = getattr(request.app.state, "telegram", None)
    if isinstance(telegram_hub, TelegramHub):
        await telegram_hub.ensure_runner(saved)
    max_hub: MaxHub | None = getattr(request.app.state, "max", None)
    if isinstance(max_hub, MaxHub):
        await max_hub.ensure_runner(saved)
    return ORJSONResponse(response)


@app.post("/api/v1/admin/projects/{project}/vk/start", response_class=ORJSONResponse)
async def admin_project_vk_start(
    project: str,
    request: Request,
    payload: ProjectVkAction,
) -> ORJSONResponse:
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        raise HTTPException(status_code=404, detail="project not found")

    provided_fields = getattr(payload, "model_fields_set", set())

    if "token" in provided_fields:
        if isinstance(payload.token, str):
            token_value = payload.token.strip() or None
        else:
            token_value = None
    else:
        token_value = (
            existing.vk_token.strip() or None
            if isinstance(existing.vk_token, str)
            else None
        )

    if not token_value:
        raise HTTPException(status_code=400, detail="VK token is not configured")

    if "auto_start" in provided_fields:
        auto_start_value = (
            bool(payload.auto_start)
            if payload.auto_start is not None
            else None
        )
    else:
        auto_start_value = existing.vk_auto_start

    project_payload = Project(
        name=existing.name,
        title=existing.title,
        domain=existing.domain,
        admin_username=existing.admin_username,
        admin_password_hash=existing.admin_password_hash,
        llm_model=existing.llm_model,
        llm_prompt=existing.llm_prompt,
        llm_emotions_enabled=existing.llm_emotions_enabled if existing.llm_emotions_enabled is not None else True,
        telegram_token=existing.telegram_token,
        telegram_auto_start=existing.telegram_auto_start,
        max_token=existing.max_token,
        max_auto_start=existing.max_auto_start,
        vk_token=token_value,
        vk_auto_start=auto_start_value,
        widget_url=existing.widget_url,
        debug_enabled=existing.debug_enabled,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: VkHub = request.app.state.vk
    await hub.start_project(saved, auto_start=auto_start_value if "auto_start" in provided_fields else None)
    response = _project_vk_payload(saved, hub)
    telegram_hub: TelegramHub | None = getattr(request.app.state, "telegram", None)
    if isinstance(telegram_hub, TelegramHub):
        await telegram_hub.ensure_runner(saved)
    max_hub: MaxHub | None = getattr(request.app.state, "max", None)
    if isinstance(max_hub, MaxHub):
        await max_hub.ensure_runner(saved)
    return ORJSONResponse(response)


@app.post("/api/v1/admin/projects/{project}/vk/stop", response_class=ORJSONResponse)
async def admin_project_vk_stop(
    project: str,
    request: Request,
    payload: ProjectVkAction | None = None,
) -> ORJSONResponse:
    project_name = _resolve_admin_project(request, project, required=True)
    mongo_client = _get_mongo_client(request)

    existing = await mongo_client.get_project(project_name)
    if not existing:
        raise HTTPException(status_code=404, detail="project not found")

    provided_fields = getattr(payload, "model_fields_set", set()) if payload else set()
    if payload and "auto_start" in provided_fields:
        auto_start_value = (
            bool(payload.auto_start)
            if payload.auto_start is not None
            else None
        )
    else:
        auto_start_value = existing.vk_auto_start

    project_payload = Project(
        name=existing.name,
        title=existing.title,
        domain=existing.domain,
        llm_model=existing.llm_model,
        llm_prompt=existing.llm_prompt,
        llm_emotions_enabled=existing.llm_emotions_enabled if existing.llm_emotions_enabled is not None else True,
        telegram_token=existing.telegram_token,
        telegram_auto_start=existing.telegram_auto_start,
        max_token=existing.max_token,
        max_auto_start=existing.max_auto_start,
        vk_token=existing.vk_token,
        vk_auto_start=auto_start_value,
        widget_url=existing.widget_url,
        admin_username=existing.admin_username,
        admin_password_hash=existing.admin_password_hash,
        debug_enabled=existing.debug_enabled,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: VkHub = request.app.state.vk
    await hub.stop_project(saved.name, auto_start=auto_start_value if payload and "auto_start" in provided_fields else None)
    response = _project_vk_payload(saved, hub)
    telegram_hub: TelegramHub | None = getattr(request.app.state, "telegram", None)
    if isinstance(telegram_hub, TelegramHub):
        await telegram_hub.ensure_runner(saved)
    max_hub: MaxHub | None = getattr(request.app.state, "max", None)
    if isinstance(max_hub, MaxHub):
        await max_hub.ensure_runner(saved)
    return ORJSONResponse(response)


@app.get("/api/v1/admin/stats/requests", response_class=ORJSONResponse)
async def admin_request_stats(
    request: Request,
    project: str | None = None,
    start: str | None = None,
    end: str | None = None,
    channel: str | None = None,
) -> ORJSONResponse:
    project_name = _resolve_admin_project(request, project)
    start_dt = _parse_stats_date(start)
    end_dt = _parse_stats_date(end)
    if end_dt:
        end_dt = end_dt + timedelta(days=1)
    mongo_client = _get_mongo_client(request)
    stats = await mongo_client.aggregate_request_stats(
        project=project_name,
        start=start_dt,
        end=end_dt,
        channel=channel,
    )
    return ORJSONResponse({"stats": stats})


@app.get("/api/v1/admin/stats/requests/export")
async def admin_request_stats_export(
    request: Request,
    project: str | None = None,
    start: str | None = None,
    end: str | None = None,
    channel: str | None = None,
) -> StreamingResponse:
    project_name = _resolve_admin_project(request, project)
    start_dt = _parse_stats_date(start)
    end_dt = _parse_stats_date(end)
    if end_dt:
        end_dt = end_dt + timedelta(days=1)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "timestamp",
        "date",
        "project",
        "channel",
        "question",
        "response_chars",
        "attachments",
        "prompt_chars",
        "session_id",
        "user_id",
        "error",
    ])

    mongo_client = _get_mongo_client(request)
    async for item in mongo_client.iter_request_stats(
        project=project_name,
        start=start_dt,
        end=end_dt,
        channel=channel,
    ):
        ts = item.get("ts")
        if isinstance(ts, datetime):
            ts_str = ts.astimezone(timezone.utc).isoformat()
        else:
            ts_str = str(ts)
        day = item.get("date")
        if isinstance(day, datetime):
            day_str = day.date().isoformat()
        else:
            day_str = str(day)
        writer.writerow(
            [
                ts_str,
                day_str,
                item.get("project"),
                item.get("channel"),
                item.get("question"),
                item.get("response_chars"),
                item.get("attachments"),
                item.get("prompt_chars"),
                item.get("session_id"),
                item.get("user_id"),
                item.get("error"),
            ]
        )

    output.seek(0)
    filename = "request_stats.csv"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
    }
    return StreamingResponse(
        iter([output.getvalue().encode("utf-8")]),
        media_type="text/csv",
        headers=headers,
    )


def _resolve_session_identifiers(request: Request, project: str | None, session_id: str | None) -> tuple[str | None, str]:
    project_name = _normalize_project(project)
    base = session_id or request.headers.get("X-Session-Id") or request.headers.get("X-Client-Session")
    if not base:
        base = request.cookies.get("chat_session")
    if not base:
        base = uuid4().hex
    base = base.strip().lower()
    if project_name:
        return project_name, f"{project_name}::{base}"
    return project_name, base


@app.get("/api/v1/admin/projects", response_class=ORJSONResponse)
async def admin_projects(request: Request) -> ORJSONResponse:
    """Return configured projects."""

    identity = _require_admin(request)
    mongo_client = _get_mongo_client(request)
    projects = await mongo_client.list_projects()
    if not identity.is_super:
        allowed = {proj.strip().lower() for proj in identity.projects if proj}
        projects = [project for project in projects if project.name in allowed]
    serialized = [_project_response(project) for project in projects]
    return ORJSONResponse({"projects": serialized})


@app.get("/api/v1/admin/projects/storage", response_class=ORJSONResponse)
async def admin_projects_storage(request: Request) -> ORJSONResponse:
    """Return aggregated storage usage per project (Mongo/GridFS/Redis)."""

    identity = _require_admin(request)
    mongo_cfg = MongoSettings()
    documents_collection = getattr(request.state, "documents_collection", mongo_cfg.documents)
    contexts_collection = getattr(request.state, "contexts_collection", mongo_cfg.contexts)

    mongo_client = _get_mongo_client(request)
    storage = await mongo_client.aggregate_project_storage(documents_collection, contexts_collection)
    redis_usage = await _redis_project_usage()

    if not identity.is_super:
        allowed = {proj.strip().lower() for proj in identity.projects if proj}
        storage = {key: value for key, value in storage.items() if key in allowed}
        redis_usage = {key: value for key, value in redis_usage.items() if key in allowed}
    else:
        allowed = None

    combined_keys = set(storage.keys()) | set(redis_usage.keys())
    if allowed is not None:
        combined_keys = {key for key in combined_keys if key in allowed}
    combined: dict[str, dict[str, float | int]] = {}
    for key in combined_keys:
        doc_stats = storage.get(key, {})
        redis_stats = redis_usage.get(key, {})
        documents_bytes = int(doc_stats.get("documents_bytes", 0) or 0)
        binary_bytes = int(doc_stats.get("binary_bytes", 0) or 0)
        text_bytes = max(documents_bytes - binary_bytes, 0)
        combined[key] = {
            "documents_bytes": documents_bytes,
            "binary_bytes": binary_bytes,
            "text_bytes": text_bytes,
            "document_count": int(doc_stats.get("document_count", 0)),
            "context_bytes": int(doc_stats.get("context_bytes", 0) or 0),
            "context_count": int(doc_stats.get("context_count", 0)),
            "redis_bytes": float(redis_stats.get("redis_bytes", 0)),
            "redis_keys": int(redis_stats.get("redis_keys", 0)),
        }

    return ORJSONResponse({"projects": combined})


@app.post("/api/v1/admin/projects", response_class=ORJSONResponse, status_code=201)
async def admin_create_project(request: Request, payload: ProjectCreate) -> ORJSONResponse:
    """Create or update a project (domain)."""

    identity = _require_admin(request)
    mongo_client = _get_mongo_client(request)

    name = _normalize_project(payload.name)
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    if not identity.is_super:
        allowed = {proj.strip().lower() for proj in identity.projects if proj}
        if name not in allowed:
            raise HTTPException(status_code=403, detail="Access to project is forbidden")

    existing = await mongo_client.get_project(name)
    provided_fields = getattr(payload, "model_fields_set", set())
    if isinstance(payload.title, str):
        title_value = payload.title.strip() or None
    else:
        title_value = existing.title if existing else None

    if isinstance(payload.domain, str):
        domain_value = payload.domain.strip() or None
    else:
        domain_value = existing.domain if existing else None
    model_value = payload.llm_model.strip() if isinstance(payload.llm_model, str) and payload.llm_model.strip() else (existing.llm_model if existing and existing.llm_model else None)
    prompt_value = payload.llm_prompt.strip() if isinstance(payload.llm_prompt, str) and payload.llm_prompt.strip() else (existing.llm_prompt if existing and existing.llm_prompt else None)

    if "llm_emotions_enabled" in provided_fields:
        emotions_value = (
            bool(payload.llm_emotions_enabled)
            if payload.llm_emotions_enabled is not None
            else True
        )
    else:
        if existing and existing.llm_emotions_enabled is not None:
            emotions_value = existing.llm_emotions_enabled
        else:
            emotions_value = True

    if "llm_voice_enabled" in provided_fields:
        voice_enabled_value = (
            bool(payload.llm_voice_enabled)
            if payload.llm_voice_enabled is not None
            else True
        )
    else:
        if existing and existing.llm_voice_enabled is not None:
            voice_enabled_value = bool(existing.llm_voice_enabled)
        else:
            voice_enabled_value = True

    if "llm_voice_model" in provided_fields:
        if isinstance(payload.llm_voice_model, str):
            voice_model_value = payload.llm_voice_model.strip() or None
        else:
            voice_model_value = None
    else:
        voice_model_value = existing.llm_voice_model if existing and existing.llm_voice_model else None

    if not voice_enabled_value:
        voice_model_value = None

    if "llm_sources_enabled" in provided_fields:
        sources_enabled_value = (
            bool(payload.llm_sources_enabled)
            if payload.llm_sources_enabled is not None
            else False
        )
    else:
        if existing and existing.llm_sources_enabled is not None:
            sources_enabled_value = bool(existing.llm_sources_enabled)
        else:
            sources_enabled_value = False

    if "debug_enabled" in provided_fields:
        debug_value = bool(payload.debug_enabled) if payload.debug_enabled is not None else False
    else:
        if existing and existing.debug_enabled is not None:
            debug_value = bool(existing.debug_enabled)
        else:
            debug_value = False

    if "debug_info_enabled" in provided_fields:
        debug_info_value = (
            bool(payload.debug_info_enabled)
            if payload.debug_info_enabled is not None
            else False
        )
    else:
        if existing and existing.debug_info_enabled is not None:
            debug_info_value = bool(existing.debug_info_enabled)
        else:
            debug_info_value = True

    if "knowledge_image_caption_enabled" in provided_fields:
        captions_value = (
            bool(payload.knowledge_image_caption_enabled)
            if payload.knowledge_image_caption_enabled is not None
            else True
        )
    else:
        if existing and existing.knowledge_image_caption_enabled is not None:
            captions_value = bool(existing.knowledge_image_caption_enabled)
        else:
            captions_value = True

    if "bitrix_enabled" in provided_fields:
        bitrix_enabled_value = (
            bool(payload.bitrix_enabled)
            if payload.bitrix_enabled is not None
            else False
        )
    else:
        if existing and existing.bitrix_enabled is not None:
            bitrix_enabled_value = bool(existing.bitrix_enabled)
        else:
            bitrix_enabled_value = False

    if "bitrix_webhook_url" in provided_fields:
        if isinstance(payload.bitrix_webhook_url, str):
            bitrix_webhook_value = payload.bitrix_webhook_url.strip() or None
        else:
            bitrix_webhook_value = None
    else:
        bitrix_webhook_value = existing.bitrix_webhook_url if existing else None

    if "telegram_token" in provided_fields:
        if isinstance(payload.telegram_token, str):
            token_value = payload.telegram_token.strip() or None
        else:
            token_value = None
    else:
        token_value = existing.telegram_token if existing else None

    if "telegram_auto_start" in provided_fields:
        auto_start_value = (
            bool(payload.telegram_auto_start)
            if payload.telegram_auto_start is not None
            else None
        )
    else:
        auto_start_value = existing.telegram_auto_start if existing else None

    if "max_token" in provided_fields:
        if isinstance(payload.max_token, str):
            max_token_value = payload.max_token.strip() or None
        else:
            max_token_value = None
    else:
        max_token_value = existing.max_token if existing else None

    if "max_auto_start" in provided_fields:
        max_auto_start_value = (
            bool(payload.max_auto_start)
            if payload.max_auto_start is not None
            else None
        )
    else:
        max_auto_start_value = existing.max_auto_start if existing else None

    if "vk_token" in provided_fields:
        if isinstance(payload.vk_token, str):
            vk_token_value = payload.vk_token.strip() or None
        else:
            vk_token_value = None
    else:
        vk_token_value = existing.vk_token if existing else None

    if "vk_auto_start" in provided_fields:
        vk_auto_start_value = (
            bool(payload.vk_auto_start)
            if payload.vk_auto_start is not None
            else None
        )
    else:
        vk_auto_start_value = existing.vk_auto_start if existing else None

    if "widget_url" in provided_fields:
        if isinstance(payload.widget_url, str):
            widget_url_value = payload.widget_url.strip() or None
        else:
            widget_url_value = None
    else:
        widget_url_value = existing.widget_url if existing else None

    admin_username_value = existing.admin_username if existing else None
    if "admin_username" in provided_fields:
        if isinstance(payload.admin_username, str):
            candidate_username = payload.admin_username.strip().lower() or None
        else:
            candidate_username = None
        if identity.is_super:
            admin_username_value = candidate_username
        else:
            current_username = (existing.admin_username if existing and existing.admin_username else identity.username).strip().lower()
            if candidate_username is None or candidate_username != current_username:
                raise HTTPException(status_code=403, detail="Project admin cannot change username")
            admin_username_value = current_username

    admin_password_hash_value = existing.admin_password_hash if existing else None
    if "admin_password" in provided_fields:
        candidate_password = payload.admin_password
        if candidate_password is None or not candidate_password.strip():
            if identity.is_super:
                admin_password_hash_value = None
            else:
                raise HTTPException(status_code=400, detail="Password cannot be empty")
        else:
            if not (admin_username_value or (existing and existing.admin_username)):
                raise HTTPException(status_code=400, detail="Set admin username before configuring password")
            admin_password_hash_value = hashlib.sha256(candidate_password.encode()).hexdigest()

    if admin_username_value is None:
        admin_password_hash_value = None

    if "mail_enabled" in provided_fields:
        mail_enabled_value = bool(payload.mail_enabled) if payload.mail_enabled is not None else False
    else:
        if existing and existing.mail_enabled is not None:
            mail_enabled_value = bool(existing.mail_enabled)
        else:
            mail_enabled_value = False

    def _resolve_mail_text(field_name: str, existing_value: str | None) -> str | None:
        if field_name in provided_fields:
            raw = getattr(payload, field_name, None)
            if isinstance(raw, str):
                return raw.strip() or None
            return None
        return existing_value

    mail_imap_host_value = _resolve_mail_text('mail_imap_host', existing.mail_imap_host if existing else None)
    mail_smtp_host_value = _resolve_mail_text('mail_smtp_host', existing.mail_smtp_host if existing else None)
    mail_username_value = _resolve_mail_text('mail_username', existing.mail_username if existing else None)
    mail_password_value = existing.mail_password if existing else None
    if 'mail_password' in provided_fields:
        raw_password = getattr(payload, 'mail_password', None)
        if isinstance(raw_password, str):
            mail_password_value = raw_password.strip() or None
        else:
            mail_password_value = None
    mail_from_value = _resolve_mail_text('mail_from', existing.mail_from if existing else None)
    mail_signature_value = _resolve_mail_text('mail_signature', existing.mail_signature if existing else None)

    if "mail_imap_port" in provided_fields:
        port_candidate = payload.mail_imap_port
        mail_imap_port_value = int(port_candidate) if isinstance(port_candidate, int) else None
    else:
        mail_imap_port_value = int(existing.mail_imap_port) if existing and isinstance(existing.mail_imap_port, int) else None

    if "mail_smtp_port" in provided_fields:
        smtp_port_candidate = payload.mail_smtp_port
        mail_smtp_port_value = int(smtp_port_candidate) if isinstance(smtp_port_candidate, int) else None
    else:
        mail_smtp_port_value = int(existing.mail_smtp_port) if existing and isinstance(existing.mail_smtp_port, int) else None

    if "mail_imap_ssl" in provided_fields:
        mail_imap_ssl_value = bool(payload.mail_imap_ssl) if payload.mail_imap_ssl is not None else True
    else:
        if existing and existing.mail_imap_ssl is not None:
            mail_imap_ssl_value = bool(existing.mail_imap_ssl)
        else:
            mail_imap_ssl_value = True

    if "mail_smtp_tls" in provided_fields:
        mail_smtp_tls_value = bool(payload.mail_smtp_tls) if payload.mail_smtp_tls is not None else True
    else:
        if existing and existing.mail_smtp_tls is not None:
            mail_smtp_tls_value = bool(existing.mail_smtp_tls)
        else:
            mail_smtp_tls_value = True

    project = Project(
        name=name,
        title=title_value,
        domain=domain_value,
        admin_username=admin_username_value,
        admin_password_hash=admin_password_hash_value,
        llm_model=model_value,
        llm_prompt=prompt_value,
        llm_emotions_enabled=emotions_value,
        llm_voice_enabled=voice_enabled_value,
        llm_voice_model=voice_model_value,
        llm_sources_enabled=sources_enabled_value,
        debug_enabled=debug_value,
        debug_info_enabled=debug_info_value,
        knowledge_image_caption_enabled=captions_value,
        bitrix_enabled=bitrix_enabled_value,
        bitrix_webhook_url=bitrix_webhook_value,
        telegram_token=token_value,
        telegram_auto_start=auto_start_value,
        max_token=max_token_value,
        max_auto_start=max_auto_start_value,
        vk_token=vk_token_value,
        vk_auto_start=vk_auto_start_value,
        widget_url=widget_url_value,
        mail_enabled=mail_enabled_value,
        mail_imap_host=mail_imap_host_value,
        mail_imap_port=mail_imap_port_value,
        mail_imap_ssl=mail_imap_ssl_value,
        mail_smtp_host=mail_smtp_host_value,
        mail_smtp_port=mail_smtp_port_value,
        mail_smtp_tls=mail_smtp_tls_value,
        mail_username=mail_username_value,
        mail_password=mail_password_value,
        mail_from=mail_from_value,
        mail_signature=mail_signature_value,
    )
    project = await mongo_client.upsert_project(project)
    hub: TelegramHub | None = getattr(request.app.state, "telegram", None)
    if isinstance(hub, TelegramHub):
        await hub.ensure_runner(project)
    max_hub: MaxHub | None = getattr(request.app.state, "max", None)
    if isinstance(max_hub, MaxHub):
        await max_hub.ensure_runner(project)
    vk_hub: VkHub | None = getattr(request.app.state, "vk", None)
    if isinstance(vk_hub, VkHub):
        await vk_hub.ensure_runner(project)
    return ORJSONResponse(_project_response(project))


@app.delete("/api/v1/admin/projects/{domain}", response_class=ORJSONResponse)
async def admin_delete_project(request: Request, domain: str) -> ORJSONResponse:
    identity = _require_admin(request)
    domain_value = _normalize_project(domain)
    if not domain_value:
        raise HTTPException(status_code=400, detail="name is required")
    if not identity.is_super:
        allowed = {proj.strip().lower() for proj in identity.projects if proj}
        if domain_value not in allowed:
            raise HTTPException(status_code=403, detail="Access to project is forbidden")
    mongo_client = _get_mongo_client(request)
    mongo_cfg = MongoSettings()
    documents_collection = getattr(request.state, "documents_collection", mongo_cfg.documents)
    contexts_collection = getattr(request.state, "contexts_collection", mongo_cfg.contexts)
    summary = await mongo_client.delete_project(
        domain_value,
        documents_collection=documents_collection,
        contexts_collection=contexts_collection,
        stats_collection=mongo_client.stats_collection,
    )
    file_ids = summary.pop("file_ids", [])
    await _purge_vector_entries(file_ids)
    hub: TelegramHub | None = getattr(request.app.state, "telegram", None)
    if isinstance(hub, TelegramHub):
        await hub.stop_project(domain_value, forget_sessions=True)
    max_hub: MaxHub | None = getattr(request.app.state, "max", None)
    if isinstance(max_hub, MaxHub):
        await max_hub.stop_project(domain_value, forget_sessions=True)
    vk_hub: VkHub | None = getattr(request.app.state, "vk", None)
    if isinstance(vk_hub, VkHub):
        await vk_hub.stop_project(domain_value, forget_sessions=True)
    return ORJSONResponse({"status": "deleted", "project": domain_value, "removed": summary})


def _normalize_source_url(raw: str) -> str:
    candidate = (raw or "").strip()
    if not candidate:
        raise ValueError("URL is required")
    if not urlparse.urlsplit(candidate).scheme:
        candidate = f"https://{candidate}"
    parsed = urlparse.urlsplit(candidate)
    if not parsed.netloc:
        raise ValueError("Invalid URL")
    path = parsed.path or "/"
    return urlparse.urlunsplit((parsed.scheme or "https", parsed.netloc, path, parsed.query, ""))


def _extract_page_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template", "svg"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    combined = " ".join(lines)
    if len(combined) > PROMPT_SAMPLE_CHAR_LIMIT:
        return combined[:PROMPT_SAMPLE_CHAR_LIMIT]
    return combined


def _describe_prompt_fetch_error(status_code: int) -> str:
    if status_code == 401:
        return "URL требует авторизацию"
    if status_code == 403:
        return "Доступ к URL запрещён"
    if status_code == 404:
        return "Страница не найдена по указанному URL"
    if status_code == 405:
        return "Сайт запретил загрузку страницы (method not allowed)"
    if status_code >= 500:
        return "Сайт вернул внутреннюю ошибку"
    return "Не удалось загрузить страницу"


async def _download_page_text(url: str) -> str:
    parsed = urlparse.urlsplit(url)
    path = parsed.path or "/"
    normalized = urlparse.urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, ""))

    candidates: list[str] = []
    seen: set[str] = set()

    def add_candidate(candidate: str) -> None:
        if candidate and candidate not in seen:
            candidates.append(candidate)
            seen.add(candidate)

    add_candidate(normalized)

    base_candidate = urlparse.urlunsplit((parsed.scheme, parsed.netloc, "/", "", ""))
    if normalized != base_candidate:
        add_candidate(base_candidate)

    if parsed.scheme.lower() == "https":
        http_path_candidate = urlparse.urlunsplit(("http", parsed.netloc, path, parsed.query, ""))
        add_candidate(http_path_candidate)
        http_base_candidate = urlparse.urlunsplit(("http", parsed.netloc, "/", "", ""))
        add_candidate(http_base_candidate)

    response: httpx.Response | None = None
    last_status_error: httpx.HTTPStatusError | None = None
    last_request_error: httpx.RequestError | None = None

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=PROMPT_FETCH_HEADERS) as client:
        for candidate in candidates:
            try:
                fetched = await client.get(candidate)
                fetched.raise_for_status()
            except httpx.HTTPStatusError as exc:
                last_status_error = exc
                logger.warning(
                    "prompt_page_fetch_http_error",
                    original_url=normalized,
                    attempted_url=candidate,
                    status=exc.response.status_code,
                )
                continue
            except httpx.RequestError as exc:
                last_request_error = exc
                logger.warning(
                    "prompt_page_fetch_request_error",
                    original_url=normalized,
                    attempted_url=candidate,
                    error=str(exc),
                )
                continue
            else:
                if candidate != normalized:
                    logger.info(
                        "prompt_page_fetch_fallback_used",
                        original_url=normalized,
                        resolved_url=candidate,
                    )
                response = fetched
                break

    if response is None:
        if last_status_error is not None:
            status_code = last_status_error.response.status_code
            detail = _describe_prompt_fetch_error(status_code)
            raise HTTPException(status_code=status_code, detail=detail) from last_status_error
        if last_request_error is not None:
            raise HTTPException(status_code=502, detail="Не удалось подключиться к сайту") from last_request_error
        raise HTTPException(status_code=400, detail="Не удалось загрузить страницу")

    content_type = (response.headers.get("content-type") or "").lower()
    if "text/html" not in content_type:
        raise HTTPException(status_code=400, detail="URL не содержит HTML-страницу")

    text = _extract_page_text(response.text or "")
    if not text:
        raise HTTPException(status_code=400, detail="Не удалось извлечь текст со страницы")
    return text


def _build_prompt_from_role(role: str, url: str, page_text: str) -> tuple[str, str, str]:
    role_key = (role or DEFAULT_PROMPT_ROLE).strip().lower() or DEFAULT_PROMPT_ROLE
    role_meta = PROMPT_ROLE_TEMPLATES.get(role_key, PROMPT_ROLE_TEMPLATES[DEFAULT_PROMPT_ROLE])
    instruction = role_meta["instruction"]
    label = role_meta["label"]
    snippet = page_text.strip()
    snippet_block = f'"""{snippet}"""' if snippet else ""

    body = (
        f"{instruction}\n\n"
        "Ты создаёшь системный промт для ассистента, который отвечает пользователям от имени компании. "
        "Сформулируй чёткие указания о стиле общения, компетенциях, ограничениях и типичных задачах. "
        "Если в тексте есть сведения о продуктах, услугах, ценностях или контактах, включи их в промт.\n\n"
        f"URL страницы: {url}\n"
        f"Роль ассистента: {label}.\n\n"
        "Контент главной страницы (усечён до ключевых фрагментов):\n"
        f"{snippet_block}\n\n"
        "Верни только готовый системный промт на русском языке без пояснений и служебных префиксов."
    )
    return body, role_key, label


def _summarize_snippets(text: str, *, limit: int = 5) -> list[str]:
    chunks = re.split(r"(?<=[.!?…])\s+", text)
    selections: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        cleaned = chunk.strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        if len(cleaned) < 25:
            continue
        selections.append(cleaned)
        if len(selections) >= limit:
            break
    if not selections and text:
        preview = re.sub(r"\s+", " ", text).strip()
        if preview:
            selections.append(preview[:240])
    return selections


def _build_prompt_fallback(role_label: str, url: str, page_text: str) -> str | None:
    snippet_list = _summarize_snippets(page_text, limit=6)
    if not snippet_list:
        return None
    bullets = "\n".join(f"- {item}" for item in snippet_list)
    guidance = (
        f"Ты выступаешь в роли {role_label} компании и общаешься на русском языке. "
        "Держи тёплый, профессиональный тон и помогай пользователю находить ответы.\n"
        f"Используй сведения с сайта {url}. Если в запросе нет данных из списка, объясни, что информации нет, и предложи способы уточнить вопрос.\n"
        "Основные факты о компании:\n"
        f"{bullets}\n\n"
        "Отвечай кратко и по делу, по возможности добавляй конкретные детали и призывы к действию, оставайся внимательным к контексту пользователя."
    )
    return guidance[: PROMPT_RESPONSE_CHAR_LIMIT]


async def _purge_vector_entries(file_ids: list[str]) -> None:
    if not file_ids:
        return
    try:
        client = QdrantClient(url=base_settings.qdrant_url)
    except Exception as exc:  # noqa: BLE001
        logger.debug("vector_cleanup_unavailable", error=str(exc))
        return

    try:
        client.delete(
            collection_name=getattr(base_settings, "qdrant_collection", "documents"),
            points_selector=qdrant_models.PointIdsList(points=[str(fid) for fid in file_ids]),
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("vector_entry_delete_failed", error=str(exc))
    finally:
        client.close()


@app.post("/api/v1/admin/projects/prompt", response_class=ORJSONResponse)
async def admin_generate_project_prompt(
    request: Request,
    payload: PromptGenerationRequest,
) -> ORJSONResponse:
    _require_super_admin(request)
    try:
        normalized_url = _normalize_source_url(payload.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    page_text = await _download_page_text(normalized_url)
    prompt_body, role_key, role_label = _build_prompt_from_role(payload.role or DEFAULT_PROMPT_ROLE, normalized_url, page_text)

    chunks: list[str] = []
    try:
        async for token in llm_client.generate(prompt_body):
            chunks.append(token)
            if len("".join(chunks)) >= PROMPT_RESPONSE_CHAR_LIMIT:
                break
    except Exception as exc:  # noqa: BLE001
        logger.error("prompt_generate_failed", url=normalized_url, error=str(exc))
        fallback_prompt = _build_prompt_fallback(role_label, normalized_url, page_text)
        if fallback_prompt:
            logger.warning(
                "prompt_generate_fallback_used",
                url=normalized_url,
                role=role_key,
                error=str(exc),
            )
            return ORJSONResponse(
                {
                    "prompt": fallback_prompt,
                    "role": role_key,
                    "role_label": role_label,
                    "url": normalized_url,
                    "fallback": True,
                }
            )
        raise HTTPException(status_code=502, detail="Не удалось получить ответ модели") from exc

    generated = "".join(chunks).strip()
    if not generated:
        fallback_prompt = _build_prompt_fallback(role_label, normalized_url, page_text)
        if fallback_prompt:
            logger.warning(
                "prompt_generate_empty_result_fallback",
                url=normalized_url,
                role=role_key,
            )
            return ORJSONResponse(
                {
                    "prompt": fallback_prompt,
                    "role": role_key,
                    "role_label": role_label,
                    "url": normalized_url,
                    "fallback": True,
                }
            )
        raise HTTPException(status_code=502, detail="Модель вернула пустой ответ")

    return ORJSONResponse(
        {
            "prompt": generated,
            "role": role_key,
            "role_label": role_label,
            "url": normalized_url,
        }
    )


@app.get("/api/v1/admin/projects/{domain}/test", response_class=ORJSONResponse)
async def admin_test_project(domain: str, request: Request) -> ORJSONResponse:
    domain_value = _resolve_admin_project(request, domain, required=True)

    mongo_ok, mongo_err = _mongo_check()
    redis_ok, redis_err = _redis_check()
    qdrant_ok, qdrant_err = _qdrant_check()

    mongo_client = _get_mongo_client(request)
    project = await mongo_client.get_project(domain_value)

    return ORJSONResponse(
        {
            "name": domain_value,
            "mongo": {"ok": mongo_ok, "error": mongo_err},
            "redis": {"ok": redis_ok, "error": redis_err},
            "qdrant": {"ok": qdrant_ok, "error": qdrant_err},
        }
    )


@app.get("/api/v1/admin/knowledge/documents/{file_id}")
async def admin_download_document(request: Request, file_id: str) -> Response:
    """Return the raw contents of a document from GridFS."""

    identity = _require_admin(request)
    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)

    def fetch_file() -> tuple[dict[str, Any], bytes]:
        with SyncMongoClient(base_settings.mongo_uri, serverSelectionTimeoutMS=2000) as sync_client:
            db = sync_client[mongo_cfg.database]
            coll = db[collection]
            doc = coll.find_one({"fileId": file_id}, {"_id": False})
            if not doc:
                raise HTTPException(status_code=404, detail="Document metadata not found")
            fs = GridFS(db)
            try:
                data = fs.get(ObjectId(file_id)).read()
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(status_code=404, detail="Failed to read document") from exc
            return doc, data

    doc_meta, payload = await run_in_threadpool(fetch_file)
    if not identity.is_super:
        allowed = {proj.strip().lower() for proj in identity.projects if proj}
        doc_project_value = doc_meta.get("project")
        if isinstance(doc_project_value, str) and doc_project_value.strip():
            normalized_doc_project = doc_project_value.strip().lower()
        else:
            domain_value = doc_meta.get("domain")
            normalized_doc_project = domain_value.strip().lower() if isinstance(domain_value, str) and domain_value.strip() else None
        if not normalized_doc_project or normalized_doc_project not in allowed:
            raise HTTPException(status_code=403, detail="Access to document is forbidden")
    filename = doc_meta.get("name") or f"{file_id}.bin"
    headers = {"Content-Disposition": _build_content_disposition(filename)}
    media_type = doc_meta.get("content_type") or "application/octet-stream"
    return Response(content=payload, media_type=media_type, headers=headers)


@app.get("/api/v1/admin/knowledge/documents/{file_id}/metadata", response_class=ORJSONResponse)
async def admin_get_document_metadata(request: Request, file_id: str) -> ORJSONResponse:
    """Return document metadata for editing."""

    identity = _require_admin(request)
    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)

    def fetch_metadata() -> dict[str, Any]:
        with SyncMongoClient(base_settings.mongo_uri, serverSelectionTimeoutMS=2000) as sync_client:
            db = sync_client[mongo_cfg.database]
            coll = db[collection]
            doc = coll.find_one({"fileId": file_id}, {"_id": False})
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")
            return doc

    doc_meta = await run_in_threadpool(fetch_metadata)

    # Check permissions
    if not identity.is_super:
        allowed = {proj.strip().lower() for proj in identity.projects if proj}
        doc_project_value = doc_meta.get("project")
        if isinstance(doc_project_value, str) and doc_project_value.strip():
            normalized_doc_project = doc_project_value.strip().lower()
        else:
            domain_value = doc_meta.get("domain")
            normalized_doc_project = domain_value.strip().lower() if isinstance(domain_value, str) and domain_value.strip() else None
        if not normalized_doc_project or normalized_doc_project not in allowed:
            raise HTTPException(status_code=403, detail="Access forbidden")

    return ORJSONResponse({
        "fileId": str(doc_meta.get("fileId", file_id)),
        "name": doc_meta.get("name", ""),
        "url": doc_meta.get("url", ""),
        "description": doc_meta.get("description", ""),
        "content": doc_meta.get("content", ""),
        "project": doc_meta.get("project", ""),
        "domain": doc_meta.get("domain", ""),
    })


@app.put("/api/v1/admin/knowledge/documents/{file_id}", response_class=ORJSONResponse)
async def admin_update_document(request: Request, file_id: str) -> ORJSONResponse:
    """Update document metadata."""

    identity = _require_admin(request)
    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    def update_metadata() -> dict[str, Any]:
        with SyncMongoClient(base_settings.mongo_uri, serverSelectionTimeoutMS=2000) as sync_client:
            db = sync_client[mongo_cfg.database]
            coll = db[collection]

            # Check if document exists
            doc = coll.find_one({"fileId": file_id}, {"_id": False})
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")

            # Check permissions
            if not identity.is_super:
                allowed = {proj.strip().lower() for proj in identity.projects if proj}
                doc_project_value = doc.get("project")
                if isinstance(doc_project_value, str) and doc_project_value.strip():
                    normalized_doc_project = doc_project_value.strip().lower()
                else:
                    domain_value = doc.get("domain")
                    normalized_doc_project = domain_value.strip().lower() if isinstance(domain_value, str) and domain_value.strip() else None
                if not normalized_doc_project or normalized_doc_project not in allowed:
                    raise HTTPException(status_code=403, detail="Access forbidden")

            # Prepare update fields
            update_fields = {}
            if "name" in body:
                update_fields["name"] = str(body["name"]).strip()
            if "url" in body:
                update_fields["url"] = str(body["url"]).strip()
            if "description" in body:
                update_fields["description"] = str(body["description"]).strip()
            if "content" in body:
                update_fields["content"] = str(body["content"]).strip()

            if not update_fields:
                raise HTTPException(status_code=400, detail="No fields to update")

            # Update document
            result = coll.update_one(
                {"fileId": file_id},
                {"$set": update_fields}
            )

            if result.matched_count == 0:
                raise HTTPException(status_code=404, detail="Document not found")

            # Return updated document
            updated_doc = coll.find_one({"fileId": file_id}, {"_id": False})
            return updated_doc

    updated_doc = await run_in_threadpool(update_metadata)

    return ORJSONResponse({
        "success": True,
        "fileId": str(updated_doc.get("fileId", file_id)),
        "name": updated_doc.get("name", ""),
        "url": updated_doc.get("url", ""),
        "description": updated_doc.get("description", ""),
        "content": updated_doc.get("content", ""),
    })


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redirect the root URL to the web chat widget.

    Opening http://localhost:8000 now lands at ``/widget/`` instead of 404.
    """
    return RedirectResponse(url="/widget/")


def _compute_process_cpu_fallback() -> float | None:
    """Return process CPU percent without relying on psutil."""

    global _PROCESS_CPU_SAMPLE

    try:
        import resource
        import time
    except Exception:  # pragma: no cover - platform limitations
        return None

    usage = resource.getrusage(resource.RUSAGE_SELF)
    total = float(usage.ru_utime + usage.ru_stime)
    now = time.time()

    previous = _PROCESS_CPU_SAMPLE
    _PROCESS_CPU_SAMPLE = {"timestamp": now, "total": total}

    if not previous:
        return None

    elapsed = now - previous.get("timestamp", 0.0)
    if elapsed <= 0:
        return None

    cpu_delta = total - previous.get("total", 0.0)
    if cpu_delta < 0:
        return None

    return (cpu_delta / elapsed) * 100.0


def _compute_system_cpu_fallback() -> float | None:
    """Approximate system-wide CPU percent via load average."""

    try:
        import os

        load_avg = os.getloadavg()[0]
        cpu_count = max(1, os.cpu_count() or 1)
        percent = (load_avg / cpu_count) * 100.0
        return max(0.0, min(percent, 100.0))
    except Exception:  # pragma: no cover - fallback best effort
        return None


def _compute_system_memory_fallback() -> tuple[int | None, int | None, float | None]:
    """Return total/used memory using sysconf or /proc reads."""

    try:
        import os

        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        phys_pages = int(os.sysconf("SC_PHYS_PAGES"))
        avail_pages = int(os.sysconf("SC_AVPHYS_PAGES"))
        total_bytes = page_size * phys_pages if phys_pages > 0 else None
        used_bytes = None
        percent = None
        if total_bytes is not None and avail_pages >= 0:
            available_bytes = page_size * avail_pages
            used_bytes = total_bytes - available_bytes
            if total_bytes:
                percent = (used_bytes / total_bytes) * 100.0
        return total_bytes, used_bytes, percent
    except Exception:
        pass

    try:
        meminfo: dict[str, int] = {}
        with open("/proc/meminfo", "r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                if ":" not in line:
                    continue
                key, raw_value = line.split(":", 1)
                tokens = raw_value.strip().split()
                number = None
                for token in tokens:
                    try:
                        number = float(token)
                        break
                    except ValueError:
                        continue
                if number is None:
                    continue
                scale = 1
                for token in tokens[1:]:
                    upper = token.upper()
                    if upper.startswith("KB"):
                        scale = 1024
                        break
                    if upper.startswith("MB"):
                        scale = 1024 * 1024
                        break
                    if upper.startswith("GB"):
                        scale = 1024 * 1024 * 1024
                        break
                meminfo[key.strip()] = int(number * scale)
        total = meminfo.get("MemTotal")
        available = meminfo.get("MemAvailable")
        if total is None:
            return None, None, None
        used = total - available if available is not None else None
        percent = (used / total) * 100.0 if used is not None else None
        return total, used, percent
    except Exception:  # pragma: no cover - fallback best effort
        return None, None, None


def _compute_process_rss_fallback() -> int | None:
    """Return RSS memory bytes using /proc or resource module."""

    try:
        import os

        with open("/proc/self/statm", "r", encoding="utf-8", errors="ignore") as handle:
            parts = handle.read().split()
        if len(parts) >= 2:
            rss_pages = int(parts[1])
            page_size = int(os.sysconf("SC_PAGE_SIZE"))
            return rss_pages * page_size
    except Exception:
        pass

    try:
        import platform
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        rss_kb = getattr(usage, "ru_maxrss", 0)
        if rss_kb:
            system_name = platform.system()
            if system_name == "Darwin":
                return int(rss_kb)
            return int(rss_kb) * 1024
    except Exception:  # pragma: no cover - fallback best effort
        pass

    return None


def _collect_gpu_stats_fallback() -> list[dict[str, object]] | None:
    """Collect GPU stats via NVML when nvidia-smi is unavailable."""

    try:
        import pynvml  # type: ignore

        pynvml.nvmlInit()
        try:
            count = pynvml.nvmlDeviceGetCount()
            gpus: list[dict[str, object]] = []
            for index in range(count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(index)
                name = pynvml.nvmlDeviceGetName(handle)
                try:
                    decoded = name.decode("utf-8")  # type: ignore[assignment]
                except AttributeError:
                    decoded = str(name)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
                gpus.append(
                    {
                        "name": decoded,
                        "util_percent": float(getattr(util, "gpu", 0.0)),
                        "memory_used_bytes": int(getattr(memory, "used", 0)),
                        "memory_total_bytes": int(getattr(memory, "total", 0)),
                    }
                )
            return gpus or None
        finally:
            with suppress(Exception):
                pynvml.nvmlShutdown()
    except Exception:  # pragma: no cover - optional dependency
        return None

@app.get("/sysinfo", include_in_schema=False)
def sysinfo() -> dict[str, object]:
    """Return process, system and GPU usage metrics for the dashboard."""

    import os
    import platform
    import shutil
    import subprocess
    import time

    info: dict[str, object] = {
        "python": platform.python_version(),
        "timestamp": time.time(),
    }

    build_info = dict(get_build_info())
    info.update(
        {
            "build": build_info,
            "build_version": build_info.get("version"),
            "build_revision": build_info.get("revision"),
            "build_time": build_info.get("built_at"),
            "build_time_iso": build_info.get("built_at_iso"),
        }
    )

    try:
        import psutil  # type: ignore

        proc = psutil.Process(os.getpid())
        rss = proc.memory_info().rss
        try:
            cpu = proc.cpu_percent(interval=None)
        except Exception:
            cpu = None

        try:
            system_cpu = psutil.cpu_percent(interval=None)
        except Exception:
            system_cpu = None

        try:
            vm = psutil.virtual_memory()
            total_mem = int(vm.total)
            used_mem = int(vm.used)
            mem_percent = float(vm.percent)
        except Exception:
            total_mem = used_mem = None
            mem_percent = None

        info.update(
            {
                "rss_bytes": int(rss),
                "cpu_percent": cpu,
                "system_cpu_percent": system_cpu,
                "memory_total_bytes": total_mem,
                "memory_used_bytes": used_mem,
                "memory_percent": mem_percent,
            }
        )
    except Exception:
        pass

    if info.get("cpu_percent") is None:
        cpu_fallback = _compute_process_cpu_fallback()
        if cpu_fallback is not None:
            info["cpu_percent"] = cpu_fallback

    if info.get("system_cpu_percent") is None:
        system_cpu_fallback = _compute_system_cpu_fallback()
        if system_cpu_fallback is not None:
            info["system_cpu_percent"] = system_cpu_fallback

    if info.get("rss_bytes") is None:
        rss_fallback = _compute_process_rss_fallback()
        if rss_fallback is not None:
            info["rss_bytes"] = rss_fallback

    if info.get("memory_total_bytes") is None or info.get("memory_used_bytes") is None:
        total_mem, used_mem, mem_percent = _compute_system_memory_fallback()
        if total_mem is not None:
            info["memory_total_bytes"] = total_mem
        if used_mem is not None:
            info["memory_used_bytes"] = used_mem
        if mem_percent is not None:
            info["memory_percent"] = mem_percent

    # GPU metrics via nvidia-smi when available
    if shutil.which("nvidia-smi"):
        try:
            result = subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                text=True,
                timeout=1,
            )
            gpus: list[dict[str, object]] = []
            for line in result.strip().splitlines():
                parts = [part.strip() for part in line.split(",")]
                if len(parts) != 4:
                    continue
                name, util, mem_used, mem_total = parts
                try:
                    util_val = float(util)
                except Exception:
                    util_val = None
                try:
                    mem_used_bytes = int(float(mem_used)) * 1024 * 1024
                    mem_total_bytes = int(float(mem_total)) * 1024 * 1024
                except Exception:
                    mem_used_bytes = mem_total_bytes = None
                gpus.append(
                    {
                        "name": name,
                        "util_percent": util_val,
                        "memory_used_bytes": mem_used_bytes,
                        "memory_total_bytes": mem_total_bytes,
                    }
                )
            if gpus:
                info["gpus"] = gpus
        except Exception:
            pass

    if "gpus" not in info:
        gpu_fallback = _collect_gpu_stats_fallback()
        if gpu_fallback:
            info["gpus"] = gpu_fallback

    return info
