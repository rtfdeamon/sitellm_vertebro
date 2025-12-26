"""Telegram bot handlers using aiogram."""

from __future__ import annotations

import asyncio
import re
import time
from contextlib import suppress
from io import BytesIO
from typing import Any, Dict, List, Tuple

from aiogram import Dispatcher, types
from aiogram.types import URLInputFile, BufferedInputFile
from aiogram.filters import Command, CommandStart
import httpx
import structlog

from .config import get_settings
from .client import rag_answer

try:  # pragma: no cover - optional dependency inside slim container
    from settings import MongoSettings
    from mongo import MongoClient as AppMongoClient, NotFound
except ModuleNotFoundError:  # pragma: no cover - degrade gracefully when unavailable
    MongoSettings = None  # type: ignore[assignment]
    AppMongoClient = None  # type: ignore[assignment]

    class NotFound(Exception):  # type: ignore[assignment]
        """Fallback placeholder when mongo module is not bundled."""


logger = structlog.get_logger(__name__)

_FEATURE_CACHE: dict[str, tuple[float, dict[str, bool]]] = {}
_FEATURE_CACHE_TTL = 0.0
_FEATURE_CACHE_LOCK = asyncio.Lock()

POSITIVE_REPLIES = {
    'да', 'давай', 'ок', 'хочу', 'конечно', 'ага', 'отправь', 'да пожалуйста',
    'yes', 'yep', 'sure', 'send', 'please send', 'да, отправь', 'да отправь',
}
NEGATIVE_REPLIES = {
    'нет', 'не надо', 'не нужно', 'пока нет', 'no', 'not now', 'нет, спасибо',
}

PENDING_ATTACHMENTS: Dict[str, Dict[str, Any]] = {}
PENDING_BITRIX: Dict[str, Dict[str, Any]] = {}
PENDING_MAIL: Dict[str, Dict[str, Any]] = {}
GOD_MODE_SESSIONS: Dict[str, Dict[str, Any]] = {}

GOD_MODE_STEPS = [
    {
        "key": "project",
        "prompt": "1/8. Укажите идентификатор проекта (латиница, цифры, дефисы):",
        "validator": "slug",
        "required": True,
    },
    {
        "key": "title",
        "prompt": "2/8. Введите отображаемое название проекта (можно оставить пустым):",
        "validator": "text_optional",
        "required": False,
    },
    {
        "key": "domain",
        "prompt": "3/8. Укажите основной домен без протокола (например, example.com):",
        "validator": "domain",
        "required": True,
    },
    {
        "key": "start_url",
        "prompt": "4/8. Введите стартовый URL для краулинга (https://...):",
        "validator": "url",
        "required": True,
    },
    {
        "key": "llm_model",
        "prompt": "5/8. Укажите LLM модель (оставьте пустым, чтобы использовать настройку по умолчанию):",
        "validator": "text_optional",
        "required": False,
    },
    {
        "key": "llm_prompt",
        "prompt": "6/8. Введите стартовый промпт для проекта (можно пропустить):",
        "validator": "text_optional",
        "required": False,
    },
    {
        "key": "emotions",
        "prompt": "7/8. Включить эмоциональные ответы и эмодзи? (да/нет, по умолчанию да):",
        "validator": "bool_optional",
        "required": False,
    },
    {
        "key": "telegram_token",
        "prompt": "8/8. Введите токен Telegram-бота (формат 123456:ABC...):",
        "validator": "token",
        "required": True,
    },
]


def _pending_key(project: str | None, session_id: str | None, user_id: int | None) -> str:
    user_part = str(user_id or 'anon')
    return f"{(project or '').lower()}::{session_id or user_part}"


def _resolve_absolute_url(url: str | None, base_url: str) -> str | None:
    if not url:
        return None
    if url.startswith('http://') or url.startswith('https://'):
        return url
    if url.startswith('/'):
        return f"{base_url}{url}"
    return f"{base_url}/{url}"


