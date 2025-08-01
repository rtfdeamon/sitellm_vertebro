"""Tests for prompt generation utilities."""

import importlib.util
import sys
from pathlib import Path

module_search = Path(__file__).resolve().parents[1] / "retrieval" / "search.py"
spec_search = importlib.util.spec_from_file_location("retrieval.search", module_search)
search = importlib.util.module_from_spec(spec_search)
sys.modules[spec_search.name] = search
spec_search.loader.exec_module(search)

module_prompt = Path(__file__).resolve().parents[1] / "backend" / "prompt.py"
spec_prompt = importlib.util.spec_from_file_location("backend.prompt", module_prompt)
prompt = importlib.util.module_from_spec(spec_prompt)
sys.modules[spec_prompt.name] = prompt
spec_prompt.loader.exec_module(prompt)


def test_build_prompt_basic():
    """Ensure prompt text selects and formats top documents."""
    long_text = "Sentence. " * 80  # >300 chars
    docs = [
        search.Doc("1", {"text": long_text}, score=0.9),
        search.Doc("2", {"text": "Second doc."}, score=0.8),
        search.Doc("3", {"text": "Third."}, score=0.5),
        search.Doc("4", {"text": "Fourth."}, score=0.1),
    ]
    result = prompt.build_prompt("Q?", docs)

    assert result.startswith("SYSTEM: Используй ТОЛЬКО данные ниже для ответа.")
    assert result.strip().endswith("ANSWER:")
    assert result.count("Документ #") == 3
    assert "Fourth" not in result

    start = result.index("Документ #1:\n") + len("Документ #1:\n")
    end = result.index("\n\nДокумент #2:")
    frag1 = result[start:end]
    assert len(frag1) <= 300
    assert frag1.endswith(".")
