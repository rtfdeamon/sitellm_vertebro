"""Knowledge service schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class KnowledgeCreate(BaseModel):
    name: str | None = None
    content: str
    domain: str | None = None
    project: str | None = None
    description: str | None = None
    url: str | None = None


class KnowledgeUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    description: str | None = None
    url: str | None = None
    project: str | None = None
    domain: str | None = None
    status: str | None = None
    status_message: str | None = Field(default=None, alias="statusMessage")


class KnowledgeDeduplicate(BaseModel):
    project: str | None = None


class KnowledgePriorityPayload(BaseModel):
    order: list[str]


class KnowledgeQAPayload(BaseModel):
    question: str
    answer: str
    priority: int | None = 0


class KnowledgeQAReorderPayload(BaseModel):
    order: list[str]


class KnowledgeUnansweredClearPayload(BaseModel):
    project: str | None = None


class KnowledgeServiceConfig(BaseModel):
    enabled: bool | None = None
    mode: str | None = None
    processing_prompt: str | None = Field(default=None, alias="processingPrompt")
    idle_threshold_seconds: int | None = Field(default=None, alias="idleThresholdSeconds")
    poll_interval_seconds: int | None = Field(default=None, alias="pollIntervalSeconds")
    cooldown_seconds: int | None = Field(default=None, alias="cooldownSeconds")
    manual_mode_message: str | None = Field(default=None, alias="manualModeMessage")


class KnowledgeServiceRunRequest(BaseModel):
    mode: str | None = None
    force: bool = False


class IntelligentProcessingPromptPayload(BaseModel):
    prompt: str
