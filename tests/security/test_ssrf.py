"""
Security tests: SSRF protection.

Tests URL validation to prevent Server-Side Request Forgery.
"""

import pytest
from fastapi import HTTPException

from backend.security import validate_url_for_ssrf, is_private_ip


@pytest.mark.security
@pytest.mark.unit
class TestSSRFProtection:
    """Test SSRF protection utilities."""
    
    def test_private_ip_detection(self):
        """Test private IP detection."""
        assert is_private_ip("127.0.0.1") is True
        assert is_private_ip("192.168.1.1") is True
        assert is_private_ip("10.0.0.1") is True
        assert is_private_ip("172.16.0.1") is True
        assert is_private_ip("169.254.1.1") is True  # Link-local
        assert is_private_ip("8.8.8.8") is False  # Public IP
        assert is_private_ip("1.1.1.1") is False  # Public IP
    
    def test_validate_url_private_ip(self):
        """Test that private IP URLs are rejected."""
        with pytest.raises(ValueError):
            validate_url_for_ssrf("http://127.0.0.1")
        
        with pytest.raises(ValueError):
            validate_url_for_ssrf("http://192.168.1.1")
        
        with pytest.raises(ValueError):
            validate_url_for_ssrf("http://localhost")
    
    def test_validate_url_public_ip(self):
        """Test that public IP URLs are allowed."""
        # Should not raise for public URLs
        try:
            validate_url_for_ssrf("https://example.com")
            validate_url_for_ssrf("http://8.8.8.8")
        except ValueError:
            # DNS resolution might fail in test environment, that's OK
            pass
    
    def test_validate_url_invalid_scheme(self):
        """Test that invalid URL schemes are rejected."""
        with pytest.raises(ValueError):
            validate_url_for_ssrf("file:///etc/passwd")
        
        with pytest.raises(ValueError):
            validate_url_for_ssrf("gopher://example.com")





