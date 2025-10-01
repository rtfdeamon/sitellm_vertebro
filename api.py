"""FastAPI routers for interacting with the LLM and crawler."""

from __future__ import annotations

import json
from pathlib import Path
import copy
import subprocess
import sys
import os
import signal
import time
import re
import urllib.parse as urlparse
from typing import Any, Sequence
from uuid import uuid4

from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
try:
    from fastapi import BackgroundTasks
except ImportError:  # pragma: no cover - fallback for test stubs
    class BackgroundTasks:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass
from fastapi.responses import ORJSONResponse, StreamingResponse
from starlette.routing import NoMatchFound
import asyncio

import structlog

from backend import llm_client
from backend.cache import _get_redis
from backend.settings import settings as backend_settings
from backend.ollama import (
    list_installed_models,
    ollama_available,
    popular_models_with_size,
)
from retrieval import search as retrieval_search
from crawler.run_crawl import (
    clear_crawler_state,
    deduplicate_recent_urls,
    get_crawler_note,
)
from bson import ObjectId

from worker import voice_train_model

try:  # pragma: no cover - optional during unit tests where worker is stubbed
    from worker import get_mongo_client as worker_mongo_client, settings as worker_settings
except Exception:  # noqa: BLE001 - fallback for lightweight worker stubs
    worker_mongo_client = None  # type: ignore[assignment]
    worker_settings = None  # type: ignore[assignment]

from models import (
    Attachment,
    Document,
    LLMRequest,
    LLMResponse,
    Project,
    ReadingPage,
    RoleEnum,
    VoiceSample,
    VoiceTrainingJob,
    VoiceTrainingStatus,
)
from mongo import MongoClient, NotFound
from pydantic import BaseModel, ConfigDict

from core.status import status_dict
from settings import MongoSettings, get_settings as get_app_settings
from core.build import get_build_info
from integrations.bitrix import BitrixError, call_bitrix_webhook
from integrations.mail import (
    MailConnectorError,
    MailSettings,
    MailMessagePayload,
    fetch_recent_messages,
    project_mail_settings,
    send_mail,
    summarize_messages,
)

logger = structlog.get_logger(__name__)
app_settings = get_app_settings()

EMOTION_ON_PROMPT = (
    "Отвечай в тёплом, дружелюбном тоне, добавляй уместные эмоции и подходящие эмодзи (не более двух в ответе),"
    " чтобы поддерживать живой диалог и эмпатию."
)
EMOTION_OFF_PROMPT = (
    "Отвечай в спокойном, нейтральном тоне и не используй эмодзи либо эмоциональные высказывания."
)

READING_MODE_PROMPT = (
    "Режим чтения книг активирован. Делись текстом источника последовательными страницами примерно по 1200–1500 символов без пропуска разделов."
    " После каждой страницы делай короткий вывод и ожидай команду пользователя (например, 'далее' или вопрос)."
    " Если пользователь просит перейти к другой части, вежливо уточняй нужную страницу или главу."
)

READING_COLLECTION_NAME = os.getenv("MONGO_READING_COLLECTION", "reading_pages")
READING_PAGE_MAX_LIMIT = 20
READING_PREVIEW_LIMIT = min(5, READING_PAGE_MAX_LIMIT)
READING_PREVIEW_MAX_SEGMENTS_PER_PAGE = 12
READING_PREVIEW_MAX_IMAGES_PER_PAGE = 6
READING_PREVIEW_SEGMENT_CHAR_LIMIT = 1800
READING_PREVIEW_TEXT_CHAR_LIMIT = 3500
READING_PREVIEW_TOTAL_CHAR_LIMIT = 20000
READING_PREVIEW_HTML_CHAR_LIMIT = 5000

try:  # pragma: no cover - optional when Celery/kombu unavailable in tests
    from celery.exceptions import CeleryError
except Exception:  # noqa: BLE001 - fallback for minimal test stubs
    class CeleryError(Exception):  # type: ignore[override]
        """Fallback Celery error type used when Celery is not installed."""


try:  # pragma: no cover - optional when kombu is not installed
    from kombu.exceptions import OperationalError as KombuOperationalError
except Exception:  # noqa: BLE001 - fallback for minimal test stubs
    class KombuOperationalError(Exception):  # type: ignore[override]
        """Fallback kombu operational error when kombu is absent."""


VOICE_ALLOWED_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/flac",
    "audio/x-flac",
    "audio/ogg",
    "audio/webm",
    "audio/aac",
    "audio/m4a",
}
VOICE_MAX_SAMPLE_BYTES = int(os.getenv("VOICE_SAMPLE_MAX_BYTES", str(25 * 1024 * 1024)))
VOICE_MIN_SAMPLE_COUNT = int(os.getenv("VOICE_MIN_SAMPLE_COUNT", "3"))
VOICE_QUEUE_ERRORS: tuple[type[BaseException], ...] = (
    CeleryError,
    KombuOperationalError,
    ConnectionError,
    TimeoutError,
)
VOICE_JOB_STALE_TIMEOUT = float(os.getenv("VOICE_JOB_STALE_TIMEOUT", "5"))
VOICE_JOB_STALE_TIMEOUT = float(os.getenv("VOICE_JOB_STALE_TIMEOUT", "20"))

SOURCE_REQUEST_KEYWORDS = (
    "источ",
    "ссыл",
    "source",
    "link",
)
MAX_SOURCE_ENTRIES = 6


def _normalize_project(value: str | None) -> str | None:
    candidate = (value or "").strip().lower()
    if candidate:
        return candidate
    fallback = backend_settings.project_name or backend_settings.domain
    if fallback:
        return fallback.strip().lower() or None
    return None


def _get_mongo_client(request: Request) -> MongoClient:
    mongo_client: MongoClient | None = getattr(request.state, "mongo", None)
    if mongo_client is None:
        mongo_client = getattr(request.app.state, "mongo", None)
        if mongo_client is None:
            raise HTTPException(status_code=503, detail="mongo_unavailable")
        request.state.mongo = mongo_client
    return mongo_client


def _resolve_session_identifiers(
    request: Request,
    project: str | None,
    session_id: str | None,
) -> tuple[str | None, str, str, bool]:
    """Return normalized project, composite session key and base id."""

    project_name = _normalize_project(project)
    candidates = (
        session_id,
        request.headers.get("X-Session-Id"),
        request.headers.get("X-Client-Session"),
        request.cookies.get("chat_session"),
    )
    base_id: str | None = None
    for candidate in candidates:
        if isinstance(candidate, str):
            trimmed = candidate.strip().lower()
            if trimmed:
                base_id = trimmed
                break
    generated = False
    if not base_id:
        base_id = uuid4().hex
        generated = True
    session_key = f"{project_name}::{base_id}" if project_name else base_id
    return project_name, session_key, base_id, generated


_KNOWLEDGE_SNIPPET_CHARS = 640
_MAX_DIALOG_TURNS = int(os.getenv("MAX_DIALOG_TURNS", "5"))
_MAX_DIALOG_CHARS = int(os.getenv("MAX_DIALOG_CHARS", "8000"))
_HISTORY_SUMMARY_MAX_CHARS = int(os.getenv("HISTORY_SUMMARY_MAX_CHARS", "900"))
_HISTORY_SUMMARY_PREFIX = "Earlier conversation summary:"  # keep neutral for multilingual chats
_VOICE_MAX_TURNS = 3
_VOICE_KNOWLEDGE_LIMIT = 2
_VOICE_KNOWLEDGE_CHARS = 800
_ATTACHMENT_PENDING_TTL = 10 * 60  # seconds
_ATTACHMENT_CONSENT_SIMPLE = {
    "да",
    "давай",
    "ок",
    "окей",
    "хочу",
    "угу",
    "ага",
    "yes",
    "y",
}
_ATTACHMENT_CONSENT_KEYWORDS = {
    "отправь",
    "пришли",
    "скинь",
    "присылай",
    "загрузи",
    "покажи",
}
_ATTACHMENT_NEGATIONS = {
    "нет",
    "не",
    "ненадо",
    "no",
    "неа",
}

_KNOWN_KNOWLEDGE_SOURCES = ("qa", "qdrant", "mongo")
_DEFAULT_KNOWLEDGE_PRIORITY = ["qa", "qdrant", "mongo"]
BITRIX_COMMAND_PROMPT = (
    "Ты помощник интеграции с Bitrix24. Анализируешь сообщение пользователя и решаешь, нужна ли задача.\n"
    "Если нужно создать задачу, верни JSON вида:\n"
    "{\"action\": \"create_task\", \"title\": \"...\", \n"
    " \"description\": \"...\", \"responsible_id\": 123, \"deadline\": \"2024-12-31T18:00:00\"}.\n"
    "Можно опустить responsible_id или deadline, если их нет.\n"
    "Если достаточно другого метода Bitrix (например crm.lead.list), верни\n"
    "{\"action\": \"call\", \"method\": \"crm.lead.list\", \"params\": {...}}.\n"
    "Если действия не требуется — {\"action\": \"skip\"}.\n"
    "Всегда отвечай строго JSON без пояснений.\n\n"
    "Сообщение пользователя: {question}\n"
)
BITRIX_RESPONSE_PREVIEW_LIMIT = 2400
BITRIX_PARAMS_PREVIEW_LIMIT = 800
MAIL_COMMAND_PROMPT = (
    "Ты ассистент по работе с электронной почтой. Анализируешь сообщение пользователя и выбираешь подходящее действие.\n"
    "Если нужно подготовить письмо, верни JSON вида:\n"
    "{\"action\": \"send_email\", \"to\": [\"user@example.com\"], \"cc\": [], \"bcc\": [],\n"
    " \"subject\": \"Тема\", \"body\": \"Текст письма\", \"reply_to\": null, \"signature\": true}.\n"
    "Если нужно показать свежие письма — верни {\"action\": \"list_inbox\", \"unread_only\": true, \"limit\": 5}.\n"
    "Если действие не требуется — {\"action\": \"skip\"}.\n"
    "Всегда отвечай строго JSON без пояснений или комментариев.\n\n"
    "Сообщение пользователя: {question}\n"
)
MAIL_BODY_PREVIEW_LIMIT = 800
MAIL_PLAN_TTL = 15 * 60


llm_router = APIRouter(
    prefix="/llm",
    tags=["llm"],
    responses={
        200: {"description": "LLM response"},
        404: {"description": "Can't find specified sessionId"},
        500: {"description": "Internal Server Error"},
    },
)

crawler_router = APIRouter(
    prefix="/crawler",
    tags=["crawler"],
)

reading_router = APIRouter(
    prefix="/reading",
    tags=["reading"],
)

voice_router = APIRouter(
    prefix="/voice",
    tags=["voice"],
)


def _normalize_priority_order(order: list[str] | None) -> list[str]:
    sanitized: list[str] = []
    if order:
        for item in order:
            if not isinstance(item, str):
                continue
            candidate = item.strip().lower()
            if candidate and candidate in _KNOWN_KNOWLEDGE_SOURCES and candidate not in sanitized:
                sanitized.append(candidate)
    for fallback in _DEFAULT_KNOWLEDGE_PRIORITY:
        if fallback not in sanitized:
            sanitized.append(fallback)
    return sanitized


def _extract_json_object(raw: str) -> dict[str, Any] | None:
    candidate = (raw or "").strip()
    if not candidate:
        return None
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        snippet = candidate[start : end + 1]
        try:
            parsed = json.loads(snippet)
        except json.JSONDecodeError:
            return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _json_preview(payload: Any, *, limit: int) -> str:
    try:
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        text = str(payload)
    text = text.strip()
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


class BitrixPlanAction(BaseModel):
    plan_id: str
    project: str | None = None
    session_id: str | None = None


class MailPlanAction(BaseModel):
    plan_id: str
    project: str | None = None
    session_id: str | None = None


class ReadingPagesResponse(BaseModel):
    pages: list[ReadingPage]
    total: int
    limit: int
    offset: int
    has_more: bool

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pages": [
                    {
                        "url": "https://example.com/books/war-and-peace/chapter-1",
                        "order": 1,
                        "title": "Глава 1",
                        "segmentCount": 2,
                        "imageCount": 1,
                        "segments": [
                            {
                                "index": 0,
                                "chars": 1250,
                                "summary": "Пьер знакомится с высшим светом Петербурга.",
                                "text": "Начало романа…",
                            }
                        ],
                        "images": [
                            {
                                "url": "https://example.com/static/ch1.jpg",
                                "fileId": "6640dcf86c6c8e8b2ef9be12",
                            }
                        ],
                    }
                ],
                "total": 8,
                "limit": 5,
                "offset": 0,
                "has_more": True,
            }
        }
    )


class VoiceSamplesResponse(BaseModel):
    samples: list[VoiceSample]


class VoiceJobsResponse(BaseModel):
    jobs: list[VoiceTrainingJob]
def _log_debug_event(message: str, **kwargs) -> None:
    if app_settings.debug:
        logger.info(message, **kwargs)
    else:
        logger.debug(message, **kwargs)


def _truncate_text(text: str, limit: int = _KNOWLEDGE_SNIPPET_CHARS) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    truncated = cleaned[:limit].rsplit(" ", 1)[0].strip()
    if not truncated:
        truncated = cleaned[:limit]
    return truncated.rstrip(". ") + "…"


