import sys
import types


class RedisError(Exception):
    pass


class ConnectionError(RedisError):
    pass


fake_redis = types.ModuleType("redis")
fake_redis.exceptions = types.SimpleNamespace(
    ConnectionError=ConnectionError, RedisError=RedisError
)
fake_redis.from_url = lambda *a, **k: object()
sys.modules.setdefault("redis", fake_redis)

import redis  # type: ignore  # noqa: E402
import backend.crawler_reporting as cr  # noqa: E402


class FailRedis:
    def hset(self, *args, **kwargs):
        raise redis.exceptions.ConnectionError("fail")

    def publish(self, *args, **kwargs):
        raise redis.exceptions.ConnectionError("fail")

    def scan_iter(self, *args, **kwargs):
        raise redis.exceptions.ConnectionError("fail")

    def hgetall(self, *args, **kwargs):
        raise redis.exceptions.ConnectionError("fail")


def test_unavailable_redis(monkeypatch):
    monkeypatch.setattr(cr, "settings", types.SimpleNamespace(redis_url="redis://"))
    reporter = cr.Reporter()
    reporter.r = FailRedis()
    progress = cr.CrawlerProgress(job_id="1")

    reporter.update(progress)
    assert reporter.get_all() == {}

