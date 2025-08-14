from __future__ import annotations
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


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
        validation_alias=AliasChoices("MONGO_URI", "mongo.uri", "mongo_uri"),
    )
    redis_url: str = Field(
        default="redis://redis:6379/0",
        validation_alias=AliasChoices("REDIS_URL", "redis.url", "redis_url"),
    )
    qdrant_url: str = Field(
        default="http://qdrant:6333",
        validation_alias=AliasChoices("QDRANT_URL", "qdrant_url"),
    )

    use_gpu: bool = Field(default=False, validation_alias=AliasChoices("USE_GPU", "use_gpu"))
    llm_model: str = Field(
        default="Vikhrmodels/Vikhr-YandexGPT-5-Lite-8B-it",
        validation_alias=AliasChoices("LLM_MODEL", "llm_model"),
    )

    domain: str | None = Field(default=None, validation_alias=AliasChoices("DOMAIN", "domain"))
    grafana_password: str | None = Field(default=None, validation_alias=AliasChoices("GRAFANA_PASSWORD", "grafana_password"))
    crawl_start_url: str | None = Field(default=None, validation_alias=AliasChoices("CRAWL_START_URL", "crawl_start_url"))
    telegram_admin_id: int | None = Field(default=None, validation_alias=AliasChoices("TELEGRAM_ADMIN_ID", "telegram_admin_id"))

    app_host: str = Field(default="0.0.0.0", validation_alias=AliasChoices("APP_HOST", "app_host"))
    app_port: int = Field(default=8000, validation_alias=AliasChoices("APP_PORT", "app_port"))


settings = Settings()


def get_settings() -> Settings:
    return settings
