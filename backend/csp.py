"""
Content Security Policy (CSP) utilities for security headers.

Provides CSP header generation and middleware integration.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# CSP configuration
CSP_ENABLED = os.getenv("CSP_ENABLED", "true").lower() == "true"
CSP_STRICT = os.getenv("CSP_STRICT", "false").lower() == "true"

# Default CSP policy
DEFAULT_CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # Allow inline scripts for compatibility
    "style-src 'self' 'unsafe-inline'; "  # Allow inline styles
    "img-src 'self' data: https:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "  # Prevent clickjacking
    "base-uri 'self'; "
    "form-action 'self'; "
    "upgrade-insecure-requests;"
)

# Strict CSP policy (for production)
STRICT_CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "  # No inline scripts
    "style-src 'self'; "  # No inline styles
    "img-src 'self' data: https:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "upgrade-insecure-requests;"
)


class CSPMiddleware(BaseHTTPMiddleware):
    """Middleware for adding Content Security Policy headers."""
    
    def __init__(self, app: Any, policy: str | None = None):
        super().__init__(app)
        self.policy = policy or (STRICT_CSP_POLICY if CSP_STRICT else DEFAULT_CSP_POLICY)
    
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Add CSP headers to response."""
        response = await call_next(request)
        
        if CSP_ENABLED:
            response.headers["Content-Security-Policy"] = self.policy
            # Add report-only header for testing
            if os.getenv("CSP_REPORT_ONLY", "false").lower() == "true":
                response.headers["Content-Security-Policy-Report-Only"] = self.policy
        
        # Additional security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response