def _extract_payload_text(payload: Any) -> str:
    if not payload:
        return ""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        for key in ("text", "content", "body", "chunk"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
        meta = payload.get("metadata")
        if isinstance(meta, dict):
            return _extract_payload_text(meta)
    return ""


def _normalize_consent_text(value: str) -> str:
    normalized = re.sub(r"[^0-9a-zа-яё\s]+", " ", value.strip().lower())
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _detect_attachment_consent(text: str) -> bool:
    normalized = _normalize_consent_text(text)
    if not normalized or len(normalized) > 120:
        return False
    tokens = normalized.split()
    if not tokens:
        return False
    if any(token in _ATTACHMENT_NEGATIONS for token in tokens):
        return False
    if normalized in _ATTACHMENT_CONSENT_SIMPLE:
        return True
    if normalized.startswith("да ") and len(tokens) <= 4:
        return True
    for keyword in _ATTACHMENT_CONSENT_KEYWORDS:
        if keyword in normalized:
            return True
    return False


def _ensure_attachment_store(app) -> tuple[dict[str, Any], asyncio.Lock]:
    store = getattr(app.state, "pending_attachments", None)
    lock = getattr(app.state, "pending_attachments_lock", None)
    if store is None or lock is None:
        store = {}
        lock = asyncio.Lock()
        app.state.pending_attachments = store
        app.state.pending_attachments_lock = lock
    return store, lock


async def _prune_pending_attachments(app, now: float) -> None:
    store, lock = _ensure_attachment_store(app)
    async with lock:
        expired_keys = [
            key
            for key, payload in store.items()
            if now - float(payload.get("ts", 0.0) or 0.0) > _ATTACHMENT_PENDING_TTL
        ]
        for key in expired_keys:
            store.pop(key, None)


async def _set_pending_attachments(
    app,
    session_key: str | None,
    attachments: list[dict[str, Any]],
    snippets: list[dict[str, Any]],
    now: float,
) -> None:
    if not session_key:
        return
    store, lock = _ensure_attachment_store(app)
    async with lock:
        if attachments:
            store[session_key] = {
                "attachments": copy.deepcopy(attachments),
                "snippets": copy.deepcopy(snippets),
                "ts": now,
            }
        else:
            store.pop(session_key, None)


async def _pop_pending_attachments(app, session_key: str | None) -> dict[str, Any] | None:
    if not session_key:
        return None
    store, lock = _ensure_attachment_store(app)
    async with lock:
        return store.pop(session_key, None)


def _extract_payload_name(payload: Any, default: str | None = None) -> str | None:
    if isinstance(payload, dict):
        for key in ("title", "name", "source", "document", "file_name"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        url = payload.get("url")
        if isinstance(url, str) and url.strip():
            return url.strip()
    return default


def _extract_payload_url(payload: Any) -> str | None:
    if isinstance(payload, dict):
        url = payload.get("url")
        if isinstance(url, str) and url.strip():
            return url.strip()
    return None


def _is_attachment_doc(meta: dict[str, Any]) -> bool:
    content_type = str(meta.get("content_type") or "").lower()
    if not content_type:
        return False
    return not content_type.startswith("text/")


def _build_download_url(request: Request, file_id: str) -> str:
    try:
        return str(request.url_for("admin_download_document", file_id=file_id))
    except NoMatchFound:
        base = str(request.base_url).rstrip("/")
        return f"{base}/api/v1/admin/knowledge/documents/{file_id}"


def _truncate_text(value: Any, limit: int) -> str | None:
    if limit <= 0:
        return None
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) <= limit:
        return cleaned
    slice_limit = max(1, limit - 3)
    truncated = cleaned[:slice_limit].rstrip()
    if not truncated:
        truncated = cleaned[:slice_limit]
    return f"{truncated}..."


def _serialize_reading_pages(
    request: Request,
    pages: Sequence[ReadingPage],
) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    remaining_chars = READING_PREVIEW_TOTAL_CHAR_LIMIT
    for page in pages:
        if remaining_chars <= 0:
            break

        payload = page.model_dump(by_alias=True)

        raw_segments = payload.get("segments") if isinstance(payload.get("segments"), list) else []
        segments_payload: list[dict[str, Any]] = []
        if raw_segments:
            for raw_segment in raw_segments:
                if remaining_chars <= 0:
                    break
                if len(segments_payload) >= READING_PREVIEW_MAX_SEGMENTS_PER_PAGE:
                    break
                if not isinstance(raw_segment, dict):
                    continue
                text_value = raw_segment.get("text")
                max_chars = min(READING_PREVIEW_SEGMENT_CHAR_LIMIT, remaining_chars)
                truncated_text = _truncate_text(text_value, max_chars)
                if not truncated_text:
                    continue
                segment_entry = dict(raw_segment)
                segment_entry["text"] = truncated_text
                segment_entry["chars"] = len(truncated_text)
                segments_payload.append(segment_entry)
                remaining_chars = max(0, remaining_chars - len(truncated_text))
            payload["segments"] = segments_payload
        else:
            payload["segments"] = []

        if segments_payload:
            payload.pop("text", None)
        else:
            max_chars = min(READING_PREVIEW_TEXT_CHAR_LIMIT, remaining_chars)
            truncated_page_text = _truncate_text(payload.get("text"), max_chars)
            if truncated_page_text:
                payload["text"] = truncated_page_text
                remaining_chars = max(0, remaining_chars - len(truncated_page_text))
            else:
                payload.pop("text", None)

        html_value = payload.get("html")
        if html_value:
            truncated_html = _truncate_text(html_value, READING_PREVIEW_HTML_CHAR_LIMIT)
            if truncated_html:
                payload["html"] = truncated_html
                remaining_chars = max(0, remaining_chars - len(truncated_html))
            else:
                payload.pop("html", None)

        images_payload: list[dict[str, Any]] = []
        for image in page.images:
            if len(images_payload) >= READING_PREVIEW_MAX_IMAGES_PER_PAGE:
                break
            source_url = getattr(image, "url", None)
            file_id = getattr(image, "file_id", None)
            image_entry: dict[str, Any] = {}
            if file_id:
                image_entry["url"] = _build_download_url(request, file_id)
                if source_url:
                    image_entry["source"] = source_url
            elif source_url:
                image_entry["url"] = source_url
                image_entry["source"] = source_url
            else:
                continue
            caption = getattr(image, "caption", None)
            if caption:
                truncated_caption = _truncate_text(caption, 240)
                if truncated_caption:
                    image_entry["caption"] = truncated_caption
            images_payload.append(image_entry)
        payload["images"] = images_payload
        payload["segmentCount"] = len(segments_payload)
        payload["imageCount"] = len(images_payload)

        serialized.append(payload)
    return serialized


def _collect_reading_items(snippets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for snippet in snippets:
        reading = snippet.get("reading")
        if not isinstance(reading, dict):
            continue
        pages = reading.get("pages")
        if not pages:
            continue
        entry = {
            "id": snippet.get("id"),
            "name": snippet.get("name"),
            "source": snippet.get("source"),
            **{k: v for k, v in reading.items() if k != "pages"},
            "pages": pages,
        }
        items.append(entry)
    return items[:3]


def _question_requests_sources(question: str) -> bool:
    normalized = (question or "").strip().lower()
    if not normalized:
        return False
    return any(keyword in normalized for keyword in SOURCE_REQUEST_KEYWORDS)


def _sanitize_source_url(raw: str | None) -> str | None:
    if not raw or not isinstance(raw, str):
        return None
    candidate = raw.strip()
    if not candidate:
        return None
    if candidate.startswith("//"):
        candidate = f"https:{candidate}"
    try:
        parsed = urlparse.urlsplit(candidate)
    except ValueError:
        return candidate
    if not parsed.scheme:
        candidate = f"https://{candidate}"
        try:
            parsed = urlparse.urlsplit(candidate)
        except ValueError:
            return candidate
    if parsed.scheme not in {"http", "https"}:
        return candidate
    if not parsed.netloc:
        return candidate
    path = parsed.path or "/"
    return urlparse.urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))


def _derive_source_label(name: str | None, url: str) -> str:
    """Pick a friendly label, favouring URL slugs when names are generic."""

    slug: str | None = None
    host = ""
    try:
        parsed = urlparse.urlsplit(url)
    except ValueError:
        parsed = None
    if parsed:
        host = parsed.netloc or ""
        path = parsed.path or ""
        if path and path not in {"", "/"}:
            slug_candidate = urlparse.unquote(path.rstrip("/").split("/")[-1])
            if slug_candidate:
                slug = slug_candidate

    if isinstance(name, str):
        stripped = name.strip()
        if stripped:
            # Prefer the URL slug when it contains a rich filename (e.g. ext)
            # and the provided label looks like a generic title.
            if slug and "." in slug and "." not in stripped:
                return slug
            return stripped

    if slug:
        return slug
    if host:
        return host
    return url


