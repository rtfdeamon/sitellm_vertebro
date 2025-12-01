"""Lightweight package init for retrieval utilities.

Avoid importing heavy optional deps (sentence_transformers) at import time.
Functions ``encode`` and ``get_encoder`` are imported lazily on first use.
"""

from __future__ import annotations

from typing import Any


def encode(text: Any):  # type: ignore[override]
    """Lazily import and delegate to ``embedder.encode``.

    This keeps package import light when embeddings are disabled.
    """
    from .embedder import encode as _encode  # local import

    return _encode(text)


def get_encoder():  # type: ignore[override]
    """Lazily import and delegate to ``embedder.get_encoder``."""
    from .embedder import get_encoder as _get_encoder  # local import

    return _get_encoder()
