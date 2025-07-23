from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class LLMRequest(BaseModel):
    session_id: UUID = Field(alias="sessionId")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sessionId": "6c94282b-708e-40f2-ac9c-6f5fc8fe0b7e",
            }
        },
    )


class LLMResponse(BaseModel):
    text: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "This is a model answer.",
            }
        }
    )


class RoleEnum(StrEnum):
    assistant = "assistant"
    user = "user"


class ContextMessage(BaseModel):
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
    name: str
    description: str
    fileId: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "document.pdf",
                "description": "The document description.",
                "fileId": "686e3550df26ab9c2015d727",
            }
        }
    )
