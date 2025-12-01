"""Hybrid search implementation with Reciprocal Rank Fusion."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List
import asyncio
import hashlib, json
import structlog

from packages.backend.cache import _get_redis

logger = structlog.get_logger(__name__)


@dataclass
class Doc:
    """Document returned by the search."""

    id: str
    payload: dict | None = None
    score: float = 0.0


# Qdrant client instance should be assigned by the application.
qdrant = None  # type: ignore


async def hybrid_search(query: str, k: int = 10) -> List[Doc]:
    """Return top ``k`` documents ranked by RRF."""

    logger.info("hybrid search", query=query)
    if qdrant is None:
        raise RuntimeError("Qdrant not configured")

    # Run blocking Qdrant calls in a separate thread
    dense_scores, bm25_scores = await asyncio.gather(
        asyncio.to_thread(qdrant.similarity, query, top=50, method="dense"),
        asyncio.to_thread(qdrant.similarity, query, top=50, method="bm25"),
    )

    rrf_const = 60
    results: Dict[str, Doc] = {}

    for rank, doc in enumerate(dense_scores, 1):
        item = results.setdefault(doc.id, Doc(doc.id, getattr(doc, "payload", None)))
        item.score += 1 / (rrf_const + rank)

    for rank, doc in enumerate(bm25_scores, 1):
        item = results.setdefault(doc.id, Doc(doc.id, getattr(doc, "payload", None)))
        item.score += 1 / (rrf_const + rank)

    docs = sorted(results.values(), key=lambda d: d.score, reverse=True)
    logger.info("hybrid search done", returned=len(docs))
    return docs[:k]


async def vector_search(query: str, k: int = 50) -> List[Doc]:
    """Perform dense vector search for ``query`` and return top ``k`` docs (cached)."""

    logger.info("vector search", query=query)
    if qdrant is None:
        raise RuntimeError("Qdrant not configured")
    key = "vector:" + hashlib.sha1(query.lower().encode()).hexdigest()
    redis = _get_redis()
    cached = await redis.get(key)
    if cached is not None:
        logger.info("cache hit", key=key)
        docs_list = json.loads(cached.decode())
        docs = [Doc(**d) for d in docs_list]
    else:
        # ``qdrant.similarity`` is a blocking call; run it in a thread so the
        # event loop stays responsive. In production consider using an
        # asynchronous Qdrant client or a dedicated thread pool.
        results = await asyncio.to_thread(
            qdrant.similarity, query, top=k, method="dense"
        )
        docs = [
            Doc(doc.id, getattr(doc, "payload", None), getattr(doc, "score", 0.0))
            for doc in results
        ]
        docs_list = [asdict(doc) for doc in docs]
        await redis.setex(key, 86400, json.dumps(docs_list, ensure_ascii=False))
        logger.info("cache store", key=key)
    logger.info("vector search done", returned=len(docs))
    return docs
