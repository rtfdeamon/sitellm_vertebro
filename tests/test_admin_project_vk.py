"""Tests for project-scoped VK admin endpoints."""

import json
import types

import pytest

from app import (
    ProjectVkAction,
    ProjectVkConfig,
    admin_project_vk_config,
    admin_project_vk_start,
    admin_project_vk_status,
    admin_project_vk_stop,
)
from packages.core.models import Project


class _FakeVkHub:
    def __init__(self) -> None:
        self.running: dict[str, bool] = {}
        self.tokens: dict[str, str] = {}
        self.auto_start: dict[str, bool] = {}
        self.errors: dict[str, str] = {}

    def is_project_running(self, project: str | None) -> bool:
        return bool(project and self.running.get(project))

    def get_last_error(self, project: str | None) -> str | None:
        return self.errors.get(project or "")

    async def ensure_runner(self, project: Project) -> None:
        token = project.vk_token
        if token:
            self.tokens[project.name] = token
        run = bool(token and project.vk_auto_start)
        self.running[project.name] = run
        self.auto_start[project.name] = bool(project.vk_auto_start)

    async def start_project(self, project: Project, *, auto_start: bool | None = None) -> None:
        if project.vk_token:
            self.tokens[project.name] = project.vk_token
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

    async def get_project(self, name: str) -> Project | None:  # pragma: no cover - simple helper
        return self.project

    async def upsert_project(self, project: Project) -> Project:
        self.saved = project
        self.project = project
        return project


def _make_request(mongo: _FakeMongo, controller: _FakeVkHub):
    state = types.SimpleNamespace(mongo=mongo)
    app_state = types.SimpleNamespace(vk=controller, telegram=None, max=None)
    app = types.SimpleNamespace(state=app_state)
    request = types.SimpleNamespace(state=state, app=app)
    return request


def _load_json(response) -> dict:
    return json.loads(response.body.decode())


@pytest.mark.asyncio
async def test_project_config_creates_and_updates_token() -> None:
    mongo = _FakeMongo(project=None)
    controller = _FakeVkHub()
    request = _make_request(mongo, controller)
    payload = ProjectVkConfig(token=" token123 ", auto_start=True)

    response = await admin_project_vk_config("demo", request, payload)
    data = _load_json(response)

    assert data["token_set"] is True
    assert data["auto_start"] is True
    assert mongo.project is not None
    assert mongo.project.vk_token == "token123"
    assert mongo.project.vk_auto_start is True
    assert controller.is_project_running("demo") is True


@pytest.mark.asyncio
async def test_project_status_reflects_running_state() -> None:
    project = Project(name="demo", vk_token="abc", vk_auto_start=False)
    mongo = _FakeMongo(project=project)
    controller = _FakeVkHub()
    controller.running["demo"] = True
    controller.tokens["demo"] = "abc"

    request = _make_request(mongo, controller)
    response = await admin_project_vk_status("demo", request)
    data = _load_json(response)

    assert data["project"] == "demo"
    assert data["running"] is True
    assert data["token_preview"] == "***"


@pytest.mark.asyncio
async def test_project_start_uses_existing_token() -> None:
    project = Project(name="demo", vk_token="starttoken", vk_auto_start=False)
    mongo = _FakeMongo(project=project)
    controller = _FakeVkHub()
    request = _make_request(mongo, controller)
    payload = ProjectVkAction()

    response = await admin_project_vk_start("demo", request, payload)
    data = _load_json(response)

    assert controller.is_project_running("demo") is True
    assert controller.tokens["demo"] == "starttoken"
    assert data["running"] is True
    assert mongo.project.vk_token == "starttoken"


@pytest.mark.asyncio
async def test_project_stop_can_update_auto_start() -> None:
    project = Project(name="demo", vk_token="token", vk_auto_start=True)
    mongo = _FakeMongo(project=project)
    controller = _FakeVkHub()
    controller.running["demo"] = True

    request = _make_request(mongo, controller)
    payload = ProjectVkAction(auto_start=False)

    response = await admin_project_vk_stop("demo", request, payload)
    data = _load_json(response)

    assert controller.is_project_running("demo") is False
    assert data["running"] is False
    assert mongo.project.vk_auto_start is False
