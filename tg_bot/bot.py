"""Telegram bot handlers using aiogram."""

from __future__ import annotations

from aiogram import Dispatcher, types
from aiogram.types import URLInputFile
from aiogram.filters import Command, CommandStart
import httpx
import structlog

from .config import get_settings
from .client import rag_answer

logger = structlog.get_logger(__name__)


async def start_handler(message: types.Message, project: str, session_id: str | None) -> None:
    """Send greeting with short instructions."""
    logger.info("/start", user=message.from_user.id)

    text = (
        "Привет! Отправьте вопрос в чат и я постараюсь помочь."
        " Используйте /help для списка команд."
    )
    await message.answer(text)


async def help_handler(message: types.Message, project: str, session_id: str | None) -> None:
    """Display available commands."""
    logger.info("/help", user=message.from_user.id)

    text = "/start - начать диалог\n/help - помощь"
    await message.answer(text)


async def text_handler(message: types.Message, project: str, session_id: str | None) -> None:
    """Handle regular user messages."""

    logger.info("user message", user=message.from_user.id)
    await message.chat.do("typing")
    try:
        response = await rag_answer(message.text or "", project=project, session_id=session_id)
        answer_text = response.get("text", "") if isinstance(response, dict) else str(response)
        attachments = response.get("attachments", []) if isinstance(response, dict) else []
        logger.info("answer ready", user=message.from_user.id, attachments=len(attachments))
    except ValueError:
        await message.answer("К сожалению, я не могу помочь с этим вопросом.")
        return

    chunks = [answer_text[i : i + 4000] for i in range(0, len(answer_text), 4000)]
    if chunks:
        for chunk in chunks:
            await message.answer(chunk)
    elif attachments:
        await message.answer("Нашёл подходящие документы:")

    for attachment in attachments:
        name = attachment.get("name") or "document"
        url = attachment.get("url")
        if not url:
            continue
        content_type = str(attachment.get("content_type") or "").lower()
        caption = attachment.get("description") or name
        try:
            if content_type.startswith("image/"):
                media = URLInputFile(url, filename=name)
                await message.answer_photo(media, caption=caption)
            else:
                media = URLInputFile(url, filename=name)
                kwargs = {"caption": caption} if caption and caption != name else {}
                await message.answer_document(media, **kwargs)
        except Exception as exc:  # noqa: BLE001
            logger.warning("attachment_send_failed", error=str(exc), name=name)
            await message.answer(f"Документ: {name}\n{url}")


async def unknown_handler(message: types.Message, project: str, session_id: str | None) -> None:
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
    dp.message.register(with_context(status_handler), Command("status"))
    dp.message.register(with_context(text_handler), lambda m: m.text and not m.text.startswith("/"))
    dp.message.register(with_context(unknown_handler))


async def status_handler(message: types.Message, project: str, session_id: str | None) -> None:
    """Return crawler and DB status from the API."""
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
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
        for k, v in data.get("crawler", {}).items():
            text.append(
                f"• {k}: queued={v.get('queued',0)} fetched={v.get('fetched',0)} "
                f"parsed={v.get('parsed',0)} indexed={v.get('indexed',0)} errors={v.get('errors',0)}"
            )
        await message.answer("\n".join(text), parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Не удалось получить статус: {e}")
