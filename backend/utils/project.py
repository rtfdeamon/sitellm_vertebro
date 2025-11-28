"""Project utility functions."""

import os
from typing import TYPE_CHECKING

from backend.settings import settings

if TYPE_CHECKING:
    pass


def normalize_project(value: str | None) -> str | None:
    """Return a normalized project identifier."""
    candidate = (value or "").strip()
    if not candidate:
        default = getattr(settings, "project_name", None) or settings.domain or os.getenv("PROJECT_NAME") or os.getenv("DOMAIN", "")
        candidate = default.strip() if default else ""
    return candidate.lower() or None
