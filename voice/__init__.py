"""
Voice assistant package scaffolding.

This module exposes light-weight helpers for deferred imports so that the rest
of the project can reference `voice` symbols even before the feature is fully
implemented.
"""

from .router import voice_assistant_router  # noqa: F401

