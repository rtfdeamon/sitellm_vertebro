"""Pydantic schemas for knowledge base and feedback endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


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
    status_message: str | None = None


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
    enabled: bool
    idle_threshold_seconds: int | None = None
    poll_interval_seconds: int | None = None
    cooldown_seconds: int | None = None
    mode: Literal["auto", "manual"] | None = None
    processing_prompt: str | None = None


class KnowledgeServiceRunRequest(BaseModel):
    reason: str | None = None


class FeedbackCreatePayload(BaseModel):
    message: str
    name: str | None = None
    contact: str | None = None
    page: str | None = None
    project: str | None = None
    source: str | None = None


class FeedbackUpdatePayload(BaseModel):
    status: str | None = None
    note: str | None = None


__all__ = [
    "FeedbackCreatePayload",
    "FeedbackUpdatePayload",
    "KnowledgeCreate",
    "KnowledgeDeduplicate",
    "KnowledgePriorityPayload",
    "KnowledgeQAPayload",
    "KnowledgeQAReorderPayload",
    "KnowledgeServiceConfig",
    "KnowledgeServiceRunRequest",
    "KnowledgeUnansweredClearPayload",
    "KnowledgeUpdate",
]
