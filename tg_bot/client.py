"""Thin async wrapper over the backend chat API."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog

from .config import get_settings
from safety import safety_check

logger = structlog.get_logger(__name__)


async def rag_answer(question: str) -> str:
    """Return answer text from the backend via SSE."""

    settings = get_settings()
    delay = 0.5
    for attempt in range(3):
        try:
            logger.info("request", attempt=attempt + 1)
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                async with client.stream(
                    "POST",
                    str(settings.backend_url),
                    params={"stream": "true"},
                    json={"question": question},
                    headers={"Accept": "text/event-stream"},
                ) as resp:
                    resp.raise_for_status()
                    chunks = []
                    async for line in resp.aiter_lines():
                        if line.startswith("data:"):
                            chunks.append(line[5:].strip())
                    answer = "".join(chunks)
                    if safety_check(answer):
                        raise ValueError("safety")
                    logger.info("success", bytes=len(answer))
                    return answer
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            logger.warning("request failed", attempt=attempt + 1, error=str(exc))
            if attempt == 2:
                raise
            await asyncio.sleep(delay)
            delay = min(delay * 2, 2)
    raise RuntimeError("Unreachable")
