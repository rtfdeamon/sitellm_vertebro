"""FastAPI application setup and lifespan management (Ollama-only)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from typing import Any, Dict
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
import re
import httpx
import structlog

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette.routing import NoMatchFound
from fastapi.responses import ORJSONResponse, PlainTextResponse
from bs4 import BeautifulSoup

from observability.logging import configure_logging, get_recent_logs
from observability.metrics import MetricsMiddleware, metrics_app

from api import llm_router, crawler_router
from mongo import MongoClient, NotFound
from models import Document, Project
from settings import MongoSettings, Settings
from core.status import status_dict
from backend.settings import settings as base_settings
from backend.cache import _get_redis
from core.build import get_build_info
from backend.ollama import (
    list_installed_models,
    popular_models_with_size,
    ollama_available,
)
from pymongo import MongoClient as SyncMongoClient
from qdrant_client import QdrantClient
from gridfs import GridFS
from bson import ObjectId
from retrieval import search as retrieval_search
from knowledge.summary import generate_document_summary
from knowledge.tasks import queue_auto_description
from knowledge.text import extract_doc_text, extract_docx_text, extract_pdf_text
from max_bot.config import get_settings as get_max_settings
import redis
import requests
from pydantic import BaseModel
from uuid import uuid4, UUID


configure_logging()

settings = Settings()
logger = structlog.get_logger(__name__)

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
OLLAMA_INSTALL_JOBS: Dict[str, Dict[str, Any]] = {}
OLLAMA_INSTALL_LOCK = asyncio.Lock()
OLLAMA_PROGRESS_RE = re.compile(r"(\d{1,3})%")
PROMPT_SAMPLE_CHAR_LIMIT = 4000
PROMPT_RESPONSE_CHAR_LIMIT = 1800
PROMPT_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; SiteLLM-PromptBuilder/1.0; +https://example.com)"
    )
}

ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv(
    "ADMIN_PASSWORD", hashlib.sha256(b"admin").hexdigest()
)
ADMIN_PASSWORD_DIGEST = bytes.fromhex(ADMIN_PASSWORD_HASH)

PDF_MIME_TYPES: set[str] = {"application/pdf"}
DOCX_MIME_TYPES: set[str] = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-word.document.macroenabled.12",
}
DOC_MIME_TYPES: set[str] = {
    "application/msword",
    "application/ms-word",
    "application/vnd.ms-word",
    "application/vnd.ms-word.document.macroenabled.12",
}


@dataclass(frozen=True)
class AdminIdentity:
    """Represents authenticated admin context."""

    username: str
    is_super: bool
    projects: tuple[str, ...] = ()

    def can_access_project(self, project: str | None) -> bool:
        if self.is_super:
            return True
        if not project:
            return False
        normalized = project.strip().lower()
        return normalized in self.projects

    @property
    def primary_project(self) -> str | None:
        return self.projects[0] if self.projects else None


def _normalize_project(value: str | None) -> str | None:
    """Return a normalized project identifier."""

    candidate = (value or "").strip()
    if not candidate:
        default = getattr(settings, "project_name", None) or settings.domain or os.getenv("PROJECT_NAME") or os.getenv("DOMAIN", "")
        candidate = default.strip() if default else ""
    return candidate.lower() or None


def _append_limited(buffer: list[str], line: str, *, limit: int = 40) -> None:
    buffer.append(line)
    if len(buffer) > limit:
        del buffer[:-limit]


def _extract_progress(line: str) -> float | None:
    match = OLLAMA_PROGRESS_RE.search(line)
    if not match:
        return None
    try:
        value = float(match.group(1))
    except ValueError:
        return None
    return max(0.0, min(value, 100.0))


async def _snapshot_install_jobs() -> Dict[str, Dict[str, Any]]:
    async with OLLAMA_INSTALL_LOCK:
        snapshot: Dict[str, Dict[str, Any]] = {}
        for model, job in OLLAMA_INSTALL_JOBS.items():
            snapshot[model] = {
                "model": job.get("model", model),
                "status": job.get("status", "unknown"),
                "progress": job.get("progress"),
                "last_line": job.get("last_line"),
                "error": job.get("error"),
                "started_at": job.get("started_at"),
                "finished_at": job.get("finished_at"),
                "log": list(job.get("log", [])[-5:]),
            }
        return snapshot


async def _run_ollama_install(model: str) -> None:
    async with OLLAMA_INSTALL_LOCK:
        job = OLLAMA_INSTALL_JOBS.get(model)
        if job is None:
            return
        job["status"] = "running"
        job.setdefault("progress", 0.0)
        job.setdefault("log", [])
        job.setdefault("stderr", [])
        job["started_at"] = job.get("started_at") or time.time()

    if not ollama_available():
        async with OLLAMA_INSTALL_LOCK:
            job = OLLAMA_INSTALL_JOBS.get(model)
            if job is not None:
                job["status"] = "error"
                job["error"] = "Ollama недоступна на сервере"
                job["finished_at"] = time.time()
        return

    try:
        proc = await asyncio.create_subprocess_exec(
            "ollama",
            "pull",
            model,
            stdout=asyncio_subprocess.PIPE,
            stderr=asyncio_subprocess.PIPE,
        )
    except FileNotFoundError:
        async with OLLAMA_INSTALL_LOCK:
            job = OLLAMA_INSTALL_JOBS.get(model)
            if job is not None:
                job["status"] = "error"
                job["error"] = "Команда `ollama` не найдена"
                job["finished_at"] = time.time()
        return
    except Exception as exc:  # noqa: BLE001
        async with OLLAMA_INSTALL_LOCK:
            job = OLLAMA_INSTALL_JOBS.get(model)
            if job is not None:
                job["status"] = "error"
                job["error"] = str(exc)
                job["finished_at"] = time.time()
        return

    async with OLLAMA_INSTALL_LOCK:
        job = OLLAMA_INSTALL_JOBS.get(model)
        if job is not None:
            job["pid"] = proc.pid

    async def _consume(stream, key: str) -> None:
        while True:
            line = await stream.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="ignore").strip()
            if not text:
                continue
            async with OLLAMA_INSTALL_LOCK:
                job = OLLAMA_INSTALL_JOBS.get(model)
                if job is None:
                    continue
                buffer = job.setdefault(key, [])
                _append_limited(buffer, text)
                if key == "log":
                    job["last_line"] = text
                    progress = _extract_progress(text)
                    if progress is not None:
                        job["progress"] = progress

    await asyncio.gather(
        _consume(proc.stdout, "log"),
        _consume(proc.stderr, "stderr"),
    )

    returncode = await proc.wait()
    async with OLLAMA_INSTALL_LOCK:
        job = OLLAMA_INSTALL_JOBS.get(model)
        if job is None:
            return
        job["finished_at"] = time.time()
        if returncode == 0:
            job["status"] = "success"
            job["progress"] = 100.0
            job.setdefault("log", [])
            _append_limited(job["log"], "Установка завершена", limit=60)
        else:
            job["status"] = "error"
            job.setdefault("stderr", [])
            if job.get("stderr"):
                job["error"] = job["stderr"][-1]
            else:
                job["error"] = f"ollama pull завершился с кодом {returncode}"


async def _schedule_ollama_install(model: str) -> Dict[str, Any]:
    normalized = model.strip()
    if not normalized:
        raise ValueError("model is required")

    async with OLLAMA_INSTALL_LOCK:
        existing = OLLAMA_INSTALL_JOBS.get(normalized)
        if existing and existing.get("status") in {"pending", "running"}:
            return existing
        job = {
            "model": normalized,
            "status": "pending",
            "progress": 0.0,
            "log": [],
            "stderr": [],
            "started_at": time.time(),
            "finished_at": None,
        }
        OLLAMA_INSTALL_JOBS[normalized] = job

    asyncio.create_task(_run_ollama_install(normalized))
    return job

def _get_admin_identity(request: Request) -> AdminIdentity | None:
    identity = getattr(request.state, "admin", None)
    return identity if isinstance(identity, AdminIdentity) else None


def _require_admin(request: Request) -> AdminIdentity:
    identity = _get_admin_identity(request)
    if identity is None:
        raise HTTPException(status_code=401, detail="Admin authentication required")
    return identity


def _require_super_admin(request: Request) -> AdminIdentity:
    identity = _require_admin(request)
    if not identity.is_super:
        raise HTTPException(status_code=403, detail="Super admin privileges required")
    return identity


def _resolve_admin_project(
    request: Request,
    project_name: str | None,
    *,
    required: bool = False,
) -> str | None:
    identity = _get_admin_identity(request)
    normalized = _normalize_project(project_name)
    if identity and not identity.is_super:
        normalized_allowed: list[str] = []
        for proj in identity.projects:
            if not proj:
                continue
            cleaned = proj.strip().lower()
            if cleaned and cleaned not in normalized_allowed:
                normalized_allowed.append(cleaned)
        if not normalized_allowed:
            raise HTTPException(status_code=403, detail="Project administrator has no assigned project")
        if normalized and normalized not in normalized_allowed:
            raise HTTPException(status_code=403, detail="Access to project is forbidden")
        normalized = normalized or normalized_allowed[0]
        if not normalized:
            raise HTTPException(status_code=403, detail="Project scope is required")
    if required and not normalized:
        raise HTTPException(status_code=400, detail="Project identifier is required")
    return normalized


def _admin_logout_response(request: Request) -> PlainTextResponse:
    identity = _get_admin_identity(request)
    if identity:
        logger.info(
            "admin_logout",
            username=identity.username,
            is_super=identity.is_super,
        )
    response = PlainTextResponse("Logged out", status_code=401)
    response.headers["WWW-Authenticate"] = 'Basic realm="admin"'
    return response


def _project_response(project: Project) -> dict[str, Any]:
    data = project.model_dump()
    data.pop("admin_password_hash", None)
    data.pop("telegram_token", None)
    data.pop("max_token", None)
    data["admin_password_set"] = bool(project.admin_password_hash)
    data["telegram_token_set"] = bool(project.telegram_token)
    data["max_token_set"] = bool(project.max_token)
    return data


def _get_mongo_client(request: Request) -> MongoClient:
    mongo_client: MongoClient | None = getattr(request.state, "mongo", None)
    if mongo_client is None:
        mongo_client = getattr(request.app.state, "mongo", None)
        if mongo_client is None:
            raise HTTPException(status_code=500, detail="Mongo client is unavailable")
        request.state.mongo = mongo_client
    return mongo_client


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


def _project_max_payload(
    project: Project,
    controller: "MaxHub | None" = None,
) -> dict[str, Any]:
    token_value = (
        project.max_token.strip() or None
        if isinstance(project.max_token, str)
        else None
    )
    running = controller.is_project_running(project.name) if controller else False
    last_error = controller.get_last_error(project.name) if controller else None
    return {
        "project": project.name,
        "running": running,
        "token_set": bool(token_value),
        "token_preview": _build_token_preview(token_value),
        "auto_start": bool(project.max_auto_start) if project.max_auto_start is not None else False,
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


class MaxRunner:
    """Long-polling task for a MAX messenger bot token."""

    def __init__(self, project: str, token: str, hub: "MaxHub") -> None:
        self.project = project
        self.token = token
        self._hub = hub
        self._task: asyncio.Task | None = None
        self._settings = get_max_settings()

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.is_running:
            return
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._run())
        self._hub._errors.pop(self.project, None)
        logger.info("max_runner_started", project=self.project)

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run(self) -> None:
        import httpx

        from tg_bot.client import rag_answer  # Reuse backend client with channel override

        base_url = self._settings.base_url()
        timeout = httpx.Timeout(
            connect=self._settings.request_timeout,
            read=self._settings.request_timeout + self._settings.updates_timeout + 10,
            write=self._settings.request_timeout,
            pool=self._settings.request_timeout,
        )
        params_base = {
            "access_token": self.token,
            "limit": max(1, int(self._settings.updates_limit)),
            "timeout": max(1, int(self._settings.updates_timeout)),
        }
        marker: int | None = None
        async with httpx.AsyncClient(timeout=timeout) as client:
            while True:
                request_params = params_base.copy()
                if marker is not None:
                    request_params["marker"] = marker
                try:
                    response = await client.get(f"{base_url}/updates", params=request_params)
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    detail = exc.response.text
                    message = f"status={status} {detail.strip() or exc!r}"
                    logger.warning("max_updates_failed", project=self.project, status=status, detail=detail)
                    self._hub._errors[self.project] = message
                    await asyncio.sleep(self._settings.idle_sleep_seconds)
                    if status in {401, 403}:
                        # authentication issues - give up until configuration changes
                        await asyncio.sleep(max(15, self._settings.idle_sleep_seconds))
                    continue
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    logger.warning("max_updates_exception", project=self.project, error=str(exc))
                    self._hub._errors[self.project] = str(exc)
                    await asyncio.sleep(self._settings.idle_sleep_seconds)
                    continue

                try:
                    payload = response.json()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("max_updates_decode_failed", project=self.project, error=str(exc))
                    self._hub._errors[self.project] = f"decode_error: {exc}"
                    await asyncio.sleep(self._settings.idle_sleep_seconds)
                    continue

                updates = payload.get("updates") or []
                marker = payload.get("marker", marker)
                if not updates:
                    self._hub._errors.pop(self.project, None)
                    await asyncio.sleep(self._settings.idle_sleep_seconds)
                    continue

                for update in updates:
                    if self._task is None or self._task.cancelled():
                        return
                    try:
                        await self._handle_update(update, client, rag_answer)
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("max_update_failed", project=self.project, error=str(exc))
                        self._hub._errors[self.project] = str(exc)
                        await asyncio.sleep(self._settings.idle_sleep_seconds)
                        break
                else:
                    self._hub._errors.pop(self.project, None)

    async def _handle_update(
        self,
        update: dict[str, Any],
        client,
        rag_answer_fn,
    ) -> None:
        update_type = str(update.get("update_type") or "").strip().lower()
        if update_type == "message_created":
            await self._handle_message_created(update, client, rag_answer_fn)
        else:
            logger.debug(
                "max_update_ignored",
                project=self.project,
                update_type=update_type,
            )

    async def _handle_message_created(self, update: dict[str, Any], client, rag_answer_fn) -> None:
        message = update.get("message") or {}
        sender = message.get("sender") or {}
        if sender.get("is_bot"):
            return
        body = message.get("body") or {}
        text = (body.get("text") or "").strip()
        if not text:
            return

        session_key = self._session_key(message)
        session_id: str | None = None
        if session_key:
            session_uuid = await self._hub.get_or_create_session(self.project, session_key)
            session_id = str(session_uuid)

        try:
            answer = await rag_answer_fn(
                text,
                project=self.project,
                session_id=session_id,
                channel="max",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("max_answer_failed", project=self.project, error=str(exc))
            self._hub._errors[self.project] = f"answer_error: {exc}"
            return

        response_text = str(answer.get("text") or "").strip()
        attachments = answer.get("attachments") or []
        fallback_blocks: list[str] = []
        attachment_messages: list[dict[str, Any]] = []

        if attachments:
            import httpx

            async with httpx.AsyncClient(timeout=self._settings.request_timeout) as download_client:
                prepared, fallbacks = await self._prepare_max_attachments(attachments, client, download_client)
                attachment_messages = prepared
                fallback_blocks.extend(fallbacks)

        if fallback_blocks:
            block = "\n\n".join(fallback_blocks)
            response_text = f"{response_text}\n\n{block}" if response_text else block

        response_text = self._clip_text(response_text)
        recipient = message.get("recipient") or {}

        if response_text:
            await self._send_message(client, recipient, {"text": response_text})

        for item in attachment_messages:
            await self._send_message(client, recipient, item)

    def _session_key(self, message: dict[str, Any]) -> str | None:
        recipient = message.get("recipient") or {}
        chat_id = recipient.get("chat_id")
        if chat_id is not None:
            return f"chat:{chat_id}"
        sender = message.get("sender") or {}
        user_id = sender.get("user_id") or recipient.get("user_id")
        if user_id is not None:
            return f"user:{user_id}"
        return None

    def _clip_text(self, text: str) -> str:
        value = text.strip()
        if len(value) > 3800:
            value = value[:3797].rstrip() + "…"
        return value

    async def _send_message(self, client, recipient: dict[str, Any], payload: dict[str, Any]) -> None:
        params: dict[str, Any] = {
            "access_token": self.token,
        }
        chat_id = recipient.get("chat_id")
        user_id = recipient.get("user_id")
        if chat_id is not None:
            params["chat_id"] = chat_id
        if user_id is not None and "chat_id" not in params:
            params["user_id"] = user_id

        body: dict[str, Any] = {}
        text = payload.get("text")
        attachments = payload.get("attachments")
        if text:
            body["text"] = text
            if self._settings.disable_link_preview:
                params["disable_link_preview"] = "true"
        if attachments:
            body["attachments"] = attachments
        if not body:
            return

        base_url = self._settings.base_url()
        try:
            response = await client.post(
                f"{base_url}/messages",
                params=params,
                json=body,
            )
            response.raise_for_status()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("max_send_failed", project=self.project, error=str(exc))
            self._hub._errors[self.project] = f"send_error: {exc}"

    async def _prepare_max_attachments(
        self,
        attachments: list[dict[str, Any]],
        api_client,
        download_client,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        prepared: list[dict[str, Any]] = []
        fallbacks: list[str] = []
        for idx, attachment in enumerate(attachments, start=1):
            try:
                result = await self._prepare_single_attachment(attachment, api_client, download_client)
            except Exception as exc:  # noqa: BLE001
                logger.warning("max_attachment_prepare_failed", project=self.project, error=str(exc))
                result = None
            if result:
                prepared.append(result)
            else:
                fallback = self._attachment_fallback_text(attachment, idx)
                if fallback:
                    fallbacks.append(fallback)
        return prepared, fallbacks

    async def _prepare_single_attachment(
        self,
        attachment: dict[str, Any],
        api_client,
        download_client,
    ) -> dict[str, Any] | None:
        name = str(attachment.get("name") or attachment.get("title") or "attachment")
        description = attachment.get("description")
        content_type = str(attachment.get("content_type") or "")
        file_bytes: bytes | None = None

        file_id = attachment.get("file_id") or attachment.get("id")
        if file_id:
            try:
                doc_meta, payload = await self._hub._mongo.get_document_with_content(
                    self._hub._mongo.documents_collection,
                    file_id,
                )
                file_bytes = payload
                if not content_type:
                    content_type = str(doc_meta.get("content_type") or "")
            except NotFound:
                file_bytes = None
            except Exception as exc:  # noqa: BLE001
                logger.warning("max_attachment_mongo_failed", project=self.project, error=str(exc))

        if file_bytes is None:
            download_url = attachment.get("download_url") or attachment.get("url")
            if download_url and str(download_url).lower().startswith("http"):
                try:
                    response = await download_client.get(download_url)
                    response.raise_for_status()
                    file_bytes = response.content
                    if not content_type:
                        content_type = str(response.headers.get("content-type") or "")
                except Exception as exc:  # noqa: BLE001
                    logger.warning("max_attachment_download_failed", project=self.project, error=str(exc), url=download_url)
            else:
                return None

        if not file_bytes:
            return None
        if not content_type:
            content_type = "application/octet-stream"

        upload_type = self._detect_upload_type(content_type)
        base_url = self._settings.base_url()
        try:
            upload_resp = await api_client.post(
                f"{base_url}/uploads",
                params={"access_token": self.token, "type": upload_type},
            )
            upload_resp.raise_for_status()
            upload_meta = upload_resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("max_upload_init_failed", project=self.project, error=str(exc))
            return None

        upload_url = upload_meta.get("url")
        initial_token = upload_meta.get("token")
        if not upload_url:
            return None

        try:
            upload_response = await download_client.post(
                upload_url,
                files={"data": (name, file_bytes, content_type or "application/octet-stream")},
            )
            upload_response.raise_for_status()
            try:
                upload_result = upload_response.json()
            except Exception:  # noqa: BLE001
                upload_result = {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("max_upload_failed", project=self.project, error=str(exc), url=upload_url)
            return None

        payload: dict[str, Any] | None = None
        if upload_type in {"video", "audio"}:
            token_value = initial_token or upload_result.get("token")
            if token_value:
                payload = {"token": token_value}
        elif upload_type == "image":
            photos = upload_result.get("photos")
            token_value = upload_result.get("token")
            if photos:
                payload = {"photos": photos}
            elif token_value:
                payload = {"token": token_value}
        else:  # file or other
            token_value = upload_result.get("token")
            if token_value:
                payload = {"token": token_value}

        if not payload:
            logger.warning("max_upload_no_token", project=self.project, type=upload_type)
            return None

        attachment_request = {"type": upload_type, "payload": payload}
        caption = description or name
        message_payload = {"attachments": [attachment_request]}
        if caption:
            message_payload["text"] = self._clip_text(str(caption))
        return message_payload

    def _detect_upload_type(self, content_type: str) -> str:
        lowered = (content_type or "").lower()
        if lowered.startswith("image/"):
            return "image"
        if lowered.startswith("video/"):
            return "video"
        if lowered.startswith("audio/"):
            return "audio"
        return "file"

    def _attachment_fallback_text(self, attachment: dict[str, Any], index: int) -> str | None:
        name = str(attachment.get("name") or attachment.get("title") or f"Документ {index}")
        description = attachment.get("description")
        download = attachment.get("download_url") or attachment.get("url")
        lines = [f"{index}. {name}"]
        if description:
            lines.append(str(description))
        if download:
            lines.append(str(download))
        return "\n".join(lines)


class MaxHub:
    """Manage MAX bot runners per project."""

    def __init__(self, mongo: MongoClient) -> None:
        self._mongo = mongo
        self._runners: dict[str, MaxRunner] = {}
        self._sessions: dict[str, dict[str, UUID]] = {}
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

    async def get_or_create_session(self, project: str, user_key: str) -> UUID:
        async with self._lock:
            sessions = self._sessions.setdefault(project, {})
            session = sessions.get(user_key)
            if session is None:
                session = uuid4()
                sessions[user_key] = session
            return session

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
                logger.warning("max_autostart_failed", project=project.name, error=str(exc))
        stale = set(self._runners) - known
        for project_name in stale:
            await self.stop_project(project_name, forget_sessions=True)

    async def ensure_runner(self, project: Project) -> None:
        token = (
            project.max_token.strip() or None
            if isinstance(project.max_token, str)
            else None
        )
        auto_start = bool(project.max_auto_start)
        if not token:
            await self.stop_project(project.name)
            return
        runner = await self._get_or_create_runner(project.name, token)
        if auto_start:
            try:
                await runner.start()
                logger.info("max_autostart_success", project=project.name)
            except Exception:
                async with self._lock:
                    self._runners.pop(project.name, None)
                raise
        else:
            await runner.stop()

    async def start_project(self, project: Project, *, auto_start: bool | None = None) -> None:
        token = (
            project.max_token.strip() or None
            if isinstance(project.max_token, str)
            else None
        )
        if not token:
            raise HTTPException(status_code=400, detail="MAX token is not configured")
        runner = await self._get_or_create_runner(project.name, token)
        try:
            await runner.start()
            logger.info("max_runner_manual_start", project=project.name)
        except Exception as exc:  # noqa: BLE001
            async with self._lock:
                self._runners.pop(project.name, None)
            raise HTTPException(status_code=400, detail=f"Failed to start MAX bot: {exc}") from exc
        if auto_start is not None:
            project.max_auto_start = auto_start
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
            if forget_sessions:
                self._sessions.pop(project_name, None)
        if runner:
            logger.info("max_runner_stopping", project=project_name)
            await runner.stop()
        if auto_start is not None:
            project = await self._mongo.get_project(project_name)
            if project:
                project.max_auto_start = auto_start
                await self._mongo.upsert_project(project)

    async def _get_or_create_runner(self, project: str, token: str) -> MaxRunner:
        async with self._lock:
            runner = self._runners.get(project)
            if runner:
                if runner.token != token:
                    await runner.stop()
                    runner = None
            if runner is None:
                runner = MaxRunner(project, token, self)
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


class BasicAuthMiddleware(BaseHTTPMiddleware):
    _PROTECTED_PREFIXES = ("/admin", "/api/v1/admin")

    async def _authenticate(self, request: Request, username: str, password: str) -> AdminIdentity | None:
        normalized_username = username.strip().lower()
        if normalized_username == ADMIN_USER.strip().lower():
            hashed = hashlib.sha256(password.encode()).digest()
            if hmac.compare_digest(hashed, ADMIN_PASSWORD_DIGEST):
                return AdminIdentity(username=normalized_username, is_super=True)

        mongo_client: MongoClient | None = getattr(request.app.state, "mongo", None)
        if not mongo_client:
            return None

        try:
            project = await mongo_client.get_project_by_admin_username(normalized_username)
        except Exception as exc:  # noqa: BLE001
            logger.warning("project_admin_lookup_failed", username=normalized_username, error=str(exc))
            return None

        if not project or not project.admin_password_hash:
            return None

        candidate_hash = hashlib.sha256(password.encode()).hexdigest()
        stored_hash = project.admin_password_hash.strip().lower()
        if not hmac.compare_digest(candidate_hash, stored_hash):
            return None

        return AdminIdentity(
            username=normalized_username,
            is_super=False,
            projects=(project.name,),
        )

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not any(path.startswith(prefix) for prefix in self._PROTECTED_PREFIXES):
            return await call_next(request)

        auth = request.headers.get("Authorization")
        if auth and auth.lower().startswith("basic "):
            try:
                encoded = auth.split(" ", 1)[1]
                decoded = base64.b64decode(encoded).decode()
                username, password = decoded.split(":", 1)
                identity = await self._authenticate(request, username, password)
                if identity:
                    request.state.admin = identity
                    return await call_next(request)
            except Exception as exc:  # noqa: BLE001
                logger.warning("basic_auth_decode_failed", error=str(exc))

        return Response(status_code=401, headers={"WWW-Authenticate": "Basic"})


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
    max_hub = MaxHub(mongo_client)

    app.state.telegram = telegram_hub
    app.state.max = max_hub
    app.state.mongo = mongo_client
    app.state.contexts_collection = contexts_collection
    app.state.context_presets_collection = context_presets_collection
    app.state.documents_collection = documents_collection
    app.state.pending_attachments = {}
    app.state.pending_attachments_lock = asyncio.Lock()

    # Warm-up runners based on stored configuration
    try:
        await telegram_hub.refresh()
    except Exception as exc:  # noqa: BLE001
        logger.warning("telegram_hub_refresh_failed", error=str(exc))
    try:
        await max_hub.refresh()
    except Exception as exc:  # noqa: BLE001
        logger.warning("max_hub_refresh_failed", error=str(exc))

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
    mongo_client.client.close()
    qdrant_client.close()
    with suppress(AttributeError):
        del app.state.mongo
        del app.state.contexts_collection
        del app.state.context_presets_collection
        del app.state.documents_collection
        del app.state.telegram
        del app.state.max

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


@app.post("/api/v1/admin/logout", response_class=PlainTextResponse, include_in_schema=False)
async def admin_logout(request: Request) -> PlainTextResponse:
    return _admin_logout_response(request)


@app.get("/api/v1/admin/logout", response_class=PlainTextResponse, include_in_schema=False)
async def admin_logout_get(request: Request) -> PlainTextResponse:
    return _admin_logout_response(request)


@app.get("/api/v1/admin/logs", response_class=ORJSONResponse)
def admin_logs(request: Request, limit: int = 200) -> ORJSONResponse:
    """Return recent application logs for the admin UI.

    Parameters
    ----------
    limit:
        Maximum number of lines to return (default 200).
    """
    _require_super_admin(request)
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


class PromptGenerationRequest(BaseModel):
    url: str
    role: str | None = None


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


class TelegramConfig(BaseModel):
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


class MaxConfig(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class MaxAction(BaseModel):
    token: str | None = None


class ProjectMaxConfig(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class ProjectMaxAction(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class OllamaInstallRequest(BaseModel):
    model: str


@app.get("/api/v1/admin/session", response_class=ORJSONResponse)
async def admin_session(request: Request) -> ORJSONResponse:
    identity = _require_admin(request)
    payload = {
        "username": identity.username,
        "is_super": identity.is_super,
        "projects": list(identity.projects),
        "primary_project": identity.primary_project,
        "can_manage_projects": identity.is_super,
    }
    return ORJSONResponse(payload)


class ProjectCreate(BaseModel):
    name: str
    title: str | None = None
    domain: str | None = None
    admin_username: str | None = None
    admin_password: str | None = None
    llm_model: str | None = None
    llm_prompt: str | None = None
    llm_emotions_enabled: bool | None = None
    debug_enabled: bool | None = None
    telegram_token: str | None = None
    telegram_auto_start: bool | None = None
    max_token: str | None = None
    max_auto_start: bool | None = None
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

        documents = [
            doc.model_dump(by_alias=True) if isinstance(doc, Document) else doc
            for doc in docs_models
        ]
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
    lower_name = new_name.lower()
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
            extracted_text = ""
            binary_payload = raw_content or b""
            if current_content_type in PDF_MIME_TYPES or lower_name.endswith(".pdf"):
                extracted_text = extract_pdf_text(binary_payload)
            elif current_content_type in DOCX_MIME_TYPES or lower_name.endswith(".docx"):
                extracted_text = extract_docx_text(binary_payload)
            elif current_content_type in DOC_MIME_TYPES or lower_name.endswith(".doc"):
                extracted_text = extract_doc_text(binary_payload)
            description_value = await generate_document_summary(new_name, extracted_text, project_model)
            auto_description = True
        update_doc: dict[str, Any] = {
            "name": new_name,
            "description": description_value,
            "url": url_value,
            "project": project_value,
            "domain": domain_value,
            "autoDescriptionPending": False,
        }
        await request.state.mongo.db[collection].update_one(
            {"fileId": file_id},
            {"$set": update_doc},
            upsert=False,
        )
        status_note = "Автоописание обновлено" if auto_description else "Описание обновлено"
        await request.state.mongo.update_document_status(
            collection,
            file_id,
            "ready",
            status_note,
        )
        return ORJSONResponse(
            {
                "file_id": file_id,
                "name": new_name,
                "project": project_value,
                "domain": domain_value,
                "description": description_value,
                "auto_description_pending": False,
                "status": "ready",
                "status_message": status_note,
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

    await request.state.mongo.db[collection].update_one(
        {"fileId": new_file_id},
        {"$set": {"autoDescriptionPending": False}},
        upsert=False,
    )
    status_note = "Автоописание обновлено" if auto_description else "Описание обновлено"
    await request.state.mongo.update_document_status(
        collection,
        new_file_id,
        "ready",
        status_note,
    )

    if project_value:
        existing = await request.state.mongo.get_project(project_value)
        project_payload = Project(
            name=project_value,
            title=existing.title if existing else None,
            domain=domain_value or (existing.domain if existing else None),
            admin_username=existing.admin_username if existing else None,
            admin_password_hash=existing.admin_password_hash if existing else None,
            llm_model=existing.llm_model if existing else None,
            llm_prompt=existing.llm_prompt if existing else None,
            llm_emotions_enabled=existing.llm_emotions_enabled if existing and existing.llm_emotions_enabled is not None else True,
            telegram_token=existing.telegram_token if existing else None,
            telegram_auto_start=existing.telegram_auto_start if existing else None,
            max_token=existing.max_token if existing else None,
            max_auto_start=existing.max_auto_start if existing else None,
            widget_url=existing.widget_url if existing else None,
        )
        saved_project = await request.state.mongo.upsert_project(project_payload)
        hub: TelegramHub | None = getattr(request.app.state, "telegram", None)
        if isinstance(hub, TelegramHub):
            await hub.ensure_runner(saved_project)
        max_hub: MaxHub | None = getattr(request.app.state, "max", None)
        if isinstance(max_hub, MaxHub):
            await max_hub.ensure_runner(saved_project)

    return ORJSONResponse(
        {
            "file_id": new_file_id,
            "name": new_name,
            "project": project_value,
            "domain": domain_value,
            "description": description_value,
            "auto_description_pending": False,
            "status": "ready",
            "status_message": status_note,
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


@app.get("/api/v1/admin/ollama/catalog", response_class=ORJSONResponse)
async def admin_ollama_catalog(request: Request) -> ORJSONResponse:
    _require_super_admin(request)

    installed_models = [
        {
            "name": model.name,
            "size_bytes": model.size_bytes,
            "size_human": model.size_human,
            "modified_at": model.modified_at,
            "digest": model.digest,
        }
        for model in list_installed_models()
    ]
    installed_names = {item["name"] for item in installed_models}
    popular = popular_models_with_size()
    for item in popular:
        item["installed"] = item.get("name") in installed_names
    jobs = await _snapshot_install_jobs()
    default_model = installed_models[0]["name"] if installed_models else None
    return ORJSONResponse(
        {
            "available": ollama_available(),
            "installed": installed_models,
            "popular": popular,
            "jobs": jobs,
            "default_model": default_model,
        }
    )


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
        widget_url=existing.widget_url,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: TelegramHub = request.app.state.telegram
    await hub.ensure_runner(saved)
    response = _project_telegram_payload(saved, hub)
    max_hub: MaxHub | None = getattr(request.app.state, "max", None)
    if isinstance(max_hub, MaxHub):
        await max_hub.ensure_runner(saved)
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
        widget_url=existing.widget_url,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: TelegramHub = request.app.state.telegram
    await hub.start_project(saved, auto_start=auto_start_value if "auto_start" in provided_fields else None)
    response = _project_telegram_payload(saved, hub)
    max_hub: MaxHub | None = getattr(request.app.state, "max", None)
    if isinstance(max_hub, MaxHub):
        await max_hub.ensure_runner(saved)
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
        debug_enabled=existing.debug_enabled,
    )

    saved = await mongo_client.upsert_project(project_payload)
    hub: TelegramHub = request.app.state.telegram
    await hub.stop_project(saved.name, auto_start=auto_start_value if payload and "auto_start" in provided_fields else None)
    response = _project_telegram_payload(saved, hub)
    max_hub: MaxHub | None = getattr(request.app.state, "max", None)
    if isinstance(max_hub, MaxHub):
        await max_hub.ensure_runner(saved)
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

    project = Project(
        name=name,
        title=title_value,
        domain=domain_value,
        admin_username=admin_username_value,
        admin_password_hash=admin_password_hash_value,
        llm_model=model_value,
        llm_prompt=prompt_value,
        llm_emotions_enabled=emotions_value,
        debug_enabled=debug_value,
        telegram_token=token_value,
        telegram_auto_start=auto_start_value,
        max_token=max_token_value,
        max_auto_start=max_auto_start_value,
        widget_url=widget_url_value,
    )
    project = await mongo_client.upsert_project(project)
    hub: TelegramHub | None = getattr(request.app.state, "telegram", None)
    if isinstance(hub, TelegramHub):
        await hub.ensure_runner(project)
    max_hub: MaxHub | None = getattr(request.app.state, "max", None)
    if isinstance(max_hub, MaxHub):
        await max_hub.ensure_runner(project)
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


async def _download_page_text(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=PROMPT_FETCH_HEADERS) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail="Не удалось загрузить страницу") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Не удалось подключиться к сайту") from exc

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


async def _purge_vector_entries(file_ids: list[str]) -> None:
    if not file_ids:
        return
    index_name = settings.redis.vector
    if not index_name:
        return
    try:
        redis_client = _get_redis()
    except Exception as exc:  # noqa: BLE001
        logger.debug("vector_cleanup_unavailable", error=str(exc))
        return

    for file_id in file_ids:
        doc_id = str(file_id)
        try:
            await redis_client.execute_command("FT.DEL", index_name, doc_id)
        except Exception:  # noqa: BLE001
            try:
                await redis_client.execute_command("FT.DEL", index_name, f"doc:{doc_id}")
            except Exception:
                logger.debug("vector_entry_delete_failed", doc_id=doc_id)
        for key in (doc_id, f"doc:{doc_id}"):
            try:
                await redis_client.delete(key)
            except Exception:
                continue


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
        raise HTTPException(status_code=502, detail="Не удалось получить ответ модели") from exc

    generated = "".join(chunks).strip()
    if not generated:
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
