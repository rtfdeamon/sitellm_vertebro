"""Bot configuration schemas."""

from pydantic import BaseModel


class TelegramConfig(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class TelegramAction(BaseModel):
    token: str | None = None


class ProjectTelegramConfig(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class ProjectTelegramAction(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class MaxConfig(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class MaxAction(BaseModel):
    token: str | None = None


class ProjectMaxConfig(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class ProjectMaxAction(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class VkConfig(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class VkAction(BaseModel):
    token: str | None = None


class ProjectVkConfig(BaseModel):
    token: str | None = None
    auto_start: bool | None = None


class ProjectVkAction(BaseModel):
    token: str | None = None
    auto_start: bool | None = None
