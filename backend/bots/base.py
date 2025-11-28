"""Base classes for bot runners and hubs."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from contextlib import suppress
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import structlog

if TYPE_CHECKING:
    from models import Project
    from mongo import MongoClient

logger = structlog.get_logger(__name__)


class BaseRunner(ABC):
    """Base class for platform-specific bot runners."""

    def __init__(self, project: str, token: str, hub: BaseHub) -> None:
        self.project = project
        self.token = token
        self._task: asyncio.Task | None = None
        self._hub = hub

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.is_running:
            return
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._run())
        self._hub._errors.pop(self.project, None)
        logger.info(f"{self._platform}_runner_started", project=self.project)


    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    @property
    @abstractmethod
    def _platform(self) -> str:
        """Platform identifier (telegram, vk, max)."""
        pass

    @abstractmethod
    async def _run(self) -> None:
        """Platform-specific polling logic."""
        pass


class BaseHub(ABC):
    """Base class for managing multiple bot instances per project."""

    def __init__(self, mongo: MongoClient) -> None:
        self._mongo = mongo
        self._runners: dict[str, Any] = {}
        self._sessions: dict[str, dict[str, UUID]] = {}
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

    async def get_or_create_session(self, project: str, user_key: str) -> UUID:
        """Get or create session ID for user in project."""
        async with self._lock:
            sessions = self._sessions.setdefault(project, {})
            session = sessions.get(user_key)
            if session is None:
                session = uuid4()
                sessions[user_key] = session
            return session

    async def stop_all(self) -> None:
        """Stop all runners and clear state."""
        async with self._lock:
            runners = list(self._runners.values())
            self._runners.clear()
            self._sessions.clear()
            self._errors.clear()
        await asyncio.gather(*(runner.stop() for runner in runners), return_exceptions=True)

    async def refresh(self) -> None:
        """Refresh all bot runners based on current project configuration."""
        projects = await self._mongo.list_projects()
        known = {p.name for p in projects}
        
        for project in projects:
            try:
                await self.ensure_runner(project)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    f"{self._platform}_autostart_failed",
                    project=project.name,
                    error=str(exc)
                )
        
        # Remove stale runners
        stale = set(self._runners) - known
        for project_name in stale:
            await self.stop_project(project_name, forget_sessions=True)

    @property
    @abstractmethod
    def _platform(self) -> str:
        """Platform identifier (telegram, vk, max)."""
        pass

    @abstractmethod
    async def ensure_runner(self, project: Project) -> None:
        """Create or update runner for project."""
        pass

    @abstractmethod
    async def start_project(self, project: Project, *, auto_start: bool | None = None) -> None:
        """Start bot for project."""
        pass

    @abstractmethod
    async def stop_project(
        self,
        project_name: str,
        *,
        auto_start: bool | None = None,
        forget_sessions: bool = False,
    ) -> None:
        """Stop bot for project."""
        pass
