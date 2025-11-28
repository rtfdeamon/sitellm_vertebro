"""Ollama model installation manager."""

import asyncio
import asyncio.subprocess as asyncio_subprocess
import json
import re
import time
from typing import Any, Dict

import httpx
import structlog

from backend.ollama import ollama_available
from backend.ollama_cluster import get_cluster_manager

logger = structlog.get_logger(__name__)

OLLAMA_INSTALL_JOBS: Dict[str, Dict[str, Any]] = {}
OLLAMA_INSTALL_LOCK = asyncio.Lock()
OLLAMA_PROGRESS_RE = re.compile(r"(\d{1,3})%")


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


def _pull_payload_progress(payload: Dict[str, Any]) -> float | None:
    """Best-effort extraction of pull progress from Ollama streaming payloads."""
    for key in ("percentage", "percent", "progress"):
        value = payload.get(key)
        if isinstance(value, (int, float)):
            return max(0.0, min(float(value), 100.0))
    completed = payload.get("completed")
    total = payload.get("total")
    if isinstance(completed, (int, float)) and isinstance(total, (int, float)) and total:
        percent = (float(completed) / float(total)) * 100.0
        return max(0.0, min(percent, 100.0))
    return None


async def update_install_job(
    model: str,
    *,
    status: str | None = None,
    progress: float | None = None,
    log_line: str | None = None,
    error: str | None = None,
    finished: bool = False,
) -> bool:
    """Update install job snapshot atomically. Returns False if job missing."""
    async with OLLAMA_INSTALL_LOCK:
        job = OLLAMA_INSTALL_JOBS.get(model)
        if job is None:
            return False
        if status:
            job["status"] = status
        if progress is not None:
            job["progress"] = max(0.0, min(progress, 100.0))
        if log_line:
            buffer = job.setdefault("log", [])
            _append_limited(buffer, log_line, limit=60)
            job["last_line"] = log_line
        if error is not None:
            job["error"] = error or None
            if error:
                buffer = job.setdefault("stderr", [])
                _append_limited(buffer, error, limit=60)
        if finished:
            job["finished_at"] = time.time()
        return True


async def pick_remote_ollama_server() -> Dict[str, Any] | None:
    """Return metadata of an enabled/healthy Ollama server suitable for install."""
    try:
        manager = get_cluster_manager()
    except RuntimeError:
        return None

    try:
        await manager.reload()
    except Exception as exc:  # noqa: BLE001
        logger.debug("ollama_remote_reload_failed", error=str(exc))

    try:
        await manager.wait_until_available(timeout=0.1)
    except Exception:
        # Ignore timeout errors – we'll fall back to snapshot below.
        pass

    try:
        snapshot = await manager.describe()
    except Exception as exc:  # noqa: BLE001
        logger.debug("ollama_remote_describe_failed", error=str(exc))
        return None

    now = time.time()
    candidates: list[Dict[str, Any]] = []
    for server in snapshot:
        if not server.get("enabled", False):
            continue
        base_url = server.get("base_url")
        if not base_url:
            continue
        cooldown_until = server.get("cooldown_until") or 0.0
        if isinstance(cooldown_until, (int, float)) and cooldown_until > now:
            continue
        if server.get("healthy") is False:
            continue
        candidates.append(server)
    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            item.get("inflight") or 0,
            item.get("avg_latency_ms") or 0,
            item.get("name") or "",
        )
    )
    return candidates[0]


async def run_remote_ollama_pull(model: str) -> bool:
    """Attempt to install model via configured remote Ollama server."""
    server = await pick_remote_ollama_server()
    if not server:
        return False

    base_url = str(server.get("base_url") or "").rstrip("/")
    server_name = server.get("name") or base_url
    await update_install_job(
        model,
        log_line=f"Используется Ollama сервер {server_name}",
    )

    url = f"{base_url}/api/pull"
    logger.info("ollama_remote_pull_start", base_url=base_url, model=model)
    success = False
    error_message: str | None = None

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            async with client.stream("POST", url, json={"name": model}) as response:
                response.raise_for_status()
                async for raw_line in response.aiter_lines():
                    if not raw_line:
                        continue
                    try:
                        payload = json.loads(raw_line)
                    except json.JSONDecodeError:
                        payload = {"status": raw_line}
                    status_text = str(payload.get("status") or payload.get("detail") or "").strip()
                    if status_text:
                        await update_install_job(model, log_line=status_text)
                    progress = _pull_payload_progress(payload)
                    if progress is not None:
                        await update_install_job(model, progress=progress)
                    if payload.get("error"):
                        error_message = str(payload["error"])
                        logger.warning(
                            "ollama_remote_pull_error",
                            base_url=base_url,
                            model=model,
                            error=error_message,
                        )
                        break
                    if status_text.lower() == "success":
                        success = True
                        break
    except httpx.HTTPError as exc:
        error_message = f"HTTP ошибка Ollama: {exc}"
        logger.warning(
            "ollama_remote_pull_http_error",
            base_url=base_url,
            model=model,
            error=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        error_message = str(exc)
        logger.warning(
            "ollama_remote_pull_unexpected_error",
            base_url=base_url,
            model=model,
            error=error_message,
        )

    if success:
        await update_install_job(
            model,
            status="success",
            progress=100.0,
            log_line="Установка завершена",
            error=None,
            finished=True,
        )
        logger.info("ollama_remote_pull_success", base_url=base_url, model=model)
    else:
        if not error_message:
            error_message = "Ollama не завершила установку"
        await update_install_job(
            model,
            status="error",
            error=f"ollamaJobError: {model} · {error_message}",
            finished=True,
        )
    return True


async def snapshot_install_jobs() -> Dict[str, Dict[str, Any]]:
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


async def run_ollama_install(model: str) -> None:
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
        if await run_remote_ollama_pull(model):
            return
        await update_install_job(
            model,
            status="error",
            error="ollamaJobError: {model} · Ollama недоступна на сервере".format(model=model),
            finished=True,
        )
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
        if await run_remote_ollama_pull(model):
            return
        await update_install_job(
            model,
            status="error",
            error="ollamaJobError: {model} · Команда `ollama` не найдена".format(model=model),
            finished=True,
        )
        return
    except Exception as exc:  # noqa: BLE001
        if await run_remote_ollama_pull(model):
            return
        await update_install_job(
            model,
            status="error",
            error=f"ollamaJobError: {model} · {exc}",
            finished=True,
        )
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


async def schedule_ollama_install(model: str) -> Dict[str, Any]:
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

    asyncio.create_task(run_ollama_install(normalized))
    return job
