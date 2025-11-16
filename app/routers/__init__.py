"""FastAPI routers package.

This package contains all API route handlers organized by domain:
- admin: Administrative endpoints
- backup: Backup and restore operations
- stats: Statistics and logging
- projects: Project CRUD and bot management (Telegram, MAX, VK)
- knowledge: Knowledge base management (documents, Q&A, unanswered questions)
- llm: LLM and Ollama endpoints
"""

from __future__ import annotations

__all__ = [
    "admin",
    "backup",
    "stats",
    "projects",
    "knowledge",
    "llm",
]

