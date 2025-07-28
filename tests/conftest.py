"""Pytest configuration with basic asyncio support."""

import asyncio
import types
import sys
import pytest

# Provide a minimal ``structlog`` stub for modules that expect it.
fake_structlog = types.ModuleType("structlog")
fake_structlog.get_logger = lambda *a, **k: types.SimpleNamespace(
    info=lambda *args, **kw: None,
    warning=lambda *args, **kw: None,
    debug=lambda *args, **kw: None,
)
sys.modules.setdefault("structlog", fake_structlog)


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
