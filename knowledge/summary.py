"""Utilities for generating document summaries via the LLM backend."""

from __future__ import annotations

import re
from typing import Optional

import structlog

from backend import llm_client
from models import Project


logger = structlog.get_logger(__name__)

SUMMARY_EXCERPT_LIMIT = 1600
SUMMARY_MAX_LEN = 220
SUMMARY_PROMPT_TEMPLATE = (
    "Составь краткое, информативное описание документа."
    " Используй 1–2 предложения, не более 220 символов и без списков."
    " Укажи назначение и ключевые темы."
    "\nНазвание: {name}\nТекст:\n{body}\n\nОписание:"
)


async def generate_document_summary(
    name: str,
    content: Optional[str],
    project: Project | None = None,
) -> str:
    """Return an LLM-generated synopsis for ``content``.

    Falls back to a generic stub when ``content`` is empty or generation fails.
    """

    safe_name = name.strip() or "документ"
    fallback = f"Документ «{safe_name}»."
    text = (content or "").strip()
    if not text:
        return fallback

    cleaned = re.sub(r"\s+", " ", text)
    excerpt = cleaned[:SUMMARY_EXCERPT_LIMIT]
    prompt = SUMMARY_PROMPT_TEMPLATE.format(name=safe_name, body=excerpt)

    model_override = None
    if project and isinstance(project.llm_model, str):
        trimmed = project.llm_model.strip()
        if trimmed:
            model_override = trimmed

    chunks: list[str] = []
    try:
        async for token in llm_client.generate(prompt, model=model_override):
            chunks.append(token)
            if len("".join(chunks)) >= SUMMARY_MAX_LEN + 80:
                break
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "summary_generate_failed",
            document=safe_name,
            error=str(exc),
        )
        return fallback

    summary = re.sub(r"\s+", " ", "".join(chunks).strip())
    if not summary:
        return fallback
    if len(summary) > SUMMARY_MAX_LEN:
        summary = summary[: SUMMARY_MAX_LEN - 1].rstrip() + "…"
    return summary