async def _transcribe_audio(
    audio: bytes,
    mime_type: str | None,
    *,
    language: str | None,
    api_url: str,
    api_key: str | None,
    timeout: float,
) -> str:
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    files = {
        "file": (
            "voice.ogg",
            audio,
            mime_type or "audio/ogg",
        )
    }
    data = {}
    if language:
        data["language"] = language
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(api_url, data=data, files=files, headers=headers)
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError:
            text = response.text.strip()
            if not text:
                raise RuntimeError("empty_transcription")
            return text
    if isinstance(payload, dict):
        for key in ("text", "result", "transcription", "transcript"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    if isinstance(payload, str) and payload.strip():
        return payload.strip()
    raise RuntimeError("invalid_transcription_response")


async def _confirm_bitrix_plan(plan_id: str, project: str | None, session_id: str | None) -> dict[str, Any]:
    settings = get_settings()
    url = f"{settings.api_base_url}/api/v1/llm/bitrix/confirm"
    payload = {
        "plan_id": plan_id,
        "project": project,
        "session_id": session_id,
    }
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


async def _cancel_bitrix_plan(plan_id: str, project: str | None, session_id: str | None) -> None:
    settings = get_settings()
    url = f"{settings.api_base_url}/api/v1/llm/bitrix/cancel"
    payload = {
        "plan_id": plan_id,
        "project": project,
        "session_id": session_id,
    }
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()


async def _confirm_mail_plan(plan_id: str, project: str | None, session_id: str | None) -> dict[str, Any]:
    settings = get_settings()
    url = f"{settings.api_base_url}/api/v1/llm/mail/confirm"
    payload = {
        "plan_id": plan_id,
        "project": project,
        "session_id": session_id,
    }
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


async def _cancel_mail_plan(plan_id: str, project: str | None, session_id: str | None) -> None:
    settings = get_settings()
    url = f"{settings.api_base_url}/api/v1/llm/mail/cancel"
    payload = {
        "plan_id": plan_id,
        "project": project,
        "session_id": session_id,
    }
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()


async def _send_attachments(message: types.Message, attachments: List[Dict[str, Any]]) -> None:
    """Deliver queued attachments to the chat."""

    if not attachments:
        return

    settings = get_settings()
    base_api_url = str(settings.api_base_url).rstrip('/')
    download_timeout = settings.request_timeout
    http_client: httpx.AsyncClient | None = None
    mongo_client: AppMongoClient | None = None
    mongo_documents_collection: str | None = None

    def _trim_caption(value: str | None) -> str | None:
        if not value:
            return None
        trimmed = value.strip()
        if not trimmed:
            return None
        if len(trimmed) > 1024:
            trimmed = trimmed[:1021].rstrip()
            trimmed = f"{trimmed}…"
        return trimmed

    async def _get_client() -> httpx.AsyncClient:
        nonlocal http_client
        if http_client is None:
            http_client = httpx.AsyncClient(timeout=download_timeout)
        return http_client

    async def _get_mongo() -> Tuple[AppMongoClient, str]:
        nonlocal mongo_client, mongo_documents_collection
        if MongoSettings is None or AppMongoClient is None:
            raise RuntimeError("mongo_support_unavailable")
        if mongo_client is None:
            cfg = MongoSettings()
            mongo_client = AppMongoClient(
                cfg.host,
                cfg.port,
                cfg.username,
                cfg.password,
                cfg.database,
                cfg.auth,
            )
            mongo_documents_collection = cfg.documents
        assert mongo_documents_collection is not None
        return mongo_client, mongo_documents_collection

    try:
        for attachment in attachments:
            name = attachment.get('name') or 'документ'
            url = attachment.get('url')
            file_id = attachment.get('file_id') or attachment.get('id')
            content_type = str(attachment.get('content_type') or '').lower()
            description = attachment.get('description')
            fallback_caption = _trim_caption(name)
            caption = _trim_caption(description) or fallback_caption
            absolute_url = _resolve_absolute_url(url, base_api_url)
            file_bytes: bytes | None = None

            if file_id:
                try:
                    mongo, collection = await _get_mongo()
                    doc_meta, payload = await mongo.get_document_with_content(collection, file_id)
                    file_bytes = payload
                    if not content_type:
                        content_type = str(doc_meta.get('content_type') or '').lower()
                except NotFound:
                    file_bytes = None
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "attachment_mongo_fetch_failed",
                        error=str(exc),
                        file_id=file_id,
                    )

            download_url = None
            if file_bytes is None:
                if file_id:
                    download_url = absolute_url or f"{base_api_url}/api/v1/admin/knowledge/documents/{file_id}"
                elif absolute_url:
                    download_url = absolute_url

                if download_url:
                    try:
                        client = await _get_client()
                        response = await client.get(download_url)
                        response.raise_for_status()
                        file_bytes = response.content
                        if not content_type:
                            content_type = str(response.headers.get('content-type') or '').lower()
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "attachment_download_failed",
                            error=str(exc),
                            file_id=file_id,
                            url=download_url,
                        )
                        file_bytes = None

            try:
                if file_bytes is not None:
                    media = BufferedInputFile(file_bytes, filename=name)
                    if content_type.startswith('image/'):
                        await message.answer_photo(media, caption=caption)
                    else:
                        extra = {"caption": caption} if caption and caption != fallback_caption else {}
                        await message.answer_document(media, **extra)
                    continue

                if absolute_url:
                    media = URLInputFile(absolute_url, filename=name)
                    if content_type.startswith('image/'):
                        await message.answer_photo(media, caption=caption)
                    else:
                        extra = {"caption": caption} if caption and caption != fallback_caption else {}
                        await message.answer_document(media, **extra)
                else:
                    text = f"Документ: {name}"
                    if description:
                        text += f"\n{description}"
                    await message.answer(text)
            except Exception as exc:  # noqa: BLE001
                logger.warning("attachment_send_failed", error=str(exc), name=name)
                fallback_url = absolute_url or (file_id and f"{base_api_url}/api/v1/admin/knowledge/documents/{file_id}")
                if fallback_url:
                    await message.answer(f"Документ: {name}\n{fallback_url}")
                elif description:
                    await message.answer(f"Документ: {name}\n{description}")
    finally:
        if http_client is not None:
            await http_client.aclose()
        if mongo_client is not None:
            await mongo_client.close()


