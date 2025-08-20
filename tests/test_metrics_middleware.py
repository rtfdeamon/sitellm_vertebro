"""Tests for MetricsMiddleware registration."""

from starlette.applications import Starlette

from observability.metrics import MetricsMiddleware


def test_metrics_middleware_registration():
    app = Starlette()
    app.add_middleware(MetricsMiddleware)
    assert any(m.cls is MetricsMiddleware for m in app.user_middleware)
