"""Configuration helpers for the VK messenger integration."""

from __future__ import annotations

from functools import lru_cache

from pydantic import AnyUrl, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration values used by the VK bot runner."""

    api_base_url: AnyUrl = "https://api.vk.com"
    api_version: str = "5.199"
    long_poll_wait: int = 25
    long_poll_mode: int = 2
    long_poll_version: int = 3
    request_timeout: int = 30
    idle_sleep_seconds: float = 1.0
    retry_delay_seconds: float = 3.0
    disable_link_preview: bool = True

    model_config = ConfigDict(env_prefix="VK_", env_file=".env", env_file_encoding="utf-8")

    def base_url(self) -> str:
        return str(self.api_base_url).rstrip("/")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached :class:`Settings` instance."""

    return Settings()
