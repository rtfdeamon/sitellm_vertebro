from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import ORJSONResponse

from models import LLMResponse, LLMRequest, RoleEnum
from mongo import NotFound

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
    mongo_client = request.state.mongo
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

    return ORJSONResponse(LLMResponse(text=response[-1].text).model_dump())
