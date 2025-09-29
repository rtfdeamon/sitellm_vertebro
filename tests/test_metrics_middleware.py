"""Tests for ``MetricsMiddleware`` registration."""

from starlette.applications import Starlette
from starlette.middleware import Middleware

from observability.metrics import MetricsMiddleware


def test_metrics_middleware_registration():
    app = Starlette()
    app.add_middleware(MetricsMiddleware)
    assert any(
        isinstance(m, Middleware) and m.cls is MetricsMiddleware
        for m in app.user_middleware
    )
