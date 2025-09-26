"""Configuration helpers for the Telegram bot."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import AnyUrl, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration for the standalone Telegram bot."""

    bot_token: str | None = None
    project: str = "default"
    api_base_url: AnyUrl = "http://app:8000"
    backend_url: AnyUrl = "http://app:8000/api/v1/llm/chat"
    backend_verify_ssl: bool = True
    backend_ca_path: str | None = None
    status_url: AnyUrl | None = None
    project_sync_interval: int = 30
    request_timeout: int = 30
    speech_to_text_url: AnyUrl | None = None
    speech_to_text_language: str | None = None
    speech_to_text_api_key: str | None = None

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    def resolve_status_url(self) -> str:
        if self.status_url:
            return str(self.status_url)
        base = str(self.api_base_url).rstrip('/')
        return f"{base}/status"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached :class:`Settings` instance."""

    return Settings()
