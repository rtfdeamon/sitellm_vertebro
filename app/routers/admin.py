"""Admin router for general admin endpoints.

Provides health checks, CSRF tokens, logout, feedback, and system information.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import ORJSONResponse, PlainTextResponse

from app.services.auth import require_admin, require_super_admin
from backend.settings import settings as base_settings
from core.build import get_build_info

router = APIRouter(tags=["admin"])


def _mongo_check(mongo_uri: str | None = None) -> tuple[bool, str | None]:
    """Best-effort Mongo probe with short retries."""
    from pymongo import MongoClient as SyncMongoClient
    from settings import MongoSettings
    
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
    """Best-effort Redis probe with short retries."""
    import redis
    
    url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
    error: str | None = None
    for timeout in (0.5, 1.0):
        try:
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
    """Best-effort Qdrant probe with short retries."""
    from qdrant_client import QdrantClient
    
    url = qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")
    error: str | None = None
    for timeout in (0.5, 1.0, 2.0):
        try:
            client = QdrantClient(url, timeout=timeout)
            client.get_collections()
            return True, None
        except Exception as exc:
            error = str(exc)
            continue
    return False, error


@router.get("/health", include_in_schema=False)
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


@router.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    """Lightweight liveness probe used by container healthchecks."""
    return {"status": "ok"}


@router.get("/api/v1/admin/csrf-token", include_in_schema=False)
async def get_csrf_token_endpoint(request: Request) -> ORJSONResponse:
    """Get CSRF token for form submission."""
    from backend.csrf import get_csrf_token
    token = await get_csrf_token(request)
    return ORJSONResponse({"csrf_token": token})


@router.post("/api/v1/admin/logout", response_class=PlainTextResponse, include_in_schema=False)
async def admin_logout(request: Request) -> PlainTextResponse:
    """Admin logout endpoint."""
    # Import here to avoid circular dependency
    from app import _admin_logout_response
    return _admin_logout_response(request)


@router.get("/api/v1/admin/logout", response_class=PlainTextResponse, include_in_schema=False)
async def admin_logout_get(request: Request) -> PlainTextResponse:
    """Admin logout endpoint (GET)."""
    # Import here to avoid circular dependency
    from app import _admin_logout_response
    return _admin_logout_response(request)


# Feedback endpoints kept in app.py for now (they use Pydantic models defined there)


@router.get("/sysinfo", include_in_schema=False)
def sysinfo() -> dict[str, object]:
    """Return process, system and GPU usage metrics for the dashboard."""
    # Import here to avoid circular dependency - these helpers stay in app.py
    from app import (
        _compute_process_cpu_fallback,
        _compute_system_cpu_fallback,
        _compute_process_rss_fallback,
        _compute_system_memory_fallback,
        _collect_gpu_stats_fallback,
    )

    info: dict[str, object] = {
        "python": platform.python_version(),
        "timestamp": time.time(),
    }

    build_info = dict(get_build_info())
    info.update({
        "build": build_info,
        "build_version": build_info.get("version"),
        "build_revision": build_info.get("revision"),
        "build_time": build_info.get("built_at"),
        "build_time_iso": build_info.get("built_at_iso"),
    })

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

        info.update({
            "rss_bytes": int(rss),
            "cpu_percent": cpu,
            "system_cpu_percent": system_cpu,
            "memory_total_bytes": total_mem,
            "memory_used_bytes": used_mem,
            "memory_percent": mem_percent,
        })
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
                gpus.append({
                    "name": name,
                    "util_percent": util_val,
                    "memory_used_bytes": mem_used_bytes,
                    "memory_total_bytes": mem_total_bytes,
                })
            if gpus:
                info["gpus"] = gpus
        except Exception:
            pass

    if "gpus" not in info:
        gpu_fallback = _collect_gpu_stats_fallback()
        if gpu_fallback:
            info["gpus"] = gpu_fallback

    return info

