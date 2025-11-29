import pytest
from unittest.mock import patch
from backend.system.api import health, healthz

class TestSystemUnit:
    """Unit tests for system health components."""

    def test_healthz(self):
        """Test lightweight liveness probe."""
        response = healthz()
        assert response == {"status": "ok"}

    @patch("backend.system.api.mongo_check")
    @patch("backend.system.api.redis_check")
    @patch("backend.system.api.qdrant_check")
    def test_health_all_ok(self, mock_qdrant, mock_redis, mock_mongo):
        """Test health check when all services are healthy."""
        mock_mongo.return_value = (True, None)
        mock_redis.return_value = (True, None)
        mock_qdrant.return_value = (True, None)

        response = health()
        
        assert response["status"] == "ok"
        assert response["mongo"] is True
        assert response["redis"] is True
        assert response["qdrant"] is True
        assert response["details"]["mongo"]["ok"] is True

    @patch("backend.system.api.mongo_check")
    @patch("backend.system.api.redis_check")
    @patch("backend.system.api.qdrant_check")
    def test_health_degraded(self, mock_qdrant, mock_redis, mock_mongo):
        """Test health check when a service is down."""
        mock_mongo.return_value = (False, "Connection failed")
        mock_redis.return_value = (True, None)
        mock_qdrant.return_value = (True, None)

        response = health()
        
        assert response["status"] == "degraded"
        assert response["mongo"] is False
        assert response["details"]["mongo"]["error"] == "Connection failed"
