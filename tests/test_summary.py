"""Tests for summary helpers that rely on the LLM backend."""

from __future__ import annotations

import pytest

from knowledge import summary


@pytest.mark.asyncio
async def test_generate_image_caption_uses_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_prompt: dict[str, str] = {}

    async def fake_generate(prompt: str, model: str | None = None):  # noqa: D401
        captured_prompt["value"] = prompt
        yield "краткое описание"

    monkeypatch.setattr(summary.llm_client, "generate", fake_generate)

    result = await summary.generate_image_caption(
        "photo.jpg",
        alt_text="Команда на выставке",
        page_context="Компания рассказала о новой продукции на ежегодной выставке",
        project=None,
    )

    assert "краткое описание" in result
    assert result.endswith(".")
    assert "Alt-текст" in captured_prompt["value"]


@pytest.mark.asyncio
async def test_generate_image_caption_falls_back_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def failing_generate(prompt: str, model: str | None = None):  # noqa: D401
        raise RuntimeError("boom")
        yield  # pragma: no cover - make this an async generator

    monkeypatch.setattr(summary.llm_client, "generate", failing_generate)

    result = await summary.generate_image_caption(
        "diagram.png",
        alt_text="Диаграмма",
        page_context="Сводные данные о росте продаж",
        project=None,
    )

    assert result.startswith("Диаграмма") or result.startswith("Изображение")
