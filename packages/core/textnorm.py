"""Basic text normalization and rewriting utilities."""

import structlog

from packages.backend import llm_client
from packages.backend.cache import cache_query_rewrite

logger = structlog.get_logger(__name__)


def normalize_query(query: str) -> str:
    """Return a normalized version of ``query``.

    Currently this is a placeholder that returns the query unchanged.
    """
    return query


@cache_query_rewrite
async def rewrite_query(query: str) -> str:
    """Return an optional rewrite of ``query`` using an auxiliary model.

    Uses :mod:`backend.llm_client` to generate a paraphrased version of the
    provided query.  If generation fails or yields an empty result, the
    original ``query`` is returned unchanged.
    """

    prompt = f"Rewrite the following query in other words: {query}"
    try:
        parts: list[str] = []
        async for token in llm_client.generate(prompt):
            parts.append(token)
        rewritten = "".join(parts).strip()
        return rewritten or query
    except Exception:  # pragma: no cover - network/llm issues
        logger.exception("rewrite failed")
        return query
