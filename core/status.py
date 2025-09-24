"""Aggregate health and progress metrics from Redis, Mongo and Qdrant.

This module is used by both the HTTP API and CLI utilities to display a
succinct snapshot of the system state: crawler queue counters, database fill
level and freshness of the last crawl. External connections are performed with
short timeouts and failures are logged but tolerated to keep the status page
responsive.
"""

from __future__ import annotations
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional

from pymongo import MongoClient
from redis import Redis
from qdrant_client import QdrantClient
try:  # Newer qdrant-client
    from qdrant_client.http.exceptions import UnexpectedResponse
except Exception:  # pragma: no cover - fallback type
    UnexpectedResponse = Exception  # type: ignore
import structlog

logger = structlog.get_logger(__name__)

REDIS_PREFIX = os.getenv("STATUS_PREFIX", "crawl:")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DB") or os.getenv("MONGO_DATABASE", "app")
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLL = os.getenv("QDRANT_COLLECTION", "documents")
TARGET_DOCS = int(os.getenv("TARGET_DOCS", "1000"))

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
class Status:
    """Top-level structure returned by :func:`get_status`."""
    ok: bool
    ts: float
    crawler: CrawlerStats
    db: DbStats
    last_crawl_ts: Optional[float] = None
    last_crawl_iso: Optional[str] = None
    notes: str = ""


def _safe_int(x) -> int:
    try:
        return int(x or 0)
    except Exception:
        return 0


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

    # Qdrant
    points = 0
    try:
        qc = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=0.3)
        info = qc.get_collection(QDRANT_COLL)
        points = getattr(info, "vectors_count", 0) or 0
    except UnexpectedResponse as exc:
        # 404 Not Found — коллекция ещё не создана: не шумим в логах
        if "Not found" in str(exc) or "404" in str(exc):
            points = 0
        else:  # реальные ошибки продолжаем логировать
            logger.warning(
                "qdrant connection failed",
                host=QDRANT_HOST,
                port=QDRANT_PORT,
                collection=QDRANT_COLL,
                error=str(exc),
            )
            points = 0
    except Exception as exc:
        logger.warning(
            "qdrant connection failed",
            host=QDRANT_HOST,
            port=QDRANT_PORT,
            collection=QDRANT_COLL,
            error=str(exc),
        )
        points = 0

    total_now = max(mongo_docs, points)
    target = max(TARGET_DOCS, 1)
    fill_percent = round(min(100.0, 100.0 * total_now / target), 2)

    ok = (f == 0) and (q == 0) and (p == 0) and (total_now > 0)

    last_crawl_iso = (
        datetime.utcfromtimestamp(last_crawl_ts).isoformat() if last_crawl_ts else None
    )

    remaining = max(q + p, 0)

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
        last_crawl_ts=last_crawl_ts,
        last_crawl_iso=last_crawl_iso,
        notes="" if ok else "Идет индексирование или есть ошибки; смотрите counters.",
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
