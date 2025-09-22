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


async def rag_answer(
    question: str,
    project: str | None = None,
    session_id: str | None = None,
    debug: bool | None = None,
    *,
    channel: str = "telegram",
) -> Dict[str, Any]:
    """Return answer text and optional attachments from the backend via SSE.

    Parameters
    ----------
    debug:
        Optional toggle that forces debug streaming on (``True``) or off
        (``False``) regardless of the project configuration.
    """

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

    from urllib.parse import urlsplit, urlunsplit

    settings = get_settings()
    raw_url = str(settings.backend_url)
    target_url = raw_url.rstrip("/")
    if target_url.endswith("/llm/ask"):
        target_url = target_url[:-3] + "chat"

    parts = urlsplit(target_url)
    path = parts.path.rstrip("/")
    if path.endswith("/ask"):
        path = path[: -len("/ask")]
    if path.endswith("/chat"):
        path = path[: -len("/chat")]
    if "llm" not in [segment for segment in path.split("/") if segment]:
        path = path.rstrip("/") + "/llm"
    path = path.rstrip("/") + "/chat"
    target_url = urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))
    delay = 0.5
    for attempt in range(3):
        try:
            logger.info("request", attempt=attempt + 1, url=target_url)
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                async with client.stream(
                    "GET",
                    target_url,
                    params={
                        "question": question,
                        **({"project": project} if project else {}),
                        **({"session_id": session_id} if session_id else {}),
                        "channel": channel,
                        **({"debug": "1" if debug else "0"} if debug is not None else {}),
                    },
                    headers={"Accept": "text/event-stream"},
                ) as resp:
                    resp.raise_for_status()
                    chunks: List[str] = []
                    attachments: List[dict[str, Any]] = []
                    current_event: str | None = None
                    meta_info: Dict[str, Any] = {}
                    line_count = 0
                    async for line in resp.aiter_lines():
                        line_count += 1
                        if line_count <= 5:
                            logger.debug("sse_line", value=line)
                        if not line:
                            current_event = None
                            continue
                        if line.startswith("event:"):
                            current_event = line.split(":", 1)[1].strip()
                            continue
                        if line.startswith("data:"):
                            payload = line[5:]
                            if payload.startswith(" "):
                                payload = payload[1:]
                            payload = payload.rstrip("\r")
                            if current_event == "attachment":
                                try:
                                    attachments.append(json.loads(payload.strip()))
                                except json.JSONDecodeError as exc:
                                    logger.warning("attachment_parse_failed", error=str(exc))
                            elif current_event == "meta":
                                try:
                                    meta_info.update(json.loads(payload.strip()))
                                except json.JSONDecodeError as exc:
                                    logger.warning("meta_parse_failed", error=str(exc), value=payload)
                            elif current_event == "debug":
                                try:
                                    debug_events = meta_info.setdefault("debug", [])
                                    if isinstance(debug_events, list):
                                        debug_events.append(json.loads(payload.strip()))
                                except json.JSONDecodeError as exc:
                                    logger.warning("debug_parse_failed", error=str(exc), value=payload)
                            elif current_event in ("end", "llm_error"):
                                continue
                            else:
                                chunks.append(payload)
                    char_count = sum(len(c) for c in chunks)
                    logger.info(
                        "sse_completed",
                        lines=line_count,
                        chars=char_count,
                        attachments=len(attachments),
                        emotions=meta_info.get("emotions_enabled"),
                    )
                    answer = "".join(chunks)
                    if safety_check(answer):
                        raise ValueError("safety")
                    logger.info("success", bytes=len(answer), attachments=len(attachments))
                    meta_payload = {
                        "lines": line_count,
                        "chars": char_count,
                    }
                    meta_payload.update(meta_info)
                    return {
                        "text": answer,
                        "attachments": attachments,
                        "meta": meta_payload,
                    }
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            logger.warning("request failed", attempt=attempt + 1, error=str(exc))
            if attempt == 2:
                raise
            await asyncio.sleep(delay)
            delay = min(delay * 2, 2)
    raise RuntimeError("Unreachable")