def _collect_source_entries(snippets: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not snippets:
        return []
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in snippets:
        candidate_url = item.get("url")
        attachment = item.get("attachment") if isinstance(item.get("attachment"), dict) else None
        if not candidate_url and attachment:
            candidate_url = attachment.get("url")
        normalized_url = _sanitize_source_url(candidate_url)
        if not normalized_url or normalized_url in seen:
            continue
        label_source = attachment.get("name") if attachment else item.get("name")
        label = _derive_source_label(label_source if isinstance(label_source, str) else None, normalized_url)
        entries.append({"name": label, "url": normalized_url})
        seen.add(normalized_url)
        if len(entries) >= MAX_SOURCE_ENTRIES:
            break
    return entries


def _collect_attachments(snippets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    attachments: list[dict[str, Any]] = []
    for item in snippets:
        att = item.get("attachment")
        if not att:
            continue
        key = att.get("url") or att.get("name")
        if not key or key in seen:
            continue
        seen.add(key)
        attachments.append(att)
    return attachments


async def _build_reading_preview(
    request: Request,
    mongo_client: MongoClient,
    project: str | None,
    doc: Document,
    *,
    limit: int = READING_PREVIEW_LIMIT,
) -> dict[str, Any] | None:
    project_name = (doc.project or project or "").strip()
    if not project_name:
        return None

    reading_collection = getattr(request.state, "reading_collection", READING_COLLECTION_NAME)

    doc_order = None
    if doc.url:
        try:
            page_matches = await mongo_client.get_reading_pages(
                reading_collection,
                project_name,
                limit=1,
                offset=0,
                url=doc.url,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "knowledge_reading_page_lookup_failed",
                project=project_name,
                url=doc.url,
                error=str(exc),
            )
            page_matches = []
        if page_matches:
            doc_order = page_matches[0].order

    try:
        total_pages = await mongo_client.count_reading_pages(reading_collection, project_name)
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "knowledge_reading_total_failed",
            project=project_name,
            error=str(exc),
        )
        total_pages = 0

    if total_pages <= 0 and doc_order is None:
        return None

    offset = 0
    if isinstance(doc_order, int) and doc_order > 0:
        offset = max(0, doc_order - 1)
        if total_pages:
            offset = min(offset, max(0, total_pages - limit))
    try:
        pages = await mongo_client.get_reading_pages(
            reading_collection,
            project_name,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "knowledge_reading_preview_failed",
            project=project_name,
            offset=offset,
            error=str(exc),
        )
        pages = []

    if not pages:
        return None

    serialized_pages = _serialize_reading_pages(request, pages)
    has_more = total_pages > offset + len(serialized_pages)
    initial_index = 0
    if isinstance(doc_order, int) and doc_order > 0:
        initial_index = max(0, min(len(serialized_pages) - 1, doc_order - 1 - offset))

    preview = {
        "pages": serialized_pages,
        "project": project_name,
        "total": total_pages,
        "has_more": has_more,
        "startOffset": offset,
        "initialIndex": initial_index,
        "initialUrl": doc.url,
    }
    return preview


async def _collect_knowledge_snippets(
    request: Request,
    question: str,
    project: str | None,
    *,
    limit: int = 6,
) -> list[dict[str, Any]]:
    question = (question or "").strip()
    if not question:
        return []
    mongo_client = getattr(request.state, "mongo", None)
    priority_order: list[str]
    if mongo_client and hasattr(mongo_client, "get_knowledge_priority"):
        try:
            stored_order = await mongo_client.get_knowledge_priority(project)
        except Exception as exc:  # noqa: BLE001
            logger.debug("knowledge_priority_load_failed", error=str(exc))
            stored_order = []
        priority_order = _normalize_priority_order(stored_order)
    else:
        priority_order = list(_DEFAULT_KNOWLEDGE_PRIORITY)

    buckets: dict[str, list[dict[str, Any]]] = {
        "qa": [],
        "qdrant": [],
        "mongo": [],
    }

    if mongo_client and hasattr(mongo_client, "search_qa_pairs"):
        try:
            qa_candidates = await mongo_client.search_qa_pairs(question, project, limit=limit * 2)
        except Exception as exc:  # noqa: BLE001
            logger.debug("knowledge_qa_search_failed", error=str(exc))
            qa_candidates = []
        qa_seen: set[str] = set()
        for idx, entry in enumerate(qa_candidates):
            answer = str(entry.get("answer") or "").strip()
            question_text = str(entry.get("question") or "").strip()
            if not answer:
                continue
            source_id = entry.get("id") or f"{idx}"
            qa_id = f"qa::{source_id}"
            if qa_id in qa_seen:
                continue
            qa_seen.add(qa_id)
            buckets["qa"].append(
                {
                    "id": qa_id,
                    "name": question_text or "FAQ",
                    "text": answer,
                    "score": entry.get("score"),
                    "source": "qa",
                    "metadata": {"question": question_text} if question_text else None,
                }
            )

    try:
        docs = await asyncio.to_thread(retrieval_search.hybrid_search, question, limit * 3)
    except Exception as exc:  # noqa: BLE001
        logger.debug("knowledge_hybrid_failed", error=str(exc))
        docs = []

    vector_seen: set[str] = set()
    for doc in docs:
        payload = getattr(doc, "payload", None)
        text = _extract_payload_text(payload)
        if not text:
            continue
        doc_id = str(getattr(doc, "id", "")) or None
        if doc_id and doc_id in vector_seen:
            continue
        buckets["qdrant"].append(
            {
                "id": doc_id,
                "name": _extract_payload_name(payload, default=doc_id),
                "text": text,
                "score": getattr(doc, "score", None),
                "url": _extract_payload_url(payload),
                "source": "qdrant",
            }
        )
        if doc_id:
            vector_seen.add(doc_id)
        if len(buckets["qdrant"]) >= limit:
            break

    if mongo_client and hasattr(mongo_client, "search_documents"):
        mongo_cfg = MongoSettings()
        collection = getattr(request.state, "documents_collection", mongo_cfg.documents)
        try:
            candidates = await mongo_client.search_documents(collection, question, project=project)
        except Exception as exc:  # noqa: BLE001
            logger.debug("knowledge_mongo_search_failed", error=str(exc))
            candidates = []

        if not candidates:
            try:
                query: dict[str, Any] = {}
                if project:
                    query["project"] = project
                cursor = (
                    mongo_client.db[collection]
                    .find(query, {"_id": False})
                    .sort("ts", -1)
                    .limit(limit * 3)
                )
                candidates = [Document(**doc) async for doc in cursor]
            except Exception as exc:  # noqa: BLE001
                logger.debug("knowledge_mongo_fallback_failed", error=str(exc))
                candidates = []

        mongo_seen: set[str] = set()
        for doc in candidates:
            file_id = getattr(doc, "fileId", None)
            if file_id and file_id in mongo_seen:
                continue
            attachment_meta: dict[str, Any] | None = None
            doc_meta = doc.model_dump()
            text = ""
            doc_url = doc.url
            try:
                if file_id and _is_attachment_doc(doc_meta):
                    text = doc.description or ""
                else:
                    _meta, payload = await mongo_client.get_document_with_content(
                        collection, doc.fileId
                    )
                    text = payload.decode("utf-8", errors="ignore")
                    if not doc_url:
                        doc_url = _meta.get("url")
            except Exception as exc:  # noqa: BLE001
                logger.debug("knowledge_content_fetch_failed", file_id=file_id, error=str(exc))
                text = doc.description or ""

            if file_id and _is_attachment_doc(doc_meta):
                download_url = _build_download_url(request, file_id)
                doc_url = doc_url or download_url
                attachment_meta = {
                    "name": doc.name or file_id,
                    "url": doc_url,
                    "content_type": doc.content_type,
                    "file_id": file_id,
                }
                if doc.description:
                    attachment_meta["description"] = doc.description
                if doc.size_bytes is not None:
                    attachment_meta["size_bytes"] = int(doc.size_bytes)
                if not text.strip():
                    text = doc.description or ""

            if not text.strip() and not attachment_meta:
                continue

            item = {
                "id": file_id,
                "name": doc.name,
                "text": text,
                "score": getattr(doc, "ts", None),
                "url": doc_url,
                "source": "mongo",
            }
            if attachment_meta:
                item["attachment"] = attachment_meta
            if getattr(doc, "reading_mode", False) and mongo_client and hasattr(mongo_client, "get_reading_pages"):
                try:
                    reading_preview = await _build_reading_preview(request, mongo_client, project, doc)
                except Exception as exc:  # noqa: BLE001
                    logger.debug(
                        "knowledge_reading_preview_error",
                        project=project,
                        url=doc.url,
                        error=str(exc),
                    )
                    reading_preview = None
                if reading_preview:
                    item["reading"] = reading_preview
            buckets["mongo"].append(item)
            if file_id:
                mongo_seen.add(file_id)
            if len(buckets["mongo"]) >= limit * 2:
                break

    merged: list[dict[str, Any]] = []
    merged_ids: set[str] = set()
    for source in priority_order:
        bucket = buckets.get(source) or []
        for entry in bucket:
            entry_id = entry.get("id")
            if entry_id and entry_id in merged_ids:
                continue
            merged.append(entry)
            if entry_id:
                merged_ids.add(entry_id)
            if len(merged) >= limit:
                break
        if len(merged) >= limit:
            break

    if len(merged) < limit:
        for source, bucket in buckets.items():
            if source in priority_order:
                continue
            for entry in bucket:
                entry_id = entry.get("id")
                if entry_id and entry_id in merged_ids:
                    continue
                merged.append(entry)
                if entry_id:
                    merged_ids.add(entry_id)
                if len(merged) >= limit:
                    break
            if len(merged) >= limit:
                break

    if not merged and mongo_client and hasattr(mongo_client, "record_unanswered_question"):
        try:
            await mongo_client.record_unanswered_question(
                project=project,
                question=question,
                metadata={"source": "knowledge"},
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("knowledge_unanswered_record_failed", error=str(exc))

    return merged[:limit]


async def _plan_bitrix_action(
    question: str,
    project: Project | None,
) -> dict[str, Any] | None:
    cleaned_question = (question or "").strip()
    if not cleaned_question:
        return None
    prompt = BITRIX_COMMAND_PROMPT.format(question=cleaned_question)
    model_override = None
    if project and isinstance(project.llm_model, str) and project.llm_model.strip():
        model_override = project.llm_model.strip()
    chunks: list[str] = []
    try:
        async for token in llm_client.generate(prompt, model=model_override):
            chunks.append(token)
            if len("".join(chunks)) >= 2000:
                break
    except Exception as exc:  # noqa: BLE001
        logger.debug("bitrix_plan_failed", error=str(exc))
        return None
    raw = "".join(chunks).strip()
    if not raw:
        return None
    parsed = _extract_json_object(raw)
    if not parsed:
        logger.debug("bitrix_plan_parse_failed", raw=raw[:200])
        return None
    action = str(parsed.get("action") or "").strip().lower()
    if action in {"", "skip", "none", "no"}:
        return {"action": "skip"}
    if action == "create_task":
        title = parsed.get("title")
        description = parsed.get("description")
        if not isinstance(title, str) or not title.strip():
            return None
        task_payload: dict[str, Any] = {
            "title": title.strip(),
            "description": description.strip() if isinstance(description, str) else "",
        }
        responsible_id = parsed.get("responsible_id")
        if isinstance(responsible_id, int) and responsible_id > 0:
            task_payload["responsible_id"] = responsible_id
        deadline = parsed.get("deadline")
        if isinstance(deadline, str) and deadline.strip():
            task_payload["deadline"] = deadline.strip()
        return {"action": "create_task", "params": task_payload}

    method = parsed.get("method")
    if not isinstance(method, str) or not method.strip():
        return None
    params = parsed.get("params") if isinstance(parsed.get("params"), dict) else None
    return {
        "action": "call",
        "method": method.strip(),
        "params": params or {},
    }


def _format_bitrix_snippet(
    method: str,
    params: dict[str, Any] | None,
    response: dict[str, Any] | str,
    *,
    error: str | None = None,
) -> str:
    segments: list[str] = [f"Bitrix24 метод: {method}"]
    if params:
        params_preview = _json_preview(params, limit=BITRIX_PARAMS_PREVIEW_LIMIT)
        segments.append(f"Параметры: {params_preview}")
    if error:
        segments.append(f"Ошибка: {error}")
    else:
        payload = response
        if isinstance(response, dict) and "result" in response:
            payload = response["result"]
        segments.append(
            "Ответ: " + _json_preview(payload, limit=BITRIX_RESPONSE_PREVIEW_LIMIT)
        )
    return "\n".join(segments)


async def _collect_bitrix_snippet(
    request: Request,
    question: str,
    project: Project | None,
    session_key: str | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    if not project or not getattr(project, "bitrix_enabled", False):
        return None, None, None
    webhook_url = getattr(project, "bitrix_webhook_url", None)
    if not isinstance(webhook_url, str) or not webhook_url.strip():
        return None, None, None

    plan = await _plan_bitrix_action(question, project)
    if not plan or plan.get("action") not in {"call", "create_task"}:
        return None, plan if plan else None, None

    if plan["action"] == "create_task":
        method = "tasks.task.add"
        params = {"fields": plan.get("params", {})}
    else:
        method = str(plan.get("method") or "").strip()
        params = plan.get("params") if isinstance(plan.get("params"), dict) else {}

    debug_info: dict[str, Any] = {
        "action": plan["action"],
        "method": method,
        "params": params,
    }

    if not method:
        debug_info["error"] = "empty_method"
        return None, debug_info, None

    if plan["action"] == "create_task":
        fields = params.get("fields", {}) if isinstance(params, dict) else {}
        preview_lines = [
            "Bitrix24 задача (предварительно):",
            f"• Название: {fields.get('title') or '—'}",
        ]
        description = fields.get("description") or ""
        if description:
            preview_lines.append(f"• Описание: {description[:400]}{'' if len(description) <= 400 else '…'}")
        responsible = fields.get("responsible_id")
        if responsible:
            preview_lines.append(f"• Ответственный: {responsible}")
        deadline = fields.get("deadline")
        if deadline:
            preview_lines.append(f"• Дедлайн: {deadline}")
        preview_lines.append(
            "\nОтветьте «да», чтобы отправить задачу в Bitrix, или «нет», чтобы отменить."
        )
        snippet_text = "\n".join(preview_lines)

        plan_id = uuid4().hex
        pending_payload = {
            "plan_id": plan_id,
            "action": plan["action"],
            "method": method,
            "params": params,
            "preview": snippet_text,
        }
        store_payload = {
            "method": method,
            "params": params,
            "project": project.name if project else None,
            "session": session_key,
            "created_at": time.time(),
        }
        try:
            redis_client = _get_redis()
            await redis_client.setex(
                f"bitrix:plan:{plan_id}",
                15 * 60,
                json.dumps(store_payload, ensure_ascii=False),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("bitrix_plan_store_failed", error=str(exc))
            debug_info["error"] = "plan_store_failed"
            return None, debug_info, None

        snippet = {
            "id": f"bitrix::pending:{plan_id}",
            "name": "Bitrix24 задача (ожидает подтверждения)",
            "text": snippet_text,
            "source": "bitrix",
            "metadata": {
                "method": method,
                "action": plan["action"],
                "pending_confirmation": True,
                "plan_id": plan_id,
            },
        }
        debug_info["pending"] = True
        debug_info["plan_id"] = plan_id
        return snippet, debug_info, pending_payload

    try:
        response = await call_bitrix_webhook(webhook_url, method, params)
        snippet_text = _format_bitrix_snippet(method, params, response)
        debug_info["response_preview"] = _json_preview(response, limit=600)
        snippet = {
            "id": f"bitrix::{method}",
            "name": f"Bitrix24 {method}",
            "text": snippet_text,
            "source": "bitrix",
            "metadata": {
                "method": method,
                "action": plan["action"],
            },
        }
        return snippet, debug_info, None
    except BitrixError as exc:
        message = str(exc)
        debug_info["error"] = message
        snippet_text = _format_bitrix_snippet(method, params, {}, error=message)
        snippet = {
            "id": f"bitrix::{method}:error",
            "name": f"Bitrix24 {method} (ошибка)",
            "text": snippet_text,
            "source": "bitrix",
            "metadata": {
                "method": method,
                "status": "error",
            },
        }
        return snippet, debug_info, None
    except Exception as exc:  # noqa: BLE001
        logger.warning("bitrix_call_unexpected_failure", error=str(exc))
        debug_info["error"] = "unexpected_failure"
        return None, debug_info, None


async def _plan_mail_action(
    question: str,
    project: Project | None,
) -> dict[str, Any] | None:
    cleaned_question = (question or "").strip()
    if not cleaned_question:
        return None
    prompt = MAIL_COMMAND_PROMPT.format(question=cleaned_question)
    model_override = None
    if project and isinstance(project.llm_model, str) and project.llm_model.strip():
        model_override = project.llm_model.strip()
    chunks: list[str] = []
    try:
        async for token in llm_client.generate(prompt, model=model_override):
            chunks.append(token)
            if len("".join(chunks)) >= 2000:
                break
    except Exception as exc:  # noqa: BLE001
        logger.debug("mail_plan_failed", error=str(exc))
        return None
    raw = "".join(chunks).strip()
    if not raw:
        return None
    parsed = _extract_json_object(raw)
    if not parsed:
        logger.debug("mail_plan_parse_failed", raw=raw[:200])
        return None
    action = str(parsed.get("action") or "").strip().lower()
    if action in {"", "skip", "none", "no"}:
        return {"action": "skip"}
    if action == "send_email":
        to_value = parsed.get("to")
        subject_value = parsed.get("subject")
        body_value = parsed.get("body")
        if not isinstance(to_value, list) or not isinstance(subject_value, str) or not isinstance(body_value, str):
            return None
        cc_value = parsed.get("cc") if isinstance(parsed.get("cc"), list) else []
        bcc_value = parsed.get("bcc") if isinstance(parsed.get("bcc"), list) else []
        reply_to_value = parsed.get("reply_to") if isinstance(parsed.get("reply_to"), str) else None
        in_reply_to_value = parsed.get("in_reply_to") if isinstance(parsed.get("in_reply_to"), str) else None
        include_signature_raw = parsed.get("signature")
        include_signature = True if include_signature_raw is None else bool(include_signature_raw)
        cleaned_to = [str(item).strip() for item in to_value if isinstance(item, str) and item.strip()]
        cleaned_cc = [str(item).strip() for item in cc_value if isinstance(item, str) and item.strip()]
        cleaned_bcc = [str(item).strip() for item in bcc_value if isinstance(item, str) and item.strip()]
        subject_clean = subject_value.strip()
        if not cleaned_to or not subject_clean:
            return None
        return {
            "action": "send_email",
            "to": cleaned_to,
            "cc": cleaned_cc,
            "bcc": cleaned_bcc,
            "subject": subject_clean,
            "body": body_value,
            "reply_to": reply_to_value,
            "in_reply_to": in_reply_to_value,
            "include_signature": include_signature,
        }
    if action == "list_inbox":
        limit_raw = parsed.get("limit")
        try:
            limit_value = int(limit_raw)
        except (TypeError, ValueError):
            limit_value = 5
        limit_value = max(1, min(limit_value, 15))
        unread_only = bool(parsed.get("unread_only"))
        return {
            "action": "list_inbox",
            "limit": limit_value,
            "unread_only": unread_only,
        }
    return None


def _format_mail_preview(plan: dict[str, Any], settings: MailSettings) -> str:
    recipients = ", ".join(plan.get("to", [])) or "—"
    cc = ", ".join(plan.get("cc", [])) or "—"
    bcc = ", ".join(plan.get("bcc", [])) or "—"
    body = str(plan.get("body") or "").strip()
    if plan.get("include_signature") and settings.signature:
        signature = settings.signature.strip()
        if signature:
            body = f"{body}\n\n{signature}" if body else signature
    if len(body) > MAIL_BODY_PREVIEW_LIMIT:
        body_preview = body[: MAIL_BODY_PREVIEW_LIMIT - 1].rstrip() + "…"
    else:
        body_preview = body
    lines = [
        "Черновик письма:",
        f"• От: {settings.sender}",
        f"• Кому: {recipients}",
        f"• Копия: {cc}",
        f"• Скрытая копия: {bcc}",
        f"• Тема: {plan.get('subject', '—')}",
    ]
    if plan.get("reply_to"):
        lines.append(f"• Ответить на: {plan['reply_to']}")
    if body_preview:
        lines.append("")
        lines.append(body_preview)
    return "\n".join(lines)


async def _collect_mail_snippet(
    request: Request,
    question: str,
    project: Project | None,
    session_key: str | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    if not project or not getattr(project, "mail_enabled", False):
        return None, None, None
    try:
        settings = project_mail_settings(project)
    except MailConnectorError as exc:
        logger.debug(
            "mail_settings_invalid",
            project=getattr(project, "name", None),
            error=str(exc),
        )
        return None, {"error": str(exc)}, None

    plan = await _plan_mail_action(question, project)
    if not plan:
        return None, None, None

    action = plan.get("action")
    debug_info: dict[str, Any] = {"action": action}

    if action == "skip":
        return None, debug_info, None

    if action == "send_email":
        preview_text = _format_mail_preview(plan, settings)
        plan_id = uuid4().hex
        pending_payload = {
            "plan_id": plan_id,
            "action": action,
            "preview": preview_text,
        }
        store_payload = {
            "project": project.name if project else None,
            "session": session_key,
            "plan": plan,
            "created_at": time.time(),
        }
        try:
            redis_client = _get_redis()
            await redis_client.setex(
                f"mail:plan:{plan_id}",
                MAIL_PLAN_TTL,
                json.dumps(store_payload, ensure_ascii=False),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("mail_plan_store_failed", error=str(exc))
            debug_info["error"] = "plan_store_failed"
            return None, debug_info, None
        snippet = {
            "id": f"mail::pending:{plan_id}",
            "name": "Почта: черновик (ожидает подтверждения)",
            "text": preview_text,
            "source": "mail",
            "metadata": {
                "pending_confirmation": True,
                "plan_id": plan_id,
            },
        }
        debug_info["pending"] = True
        debug_info["plan_id"] = plan_id
        return snippet, debug_info, pending_payload

    if action == "list_inbox":
        limit = int(plan.get("limit") or 5)
        unread_only = bool(plan.get("unread_only"))
        try:
            messages = await fetch_recent_messages(
                settings,
                limit=limit,
                unseen_only=unread_only,
            )
        except MailConnectorError as exc:
            logger.warning(
                "mail_fetch_failed",
                project=getattr(project, "name", None),
                error=str(exc),
            )
            debug_info["error"] = str(exc)
            return None, debug_info, None
        if not messages:
            debug_info["result"] = "empty"
            return None, debug_info, None
        summary_text = summarize_messages(messages, limit=limit)
        snippet = {
            "id": f"mail::inbox:{project.name if project else 'default'}",
            "name": "Почта — свежие письма",
            "text": summary_text,
            "source": "mail",
            "metadata": {
                "unread_only": unread_only,
                "count": len(messages),
            },
        }
        debug_info["messages"] = len(messages)
        debug_info["unread_only"] = unread_only
        return snippet, debug_info, None

    debug_info["error"] = "unsupported_action"
    return None, debug_info, None


@llm_router.post("/bitrix/confirm", response_class=ORJSONResponse)
async def confirm_bitrix_plan(request: Request, payload: BitrixPlanAction) -> ORJSONResponse:
    try:
        redis_client = _get_redis()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="redis_unavailable") from exc
    key = f"bitrix:plan:{payload.plan_id}"
    raw = await redis_client.get(key)
    if raw is None:
        raise HTTPException(status_code=404, detail="bitrix_plan_not_found")
    try:
        stored = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        await redis_client.delete(key)
        raise HTTPException(status_code=410, detail="bitrix_plan_corrupted") from exc

    expected_session = stored.get("session")
    if expected_session and payload.session_id and expected_session != payload.session_id:
        raise HTTPException(status_code=403, detail="session_mismatch")

    project_name = _normalize_project(payload.project or stored.get("project"))
    project_obj: Project | None = None
    if project_name:
        mongo_client = _get_mongo_client(request)
        project_obj = await mongo_client.get_project(project_name)
    if not project_obj or not getattr(project_obj, "bitrix_enabled", False):
        raise HTTPException(status_code=400, detail="bitrix_not_configured")
    webhook_url = getattr(project_obj, "bitrix_webhook_url", None)
    if not isinstance(webhook_url, str) or not webhook_url.strip():
        raise HTTPException(status_code=400, detail="bitrix_webhook_missing")

    method = stored.get("method")
    params = stored.get("params")
    if not isinstance(method, str) or not method.strip():
        await redis_client.delete(key)
        raise HTTPException(status_code=410, detail="bitrix_plan_invalid")

    try:
        response = await call_bitrix_webhook(webhook_url, method, params if isinstance(params, dict) else {})
    except BitrixError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        await redis_client.delete(key)

    return ORJSONResponse({"status": "sent", "result": response})


@llm_router.post("/bitrix/cancel", response_class=ORJSONResponse)
async def cancel_bitrix_plan(payload: BitrixPlanAction) -> ORJSONResponse:
    try:
        redis_client = _get_redis()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="redis_unavailable") from exc
    key = f"bitrix:plan:{payload.plan_id}"
    raw = await redis_client.get(key)
    if raw is None:
        return ORJSONResponse({"status": "cancelled", "removed": False})
    try:
        stored = json.loads(raw)
    except Exception:
        stored = {}
    expected_session = stored.get("session")
    if expected_session and payload.session_id and expected_session != payload.session_id:
        raise HTTPException(status_code=403, detail="session_mismatch")
    await redis_client.delete(key)
    return ORJSONResponse({"status": "cancelled", "removed": True})


@llm_router.post("/mail/confirm", response_class=ORJSONResponse)
async def confirm_mail_plan(request: Request, payload: MailPlanAction) -> ORJSONResponse:
    try:
        redis_client = _get_redis()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="redis_unavailable") from exc
    key = f"mail:plan:{payload.plan_id}"
    raw = await redis_client.get(key)
    if raw is None:
        raise HTTPException(status_code=404, detail="mail_plan_not_found")
    try:
        stored = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        await redis_client.delete(key)
        raise HTTPException(status_code=410, detail="mail_plan_corrupted") from exc

    expected_session = stored.get("session")
    if expected_session and payload.session_id and expected_session != payload.session_id:
        await redis_client.delete(key)
        raise HTTPException(status_code=403, detail="session_mismatch")

    project_name = _normalize_project(payload.project or stored.get("project"))
    mongo_client = _get_mongo_client(request)
    project_obj = await mongo_client.get_project(project_name) if project_name else None
    if not project_obj or not getattr(project_obj, "mail_enabled", False):
        await redis_client.delete(key)
        raise HTTPException(status_code=400, detail="mail_not_configured")

    try:
        settings = project_mail_settings(project_obj)
    except MailConnectorError as exc:
        await redis_client.delete(key)
        raise HTTPException(status_code=400, detail=f"mail_settings_invalid:{exc}") from exc

    plan = stored.get("plan") or {}
    if plan.get("action") != "send_email":
        await redis_client.delete(key)
        raise HTTPException(status_code=410, detail="mail_plan_invalid")

    message_payload = MailMessagePayload(
        to=plan.get("to") or [],
        cc=plan.get("cc") or [],
        bcc=plan.get("bcc") or [],
        subject=plan.get("subject") or "Без темы",
        body=str(plan.get("body") or ""),
        reply_to=plan.get("reply_to") if isinstance(plan.get("reply_to"), str) else None,
        in_reply_to=plan.get("in_reply_to") if isinstance(plan.get("in_reply_to"), str) else None,
    )

    if plan.get("include_signature") and settings.signature:
        signature = settings.signature.strip()
        if signature:
            if message_payload.body.strip():
                message_payload.body = f"{message_payload.body}\n\n{signature}"
            else:
                message_payload.body = signature

    try:
        result = await send_mail(settings, message_payload)
    except MailConnectorError as exc:
        logger.warning(
            "mail_send_failed",
            project=project_name,
            error=str(exc),
        )
        await redis_client.delete(key)
        raise HTTPException(status_code=400, detail=f"mail_delivery_failed:{exc}") from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("mail_send_unexpected", project=project_name, error=str(exc))
        await redis_client.delete(key)
        raise HTTPException(status_code=500, detail="mail_delivery_exception") from exc

    await redis_client.delete(key)
    return ORJSONResponse({"status": "sent", "message_id": result.message_id})


@llm_router.post("/mail/cancel", response_class=ORJSONResponse)
async def cancel_mail_plan(payload: MailPlanAction) -> ORJSONResponse:
    try:
        redis_client = _get_redis()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="redis_unavailable") from exc
    key = f"mail:plan:{payload.plan_id}"
    stored = await redis_client.get(key)
    if stored is None:
        return ORJSONResponse({"status": "cancelled", "removed": False})
    try:
        data = json.loads(stored)
    except Exception:
        data = {}
    expected_session = data.get("session")
    if expected_session and payload.session_id and expected_session != payload.session_id:
        raise HTTPException(status_code=403, detail="session_mismatch")
    await redis_client.delete(key)
    return ORJSONResponse({"status": "cancelled", "removed": True})


def _compose_knowledge_message(snippets: list[dict[str, Any]]) -> str:
    if not snippets:
        return ""
    blocks: list[str] = []
    has_attachments = any(bool(item.get("attachment")) for item in snippets)
    for idx, item in enumerate(snippets, 1):
        name = item.get("name") or f"Источник {idx}"
        snippet_text = _truncate_text(item.get("text", ""))
        attachment = item.get("attachment")
        url = item.get("url")
        if attachment:
            attachment_url = attachment.get("url") or url
            attachment_name = attachment.get("name") or name
            attachment_line = f"Документ: {attachment_name} ({attachment_url})" if attachment_url else f"Документ: {attachment_name}"
            if snippet_text:
                snippet_text = f"{snippet_text}\n{attachment_line}"
            else:
                snippet_text = attachment_line
            url = attachment_url or url
        footer = f"\nИсточник: {url}" if url and url not in snippet_text else ""
        blocks.append(f"Источник {idx} ({name}):\n{snippet_text}{footer}")
    prefix = [
        "Тебе доступны выдержки из базы знаний. Сначала проанализируй их, выдели ключевые факты и противоречия,",
        "затем дай итоговый ответ, ссылаясь на несколько источников, если это повышает точность.",
    ]
    if has_attachments:
        prefix.append(
            "Если посчитаешь нужным отправить документ, кратко опиши его, спроси подтверждение и жди явного согласия"
            " (например: 'да', 'пришли', 'отправь'). Не отправляй файлы без подтверждения пользователя."
        )
    header = " ".join(prefix)
    return header + "\n\n" + "\n\n".join(blocks)


def _trim_voice_snippets(snippets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not snippets:
        return []
    trimmed: list[dict[str, Any]] = []
    total_chars = 0
    for item in snippets[:_VOICE_KNOWLEDGE_LIMIT]:
        text = item.get("text", "")
        remaining = _VOICE_KNOWLEDGE_CHARS - total_chars
        if remaining <= 0:
            break
        if len(text) > remaining:
            slice_ = text[:remaining]
            slice_ = slice_.rsplit(" ", 1)[0].strip() or text[:remaining]
            text = slice_.rstrip(". ") + "…"
        total_chars += len(text)
        new_item = dict(item)
        new_item["text"] = text
        trimmed.append(new_item)
    return trimmed


def _summarize_messages(messages: list[dict[str, Any]], *, max_len: int = _HISTORY_SUMMARY_MAX_CHARS) -> str | None:
    """Build a compact textual summary of older dialog turns."""

    if not messages or max_len <= 0:
        return None

    summary_parts: list[str] = []
    remaining = max_len
    for msg in messages:
        content = str(msg.get("content", "")).strip()
        if not content:
            continue
        role = str(msg.get("role", "")).lower()
        speaker = "User" if role == RoleEnum.user.value else "Assistant"
        normalized = " ".join(content.split())
        if len(normalized) > min(240, remaining):
            clipped = normalized[: min(240, remaining)].rsplit(" ", 1)[0]
            normalized = (clipped or normalized[: min(240, remaining)]).rstrip(".,;") + "…"
        fragment = f"{speaker}: {normalized}"
        fragment_len = len(fragment)
        if fragment_len >= remaining and summary_parts:
            break
        if fragment_len > remaining:
            fragment = fragment[:remaining]
        summary_parts.append(fragment)
        remaining -= len(fragment) + 2  # include separator allowance
        if remaining <= 0:
            break

    if not summary_parts:
        return None

    summary = f"{_HISTORY_SUMMARY_PREFIX} {'; '.join(summary_parts)}"
    if len(summary) > max_len:
        summary = summary[:max_len].rsplit(" ", 1)[0].rstrip(".,;") + "…"
    return summary


def _limit_dialog_history(
    messages: list[dict[str, Any]],
    max_turns: int = _MAX_DIALOG_TURNS,
    *,
    max_chars: int = _MAX_DIALOG_CHARS,
) -> list[dict[str, Any]]:
    """Return dialog history limited by ``max_turns`` and ``max_chars`` with optional summary."""

    if not messages:
        return []

    trimmed: list[dict[str, Any]]
    if max_turns <= 0:
        trimmed = list(messages)
    else:
        kept: list[dict[str, Any]] = []
        user_seen = 0
        for msg in reversed(messages):
            role = str(msg.get("role", "")).lower()
            if role == RoleEnum.user.value:
                user_seen += 1
            kept.append(msg)
            if user_seen >= max_turns:
                break
        trimmed = list(reversed(kept))

    removed_count = max(0, len(messages) - len(trimmed))
    summary_inserted = False

    if removed_count > 0:
        older = messages[: removed_count]
        summary_text = _summarize_messages(older)
        if summary_text:
            trimmed = [{"role": "system", "content": summary_text}, *trimmed]
            summary_inserted = True

    char_pruned: list[dict[str, Any]] = []

    if max_chars > 0:
        def _msg_len(item: dict[str, Any]) -> int:
            return len(str(item.get("content", "")))

        total_chars = sum(_msg_len(item) for item in trimmed)
        removal_index = 1 if summary_inserted else 0
        # ensure we keep at least the last two actual messages
        while total_chars > max_chars and len(trimmed) - removal_index > 1:
            removed = trimmed.pop(removal_index)
            total_chars -= _msg_len(removed)
            char_pruned.append(removed)

    if char_pruned and not summary_inserted:
        summary_text = _summarize_messages(char_pruned)
        if summary_text:
            trimmed = [{"role": "system", "content": summary_text}, *trimmed]
            summary_inserted = True
            if max_chars > 0:
                total_chars = sum(len(str(item.get("content", ""))) for item in trimmed)
                removal_index = 1 if summary_inserted else 0
                while total_chars > max_chars and len(trimmed) - removal_index > 1:
                    removed = trimmed.pop(removal_index)
                    total_chars -= len(str(removed.get("content", "")))

    if summary_inserted and max_chars > 0 and trimmed:
        other_chars = sum(len(str(item.get("content", ""))) for item in trimmed[1:])
        if other_chars >= max_chars:
            # No room for the summary at all.
            trimmed.pop(0)
        else:
            allowance = max_chars - other_chars
            summary_content = str(trimmed[0].get("content", ""))
            if len(summary_content) > allowance:
                snippet = summary_content[:allowance]
                snippet = snippet.rsplit(" ", 1)[0].strip() or snippet.strip()
                snippet = snippet.rstrip(".,; ")
                if snippet and not snippet.endswith("…"):
                    snippet = f"{snippet}…"
                if snippet:
                    trimmed[0]["content"] = snippet
                else:
                    trimmed.pop(0)

    return trimmed


@llm_router.post("/ask", response_class=ORJSONResponse, response_model=LLMResponse)
async def ask_llm(request: Request, llm_request: LLMRequest) -> ORJSONResponse:
    """Return a response from the language model for the given session.

    Parameters
    ----------
    request:
        Incoming request used to access application state.
    llm_request:
        Input payload specifying the ``session_id`` and optional project slug.

    Raises
    ------
    HTTPException
        If the session or preset cannot be found or if generation fails.
    """

    try:
        mongo_client = request.state.mongo
    except Exception as exc:
        logger.error("mongo_client_missing", error=str(exc))
        raise HTTPException(status_code=500, detail="Mongo client unavailable") from exc
    project_name = _normalize_project(llm_request.project)
    project: Project | None = None
    if project_name:
        try:
            project = await request.state.mongo.get_project(project_name)
            if project is None:
                project = await request.state.mongo.upsert_project(Project(name=project_name))
        except Exception as exc:
            logger.error("project_resolve_failed", project=project_name, error=str(exc))
            raise HTTPException(status_code=500, detail="Failed to resolve project") from exc
    emotions_enabled = True
    if project and project.llm_emotions_enabled is not None:
        emotions_enabled = bool(project.llm_emotions_enabled)

    logger.info(
        "ask",
        session=str(llm_request.session_id),
        project=project_name,
        emotions=emotions_enabled,
    )
    context = []

    try:
        preset = [
            {"role": message.role, "content": message.text}
            async for message in mongo_client.get_context_preset(
                request.state.context_presets_collection
            )
        ]
    except NotFound:
        logger.warning("preset_not_found", session=str(llm_request.session_id))
        raise HTTPException(status_code=404, detail="Preset not found")
    except Exception as exc:
        logger.error("preset_load_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to load preset") from exc
    try:
        async for message in mongo_client.get_sessions(
            request.state.contexts_collection, str(llm_request.session_id)
        ):
            context.append({"role": str(message.role), "content": message.text})
    except NotFound:
        logger.warning("session_not_found", session=str(llm_request.session_id))
        raise HTTPException(status_code=404, detail="Can't find specified sessionId")
    except Exception as exc:
        logger.error("session_load_failed", session=str(llm_request.session_id), error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to load session history") from exc

    if not context:
        raise HTTPException(status_code=400, detail="No conversation history provided")

    context = _limit_dialog_history(context)

    if context[-1]["role"] == RoleEnum.assistant:
        logger.error(
            "incorrect session state", session=str(llm_request.session_id)
        )
        raise HTTPException(
            status_code=400, detail="Last message role cannot be assistant"
        )

    knowledge_snippets: list[dict[str, Any]] = []
    attachments_payload: list[dict[str, Any]] = []
    attachments_to_queue: list[dict[str, Any]] = []
    knowledge_message = ""
    question_text = context[-1].get("content", "")
    try:
        knowledge_snippets = await _collect_knowledge_snippets(
            request, question_text, project_name
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "knowledge_lookup_failed",
            session=str(llm_request.session_id),
            project=project_name,
            error=str(exc),
        )

    bitrix_snippet: dict[str, Any] | None = None
    bitrix_debug: dict[str, Any] | None = None
    bitrix_pending: dict[str, Any] | None = None
    mail_snippet: dict[str, Any] | None = None
    mail_debug: dict[str, Any] | None = None
    mail_pending: dict[str, Any] | None = None
    mail_used = False
    try:
        bitrix_snippet, bitrix_debug, bitrix_pending = await _collect_bitrix_snippet(
            request,
            question_text,
            project,
            str(llm_request.session_id),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "bitrix_collect_failed",
            session=str(llm_request.session_id),
            project=project_name,
            error=str(exc),
        )
        bitrix_debug = {"error": "exception", "detail": str(exc)}
        bitrix_snippet = None
        bitrix_pending = None

    if bitrix_snippet:
        knowledge_snippets = [bitrix_snippet, *knowledge_snippets]

    try:
        mail_snippet, mail_debug, mail_pending = await _collect_mail_snippet(
            request,
            question_text,
            project,
            str(llm_request.session_id),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "mail_collect_failed",
            session=str(llm_request.session_id),
            project=project_name,
            error=str(exc),
        )
        mail_snippet = None
        mail_debug = {"error": "exception", "detail": str(exc)}
        mail_pending = None

    if mail_debug:
        if mail_debug.get("pending") or mail_debug.get("messages"):
            mail_used = True
    if mail_snippet:
        knowledge_snippets = [mail_snippet, *knowledge_snippets]
        mail_used = True

    if knowledge_snippets:
        knowledge_message = _compose_knowledge_message(knowledge_snippets)
        attachments_payload = _collect_attachments(knowledge_snippets)
        if knowledge_message:
            preset = preset + [{"role": "system", "content": knowledge_message}]
            log_payload = [
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "source": item.get("source"),
                    "url": item.get("url"),
                    "chars": len(item.get("text", "")),
                    "score": item.get("score"),
                }
                for item in knowledge_snippets
            ]
            _log_debug_event(
                "knowledge_context_attached",
                session=str(llm_request.session_id),
                project=project_name,
                docs=log_payload,
                bitrix=bitrix_debug,
                bitrix_pending=bitrix_pending,
                mail=mail_debug,
                mail_pending=mail_pending,
            )
    if bitrix_debug:
        _log_debug_event(
            "bitrix_context_decision",
            session=str(llm_request.session_id),
            project=project_name,
            details=bitrix_debug,
        )
    if mail_debug and not mail_snippet:
        _log_debug_event(
            "mail_context_decision",
            session=str(llm_request.session_id),
            project=project_name,
            details=mail_debug,
        )

    system_messages: list[dict[str, str]] = []
    if project and project.llm_prompt:
        prompt_text = project.llm_prompt.strip()
        if prompt_text:
            system_messages.append({"role": "system", "content": prompt_text})
            _log_debug_event(
                "project_prompt_attached",
                session=str(llm_request.session_id),
                project=project_name,
                prompt_length=len(prompt_text),
            )

    emotion_instruction = EMOTION_ON_PROMPT if emotions_enabled else EMOTION_OFF_PROMPT
    system_messages.append({"role": "system", "content": emotion_instruction})

    reading_mode = request.query_params.get("reading") == "1"
    if reading_mode:
        system_messages.append({"role": "system", "content": READING_MODE_PROMPT})

    if system_messages:
        preset = system_messages + preset

    # Build a prompt similar to the HTTPModelClient/YaLLM formatting
    prompt_parts: list[str] = []
    for m in preset + context:
        role = m.get("role", "user")
        text = m.get("content", "")
        prompt_parts.append(f"{role}: {text}")
    prompt = "\n".join(prompt_parts)

    knowledge_log = [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "source": item.get("source"),
            "chars": len(item.get("text", "")),
            "url": item.get("url"),
        }
        for item in knowledge_snippets
    ]
    _log_debug_event(
        "llm_prompt_compiled",
        session=str(llm_request.session_id),
        project=project_name,
        emotions=emotions_enabled,
        prompt_preview=prompt[:500],
        prompt_length=len(prompt),
        knowledge=knowledge_log,
    )

    chunks: list[str] = []
    model_override = None
    if project and project.llm_model:
        trimmed_model = project.llm_model.strip()
        if trimmed_model:
            model_override = trimmed_model
    try:
        async for token in llm_client.generate(prompt, model=model_override):
            chunks.append(token)
    except Exception as exc:
        logger.error("llm_generate_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="LLM generation failed") from exc
    text = "".join(chunks)
    logger.info("llm answered", length=len(text), emotions=emotions_enabled)

    response_payload = LLMResponse(
        text=text,
        attachments=[Attachment(**att) for att in attachments_payload],
        emotions_enabled=emotions_enabled,
    )
    reading_items = _collect_reading_items(knowledge_snippets)

    meta_payload: dict[str, Any] = {
        "emotions_enabled": emotions_enabled,
    }
    if bitrix_debug:
        meta_payload["bitrix_debug"] = bitrix_debug
    if bitrix_pending:
        meta_payload["bitrix_pending"] = bitrix_pending
    if mail_debug:
        meta_payload["mail_debug"] = mail_debug
    if mail_pending:
        meta_payload["mail_pending"] = mail_pending
    if attachments_payload:
        meta_payload["attachments"] = len(attachments_payload)
    if reading_items:
        meta_payload["reading_available"] = True
        meta_payload["reading"] = reading_items
    else:
        meta_payload["reading_available"] = False
    await request.state.mongo.log_request_stat(
        project=project_name,
        question=context[-1].get("content", "") if context else None,
        response_chars=len(text),
        attachments=len(attachments_payload),
        prompt_chars=len(prompt),
        channel="api",
        session_id=str(llm_request.session_id),
        user_id=None,
        error=None,
    )
    payload = response_payload.model_dump()
    if meta_payload:
        payload["meta"] = meta_payload
    return ORJSONResponse(payload)


@llm_router.get("/chat")
async def chat(
    request: Request,
    question: str,
    project: str | None = None,
    channel: str | None = None,
    debug: bool | None = None,
    session_id: str | None = None,
    model: str | None = None,
) -> StreamingResponse:
    """Stream tokens from the language model using server-sent events.

    Parameters
    ----------
    question:
        Text sent as a query parameter. Example: ``/chat?question=hi``.
    """

    project_name, session_key, session_base, session_generated = _resolve_session_identifiers(
        request,
        project,
        session_id,
    )
    channel_name = (channel or "widget").strip() or "widget"
    project_obj: Project | None = None
    if project_name:
        project_obj = await request.state.mongo.get_project(project_name)
        if project_obj is None:
            project_obj = await request.state.mongo.upsert_project(Project(name=project_name))

    reading_mode = request.query_params.get("reading") == "1"

    emotions_enabled = True
    if project_obj and project_obj.llm_emotions_enabled is not None:
        emotions_enabled = bool(project_obj.llm_emotions_enabled)

    project_debug_info_enabled = True
    if project_obj and project_obj.debug_info_enabled is not None:
        project_debug_info_enabled = bool(project_obj.debug_info_enabled)

    request_debug_enabled = bool(debug) if debug is not None else False
    project_debug_enabled = bool(project_obj.debug_enabled) if project_obj and project_obj.debug_enabled is not None else False
    send_debug = request_debug_enabled or project_debug_enabled
    info_enabled = project_debug_info_enabled
    project_sources_enabled = False
    if project_obj and project_obj.llm_sources_enabled is not None:
        project_sources_enabled = bool(project_obj.llm_sources_enabled)
    sources_requested = _question_requests_sources(question)
    if send_debug:
        if request_debug_enabled and project_debug_enabled:
            debug_origin = "project+request"
        elif request_debug_enabled:
            debug_origin = "request"
        else:
            debug_origin = "project"
    else:
        debug_origin = None

    prompt_base = question
    if project_obj and project_obj.llm_prompt:
        prompt_text = project_obj.llm_prompt.strip()
        if prompt_text:
            prompt_base = f"{prompt_text}\n\n{question}"
            logger.info(
                "project_prompt_attached",
                project=project_name,
                prompt_length=len(prompt_text),
                mode="stream",
            )
    requested_model = model.strip() if isinstance(model, str) and model.strip() else None
    base_model_override = None
    if project_obj and project_obj.llm_model:
        model_text = project_obj.llm_model.strip()
        if model_text:
            base_model_override = model_text

    voice_model_override = None
    if project_obj and project_obj.llm_voice_model:
        voice_model_text = project_obj.llm_voice_model.strip()
        if voice_model_text:
            voice_model_override = voice_model_text

    voice_enabled = True
    if project_obj and project_obj.llm_voice_enabled is not None:
        voice_enabled = bool(project_obj.llm_voice_enabled)

    selected_model_override = base_model_override
    if channel_name.lower() == "voice-avatar":
        if not voice_enabled:
            logger.warning(
                "voice_channel_disabled",
                project=project_name,
                session=session_key,
                channel=channel_name,
            )
            raise HTTPException(status_code=403, detail="voice_mode_disabled")
        if voice_model_override:
            selected_model_override = voice_model_override

    if requested_model:
        selected_model_override = requested_model

    model_override = selected_model_override
    effective_model = model_override or getattr(llm_client, "MODEL_NAME", "unknown")

    mongo_client = request.state.mongo
    contexts_collection = getattr(request.state, "contexts_collection", MongoSettings().contexts)
    normalized_question = question.strip()
    dialog_history: list[dict[str, str]] = []
    if session_key:
        try:
            async for record in mongo_client.get_sessions(contexts_collection, session_key):
                dialog_history.append({
                    "role": str(record.role),
                    "content": record.text,
                })
        except NotFound:
            dialog_history = []
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "session_history_load_failed",
                session=session_key,
                project=project_name,
                error=str(exc),
            )
            dialog_history = []

    keep_messages = max(_MAX_DIALOG_TURNS * 2, 10)
    if session_key and normalized_question:
        last_entry = dialog_history[-1] if dialog_history else None
        if not last_entry or not (
            last_entry.get("role") == RoleEnum.user.value
            and last_entry.get("content") == normalized_question
        ):
            try:
                await mongo_client.append_session_message(
                    contexts_collection,
                    session_key,
                    RoleEnum.user.value,
                    normalized_question,
                    project=project_name,
                    keep=keep_messages,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "session_history_append_failed",
                    role="user",
                    session=session_key,
                    project=project_name,
                    error=str(exc),
                )
            else:
                dialog_history.append({
                    "role": RoleEnum.user.value,
                    "content": normalized_question,
                })

    limited_history = _limit_dialog_history(dialog_history, max_turns=_MAX_DIALOG_TURNS, max_chars=_MAX_DIALOG_CHARS)
    history_system_prompts: list[str] = []
    conversation_lines: list[str] = []
    for entry in limited_history:
        role = str(entry.get("role", ""))
        text = str(entry.get("content", ""))
        if not text:
            continue
        if role == "system":
            history_system_prompts.append(text)
        elif role == RoleEnum.user.value:
            conversation_lines.append(f"Пользователь: {text}")
        else:
            conversation_lines.append(f"Ассистент: {text}")

    if app_settings.debug:
        logger.info(
            "chat",
            question=question,
            project=project_name,
            emotions=emotions_enabled,
            session=session_key,
            debug=send_debug,
            channel=channel_name,
        )
    else:
        logger.info(
            "chat",
            question_chars=len(question or ""),
            project=project_name,
            emotions=emotions_enabled,
            session=session_key,
            debug=send_debug,
            channel=channel_name,
        )

    now_ts = time.time()
    await _prune_pending_attachments(request.app, now_ts)

    knowledge_snippets: list[dict[str, Any]] = []
    attachments_payload: list[dict[str, Any]] = []
    planned_attachments_count = 0
    pending_consumed = False
    bitrix_debug: dict[str, Any] | None = None
    bitrix_pending: dict[str, Any] | None = None
    bitrix_used = False
    mail_snippet: dict[str, Any] | None = None
    mail_debug: dict[str, Any] | None = None
    mail_pending: dict[str, Any] | None = None
    mail_used = False

    if session_key and _detect_attachment_consent(question):
        stored_entry = await _pop_pending_attachments(request.app, session_key)
        attachments_from_store = (stored_entry or {}).get("attachments") or []
        if attachments_from_store:
            attachments_payload = attachments_from_store
            knowledge_snippets = (stored_entry or {}).get("snippets") or []
            if is_voice_channel:
                knowledge_snippets = _trim_voice_snippets(knowledge_snippets)
                attachments_payload = []
            planned_attachments_count = len(attachments_payload)
            pending_consumed = True

    is_voice_channel = channel_name.lower() == "voice-avatar"

    if not knowledge_snippets:
        try:
            knowledge_snippets = await _collect_knowledge_snippets(
                request, question, project_name
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "knowledge_lookup_failed",
                project=project_name,
                error=str(exc),
                mode="stream",
            )
        else:
            if is_voice_channel:
                knowledge_snippets = _trim_voice_snippets(knowledge_snippets)
            attachments_to_queue = _collect_attachments(knowledge_snippets)
            if pending_consumed:
                # Attachments already confirmed for delivery; do not overwrite payload
                planned_attachments_count = len(attachments_payload)
            else:
                planned_attachments_count = len(attachments_to_queue)
                if is_voice_channel:
                    attachments_to_queue = []
                    planned_attachments_count = 0
                else:
                    await _set_pending_attachments(
                        request.app,
                        session_key,
                        attachments_to_queue,
                        knowledge_snippets,
                        now_ts,
                    )
                    attachments_payload = []  # wait for explicit confirmation

    try:
        bitrix_snippet, bitrix_debug, bitrix_pending = await _collect_bitrix_snippet(
            request,
            question,
            project_obj,
            session_key,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "bitrix_collect_failed",
            project=project_name,
            error=str(exc),
            mode="stream",
        )
        bitrix_snippet = None
        bitrix_debug = {"error": "exception", "detail": str(exc)}
    if bitrix_debug:
        if bitrix_debug.get("action") == "call" or bitrix_debug.get("pending"):
            bitrix_used = True
    if bitrix_snippet:
        knowledge_snippets = [bitrix_snippet, *knowledge_snippets]
        bitrix_used = True

    try:
        mail_snippet, mail_debug, mail_pending = await _collect_mail_snippet(
            request,
            question,
            project_obj,
            session_key,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "mail_collect_failed",
            project=project_name,
            error=str(exc),
            mode="stream",
        )
        mail_snippet = None
        mail_debug = {"error": "exception", "detail": str(exc)}
        mail_pending = None
    if mail_debug:
        if mail_debug.get("pending") or mail_debug.get("messages"):
            mail_used = True
    if mail_snippet:
        knowledge_snippets = [mail_snippet, *knowledge_snippets]
        mail_used = True
    if is_voice_channel and knowledge_snippets:
        knowledge_snippets = _trim_voice_snippets(knowledge_snippets)

    knowledge_message = _compose_knowledge_message(knowledge_snippets)
    if knowledge_message:
        _log_debug_event(
            "knowledge_context_attached",
            project=project_name,
            mode="stream",
            session=session_key,
            debug=send_debug,
            docs=[
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "source": item.get("source"),
                    "url": item.get("url"),
                    "chars": len(item.get("text", "")),
                    "score": item.get("score"),
                }
                for item in knowledge_snippets
            ],
            bitrix=bitrix_debug,
            bitrix_pending=bitrix_pending,
            mail=mail_debug,
            mail_pending=mail_pending,
        )
    if bitrix_debug and not knowledge_message:
        _log_debug_event(
            "bitrix_context_decision",
            project=project_name,
            mode="stream",
            session=session_key,
            details=bitrix_debug,
        )
    if mail_debug and not mail_snippet:
        _log_debug_event(
            "mail_context_decision",
            project=project_name,
            mode="stream",
            session=session_key,
            details=mail_debug,
        )

    emotion_instruction = EMOTION_ON_PROMPT if emotions_enabled else EMOTION_OFF_PROMPT
    system_prompts: list[str] = []
    if reading_mode:
        system_prompts.append(READING_MODE_PROMPT)
    system_prompts.append(emotion_instruction)
    if knowledge_message:
        system_prompts.append(knowledge_message)
    if history_system_prompts:
        system_prompts.extend(history_system_prompts)

    conversation_block = "\n".join(conversation_lines)
    if not conversation_block:
        fallback_question = normalized_question or question
        if fallback_question:
            conversation_block = f"Пользователь: {fallback_question}"

    prompt_segments = []
    if system_prompts:
        prompt_segments.append("\n\n".join(system_prompts))
    if conversation_block:
        prompt_segments.append(conversation_block)
    prompt_segments.append("Ассистент:")
    prompt_base = "\n\n".join(segment for segment in prompt_segments if segment)

    knowledge_log_stream = [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "source": item.get("source"),
            "chars": len(item.get("text", "")),
            "url": item.get("url"),
        }
        for item in knowledge_snippets
    ]
    knowledge_source_counts: dict[str, int] = {}
    total_knowledge_chars = 0
    for item in knowledge_snippets:
        source_label = str(item.get("source") or "unknown").lower()
        knowledge_source_counts[source_label] = knowledge_source_counts.get(source_label, 0) + 1
        total_knowledge_chars += len(item.get("text", ""))

    knowledge_preview = [
        {
            "id": entry.get("id"),
            "name": entry.get("name"),
            "source": entry.get("source"),
            "score": entry.get("score"),
            "url": entry.get("url"),
        }
        for entry in knowledge_snippets[:3]
    ]
    reading_items_stream = _collect_reading_items(knowledge_snippets)
    _log_debug_event(
        "llm_prompt_compiled_stream",
        project=project_name,
        emotions=emotions_enabled,
        prompt_preview=prompt_base[:500],
        prompt_length=len(prompt_base),
        knowledge=knowledge_log_stream,
        session=session_key,
        debug=send_debug,
    )

    stream_chars = 0
    error_message: str | None = None
    source_entries = _collect_source_entries(knowledge_snippets)
    should_emit_sources = bool(source_entries) and (project_sources_enabled or sources_requested)

    response_chunks: list[str] = []

    async def event_stream():
        nonlocal stream_chars, error_message
        build_info = get_build_info()
        build_payload = {
            key: build_info.get(key)
            for key in ("version", "revision", "built_at", "built_at_iso")
            if build_info.get(key) is not None
        }
        components = build_info.get("components")
        if components:
            build_payload["components"] = components
        try:
            meta_payload = {
                "emotions_enabled": emotions_enabled,
                "session_id": session_key,
                "debug_enabled": send_debug,
                "debug_info_enabled": info_enabled,
                "debug_origin": debug_origin,
                "attachments_pending": planned_attachments_count,
                "model": effective_model,
                "reading_mode": reading_mode,
                "bitrix_used": bitrix_used,
                "mail_used": mail_used,
            }
            if bitrix_pending:
                meta_payload["bitrix_pending"] = bitrix_pending
            if mail_pending:
                meta_payload["mail_pending"] = mail_pending
            if mail_debug:
                meta_payload["mail_debug"] = mail_debug
            if build_payload:
                meta_payload["build"] = build_payload
            if reading_items_stream:
                meta_payload["reading_available"] = True
            else:
                meta_payload["reading_available"] = False
            yield "event: meta\n"
            yield f"data: {json.dumps(meta_payload, ensure_ascii=False)}\n\n"
            if reading_items_stream:
                yield "event: reading\n"
                yield f"data: {json.dumps({'items': reading_items_stream}, ensure_ascii=False)}\n\n"
            if should_emit_sources:
                yield "event: sources\n"
                yield f"data: {json.dumps({'entries': source_entries}, ensure_ascii=False)}\n\n"
            if send_debug:
                debug_start_payload = {
                    "stage": "begin",
                    "session_id": session_key,
                    "project": project_name,
                    "channel": channel_name,
                    "question_preview": question[:160],
                    "question_chars": len(question or ""),
                    "prompt_chars": len(prompt_base),
                    "knowledge_count": len(knowledge_snippets),
                    "knowledge_sources": knowledge_source_counts,
                    "knowledge_preview": knowledge_preview,
                    "attachments_planned": planned_attachments_count,
                    "emotions_enabled": emotions_enabled,
                    "model": effective_model,
                    "reading_mode": reading_mode,
                    "reading_available": bool(reading_items_stream),
                    "debug_origin": debug_origin,
                    "total_knowledge_chars": total_knowledge_chars,
                    "ts": time.time(),
                    "bitrix_used": bitrix_used,
                    "mail_used": mail_used,
                }
                if bitrix_debug:
                    debug_start_payload["bitrix"] = bitrix_debug
                if bitrix_pending:
                    debug_start_payload["bitrix_pending"] = bitrix_pending
                if mail_debug:
                    debug_start_payload["mail"] = mail_debug
                if mail_pending:
                    debug_start_payload["mail_pending"] = mail_pending
                if build_payload:
                    debug_start_payload["build"] = build_payload
                yield "event: debug\n"
                yield f"data: {json.dumps(debug_start_payload, ensure_ascii=False)}\n\n"
            if attachments_payload:
                for att in attachments_payload:
                    yield "event: attachment\n"
                    yield f"data: {json.dumps(att, ensure_ascii=False)}\n\n"
            async for token in llm_client.generate(prompt_base, model=model_override):
                stream_chars += len(token)
                response_chunks.append(token)
                payload = {
                    "text": token,
                    "role": "assistant",
                    "meta": {},
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as exc:  # keep connection graceful for the widget
            logger.warning("sse_generate_failed", error=str(exc))
            error_message = str(exc)
            yield "event: llm_error\ndata: generation_failed\n\n"
        finally:
            if send_debug:
                debug_summary_payload = {
                    "stage": "end",
                    "session_id": session_key,
                    "project": project_name,
                    "channel": channel_name,
                    "response_chars": stream_chars,
                    "attachments": len(attachments_payload),
                    "error": error_message,
                    "knowledge_count": len(knowledge_snippets),
                    "knowledge_sources": knowledge_source_counts,
                    "total_knowledge_chars": total_knowledge_chars,
                    "model": effective_model,
                    "emotions_enabled": emotions_enabled,
                    "ts": time.time(),
                    "bitrix_used": bitrix_used,
                    "mail_used": mail_used,
                }
                if bitrix_debug:
                    debug_summary_payload["bitrix"] = bitrix_debug
                if bitrix_pending:
                    debug_summary_payload["bitrix_pending"] = bitrix_pending
                if mail_debug:
                    debug_summary_payload["mail"] = mail_debug
                if mail_pending:
                    debug_summary_payload["mail_pending"] = mail_pending
                if build_payload:
                    debug_summary_payload["build"] = build_payload
                yield "event: debug\n"
                yield f"data: {json.dumps(debug_summary_payload, ensure_ascii=False)}\n\n"
            # Signal the client that stream has completed
            yield "event: end\ndata: [DONE]\n\n"
            await request.state.mongo.log_request_stat(
                project=project_name,
                question=question,
                response_chars=stream_chars,
                attachments=len(attachments_payload),
                prompt_chars=len(prompt_base),
                channel=channel_name,
                session_id=session_key,
                user_id=None,
                error=error_message,
            )
            final_text = "".join(response_chunks).strip()
            if session_key and final_text:
                last_entry = dialog_history[-1] if dialog_history else None
                if not last_entry or last_entry.get("role") != RoleEnum.assistant.value or last_entry.get("content") != final_text:
                    try:
                        await mongo_client.append_session_message(
                            contexts_collection,
                            session_key,
                            RoleEnum.assistant.value,
                            final_text,
                            project=project_name,
                            keep=keep_messages,
                        )
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "session_history_append_failed",
                            role="assistant",
                            session=session_key,
                            project=project_name,
                            error=str(exc),
                        )
                    else:
                        dialog_history.append({
                            "role": RoleEnum.assistant.value,
                            "content": final_text,
                        })

    model_header = effective_model
    headers = {"X-Model-Name": model_header}
    response = StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)
    if session_generated:
        response.set_cookie(
            "chat_session",
            session_base,
            max_age=30 * 24 * 3600,
            httponly=False,
            samesite="Lax",
        )
    return response


