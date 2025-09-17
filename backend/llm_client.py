"""Ollama streaming client.

Provides ``generate(prompt)`` that yields tokens from an Ollama instance
configured via environment (``OLLAMA_BASE_URL`` and ``OLLAMA_MODEL``).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import httpx
import structlog
from .settings import settings

logger = structlog.get_logger(__name__)

MODEL_NAME = getattr(settings, "ollama_model", None) or getattr(settings, "llm_model", None)
OLLAMA_BASE = getattr(settings, "ollama_base_url", None)
DEVICE = "ollama"


RETRY_ATTEMPTS = 3
RETRY_DELAY = 0.2


def _http_client_factory(**kwargs):
    return httpx.AsyncClient(**kwargs)


async def generate(prompt: str) -> AsyncIterator[str]:
    """Yield tokens from the configured LLM backend.

    - If ``OLLAMA_BASE_URL`` is set, stream from Ollama ``/api/generate``.
    - Otherwise, fallback to local transformers with streaming.
    """

    if not OLLAMA_BASE:
        raise RuntimeError("OLLAMA_BASE_URL is not configured")

    url = f"{OLLAMA_BASE.rstrip('/')}/api/generate"
    payload = {"model": MODEL_NAME, "prompt": prompt, "stream": True}
    logger.info("ollama_generate", url=url, model=MODEL_NAME)
    last_exc: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            async with _http_client_factory(timeout=None) as client:
                async with client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except Exception:
                            continue
                        token = data.get("response")
                        if token:
                            yield token
                            await asyncio.sleep(0)
                        if data.get("done"):
                            return
            return
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "ollama_stream_failed", attempt=attempt + 1, error=str(exc)
            )
            if attempt < RETRY_ATTEMPTS - 1:
                await asyncio.sleep(RETRY_DELAY)
            else:
                raise

    if last_exc:
        raise last_exc
