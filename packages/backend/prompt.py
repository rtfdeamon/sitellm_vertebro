"""Utility to build prompts for the language model."""

from __future__ import annotations

from typing import List

from retrieval.search import Doc
import structlog

logger = structlog.get_logger(__name__)


_MAX_CHARS = 300
_SENTENCE_ENDS = ".!?"


def _truncate(text: str, limit: int = _MAX_CHARS) -> str:
    """Truncate ``text`` to ``limit`` characters without breaking sentences."""
    if len(text) <= limit:
        return text
    truncated = text[:limit]
    last = max((truncated.rfind(c) for c in _SENTENCE_ENDS), default=-1)
    if last != -1:
        return truncated[: last + 1]
    return truncated


def build_prompt(question: str, docs: List[Doc]) -> str:
    """Return a formatted prompt using top scored documents."""
    top_docs = sorted(docs, key=lambda d: d.score, reverse=True)[:3]
    fragments = []
    for idx, doc in enumerate(top_docs, 1):
        text = ""
        if doc.payload:
            if isinstance(doc.payload, dict):
                text = str(doc.payload.get("text", ""))
            elif isinstance(doc.payload, str):
                text = doc.payload
        frag = _truncate(text)
        fragments.append(f"Документ #{idx}:\n{frag}")
    docs_block = "\n\n".join(fragments)
    prompt = (
        "SYSTEM: Используй ТОЛЬКО данные ниже для ответа."\
        f"\n\n{docs_block}\n\nQUESTION: {question}\nANSWER:"
    )
    logger.debug("prompt built", length=len(prompt))
    return prompt
