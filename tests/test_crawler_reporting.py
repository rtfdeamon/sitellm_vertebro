import sys
import types

# Provide a minimal redis stub with RedisError
class RedisError(Exception):
    pass

redis_stub = types.ModuleType("redis")
redis_stub.exceptions = types.SimpleNamespace(RedisError=RedisError)
redis_stub.from_url = lambda *a, **k: None
sys.modules.setdefault("redis", redis_stub)

from backend import crawler_reporting as cr


class DummyLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, msg, **kw):
        self.warnings.append((msg, kw))


class FailRedis:
    def hset(self, *a, **k):
        raise cr.redis.exceptions.RedisError("down")

    def publish(self, *a, **k):
        raise cr.redis.exceptions.RedisError("down")

    def scan_iter(self, *a, **k):
        raise cr.redis.exceptions.RedisError("down")

    def hgetall(self, *a, **k):
        raise cr.redis.exceptions.RedisError("down")


def test_reporter_handles_unavailable_redis(monkeypatch):
    dummy = DummyLogger()
    monkeypatch.setattr(cr, "logger", dummy)
    monkeypatch.setattr(cr, "settings", types.SimpleNamespace(redis_url="redis://"))
    monkeypatch.setattr(cr.redis, "from_url", lambda *a, **k: FailRedis())

    reporter = cr.Reporter()
    reporter.update(cr.CrawlerProgress(job_id="1"))
    assert dummy.warnings

    dummy.warnings.clear()
    assert reporter.get_all() == {}
    assert dummy.warnings
