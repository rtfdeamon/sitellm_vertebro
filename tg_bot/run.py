"""Entry point for running the Telegram bot."""

from __future__ import annotations

import asyncio
import os
import sys

from aiogram import Bot, Dispatcher
import structlog

from observability.logging import configure_logging

configure_logging()
logger = structlog.get_logger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
if not TOKEN:
    logger.warning("[telegram] TELEGRAM_BOT_TOKEN is empty — bot disabled")
    sys.exit(0)

from .bot import setup
from .config import get_settings


async def init_bot() -> None:
    """Initialize bot and start polling."""

    settings = get_settings()
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    setup(dp)
    logger.info("bot starting")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(init_bot())
