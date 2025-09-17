"""FastAPI application setup and lifespan management (Ollama-only)."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
import base64
import hashlib
import hmac
import os

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
from mongo import MongoClient
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
async def lifespan(_) -> AsyncGenerator[dict[str, Any], None]:
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

    yield {
        "llm": llm,
        "mongo": mongo_client,
        "contexts_collection": contexts_collection,
        "context_presets_collection": context_presets_collection,
        "documents_collection": documents_collection,
        "vector_store": vector_store,
    }

    del llm
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


class ProjectCreate(BaseModel):
    name: str
    title: str | None = None
    domain: str | None = None
    llm_model: str | None = None
    llm_prompt: str | None = None


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
    title_value = payload.title.strip() if isinstance(payload.title, str) else (existing.title if existing else None)
    domain_value = payload.domain.strip() if isinstance(payload.domain, str) else (existing.domain if existing else None)
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
    """Return basic process/system metrics for the dashboard.

    Includes process RSS memory, CPU percent (best-effort), and Python version.
    Uses ``psutil`` when available, falls back to minimal data otherwise.
    """
    import os
    import platform
    info: dict[str, object] = {
        "python": platform.python_version(),
    }
    try:
        import psutil  # type: ignore

        p = psutil.Process(os.getpid())
        mem = p.memory_info().rss
        try:
            cpu = p.cpu_percent(interval=0.0)
        except Exception:
            cpu = None
        info.update({
            "rss_bytes": int(mem),
            "cpu_percent": cpu,
        })
    except Exception:
        pass
    return info
