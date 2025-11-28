"""Smoke tests for all routers.

Basic tests to ensure routers can be imported and registered without errors.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_backup_router_import():
    """Test that backup router can be imported."""
    from app.routers import backup
    
    assert backup.router is not None
    assert hasattr(backup.router, "routes")


def test_stats_router_import():
    """Test that stats router can be imported."""
    from app.routers import stats
    
    assert stats.router is not None
    assert hasattr(stats.router, "routes")


def test_admin_router_import():
    """Test that admin router can be imported."""
    from app.routers import admin
    
    assert admin.router is not None
    assert hasattr(admin.router, "routes")


def test_projects_router_import():
    """Test that projects router can be imported."""
    from app.routers import projects
    
    assert projects.router is not None
    assert hasattr(projects.router, "routes")


def test_knowledge_router_import():
    """Test that knowledge router can be imported."""
    from app.routers import knowledge
    
    assert knowledge.router is not None
    assert hasattr(knowledge.router, "routes")


def test_llm_router_import():
    """Test that LLM router can be imported."""
    from app.routers import llm
    
    assert llm.router is not None
    assert hasattr(llm.router, "routes")


def test_main_factory():
    """Test that create_app factory function works."""
    from app.main import create_app
    
    app = create_app(debug=False)
    assert app is not None
    assert isinstance(app, FastAPI)


def test_app_import():
    """Test that app can be imported from app package."""
    from app import app
    
    assert app is not None
    assert isinstance(app, FastAPI)


def test_routers_registered():
    """Test that all routers are registered in the app."""
    from app import app
    
    router_paths = {route.path for route in app.routes}
    
    # Check that key router paths exist
    assert "/api/v1/admin/backup/status" in router_paths or any(
        "/backup" in path for path in router_paths
    )
    assert "/api/v1/admin/stats/requests" in router_paths or any(
        "/stats" in path for path in router_paths
    )
    assert "/health" in router_paths or "/healthz" in router_paths
    assert "/api/v1/admin/projects" in router_paths or any(
        "/projects" in path for path in router_paths
    )


def test_admin_router_health_endpoint():
    """Test that health endpoint is accessible."""
    from app import app
    
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

