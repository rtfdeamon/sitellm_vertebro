"""Prometheus metrics instrumentation."""

from __future__ import annotations

import time

from collections.abc import Awaitable, Callable

from fastapi import Request
from prometheus_client import Counter, Histogram, make_asgi_app
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

request_count = Counter("request_count", "HTTP requests", ["method", "path"])
latency_ms = Histogram("latency_ms", "Request latency in ms")
error_count = Counter("error_count", "Error responses", ["path"])

metrics_app = make_asgi_app()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record Prometheus metrics for each request."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Measure latency and increment counters for ``request``."""
        start = time.perf_counter()
        response = await call_next(request)
        duration = (time.perf_counter() - start) * 1000
        request_count.labels(request.method, request.url.path).inc()
        latency_ms.observe(duration)
        if response.status_code >= 500:
            error_count.labels(request.url.path).inc()
        return response
