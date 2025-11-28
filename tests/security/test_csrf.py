"""
Security tests: CSRF protection.

Tests CSRF token generation and validation.
"""

import pytest
from fastapi.testclient import TestClient

from backend.csrf import generate_csrf_token, verify_csrf_token, get_csrf_token


@pytest.mark.security
@pytest.mark.unit
class TestCSRF:
    """Test CSRF protection."""
    
    def test_csrf_token_generation(self):
        """Test that CSRF tokens are generated correctly."""
        token1 = generate_csrf_token()
        token2 = generate_csrf_token()
        
        assert len(token1) > 0
        assert len(token2) > 0
        assert token1 != token2  # Tokens should be unique
    
    def test_csrf_token_verification(self):
        """Test CSRF token verification."""
        token = generate_csrf_token()
        
        # Valid token
        assert verify_csrf_token(token, token) is True
        
        # Invalid token
        assert verify_csrf_token(token, "invalid") is False
        assert verify_csrf_token(token, None) is False
        assert verify_csrf_token(None, token) is False
    
    def test_csrf_endpoint(self, client: TestClient):
        """Test CSRF token endpoint."""
        response = client.get("/api/v1/admin/csrf-token")
        
        # Should return CSRF token
        assert response.status_code == 200
        data = response.json()
        assert "csrf_token" in data
        assert len(data["csrf_token"]) > 0





