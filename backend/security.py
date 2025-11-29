"""
Security utilities for rate limiting and attack surface hardening.

Provides:
- Redis-backed rate limiting
- Query sanitization
- CSRF protection
- SSRF protection
"""

from __future__ import annotations

import os
import re
import socket
import ipaddress
import urllib.parse as urlparse
import structlog
from typing import Any
from datetime import datetime, timedelta, timezone

from redis import asyncio as redis_async
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse

logger = structlog.get_logger(__name__)

# Rate limiting configuration
RATE_LIMIT_READ_PER_MIN = int(os.getenv("RATE_LIMIT_READ_PER_MIN", "100"))
RATE_LIMIT_WRITE_PER_MIN = int(os.getenv("RATE_LIMIT_WRITE_PER_MIN", "10"))
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))

# Private IP ranges to block (SSRF protection)
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),  # Catch-all for invalid/unspecified
]

# Regex to detect MongoDB operator injection
MONGO_OPERATOR_REGEX = re.compile(r"^\$[a-z_]+", re.IGNORECASE)

# CSRF token configuration
CSRF_TOKEN_NAME = "X-CSRF-Token"
CSRF_COOKIE_NAME = "csrftoken"
CSRF_SECRET_KEY = os.getenv("CSRF_SECRET_KEY", "super-secret-csrf-key-change-me")


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    # Check X-Forwarded-For header (proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain
        ip = forwarded_for.split(",")[0].strip()
        if ip:
            return ip
    
    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fall back to direct client IP
    if request.client and request.client.host:
        return request.client.host
    
    return "unknown"


def sanitize_mongo_query(query: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize MongoDB query to prevent operator injection."""
    sanitized_query = {}
    for key, value in query.items():
        if MONGO_OPERATOR_REGEX.match(key):
            logger.warning("mongo_operator_injection_attempt", key=key)
            raise HTTPException(status_code=400, detail=f"Invalid query operator: {key}")
        if isinstance(value, dict):
            sanitized_query[key] = sanitize_mongo_query(value)
        elif isinstance(value, list):
            sanitized_query[key] = [
                sanitize_mongo_query(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized_query[key] = value
    return sanitized_query


def validate_url_for_ssrf(url: str) -> None:
    """Validate a URL to prevent Server-Side Request Forgery (SSRF).
    
    Raises ValueError if URL is unsafe (private IP, invalid scheme, etc.).
    """
    if not url:
        return
    
    # Basic scheme validation
    if not url.startswith(("http://", "https://")):
        logger.warning("ssrf_invalid_scheme", url=url)
        raise ValueError("Invalid URL scheme")
    
    # Parse URL components
    parsed_url = urlparse.urlparse(url)
    hostname = parsed_url.hostname
    if not hostname:
        logger.warning("ssrf_no_hostname", url=url)
        raise ValueError("URL has no hostname")
    
    # Resolve hostname to IP addresses
    try:
        # Use getaddrinfo to resolve all possible IPs and check them
        # This is more robust than gethostbyname which only returns one
        addr_info = socket.getaddrinfo(hostname, None)
        for family, socktype, proto, canonname, sa in addr_info:
            ip_str = sa[0]  # IPv4 address string
            if is_private_ip(ip_str):
                logger.warning("ssrf_private_ip_detected", url=url, ip=ip_str)
                raise ValueError("Access to private IP addresses is forbidden")
    except socket.gaierror:
        logger.warning("ssrf_hostname_resolution_failed", url=url, hostname=hostname)
        raise ValueError("Could not resolve hostname")
    except Exception as exc:  # noqa: BLE001
        logger.error("ssrf_validation_error", url=url, error=str(exc))
        raise ValueError("SSRF validation failed") from exc


def is_private_ip(ip_address_str: str) -> bool:
    """Check if an IP address is a private, loopback, or link-local address."""
    try:
        ip = ipaddress.ip_address(ip_address_str)
        return ip.is_link_local or ip.is_private or ip.is_loopback
    except ValueError:
        return False


class RateLimiter:
    """Redis-backed rate limiter."""
    
    def __init__(self, redis_client: redis_async.Redis | None = None):
        self.redis = redis_client
    
    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        period_seconds: int,
        request_type: str = "request",
    ) -> tuple[bool, int]:
        """
        Check if the given key has exceeded the rate limit.
        Returns (allowed, retry_after).
        """
        if not self.redis:
            logger.warning("rate_limiter_redis_unavailable", key=key)
            return True, 0  # Allow all requests if Redis is not configured
        
        now = datetime.now(timezone.utc)
        # Use a sorted set to store timestamps of requests
        # Score is timestamp, member is unique request ID (or just timestamp again)
        
        # Remove old entries
        await self.redis.zremrangebyscore(
            key, 0, (now - timedelta(seconds=period_seconds)).timestamp()
        )
        
        # Add current request
        await self.redis.zadd(key, {now.timestamp(): now.timestamp()})
        
        # Get current count
        current_count = await self.redis.zcard(key)
        
        # Set expiry for the key to clean up
        await self.redis.expire(key, period_seconds + 5)  # A bit longer than period
        
        if current_count > limit:
            logger.warning(
                "rate_limit_exceeded",
                key=key,
                limit=limit,
                period_seconds=period_seconds,
                current_count=current_count,
                request_type=request_type,
            )
            return False, period_seconds
            
        return True, 0

    async def check_read_limit(self, key: str) -> tuple[bool, int]:
        """Check if read rate limit is exceeded."""
        return await self.check_rate_limit(
            key,
            RATE_LIMIT_READ_PER_MIN,
            60,
            request_type="read",
        )

    async def check_write_limit(self, key: str) -> tuple[bool, int]:
        """Check if write rate limit is exceeded."""
        return await self.check_rate_limit(
            key,
            RATE_LIMIT_WRITE_PER_MIN,
            60,
            request_type="write",
        )


# Placeholder for CSRF token generation and validation
def generate_csrf_token() -> str:
    """Generate a random CSRF token."""
    return os.urandom(32).hex()


def validate_csrf_token(request: Request, token: str) -> bool:
    """Validate CSRF token against session/cookie."""
    # This is a simplified stub. In a real app, this would involve
    # comparing against a token stored in the user's session or a cookie
    # and ensuring it's not a replay attack.
    # For now, we'll just check if it's present and non-empty.
    return bool(token)


def require_super_admin(request: Request) -> None:
    """
    Decorator/dependency to ensure the user is a super admin.
    Logs unauthorized attempts.
    """
    if not getattr(request.state, "is_super_admin", False):
        logger.warning(
            "unauthorized_super_admin_access_attempt",
            user_id=getattr(request.state, "user_id", "unknown"),
            path=request.url.path,
            method=request.method,
            ip=get_client_ip(request),
        )
        raise HTTPException(status_code=403, detail="Operation requires super admin privileges")


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware for applying security headers and IP blocking.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Block private IP access if configured
        client_host = get_client_ip(request)
        if client_host and client_host != "unknown" and is_private_ip(client_host):
            logger.warning("private_ip_access_blocked", client_host=client_host, path=request.url.path)
            return JSONResponse(
                status_code=403,
                content={"detail": "Access from private IP addresses is forbidden"},
            )
        
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        # Example CSP - needs to be carefully configured for the specific frontend
        # response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
        
        return response
