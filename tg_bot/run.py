"""Entry point for running the Telegram bot."""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
import structlog


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    structlog.configure(
        processors=[structlog.processors.JSONRenderer()],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


configure_logging()
logger = structlog.get_logger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
if not TOKEN:
    logger.error("[telegram] TELEGRAM_BOT_TOKEN is empty — bot disabled")
    sys.exit(1)

from .bot import setup
from .config import get_settings


async def init_bot() -> None:
    """Initialize bot and start polling."""

    logger.info("bot starting")
    try:
        settings = get_settings()
        bot = Bot(token=settings.bot_token)
        dp = Dispatcher()
        setup(dp)
        logger.info("connecting to telegram")
        await dp.start_polling(bot)
    except Exception:
        logger.exception("bot failed")
        raise


if __name__ == "__main__":
    asyncio.run(init_bot())
