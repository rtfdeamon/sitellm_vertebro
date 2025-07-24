"""Application settings models."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class MongoSettings(BaseSettings):
    """Settings for MongoDB connection."""

    host: str = "localhost"
    port: int = 27017
    username: str | None = None
    password: str | None = None
    database: str = "smarthelperdb"
    auth: str = "admin"

    contexts: str = "contexts"
    presets: str = "contextPresets"
    vectors: str = "vectors"
    documents: str = "documents"


class Redis(BaseSettings):
    """Redis connection parameters."""

    host: str = "localhost"
    port: int = 6379
    secure: bool = False
    password: str | None = None

    vector: str | None = "vector"


class CelerySettings(BaseSettings):
    """Celery broker and result backend configuration."""

    broker: str = "redis://localhost:6379"
    result: str = "redis://localhost:6379"


class Settings(BaseSettings):
    """Top level application settings."""

    debug: bool = False

    mongo: MongoSettings = MongoSettings()
    celery: CelerySettings = CelerySettings()
    redis: Redis = Redis()

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_nested_delimiter="_"
    )