@llm_router.get("/project-config", response_class=ORJSONResponse)
async def project_config(request: Request, project: str | None = None) -> ORJSONResponse:
    """Expose project configuration for widgets and clients."""

    try:
        mongo_client = _get_mongo_client(request)
    except HTTPException as exc:
        logger.warning("project_config_mongo_unavailable", error=str(exc.detail))
        mongo_client = None

    normalized = _normalize_project(project)
    if not normalized:
        normalized = _normalize_project(backend_settings.project_name)

    project_obj: Project | None = None
    if normalized and mongo_client is not None:
        try:
            project_obj = await mongo_client.get_project(normalized)
        except Exception as exc:  # noqa: BLE001
            logger.warning("project_config_load_failed", project=normalized, error=str(exc))
        if project_obj is None:
            logger.info("project_config_missing", project=normalized)

    if project_obj is None and normalized:
        # create placeholder to keep defaults if project not stored yet
        project_obj = Project(name=normalized)

    voice_enabled = True
    voice_model = None
    llm_model = getattr(llm_client, "MODEL_NAME", None)
    title = None
    emotions_enabled = True
    debug_enabled = False
    debug_info_enabled = True
    knowledge_image_caption_enabled = True

    if project_obj:
        title = project_obj.title
        if project_obj.llm_model:
            llm_model = project_obj.llm_model
        if project_obj.llm_voice_enabled is not None:
            voice_enabled = bool(project_obj.llm_voice_enabled)
        if project_obj.llm_voice_model:
            voice_model = project_obj.llm_voice_model
        if project_obj.llm_emotions_enabled is not None:
            emotions_enabled = bool(project_obj.llm_emotions_enabled)
        if project_obj.debug_enabled is not None:
            debug_enabled = bool(project_obj.debug_enabled)
        if project_obj.debug_info_enabled is not None:
            debug_info_enabled = bool(project_obj.debug_info_enabled)
        if project_obj.knowledge_image_caption_enabled is not None:
            knowledge_image_caption_enabled = bool(project_obj.knowledge_image_caption_enabled)

    payload = {
        "project": normalized,
        "title": title,
        "llm_model": llm_model,
        "llm_voice_enabled": voice_enabled,
        "llm_voice_model": voice_model,
        "emotions_enabled": emotions_enabled,
        "debug_enabled": debug_enabled,
        "debug_info_enabled": debug_info_enabled,
        "knowledge_image_caption_enabled": knowledge_image_caption_enabled,
    }
    return ORJSONResponse(payload)

