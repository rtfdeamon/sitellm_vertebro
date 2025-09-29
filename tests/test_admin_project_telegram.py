"""Tests for project-scoped Telegram admin endpoints."""

import json
import types

import pytest

from app import (
    ProjectTelegramAction,
    ProjectTelegramConfig,
    admin_project_telegram_config,
    admin_project_telegram_start,
    admin_project_telegram_status,
    admin_project_telegram_stop,
)
from models import Project


class _FakeHub:
    def __init__(self) -> None:
        self.running: dict[str, bool] = {}
        self.tokens: dict[str, str] = {}
        self.auto_start: dict[str, bool] = {}

    def is_project_running(self, project: str | None) -> bool:
        return bool(project and self.running.get(project))

    def get_last_error(self, project: str | None) -> str | None:  # pragma: no cover - simple stub
        return None

    async def ensure_runner(self, project: Project) -> None:
        token = project.telegram_token
        if token:
            self.tokens[project.name] = token
        run = bool(token and project.telegram_auto_start)
        self.running[project.name] = run
        self.auto_start[project.name] = bool(project.telegram_auto_start)

    async def start_project(self, project: Project, *, auto_start: bool | None = None) -> None:
        if project.telegram_token:
            self.tokens[project.name] = project.telegram_token
        self.running[project.name] = True
        if auto_start is not None:
            self.auto_start[project.name] = bool(auto_start)

    async def stop_project(
        self,
        project_name: str,
        *,
        auto_start: bool | None = None,
        forget_sessions: bool = False,
    ) -> None:
        self.running[project_name] = False
        if auto_start is not None:
            self.auto_start[project_name] = bool(auto_start)


class _FakeMongo:
    def __init__(self, project: Project | None):
        self.project = project
        self.saved: Project | None = None

    async def get_project(self, name: str) -> Project | None:  # pragma: no cover - simple
        return self.project

    async def upsert_project(self, project: Project) -> Project:
        self.saved = project
        self.project = project
        return project


def _make_request(mongo: _FakeMongo, controller: _FakeHub):
    state = types.SimpleNamespace(mongo=mongo)
    app_state = types.SimpleNamespace(telegram=controller)
    app = types.SimpleNamespace(state=app_state)
    request = types.SimpleNamespace(state=state, app=app)
    return request


def _load_json(response) -> dict:
    return json.loads(response.body.decode())


@pytest.mark.asyncio
async def test_project_config_creates_and_updates_token() -> None:
    mongo = _FakeMongo(project=None)
    controller = _FakeHub()
    request = _make_request(mongo, controller)
    payload = ProjectTelegramConfig(token=" 12345:token ", auto_start=True)

    response = await admin_project_telegram_config("demo", request, payload)
    data = _load_json(response)

    assert data["token_set"] is True
    assert data["auto_start"] is True
    assert mongo.project is not None
    assert mongo.project.telegram_token == "12345:token"
    assert mongo.project.telegram_auto_start is True
    assert controller.is_project_running("demo") is True


@pytest.mark.asyncio
async def test_project_status_reflects_running_state() -> None:
    project = Project(name="demo", telegram_token="abcd1234", telegram_auto_start=False)
    mongo = _FakeMongo(project=project)
    controller = _FakeHub()
    controller.running["demo"] = True
    controller.tokens["demo"] = "abcd1234"

    request = _make_request(mongo, controller)
    response = await admin_project_telegram_status("demo", request)
    data = _load_json(response)

    assert data["project"] == "demo"
    assert data["running"] is True
    assert data["token_preview"] == "abcd…34"


@pytest.mark.asyncio
async def test_project_start_uses_existing_token() -> None:
    project = Project(name="demo", telegram_token="starttoken", telegram_auto_start=False)
    mongo = _FakeMongo(project=project)
    controller = _FakeHub()
    request = _make_request(mongo, controller)
    payload = ProjectTelegramAction()

    response = await admin_project_telegram_start("demo", request, payload)
    data = _load_json(response)

    assert controller.is_project_running("demo") is True
    assert controller.tokens["demo"] == "starttoken"
    assert data["running"] is True
    assert mongo.project.telegram_token == "starttoken"


@pytest.mark.asyncio
async def test_project_stop_can_update_auto_start() -> None:
    project = Project(name="demo", telegram_token="token", telegram_auto_start=True)
    mongo = _FakeMongo(project=project)
    controller = _FakeHub()
    controller.running["demo"] = True
    controller.tokens["demo"] = "token"

    request = _make_request(mongo, controller)
    payload = ProjectTelegramAction(auto_start=False)

    response = await admin_project_telegram_stop("demo", request, payload)
    data = _load_json(response)

    assert controller.is_project_running("demo") is False
    assert data["running"] is False
    assert mongo.project.telegram_auto_start is False
