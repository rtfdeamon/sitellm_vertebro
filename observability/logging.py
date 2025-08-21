"""Logging configuration utilities."""

from __future__ import annotations

import logging

import structlog


def configure_logging() -> None:
    """Configure stdlib logging and structlog."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
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
