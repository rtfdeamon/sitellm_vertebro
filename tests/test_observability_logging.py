"""Tests for the in-memory logging ring buffer helpers."""

from __future__ import annotations

import importlib
import logging
from datetime import datetime, timedelta


def _reload_logging_module():
    module = importlib.import_module("observability.logging")
    return importlib.reload(module)


def _ring_handler(module):
    module.configure_logging()
    for handler in logging.getLogger().handlers:
        if getattr(handler, "buffer", None) is module._ring:
            return handler
    raise AssertionError("ring buffer handler not configured")


def _make_record(message: str, when: datetime) -> logging.LogRecord:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )
    created = when.timestamp()
    record.created = created
    record.msecs = (created - int(created)) * 1000
    record.relativeCreated = (created - logging._startTime) * 1000  # type: ignore[attr-defined]
    return record


def test_get_recent_logs_ignores_entries_older_than_retention():
    module = _reload_logging_module()
    module.configure_logging()
    handler = _ring_handler(module)
    handler.buffer.clear()

    now = datetime.now()
    recent = now - timedelta(hours=2)
    stale = now - timedelta(days=module.LOG_RETENTION_DAYS + 1)

    handler.handle(_make_record("discarded", stale))
    handler.handle(_make_record("kept", recent))

    result = module.get_recent_logs(limit=5)
    assert any("kept" in line for line in result)
    assert all("discarded" not in line for line in result)


def test_get_recent_logs_honours_limit_after_filtering():
    module = _reload_logging_module()
    module.configure_logging()
    handler = _ring_handler(module)
    handler.buffer.clear()

    now = datetime.now()
    for idx in range(4, -1, -1):
        handler.handle(_make_record(f"recent-{idx}", now - timedelta(hours=idx)))

    result = module.get_recent_logs(limit=3)
    messages = [line.rsplit(" ", 1)[-1] for line in result]
    assert len(result) == 3
    # Latest messages should be retained in chronological order
    assert messages == [f"recent-{idx}" for idx in range(2, -1, -1)]