class CrawlRequest(BaseModel):
    start_url: str
    max_pages: int = 500
    max_depth: int = 3
    project: str | None = None
    domain: str | None = None
    collect_medex: bool | None = None
    collect_books: bool | None = None


def _spawn_crawler(
    start_url: str,
    max_pages: int,
    max_depth: int,
    *,
    project: str | None,
    domain: str | None,
    mongo_uri: str | None,
    collect_medex: bool | None,
    collect_books: bool | None,
) -> None:
    base_dir = Path(__file__).resolve().parent
    script = base_dir / "crawler" / "run_crawl.py"
    cmd = [
        sys.executable,
        str(script),
        "--url",
        start_url,
        "--max-pages",
        str(max_pages),
        "--max-depth",
        str(max_depth),
    ]
    if project:
        cmd.extend(["--project", project])
    if domain:
        cmd.extend(["--domain", domain])
    if mongo_uri:
        cmd.extend(["--mongo-uri", mongo_uri])
    if collect_medex is True:
        cmd.append("--collect-medex")
    elif collect_medex is False:
        cmd.append("--no-collect-medex")
    if collect_books is True:
        cmd.append("--collect-books")
    elif collect_books is False:
        cmd.append("--no-collect-books")
    env = os.environ.copy()
    python_paths = [str(base_dir)]
    existing_py_path = env.get("PYTHONPATH")
    if existing_py_path:
        python_paths.append(existing_py_path)
    env["PYTHONPATH"] = os.pathsep.join(python_paths)
    proc = subprocess.Popen(cmd, cwd=str(base_dir), env=env)
    try:
        (Path("/tmp") / "crawler.pid").write_text(str(proc.pid), encoding="utf-8")
    except Exception:
        pass


