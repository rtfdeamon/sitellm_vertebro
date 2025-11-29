"""Logging configuration utilities with in-memory ring buffer.

Provides ``get_recent_logs(limit)`` used by the admin UI to display the last
N log lines without touching files or Docker logs. The buffer captures standard
library logging records as plain text in FIFO order while automatically
dropping entries older than seven days.
"""

from __future__ import annotations

import json
import logging
from collections import deque
from datetime import datetime, timedelta
from functools import partial
from typing import List

import structlog

get_logger = structlog.get_logger


_ring: deque[str] | None = None

LOG_RETENTION_DAYS = 7
_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S,%f"


def _extract_timestamp(entry: str) -> datetime | None:
    """Parse the ``logging`` timestamp prefix from a log entry."""

    try:
        date_part, time_part, *_ = entry.split(" ", 2)
    except ValueError:
        return None
    stamp = f"{date_part} {time_part}"
    try:
        return datetime.strptime(stamp, _TIMESTAMP_FORMAT)
    except ValueError:
        return None


class _RingBufferHandler(logging.Handler):
    def __init__(self, capacity: int = 2000) -> None:
        super().__init__()
        self.buffer: deque[str] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        try:
            msg = self.format(record)
        except Exception:  # pragma: no cover - best-effort formatting
            msg = record.getMessage()
        self.buffer.append(msg)


def configure_logging() -> None:
    """Configure stdlib logging and structlog."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # Attach in-memory ring buffer handler (idempotent)
    global _ring
    if _ring is None:
        handler = _RingBufferHandler(capacity=2000)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        root = logging.getLogger()
        root.addHandler(handler)
        _ring = handler.buffer
    if not hasattr(structlog, "configure"):
        return
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.processors.JSONRenderer(
                serializer=partial(json.dumps, ensure_ascii=False)
            ),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


def get_recent_logs(limit: int = 200) -> List[str]:
    """Return up to ``limit`` log lines from the last seven days.

    Entries older than ``LOG_RETENTION_DAYS`` are ignored to keep the
    in-memory buffer small and reduce noise in the admin UI.
    """

    buf = _ring or deque()
    if limit <= 0:
        return []

    cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    selected: list[str] = []

    for entry in reversed(buf):
        ts = _extract_timestamp(entry)
        if ts is not None and ts < cutoff:
            continue
        selected.append(entry)
        if len(selected) >= limit:
            break

    return list(reversed(selected))
