"""Async client for generating text from an external LLM service."""

from __future__ import annotations

import asyncio
import os
import threading
from collections.abc import AsyncIterator
import json
import httpx

try:  # optional heavy deps
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TextIteratorStreamer,
    )
except Exception:  # pragma: no cover - missing deep learning deps
    torch = None
    AutoModelForCausalLM = AutoTokenizer = TextIteratorStreamer = None
from .settings import settings
import structlog

logger = structlog.get_logger(__name__)

_tokenizer: AutoTokenizer | None = None
_model: AutoModelForCausalLM | None = None

USE_GPU = settings.use_gpu
DEVICE = "cuda" if USE_GPU and torch and torch.cuda.is_available() else "cpu"
MODEL_NAME = settings.ollama_model or settings.llm_model
OLLAMA_BASE = settings.ollama_base_url


def _load() -> None:
    """Load model and tokenizer if not yet initialized."""

    global _tokenizer, _model
    if _model is not None:
        return
    if AutoModelForCausalLM is None:
        raise RuntimeError("transformers not installed")
    logger.info("load_model", model=MODEL_NAME, device=DEVICE)
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    _model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
    if torch:
        _model = _model.to(DEVICE)


async def generate(prompt: str) -> AsyncIterator[str]:
    """Yield tokens from the configured LLM backend.

    - If ``OLLAMA_BASE_URL`` is set, stream from Ollama ``/api/generate``.
    - Otherwise, fallback to local transformers with streaming.
    """

    if OLLAMA_BASE:
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
        return

    # Fallback: local transformers runtime
    delay = 0.5
    for attempt in range(4):
        try:
            await asyncio.to_thread(_load)
            streamer = TextIteratorStreamer(_tokenizer, skip_prompt=True)
            inputs = _tokenizer(prompt, return_tensors="pt")
            if torch:
                inputs = inputs.to(DEVICE)

            thread = threading.Thread(
                target=_model.generate,
                kwargs={
                    **inputs,
                    "max_new_tokens": 128,
                    "streamer": streamer,
                },
            )
            thread.start()
            for token in streamer:
                yield token
                await asyncio.sleep(0)
            thread.join()
            logger.info("success", attempt=attempt + 1)
            return
        except Exception as exc:
            logger.warning("generate failed", attempt=attempt + 1, error=str(exc))
            if attempt == 3:
                raise
            await asyncio.sleep(delay)
            delay = min(delay * 2, 4)
