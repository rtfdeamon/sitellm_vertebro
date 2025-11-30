"""Tests covering book-reading ingestion helpers."""

from __future__ import annotations

from packages.crawler.run_crawl import chunk_reading_blocks, prepare_reading_material


def test_prepare_reading_material_strips_header_footer() -> None:
    html = """
    <html>
      <body>
        <header>Навигация сайта</header>
        <nav>Главная | Контакты</nav>
        <main>
          <h1>Глава 1. Начало</h1>
          <p>Первый абзац романа с длинным вступлением.</p>
          <p>Второй абзац продолжает мысль и развивает сюжет.</p>
        </main>
        <footer>Контакты и юридическая информация</footer>
      </body>
    </html>
    """

    result = prepare_reading_material(html, "https://example.com/book")

    assert "Навигация" not in result["text"]
    assert "Контакты" not in result["text"]
    assert "Первый абзац" in result["text"]
    assert "Второй абзац" in result["text"]
    assert result["title"] == "Глава 1. Начало"
    assert result["images"] == []
    assert len(result["blocks"]) == 3  # heading + two paragraphs


def test_chunk_reading_blocks_preserves_order() -> None:
    blocks = [
        "A" * 500,
        "B" * 520,
        "C" * 480,
        "D" * 120,
    ]

    chunks = chunk_reading_blocks(blocks, max_chars=1000)

    assert len(chunks) == 2
    assert "A" * 100 in chunks[0]
    assert "B" * 100 in chunks[0]
    assert "C" * 100 in chunks[1]
    assert "D" * 50 in chunks[1]
