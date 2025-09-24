"""Backend settings with environment-variable aliases.

This module defines a small :class:`Settings` model that reads configuration
from ``.env`` and the process environment. It supports backwards-compatible
aliases (e.g. ``MONGO_URI`` and ``mongo.uri``) via ``pydantic``
``AliasChoices`` so the app can be configured in different deployment styles.

Use :func:`get_settings` to access a singleton instance.
"""

from __future__ import annotations
from typing import Optional
from pydantic import Field
import json
from pydantic_settings import BaseSettings, SettingsConfigDict
from backend.ollama import installed_model_names


class Settings(BaseSettings):
    """Application settings with backward-compatible env aliases."""
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__",
    )

    mongo_uri: str = Field(
        default="mongodb://root:root@mongo:27017",
        env=["MONGO_URI", "mongo.uri", "mongo_uri"],
    )
    redis_url: str = Field(
        default="redis://redis:6379/0",
        env=["REDIS_URL", "redis.url", "redis_url"],
    )
    qdrant_url: str = Field(
        default="http://qdrant:6333",
        env=["QDRANT_URL", "qdrant_url"],
    )

    use_gpu: bool = Field(default=False, env=["USE_GPU", "use_gpu"])
    llm_model: str = Field(
        default="Vikhrmodels/Vikhr-YandexGPT-5-Lite-8B-it",
        env=["LLM_MODEL", "llm_model"],
    )

    domain: Optional[str] = Field(default=None, env=["DOMAIN", "domain"])
    project_name: Optional[str] = Field(default=None, env=["PROJECT_NAME", "project.name"])
    grafana_password: Optional[str] = Field(default=None, env=["GRAFANA_PASSWORD", "grafana_password"])
    crawl_start_url: Optional[str] = Field(default=None, env=["CRAWL_START_URL", "crawl_start_url"])
    telegram_admin_id: Optional[int] = Field(default=None, env=["TELEGRAM_ADMIN_ID", "telegram_admin_id"])

    app_host: str = Field(default="0.0.0.0", env=["APP_HOST", "app_host"])
    app_port: int = Field(default=8000, env=["APP_PORT", "app_port"])
    cors_origins: str = Field(default="*", env=["CORS_ORIGINS", "cors.origins"])

    # Optional: use external model microservice instead of local model loading
    model_base_url: Optional[str] = Field(default=None, env=["MODEL_BASE_URL", "model.base_url"])
    model_api_key: Optional[str] = Field(default=None, env=["MODEL_API_KEY", "model.api_key"])

    # Optional: use host Ollama runtime
    ollama_base_url: Optional[str] = Field(default=None, env=["OLLAMA_BASE_URL", "ollama.base_url"])  # e.g. http://host.docker.internal:11434
    # Default to a model that is present in the repo's instructions and used in tags
    ollama_model: Optional[str] = Field(
        default="yandex/YandexGPT-5-Lite-8B-instruct-GGUF:latest",
        env=["OLLAMA_MODEL", "ollama.model"],
    )  # defaults to this value unless overridden

    llm_model_choices: Optional[str] = Field(
        default=None,
        env=["LLM_MODEL_CHOICES", "LLM_MODELS", "llm.models"],
    )

    def get_available_llm_models(self) -> list[str]:
        """Return a de-duplicated list of available LLM model identifiers."""

        default_models = [
            "Vikhrmodels/Vikhr-YandexGPT-5-Lite-8B-it",
            "yandex/YandexGPT-5-Lite-8B-instruct-GGUF:latest",
            "llama3.1:70b",
            "qwen2.5:14b",
        ]

        models: list[str] = []
        models.extend(installed_model_names())
        if self.llm_model:
            models.append(str(self.llm_model).strip())

        raw = self.llm_model_choices
        if raw:
            parsed: list[str] = []
            try:
                data = json.loads(raw)
                if isinstance(data, (list, tuple)):
                    parsed = [str(item).strip() for item in data if str(item).strip()]
            except json.JSONDecodeError:
                parsed = [item.strip() for item in raw.split(",") if item.strip()]
            models.extend(parsed)

        models.extend(default_models)

        unique: list[str] = []
        for model in models:
            if model and model not in unique:
                unique.append(model)
        return unique

    def _discover_local_ollama_models(self) -> list[str]:
        """Backward-compatible wrapper preserved for callers using the old API."""

        return installed_model_names()


settings = Settings()


def get_settings() -> Settings:
    """Return the global :class:`Settings` instance.

    The object is instantiated at import time and reused across the
    application to avoid parsing the environment repeatedly.
    """
    return settings
