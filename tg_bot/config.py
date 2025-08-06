"""Configuration helpers for the Telegram bot."""

from __future__ import annotations

from functools import lru_cache

from pydantic import AnyUrl, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration for the Telegram bot."""

    bot_token: str
    backend_url: AnyUrl = "http://localhost:9000/api/chat"
    request_timeout: int = 30

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached :class:`Settings` instance."""

    return Settings()
