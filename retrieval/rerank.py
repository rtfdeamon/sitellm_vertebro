"""Cross-encoder based document reranking."""

from __future__ import annotations

from typing import List

from sentence_transformers import CrossEncoder
import structlog

logger = structlog.get_logger(__name__)

from .search import Doc


_MODEL_NAME = "DiTy/cross-encoder-russian-msmarco"
_reranker: CrossEncoder | None = None


def get_reranker() -> CrossEncoder:
    """Return cached ``CrossEncoder`` instance."""
    global _reranker
    if _reranker is None:
        logger.info("loading reranker", model=_MODEL_NAME)
        _reranker = CrossEncoder(_MODEL_NAME)
    return _reranker


def rerank(query: str, docs: List[Doc], top: int = 10) -> List[Doc]:
    """Return ``docs`` ordered by cross-encoder score."""
    if len(docs) <= top:
        return docs

    model = get_reranker()
    pairs = [(query, doc.payload.get("text", "") if doc.payload else "") for doc in docs]
    scores = model.predict(pairs)

    for doc, score in zip(docs, scores):
        setattr(doc, "cross_score", float(score))

    docs_sorted = sorted(docs, key=lambda d: getattr(d, "cross_score"), reverse=True)
    logger.info("reranked", count=len(docs_sorted))
    return docs_sorted[:top]
