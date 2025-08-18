import structlog
from backend.cache import cache_query_rewrite

logger = structlog.get_logger(__name__)


def normalize_query(text: str) -> str:
    """Normalize the user query (e.g., strip whitespace and lowercase)."""
    normalized = text.strip().lower()
    logger.debug("normalized query", original=text, normalized=normalized)
    return normalized


@cache_query_rewrite
async def rewrite_query(text: str) -> str:
    """Rewrite the query for better retrieval using an LLM (LLM#2)."""
    # TODO: Use an LLM to rephrase the query. For now, return the text unchanged.
    return text
