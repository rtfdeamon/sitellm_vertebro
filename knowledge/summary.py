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

IMAGE_CONTEXT_LIMIT = 800
IMAGE_CAPTION_MAX_LEN = 220
IMAGE_CAPTION_PROMPT_TEMPLATE = (
    "Сформулируй лаконичное описание изображения для пересылки в чат Telegram."
    " Используй одно предложение до 220 символов, без эмодзи и перечислений."
    " Укажи, что изображено и его контекст."
    "\nФайл: {name}\nAlt-текст: {alt}\nКонтекст страницы:\n{context}\n\nОписание:"  # noqa: E501
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


def _clean_text_fragment(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _finalize_caption(candidate: str, fallback: str) -> str:
    cleaned = _clean_text_fragment(candidate).strip("\"'«»")
    if not cleaned:
        return fallback
    if len(cleaned) > IMAGE_CAPTION_MAX_LEN:
        trimmed = cleaned[: IMAGE_CAPTION_MAX_LEN - 1].rstrip()
        cleaned = f"{trimmed}…"
    if cleaned and cleaned[-1] not in ".!?…":
        cleaned += "."
    return cleaned


async def generate_image_caption(
    name: str,
    alt_text: str | None,
    page_context: str | None,
    project: Project | None = None,
) -> str:
    """Return a concise caption for an image tuned for Telegram delivery."""

    safe_name = name.strip() or "изображение"
    alt_clean = _clean_text_fragment(alt_text or "")
    context_clean = _clean_text_fragment(page_context or "")
    fallback_parts: list[str] = []
    if alt_clean:
        fallback_parts.append(alt_clean)
    fallback_default = f"Изображение «{safe_name}»."
    fallback = _finalize_caption(" ".join(fallback_parts), fallback_default)
    if context_clean:
        context_excerpt = context_clean[:IMAGE_CONTEXT_LIMIT]
    else:
        context_excerpt = ""

    if not alt_clean and not context_excerpt:
        return fallback

    prompt = IMAGE_CAPTION_PROMPT_TEMPLATE.format(
        name=safe_name,
        alt=alt_clean or "(нет)",
        context=context_excerpt or "(контекст не найден)",
    )

    model_override = None
    if project and isinstance(project.llm_model, str):
        trimmed = project.llm_model.strip()
        if trimmed:
            model_override = trimmed

    chunks: list[str] = []
    try:
        async for token in llm_client.generate(prompt, model=model_override):
            chunks.append(token)
            if len("".join(chunks)) >= IMAGE_CAPTION_MAX_LEN + 80:
                break
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "image_caption_generate_failed",
            image=safe_name,
            error=str(exc),
        )
        return fallback

    candidate = "".join(chunks)
    caption = _finalize_caption(candidate, fallback)
    if len(caption) > 1024:
        caption = caption[:1023].rstrip()
    return caption