def _god_mode_key(message: types.Message) -> str:
    return f"{message.chat.id}:{message.from_user.id}"


def _validate_god_mode_input(kind: str, value: str) -> Any:
    text = value.strip()
    if kind == "slug":
        slug = re.sub(r"[^a-zA-Z0-9_-]", "", text).lower()
        if not slug:
            raise ValueError("Используйте латиницу, цифры и дефисы")
        return slug
    if kind == "text_optional":
        return text or None
    if kind == "domain":
        domain = text.lower().strip()
        # Remove protocol if user added it by mistake
        if domain.startswith("http://"):
            domain = domain[7:]
        elif domain.startswith("https://"):
            domain = domain[8:]
        # Remove trailing slash
        domain = domain.rstrip("/")
        if not domain or " " in domain:
            raise ValueError("Введите домен без протокола, например example.com")
        # Check for valid domain format (must have at least one dot, or be localhost/IP)
        if "." not in domain and domain != "localhost" and not domain.replace(":", "").isdigit():
            raise ValueError("Введите корректный домен, например example.com")
        return domain
    if kind == "url":
        if not text.lower().startswith("http://") and not text.lower().startswith("https://"):
            raise ValueError("URL должен начинаться с http:// или https://")
        # Check that URL has a domain after the protocol
        from urllib.parse import urlparse
        parsed = urlparse(text)
        if not parsed.netloc or len(parsed.netloc) < 3:
            raise ValueError("Введите полный URL с доменом, например https://example.com")
        return text
    if kind == "bool_optional":
        if not text:
            return True
        lower = text.lower()
        if lower in {"да", "yes", "y", "true", "1", "+"}:
            return True
        if lower in {"нет", "no", "n", "false", "0", "-"}:
            return False
        raise ValueError("Введите 'да' или 'нет'")
    if kind == "token":
        if len(text) < 20 or ":" not in text:
            raise ValueError("Похоже, токен неверный. Формат 123456:ABC...")
        return text
    return text


async def _god_mode_command(
    message: types.Message,
    project: str,
    session_id: str | None,
    **_: object,
) -> None:
    key = _god_mode_key(message)
    GOD_MODE_SESSIONS[key] = {
        "step": 0,
        "data": {},
        "project": project,
        "session_id": session_id,
        "started_at": time.time(),
    }
    await message.answer(
        "👑 Режим супер-админа активирован. Ответы 'cancel' прерывают сценарий."
        "\n\nСейчас настроим новый проект и Telegram-бота."
    )
    await message.answer(GOD_MODE_STEPS[0]["prompt"])


async def _get_project_features(project: str | None) -> dict[str, bool]:
    """Return cached feature flags for the given project."""

    if not project:
        return {
            "emotions_enabled": True,
            "debug_enabled": False,
            "debug_info_enabled": True,
        }

    key = project.lower()
    now = time.time()

    settings = get_settings()
    base_url = str(settings.api_base_url).rstrip("/")
    api_url = f"{base_url}/api/v1/llm/project-config"
    emotions_enabled = True
    debug_enabled = False
    debug_info_enabled = True

    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            resp = await client.get(api_url, params={"project": key})
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "project_features_fetch_failed",
            project=project,
            error=str(exc),
        )
    else:
        emotions_enabled = bool(data.get("emotions_enabled", True))
        debug_enabled = bool(data.get("debug_enabled", False))
        debug_info_enabled = bool(data.get("debug_info_enabled", True))

    features = {
        "emotions_enabled": emotions_enabled,
        "debug_enabled": debug_enabled,
        "debug_info_enabled": debug_info_enabled,
    }
    async with _FEATURE_CACHE_LOCK:
        _FEATURE_CACHE[key] = (now, features.copy())
    return features


