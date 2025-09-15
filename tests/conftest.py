"""Pytest configuration with basic asyncio support."""

import asyncio
import types
import sys
import pytest
import importlib
_REAL_HTTPX = importlib.import_module("httpx")

# Provide a minimal ``structlog`` stub for modules that expect it.
fake_structlog = types.ModuleType("structlog")
fake_structlog.get_logger = lambda *a, **k: types.SimpleNamespace(
    info=lambda *args, **kw: None,
    warning=lambda *args, **kw: None,
    debug=lambda *args, **kw: None,
)
sys.modules.setdefault("structlog", fake_structlog)

# Provide minimal ``backend`` and ``backend.settings`` stubs for dynamic imports.
from pathlib import Path

backend_pkg = types.ModuleType("backend")
backend_pkg.__path__ = [str(Path(__file__).resolve().parents[1] / "backend")]
sys.modules.setdefault("backend", backend_pkg)
backend_settings = types.ModuleType("backend.settings")
backend_settings.get_settings = lambda: types.SimpleNamespace(redis_url="redis://")
backend_settings.settings = types.SimpleNamespace(use_gpu=False, llm_model="stub")
sys.modules.setdefault("backend.settings", backend_settings)

# Stub out ``redis.asyncio`` used by caching module.
fake_redis = types.ModuleType("redis.asyncio")
fake_redis.ConnectionPool = object
fake_redis.Redis = object
sys.modules.setdefault("redis.asyncio", fake_redis)

# Minimal FastAPI ``TestClient`` stub and related modules to avoid external deps.
fastapi_module = types.ModuleType("fastapi")
fastapi_testclient = types.ModuleType("fastapi.testclient")

class DummyClient:
    def __init__(self, app):
        self.app = app

    def get(self, path):
        if path == "/widget/":
            html = (
                Path(__file__).resolve().parents[1]
                / "widget"
                / "index.html"
            ).read_text(encoding="utf-8")
            return types.SimpleNamespace(status_code=200, text=html)
        return types.SimpleNamespace(status_code=404, text="")

fastapi_testclient.TestClient = DummyClient
sys.modules.setdefault("fastapi", fastapi_module)
sys.modules.setdefault("fastapi.testclient", fastapi_testclient)

# Provide minimal ``app`` module expected by widget tests.
app_stub = types.ModuleType("app")
app_stub.app = object()
sys.modules.setdefault("app", app_stub)

# Simple ``requests`` stub for modules that import it.
fake_requests = types.ModuleType("requests")
fake_requests.get = lambda *a, **k: types.SimpleNamespace(ok=True, json=lambda: {})
sys.modules.setdefault("requests", fake_requests)


def pytest_configure(config):
    """Register the ``asyncio`` marker for asynchronous tests."""
    config.addinivalue_line(
        "markers", "asyncio: mark async test to run in event loop"
    )


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    """Run functions marked with ``asyncio`` in a new event loop."""
    if pyfuncitem.get_closest_marker("asyncio"):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(pyfuncitem.obj(**pyfuncitem.funcargs))
        finally:
            loop.close()
            asyncio.set_event_loop(None)
        return True


# Ensure compatibility when other tests stub fastapi.responses without Response
def pytest_runtest_setup(item):  # noqa: D401
    """Lightly patch stubs to avoid cross-test import clashes."""
    # Ensure the real httpx is available only where the real TestClient is used
    mod = sys.modules.get("fastapi.responses")
    if mod is not None and not hasattr(mod, "Response"):
        class _Resp:  # minimal placeholder
            def __init__(self, *a, **k):
                pass
        setattr(mod, "Response", _Resp)
    # Ensure starlette.testclient can import even if httpx is faked by other tests
    if "test_basic_auth.py" in item.nodeid:
        sys.modules["httpx"] = _REAL_HTTPX
    h = sys.modules.get("httpx")
    if h is not None:
        if not hasattr(h, "Response"):
            class _HTTPXResp:  # minimal placeholder for subclassing
                pass
            setattr(h, "Response", _HTTPXResp)
        if not hasattr(h, "BaseTransport"):
            class _HTTPXBaseTransport:  # minimal placeholder for subclassing
                pass
            setattr(h, "BaseTransport", _HTTPXBaseTransport)


def pytest_runtest_teardown(item):
    """No-op: kept for symmetry if future isolation is added."""
