"""Tests for handling missing Qdrant configuration."""

import importlib.util
import sys
from pathlib import Path

import pytest

# Dynamically import the search module to avoid side effects.
module_path = Path(__file__).resolve().parents[1] / "packages" / "retrieval" / "search.py"
spec = importlib.util.spec_from_file_location("packages.retrieval.search", module_path)
search = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = search
spec.loader.exec_module(search)


@pytest.mark.asyncio
async def test_hybrid_requires_qdrant():
    """Calling hybrid_search without qdrant should raise an error."""
    search.qdrant = None
    with pytest.raises(RuntimeError, match="Qdrant not configured"):
        await search.hybrid_search("query")


@pytest.mark.asyncio
async def test_vector_requires_qdrant():
    """Calling vector_search without qdrant should raise an error."""
    search.qdrant = None
    with pytest.raises(RuntimeError, match="Qdrant not configured"):
        await search.vector_search("query")
