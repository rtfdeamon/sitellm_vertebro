"""FastAPI routers for interacting with the LLM and crawler."""

from pathlib import Path
import subprocess
import sys
import os
import signal
import urllib.parse as urlparse

from fastapi import APIRouter, Request, HTTPException
try:
    from fastapi import BackgroundTasks
except ImportError:  # pragma: no cover - fallback for test stubs
    class BackgroundTasks:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass
from fastapi.responses import ORJSONResponse, StreamingResponse
import asyncio

import redis.asyncio as redis

import structlog

from backend import llm_client
from backend.settings import settings as backend_settings

from models import LLMResponse, LLMRequest, RoleEnum, Project
from mongo import NotFound
from pydantic import BaseModel

from core.status import status_dict

logger = structlog.get_logger(__name__)


def _normalize_project(value: str | None) -> str | None:
    candidate = (value or "").strip().lower()
    if candidate:
        return candidate
    fallback = backend_settings.project_name or backend_settings.domain
    if fallback:
        return fallback.strip().lower() or None
    return None

llm_router = APIRouter(
    prefix="/llm",
    tags=["llm"],
    responses={
        200: {"description": "LLM response"},
        404: {"description": "Can't find specified sessionId"},
        500: {"description": "Internal Server Error"},
    },
)

crawler_router = APIRouter(
    prefix="/crawler",
    tags=["crawler"],
)


@llm_router.post("/ask", response_class=ORJSONResponse, response_model=LLMResponse)
async def ask_llm(request: Request, llm_request: LLMRequest) -> ORJSONResponse:
    """Return a response from the language model for the given session.

    Parameters
    ----------
    request:
        Incoming request used to access application state.
    llm_request:
        Input payload specifying the ``session_id``.

    Returns
    -------
    ORJSONResponse
        JSON response containing the assistant reply under ``text``.
    """
    mongo_client = request.state.mongo
    project_name = _normalize_project(llm_request.project)
    project: Project | None = None
    if project_name:
        project = await request.state.mongo.get_project(project_name)
        if project is None:
            project = await request.state.mongo.upsert_project(Project(name=project_name))
    logger.info("ask", session=str(llm_request.session_id), project=project_name)
    context = []

    try:
        preset = [
            {"role": message.role, "content": message.text}
            async for message in mongo_client.get_context_preset(
                request.state.context_presets_collection
            )
        ]
    except NotFound:
        logger.warning(
            "preset not found", session=str(llm_request.session_id)
        )
        raise HTTPException(status_code=404, detail="Preset not found")
    try:
        async for message in mongo_client.get_sessions(
            request.state.contexts_collection, str(llm_request.session_id)
        ):
            context.append({"role": str(message.role), "content": message.text})
    except NotFound:
        logger.warning(
            "session not found", session=str(llm_request.session_id)
        )
        raise HTTPException(status_code=404, detail="Can't find specified sessionId")

    if not context:
        raise HTTPException(status_code=400, detail="No conversation history provided")

    if context[-1]["role"] == RoleEnum.assistant:
        logger.error(
            "incorrect session state", session=str(llm_request.session_id)
        )
        raise HTTPException(
            status_code=400, detail="Last message role cannot be assistant"
        )

    if project and project.llm_prompt:
        prompt_text = project.llm_prompt.strip()
        if prompt_text:
            preset = [{"role": "system", "content": prompt_text}] + preset

    # Build a prompt similar to the HTTPModelClient/YaLLM formatting
    prompt_parts: list[str] = []
    for m in preset + context:
        role = m.get("role", "user")
        text = m.get("content", "")
        prompt_parts.append(f"{role}: {text}")
    prompt = "\n".join(prompt_parts)

    chunks: list[str] = []
    model_override = None
    if project and project.llm_model:
        trimmed_model = project.llm_model.strip()
        if trimmed_model:
            model_override = trimmed_model
    async for token in llm_client.generate(prompt, model=model_override):
        chunks.append(token)
    text = "".join(chunks)
    logger.info("llm answered", length=len(text))

    return ORJSONResponse(LLMResponse(text=text).model_dump())


@llm_router.get("/chat")
async def chat(request: Request, question: str, project: str | None = None) -> StreamingResponse:
    """Stream tokens from the language model using server-sent events.

    Parameters
    ----------
    question:
        Text sent as a query parameter. Example: ``/chat?question=hi``.
    """

    project_name = _normalize_project(project)
    project_obj: Project | None = None
    if project_name:
        project_obj = await request.state.mongo.get_project(project_name)
        if project_obj is None:
            project_obj = await request.state.mongo.upsert_project(Project(name=project_name))

    prompt_base = question
    if project_obj and project_obj.llm_prompt:
        prompt_text = project_obj.llm_prompt.strip()
        if prompt_text:
            prompt_base = f"{prompt_text}\n\n{question}"
    model_override = None
    if project_obj and project_obj.llm_model:
        model_text = project_obj.llm_model.strip()
        if model_text:
            model_override = model_text

    logger.info("chat", question=question, project=project_name)

    async def event_stream():
        try:
            async for token in llm_client.generate(prompt_base, model=model_override):
                yield f"data: {token}\n\n"
        except Exception as exc:  # keep connection graceful for the widget
            logger.warning("sse_generate_failed", error=str(exc))
            yield "event: llm_error\ndata: generation_failed\n\n"
        finally:
            # Signal the client that stream has completed
            yield "event: end\ndata: [DONE]\n\n"

    model_header = model_override or getattr(llm_client, "MODEL_NAME", "unknown")
    headers = {"X-Model-Name": model_header}
    response = StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)
    return response


