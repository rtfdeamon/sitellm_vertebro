"""FastAPI router with an endpoint for interacting with the LLM."""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import ORJSONResponse, StreamingResponse

import structlog

from backend import llm_client, prompt
from retrieval import search
import textnorm

from models import LLMResponse, LLMRequest, RoleEnum
from mongo import NotFound
from settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

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
    """Process the query through RAG pipeline and stream LLM answer with full logging."""

    logger.info("raw query", query=question)
    normalized_query = textnorm.normalize_query(question)
    logger.info("normalized query", query=normalized_query)
    rewritten_query = await textnorm.rewrite_query(normalized_query)
    logger.info("rewritten query", query=rewritten_query)

    docs_kw = await request.state.mongo.search_documents(
        settings.mongo.documents, rewritten_query
    )
    docs_vec = await search.vector_search(rewritten_query)

    results = {}
    for rank, doc in enumerate(docs_vec, start=1):
        item = results.setdefault(
            doc.id, search.Doc(doc.id, getattr(doc, "payload", None))
        )
        item.score += 1 / (60 + rank)
    for rank, doc in enumerate(docs_kw, start=1):
        item = results.setdefault(doc.fileId, search.Doc(doc.fileId, None))
        item.score += 1 / (60 + rank)

    docs_combined = sorted(results.values(), key=lambda d: d.score, reverse=True)
    doc_ids = [doc.id for doc in docs_combined]
    logger.info("documents found", ids=doc_ids)

    prompt_text = prompt.build_prompt(question, docs_combined)
    logger.debug("prompt built", length=len(prompt_text))

    async def event_stream():
        answer = ""
        async for token in llm_client.generate(prompt_text):
            answer += token
            yield f"data: {token}\n\n"
        logger.info("model answer", answer=answer)

    headers = {"X-Model-Name": settings.llm_model}
    return StreamingResponse(
        event_stream(), media_type="text/event-stream", headers=headers
    )
