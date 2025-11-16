"""App package for SiteLLM Vertebro.

Provides FastAPI application and routers.
"""

from __future__ import annotations

# Backward compatibility: app instance is defined in app.py (root level module)
# For backward compatibility, users should import directly:
#   - `from app import app` (imports app.py module at root level, not this package)
#   - Or use factory: `from app.main import create_app`
# This package exports routers, services, and factory function

# Export routers for explicit imports
from app.routers import (
    backup,
    stats,
    admin,
    projects,
    knowledge,
    llm as llm_admin,
)

# Export services
from app.services import auth

# Export factory function
from app.main import create_app

__all__ = [
    # Note: app instance is in app.py at root level, not exported from this package
    # Use `from app import app` to import from app.py, or `from app.main import create_app`
    "create_app",
    "backup",
    "stats",
    "admin",
    "projects",
    "knowledge",
    "llm_admin",
    "auth",
]
