import importlib
import importlib.util
from pathlib import Path
import sys

import pytest

# Ensure real FastAPI modules are used instead of stubs from conftest
sys.modules["fastapi"] = importlib.import_module("fastapi")
sys.modules["fastapi.responses"] = importlib.import_module("fastapi.responses")
sys.modules["fastapi.testclient"] = importlib.import_module("fastapi.testclient")

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
APP_SPEC = importlib.util.spec_from_file_location("app_hub", APP_PATH)
app_module = importlib.util.module_from_spec(APP_SPEC)
sys.modules["app_hub"] = app_module
APP_SPEC.loader.exec_module(app_module)

Project = app_module.Project
TelegramHub = app_module.TelegramHub


class _FakeMongo:
    def __init__(self, projects):
        self._projects = projects

    async def list_projects(self):
        return self._projects

    async def log_request_stat(self, **kwargs):
        return None


@pytest.mark.asyncio
async def test_refresh_autostart(monkeypatch):
    started = {}

    class DummyRunner:
        def __init__(self, project, token, hub):
            self.project = project
            self.token = token
            self._hub = hub

        @property
        def is_running(self):
            return started.get(self.project) == self.token

        async def start(self):
            started[self.project] = self.token

        async def stop(self):
            started.pop(self.project, None)

    monkeypatch.setattr(app_module, "TelegramRunner", DummyRunner)

    project = Project(name="demo", telegram_token="123", telegram_auto_start=True)
    hub = TelegramHub(_FakeMongo([project]))
    await hub.refresh()

    assert started["demo"] == "123"


@pytest.mark.asyncio
async def test_start_project_with_auto_start(monkeypatch):
    started = {}

    class DummyRunner:
        def __init__(self, project, token, hub):
            self.project = project
            self.token = token
            self._hub = hub

        @property
        def is_running(self):
            return started.get(self.project) == self.token

        async def start(self):
            started[self.project] = self.token

        async def stop(self):
            started.pop(self.project, None)

    monkeypatch.setattr(app_module, "TelegramRunner", DummyRunner)

    mongo = _FakeMongo([])
    hub = TelegramHub(mongo)
    project = Project(name="demo", telegram_token="123", telegram_auto_start=True)
    await hub.start_project(project, auto_start=True)

    assert started["demo"] == "123"
