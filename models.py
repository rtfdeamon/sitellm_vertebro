"""Pydantic models used throughout the application.

Adds a compatibility shim for ``enum.StrEnum`` on Python < 3.11.
"""

from __future__ import annotations

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
    project: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sessionId": "6c94282b-708e-40f2-ac9c-6f5fc8fe0b7e",
                "project": "mmvs",
            }
        },
    )


class Attachment(BaseModel):
    """Metadata about a downloadable document attachment."""

    name: str
    url: str | None = None
    content_type: str | None = None
    file_id: str | None = None
    size_bytes: int | None = None
    description: str | None = None


class LLMResponse(BaseModel):
    """Response returned by the language model."""

    text: str
    attachments: list[Attachment] = []
    emotions_enabled: bool | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "Это выдержка из договора.",
                "attachments": [
                    {
                        "name": "typical-contract.pdf",
                        "content_type": "application/pdf",
                        "file_id": "686e3550df26ab9c2015d727",
                        "url": "https://example.com/api/v1/admin/knowledge/documents/abc123",
                    }
                ],
                "emotions_enabled": True,
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
    project: str | None = None

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
    project: str | None = None
    source_content_type: str | None = None
    size_bytes: int | None = None
    status: str | None = None
    status_message: str | None = Field(default=None, alias="statusMessage")
    status_updated_at: float | None = Field(default=None, alias="statusUpdatedAt")
    auto_description_pending: bool | None = Field(default=None, alias="autoDescriptionPending")
    auto_description_generated_at: float | None = Field(default=None, alias="autoDescriptionGeneratedAt")
    content_hash: str | None = None

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
                "project": "mmvs",
                "size_bytes": 10240,
            }
        }
    )


class Project(BaseModel):
    """Configuration of a logical project within the deployment."""

    name: str
    title: str | None = None
    domain: str | None = None
    admin_username: str | None = None
    admin_password_hash: str | None = None
    llm_model: str | None = None
    llm_prompt: str | None = None
    llm_emotions_enabled: bool | None = True
    llm_voice_enabled: bool | None = True
    llm_voice_model: str | None = None
    telegram_token: str | None = None
    telegram_auto_start: bool | None = None
    max_token: str | None = None
    max_auto_start: bool | None = None
    vk_token: str | None = None
    vk_auto_start: bool | None = None
    widget_url: str | None = None
    debug_enabled: bool | None = None
    debug_info_enabled: bool | None = True

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "mmvs",
                "domain": "mmvs.ru",
                "title": "Проект MMVS",
                "admin_username": "mmvs_admin",
                "llm_model": "Vikhrmodels/Vikhr-YandexGPT-5-Lite-8B-it",
                "llm_prompt": "You are helpful and concise.",
                "llm_emotions_enabled": True,
                "llm_voice_enabled": True,
                "llm_voice_model": "fast-solutions/voice-gpt",
                "debug_enabled": False,
                "debug_info_enabled": True,
                "telegram_auto_start": False,
                "max_auto_start": False,
                "vk_auto_start": False,
                "widget_url": "https://example.com/widget?project=mmvs",
            }
        }
    )


class OllamaServer(BaseModel):
    """Configuration entry describing an Ollama backend node."""

    name: str
    base_url: str
    enabled: bool = True
    created_at: float | None = None
    updated_at: float | None = None
    stats: dict | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "primary",
                "base_url": "http://localhost:11434",
                "enabled": True,
                "stats": {
                    "avg_latency_ms": 2200.0,
                    "requests_last_hour": 12,
                    "updated_at": 1_700_000_000.0,
                },
            }
        }
    )
