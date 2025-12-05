"""Aggregate health and progress metrics from Redis, Mongo and Qdrant.

This module is used by both the HTTP API and CLI utilities to display a
succinct snapshot of the system state: crawler queue counters, database fill
level and freshness of the last crawl. External connections are performed with
short timeouts and failures are logged but tolerated to keep the status page
responsive.
"""

from __future__ import annotations
import os
import platform
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional

from pymongo import MongoClient
from redis import Redis
import structlog

logger = structlog.get_logger(__name__)

REDIS_PREFIX = os.getenv("STATUS_PREFIX", "crawl:")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DB") or os.getenv("MONGO_DATABASE", "app")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
TARGET_DOCS = int(os.getenv("TARGET_DOCS", "1000"))

# Global for CPU tracking
_PROCESS_CPU_SAMPLE: dict | None = None

def _redis_key(name: str, project: str | None = None) -> str:
    if project:
        return f"{REDIS_PREFIX}{project}:{name}"
    return REDIS_PREFIX + name


@dataclass
class CrawlerStats:
    """Counters describing the crawler queue and activity."""
    queued: int = 0
    in_progress: int = 0
    done: int = 0
    failed: int = 0
    last_url: Optional[str] = None
    started_at: Optional[float] = None
    recent_urls: Optional[list[str]] = None
    remaining: int = 0


@dataclass
class DbStats:
    """Database-related metrics for MongoDB and Qdrant."""
    mongo_docs: int = 0
    qdrant_points: int = 0
    target_docs: int = 0
    fill_percent: float = 0.0


@dataclass
class ResourceStats:
    """System resource metrics."""
    cpu_app: Optional[float] = None
    cpu_sys: Optional[float] = None
    ram_used: Optional[int] = None
    ram_total: Optional[int] = None
    ram_percent: Optional[float] = None
    rss_used: Optional[int] = None
    gpu_info: Optional[str] = None
    python_version: Optional[str] = None


@dataclass
class Status:
    """Top-level structure returned by :func:`get_status`."""
    ok: bool
    ts: float
    crawler: CrawlerStats
    db: DbStats
    resources: Optional[ResourceStats] = None
    last_crawl_ts: Optional[float] = None
    last_crawl_iso: Optional[str] = None
    notes: str = ""
    note_codes: tuple[str, ...] = ()
    llm_available: Optional[bool] = None
    qdrant_ok: Optional[bool] = None


def _safe_int(x) -> int:
    try:
        return int(x or 0)
    except Exception:
        return 0


def _compute_process_cpu_fallback() -> float | None:
    """Return process CPU percent without relying on psutil."""
    global _PROCESS_CPU_SAMPLE

    try:
        import resource
    except Exception:
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
        load_avg = os.getloadavg()[0]
        cpu_count = max(1, os.cpu_count() or 1)
        percent = (load_avg / cpu_count) * 100.0
        return max(0.0, min(percent, 100.0))
    except Exception:
        return None


def _read_proc_meminfo() -> dict[str, int]:
    """Parse /proc/meminfo into a mapping of values in bytes."""
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
    return meminfo


def _compute_system_memory_fallback() -> tuple[int | None, int | None, float | None]:
    """Return total/used memory using /proc/meminfo or sysconf fallback.

    Uses MemAvailable from /proc/meminfo which accounts for reclaimable
    buffers and cache, giving accurate "available for applications" memory.
    Falls back to sysconf on systems without /proc/meminfo.
    """
    # Primary method: /proc/meminfo (more accurate, accounts for reclaimable cache)
    try:
        meminfo = _read_proc_meminfo()
        total = meminfo.get("MemTotal")
        if total is not None:
            available = meminfo.get("MemAvailable")
            if available is not None:
                used = int(total) - int(available)
            else:
                # Fallback for old kernels without MemAvailable
                free = meminfo.get("MemFree")
                buffers = meminfo.get("Buffers")
                cached = meminfo.get("Cached")
                sreclaimable = meminfo.get("SReclaimable")
                shmem = meminfo.get("Shmem")

                if all(value is not None for value in (free, buffers, cached)):
                    cache_total = int(cached)
                    if sreclaimable is not None:
                        cache_total += int(sreclaimable)
                    if shmem is not None:
                        cache_total -= int(shmem)
                    cache_total = max(0, cache_total)
                    used = int(total) - int(free) - int(buffers) - cache_total
                else:
                    used = None

            if used is not None:
                used = max(0, min(int(used), int(total)))
                percent = (used / total) * 100.0 if total else None
                if percent is not None:
                    percent = max(0.0, min(percent, 100.0))
            else:
                percent = None

            return int(total), used, percent
    except Exception:
        pass

    # Fallback method: sysconf (for non-Linux systems)
    try:
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
        return None, None, None


