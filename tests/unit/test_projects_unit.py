import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException, Request
from backend.projects.schemas import ProjectCreate
from backend.projects.api import admin_create_project
from models import Project

class TestProjectsUnit:
    """Unit tests for project management components."""

    async def test_project_create_schema_validation(self):
        """Test ProjectCreate schema validation."""
        # Valid payload
        payload = ProjectCreate(name="test_project", title="Test Project")
        assert payload.name == "test_project"
        assert payload.title == "Test Project"
        assert payload.telegram_auto_start is None

        # Missing required field
        with pytest.raises(ValueError):
            ProjectCreate(title="No Name")

    async def test_project_model_defaults(self):
        """Test Project model default values."""
        project = Project(name="default_project")
        assert project.llm_emotions_enabled is True
        assert project.llm_voice_enabled is True
        assert project.debug_info_enabled is True
        assert project.knowledge_image_caption_enabled is True

    async def test_admin_create_project_success(self):
        """Test admin_create_project success path."""
        # Mock Request and Mongo
        mock_request = MagicMock(spec=Request)
        mock_mongo = AsyncMock()
        mock_request.state.mongo = mock_mongo
        
        # Mock existing project check (None means create new)
        mock_mongo.get_project.return_value = None
        
        # Mock create_project return value
        created_project = Project(name="new_project", title="New Project")
        mock_mongo.create_project.return_value = created_project

        payload = ProjectCreate(name="new_project", title="New Project")
        
        response = await admin_create_project(mock_request, payload)
        
        assert response.status_code == 200
        mock_mongo.create_project.assert_called_once()
        call_args = mock_mongo.create_project.call_args
        assert call_args[0][0] == "new_project"
        assert call_args[1]["title"] == "New Project"

    async def test_admin_create_project_update(self):
        """Test admin_create_project update path."""
        # Mock Request and Mongo
        mock_request = MagicMock(spec=Request)
        mock_mongo = AsyncMock()
        mock_request.state.mongo = mock_mongo
        
        # Mock existing project
        existing_project = Project(name="existing", title="Old Title")
        mock_mongo.get_project.return_value = existing_project
        
        # Mock update_project return value
        updated_project = Project(name="existing", title="New Title")
        mock_mongo.update_project.return_value = updated_project

        payload = ProjectCreate(name="existing", title="New Title")
        
        response = await admin_create_project(mock_request, payload)
        
        assert response.status_code == 200
        mock_mongo.update_project.assert_called_once()
        call_args = mock_mongo.update_project.call_args
        assert call_args[0][0] == "existing"
        assert call_args[0][1]["title"] == "New Title"

    async def test_admin_create_project_empty_name(self):
        """Test admin_create_project with empty name."""
        mock_request = MagicMock(spec=Request)
        payload = ProjectCreate(name="   ")
        
        with pytest.raises(HTTPException) as exc:
            await admin_create_project(mock_request, payload)
        
        assert exc.value.status_code == 400
        assert "Project name required" in exc.value.detail
