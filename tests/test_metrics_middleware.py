"""Tests for ``MetricsMiddleware`` registration."""

import sys

from starlette.applications import Starlette
from starlette.middleware import Middleware

# Ensure the ``fastapi`` stub provides ``Request`` for metrics import.
sys.modules["fastapi"].Request = type("Request", (), {})

from observability.metrics import MetricsMiddleware


def test_metrics_middleware_registration():
    app = Starlette()
    app.add_middleware(MetricsMiddleware)
    assert any(
        isinstance(m, Middleware) and m.cls is MetricsMiddleware
        for m in app.user_middleware
    )
