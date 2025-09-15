"""FastAPI application setup and lifespan management (Ollama-only)."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
import base64
import hashlib
import hmac
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from fastapi.responses import ORJSONResponse

from observability.logging import configure_logging
from observability.metrics import MetricsMiddleware, metrics_app

from api import llm_router, crawler_router
from mongo import MongoClient
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

ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv(
    "ADMIN_PASSWORD", hashlib.sha256(b"admin").hexdigest()
)
ADMIN_PASSWORD_DIGEST = bytes.fromhex(ADMIN_PASSWORD_HASH)


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

    vector_store = None

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


def _mongo_ok() -> bool:
    """Best-effort Mongo probe with short retries.

    Containerized Mongo can take a moment to accept connections after it
    reports healthy. Use incremental timeouts to reduce false negatives.
    """
    timeouts = (0.5, 1.5, 3.0)
    for t in timeouts:
        try:
            mc = SyncMongoClient(base_settings.mongo_uri, serverSelectionTimeoutMS=int(t * 1000))
            mc.admin.command("ping")
            mc.close()
            return True
        except Exception:
            continue
    return False


def _redis_ok() -> bool:
    for t in (0.5, 1.0):
        try:
            r = redis.from_url(base_settings.redis_url, socket_connect_timeout=t)
            ok = bool(r.ping())
            try:
                r.close()
            except Exception:
                pass
            return ok
        except Exception:
            continue
    return False


def _qdrant_ok() -> bool:
    for t in (0.8, 1.5):
        try:
            resp = requests.get(f"{base_settings.qdrant_url}/healthz", timeout=t)
            if resp.ok:
                return True
        except Exception:
            continue
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


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    """Lightweight liveness probe used by container healthchecks."""
    return {"status": "ok"}


@app.get("/status")
def status() -> dict[str, object]:
    """Return aggregated crawler and database status."""
    return status_dict()


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
