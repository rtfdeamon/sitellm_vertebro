"""Async client for generating text from an external LLM service."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator

import aiohttp
import structlog

logger = structlog.get_logger(__name__)


async def generate(prompt: str) -> AsyncIterator[str]:
    """Stream model output for ``prompt`` using Server-Sent Events.

    The LLM URL is taken from the ``LLM_URL`` environment variable or defaults
    to ``http://localhost:8000``. The request body is ``{"prompt": prompt,
    "stream": true}``. Tokens are yielded for each ``data:`` line in the
    response. Up to four attempts are made with exponential backoff between
    0.5 and 4 seconds.
    """

    url = os.getenv("LLM_URL", "http://localhost:8000")
    payload = {"prompt": prompt, "stream": True}

    delay = 0.5
    for attempt in range(4):
        try:
            logger.info("request", attempt=attempt + 1)
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    response.raise_for_status()
                    async for raw in response.content:
                        line = raw.decode().strip()
                        if line.startswith("data:"):
                            yield line[5:].strip()
                    logger.info("success", attempt=attempt + 1)
                    return
        except Exception as exc:
            logger.warning("request failed", attempt=attempt + 1, error=str(exc))
            if attempt == 3:
                raise
            await asyncio.sleep(delay)
            delay = min(delay * 2, 4)
