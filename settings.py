"""Application settings models."""

from functools import lru_cache
from pydantic import AnyUrl, BaseSettings, ConfigDict


class MongoSettings(BaseSettings):
    """Settings for MongoDB connection.

    Environment variables follow the ``MONGO_`` prefix. For example,
    ``MONGO_HOST`` and ``MONGO_PORT`` configure the connection host and port.
    ``MONGO_CONTEXTS`` defines the collection name for conversation contexts.
    """

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
    """Redis connection parameters.

    Variables prefixed with ``REDIS_`` configure the vector store backend.
    Use ``REDIS_PASSWORD`` and ``REDIS_SECURE`` for authentication and TLS.
    """

    host: str = "localhost"
    port: int = 6379
    secure: bool = False
    password: str | None = None

    vector: str | None = "vector"


class CelerySettings(BaseSettings):
    """Celery broker and result backend configuration.

    The fields read ``CELERY_BROKER`` and ``CELERY_RESULT`` environment
    variables which are Redis URLs used by the worker and beat services.
    """

    broker: str = "redis://localhost:6379"
    result: str = "redis://localhost:6379"


class Settings(BaseSettings):
    """Top level application settings loaded from ``.env``.

    Nested models use environment prefixes such as ``MONGO_`` and ``REDIS_``.
    The :class:`pydantic.BaseSettings` machinery automatically reads these
    variables when the application starts.
    """

    debug: bool = False
    llm_url: str = "http://localhost:8000"
    emb_model_name: str = "sentence-transformers/sbert_large_nlu_ru"
    rerank_model_name: str = "sbert_cross_ru"
    redis_url: AnyUrl | str = "redis://localhost:6379/0"
    use_gpu: bool = False

    mongo: MongoSettings = MongoSettings()
    celery: CelerySettings = CelerySettings()
    redis: Redis = Redis()

    model_config = ConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_nested_delimiter="_"
    )


@lru_cache(maxsize=1)
def get_settings() -> "Settings":
    """Return cached application settings."""

    return Settings()
