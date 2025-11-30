"""Behavioural checks for source link helpers used by /chat endpoint."""

from apps.api import _collect_source_entries, _question_requests_sources


def test_collect_source_entries_sanitises_and_deduplicates() -> None:
    snippets = [
        {"url": "example.com/content/guide?ref=mail", "name": "Guide"},
        {"attachment": {"url": "example.com/content/guide?ref=mail", "name": "Duplicate"}},
        {"attachment": {"url": "//cdn.example.com/assets/preview.png", "name": "Preview"}},
    ]

    entries = _collect_source_entries(snippets)

    assert len(entries) == 2
    assert entries[0]["name"] == "Guide"
    assert entries[0]["url"] == "https://example.com/content/guide?ref=mail"
    assert entries[1]["name"] == "preview.png"
    assert entries[1]["url"] == "https://cdn.example.com/assets/preview.png"


def test_question_requests_sources_detects_keywords() -> None:
    assert _question_requests_sources("Покажи, пожалуйста, источники ответа") is True
    assert _question_requests_sources("Включи ссылки на материалы") is True
    assert _question_requests_sources("Расскажи подробнее") is False
