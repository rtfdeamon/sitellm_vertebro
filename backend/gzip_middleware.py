"""
GZip compression middleware for FastAPI.

Provides automatic compression of responses to reduce bandwidth.
"""

from __future__ import annotations

import os
import gzip
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, StreamingResponse

# GZip configuration
GZIP_ENABLED = os.getenv("GZIP_ENABLED", "true").lower() == "true"
GZIP_MIN_SIZE = int(os.getenv("GZIP_MIN_SIZE", "1000"))  # Compress responses > 1KB
GZIP_CONTENT_TYPES = {
    "application/json",
    "application/javascript",
    "text/html",
    "text/css",
    "text/plain",
    "text/xml",
    "application/xml",
    "text/event-stream",
}


class GZipMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic GZip compression of responses."""
    
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Compress response if enabled and applicable."""
        response = await call_next(request)
        
        if not GZIP_ENABLED:
            return response
        
        # Skip compression for streaming responses (they handle their own compression)
        if isinstance(response, StreamingResponse):
            return response
        
        # Check if client accepts gzip
        accept_encoding = request.headers.get("Accept-Encoding", "")
        if "gzip" not in accept_encoding.lower():
            return response
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        if not any(ct in content_type.lower() for ct in GZIP_CONTENT_TYPES):
            return response
        
        # Check content length
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                length = int(content_length)
                if length < GZIP_MIN_SIZE:
                    return response
            except ValueError:
                pass
        
        # Get response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        
        # Skip if body is too small
        if len(body) < GZIP_MIN_SIZE:
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        
        # Compress body
        compressed = gzip.compress(body, compresslevel=6)
        
        # Create new response with compressed body
        return Response(
            content=compressed,
            status_code=response.status_code,
            headers={
                **dict(response.headers),
                "Content-Encoding": "gzip",
                "Content-Length": str(len(compressed)),
            },
            media_type=response.media_type,
        )





