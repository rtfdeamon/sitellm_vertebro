"""FastAPI router with an endpoint for interacting with the LLM."""

from __future__ import annotations

import inspect

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import ORJSONResponse, StreamingResponse

import structlog

from backend import llm_client, prompt
from backend.settings import settings as base_settings
from retrieval import search
from settings import get_settings

from mongo import NotFound, MongoClient

logger = structlog.get_logger(__name__)
settings = get_settings()

# ``textnorm`` may not be available in all environments. Provide fallbacks
# so that importing this module does not fail during tests.
try:  # pragma: no cover - optional dependency
    import textnorm  # type: ignore
except Exception:  # pragma: no cover - missing optional module
    class _TextNorm:  # noqa: D401 - simple namespace for fallbacks
        """Fallback normalizer used when ``textnorm`` isn't installed."""

        @staticmethod
        def normalize_query(query: str) -> str:
            return query

        @staticmethod
        async def rewrite_query(query: str) -> str:  # pragma: no cover - trivial
            return query

    textnorm = _TextNorm()  # type: ignore


class QueryLogger:
    """Wrapper class to log all steps of the query processing pipeline."""

    def __init__(self, mongo_client: MongoClient, llm_client_module):
        self.mongo = mongo_client
        self.llm_client = llm_client_module
        self.documents_collection = get_settings().mongo.documents
        # Initialize Qdrant client if not already set
        if search.qdrant is None:  # pragma: no cover - network/client setup
            try:
                from qdrant_client import QdrantClient

                search.qdrant = QdrantClient(url=str(base_settings.qdrant_url))
                logger.info("qdrant ready")
            except Exception as e:  # pragma: no cover - optional service
                logger.warning("qdrant init failed", error=str(e))

    async def stream(self, question: str):
        """Async generator yielding answer tokens while logging each step."""

        # Raw query
        logger.info("raw query", query=question)
        normalized = textnorm.normalize_query(question)
        logger.info("normalized query", query=normalized)
        rewritten = await textnorm.rewrite_query(normalized)
        logger.info("rewritten query", query=rewritten)

        # Retrieve documents via prefilter and vector search
        docs_kw = []
        if hasattr(self.mongo, "search_documents"):
            try:
                func = getattr(self.mongo, "search_documents")
                docs_kw = await func(self.documents_collection, rewritten)
            except Exception as e:  # pragma: no cover - external service
                logger.warning("search_documents failed", error=str(e))

        vector_search = getattr(search, "vector_search", None)
        try:
            if vector_search is None:
                docs_vec = search.hybrid_search(rewritten)
            elif inspect.iscoroutinefunction(vector_search):
                docs_vec = await vector_search(rewritten)
            else:
                docs_vec = vector_search(rewritten)
        except Exception as e:  # pragma: no cover - external service
            logger.warning("vector search failed", error=str(e))
            docs_vec = []

        # RRF combination of results
        results = {}
        for rank, doc in enumerate(docs_vec, start=1):
            item = results.setdefault(
                doc.id, search.Doc(doc.id, getattr(doc, "payload", None))
            )
            item.score += 1 / (60 + rank)
        for rank, doc in enumerate(docs_kw, start=1):
            doc_id = getattr(doc, "id", None) or getattr(doc, "fileId", None)
            item = results.setdefault(doc_id, search.Doc(doc_id, getattr(doc, "payload", None)))
            item.score += 1 / (60 + rank)
        docs_combined = sorted(results.values(), key=lambda d: d.score, reverse=True)
        logger.info("documents found", ids=[d.id for d in docs_combined])

        prompt_text = prompt.build_prompt(question, docs_combined)

        # Stream model answer tokens
        answer = ""
        async for token in self.llm_client.generate(prompt_text):
            answer += token
            yield token
        logger.info("model answer", answer=answer)

    async def run(self, question: str) -> str:
        """Generate the full answer text with all steps logged."""

        tokens = []
        async for token in self.stream(question):
            tokens.append(token)
        return "".join(tokens)

llm_router = APIRouter(
    prefix="/llm",
    tags=["llm"],
    responses={
        200: {"description": "LLM response"},
        404: {"description": "Can't find specified sessionId"},
        500: {"description": "Internal Server Error"},
    },
)


@llm_router.post("/ask", response_class=ORJSONResponse, response_model=LLMResponse)
async def ask_llm(request: Request, llm_request: LLMRequest) -> ORJSONResponse:
    """Return a response from the language model for the given session.

    Parameters
    ----------
    request:
        Incoming request used to access application state.
    llm_request:
        Input payload specifying the ``session_id``.

    Returns
    -------
    ORJSONResponse
        JSON response containing the assistant reply under ``text``.
    """
    mongo_client = request.state.mongo
    logger.info("ask", session=str(llm_request.session_id))
    context = []

    try:
        preset = [
            {"role": message.role, "content": message.text}
            async for message in mongo_client.get_context_preset(
                request.state.context_presets_collection
            )
        ]
    except NotFound:
        raise HTTPException(status_code=404, detail="Preset not found")
    try:
        async for message in mongo_client.get_sessions(
            request.state.contexts_collection, str(llm_request.session_id)
        ):
            context.append({"role": str(message.role), "content": message.text})
    except NotFound:
        raise HTTPException(status_code=404, detail="Can't find specified sessionId")

    if context[-1]["role"] == RoleEnum.assistant:
        raise HTTPException(
            status_code=500, detail="Incorrect session state in database"
        )

    response = await request.state.llm.respond(context, preset)
    logger.info("llm answered", length=len(response[-1].text))

    return ORJSONResponse(LLMResponse(text=response[-1].text).model_dump())


@llm_router.get("/chat")
async def chat(request: Request, question: str) -> StreamingResponse:
    """Stream tokens from the language model with all steps logged."""

    pipeline = QueryLogger(request.state.mongo, llm_client)

    async def event_stream():
        async for token in pipeline.stream(question):
            yield f"data: {token}\n\n"
        logger.info("model answer", answer=answer)

    headers = {"X-Model-Name": get_settings().llm_model}
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)
  