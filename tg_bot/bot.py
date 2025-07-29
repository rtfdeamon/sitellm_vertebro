"""Telegram bot handlers using aiogram."""

from __future__ import annotations

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
import structlog

logger = structlog.get_logger(__name__)

from .client import rag_answer


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
    dp.message.register(text_handler, lambda m: m.text and not m.text.startswith("/"))
    dp.message.register(unknown_handler)
