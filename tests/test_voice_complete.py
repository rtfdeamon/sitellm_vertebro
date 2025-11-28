#!/usr/bin/env python3
"""
Complete voice feature test suite.

Runs all voice-related tests to ensure complete functionality.
"""

from __future__ import annotations

import pytest


def test_voice_router_tests():
    """Run voice router unit tests."""
    pytest.main(["-v", "tests/test_voice_router.py", "--tb=short"])


def test_voice_e2e_tests():
    """Run voice E2E tests."""
    pytest.main(["-v", "tests/test_voice_e2e.py", "--tb=short"])


def test_voice_browser_dialogs():
    """Run voice browser dialog tests."""
    pytest.main(["-v", "tests/test_voice_browser_dialogs.py", "--tb=short"])


if __name__ == "__main__":
    # Run all voice tests
    exit_code = 0
    exit_code |= pytest.main(["-v", "tests/test_voice_router.py", "--tb=short"])
    exit_code |= pytest.main(["-v", "tests/test_voice_e2e.py", "--tb=short"])
    exit_code |= pytest.main(["-v", "tests/test_voice_browser_dialogs.py", "--tb=short"])
    exit(exit_code)