def _compute_process_rss_fallback() -> int | None:
    """Return RSS memory bytes using /proc or resource module."""
    try:
        with open("/proc/self/statm", "r", encoding="utf-8", errors="ignore") as handle:
            parts = handle.read().split()
        if len(parts) >= 2:
            rss_pages = int(parts[1])
            page_size = int(os.sysconf("SC_PAGE_SIZE"))
            return rss_pages * page_size
    except Exception:
        pass

    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF)
        rss_kb = getattr(usage, "ru_maxrss", 0)
        if rss_kb:
            system_name = platform.system()
            if system_name == "Darwin":
                return int(rss_kb)
            return int(rss_kb) * 1024
    except Exception:
        pass

    return None


def _collect_gpu_info() -> str | None:
    """Collect GPU information as a formatted string."""
    try:
        import pynvml
        pynvml.nvmlInit()
        try:
            count = pynvml.nvmlDeviceGetCount()
            if count == 0:
                return None
            gpu_parts = []
            for index in range(count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(index)
                name = pynvml.nvmlDeviceGetName(handle)
                try:
                    decoded = name.decode("utf-8")
                except AttributeError:
                    decoded = str(name)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
                util_percent = float(getattr(util, "gpu", 0.0))
                mem_used_gb = int(getattr(memory, "used", 0)) / (1024**3)
                mem_total_gb = int(getattr(memory, "total", 0)) / (1024**3)
                gpu_parts.append(f"{decoded}: {util_percent:.0f}% · {mem_used_gb:.1f}/{mem_total_gb:.1f} GB")
            return "\n".join(gpu_parts) if gpu_parts else None
        finally:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
    except Exception:
        return None


def get_status(domain: str | None = None) -> Status:
    """Collect and return the current :class:`Status`.

    Connects to Redis, MongoDB and Qdrant using environment variables for
    endpoints. Any connection errors are logged and treated as zeros in the
    resulting metrics so the status endpoint never fails hard.
    """
    # Redis counters
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    project_key = domain.strip().lower() if domain else None

    try:
        url = os.getenv("REDIS_URL")
        if url:
            r = Redis.from_url(url, decode_responses=True, socket_connect_timeout=1)
        else:
            r = Redis(
                host=redis_host,
                port=redis_port,
                password=os.getenv("REDIS_PASSWORD") or None,
                decode_responses=True,
                socket_connect_timeout=1,
            )
        q = _safe_int(r.get(_redis_key("queued", project_key)))
        p = _safe_int(r.get(_redis_key("in_progress", project_key)))
        d = _safe_int(r.get(_redis_key("done", project_key)))
        f = _safe_int(r.get(_redis_key("failed", project_key)))
        last_url = r.get(_redis_key("last_url", project_key))
        try:
            recent_urls = list(r.lrange(_redis_key("recent_urls", project_key), 0, 19))
        except Exception:
            recent_urls = None
        started_at = float(r.get(_redis_key("started_at", project_key)) or 0)
    except Exception as exc:
        logger.warning(
            "redis connection failed",
            host=redis_host,
            port=redis_port,
            error=str(exc),
        )
        q = p = d = f = 0
        last_url = None
        recent_urls = None
        started_at = 0

    # Mongo
    mongo_docs = 0
    last_crawl_ts: Optional[float] = None
    try:
        mc = MongoClient(MONGO_URI, serverSelectionTimeoutMS=200)
        mdb = mc[MONGO_DB]
        try:
            names = mdb.list_collection_names()
        except Exception:
            names = []
        doc_filter = {}
        if domain:
            doc_filter = {"$or": [{"project": domain}, {"domain": domain}]}
        if "documents" in names:
            try:
                query = doc_filter or {}
                doc = mdb["documents"].find_one(query, sort=[("ts", -1)])
                if doc and doc.get("ts"):
                    last_crawl_ts = float(doc["ts"])
            except Exception:
                pass
        if "documents" in names:
            try:
                if doc_filter:
                    mongo_docs += mdb["documents"].count_documents(doc_filter)
                else:
                    mongo_docs += mdb["documents"].estimated_document_count()
            except Exception:
                pass
    except Exception as exc:
        logger.warning(
            "mongo connection failed",
            uri=MONGO_URI,
            db=MONGO_DB,
            error=str(exc),
        )
        mongo_docs = 0
        last_crawl_ts = None

    # Qdrant health check
    qdrant_ok = False
    points = 0
    try:
        import httpx
        with httpx.Client(timeout=1.0) as client:
            resp = client.get(f"{QDRANT_URL}/healthz")
            if resp.status_code == 200:
                qdrant_ok = True
    except Exception as exc:
        logger.warning(
            "qdrant connection failed",
            url=QDRANT_URL,
            error=str(exc),
        )

    total_now = max(mongo_docs, points)
    target = max(TARGET_DOCS, 1)
    fill_percent = round(min(100.0, 100.0 * total_now / target), 2)

    ok = (f == 0) and (q == 0) and (p == 0) and (total_now > 0)

    llm_available: Optional[bool]
    try:
        from backend.ollama_cluster import get_cluster_manager  # local import to avoid circular deps

        cluster = get_cluster_manager()
    except Exception:
        llm_available = None
    else:
        try:
            llm_available = cluster.has_available()
        except Exception:
            llm_available = None

    last_crawl_iso = (
        datetime.utcfromtimestamp(last_crawl_ts).isoformat() if last_crawl_ts else None
    )

    remaining = max(q + p, 0)

    notes_parts: list[str] = []
    note_codes: list[str] = []
    if not ok:
        notes_parts.append("Indexing in progress or errors detected; see counters.")
        note_codes.append("crawler_indexing_or_errors")
    if llm_available is False:
        notes_parts.append("LLM unavailable — queue processing paused.")
        note_codes.append("llm_queue_paused")
    notes_text = " ".join(part for part in notes_parts if part)

    # Collect resource metrics
    cpu_app = _compute_process_cpu_fallback()
    cpu_sys = _compute_system_cpu_fallback()
    ram_total, ram_used, ram_percent = _compute_system_memory_fallback()
    rss_used = _compute_process_rss_fallback()
    gpu_info = _collect_gpu_info()
    python_version = platform.python_version()

    resources = ResourceStats(
        cpu_app=cpu_app,
        cpu_sys=cpu_sys,
        ram_used=ram_used,
        ram_total=ram_total,
        ram_percent=ram_percent,
        rss_used=rss_used,
        gpu_info=gpu_info,
        python_version=python_version,
    )

    return Status(
        ok=ok,
        ts=time.time(),
        crawler=CrawlerStats(
            queued=q,
            in_progress=p,
            done=d,
            failed=f,
            last_url=last_url,
            started_at=started_at if started_at > 0 else None,
            recent_urls=recent_urls,
            remaining=remaining,
        ),
        db=DbStats(mongo_docs, points, target, fill_percent),
        resources=resources,
        last_crawl_ts=last_crawl_ts,
        last_crawl_iso=last_crawl_iso,
        notes=notes_text,
        note_codes=tuple(note_codes),
        llm_available=llm_available,
        qdrant_ok=qdrant_ok,
    )


def status_dict(domain: str | None = None) -> Dict[str, Any]:
    """Return the status as a plain dictionary with convenience fields."""
    s = get_status(domain)
    out = asdict(s)
    out["fill_percent"] = out["db"]["fill_percent"]
    if out.get("last_crawl_ts"):
        out["freshness"] = time.time() - out["last_crawl_ts"]
    else:
        out["freshness"] = None
    return out