@crawler_router.post("/run", status_code=202)
async def run_crawler(
    req: CrawlRequest, background_tasks: BackgroundTasks, request: Request
) -> dict[str, str]:
    """Start the crawler in a background task."""

    parsed_host = urlparse.urlsplit(req.start_url).netloc
    allowed_domain = (req.domain or parsed_host or "").lower()
    project_name = _normalize_project(req.project) or _normalize_project(allowed_domain)
    if not project_name:
        raise HTTPException(status_code=400, detail="project is required")

    project = await request.state.mongo.get_project(project_name)
    if project is None:
        project = await request.state.mongo.upsert_project(
            Project(name=project_name, domain=allowed_domain or None)
        )

    background_tasks.add_task(
        _spawn_crawler,
        req.start_url,
        req.max_pages,
        req.max_depth,
        project=project_name,
        domain=allowed_domain or None,
        mongo_uri=backend_settings.mongo_uri,
        collect_medex=req.collect_medex,
        collect_books=req.collect_books,
    )
    return {
        "status": "started",
        "project": project_name,
        "domain": allowed_domain or None,
    }


@crawler_router.get("/status")
async def crawler_status(project: str | None = None) -> dict[str, object]:
    """Return current crawler and database status."""

    project_label = _normalize_project(project)
    data = status_dict(project_label)
    crawler = data.get("crawler") or {}
    note = get_crawler_note(project_label)
    if note:
        data["notes"] = note
    data.update(
        {
            "queued": crawler.get("queued", 0),
            "in_progress": crawler.get("in_progress", 0),
            "done": crawler.get("done", 0),
            "failed": crawler.get("failed", 0),
            "remaining": crawler.get("remaining", max(0, crawler.get("queued", 0) + crawler.get("in_progress", 0))),
            "recent_urls": crawler.get("recent_urls") or [],
            "last_url": crawler.get("last_url"),
        }
    )
    logger.info(
        "crawler_status_snapshot",
        project=project_label,
        ok=data.get("ok"),
        queued=data.get("queued"),
        in_progress=data.get("in_progress"),
        done=data.get("done"),
        failed=data.get("failed"),
        remaining=data.get("remaining"),
        last_url=data.get("last_url"),
        notes=data.get("notes"),
    )
    return data


