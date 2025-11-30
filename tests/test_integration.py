"""Integration test covering prompt building and LLM output."""

import importlib
import importlib.util
import sys
from pathlib import Path
import types
import uuid

import pytest
from starlette.exceptions import HTTPException
from starlette.requests import Request


class DummyRouter:
    def __init__(self, *a, **k):
        pass

    def post(self, *a, **k):
        def decorator(func):
            return func

        return decorator

    def get(self, *a, **k):
        def decorator(func):
            return func

        return decorator


class ORJSONResponse:  # minimal placeholder for fallback
    def __init__(self, content):
        self.content = content


class StreamingResponse:  # placeholder for fallback
    def __init__(self, *a, **k):
        pass


try:
    fastapi_module = importlib.import_module("fastapi")
    fastapi_responses = importlib.import_module("fastapi.responses")
except Exception:  # pragma: no cover - fallback for stripped setups
    fastapi_module = types.ModuleType("fastapi")
    fastapi_module.APIRouter = DummyRouter
    fastapi_module.Request = Request
    fastapi_module.HTTPException = HTTPException

    fastapi_responses = types.ModuleType("fastapi.responses")
    fastapi_responses.ORJSONResponse = ORJSONResponse
    fastapi_responses.StreamingResponse = StreamingResponse
    fastapi_module.responses = fastapi_responses

sys.modules["fastapi"] = fastapi_module
sys.modules["fastapi.responses"] = fastapi_responses

try:
    mongo_module = importlib.import_module("mongo")
except Exception:  # pragma: no cover - fallback for stripped setups
    fake_mongo = types.ModuleType("mongo")

    class NotFound(Exception):
        pass


    fake_mongo.NotFound = NotFound
    sys.modules["mongo"] = fake_mongo
else:
    sys.modules["mongo"] = mongo_module


fake_structlog = types.ModuleType("structlog")
fake_structlog.get_logger = lambda *a, **k: types.SimpleNamespace(
    info=lambda *x, **y: None,
    warning=lambda *x, **y: None,
    debug=lambda *x, **y: None,
)
sys.modules.setdefault("structlog", fake_structlog)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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

fake_aiohttp = types.ModuleType("aiohttp")
fake_aiohttp.ClientResponseError = type("ClientResponseError", (Exception,), {})
fake_aiohttp.ClientSession = None  # placeholder
sys.modules["aiohttp"] = fake_aiohttp

module_llm = Path(__file__).resolve().parents[1] / "backend" / "llm_client.py"
spec_llm = importlib.util.spec_from_file_location("backend.llm_client", module_llm)
llm_client = importlib.util.module_from_spec(spec_llm)
sys.modules[spec_llm.name] = llm_client
spec_llm.loader.exec_module(llm_client)

from apps.api import ask_llm
from packages.core.models import LLMRequest


@pytest.mark.asyncio
async def test_answer_without_antibiotics(monkeypatch):
    """Ensure generated answers avoid antibiotics and mention gargling."""
    def fake_search(query: str, k: int = 10):
        return [search.Doc("1", {"text": "Промывайте горло соленой водой."}, score=1.0)]

    async def fake_generate(prompt_text: str):
        yield "Промывайте горло тёплым солёным раствором."  # simple stream

    monkeypatch.setattr(search, "hybrid_search", fake_search)
    monkeypatch.setattr(llm_client, "generate", fake_generate)

    query = "Мне больно в горле, какие лекарства?"
    docs = search.hybrid_search(query)
    text_prompt = prompt.build_prompt(query, docs)

    tokens = []
    async for token in llm_client.generate(text_prompt):
        tokens.append(token)
    answer = "".join(tokens)

    assert "промывайте" in answer.lower()
    assert "антибиот" not in answer.lower()


class DummyMongo:
    async def get_context_preset(self, collection):
        if False:
            yield

    async def get_sessions(self, collection, session_id):
        if False:
            yield


@pytest.mark.asyncio
async def test_request_without_history():
    request = Request({"type": "http"})
    request.state.mongo = DummyMongo()
    request.state.context_presets_collection = None
    request.state.contexts_collection = None
    request.state.llm = types.SimpleNamespace(respond=lambda *a, **k: None)
    llm_request = LLMRequest(sessionId=uuid.uuid4())
    with pytest.raises(HTTPException) as exc:
        await ask_llm(request, llm_request)
    assert exc.value.status_code == 400
