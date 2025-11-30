"""Standalone FastAPI microservice for LLM inference.

This service loads the configured model once and exposes a minimal HTTP API:
  - GET /healthz: liveness probe
  - GET /chat?question=...: Server-Sent Events streaming tokens

The service is autonomous and does not require Mongo or Redis.
"""

from __future__ import annotations

import asyncio
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, ORJSONResponse
from pydantic import BaseModel
import structlog

from packages.backend import llm_client
from packages.backend.settings import settings


logger = structlog.get_logger(__name__)

def _parse_cors_origins(raw: str | list[str] | tuple[str, ...]) -> list[str]:
    if isinstance(raw, (list, tuple)):
        values = [str(item).strip() for item in raw if str(item).strip()]
    else:
        values = [item.strip() for item in str(raw or "").split(",") if item.strip()]
    return values or ["*"]


cors_origins = _parse_cors_origins(getattr(settings, "cors_origins", "*"))
allow_all_origins = "*" in cors_origins

app = FastAPI(title="LLM Model Service", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_API_KEY = os.environ.get("MODEL_API_KEY")


def _check_auth(request: Request) -> None:
    if not MODEL_API_KEY:
        return
    # Accept either Authorization: Bearer <key> or X-API-Key: <key>
    auth = request.headers.get("authorization") or ""
    xkey = request.headers.get("x-api-key") or ""
    token = ""
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
    elif xkey:
        token = xkey.strip()
    if token != MODEL_API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/chat")
async def chat(request: Request, question: str) -> StreamingResponse:
    """Stream tokens from the model using SSE."""
    _check_auth(request)
    logger.info("chat", question_len=len(question), model=settings.llm_model)

    async def event_stream():
        async for token in llm_client.generate(question):
            yield f"data: {token}\n\n"
            # Yield control to event loop
            await asyncio.sleep(0)

    headers = {"X-Model-Name": settings.llm_model}
    return StreamingResponse(
        event_stream(), media_type="text/event-stream", headers=headers
    )


class CompletionRequest(BaseModel):
    prompt: str
    stream: bool | None = False


@app.post("/v1/completions")
async def completions(request: Request, body: CompletionRequest):
    _check_auth(request)
    if body.stream:
        async def event_stream():
            async for token in llm_client.generate(body.prompt):
                yield f"data: {token}\n\n"
                await asyncio.sleep(0)
        return StreamingResponse(event_stream(), media_type="text/event-stream")
    # non-streaming: aggregate
    chunks: list[str] = []
    async for token in llm_client.generate(body.prompt):
        chunks.append(token)
        await asyncio.sleep(0)
    return ORJSONResponse({"text": "".join(chunks), "model": settings.llm_model})
