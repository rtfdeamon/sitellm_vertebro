"""Ollama streaming client backed by the cluster manager."""

from __future__ import annotations

from collections.abc import AsyncIterator

from packages.backend.settings import settings
from .ollama_cluster import get_cluster_manager, ModelNotFoundError

DEVICE = "ollama"
MODEL_NAME = getattr(settings, "ollama_model", None) or getattr(settings, "llm_model", None)


async def generate(prompt: str, *, model: str | None = None) -> AsyncIterator[str]:
    manager = get_cluster_manager()
    async for chunk in manager.generate(prompt, model=model or MODEL_NAME):
        yield chunk