@crawler_router.post("/reset", status_code=202)
async def crawler_reset(request: Request, project: str | None = None) -> dict[str, object]:
    """Reset crawler counters and recent URLs for the given project."""

    _require_super_admin(request)
    project_label = _normalize_project(project)
    removed = clear_crawler_state(project_label)
    return {"status": "reset", "project": project_label, "purged_jobs": removed}


@crawler_router.post("/deduplicate", status_code=200)
async def crawler_deduplicate(request: Request, project: str | None = None) -> dict[str, object]:
    """Deduplicate the recent URL list for the crawler."""

    _require_super_admin(request)
    project_label = _normalize_project(project)
    removed = deduplicate_recent_urls(project_label)
    return {"status": "deduplicated", "removed": removed, "project": project_label}


@crawler_router.post("/stop", status_code=202)
async def stop_crawler() -> dict[str, str]:
    """Attempt to stop the last started crawler process by PID file."""
    pid_path = Path("/tmp") / "crawler.pid"
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
    except Exception:
        return {"status": "unknown"}
    try:
        os.kill(pid, signal.SIGTERM)
        return {"status": "stopping", "pid": pid}
    except ProcessLookupError:
        return {"status": "not_running"}
    except Exception:
        return {"status": "error"}


@reading_router.get("/pages", response_model=ReadingPagesResponse)
async def reading_pages(
    request: Request,
    project: str | None = None,
    limit: int = 5,
    offset: int = 0,
    url: str | None = None,
    include_html: bool | None = None,
) -> ORJSONResponse:
    """Return book-reading payload for the requested project."""

    project_name = _normalize_project(project)
    if not project_name:
        raise HTTPException(status_code=400, detail="project_required")

    safe_limit = max(1, min(limit, READING_PAGE_MAX_LIMIT))
    safe_offset = max(0, offset)
    include_html_flag = bool(include_html) if include_html is not None else False

    mongo_client = _get_mongo_client(request)
    collection = getattr(request.state, "reading_collection", READING_COLLECTION_NAME)
    pages = await mongo_client.get_reading_pages(
        collection,
        project_name,
        limit=safe_limit,
        offset=safe_offset,
        url=url,
    )

    if not include_html_flag:
        for page in pages:
            page.html = None

    if url:
        total = 1 if pages else 0
    else:
        total = await mongo_client.count_reading_pages(collection, project_name)

    has_more = safe_offset + len(pages) < total

    response = ReadingPagesResponse(
        pages=pages,
        total=total,
        limit=safe_limit,
        offset=safe_offset,
        has_more=has_more,
    )
    return ORJSONResponse(response.model_dump(by_alias=True))