class CrawlRequest(BaseModel):
    start_url: str
    max_pages: int = 500
    max_depth: int = 3
    project: str | None = None
    domain: str | None = None


crawler_router = APIRouter(prefix="/crawler", tags=["crawler"])


def _spawn_crawler(
    start_url: str,
    max_pages: int,
    max_depth: int,
    *,
    project: str | None,
    domain: str | None,
    mongo_uri: str | None,
) -> None:
    script = Path(__file__).resolve().parent / "crawler" / "run_crawl.py"
    cmd = [
        sys.executable,
        str(script),
        "--url",
        start_url,
        "--max-pages",
        str(max_pages),
        "--max-depth",
        str(max_depth),
    ]
    if project:
        cmd.extend(["--project", project])
    if domain:
        cmd.extend(["--domain", domain])
    if mongo_uri:
        cmd.extend(["--mongo-uri", mongo_uri])
    proc = subprocess.Popen(cmd)
    try:
        (Path("/tmp") / "crawler.pid").write_text(str(proc.pid), encoding="utf-8")
    except Exception:
        pass


@crawler_router.post("/run", status_code=202)
async def run_crawler(
    req: CrawlRequest, background_tasks: BackgroundTasks, request: Request
) -> dict[str, str]:
    """Start the crawler in a background task."""

    parsed_host = urlparse.urlsplit(req.start_url).netloc
    allowed_domain = (req.domain or parsed_host or "").lower()
    project_name = _normalize_project(req.project) or _normalize_project(allowed_domain)
    if not project_name:
        raise HTTPException(status_code=400, detail="project is required")

    project = await request.state.mongo.get_project(project_name)
    if project is None:
        project = await request.state.mongo.upsert_project(
            Project(name=project_name, domain=allowed_domain or None)
        )

    background_tasks.add_task(
        _spawn_crawler,
        req.start_url,
        req.max_pages,
        req.max_depth,
        project=project_name,
        domain=allowed_domain or None,
        mongo_uri=backend_settings.mongo_uri,
    )
    return {
        "status": "started",
        "project": project_name,
        "domain": allowed_domain or None,
    }


@crawler_router.get("/status")
async def crawler_status(project: str | None = None) -> dict[str, object]:
    """Return current crawler and database status."""

    return status_dict(_normalize_project(project))


@crawler_router.post("/stop", status_code=202)
async def stop_crawler() -> dict[str, str]:
    """Attempt to stop the last started crawler process by PID file."""
    pid_path = Path("/tmp") / "crawler.pid"
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
    except Exception:
        return {"status": "unknown"}
    try:
        os.kill(pid, signal.SIGTERM)
        return {"status": "stopping", "pid": pid}
    except ProcessLookupError:
        return {"status": "not_running"}
    except Exception:
        return {"status": "error"}


@llm_router.get("/info")
def llm_info() -> dict[str, object]:
    """Expose basic LLM runtime details for the admin panel."""
    device = getattr(llm_client, "DEVICE", "unknown")
    model = getattr(llm_client, "MODEL_NAME", None)
    ollama = getattr(llm_client, "OLLAMA_BASE", None)
    backend = "ollama" if ollama else (device or "local")
    return {
        "model": model,
        "device": device,
        "backend": backend,
        "ollama_base": ollama,
    }


class LLMConfig(BaseModel):
    ollama_base: str | None = None
    model: str | None = None


@llm_router.post("/config", response_class=ORJSONResponse)
def llm_set_config(cfg: LLMConfig) -> ORJSONResponse:
    """Update LLM runtime parameters at runtime.

    This does not persist across process restarts; intended for quick ops.
    """
    if cfg.ollama_base is not None:
        llm_client.OLLAMA_BASE = cfg.ollama_base or None
    if cfg.model:
        llm_client.MODEL_NAME = cfg.model
    return ORJSONResponse(llm_info())


@llm_router.get("/ping")
async def llm_ping() -> dict[str, object]:
    """Ping the configured LLM backend.

    - If Ollama base is set, checks ``/api/tags``.
    - Otherwise returns enabled=False.
    """
    base = getattr(llm_client, "OLLAMA_BASE", None)
    if not base:
        return {"enabled": False, "reachable": None}
    import httpx
    url = f"{base.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            resp = await client.get(url)
            ok = bool(resp.status_code == 200)
            return {"enabled": True, "reachable": ok, "status": resp.status_code}
    except Exception as exc:
        return {"enabled": True, "reachable": False, "error": str(exc)}
