"""Unit tests ensuring cross-encoder reranking sorts documents by predicted relevance."""

import importlib.util
import sys
import types
from pathlib import Path

module_search = Path(__file__).resolve().parents[1] / "retrieval" / "search.py"
spec_search = importlib.util.spec_from_file_location(
    "retrieval.search", module_search
)
search = importlib.util.module_from_spec(spec_search)
sys.modules[spec_search.name] = search
spec_search.loader.exec_module(search)

module_rerank = Path(__file__).resolve().parents[1] / "retrieval" / "rerank.py"
spec_rerank = importlib.util.spec_from_file_location(
    "retrieval.rerank", module_rerank
)
rerank = importlib.util.module_from_spec(spec_rerank)
sys.modules[spec_rerank.name] = rerank


class FakeCrossEncoder:
    """Minimal mock of :class:`CrossEncoder` returning predefined scores."""

    def __init__(self, scores):
        self.scores = scores
        self.calls = []

    def predict(self, pairs):
        self.calls.append(pairs)
        return self.scores[: len(pairs)]


def setup_module(module):
    """Prepare fake ``sentence_transformers`` module for tests."""
    fake = types.ModuleType("sentence_transformers")
    fake.CrossEncoder = None  # placeholder
    sys.modules["sentence_transformers"] = fake


def test_rerank_order_and_scores():
    """Documents should be ordered by descending cross-score."""
    sys.modules["sentence_transformers"].CrossEncoder = lambda name: FakeCrossEncoder([0.1, 0.3, 0.2])
    spec_rerank.loader.exec_module(rerank)

    docs = [search.Doc("A"), search.Doc("B"), search.Doc("C")]
    result = rerank.rerank("q", docs, top=2)

    assert [d.id for d in result] == ["B", "C"]
    assert getattr(result[0], "cross_score") == 0.3
    assert getattr(result[1], "cross_score") == 0.2


def test_rerank_noop_for_small_list():
    """If ``docs`` length <= top the list is returned unchanged."""
    sys.modules["sentence_transformers"].CrossEncoder = lambda name: FakeCrossEncoder([1])
    spec_rerank.loader.exec_module(rerank)

    docs = [search.Doc("A"), search.Doc("B")]
    result = rerank.rerank("q", docs, top=2)
    assert result is docs