async def _typing_indicator(message: types.Message, stop_event: asyncio.Event) -> None:
    """Continuously send the typing status until ``stop_event`` is set."""

    try:
        while not stop_event.is_set():
            try:
                await message.chat.do("typing")
            except Exception as exc:  # noqa: BLE001
                logger.debug("typing_indicator_failed", error=str(exc))
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=4.0)
            except asyncio.TimeoutError:
                continue
    except asyncio.CancelledError:
        raise


async def _complete_god_mode(message: types.Message, session: Dict[str, Any]) -> None:
    data = session.get("data", {})
    project_slug = data.get("project")
    domain = data.get("domain")
    start_url = data.get("start_url")
    llm_model = data.get("llm_model") or None
    llm_prompt = data.get("llm_prompt") or None
    emotions_enabled = data.get("emotions") if "emotions" in data else True
    telegram_token = data.get("telegram_token")
    if not (project_slug and domain and start_url and telegram_token):
        await message.answer("⚠️ Недостаточно данных для создания бота. Попробуйте заново.")
        return

    settings = get_settings()
    base_url = str(settings.api_base_url).rstrip('/')
    status_messages = []

    payload_project = {
        "name": project_slug,
        "title": data.get("title") or None,
        "domain": domain,
        "llm_model": llm_model,
        "llm_prompt": llm_prompt,
        "llm_emotions_enabled": emotions_enabled,
    }

    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            resp = await client.post(f"{base_url}/api/v1/admin/projects", json=payload_project)
            if not resp.ok:
                raise RuntimeError(f"Создание проекта: {resp.status_code} {await resp.text()}")
            status_messages.append("• Проект сохранён")

            cfg_payload = {"token": telegram_token, "auto_start": True}
            resp = await client.post(
                f"{base_url}/api/v1/admin/projects/{project_slug}/telegram/config",
                json=cfg_payload,
            )
            if not resp.ok:
                raise RuntimeError(f"Настройка Telegram: {resp.status_code} {await resp.text()}")
            status_messages.append("• Токен Telegram сохранён")

            resp = await client.post(
                f"{base_url}/api/v1/admin/projects/{project_slug}/telegram/start",
                json={"token": telegram_token, "auto_start": True},
            )
            if not resp.ok:
                raise RuntimeError(f"Запуск Telegram-бота: {resp.status_code} {await resp.text()}")
            status_messages.append("• Бот запущен")

            crawler_payload = {
                "start_url": start_url,
                "max_depth": 2,
                "max_pages": 200,
                "project": project_slug,
                "domain": domain,
            }
            resp = await client.post(f"{base_url}/api/v1/crawler/run", json=crawler_payload)
            if not resp.ok:
                raise RuntimeError(f"Старт краулинга: {resp.status_code} {await resp.text()}")
            status_messages.append("• Краулер запущен")
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"⚠️ Не удалось завершить настройку: {exc}")
        return

    features_snapshot = await _get_project_features(project_slug)
    features_snapshot["emotions_enabled"] = emotions_enabled
    async with _FEATURE_CACHE_LOCK:
        _FEATURE_CACHE[project_slug] = (time.time(), features_snapshot.copy())

    summary = "\n".join(status_messages)
    await message.answer(
        "✅ Готово!" \
        + f"\n{summary}\n" \
        + f"\nАдмин-панель: /admin?project={project_slug}"
    )


async def start_handler(
    message: types.Message,
    project: str,
    session_id: str | None,
    **_: object,
) -> None:
    """Send greeting with short instructions."""
    logger.info("/start", user=message.from_user.id)

    text = (
        "Привет! Отправьте вопрос в чат и я постараюсь помочь."
        " Используйте /help для списка команд."
    )
    await message.answer(text)


async def help_handler(
    message: types.Message,
    project: str,
    session_id: str | None,
    **_: object,
) -> None:
    """Display available commands."""
    logger.info("/help", user=message.from_user.id)

    text = "/start - начать диалог\n/help - помощь\n/rtfdeamon_god_mode - режим супер-админа"
    await message.answer(text)


