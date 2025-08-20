from __future__ import annotations
import os
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional

from pymongo import MongoClient
from redis import Redis
from qdrant_client import QdrantClient
import structlog

logger = structlog.get_logger(__name__)

REDIS_PREFIX = os.getenv("STATUS_PREFIX", "crawl:")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DB") or os.getenv("MONGO_DATABASE", "app")
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLL = os.getenv("QDRANT_COLLECTION", "documents")
TARGET_DOCS = int(os.getenv("TARGET_DOCS", "1000"))


@dataclass
class CrawlerStats:
    queued: int = 0
    in_progress: int = 0
    done: int = 0
    failed: int = 0
    last_url: Optional[str] = None
    started_at: Optional[float] = None


@dataclass
class DbStats:
    mongo_docs: int = 0
    qdrant_points: int = 0
    target_docs: int = 0
    fill_percent: float = 0.0


@dataclass
class Status:
    ok: bool
    ts: float
    crawler: CrawlerStats
    db: DbStats
    notes: str = ""


def _safe_int(x) -> int:
    try:
        return int(x or 0)
    except Exception:
        return 0


def get_status() -> Status:
    # Redis counters
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    try:
        r = Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True,
            socket_connect_timeout=1,
        )
        q = _safe_int(r.get(REDIS_PREFIX + "queued"))
        p = _safe_int(r.get(REDIS_PREFIX + "in_progress"))
        d = _safe_int(r.get(REDIS_PREFIX + "done"))
        f = _safe_int(r.get(REDIS_PREFIX + "failed"))
        last_url = r.get(REDIS_PREFIX + "last_url")
        started_at = float(r.get(REDIS_PREFIX + "started_at") or 0)
    except Exception as exc:
        logger.warning(
            "redis connection failed",
            host=redis_host,
            port=redis_port,
            error=str(exc),
        )
        q = p = d = f = 0
        last_url = None
        started_at = 0

    # Mongo
    mongo_docs = 0
    try:
        mc = MongoClient(MONGO_URI, serverSelectionTimeoutMS=200)
        mdb = mc[MONGO_DB]
        try:
            names = mdb.list_collection_names()
        except Exception:
            names = []
        for col in ("documents", "pages", "chunks"):
            if col in names:
                try:
                    mongo_docs += mdb[col].estimated_document_count()
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

    # Qdrant
    points = 0
    try:
        qc = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=0.2)
        info = qc.get_collection(QDRANT_COLL)
        points = info.vectors_count or 0
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

    return Status(
        ok=ok,
        ts=time.time(),
        crawler=CrawlerStats(q, p, d, f, last_url, started_at if started_at > 0 else None),
        db=DbStats(mongo_docs, points, target, fill_percent),
        notes="" if ok else "Идет индексирование или есть ошибки; смотрите counters.",
    )


def status_dict() -> Dict[str, Any]:
    s = get_status()
    out = asdict(s)
    out["fill_percent"] = out["db"]["fill_percent"]
    return out
