from __future__ import annotations
from dataclasses import dataclass, asdict
import json
import time
import redis
from typing import Optional, Dict, Any
from .settings import settings

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


class Reporter:
    def __init__(self) -> None:
        self.r: redis.Redis = redis.from_url(settings.redis_url)

    def update(self, p: CrawlerProgress) -> None:
        self.r.hset(KEY_TPL.format(job_id=p.job_id), mapping=p.to_dict())
        self.r.publish(CHANNEL, json.dumps(p.to_dict()))

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        res: Dict[str, Dict[str, Any]] = {}
        for key in self.r.scan_iter(match="crawler:progress:*"):
            res[key.decode()] = {k.decode(): v.decode() for k, v in self.r.hgetall(key).items()}
        return res
