"""Unit tests for the safety filter that flags unsafe medical terms."""

import importlib.util
import sys
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "safety" / "filter.py"
spec = importlib.util.spec_from_file_location("safety.filter", module_path)
safety = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = safety
spec.loader.exec_module(safety)


def test_safety_check_positive():
    """Each stopword must trigger ``True`` from :func:`safety_check`."""
    for word in safety.STOPWORDS:
        assert safety.safety_check(f"Текст содержит {word}.")


def test_safety_check_negative():
    """A clean sentence should not be flagged as unsafe."""
    assert not safety.safety_check("Это безопасный текст без запрещенных слов.")

