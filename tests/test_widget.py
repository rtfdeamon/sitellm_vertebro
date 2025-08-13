from fastapi.testclient import TestClient
from app import app


def test_widget_served():
    client = TestClient(app)
    response = client.get("/widget/")
    assert response.status_code == 200
    assert "LLM Chat Widget" in response.text
