"""Hybrid search implementation with Reciprocal Rank Fusion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict


@dataclass
class Doc:
    """Document returned by the search."""

    id: str
    payload: dict | None = None
    score: float = 0.0


# Qdrant client instance should be assigned by the application.
qdrant = None  # type: ignore


def hybrid_search(query: str, k: int = 10) -> List[Doc]:
    """Return top ``k`` documents ranked by RRF."""

    dense_scores = qdrant.similarity(query, top=50, method="dense")
    bm25_scores = qdrant.similarity(query, top=50, method="bm25")

    rrf_const = 60
    results: Dict[str, Doc] = {}

    for rank, doc in enumerate(dense_scores, 1):
        item = results.setdefault(doc.id, Doc(doc.id, getattr(doc, "payload", None)))
        item.score += 1 / (rrf_const + rank)

    for rank, doc in enumerate(bm25_scores, 1):
        item = results.setdefault(doc.id, Doc(doc.id, getattr(doc, "payload", None)))
        item.score += 1 / (rrf_const + rank)

    docs = sorted(results.values(), key=lambda d: d.score, reverse=True)
    return docs[:k]
