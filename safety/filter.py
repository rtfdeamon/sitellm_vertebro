"""Utilities for detecting unsafe medical advice in generated text."""

from __future__ import annotations

import re
from typing import List

STOPWORDS: List[str] = [
    "азитромицин",
    "левофлоксацин",
    "дозировка",
    "мг/кг",
    "самолечение",
]

# Precompiled regular expression for fast checks.
_RE = re.compile("|".join(re.escape(w) for w in STOPWORDS), re.IGNORECASE)


def safety_check(text: str) -> bool:
    """Return ``True`` if ``text`` contains unsafe terminology."""
    return bool(_RE.search(text))
