"""Telegram bot handlers using aiogram."""

from __future__ import annotations

from aiogram import Dispatcher, types
from aiogram.filters import Command, CommandStart
import httpx
import structlog

from .config import get_settings
from .client import rag_answer

logger = structlog.get_logger(__name__)


async def start_handler(message: types.Message) -> None:
    """Send greeting with short instructions."""
    logger.info("/start", user=message.from_user.id)

    text = (
        "Привет! Отправьте вопрос в чат и я постараюсь помочь."
        " Используйте /help для списка команд."
    )
    await message.answer(text)


async def help_handler(message: types.Message) -> None:
    """Display available commands."""
    logger.info("/help", user=message.from_user.id)

    text = "/start - начать диалог\n/help - помощь"
    await message.answer(text)


async def text_handler(message: types.Message) -> None:
    """Handle regular user messages."""

    logger.info("user message", user=message.from_user.id)
    await message.chat.do("typing")
    try:
        answer = await rag_answer(message.text or "")
        logger.info("answer ready", user=message.from_user.id)
    except ValueError:
        await message.answer("К сожалению, я не могу помочь с этим вопросом.")
        return

    chunks = [answer[i : i + 4000] for i in range(0, len(answer), 4000)]
    for chunk in chunks:
        await message.answer(chunk)


async def unknown_handler(message: types.Message) -> None:
    """Reply to unsupported commands."""
    user_id = getattr(getattr(message, "from_user", None), "id", None)
    logger.info("unknown command", user=user_id)
    await message.answer("Unknown command")


def setup(dp: Dispatcher) -> None:
    """Register message handlers on the dispatcher."""

    logger.info("register handlers")
    dp.message.register(start_handler, CommandStart())
    dp.message.register(help_handler, Command("help"))
    dp.message.register(status_handler, Command("status"))
    dp.message.register(text_handler, lambda m: m.text and not m.text.startswith("/"))
    dp.message.register(unknown_handler)


async def status_handler(message: types.Message) -> None:
    """Return crawler and DB status from the API."""
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            resp = await client.get(f"{settings.api_base_url}/status")
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
