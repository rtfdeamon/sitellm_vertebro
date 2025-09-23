"""Tests for crawler knowledge filtering helpers."""

from crawler.run_crawl import _normalize_for_hash, _should_skip_text_document


def test_should_skip_navigation_breadcrumbs() -> None:
    text = "Главная / О компании / Контакты"
    assert _should_skip_text_document(text) is True


def test_should_skip_footer_fragment() -> None:
    text = "© 2024 Компания. Все права защищены."
    assert _should_skip_text_document(text) is True


def test_should_keep_meaningful_text() -> None:
    text = "Компания предоставляет услуги автоматизации и поддержку клиентов 24/7."
    assert _should_skip_text_document(text) is False
    # normalization should collapse whitespace
    normalized = _normalize_for_hash("  Компания   предоставляет  услуги   ")
    assert normalized == "компания предоставляет услуги"
