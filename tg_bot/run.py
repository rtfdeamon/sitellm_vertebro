"""Entry point for running the Telegram bot."""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
import structlog

from observability.logging import configure_logging

configure_logging()
logger = structlog.get_logger(__name__)

from .bot import setup
from .config import get_settings


async def init_bot() -> None:
    """Initialize bot and start polling."""

    logger.info("bot starting")
    try:
        settings = get_settings()
        token = (settings.bot_token or "").strip()
        if not token:
            logger.warning("[telegram] BOT_TOKEN is empty — bot disabled")
            return

        bot = Bot(token=token)
        dp = Dispatcher()
        session_cache = {}

        class SessionProvider:
            async def get_session(self, project, user_id):
                if user_id is None:
                    return None
                project_map = session_cache.setdefault(project, {})
                if user_id not in project_map:
                    project_map[user_id] = os.urandom(16).hex()
                return project_map[user_id]

        setup(dp, project=settings.project, session_provider=SessionProvider())
        logger.info("connecting to telegram")
        await dp.start_polling(bot)
    except Exception:
        logger.exception("bot failed")
        raise


if __name__ == "__main__":
    asyncio.run(init_bot())
