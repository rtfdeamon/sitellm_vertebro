"""Tests for attachment handling in API helpers."""

from tests.test_llm_ask import api as api_mod


def test_collect_attachments_preserves_description():
    attachment = {
        "name": "Типовой договор",
        "url": "https://example.com/doc.pdf",
        "content_type": "application/pdf",
        "description": "Типовой договор поставки",
    }
    result = api_mod._collect_attachments([
        {"id": "1", "name": "doc.pdf", "text": "", "attachment": attachment}
    ])
    assert result == [attachment]


def test_compose_knowledge_message_uses_attachment_description():
    snippet = {
        "id": "2",
        "name": "Фото лицензии",
        "text": "Фото лицензии",
        "attachment": {
            "name": "license.jpg",
            "url": "https://example.com/license.jpg",
            "content_type": "image/jpeg",
            "description": "Фото лицензии",
        },
    }
    message = api_mod._compose_knowledge_message([snippet])
    assert "Фото лицензии" in message
    assert "license.jpg" in message
    assert "Не отправляй файлы" in message


def test_detect_attachment_consent_positive_cases():
    assert api_mod._detect_attachment_consent("Да") is True
    assert api_mod._detect_attachment_consent("да, отправь документ") is True
    assert api_mod._detect_attachment_consent("Отправь, пожалуйста") is True


def test_detect_attachment_consent_negative_cases():
    assert api_mod._detect_attachment_consent("да нет") is False
    assert api_mod._detect_attachment_consent("не нужно") is False
    assert api_mod._detect_attachment_consent("Документ готов?") is False