async def text_handler(
    message: types.Message,
    project: str,
    session_id: str | None,
    *,
    override_text: str | None = None,
    **_: object,
) -> None:
    """Handle regular user messages."""

    logger.info("user message", user=message.from_user.id)
    incoming_text = override_text if override_text is not None else (message.text or "")
    raw_text = incoming_text.strip()

    god_key = _god_mode_key(message)
    god_session = GOD_MODE_SESSIONS.get(god_key)
    if god_session:
        if raw_text.lower() in {"cancel", "отмена"}:
            GOD_MODE_SESSIONS.pop(god_key, None)
            await message.answer("❌ Режим супер-админа завершён.")
            return
        step_index = god_session["step"]
        if 0 <= step_index < len(GOD_MODE_STEPS):
            step = GOD_MODE_STEPS[step_index]
            try:
                value = _validate_god_mode_input(step["validator"], raw_text)
            except ValueError as exc:
                await message.answer(f"⚠️ {exc}. Попробуйте ещё раз.")
                return
            god_session["data"][step["key"]] = value
            god_session["step"] += 1
            if god_session["step"] >= len(GOD_MODE_STEPS):
                await _complete_god_mode(message, god_session)
                GOD_MODE_SESSIONS.pop(god_key, None)
            else:
                await message.answer(GOD_MODE_STEPS[god_session["step"]]["prompt"])
            return

    normalized_text = raw_text.lower()
    pending_key = _pending_key(project, session_id, message.from_user.id)
    pending_bitrix = PENDING_BITRIX.get(pending_key)
    if pending_bitrix:
        if normalized_text in POSITIVE_REPLIES:
            try:
                await _confirm_bitrix_plan(
                    pending_bitrix["plan_id"],
                    project,
                    session_id,
                )
                await message.answer(
                    "✅ Задача отправлена в Bitrix24"
                    if pending_bitrix.get("emotions", True)
                    else "Задача отправлена в Bitrix24."
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("bitrix_confirm_failed", error=str(exc))
                await message.answer(
                    "⚠️ Не удалось отправить задачу в Bitrix. Попробуйте позже."
                )
            finally:
                PENDING_BITRIX.pop(pending_key, None)
            return
        if normalized_text in NEGATIVE_REPLIES:
            try:
                await _cancel_bitrix_plan(
                    pending_bitrix["plan_id"],
                    project,
                    session_id,
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("bitrix_cancel_failed", error=str(exc))
            await message.answer(
                "🛑 Задача не будет создана"
                if pending_bitrix.get("emotions", True)
                else "Создание задачи отменено."
            )
            PENDING_BITRIX.pop(pending_key, None)
            return
        if normalized_text:
            try:
                await _cancel_bitrix_plan(
                    pending_bitrix["plan_id"],
                    project,
                    session_id,
                )
            except Exception:
                pass
            PENDING_BITRIX.pop(pending_key, None)

    pending_mail = PENDING_MAIL.get(pending_key)
    if pending_mail:
        mail_emotions = pending_mail.get("emotions", True)
        if normalized_text in POSITIVE_REPLIES:
            try:
                await _confirm_mail_plan(
                    pending_mail["plan_id"],
                    project,
                    session_id,
                )
                await message.answer(
                    "✉️ Письмо отправлено!"
                    if mail_emotions
                    else "Письмо отправлено."
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("mail_confirm_failed", error=str(exc))
                await message.answer(
                    "⚠️ Не удалось отправить письмо. Попробуйте позже."
                )
            finally:
                PENDING_MAIL.pop(pending_key, None)
            return
        if normalized_text in NEGATIVE_REPLIES:
            try:
                await _cancel_mail_plan(
                    pending_mail["plan_id"],
                    project,
                    session_id,
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("mail_cancel_failed", error=str(exc))
            await message.answer(
                "🛑 Письмо не будет отправлено."
                if mail_emotions
                else "Письмо не будет отправлено."
            )
            PENDING_MAIL.pop(pending_key, None)
            return
        if normalized_text:
            try:
                await _cancel_mail_plan(
                    pending_mail["plan_id"],
                    project,
                    session_id,
                )
            except Exception:
                pass
            PENDING_MAIL.pop(pending_key, None)

    pending_pack = PENDING_ATTACHMENTS.get(pending_key)
    if pending_pack:
        attachments_to_send = pending_pack.get('attachments', [])
        pending_emotions = pending_pack.get('emotions', True)
        if normalized_text in POSITIVE_REPLIES:
            await message.answer(
                "📎 Отправляю документы!" if pending_emotions else "Отправляю документы."
            )
            await _send_attachments(message, attachments_to_send)
            await message.answer(
                "Готово! Если нужен ещё документ — просто скажите 😊"
                if pending_emotions
                else "Готово. Могу помочь чем-то ещё?"
            )
            PENDING_ATTACHMENTS.pop(pending_key, None)
            return
        if normalized_text in NEGATIVE_REPLIES:
            await message.answer(
                "Хорошо, не буду отправлять 📁" if pending_emotions else "Понял, не отправляю документ."
            )
            PENDING_ATTACHMENTS.pop(pending_key, None)
            return
        if normalized_text:
            PENDING_ATTACHMENTS.pop(pending_key, None)

    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(_typing_indicator(message, stop_typing))
    try:
        settings = get_settings()
        backend_hint = str(settings.backend_url)
        features = await _get_project_features(project)
        emotions_enabled = features.get("emotions_enabled", True)
        debug_info_allowed = features.get("debug_info_enabled", False)
        debug_summary_allowed = features.get("debug_enabled", False)
        try:
            response = await rag_answer(
                incoming_text,
                project=project,
                session_id=session_id,
                debug=debug_summary_allowed,
            )
        except ValueError:
            stop_typing.set()
            await message.answer("🚫 Ответ заблокирован фильтром безопасности.")
            await message.answer("К сожалению, я не могу помочь с этим вопросом.")
            return
        except Exception as exc:  # noqa: BLE001
            stop_typing.set()
            logger.exception("rag_answer_failed", user=message.from_user.id, error=str(exc))
            await message.answer(f"⚠️ Ошибка при обращении к бэкенду: {exc}")
            await message.answer("Сервис сейчас недоступен, попробуйте позже.")
            return

        stop_typing.set()
        answer_text = response.get("text", "") if isinstance(response, dict) else str(response)
        attachments = response.get("attachments", []) if isinstance(response, dict) else []
        meta = response.get("meta", {}) if isinstance(response, dict) else {}
        emotions_enabled = bool(meta.get('emotions_enabled', emotions_enabled))
        debug_summary_allowed = bool(meta.get('debug_enabled', debug_summary_allowed))
        debug_info_allowed = bool(meta.get('debug_info_enabled', debug_info_allowed))
        if project:
            async with _FEATURE_CACHE_LOCK:
                _FEATURE_CACHE[project.lower()] = (
                    time.time(),
                    {
                        "emotions_enabled": emotions_enabled,
                        "debug_enabled": debug_summary_allowed,
                        "debug_info_enabled": debug_info_allowed,
                    },
                )
        logger.info(
            "answer ready",
            user=message.from_user.id,
            attachments=len(attachments),
            session=meta.get('session_id'),
        )

        bitrix_pending_meta = meta.get('bitrix_pending') if isinstance(meta, dict) else None
        if isinstance(bitrix_pending_meta, dict) and bitrix_pending_meta.get('plan_id'):
            PENDING_BITRIX[pending_key] = {
                "plan_id": bitrix_pending_meta.get('plan_id'),
                "method": bitrix_pending_meta.get('method'),
                "preview": bitrix_pending_meta.get('preview'),
                "emotions": emotions_enabled,
            }
            preview_text = bitrix_pending_meta.get('preview') or 'Подтвердите создание задачи в Bitrix24.'
            prompt_text = (
                f"{preview_text}\n\nОтправить задачу в Bitrix? Ответьте «да» или «нет»."
                if emotions_enabled
                else f"{preview_text}\n\nОтправить задачу в Bitrix? Ответьте 'да' или 'нет'."
            )
            await message.answer(prompt_text)

        mail_pending_meta = meta.get('mail_pending') if isinstance(meta, dict) else None
        if isinstance(mail_pending_meta, dict) and mail_pending_meta.get('plan_id'):
            PENDING_MAIL[pending_key] = {
                "plan_id": mail_pending_meta.get('plan_id'),
                "preview": mail_pending_meta.get('preview'),
                "emotions": emotions_enabled,
            }
            preview_text = mail_pending_meta.get('preview') or 'Подтвердите отправку письма.'
            prompt_text = (
                f"{preview_text}\n\nОтправить письмо? Ответьте «да» или «нет»."
                if emotions_enabled
                else f"{preview_text}\n\nОтправить письмо? Ответьте 'да' или 'нет'."
            )
            await message.answer(prompt_text)

        chunks = [answer_text[i : i + 4000] for i in range(0, len(answer_text), 4000)]
        if debug_info_allowed:
            info_lines = [
                "🛰️ Отправляю запрос бэкенду",
                f"• проект: {project or '—'}",
                f"• endpoint: {backend_hint}",
                f"• эмоции: {'включены ✨' if emotions_enabled else 'выключены'}",
            ]
            if debug_summary_allowed:
                info_lines.append("• отладка: включена")
            await message.answer("\n".join(info_lines))

        if chunks:
            for chunk in chunks:
                await message.answer(chunk)

        if debug_summary_allowed:
            summary_lines: List[str] = [
                "✅ Ответ получен",
                f"• символов: {len(answer_text)} (SSE: {meta.get('chars', '—')})",
                f"• вложений: {len(attachments)}",
                f"• SSE строк: {meta.get('lines', '—')}",
                f"• эмоции: {'включены ✨' if emotions_enabled else 'выключены'}",
            ]

            model_name = meta.get('model')
            if model_name:
                summary_lines.append(f"• модель: {model_name}")

            last_debug_event: Dict[str, Any] | None = None
            debug_events = meta.get('debug')
            if isinstance(debug_events, list) and debug_events:
                maybe_last = debug_events[-1]
                if isinstance(maybe_last, dict):
                    last_debug_event = maybe_last

            session_label = meta.get('session_id') or (last_debug_event.get('session_id') if last_debug_event else None)
            if session_label:
                summary_lines.append(f"• сессия: {session_label}")

            summary_lines.append("• отладка: включена")
            debug_origin = meta.get('debug_origin') or (last_debug_event.get('debug_origin') if last_debug_event else None)
            if debug_origin:
                summary_lines.append(f"• источник отладки: {debug_origin}")

            if last_debug_event:
                sources = last_debug_event.get('knowledge_sources')
                knowledge_count = last_debug_event.get('knowledge_count')
                if isinstance(knowledge_count, int):
                    if isinstance(sources, dict) and sources:
                        formatted_sources = ", ".join(f"{k}:{v}" for k, v in sources.items())
                        summary_lines.append(f"• знания: {knowledge_count} ({formatted_sources})")
                    else:
                        summary_lines.append(f"• знания: {knowledge_count}")
                debug_origin = last_debug_event.get('debug_origin') or meta.get('debug_origin')
                if debug_origin:
                    summary_lines.append(f"• отладка: {debug_origin}")
                error_text = last_debug_event.get('error')
                if error_text:
                    summary_lines.append(f"• ошибка: {error_text}")

            await message.answer(
                "\n".join(summary_lines)
                if (answer_text or attachments)
                else "ℹ️ Бэкенд не вернул текста или вложений"
            )
    finally:
        stop_typing.set()
        with suppress(asyncio.CancelledError):
            await typing_task

    if attachments:
        PENDING_ATTACHMENTS[pending_key] = {
            "attachments": attachments,
            "emotions": emotions_enabled,
        }
        preview_lines: List[str] = []
        for idx, att in enumerate(attachments, 1):
            title = att.get('name') or f'Документ {idx}'
            desc = att.get('description') or ''
            if len(desc) > 120:
                desc = desc[:117].rstrip() + '…'
            line = f"• {title}"
            if desc:
                line += f" — {desc}"
            preview_lines.append(line)
        confirm_body = "\n".join(preview_lines)
        prompt_text = (
            f"📎 Кажется, этот материал пригодится:\n{confirm_body}\nОтправить? Ответьте «да» — и пришлю, «нет» — чтобы пропустить."
            if emotions_enabled
            else f"Нашёл документы:\n{confirm_body}\nНапишите \"да\" для отправки или \"нет\", если они не нужны."
        )
        await message.answer(prompt_text)
    else:
        PENDING_ATTACHMENTS.pop(pending_key, None)


async def voice_handler(
    message: types.Message,
    project: str,
    session_id: str | None,
    **_: object,
) -> None:
    """Handle user voice messages by transcribing them to text."""

    settings = get_settings()
    stt_url = getattr(settings, "speech_to_text_url", None)
    if not stt_url:
        await message.answer("🎙️ Голосовые сообщения пока не поддерживаются. Попробуйте отправить текст.")
        return

    if not message.voice:
        await message.answer("Не удалось получить голосовое сообщение.")
        return

    buffer = BytesIO()
    try:
        await message.bot.download(message.voice, buffer)
    except Exception as exc:  # noqa: BLE001
        logger.warning("voice_download_failed", error=str(exc))
        await message.answer("⚠️ Не удалось скачать голосовое сообщение. Попробуйте ещё раз.")
        return

    audio_bytes = buffer.getvalue()
    if not audio_bytes:
        await message.answer("⚠️ Голосовое сообщение пустое.")
        return

    try:
        transcript = await _transcribe_audio(
            audio_bytes,
            message.voice.mime_type,
            language=getattr(settings, "speech_to_text_language", None),
            api_url=str(stt_url),
            api_key=getattr(settings, "speech_to_text_api_key", None),
            timeout=settings.request_timeout,
        )
    except httpx.HTTPStatusError as exc:  # pragma: no cover - network dependent
        logger.warning("voice_transcribe_http_error", status=exc.response.status_code)
        await message.answer("⚠️ Сервис распознавания временно недоступен.")
        return
    except Exception as exc:  # noqa: BLE001
        logger.warning("voice_transcribe_failed", error=str(exc))
        await message.answer("⚠️ Не удалось распознать голосовое сообщение.")
        return

    transcript = transcript.strip()
    if not transcript:
        await message.answer("⚠️ Не получилось понять сообщение. Попробуйте сказать чётче или отправьте текст.")
        return

    await message.answer(f"📝 Распознала: {transcript}")
    await text_handler(
        message,
        project,
        session_id,
        override_text=transcript,
    )


async def unknown_handler(
    message: types.Message,
    project: str,
    session_id: str | None,
    **_: object,
) -> None:
    """Reply to unsupported commands."""
    user_id = getattr(getattr(message, "from_user", None), "id", None)
    logger.info("unknown command", user=user_id)
    await message.answer("Unknown command")


def setup(dp: Dispatcher, project: str, session_provider) -> None:
    """Register message handlers on the dispatcher."""

    logger.info("register handlers", project=project)

    def with_context(handler):
        async def wrapper(message: types.Message, *args, **kwargs):
            user_id = getattr(getattr(message, "from_user", None), "id", None)
            session_id = await session_provider.get_session(project, user_id)
            return await handler(message, project, session_id, *args, **kwargs)

        return wrapper

    dp.message.register(with_context(start_handler), CommandStart())
    dp.message.register(with_context(help_handler), Command("help"))
    dp.message.register(with_context(_god_mode_command), Command("rtfdeamon_god_mode"))
    dp.message.register(with_context(status_handler), Command("status"))
    dp.message.register(with_context(voice_handler), lambda m: getattr(m, "voice", None) is not None)
    dp.message.register(with_context(text_handler), lambda m: m.text and not m.text.startswith("/"))
    dp.message.register(with_context(unknown_handler))


async def status_handler(
    message: types.Message,
    project: str,
    session_id: str | None,
    **_: object,
) -> None:
    """Return crawler and DB status from the API."""
    settings = get_settings()
    try:
        if settings.backend_verify_ssl:
            if getattr(settings, "backend_ca_path", None):
                verify_option: Any = str(settings.backend_ca_path)
            else:
                verify_option = True
        else:
            verify_option = False

        async with httpx.AsyncClient(timeout=settings.request_timeout, verify=verify_option) as client:
            resp = await client.get(settings.resolve_status_url(), params={"project": project})
        resp.raise_for_status()
        data = resp.json()
        mongo = data["db"].get("mongo_collections", {})
        qpts = data["db"].get("qdrant_points")
        text = ["<b>DB</b>"]
        for k, v in mongo.items():
            text.append(f"• {k}: {v}")
        text.append(f"• qdrant_points: {qpts}")
        text.append("\n<b>Crawler</b>")
        crawler_data = data.get("crawler") or {}
        if crawler_data and all(isinstance(v, dict) for v in crawler_data.values()):
            items = crawler_data.items()
        else:
            items = []
            if crawler_data:
                items.append((project or "main", crawler_data))
            elif any(key in data for key in ("queued", "in_progress", "done", "failed")):
                items.append(
                    (
                        project or "main",
                        {
                            "queued": data.get("queued", 0),
                            "in_progress": data.get("in_progress", 0),
                            "parsed": data.get("parsed", 0),
                            "indexed": data.get("indexed", 0),
                            "errors": data.get("failed", 0),
                            "remaining": data.get("remaining"),
                        },
                    )
                )
        if not items:
            items = [(project or "main", {})]
        for name, counters in items:
            if not isinstance(counters, dict):
                continue
            queued = counters.get("queued", 0)
            fetched = counters.get("fetched", data.get("done", 0))
            parsed = counters.get("parsed", 0)
            indexed = counters.get("indexed", 0)
            errors = counters.get("errors", counters.get("failed", 0))
            remaining = counters.get("remaining")
            if remaining is None:
                remaining = queued + counters.get("in_progress", data.get("in_progress", 0))
            text.append(
                "• {name}: queued={queued} left={remaining} "
                "fetched={fetched} parsed={parsed} indexed={indexed} errors={errors}".format(
                    name=name,
                    queued=queued,
                    remaining=max(int(remaining), 0),
                    fetched=fetched,
                    parsed=parsed,
                    indexed=indexed,
                    errors=errors,
                )
            )
        await message.answer("\n".join(text), parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Не удалось получить статус: {e}")
