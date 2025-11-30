"""Tests for crawler text normalization helpers."""

from packages.crawler.run_crawl import clean_text


def test_clean_text_removes_spaces_inside_phone_numbers() -> None:
    raw = "Позвоните +7 999 123 45 67 или 8 800 555 35 35 для консультации."

    cleaned = clean_text(raw)

    assert "+79991234567" in cleaned
    assert "88005553535" in cleaned
    # surrounding text remains intact aside from normalization
    assert "Позвоните" in cleaned
    assert "для консультации." in cleaned
