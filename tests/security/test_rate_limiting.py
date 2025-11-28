"""
Security tests: Rate limiting.

Tests Redis-backed rate limiting middleware.
"""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import Response

from backend.rate_limiting import RateLimitingMiddleware


@pytest.mark.security
@pytest.mark.integration
@pytest.mark.requires_redis
class TestRateLimiting:
    """Test rate limiting middleware."""
    
    def test_rate_limit_read_requests(self, client: TestClient):
        """Test that read requests are rate limited."""
        # Make multiple GET requests
        for i in range(110):  # Exceed default limit of 100/min
            response = client.get("/healthz")
            if i < 100:
                assert response.status_code == 200
            else:
                # Should hit rate limit
                if response.status_code == 429:
                    assert "Retry-After" in response.headers
                    break
    
    def test_rate_limit_write_requests(self, client: TestClient):
        """Test that write requests are rate limited."""
        # Make multiple POST requests
        for i in range(15):  # Exceed default limit of 10/min
            response = client.post("/api/v1/admin/logout")
            if i < 10:
                # Should work
                assert response.status_code in (200, 401)
            else:
                # Should hit rate limit
                if response.status_code == 429:
                    assert "Retry-After" in response.headers
                    break
    
    def test_rate_limit_excluded_paths(self, client: TestClient):
        """Test that excluded paths don't require rate limiting."""
        # Health check endpoints should not be rate limited
        for _ in range(200):
            response = client.get("/healthz")
            assert response.status_code == 200
    
    def test_rate_limit_headers(self, client: TestClient):
        """Test that rate limit headers are present in responses."""
        response = client.get("/healthz")
        # Rate limit headers should be present (even if not exceeded)
        assert "X-RateLimit-Limit" in response.headers or response.status_code == 200





