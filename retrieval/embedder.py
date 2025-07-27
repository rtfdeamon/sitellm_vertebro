"""SentenceTransformers embedder with simple caching."""

from __future__ import annotations

from functools import lru_cache
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer


_MODEL_NAME = "sentence-transformers/sbert_large_nlu_ru"
_encoder: SentenceTransformer | None = None


def get_encoder() -> SentenceTransformer:
    """Return cached ``SentenceTransformer`` instance."""
    global _encoder
    if _encoder is None:
        _encoder = SentenceTransformer(_MODEL_NAME)
    return _encoder


@lru_cache(maxsize=128)
def _encode_cached(text: str) -> np.ndarray:
    """Return the embedding vector for ``text`` using cached encoder."""
    return get_encoder().encode(text)


def encode(text: str | List[str]) -> np.ndarray:
    """Encode ``text`` into a numpy array."""
    if isinstance(text, str):
        return _encode_cached(text)
    vectors = [_encode_cached(t) for t in text]
    return np.vstack(vectors)
