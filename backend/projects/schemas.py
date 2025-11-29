"""Project configuration schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=lambda s: "".join(word.capitalize() if i > 0 else word for i, word in enumerate(s.split("_"))))

    name: str
    title: str | None = None
    domain: str | None = None
    admin_username: str | None = None
    admin_password: str | None = None
    llm_model: str | None = None
    llm_prompt: str | None = None
    telegram_token: str | None = None
    telegram_auto_start: bool | None = None
    max_token: str | None = None
    max_auto_start: bool | None = None
    vk_token: str | None = None
    vk_auto_start: bool | None = None
    
    # Mail settings
    mail_smtp_host: str | None = None
    mail_smtp_port: int | None = None
    mail_smtp_tls: bool | None = None
    mail_username: str | None = None
    mail_password: str | None = None
    mail_from: str | None = None
    mail_signature: str | None = None


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=lambda s: "".join(word.capitalize() if i > 0 else word for i, word in enumerate(s.split("_"))))

    title: str | None = None
    domain: str | None = None
    admin_username: str | None = None
    admin_password: str | None = None
    llm_model: str | None = None
    llm_prompt: str | None = None
    telegram_token: str | None = None
    telegram_auto_start: bool | None = None
    max_token: str | None = None
    max_auto_start: bool | None = None
    vk_token: str | None = None
    vk_auto_start: bool | None = None
    
    # Mail settings
    mail_smtp_host: str | None = None
    mail_smtp_port: int | None = None
    mail_smtp_tls: bool | None = None
    mail_username: str | None = None
    mail_password: str | None = None
    mail_from: str | None = None
    mail_signature: str | None = None


class FeedbackCreatePayload(BaseModel):
    message: str
    name: str | None = None
    contact: str | None = None
    page: str | None = None
    project: str | None = None
    source: str | None = None


class FeedbackUpdatePayload(BaseModel):
    status: Literal["open", "in_progress", "done", "dismissed"]
    note: str | None = None


class OllamaInstallRequest(BaseModel):
    model: str


class OllamaServerPayload(BaseModel):
    name: str
    base_url: str
    enabled: bool = True


class PromptGenerationRequest(BaseModel):
    url: str
    role: str | None = None
