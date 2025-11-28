"""Performance tests for API endpoint latency.

Tests verify that critical endpoints meet p95 < 500ms requirement.
"""

from __future__ import annotations

import time
import statistics
import pytest

from fastapi.testclient import TestClient
from app import app


@pytest.mark.performance
@pytest.mark.requires_mongo
@pytest.mark.requires_redis
class TestAPILatency:
    """Test API endpoint latency requirements."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_health_endpoint_latency(self, client: TestClient):
        """Test that /health endpoint responds quickly."""
        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            response = client.get("/health")
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            latencies.append(elapsed)
            assert response.status_code == 200

        p95 = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        assert p95 < 500, f"p95 latency {p95:.2f}ms exceeds 500ms threshold"

    def test_healthz_endpoint_latency(self, client: TestClient):
        """Test that /healthz endpoint responds quickly."""
        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            response = client.get("/healthz")
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)
            assert response.status_code == 200

        p95 = statistics.quantiles(latencies, n=20)[18]
        assert p95 < 100, f"p95 latency {p95:.2f}ms exceeds 100ms threshold for lightweight endpoint"

    def test_status_endpoint_latency(self, client: TestClient):
        """Test that /status endpoint responds within acceptable time."""
        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            response = client.get("/status")
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)
            assert response.status_code == 200

        p95 = statistics.quantiles(latencies, n=20)[18]
        # Status endpoint may be slower due to aggregations
        assert p95 < 1000, f"p95 latency {p95:.2f}ms exceeds 1000ms threshold"

    def test_csrf_token_endpoint_latency(self, client: TestClient):
        """Test that CSRF token endpoint responds quickly."""
        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            response = client.get("/api/v1/admin/csrf-token")
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)
            # May fail without auth, but should still be fast
            if response.status_code == 200:
                assert response.json().get("csrf_token") is not None

        if latencies:
            p95 = statistics.quantiles(latencies, n=20)[18]
            assert p95 < 500, f"p95 latency {p95:.2f}ms exceeds 500ms threshold"

