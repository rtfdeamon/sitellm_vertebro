"""Tests for project-scoped MAX admin endpoints."""

import json
import types

import pytest

from backend.bots.schemas import (
    ProjectMaxAction,
    ProjectMaxConfig,
)
from backend.projects.api import (
    admin_project_max_config,
    admin_project_max_start,
    admin_project_max_status,
    admin_project_max_stop,
)
from models import Project


class _FakeMaxHub:
    def __init__(self) -> None:
        self.runners: dict[str, dict] = {}
        self.errors: dict[str, str] = {}

    def is_project_running(self, project: str | None) -> bool:
        if not project or project not in self.runners:
            return False
        return self.runners[project].get("running", False)

    def get_last_error(self, project: str | None) -> str | None:
        return self.errors.get(project or "")

    async def ensure_runner(self, project: Project) -> None:
        token = project.max_token
        running = bool(token and project.max_auto_start)
        self.runners[project.name] = {
            "token": token,
            "running": running,
            "auto_start": bool(project.max_auto_start)
        }

    async def start_project(self, project: str, token: str) -> None:
        # Note: real hub takes project name and token
        self.runners[project] = {
            "token": token,
            "running": True,
            "auto_start": True # Implicit?
        }

    async def stop_project(
        self,
        project_name: str,
        *,
        auto_start: bool | None = None,
        forget_sessions: bool = False,
    ) -> None:
        if project_name not in self.runners:
            self.runners[project_name] = {"token": None, "running": False}
        
        self.runners[project_name]["running"] = False
        if auto_start is not None:
            self.runners[project_name]["auto_start"] = bool(auto_start)


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


def _make_request(mongo: _FakeMongo, controller: _FakeMaxHub):
    state = types.SimpleNamespace(mongo=mongo)
    app_state = types.SimpleNamespace(max=controller, telegram=None)
    app = types.SimpleNamespace(state=app_state)
    request = types.SimpleNamespace(state=state, app=app)
    return request


def _load_json(response) -> dict:
    return json.loads(response.body.decode())


from unittest.mock import patch

class TestProjectMaxAdminEndpoints:
    @pytest.fixture
    def client(self):
        from app import app
        from starlette.testclient import TestClient
        from unittest.mock import patch, AsyncMock, MagicMock
        from models import Project
        
        # Patch MongoClient in app module (since it's already imported)
        with patch("app.MongoClient") as mock_cls:
            mock_instance = mock_cls.return_value
            # Stateful mock
            projects_db = {}

            async def get_project_side_effect(name):
                p = projects_db.get(name)
                if p:
                    return p.model_copy()
                return None

            async def create_project_side_effect(name, **kwargs):
                p = Project(name=name, **kwargs)
                projects_db[name] = p
                return p

            async def update_project_side_effect(name, updates):
                if name in projects_db:
                    p = projects_db[name]
                    for k, v in updates.items():
                        setattr(p, k, v)
                    return p
                return None

            mock_instance.get_project = AsyncMock(side_effect=get_project_side_effect)
            mock_instance.create_project = AsyncMock(side_effect=create_project_side_effect)
            mock_instance.update_project = AsyncMock(side_effect=update_project_side_effect)
            
            # Also mock db attribute for other lookups if needed
            mock_instance.db = MagicMock()
            
            with TestClient(app) as c:
                yield c

    def test_project_config_creates_and_updates_token(self, client):
        fake_hub = _FakeMaxHub()
        # client.app.state.max_hub = fake_hub # Not used by get_instance
        
        # Mongo is already mocked by fixture
    
        with patch("backend.bots.max.MaxHub.get_instance", return_value=fake_hub):
            # 1. Create project with token
            resp = client.post(
                "/api/v1/admin/projects",
                json={"name": "max_p1", "maxToken": "token_A", "maxAutoStart": True},
                auth=("admin", "admin"),
            )
            if resp.status_code != 200:
                print(f"DEBUG: Response status: {resp.status_code}")
                print(f"DEBUG: Response body: {resp.text}")
            assert resp.status_code == 200
            
            # Verify start called
            assert "max_p1" in fake_hub.runners
            assert fake_hub.runners["max_p1"]["token"] == "token_A"
            assert fake_hub.runners["max_p1"]["running"] is True
    
            # 2. Update token
            resp = client.put(
                "/api/v1/admin/projects/max_p1",
                json={"maxToken": "token_B"},
                auth=("admin", "admin"),
            )
            assert resp.status_code == 200
    
            # Verify restart with new token
            assert fake_hub.runners["max_p1"]["token"] == "token_B"
            assert fake_hub.runners["max_p1"]["running"] is True

    def test_project_status_reflects_running_state(self, client):
        fake_hub = _FakeMaxHub()
        client.app.state.max_hub = fake_hub
        
        # Setup running project
        fake_hub.runners["max_p2"] = {"token": "t", "running": True}
        
        # Create project (no token provided in create, but hub says running?)
        # Actually create needs to match.
        # Let's just create it.
        client.post(
            "/api/v1/admin/projects",
            json={"name": "max_p2", "maxToken": "t", "maxAutoStart": True},
            auth=("admin", "admin"),
        )
        
        resp = client.get("/api/v1/admin/projects/max_p2", auth=("admin", "admin"))
        assert resp.status_code == 200
        data = resp.json()
        assert data["maxRunning"] is True

    def test_project_start_uses_existing_token(self, client):
        fake_hub = _FakeMaxHub()
        client.app.state.max_hub = fake_hub

        # Create stopped
        client.post(
            "/api/v1/admin/projects",
            json={"name": "max_p3", "maxToken": "token_C", "maxAutoStart": False},
            auth=("admin", "admin"),
        )
        assert fake_hub.runners["max_p3"]["running"] is False # Should be False initially

        # Manual start
        resp = client.post(
            "/api/v1/admin/projects/max_p3/max/start",
            auth=("admin", "admin"),
        )
        assert resp.status_code == 200
        assert fake_hub.runners["max_p3"]["running"] is True
        assert fake_hub.runners["max_p3"]["token"] == "token_C"

    def test_project_stop_can_update_auto_start(self, client):
        fake_hub = _FakeMaxHub()
        client.app.state.max_hub = fake_hub

        # Create running
        client.post(
            "/api/v1/admin/projects",
            json={"name": "max_p4", "maxToken": "token_D", "maxAutoStart": True},
            auth=("admin", "admin"),
        )
        assert fake_hub.runners["max_p4"]["running"] is True

        # Stop and disable auto-start
        resp = client.post(
            "/api/v1/admin/projects/max_p4/max/stop?auto_start=false",
            auth=("admin", "admin"),
        )
        assert resp.status_code == 200
        assert fake_hub.runners["max_p4"]["running"] is False # Should be False, not removed

        # Verify auto_start updated in DB (via API)
        resp = client.get("/api/v1/admin/projects/max_p4", auth=("admin", "admin"))
        assert resp.json()["maxAutoStart"] is False
