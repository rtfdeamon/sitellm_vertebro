"""FastAPI application setup and lifespan management (Ollama-only)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from typing import Any
from datetime import datetime, timezone, timedelta
import csv
import io
import base64
import hashlib
import hmac
import os
import time
import asyncio
import structlog

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette.routing import NoMatchFound
from fastapi.responses import ORJSONResponse

from observability.logging import configure_logging, get_recent_logs
from observability.metrics import MetricsMiddleware, metrics_app

from api import llm_router, crawler_router
from mongo import MongoClient, NotFound
from models import Document, Project
from settings import MongoSettings, Settings
from core.status import status_dict
from backend.settings import settings as base_settings
from backend.cache import _get_redis
from pymongo import MongoClient as SyncMongoClient
from qdrant_client import QdrantClient
from gridfs import GridFS
from bson import ObjectId
from retrieval import search as retrieval_search
from knowledge.summary import generate_document_summary
import redis
import requests
from pydantic import BaseModel
from uuid import uuid4, UUID


configure_logging()

settings = Settings()
logger = structlog.get_logger(__name__)

ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv(
    "ADMIN_PASSWORD", hashlib.sha256(b"admin").hexdigest()
)
ADMIN_PASSWORD_DIGEST = bytes.fromhex(ADMIN_PASSWORD_HASH)


def _normalize_project(value: str | None) -> str | None:
    """Return a normalized project identifier."""

    candidate = (value or "").strip()
    if not candidate:
        default = getattr(settings, "project_name", None) or settings.domain or os.getenv("PROJECT_NAME") or os.getenv("DOMAIN", "")
        candidate = default.strip() if default else ""
    return candidate.lower() or None


def _parse_stats_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt_value = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Invalid date format (expected YYYY-MM-DD)") from exc
    return dt_value.replace(tzinfo=timezone.utc)


def _build_download_url(request: Request, file_id: str) -> str:
    try:
        return str(request.url_for("admin_download_document", file_id=file_id))
    except NoMatchFound:
        base = str(request.base_url).rstrip("/")
        return f"{base}/api/v1/admin/knowledge/documents/{file_id}"


def _build_token_preview(token: str | None) -> str | None:
    if not token:
        return None
    token = token.strip()
    if not token:
        return None
    return f"{token[:4]}…{token[-2:]}" if len(token) > 6 else "***"


async def _redis_project_usage() -> dict[str, dict[str, float | int]]:
    redis = _get_redis()
    usage: dict[str, dict[str, float | int]] = {}
    try:
        async for key in redis.scan_iter(match="crawler:progress:*"):
            project_key = "__default__"
            try:
                project_value = await redis.hget(key, "project")
                if project_value:
                    decoded = project_value.decode().strip().lower()
                    if decoded:
                        project_key = decoded
            except Exception:  # noqa: BLE001
                pass
            try:
                size = await redis.memory_usage(key)
            except Exception:  # noqa: BLE001
                size = None
            entry = usage.setdefault(
                project_key,
                {
                    "redis_bytes": 0.0,
                    "redis_keys": 0,
                },
            )
            entry["redis_keys"] += 1
            entry["redis_bytes"] += float(size or 0)
    except Exception as exc:  # noqa: BLE001
        logger.warning("redis_usage_failed", error=str(exc))
    return usage


def _project_telegram_payload(
    project: Project,
    controller: "TelegramHub | None" = None,
) -> dict[str, Any]:
    token_value = (
        project.telegram_token.strip() or None
        if isinstance(project.telegram_token, str)
        else None
    )
    running = controller.is_project_running(project.name) if controller else False
    last_error = controller.get_last_error(project.name) if controller else None
    return {
        "project": project.name,
        "running": running,
        "token_set": bool(token_value),
        "token_preview": _build_token_preview(token_value),
        "auto_start": bool(project.telegram_auto_start) if project.telegram_auto_start is not None else False,
        "last_error": last_error,
    }


class _HubSessionProvider:
    """Expose hub session helpers in the shape expected by tg_bot.setup."""

    def __init__(self, hub: "TelegramHub", project: str) -> None:
        self._hub = hub
        self._project = project

    async def get_session(self, project: str, user_id: int | None) -> str | None:
        if user_id is None:
            return None
        project_key = project or self._project
        session = await self._hub.get_or_create_session(project_key, user_id)
        return str(session)


class TelegramRunner:
    """Single bot polling task bound to a project token."""

    def __init__(self, project: str, token: str, hub: "TelegramHub") -> None:
        self.project = project
        self.token = token
        self._task: asyncio.Task | None = None
        self._hub = hub

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.is_running:
            return
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._run())
        self._hub._errors.pop(self.project, None)
        logger.info("telegram_runner_started", project=self.project)

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run(self) -> None:
        from tg_bot.bot import setup
        from aiogram import Bot, Dispatcher

        bot = Bot(token=self.token)
        dp = Dispatcher()
        session_provider = _HubSessionProvider(self._hub, self.project)
        setup(dp, project=self.project, session_provider=session_provider)
        try:
            try:
                await bot.get_me()
            except Exception as exc:  # noqa: BLE001
                self._hub._errors[self.project] = f"token_error: {exc}"
                raise
            await dp.start_polling(bot)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("telegram_runner_failed", project=self.project, error=str(exc))
            self._hub._errors[self.project] = str(exc)
        finally:
            with suppress(Exception):
                await dp.storage.close()
            with suppress(Exception):
                await bot.session.close()


class TelegramHub:
    """Manage multiple Telegram bot instances keyed by project."""

    def __init__(self, mongo: MongoClient) -> None:
        self._mongo = mongo
        self._runners: dict[str, TelegramRunner] = {}
        self._sessions: dict[str, dict[int, UUID]] = {}
        self._errors: dict[str, str] = {}
        self._lock = asyncio.Lock()

    @property
    def is_any_running(self) -> bool:
        return any(runner.is_running for runner in self._runners.values())

    def is_project_running(self, project: str | None) -> bool:
        if not project:
            return False
        runner = self._runners.get(project)
        return runner.is_running if runner else False

    def get_last_error(self, project: str) -> str | None:
        return self._errors.get(project)

    async def get_or_create_session(self, project: str, user_id: int) -> UUID:
        async with self._lock:
            sessions = self._sessions.setdefault(project, {})
            session = sessions.get(user_id)
            if session is None:
                session = uuid4()
                sessions[user_id] = session
            return session

    async def drop_session(self, project: str, user_id: int) -> None:
        async with self._lock:
            sessions = self._sessions.get(project)
            if sessions and user_id in sessions:
                sessions.pop(user_id, None)
                if not sessions:
                    self._sessions.pop(project, None)

    async def stop_all(self) -> None:
        async with self._lock:
            runners = list(self._runners.values())
            self._runners.clear()
            self._sessions.clear()
            self._errors.clear()
        await asyncio.gather(*(runner.stop() for runner in runners), return_exceptions=True)

    async def refresh(self) -> None:
        projects = await self._mongo.list_projects()
        known = {p.name for p in projects}
        for project in projects:
            try:
                await self.ensure_runner(project)
            except Exception as exc:  # noqa: BLE001
                logger.warning("telegram_autostart_failed", project=project.name, error=str(exc))
        stale_keys = set(self._runners) - known
        for project_name in stale_keys:
            await self.stop_project(project_name, forget_sessions=True)

    async def ensure_runner(self, project: Project) -> None:
        token = (
            project.telegram_token.strip() or None
            if isinstance(project.telegram_token, str)
            else None
        )
        auto_start = bool(project.telegram_auto_start)
        if not token:
            await self.stop_project(project.name)
            return
        runner = await self._get_or_create_runner(project.name, token)
        if auto_start:
            try:
                await runner.start()
                logger.info("telegram_autostart_success", project=project.name)
            except Exception:
                async with self._lock:
                    self._runners.pop(project.name, None)
                raise
        else:
            await runner.stop()

    async def start_project(self, project: Project, *, auto_start: bool | None = None) -> None:
        token = (
            project.telegram_token.strip() or None
            if isinstance(project.telegram_token, str)
            else None
        )
        if not token:
            raise HTTPException(status_code=400, detail="Telegram token is not configured")
        runner = await self._get_or_create_runner(project.name, token)
        try:
            await runner.start()
            logger.info("telegram_runner_manual_start", project=project.name)
        except Exception as exc:  # noqa: BLE001
            async with self._lock:
                self._runners.pop(project.name, None)
            raise HTTPException(status_code=400, detail=f"Failed to start bot: {exc}") from exc
        if auto_start is not None:
            project.telegram_auto_start = auto_start
            await self._mongo.upsert_project(project)

    async def stop_project(
        self,
        project_name: str,
        *,
        auto_start: bool | None = None,
        forget_sessions: bool = False,
    ) -> None:
        async with self._lock:
            runner = self._runners.pop(project_name, None)
            self._errors.pop(project_name, None)
        if runner:
            logger.info("telegram_runner_stopping", project=project_name)
            await runner.stop()
        if auto_start is not None:
            project = await self._mongo.get_project(project_name)
            if project:
                project.telegram_auto_start = auto_start
                await self._mongo.upsert_project(project)
        if forget_sessions:
            async with self._lock:
                self._sessions.pop(project_name, None)

    async def _get_or_create_runner(self, project: str, token: str) -> TelegramRunner:
        async with self._lock:
            runner = self._runners.get(project)
        if runner and runner.token != token:
            await runner.stop()
            runner = None
        if runner is None:
            runner = TelegramRunner(project, token, self)
            async with self._lock:
                self._runners[project] = runner
        else:
            runner.token = token
        return runner



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

    normalized = _normalize_project(project_name)
    project: Project | None = None
    if normalized:
        try:
            project = await request.state.mongo.get_project(normalized)
        except Exception as exc:  # noqa: BLE001
            logger.error("project_lookup_failed", project=normalized, error=str(exc))
            raise HTTPException(status_code=500, detail="Failed to read project configuration") from exc
    return normalized, project, request.state.mongo, False


class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/admin"):
            auth = request.headers.get("Authorization")
            if auth and auth.lower().startswith("basic "):
                try:
                    encoded = auth.split(" ", 1)[1]
                    decoded = base64.b64decode(encoded).decode()
                    username, password = decoded.split(":", 1)
                    if username == ADMIN_USER:
                        hashed = hashlib.sha256(password.encode()).digest()
                        if hmac.compare_digest(hashed, ADMIN_PASSWORD_DIGEST):
                            return await call_next(request)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("basic_auth_decode_failed", error=str(exc))
            return Response(status_code=401, headers={"WWW-Authenticate": "Basic"})
        return await call_next(request)


class OllamaLLM:
    """Minimal adapter to use Ollama via backend.llm_client.

    Provides a ``respond`` method compatible with the previous local LLM
    wrapper so the rest of the API does not change.
    """

    class _Msg:
        def __init__(self, text: str) -> None:
            self.text = text

    async def respond(self, session: list[dict[str, str]], preset: list[dict[str, str]]):
        from backend import llm_client

        prompt_parts: list[str] = []
        for m in preset + session:
            role = m.get("role", "user")
            text = m.get("content", "")
            prompt_parts.append(f"{role}: {text}")
        prompt = "\n".join(prompt_parts)

        chunks: list[str] = []
        async for token in llm_client.generate(prompt):
            chunks.append(token)
        return [self._Msg("".join(chunks))]


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
    retrieval_search.qdrant = qdrant_client

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

    vector_store = None

    telegram_hub = TelegramHub(mongo_client)
    app.state.telegram = telegram_hub

    # Warm-up runners based on stored configuration
    try:
        await telegram_hub.refresh()
    except Exception as exc:  # noqa: BLE001
        logger.warning("telegram_hub_refresh_failed", error=str(exc))

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
    mongo_client.client.close()
    qdrant_client.close()


app = FastAPI(lifespan=lifespan, debug=settings.debug)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])
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


@app.get("/api/v1/admin/logs", response_class=ORJSONResponse)
def admin_logs(limit: int = 200) -> ORJSONResponse:
    """Return recent application logs for the admin UI.

    Parameters
    ----------
    limit:
        Maximum number of lines to return (default 200).
    """
    try:
        limit = max(1, min(int(limit), 1000))
    except Exception:
        limit = 200
    lines = get_recent_logs(limit)
    return ORJSONResponse({"lines": lines})


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


class KnowledgeServiceConfig(BaseModel):
    enabled: bool
    idle_threshold_seconds: int | None = None
    poll_interval_seconds: int | None = None
    cooldown_seconds: int | None = None


KNOWLEDGE_SERVICE_KEY = "knowledge_service"


class TelegramConfig(BaseModel):
async def _knowledge_service_status_impl(request: Request) -> ORJSONResponse:
    doc = await request.state.mongo.get_setting(KNOWLEDGE_SERVICE_KEY) or {}
    enabled = bool(doc.get("enabled", False))
    idle = int(doc.get("idle_threshold_seconds") or 300)
    poll = int(doc.get("poll_interval_seconds") or 60)
    cooldown = int(doc.get("cooldown_seconds") or 900)
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
        "message": doc.get("message"),
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
    updated["updated_at"] = time.time()
    await request.state.mongo.set_setting(KNOWLEDGE_SERVICE_KEY, updated)
    return ORJSONResponse({"status": "ok", "enabled": updated["enabled"]})


    token: str | None = None
    auto_start: bool | None = None


class TelegramAction(BaseModel):
    token: str | None = None


class ProjectTelegramConfig(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class ProjectTelegramAction(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class ProjectCreate(BaseModel):
    name: str
    title: str | None = None
    domain: str | None = None
    llm_model: str | None = None
    llm_prompt: str | None = None
    llm_emotions_enabled: bool | None = None
    debug_enabled: bool | None = None
    telegram_token: str | None = None
    telegram_auto_start: bool | None = None
    widget_url: str | None = None


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
        limit = max(1, min(int(limit), 200))
    except Exception:  # noqa: BLE001
        limit = 50

    selector = project or domain
    project_name, project, mongo_client, owns_client = await _get_project_context(
        request, selector
    )

    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)
    filter_query = {"project": project_name} if project_name else {}

    try:
        if q:
            docs_models = await mongo_client.search_documents(
                collection, q, project=project_name
            )
        else:
            cursor = (
                mongo_client.db[collection]
                .find(filter_query, {"_id": False})
                .sort("name", 1)
                .limit(limit)
            )
            docs_models = [Document(**doc) async for doc in cursor]

        documents = [doc.model_dump() if isinstance(doc, Document) else doc for doc in docs_models]
        for doc in documents:
            file_id = doc.get("fileId")
            if file_id:
                doc["downloadUrl"] = _build_download_url(request, file_id)
        total = await mongo_client.db[collection].count_documents(filter_query or {})
        if q:
            matched = len(documents)
            has_more = len(documents) >= limit
        else:
            matched = total
            has_more = len(documents) < total
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"MongoDB query failed: {exc}") from exc
    finally:
        if owns_client:
            await mongo_client.close()

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

    auto_description = False
    description_value = (payload.description or "").strip()
    if not description_value:
        description_value = await generate_document_summary(name, payload.content, project)
        auto_description = True

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
        if project_name:
            project_payload = Project(
                name=project.name if project else project_name,
                title=project.title if project else None,
                domain=domain_value,
                llm_model=project.llm_model if project else None,
                llm_prompt=project.llm_prompt if project else None,
                llm_emotions_enabled=project.llm_emotions_enabled if project else True,
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
        "auto_description": auto_description,
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
    description_value = (description or "").strip()
    auto_description = False
    text_for_summary = ""
    if not description_value:
        if content_type.startswith("text/") or content_type in {"application/json", "application/xml"}:
            text_for_summary = payload.decode("utf-8", errors="ignore")
        description_value = await generate_document_summary(
            filename,
            text_for_summary,
            project_model,
        )
        auto_description = True

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
            "auto_description": auto_description,
        }
    )


@app.get("/api/v1/admin/knowledge/{file_id}", response_class=ORJSONResponse)
async def admin_get_document(request: Request, file_id: str) -> ORJSONResponse:
    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)
    try:
        doc, payload = await request.state.mongo.get_document_with_content(collection, file_id)
    except NotFound:
        raise HTTPException(status_code=404, detail="Document not found")
    content_type = str(doc.get("content_type") or "").lower()
    if content_type and not content_type.startswith("text/"):
        doc["content"] = ""
    else:
        doc["content"] = payload.decode("utf-8", errors="replace")
    return ORJSONResponse(doc)


@app.put("/api/v1/admin/knowledge/{file_id}", response_class=ORJSONResponse)
async def admin_update_document(request: Request, file_id: str, payload: KnowledgeUpdate) -> ORJSONResponse:
    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)
    try:
        existing_doc, raw_content = await request.state.mongo.get_document_with_content(collection, file_id)
    except NotFound:
        raise HTTPException(status_code=404, detail="Document not found")

    current_name = existing_doc.get("name") or "document"
    current_project = existing_doc.get("project") or existing_doc.get("domain")
    current_domain = existing_doc.get("domain")
    current_description = existing_doc.get("description")
    current_url = existing_doc.get("url")
    current_content = raw_content.decode("utf-8", errors="replace")
    current_content_type = str(existing_doc.get("content_type") or "").lower()

    new_name = (payload.name.strip() if isinstance(payload.name, str) else current_name).strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Document name cannot be empty")

    domain_value = (payload.domain.strip() if isinstance(payload.domain, str) else current_domain) or None
    project_value = _normalize_project(payload.project or current_project)
    description_input_provided = isinstance(payload.description, str)
    description_input = payload.description.strip() if description_input_provided else None
    url_value = (payload.url.strip() if isinstance(payload.url, str) else current_url) or None
    project_model = await request.state.mongo.get_project(project_value) if project_value else None
    is_binary = bool(current_content_type and not current_content_type.startswith("text/"))
    auto_description = False

    if is_binary:
        description_value = description_input if description_input_provided else current_description
        if not description_value:
            description_value = await generate_document_summary(new_name, "", project_model)
            auto_description = True
        update_doc: dict[str, Any] = {
            "name": new_name,
            "description": description_value,
            "url": url_value,
            "project": project_value,
            "domain": domain_value,
        }
        await request.state.mongo.db[collection].update_one(
            {"fileId": file_id},
            {"$set": update_doc},
            upsert=False,
        )
        return ORJSONResponse(
            {
                "file_id": file_id,
                "name": new_name,
                "project": project_value,
                "domain": domain_value,
                "description": description_value,
                "auto_description": auto_description,
            }
        )

    content_value = payload.content if payload.content is not None else current_content
    if not content_value or not content_value.strip():
        raise HTTPException(status_code=400, detail="Content is empty")

    description_value = description_input if description_input_provided else current_description
    if not description_value:
        description_value = await generate_document_summary(new_name, content_value, project_model)
        auto_description = True

    name_changed = new_name.lower() != (current_name or "").lower()
    project_changed = project_value != _normalize_project(current_project)

    if name_changed or project_changed:
        await request.state.mongo.delete_document(collection, file_id)
        new_file_id = await request.state.mongo.upsert_text_document(
            name=new_name,
            content=content_value,
            documents_collection=collection,
            description=description_value,
            project=project_value,
            domain=domain_value,
            url=url_value,
        )
    else:
        new_file_id = await request.state.mongo.upsert_text_document(
            name=new_name,
            content=content_value,
            documents_collection=collection,
            description=description_value,
            project=project_value,
            domain=domain_value,
            url=url_value,
        )

    if project_value:
        existing = await request.state.mongo.get_project(project_value)
        project_payload = Project(
            name=project_value,
            title=existing.title if existing else None,
            domain=domain_value or (existing.domain if existing else None),
            llm_model=existing.llm_model if existing else None,
            llm_prompt=existing.llm_prompt if existing else None,
            llm_emotions_enabled=existing.llm_emotions_enabled if existing and existing.llm_emotions_enabled is not None else True,
            telegram_token=existing.telegram_token if existing else None,
            telegram_auto_start=existing.telegram_auto_start if existing else None,
            widget_url=existing.widget_url if existing else None,
        )
        saved_project = await request.state.mongo.upsert_project(project_payload)
        hub: TelegramHub | None = getattr(request.app.state, "telegram", None)
        if isinstance(hub, TelegramHub):
            await hub.ensure_runner(saved_project)

    return ORJSONResponse(
        {
            "file_id": new_file_id,
            "name": new_name,
            "project": project_value,
            "domain": domain_value,
            "description": description_value,
            "auto_description": auto_description,
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
async def admin_reindex_documents() -> ORJSONResponse:
    loop = asyncio.get_running_loop()

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

    def _run_update() -> None:
        from worker import update_vector_store

        update_vector_store()

    loop.run_in_executor(None, _run_update)
    return ORJSONResponse({"status": "queued"})


@app.get("/api/v1/admin/knowledge/service", response_class=ORJSONResponse)
async def admin_knowledge_service_status(request: Request) -> ORJSONResponse:
    return await _knowledge_service_status_impl(request)


@app.post("/api/v1/admin/knowledge/service", response_class=ORJSONResponse)
async def admin_knowledge_service_update(
    request: Request, payload: KnowledgeServiceConfig
) -> ORJSONResponse:
    return await _knowledge_service_update_impl(request, payload)


@llm_router.get("/admin/knowledge/service", response_class=ORJSONResponse)
async def llm_knowledge_service_status(request: Request) -> ORJSONResponse:
    return await _knowledge_service_status_impl(request)


@llm_router.post("/admin/knowledge/service", response_class=ORJSONResponse)
async def llm_knowledge_service_update(
    request: Request, payload: KnowledgeServiceConfig
) -> ORJSONResponse:
    return await _knowledge_service_update_impl(request, payload)

@app.get("/api/v1/admin/projects/names", response_class=ORJSONResponse)
async def admin_project_names(request: Request, limit: int = 100) -> ORJSONResponse:
    """Return a list of known project identifiers."""

    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)
    names = await request.state.mongo.list_project_names(collection, limit=limit)
    default_name = _normalize_project(None)
    if default_name and default_name not in names:
        names.insert(0, default_name)
    return ORJSONResponse({"projects": names})


@app.get("/api/v1/admin/llm/models", response_class=ORJSONResponse)
def admin_llm_models() -> ORJSONResponse:
    """Return available LLM model identifiers."""

    models = base_settings.get_available_llm_models()
    return ORJSONResponse({"models": models})


@app.get("/api/v1/admin/telegram", response_class=ORJSONResponse)
async def telegram_status(request: Request) -> ORJSONResponse:
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
    hub: TelegramHub = request.app.state.telegram
    default_project = _normalize_project(None)
    if not default_project:
        raise HTTPException(status_code=400, detail="Default project is not configured")
    await hub.stop_project(default_project)
    return ORJSONResponse({"running": False})


@app.get("/api/v1/admin/projects/{project}/telegram", response_class=ORJSONResponse)
async def admin_project_telegram_status(project: str, request: Request) -> ORJSONResponse:
    project_name = _normalize_project(project)
    if not project_name:
        raise HTTPException(status_code=400, detail="project is required")

    existing = await request.state.mongo.get_project(project_name)
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
    project_name = _normalize_project(project)
    if not project_name:
        raise HTTPException(status_code=400, detail="project is required")

    existing = await request.state.mongo.get_project(project_name)
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
        llm_model=existing.llm_model,
        llm_prompt=existing.llm_prompt,
        llm_emotions_enabled=existing.llm_emotions_enabled if existing.llm_emotions_enabled is not None else True,
        telegram_token=token_value,
        telegram_auto_start=auto_start_value,
        widget_url=existing.widget_url,
    )

    saved = await request.state.mongo.upsert_project(project_payload)
    hub: TelegramHub = request.app.state.telegram
    await hub.ensure_runner(saved)
    response = _project_telegram_payload(saved, hub)
    return ORJSONResponse(response)


@app.post("/api/v1/admin/projects/{project}/telegram/start", response_class=ORJSONResponse)
async def admin_project_telegram_start(
    project: str,
    request: Request,
    payload: ProjectTelegramAction,
) -> ORJSONResponse:
    project_name = _normalize_project(project)
    if not project_name:
        raise HTTPException(status_code=400, detail="project is required")

    existing = await request.state.mongo.get_project(project_name)
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
        llm_model=existing.llm_model,
        llm_prompt=existing.llm_prompt,
        llm_emotions_enabled=existing.llm_emotions_enabled if existing.llm_emotions_enabled is not None else True,
        telegram_token=token_value,
        telegram_auto_start=auto_start_value,
        widget_url=existing.widget_url,
    )

    saved = await request.state.mongo.upsert_project(project_payload)
    hub: TelegramHub = request.app.state.telegram
    await hub.start_project(saved, auto_start=auto_start_value if "auto_start" in provided_fields else None)
    response = _project_telegram_payload(saved, hub)
    return ORJSONResponse(response)


@app.post("/api/v1/admin/projects/{project}/telegram/stop", response_class=ORJSONResponse)
async def admin_project_telegram_stop(
    project: str,
    request: Request,
    payload: ProjectTelegramAction | None = None,
) -> ORJSONResponse:
    project_name = _normalize_project(project)
    if not project_name:
        raise HTTPException(status_code=400, detail="project is required")

    existing = await request.state.mongo.get_project(project_name)
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
    )

    saved = await request.state.mongo.upsert_project(project_payload)
    hub: TelegramHub = request.app.state.telegram
    await hub.stop_project(saved.name, auto_start=auto_start_value if payload and "auto_start" in provided_fields else None)
    response = _project_telegram_payload(saved, hub)
    return ORJSONResponse(response)


@app.get("/api/v1/admin/stats/requests", response_class=ORJSONResponse)
async def admin_request_stats(
    request: Request,
    project: str | None = None,
    start: str | None = None,
    end: str | None = None,
    channel: str | None = None,
) -> ORJSONResponse:
    project_name = _normalize_project(project)
    start_dt = _parse_stats_date(start)
    end_dt = _parse_stats_date(end)
    if end_dt:
        end_dt = end_dt + timedelta(days=1)
    stats = await request.state.mongo.aggregate_request_stats(
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
    project_name = _normalize_project(project)
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

    async for item in request.state.mongo.iter_request_stats(
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

    projects = await request.state.mongo.list_projects()
    return ORJSONResponse({"projects": [p.model_dump() for p in projects]})


@app.get("/api/v1/admin/projects/storage", response_class=ORJSONResponse)
async def admin_projects_storage(request: Request) -> ORJSONResponse:
    """Return aggregated storage usage per project (Mongo/GridFS/Redis)."""

    mongo_cfg = MongoSettings()
    documents_collection = getattr(request.state, "documents_collection", mongo_cfg.documents)
    contexts_collection = getattr(request.state, "contexts_collection", mongo_cfg.contexts)

    storage = await request.state.mongo.aggregate_project_storage(documents_collection, contexts_collection)
    redis_usage = await _redis_project_usage()

    combined_keys = set(storage.keys()) | set(redis_usage.keys())
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

    name = _normalize_project(payload.name)
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    existing = await request.state.mongo.get_project(name)
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

    if "debug_enabled" in provided_fields:
        debug_value = bool(payload.debug_enabled) if payload.debug_enabled is not None else False
    else:
        if existing and existing.debug_enabled is not None:
            debug_value = bool(existing.debug_enabled)
        else:
            debug_value = False

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

    if "widget_url" in provided_fields:
        if isinstance(payload.widget_url, str):
            widget_url_value = payload.widget_url.strip() or None
        else:
            widget_url_value = None
    else:
        widget_url_value = existing.widget_url if existing else None

    project = Project(
        name=name,
        title=title_value,
        domain=domain_value,
        llm_model=model_value,
        llm_prompt=prompt_value,
        llm_emotions_enabled=emotions_value,
        debug_enabled=debug_value,
        telegram_token=token_value,
        telegram_auto_start=auto_start_value,
        widget_url=widget_url_value,
    )
    project = await request.state.mongo.upsert_project(project)
    hub: TelegramHub | None = getattr(request.app.state, "telegram", None)
    if isinstance(hub, TelegramHub):
        await hub.ensure_runner(project)
    return ORJSONResponse(project.model_dump())


@app.delete("/api/v1/admin/projects/{domain}", status_code=204)
async def admin_delete_project(request: Request, domain: str) -> Response:
    domain_value = _normalize_project(domain)
    if not domain_value:
        raise HTTPException(status_code=400, detail="name is required")
    await request.state.mongo.delete_project(domain_value)
    hub: TelegramHub | None = getattr(request.app.state, "telegram", None)
    if isinstance(hub, TelegramHub):
        await hub.stop_project(domain_value, forget_sessions=True)
    return Response(status_code=204)


@app.get("/api/v1/admin/projects/{domain}/test", response_class=ORJSONResponse)
async def admin_test_project(domain: str, request: Request) -> ORJSONResponse:
    domain_value = _normalize_project(domain)
    if not domain_value:
        raise HTTPException(status_code=400, detail="name is required")

    mongo_ok, mongo_err = _mongo_check()
    redis_ok, redis_err = _redis_check()
    qdrant_ok, qdrant_err = _qdrant_check()

    project = await request.state.mongo.get_project(domain_value)

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
    filename = doc_meta.get("name") or f"{file_id}.bin"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    media_type = doc_meta.get("content_type") or "application/octet-stream"
    return Response(content=payload, media_type=media_type, headers=headers)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redirect the root URL to the web chat widget.

    Opening http://localhost:8000 now lands at ``/widget/`` instead of 404.
    """
    return RedirectResponse(url="/widget/")


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

    return info
