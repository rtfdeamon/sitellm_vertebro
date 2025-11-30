"""Backward compatibility stub for api.py - delegates to apps.api.main."""
from apps.api.main import (
    llm_router,
    crawler_router,
    reading_router,
    voice_router,
    _DEFAULT_KNOWLEDGE_PRIORITY,
    _KNOWN_KNOWLEDGE_SOURCES,
)

__all__ = [
    "llm_router",
    "crawler_router",
    "reading_router",
    "voice_router",
    "_DEFAULT_KNOWLEDGE_PRIORITY",
    "_KNOWN_KNOWLEDGE_SOURCES",
]
