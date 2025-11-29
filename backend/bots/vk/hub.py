"""VK bot hub for managing multiple bot instances."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import structlog
from fastapi import HTTPException

from backend.bots.vk.runner import VkRunner

if TYPE_CHECKING:
    from models import Project
    from mongo import MongoClient

logger = structlog.get_logger(__name__)


class VkHub:
    """Manage VK bot runners per project."""

    _instance: VkHub | None = None

    def __init__(self, mongo: MongoClient) -> None:
        VkHub._instance = self
        self._mongo = mongo
        self._runners: dict[str, VkRunner] = {}
        self._sessions: dict[str, dict[str, UUID]] = {}
        self._errors: dict[str, str] = {}
        self._pending: dict[str, dict[str, dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> VkHub:
        if cls._instance is None:
            raise RuntimeError("VkHub not initialized")
        return cls._instance

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

    async def get_or_create_session(self, project: str, user_key: str) -> UUID:
        async with self._lock:
            sessions = self._sessions.setdefault(project, {})
            session = sessions.get(user_key)
            if session is None:
                session = uuid4()
                sessions[user_key] = session
            return session

    async def stop_all(self) -> None:
        async with self._lock:
            runners = list(self._runners.values())
            self._runners.clear()
            self._sessions.clear()
            self._errors.clear()
            self._pending.clear()
        await asyncio.gather(*(runner.stop() for runner in runners), return_exceptions=True)

    async def refresh(self) -> None:
        projects = await self._mongo.list_projects()
        known = {p.name for p in projects}
        for project in projects:
            try:
                await self.ensure_runner(project)
            except Exception as exc:  # noqa: BLE001
                logger.warning("vk_autostart_failed", project=project.name, error=str(exc))
        stale = set(self._runners) - known
        for project_name in stale:
            await self.stop_project(project_name, forget_sessions=True)

    async def ensure_runner(self, project: Project) -> None:
        token = (
            project.vk_token.strip() or None
            if isinstance(project.vk_token, str)
            else None
        )
        auto_start = bool(project.vk_auto_start)
        if not token:
            await self.stop_project(project.name)
            return
        runner = await self._get_or_create_runner(project.name, token)
        if auto_start:
            try:
                await runner.start()
                logger.info("vk_autostart_success", project=project.name)
            except Exception:
                async with self._lock:
                    self._runners.pop(project.name, None)
                raise
        else:
            await runner.stop()

    async def start_project(self, project: Project, *, auto_start: bool | None = None) -> None:
        token = (
            project.vk_token.strip() or None
            if isinstance(project.vk_token, str)
            else None
        )
        if not token:
            raise HTTPException(status_code=400, detail="VK token is not configured")
        runner = await self._get_or_create_runner(project.name, token)
        try:
            await runner.start()
            logger.info("vk_runner_manual_start", project=project.name)
        except Exception as exc:  # noqa: BLE001
            async with self._lock:
                self._runners.pop(project.name, None)
            raise HTTPException(status_code=400, detail=f"Failed to start VK bot: {exc}") from exc
        if auto_start is not None:
            project.vk_auto_start = auto_start
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
            if forget_sessions:
                self._sessions.pop(project_name, None)
                self._pending.pop(project_name, None)
        if runner:
            logger.info("vk_runner_stopping", project=project_name)
            await runner.stop()
        if auto_start is not None:
            project = await self._mongo.get_project(project_name)
            if project:
                project.vk_auto_start = auto_start
                await self._mongo.upsert_project(project)

    async def _get_or_create_runner(self, project: str, token: str) -> VkRunner:
        async with self._lock:
            runner = self._runners.get(project)
            if runner:
                if runner.token != token:
                    await runner.stop()
                    runner = None
            if runner is None:
                runner = VkRunner(project, token, self)
                self._runners[project] = runner
            else:
                runner.token = token
        return runner

    async def set_pending_attachments(
        self,
        project: str,
        session_key: str,
        payload: dict[str, Any],
    ) -> None:
        async with self._lock:
            project_map = self._pending.setdefault(project, {})
            project_map[session_key] = payload

    async def get_pending_attachments(
        self,
        project: str,
        session_key: str,
    ) -> dict[str, Any] | None:
        async with self._lock:
            return (self._pending.get(project) or {}).get(session_key)

    async def clear_pending_attachments(self, project: str, session_key: str) -> None:
        async with self._lock:
            project_map = self._pending.get(project)
            if project_map and session_key in project_map:
                project_map.pop(session_key, None)
                if not project_map:
                    self._pending.pop(project, None)
