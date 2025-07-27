"""Pytest configuration with basic asyncio support."""

import asyncio
import pytest


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
