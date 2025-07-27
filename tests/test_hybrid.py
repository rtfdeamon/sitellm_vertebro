import importlib.util
import sys
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "retrieval" / "search.py"
spec = importlib.util.spec_from_file_location("search", module_path)
search = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = search
spec.loader.exec_module(search)


class FakeDoc(search.Doc):
    pass


class FakeQdrant:
    def similarity(self, query, top, method):
        if method == "dense":
            return [FakeDoc("A"), FakeDoc("B"), FakeDoc("C")]
        return [FakeDoc("C"), FakeDoc("A"), FakeDoc("D")]


def test_hybrid_search_order():
    search.qdrant = FakeQdrant()
    result = search.hybrid_search("test", k=4)
    assert [doc.id for doc in result] == ["A", "C", "B", "D"]
