from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, ConfigDict


class VoiceSessionRequest(BaseModel):
    project: str
    user_id: str | None = Field(default=None, alias="userId")
    language: str = "ru-RU"
    voice_preference: dict[str, Any] | None = Field(default=None, alias="voicePreference")

    model_config = ConfigDict(populate_by_name=True)


class VoiceSessionResponse(BaseModel):
    session_id: str = Field(alias="sessionId")
    websocket_url: str = Field(alias="websocketUrl")
    expires_at: datetime = Field(alias="expiresAt")
    initial_greeting: str = Field(alias="initialGreeting")

    model_config = ConfigDict(populate_by_name=True)


class RecognitionRequest(BaseModel):
    audio_base64: str | None = Field(default=None, alias="audioBase64")
    language: str | None = None
    text_hint: str | None = Field(default=None, alias="textHint")

    model_config = ConfigDict(populate_by_name=True)


class RecognitionResult(BaseModel):
    text: str
    confidence: float
    language: str = "und"
    processing_time_ms: float | None = Field(default=None, alias="processingTimeMs")
    is_final: bool | None = Field(default=True, alias="isFinal")
    alternatives: list[str] | None = None

    model_config = ConfigDict(populate_by_name=True)


class SynthesisRequest(BaseModel):
    text: str = Field(min_length=1)
    voice: str = "default"
    language: str = "ru-RU"
    emotion: str | None = None
    options: dict[str, Any] | None = None


class SynthesisResponse(BaseModel):
    audio_url: str = Field(alias="audioUrl")
    duration_seconds: float = Field(alias="durationSeconds")
    cached: bool

    model_config = ConfigDict(populate_by_name=True)


class IntentRequest(BaseModel):
    text: str


class IntentResponse(BaseModel):
    intent: str
    confidence: float
    entities: dict[str, Any] = Field(default_factory=dict)
    suggested_action: dict[str, Any] | None = Field(default=None, alias="suggestedAction")

    model_config = ConfigDict(populate_by_name=True)


class DialogMessageRequest(BaseModel):
    session_id: str = Field(alias="sessionId")
    project: str
    text: str
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(populate_by_name=True)


class ResponseMessage(BaseModel):
    type: str
    text: str
    audio_url: str | None = Field(default=None, alias="audioUrl")
    sources: list[dict[str, Any]] = Field(default_factory=list)
    suggested_actions: list[dict[str, Any]] = Field(default_factory=list, alias="suggestedActions")

    model_config = ConfigDict(populate_by_name=True)