def _validate_voice_project(project: str | None) -> str:
    project_name = _normalize_project(project)
    if not project_name:
        raise HTTPException(status_code=400, detail="project_required")
    return project_name


def _queue_voice_training_job(job_id: str) -> bool:
    try:
        voice_train_model.delay(job_id)
        return True
    except VOICE_QUEUE_ERRORS as exc:
        logger.warning("voice_training_enqueue_failed", job_id=job_id, error=str(exc))
        return False


async def _run_voice_job_inline(job_id: str, mongo_client: MongoClient) -> None:
    stages = [
        (VoiceTrainingStatus.preparing, 0.1, "Готовим набор примеров", 0.6),
        (VoiceTrainingStatus.training, 0.65, "Обучаем голосовую модель", 1.2),
        (VoiceTrainingStatus.validating, 0.9, "Проверяем результат", 0.8),
    ]
    try:
        started_at = time.time()
        await mongo_client.update_voice_training_job(
            job_id,
            status=VoiceTrainingStatus.preparing,
            progress=0.05,
            message="Запускаем обучение",
            started_at=started_at,
        )
        for status, progress, message, delay in stages:
            await asyncio.sleep(delay)
            await mongo_client.update_voice_training_job(
                job_id,
                status=status,
                progress=progress,
                message=message,
            )
        await asyncio.sleep(0.6)
        await mongo_client.update_voice_training_job(
            job_id,
            status=VoiceTrainingStatus.completed,
            progress=1.0,
            message="Голосовой профиль готов",
            finished_at=time.time(),
        )
        logger.info("voice_training_inline_completed", job_id=job_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("voice_training_inline_failed", job_id=job_id, error=str(exc))
        await mongo_client.update_voice_training_job(
            job_id,
            status=VoiceTrainingStatus.failed,
            progress=0.0,
            message="Ошибка при обучении",
            finished_at=time.time(),
        )


async def _voice_job_watchdog(job_id: str, project: str, mongo_client: MongoClient) -> None:
    await asyncio.sleep(max(1.0, VOICE_JOB_STALE_TIMEOUT))
    try:
        jobs = await mongo_client.list_voice_training_jobs(project, limit=1)
    except Exception as exc:  # noqa: BLE001
        logger.warning("voice_training_watchdog_fetch_error", job_id=job_id, project=project, error=str(exc))
        return
    if not jobs:
        return
    job = jobs[0]
    if job.id != job_id:
        return
    if job.status == VoiceTrainingStatus.queued:
        logger.warning("voice_training_watchdog_inline", job_id=job_id, project=project)
        await _run_voice_job_inline(job_id, mongo_client)


def _validate_voice_payload(
    filename: str | None,
    content_type: str | None,
    payload: bytes,
) -> tuple[str, str | None, bytes]:
    safe_name = Path(filename or "sample").name
    if len(payload) == 0:
        raise HTTPException(status_code=400, detail="empty_sample")
    if len(payload) > VOICE_MAX_SAMPLE_BYTES:
        raise HTTPException(status_code=413, detail="sample_too_large")
    lowered = (content_type or "").lower() or None
    if lowered and lowered in VOICE_ALLOWED_CONTENT_TYPES:
        return safe_name, lowered, payload
    suffix = Path(safe_name).suffix.lower()
    if suffix in {".mp3", ".wav", ".flac", ".ogg", ".webm", ".m4a", ".aac"}:
        return safe_name, lowered, payload
    raise HTTPException(status_code=415, detail="unsupported_content_type")


@voice_router.get("/samples", response_model=VoiceSamplesResponse)
async def voice_samples(request: Request, project: str | None = None) -> ORJSONResponse:
    project_name = _validate_voice_project(project)
    mongo_client = _get_mongo_client(request)
    samples = await mongo_client.list_voice_samples(project_name)
    return ORJSONResponse(VoiceSamplesResponse(samples=samples).model_dump(by_alias=True))


@voice_router.post("/samples", response_model=VoiceSamplesResponse)
async def upload_voice_samples(
    request: Request,
    project: str = Form(...),
    files: list[UploadFile] = File(...),
) -> ORJSONResponse:
    project_name = _validate_voice_project(project)
    if not files:
        raise HTTPException(status_code=400, detail="files_required")

    mongo_client = _get_mongo_client(request)
    accepted: list[VoiceSample] = []
    for file in files:
        payload = await file.read()
        filename, content_type, payload = _validate_voice_payload(file.filename, file.content_type, payload)
        sample = await mongo_client.add_voice_sample(project_name, filename, payload, content_type)
        accepted.append(sample)
        await file.close()
    logger.info(
        "voice_samples_uploaded",
        project=project_name,
        uploaded=len(accepted),
    )
    samples = await mongo_client.list_voice_samples(project_name)
    return ORJSONResponse(VoiceSamplesResponse(samples=samples).model_dump(by_alias=True))


@voice_router.delete("/samples/{sample_id}", response_model=VoiceSamplesResponse)
async def delete_voice_sample(
    request: Request,
    sample_id: str,
    project: str | None = None,
) -> ORJSONResponse:
    project_name = _validate_voice_project(project)
    mongo_client = _get_mongo_client(request)
    removed = await mongo_client.delete_voice_sample(project_name, sample_id)
    if not removed:
        raise HTTPException(status_code=404, detail="sample_not_found")
    samples = await mongo_client.list_voice_samples(project_name)
    return ORJSONResponse(VoiceSamplesResponse(samples=samples).model_dump(by_alias=True))


@voice_router.get("/jobs", response_model=VoiceJobsResponse)
async def voice_jobs(request: Request, project: str | None = None, limit: int = 10) -> ORJSONResponse:
    project_name = _validate_voice_project(project)
    safe_limit = max(1, min(limit, 25))
    mongo_client = _get_mongo_client(request)
    jobs = await mongo_client.list_voice_training_jobs(project_name, limit=safe_limit)
    return ORJSONResponse(VoiceJobsResponse(jobs=jobs).model_dump(by_alias=True))


@voice_router.get("/status")
async def voice_training_status(request: Request, project: str | None = None) -> ORJSONResponse:
    project_name = _validate_voice_project(project)
    mongo_client = _get_mongo_client(request)
    jobs = await mongo_client.list_voice_training_jobs(project_name, limit=1)
    job = jobs[0] if jobs else None
    payload = job.model_dump(by_alias=True) if job else None
    return ORJSONResponse({"job": payload})


@voice_router.post("/train")
async def start_voice_training(request: Request, project: str = Form(...)) -> ORJSONResponse:
    project_name = _validate_voice_project(project)
    mongo_client = _get_mongo_client(request)
    samples = await mongo_client.list_voice_samples(project_name)
    if len(samples) < VOICE_MIN_SAMPLE_COUNT:
        raise HTTPException(
            status_code=400,
            detail=f"not_enough_samples:{len(samples)}/{VOICE_MIN_SAMPLE_COUNT}",
        )

    existing_jobs = await mongo_client.list_voice_training_jobs(project_name, limit=1)
    if existing_jobs:
        existing_job = existing_jobs[0]
        if existing_job.status in {
            VoiceTrainingStatus.queued,
            VoiceTrainingStatus.preparing,
            VoiceTrainingStatus.training,
            VoiceTrainingStatus.validating,
        }:
            payload = existing_job.model_dump(by_alias=True)
            updated_at = payload.get("updatedAt") or payload.get("updated_at")
            if updated_at is None:
                updated_at = existing_job.created_at or time.time()
            try:
                updated_at_value = float(updated_at)
            except (TypeError, ValueError):
                updated_at_value = time.time()

            age = time.time() - updated_at_value
            if age >= VOICE_JOB_STALE_TIMEOUT:
                logger.warning(
                    "voice_training_job_stale",
                    project=project_name,
                    job_id=existing_job.id,
                    status=existing_job.status.value,
                    age=age,
                )
                updated_job = await mongo_client.update_voice_training_job(
                    existing_job.id,
                    status=VoiceTrainingStatus.queued,
                    progress=existing_job.progress or 0.0,
                    message="Перезапускаем обучение",
                )
                if updated_job:
                    payload = updated_job.model_dump(by_alias=True)
                requeued = False
                if worker_mongo_client is not None and worker_settings is not None:
                    requeued = _queue_voice_training_job(existing_job.id)
                if requeued:
                    asyncio.create_task(_voice_job_watchdog(existing_job.id, project_name, mongo_client))
                else:
                    asyncio.create_task(_run_voice_job_inline(existing_job.id, mongo_client))
                return ORJSONResponse(
                    {"job": payload, "resumed": True, "detail": "job_resumed"},
                    status_code=202,
                )

            if existing_job.status == VoiceTrainingStatus.queued:
                asyncio.create_task(_voice_job_watchdog(existing_job.id, project_name, mongo_client))

            logger.info(
                "voice_training_job_active",
                project=project_name,
                job_id=existing_job.id,
                status=existing_job.status.value,
            )
            return ORJSONResponse(
                {"job": payload, "resumed": False, "detail": "job_in_progress"},
                status_code=202,
            )

    job = await mongo_client.create_voice_training_job(project_name)
    queued = False
    if worker_mongo_client is not None and worker_settings is not None:
        queued = _queue_voice_training_job(job.id)
    if queued:
        asyncio.create_task(_voice_job_watchdog(job.id, project_name, mongo_client))
    else:
        asyncio.create_task(_run_voice_job_inline(job.id, mongo_client))
    logger.info(
        "voice_training_queued",
        project=project_name,
        job_id=job.id,
        transport="celery" if queued else "inline",
    )
    return ORJSONResponse({"job": job.model_dump(by_alias=True), "detail": "job_queued"}, status_code=202)


@llm_router.get("/info")
def llm_info() -> dict[str, object]:
    """Expose basic LLM runtime details for the admin panel."""
    device = getattr(llm_client, "DEVICE", "unknown")
    model = getattr(llm_client, "MODEL_NAME", None)
    ollama = getattr(llm_client, "OLLAMA_BASE", None)
    backend = "ollama" if ollama else (device or "local")
    return {
        "model": model,
        "device": device,
        "backend": backend,
        "ollama_base": ollama,
    }


class LLMConfig(BaseModel):
    ollama_base: str | None = None
    model: str | None = None


@llm_router.post("/config", response_class=ORJSONResponse)
def llm_set_config(cfg: LLMConfig) -> ORJSONResponse:
    """Update LLM runtime parameters at runtime.

    This does not persist across process restarts; intended for quick ops.
    """
    if cfg.ollama_base is not None:
        llm_client.OLLAMA_BASE = cfg.ollama_base or None
    if cfg.model:
        llm_client.MODEL_NAME = cfg.model
    return ORJSONResponse(llm_info())


@llm_router.get("/ping")
async def llm_ping() -> dict[str, object]:
    """Ping the configured LLM backend.

    - If Ollama base is set, checks ``/api/tags``.
    - Otherwise returns enabled=False.
    """
    base = getattr(llm_client, "OLLAMA_BASE", None)
    if not base:
        return {"enabled": False, "reachable": None}
    import httpx
    url = f"{base.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            resp = await client.get(url)
            ok = bool(resp.status_code == 200)
            return {"enabled": True, "reachable": ok, "status": resp.status_code}
    except Exception as exc:
        return {"enabled": True, "reachable": False, "error": str(exc)}
