"""Telegram bot runner implementation."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING

import structlog

from backend.bots.base import BaseRunner
from backend.bots.session_provider import HubSessionProvider

if TYPE_CHECKING:
    from backend.bots.telegram.hub import TelegramHub

logger = structlog.get_logger(__name__)


class TelegramRunner(BaseRunner):
    """Single bot polling task bound to a project token."""

    def __init__(self, project: str, token: str, hub: TelegramHub) -> None:
        super().__init__(project, token, hub)

    @property
    def _platform(self) -> str:
        return "telegram"

    async def _run(self) -> None:
        from tg_bot.bot import setup
        from aiogram import Bot, Dispatcher

        bot = Bot(token=self.token)
        dp = Dispatcher()
        session_provider = HubSessionProvider(self._hub, self.project)
        setup(dp, project=self.project, session_provider=session_provider)
        
        try:
            try:
                await bot.get_me()
            except Exception as exc:  # noqa: BLE001
                self._hub._errors[self.project] = f"token_error: {exc}"
                raise
            await dp.start_polling(bot)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("telegram_runner_failed", project=self.project, error=str(exc))
            self._hub._errors[self.project] = str(exc)
        finally:
            with suppress(Exception):
                await dp.storage.close()
            with suppress(Exception):
                await bot.session.close()
