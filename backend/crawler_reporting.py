from __future__ import annotations
from dataclasses import dataclass, asdict
import json
import time
from typing import Optional, Dict, Any
import structlog
from .settings import settings


logger = structlog.get_logger(__name__)

CHANNEL = "crawler:events"
KEY_TPL = "crawler:progress:{job_id}"


@dataclass
class CrawlerProgress:
    job_id: str
    started_at: float = time.time()
    queued: int = 0
    fetched: int = 0
    parsed: int = 0
    indexed: int = 0
    errors: int = 0
    last_url: Optional[str] = None
    done: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


logger = structlog.get_logger(__name__)


class Reporter:
    def __init__(self) -> None:
        self.r: redis.Redis = redis.from_url(
            settings.redis_url, socket_connect_timeout=1
        )

    def update(self, p: CrawlerProgress) -> None:
        try:
            self.r.hset(KEY_TPL.format(job_id=p.job_id), mapping=p.to_dict())
            self.r.publish(CHANNEL, json.dumps(p.to_dict()))
        except redis.exceptions.RedisError as exc:  # pragma: no cover - logged
            logger.warning("redis update failed", error=str(exc))

    def get_all(self) -> Dict[str, Dict[str, Any]]:
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

