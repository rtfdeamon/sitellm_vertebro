"""Session provider for bot integrations."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from backend.bots.base import BaseHub


class HubSessionProvider:
    """Provides session IDs for bot users via hub."""

    def __init__(self, hub: BaseHub, project: str) -> None:
        self._hub = hub
        self._project = project

    async def get_session(self, user_id: int | str | None) -> UUID | None:
        """Get or create session for user."""
        if user_id is None:
            return None
        user_key = f"user:{user_id}"
        return await self._hub.get_or_create_session(self._project, user_key)
