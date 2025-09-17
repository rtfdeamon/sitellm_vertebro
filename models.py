"""Pydantic models used throughout the application.

Adds a compatibility shim for ``enum.StrEnum`` on Python < 3.11.
"""

from enum import Enum
try:  # Python 3.11+
    from enum import StrEnum as _StrEnum
except ImportError:  # Python 3.10 fallback
    class _StrEnum(str, Enum):
        pass
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class LLMRequest(BaseModel):
    """Model for a request to the language model."""

    session_id: UUID = Field(alias="sessionId")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sessionId": "6c94282b-708e-40f2-ac9c-6f5fc8fe0b7e",
            }
        },
    )


class LLMResponse(BaseModel):
    """Response returned by the language model."""

    text: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "This is a model answer.",
            }
        }
    )


class RoleEnum(_StrEnum):
    """Role of the participant in a conversation."""

    assistant = "assistant"
    user = "user"


class ContextMessage(BaseModel):
    """Single message stored in a conversation session."""

    session_id: UUID = Field(alias="sessionId")
    text: str
    role: RoleEnum
    number: int = Field(ge=0)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sessionId": "6c94282b-708e-40f2-ac9c-6f5fc8fe0b7e",
                "text": "Is this a user question?.",
                "role": RoleEnum.user.value,
                "number": 0,
            }
        }
    )


class ContextPreset(BaseModel):
    """Default prompt shown to the LLM before conversation starts."""

    text: str
    role: RoleEnum
    number: int = Field(ge=0)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "You are a helpful assistant.",
                "role": RoleEnum.user.value,
                "number": 0,
            }
        }
    )


class Document(BaseModel):
    """Metadata about a document stored in MongoDB/GridFS."""

    name: str
    description: str
    fileId: str
    url: str | None = None
    ts: float | None = None
    content_type: str | None = None
    domain: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "document.pdf",
                "description": "The document description.",
                "fileId": "686e3550df26ab9c2015d727",
                "url": "https://example.com/file",
                "ts": 1_700_000_000.0,
                "content_type": "text/plain",
                "domain": "example.com",
            }
        }
    )


class Project(BaseModel):
    domain: str
    title: str | None = None
    mongo_uri: str | None = None
    redis_url: str | None = None
    qdrant_url: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "domain": "mmvs.ru",
                "title": "Проект MMVS",
                "mongo_uri": "mongodb://user:pass@mongo:27017/db?authSource=admin",
                "redis_url": "redis://:password@redis:6379/0",
                "qdrant_url": "http://qdrant:6333",
            }
        }
    )
