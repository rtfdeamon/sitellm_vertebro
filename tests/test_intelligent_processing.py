"""Tests for intelligent processing admin endpoints."""

from __future__ import annotations

import json
import types

import pytest

app_module = pytest.importorskip("app", reason="app module dependencies not installed")

for required in (
    "AdminIdentity",
    "IntelligentProcessingPromptPayload",
    "KNOWLEDGE_SERVICE_KEY",
    "intelligent_processing_save_prompt",
    "intelligent_processing_state",
):
    if not hasattr(app_module, required):
        pytest.skip(
            f"'{required}' not available on app module (likely running with stubbed dependencies)",
            allow_module_level=True,
        )

AdminIdentity = getattr(app_module, "AdminIdentity")
IntelligentProcessingPromptPayload = getattr(app_module, "IntelligentProcessingPromptPayload")
KNOWLEDGE_SERVICE_KEY = getattr(app_module, "KNOWLEDGE_SERVICE_KEY")
intelligent_processing_save_prompt = getattr(app_module, "intelligent_processing_save_prompt")
intelligent_processing_state = getattr(app_module, "intelligent_processing_state")


class _FakeMongo:
    def __init__(self, initial: dict | None = None) -> None:
        self.state = initial or {}
        self.saved_payload: dict | None = None
        self.saved_key: str | None = None

    async def get_setting(self, key: str) -> dict | None:
        if key != KNOWLEDGE_SERVICE_KEY:
            return None
        return dict(self.state)

    async def set_setting(self, key: str, value: dict) -> None:
        self.saved_key = key
        self.state = dict(value)
        self.saved_payload = dict(value)


def _make_request(mongo: _FakeMongo):
    state = types.SimpleNamespace(
        mongo=mongo,
        admin=AdminIdentity(username="tester", is_super=True, projects=()),
    )
    return types.SimpleNamespace(state=state)


def _json(response) -> dict:
    return json.loads(response.body.decode())


@pytest.mark.asyncio
async def test_intelligent_processing_state_returns_current_config() -> None:
    mongo = _FakeMongo(
        {
            "enabled": True,
            "mode": "manual",
            "processing_prompt": "Existing prompt",
            "message": "OK",
        }
    )
    request = _make_request(mongo)

    response = await intelligent_processing_state(request)
    data = _json(response)

    assert data["enabled"] is True
    assert data["mode"] == "manual"
    assert data["processing_prompt"] == "Existing prompt"


@pytest.mark.asyncio
async def test_intelligent_processing_prompt_updates_prompt_only() -> None:
    mongo = _FakeMongo({"enabled": False, "mode": "manual", "processing_prompt": "Old"})
    request = _make_request(mongo)
    payload = IntelligentProcessingPromptPayload(processing_prompt="  New prompt  ")

    response = await intelligent_processing_save_prompt(request, payload)
    data = _json(response)

    assert data["status"] == "ok"
    assert mongo.state["enabled"] is False
    assert mongo.state["processing_prompt"] == "New prompt"


@pytest.mark.asyncio
async def test_intelligent_processing_prompt_can_toggle_state() -> None:
    mongo = _FakeMongo({"enabled": False, "mode": "manual", "processing_prompt": "Old"})
    request = _make_request(mongo)
    payload = IntelligentProcessingPromptPayload(
        enabled=True,
        mode="auto",
        processing_prompt="Next prompt",
    )

    response = await intelligent_processing_save_prompt(request, payload)
    data = _json(response)

    assert data["status"] == "ok"
    assert mongo.state["enabled"] is True
    assert mongo.state["mode"] == "auto"
    assert mongo.state["processing_prompt"] == "Next prompt"
