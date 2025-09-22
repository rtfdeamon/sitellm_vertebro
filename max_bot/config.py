"""Configuration helpers for the MAX messenger integration."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import AnyUrl, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration values used by the MAX bot runner."""

    api_base_url: AnyUrl = "https://botapi.max.ru"
    updates_limit: int = 25
    updates_timeout: int = 25
    request_timeout: int = 30
    idle_sleep_seconds: float = 1.0
    disable_link_preview: bool = True

    model_config = ConfigDict(env_prefix="MAX_", env_file=".env", env_file_encoding="utf-8")

    def base_url(self) -> str:
        return str(self.api_base_url).rstrip("/")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached :class:`Settings` instance."""

    return Settings()
