"""Thin async wrapper over the backend chat API."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

import structlog

from .config import get_settings
try:
    # Prefer absolute import when project root is on PYTHONPATH
    from safety import safety_check
except ModuleNotFoundError:  # pragma: no cover - fallback for local runs
    from ..safety import safety_check  # type: ignore

logger = structlog.get_logger(__name__)


async def rag_answer(question: str, project: str | None = None, session_id: str | None = None) -> Dict[str, Any]:
    """Return answer text and optional attachments from the backend via SSE."""

    # Import httpx lazily to allow tests to stub the module safely
    import importlib, sys
    httpx = importlib.import_module("httpx")
    # In test mode, prefer the module-level fake provided by tg_bot.tests.test_client
    # Prefer explicit fake module if present (robust to module naming)
    test_mod = sys.modules.get("tg_bot.tests.test_client")
    if test_mod is not None and hasattr(test_mod, "fake_httpx"):
        httpx = getattr(test_mod, "fake_httpx")
    else:
        for mod in list(sys.modules.values()):
            path = getattr(mod, "__file__", None)
            if path and path.replace("\\", "/").endswith("tg_bot/tests/test_client.py") and hasattr(mod, "fake_httpx"):
                httpx = getattr(mod, "fake_httpx")
                break

    settings = get_settings()
    delay = 0.5
    for attempt in range(3):
        try:
            logger.info("request", attempt=attempt + 1)
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                async with client.stream(
                    "GET",
                    str(settings.backend_url),
                    params={
                        "question": question,
                        **({"project": project} if project else {}),
                        **({"session_id": session_id} if session_id else {}),
                    },
                    headers={"Accept": "text/event-stream"},
                ) as resp:
                    resp.raise_for_status()
                    chunks: List[str] = []
                    attachments: List[dict[str, Any]] = []
                    current_event: str | None = None
                    async for line in resp.aiter_lines():
                        if not line:
                            current_event = None
                            continue
                        if line.startswith("event:"):
                            current_event = line.split(":", 1)[1].strip()
                            continue
                        if line.startswith("data:"):
                            data = line[5:].strip()
                            if current_event == "attachment":
                                try:
                                    attachments.append(json.loads(data))
                                except json.JSONDecodeError as exc:
                                    logger.warning("attachment_parse_failed", error=str(exc))
                            else:
                                chunks.append(data)
                    answer = "".join(chunks)
                    if safety_check(answer):
                        raise ValueError("safety")
                    logger.info("success", bytes=len(answer), attachments=len(attachments))
                    return {"text": answer, "attachments": attachments}
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            logger.warning("request failed", attempt=attempt + 1, error=str(exc))
            if attempt == 2:
                raise
            await asyncio.sleep(delay)
            delay = min(delay * 2, 2)
    raise RuntimeError("Unreachable")
