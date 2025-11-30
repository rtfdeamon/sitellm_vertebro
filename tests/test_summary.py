"""Tests for summary helpers that rely on the LLM backend."""

from __future__ import annotations

import pytest

from packages.knowledge import summary


@pytest.mark.asyncio
async def test_generate_image_caption_prefers_alt_text(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_if_called(*args, **kwargs):  # noqa: D401
        raise AssertionError("LLM should not be invoked for image captions")
        yield

    monkeypatch.setattr(summary.llm_client, "generate", fail_if_called)

    result = await summary.generate_image_caption(
        "photo.jpg",
        alt_text="Команда на выставке",
        page_context="Компания рассказала о новой продукции на ежегодной выставке",
        project=None,
    )

    assert result == "Команда на выставке."


@pytest.mark.asyncio
async def test_generate_image_caption_fallback_without_alt(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_if_called(*args, **kwargs):  # noqa: D401
        raise AssertionError("LLM should not be invoked for image captions")
        yield

    monkeypatch.setattr(summary.llm_client, "generate", fail_if_called)

    result = await summary.generate_image_caption(
        "diagram.png",
        alt_text=None,
        page_context="Сводные данные о росте продаж",
        project=None,
    )

    assert result == "Изображение «diagram.png»."
