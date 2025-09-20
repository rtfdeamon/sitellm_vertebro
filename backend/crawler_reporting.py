"""Helpers to publish and read crawler progress via Redis.

The :class:`Reporter` provides two operations:
- :meth:`update` to publish and persist progress snapshots; and
- :meth:`get_all` to read all known jobs for console/monitoring tools.

Progress is sent as a Redis hash (``crawler:progress:{job_id}``) and a
pub/sub message to the ``crawler:events`` channel for real-time consumers.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict, field
import json
import time
from typing import Optional, Dict, Any
import structlog
import redis
from .settings import settings


logger = structlog.get_logger(__name__)

CHANNEL = "crawler:events"
KEY_TPL = "crawler:progress:{job_id}"


@dataclass
class CrawlerProgress:
    """Lightweight structure holding per-job crawler counters."""
    job_id: str
    started_at: float = field(default_factory=time.time)
    queued: int = 0
    fetched: int = 0
    parsed: int = 0
    indexed: int = 0
    errors: int = 0
    last_url: Optional[str] = None
    done: bool = False
    project: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert progress to a plain dict for JSON/Redis."""
        return asdict(self)

class Reporter:
    """Publish/consume crawler progress using Redis primitives."""

    def __init__(self) -> None:
        self.r: redis.Redis = redis.from_url(
            settings.redis_url, socket_connect_timeout=1
        )

    def update(self, p: CrawlerProgress) -> None:
        """Store and broadcast a progress snapshot for a job."""
        try:
            self.r.hset(KEY_TPL.format(job_id=p.job_id), mapping=p.to_dict())
            self.r.publish(
                CHANNEL,
                json.dumps(p.to_dict(), ensure_ascii=False),
            )
        except redis.exceptions.RedisError as exc:  # pragma: no cover - logged
            logger.warning("redis update failed", error=str(exc))

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Return a mapping of all job keys to their last known state."""
        res: Dict[str, Dict[str, Any]] = {}
        try:
            for key in self.r.scan_iter(match="crawler:progress:*"):
                res[key.decode()] = {
                    k.decode(): v.decode() for k, v in self.r.hgetall(key).items()
                }
        except redis.exceptions.RedisError as exc:  # pragma: no cover - logged
            logger.warning("redis get_all failed", error=str(exc))
            return {}
        return res
