"""Basic text normalization and rewriting utilities."""

import structlog

logger = structlog.get_logger(__name__)


def normalize_query(query: str) -> str:
    """Return a normalized version of ``query``.

    Currently this is a placeholder that returns the query unchanged.
    """
    return query


async def rewrite_query(query: str) -> str:
    """Return an optional rewrite of ``query`` using an auxiliary model.

    This default implementation simply echoes the input query.
    """
    return query
