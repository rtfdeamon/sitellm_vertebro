"""FastAPI router with an endpoint for interacting with the LLM."""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import ORJSONResponse, StreamingResponse

import structlog

from backend import llm_client

from models import LLMResponse, LLMRequest, RoleEnum
from mongo import NotFound

logger = structlog.get_logger(__name__)

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

    if not context:
        raise HTTPException(status_code=400, detail="No conversation history provided")

    if context[-1]["role"] == RoleEnum.assistant:
        raise HTTPException(
            status_code=400, detail="Last message role cannot be assistant"
        )

    response = await request.state.llm.respond(context, preset)
    logger.info("llm answered", length=len(response[-1].text))

    return ORJSONResponse(LLMResponse(text=response[-1].text).model_dump())


@llm_router.get("/chat")
async def chat(question: str) -> StreamingResponse:
    """Stream tokens from the language model using server-sent events.

    Parameters
    ----------
    question:
        Text sent as a query parameter. Example: ``/chat?question=hi``.
    """

    logger.info("chat", question=question)

    async def event_stream():
        async for token in llm_client.generate(question):
            yield f"data: {token}\n\n"

    headers = {"X-Model-Name": "vikhr-gpt-8b-it"}
    response = StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)
    return response
