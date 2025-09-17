"""FastAPI application setup and lifespan management (Ollama-only)."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from typing import Any
import base64
import hashlib
import hmac
import os
import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from fastapi.responses import ORJSONResponse

from observability.logging import configure_logging, get_recent_logs
from observability.metrics import MetricsMiddleware, metrics_app

from api import llm_router, crawler_router
from mongo import MongoClient, NotFound
from models import Document, Project
from settings import MongoSettings, Settings
from core.status import status_dict
from backend.settings import settings as base_settings
from pymongo import MongoClient as SyncMongoClient
from qdrant_client import QdrantClient
from gridfs import GridFS
from bson import ObjectId
from retrieval import search as retrieval_search
import redis
import requests
from pydantic import BaseModel
from uuid import uuid4


configure_logging()

settings = Settings()

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


class TelegramController:
    """Manage lifecycle of the Telegram bot polling task."""

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._token: str | None = None

    @property
    def token(self) -> str | None:
        return self._token

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self, token: str) -> None:
        token = token.strip()
        if not token:
            raise ValueError("Bot token is empty")
        if self.is_running:
            if token == self._token:
                return
            await self.stop()
        self._token = token
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._run(token))

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        self._token = None

    async def _run(self, token: str) -> None:
        from tg_bot.bot import setup
        from aiogram import Bot, Dispatcher

        bot = Bot(token=token)
        dp = Dispatcher()
        setup(dp)
        try:
            await dp.start_polling(bot)
        except asyncio.CancelledError:
            with suppress(Exception):
                await dp.storage.close()
            with suppress(Exception):
                await bot.session.close()
            raise
        except Exception:
            logger.exception("telegram bot polling stopped with error")
        finally:
            with suppress(Exception):
                await dp.storage.close()
            with suppress(Exception):
                await bot.session.close()
            self._task = None
            self._token = None


async def _get_project_context(request: Request, project_name: str | None):
    normalized = _normalize_project(project_name)
    project: Project | None = None
    if normalized:
        project = await request.state.mongo.get_project(normalized)
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
                except Exception:  # noqa: BLE001
                    pass
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
    contexts_collection = mongo_cfg.contexts
    context_presets_collection = mongo_cfg.presets
    documents_collection = mongo_cfg.documents

    vector_store = None

    telegram_ctrl = TelegramController()
    app.state.telegram = telegram_ctrl

    # Optionally auto start Telegram bot if stored in settings
    try:
        setting = await mongo_client.get_setting("telegram")
        if setting and setting.get("auto_start") and setting.get("token"):
            await telegram_ctrl.start(setting["token"])
    except Exception:
        logger.warning("telegram auto-start failed", exc_info=True)

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
        await telegram_ctrl.stop()
    await mongo_client.client.close()
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


class ProjectCreate(BaseModel):
    name: str
    title: str | None = None
    domain: str | None = None
    llm_model: str | None = None
    llm_prompt: str | None = None


class TelegramConfig(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class TelegramAction(BaseModel):
    token: str | None = None


@app.get("/api/v1/admin/knowledge", response_class=ORJSONResponse)
async def admin_knowledge(
    request: Request,
    q: str | None = None,
    limit: int = 50,
    domain: str | None = None,
) -> ORJSONResponse:
    """Return knowledge base documents for the admin UI."""

    try:
        limit = max(1, min(int(limit), 200))
    except Exception:  # noqa: BLE001
        limit = 50

    project_name, project, mongo_client, owns_client = await _get_project_context(
        request, domain
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

    try:
        domain_value = payload.domain or (project.domain if project else None)
        file_id = await mongo_client.upsert_text_document(
            name=name,
            content=payload.content,
            documents_collection=collection,
            description=payload.description,
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
    })


@app.get("/api/v1/admin/knowledge/{file_id}", response_class=ORJSONResponse)
async def admin_get_document(request: Request, file_id: str) -> ORJSONResponse:
    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)
    try:
        doc, payload = await request.state.mongo.get_document_with_content(collection, file_id)
    except NotFound:
        raise HTTPException(status_code=404, detail="Document not found")
    content = payload.decode("utf-8", errors="replace")
    doc["content"] = content
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

    new_name = (payload.name.strip() if isinstance(payload.name, str) else current_name).strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Document name cannot be empty")

    domain_value = (payload.domain.strip() if isinstance(payload.domain, str) else current_domain) or None
    project_value = _normalize_project(payload.project or current_project)
    description_value = (payload.description.strip() if isinstance(payload.description, str) else current_description) or None
    url_value = (payload.url.strip() if isinstance(payload.url, str) else current_url) or None
    content_value = payload.content if payload.content is not None else current_content

    if not content_value or not content_value.strip():
        raise HTTPException(status_code=400, detail="Content is empty")

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
        )
        await request.state.mongo.upsert_project(project_payload)

    return ORJSONResponse(
        {
            "file_id": new_file_id,
            "name": new_name,
            "project": project_value,
            "domain": domain_value,
        }
    )


@app.post("/api/v1/admin/knowledge/reindex", response_class=ORJSONResponse)
async def admin_reindex_documents() -> ORJSONResponse:
    loop = asyncio.get_running_loop()

    def _run_update() -> None:
        from worker import update_vector_store

        update_vector_store()

    loop.run_in_executor(None, _run_update)
    return ORJSONResponse({"status": "queued"})


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

    models = backend_settings.get_available_llm_models()
    return ORJSONResponse({"models": models})


@app.get("/api/v1/admin/telegram", response_class=ORJSONResponse)
async def telegram_status(request: Request) -> ORJSONResponse:
    controller: TelegramController = request.app.state.telegram
    setting = await request.state.mongo.get_setting("telegram") or {}
    token = setting.get("token")
    preview = None
    if token:
        preview = f"{token[:4]}…{token[-2:]}" if len(token) > 6 else "***"
    return ORJSONResponse(
        {
            "running": controller.is_running,
            "token_set": bool(token),
            "token_preview": preview,
            "auto_start": bool(setting.get("auto_start")),
        }
    )


@app.post("/api/v1/admin/telegram/config", response_class=ORJSONResponse)
async def telegram_config(request: Request, payload: TelegramConfig) -> ORJSONResponse:
    controller: TelegramController = request.app.state.telegram
    setting = await request.state.mongo.get_setting("telegram") or {}

    if payload.token is not None:
        token_value = payload.token.strip()
        if token_value:
            setting["token"] = token_value
        else:
            setting.pop("token", None)
        if not token_value and controller.is_running:
            await controller.stop()
    if payload.auto_start is not None:
        setting["auto_start"] = bool(payload.auto_start)

    await request.state.mongo.set_setting("telegram", setting)
    return ORJSONResponse({"ok": True})


@app.post("/api/v1/admin/telegram/start", response_class=ORJSONResponse)
async def telegram_start(request: Request, payload: TelegramAction) -> ORJSONResponse:
    controller: TelegramController = request.app.state.telegram
    setting = await request.state.mongo.get_setting("telegram") or {}
    token = (payload.token or setting.get("token") or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Telegram token is not configured")

    await controller.start(token)
    setting["token"] = token
    await request.state.mongo.set_setting("telegram", setting)
    return ORJSONResponse({"running": True})


@app.post("/api/v1/admin/telegram/stop", response_class=ORJSONResponse)
async def telegram_stop(request: Request) -> ORJSONResponse:
    controller: TelegramController = request.app.state.telegram
    await controller.stop()
    return ORJSONResponse({"running": False})


@app.get("/api/v1/admin/projects", response_class=ORJSONResponse)
async def admin_projects(request: Request) -> ORJSONResponse:
    """Return configured projects."""

    projects = await request.state.mongo.list_projects()
    return ORJSONResponse({"projects": [p.model_dump() for p in projects]})


@app.post("/api/v1/admin/projects", response_class=ORJSONResponse, status_code=201)
async def admin_create_project(request: Request, payload: ProjectCreate) -> ORJSONResponse:
    """Create or update a project (domain)."""

    name = _normalize_project(payload.name)
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    existing = await request.state.mongo.get_project(name)
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

    project = Project(
        name=name,
        title=title_value,
        domain=domain_value,
        llm_model=model_value,
        llm_prompt=prompt_value,
    )
    project = await request.state.mongo.upsert_project(project)
    return ORJSONResponse(project.model_dump())


@app.delete("/api/v1/admin/projects/{domain}", status_code=204)
async def admin_delete_project(request: Request, domain: str) -> Response:
    domain_value = _normalize_project(domain)
    if not domain_value:
        raise HTTPException(status_code=400, detail="name is required")
    await request.state.mongo.delete_project(domain_value)
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
    return Response(content=payload, media_type="application/octet-stream", headers=headers)


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
