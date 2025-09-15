"""Logging configuration utilities with in-memory ring buffer.

Provides ``get_recent_logs(limit)`` used by the admin UI to display the last
N log lines without touching files or Docker logs. The buffer captures standard
library logging records as plain text in FIFO order.
"""

from __future__ import annotations

import logging
from collections import deque
from typing import List

import structlog


_ring: deque[str] | None = None


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
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


def get_recent_logs(limit: int = 200) -> List[str]:
    """Return up to ``limit`` last log lines captured in memory."""
    buf = _ring or deque()
    if limit <= 0:
        return []
    # Convert to list while respecting order
    if len(buf) <= limit:
        return list(buf)
    # Slice from the right efficiently
    return list(list(buf)[-limit:])
