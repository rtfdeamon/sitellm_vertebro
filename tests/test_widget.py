from fastapi.testclient import TestClient
from app import app
from core.build import get_build_info


def test_widget_served():
    client = TestClient(app)
    response = client.get("/widget/")
    assert response.status_code == 200
    assert "LLM Chat Widget" in response.text


def test_build_info_contains_metadata():
    info = get_build_info()
    assert "version" in info
    assert "built_at" in info
    assert "built_at_iso" in info
