"""Telegram bot hub for managing multiple bot instances."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import structlog
from fastapi import HTTPException

from backend.bots.telegram.runner import TelegramRunner

if TYPE_CHECKING:
    from models import Project
    from mongo import MongoClient

logger = structlog.get_logger(__name__)


class TelegramHub:
    """Manage multiple Telegram bot instances keyed by project."""

    def __init__(self, mongo: MongoClient) -> None:
        self._mongo = mongo
        self._runners: dict[str, TelegramRunner] = {}
        self._sessions: dict[str, dict[int, UUID]] = {}
        self._errors: dict[str, str] = {}
        self._lock = asyncio.Lock()

    @property
    def is_any_running(self) -> bool:
        return any(runner.is_running for runner in self._runners.values())

    def is_project_running(self, project: str | None) -> bool:
        if not project:
            return False
        runner = self._runners.get(project)
        return runner.is_running if runner else False

    def get_last_error(self, project: str) -> str | None:
        return self._errors.get(project)

    async def get_or_create_session(self, project: str, user_id: int) -> UUID:
        async with self._lock:
            sessions = self._sessions.setdefault(project, {})
            session = sessions.get(user_id)
            if session is None:
                session = uuid4()
                sessions[user_id] = session
            return session

    async def drop_session(self, project: str, user_id: int) -> None:
        async with self._lock:
            sessions = self._sessions.get(project)
            if sessions and user_id in sessions:
                sessions.pop(user_id, None)
                if not sessions:
                    self._sessions.pop(project, None)

    async def stop_all(self) -> None:
        async with self._lock:
            runners = list(self._runners.values())
            self._runners.clear()
            self._sessions.clear()
            self._errors.clear()
        await asyncio.gather(*(runner.stop() for runner in runners), return_exceptions=True)

    async def refresh(self) -> None:
        projects = await self._mongo.list_projects()
        known = {p.name for p in projects}
        for project in projects:
            try:
                await self.ensure_runner(project)
            except Exception as exc:  # noqa: BLE001
                logger.warning("telegram_autostart_failed", project=project.name, error=str(exc))
        stale_keys = set(self._runners) - known
        for project_name in stale_keys:
            await self.stop_project(project_name, forget_sessions=True)

    async def ensure_runner(self, project: Project) -> None:
        token = (
            project.telegram_token.strip() or None
            if isinstance(project.telegram_token, str)
            else None
        )
        auto_start = bool(project.telegram_auto_start)
        if not token:
            await self.stop_project(project.name)
            return
        runner = await self._get_or_create_runner(project.name, token)
        if auto_start:
            try:
                await runner.start()
                logger.info("telegram_autostart_success", project=project.name)
            except Exception:
                async with self._lock:
                    self._runners.pop(project.name, None)
                raise
        else:
            await runner.stop()

    async def start_project(self, project: Project, *, auto_start: bool | None = None) -> None:
        token = (
            project.telegram_token.strip() or None
            if isinstance(project.telegram_token, str)
            else None
        )
        if not token:
            raise HTTPException(status_code=400, detail="Telegram token is not configured")
        runner = await self._get_or_create_runner(project.name, token)
        try:
            await runner.start()
            logger.info("telegram_runner_manual_start", project=project.name)
        except Exception as exc:  # noqa: BLE001
            async with self._lock:
                self._runners.pop(project.name, None)
            raise HTTPException(status_code=400, detail=f"Failed to start bot: {exc}") from exc
        if auto_start is not None:
            project.telegram_auto_start = auto_start
            maybe_upsert = getattr(self._mongo, "upsert_project", None)
            if callable(maybe_upsert):
                await maybe_upsert(project)

    async def stop_project(
        self,
        project_name: str,
        *,
        auto_start: bool | None = None,
        forget_sessions: bool = False,
    ) -> None:
        async with self._lock:
            runner = self._runners.pop(project_name, None)
            self._errors.pop(project_name, None)
        if runner:
            logger.info("telegram_runner_stopping", project=project_name)
            await runner.stop()
        if auto_start is not None:
            project = await self._mongo.get_project(project_name)
            if project:
                project.telegram_auto_start = auto_start
                await self._mongo.upsert_project(project)
        if forget_sessions:
            async with self._lock:
                self._sessions.pop(project_name, None)

    async def _get_or_create_runner(self, project: str, token: str) -> TelegramRunner:
        async with self._lock:
            runner = self._runners.get(project)
        if runner and runner.token != token:
            await runner.stop()
            runner = None
        if runner is None:
            runner = TelegramRunner(project, token, self)
            async with self._lock:
                self._runners[project] = runner
        else:
            runner.token = token
        return runner
