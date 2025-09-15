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
    async with httpx.AsyncClient(timeout=None) as client:
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
                    break
