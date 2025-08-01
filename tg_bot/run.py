"""Entry point for running the Telegram bot."""

from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
import structlog

from .bot import setup
from .config import get_settings

logger = structlog.get_logger(__name__)


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
