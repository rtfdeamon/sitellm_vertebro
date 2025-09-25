"""FastAPI routers for interacting with the LLM and crawler."""

from __future__ import annotations

import json
from pathlib import Path
import copy
import subprocess
import sys
import os
import signal
import time
import re
import urllib.parse as urlparse
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
try:
    from fastapi import BackgroundTasks
except ImportError:  # pragma: no cover - fallback for test stubs
    class BackgroundTasks:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass
from fastapi.responses import ORJSONResponse, StreamingResponse
from starlette.routing import NoMatchFound
import asyncio

import redis.asyncio as redis

import structlog

from backend import llm_client
from backend.settings import settings as backend_settings
from backend.ollama import (
    list_installed_models,
    ollama_available,
    popular_models_with_size,
)
from retrieval import search as retrieval_search
from crawler.run_crawl import (
    clear_crawler_state,
    deduplicate_recent_urls,
    get_crawler_note,
)

from models import Document, LLMResponse, LLMRequest, RoleEnum, Project, Attachment
from mongo import NotFound
from pydantic import BaseModel

from core.status import status_dict
from settings import MongoSettings, get_settings as get_app_settings
from core.build import get_build_info

logger = structlog.get_logger(__name__)
app_settings = get_app_settings()

EMOTION_ON_PROMPT = (
    "Отвечай в тёплом, дружелюбном тоне, добавляй уместные эмоции и подходящие эмодзи (не более двух в ответе),"
    " чтобы поддерживать живой диалог и эмпатию."
)
EMOTION_OFF_PROMPT = (
    "Отвечай в спокойном, нейтральном тоне и не используй эмодзи либо эмоциональные высказывания."
)


def _normalize_project(value: str | None) -> str | None:
    candidate = (value or "").strip().lower()
    if candidate:
        return candidate
    fallback = backend_settings.project_name or backend_settings.domain
    if fallback:
        return fallback.strip().lower() or None
    return None


def _resolve_session_identifiers(
    request: Request,
    project: str | None,
    session_id: str | None,
) -> tuple[str | None, str, str, bool]:
    """Return normalized project, composite session key and base id."""

    project_name = _normalize_project(project)
    candidates = (
        session_id,
        request.headers.get("X-Session-Id"),
        request.headers.get("X-Client-Session"),
        request.cookies.get("chat_session"),
    )
    base_id: str | None = None
    for candidate in candidates:
        if isinstance(candidate, str):
            trimmed = candidate.strip().lower()
            if trimmed:
                base_id = trimmed
                break
    generated = False
    if not base_id:
        base_id = uuid4().hex
        generated = True
    session_key = f"{project_name}::{base_id}" if project_name else base_id
    return project_name, session_key, base_id, generated


_KNOWLEDGE_SNIPPET_CHARS = 640
_MAX_DIALOG_TURNS = 5
_ATTACHMENT_PENDING_TTL = 10 * 60  # seconds
_ATTACHMENT_CONSENT_SIMPLE = {
    "да",
    "давай",
    "ок",
    "окей",
    "хочу",
    "угу",
    "ага",
    "yes",
    "y",
}
_ATTACHMENT_CONSENT_KEYWORDS = {
    "отправь",
    "пришли",
    "скинь",
    "присылай",
    "загрузи",
    "покажи",
}
_ATTACHMENT_NEGATIONS = {
    "нет",
    "не",
    "ненадо",
    "no",
    "неа",
}


def _log_debug_event(message: str, **kwargs) -> None:
    if app_settings.debug:
        logger.info(message, **kwargs)
    else:
        logger.debug(message, **kwargs)


def _truncate_text(text: str, limit: int = _KNOWLEDGE_SNIPPET_CHARS) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    truncated = cleaned[:limit].rsplit(" ", 1)[0].strip()
    if not truncated:
        truncated = cleaned[:limit]
    return truncated.rstrip(". ") + "…"


def _extract_payload_text(payload: Any) -> str:
    if not payload:
        return ""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        for key in ("text", "content", "body", "chunk"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
        meta = payload.get("metadata")
        if isinstance(meta, dict):
            return _extract_payload_text(meta)
    return ""


def _normalize_consent_text(value: str) -> str:
    normalized = re.sub(r"[^0-9a-zа-яё\s]+", " ", value.strip().lower())
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _detect_attachment_consent(text: str) -> bool:
    normalized = _normalize_consent_text(text)
    if not normalized or len(normalized) > 120:
        return False
    tokens = normalized.split()
    if not tokens:
        return False
    if any(token in _ATTACHMENT_NEGATIONS for token in tokens):
        return False
    if normalized in _ATTACHMENT_CONSENT_SIMPLE:
        return True
    if normalized.startswith("да ") and len(tokens) <= 4:
        return True
    for keyword in _ATTACHMENT_CONSENT_KEYWORDS:
        if keyword in normalized:
            return True
    return False


def _ensure_attachment_store(app) -> tuple[dict[str, Any], asyncio.Lock]:
    store = getattr(app.state, "pending_attachments", None)
    lock = getattr(app.state, "pending_attachments_lock", None)
    if store is None or lock is None:
        store = {}
        lock = asyncio.Lock()
        app.state.pending_attachments = store
        app.state.pending_attachments_lock = lock
    return store, lock


async def _prune_pending_attachments(app, now: float) -> None:
    store, lock = _ensure_attachment_store(app)
    async with lock:
        expired_keys = [
            key
            for key, payload in store.items()
            if now - float(payload.get("ts", 0.0) or 0.0) > _ATTACHMENT_PENDING_TTL
        ]
        for key in expired_keys:
            store.pop(key, None)


async def _set_pending_attachments(
    app,
    session_key: str | None,
    attachments: list[dict[str, Any]],
    snippets: list[dict[str, Any]],
    now: float,
) -> None:
    if not session_key:
        return
    store, lock = _ensure_attachment_store(app)
    async with lock:
        if attachments:
            store[session_key] = {
                "attachments": copy.deepcopy(attachments),
                "snippets": copy.deepcopy(snippets),
                "ts": now,
            }
        else:
            store.pop(session_key, None)


async def _pop_pending_attachments(app, session_key: str | None) -> dict[str, Any] | None:
    if not session_key:
        return None
    store, lock = _ensure_attachment_store(app)
    async with lock:
        return store.pop(session_key, None)


def _extract_payload_name(payload: Any, default: str | None = None) -> str | None:
    if isinstance(payload, dict):
        for key in ("title", "name", "source", "document", "file_name"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        url = payload.get("url")
        if isinstance(url, str) and url.strip():
            return url.strip()
    return default


def _extract_payload_url(payload: Any) -> str | None:
    if isinstance(payload, dict):
        url = payload.get("url")
        if isinstance(url, str) and url.strip():
            return url.strip()
    return None


def _is_attachment_doc(meta: dict[str, Any]) -> bool:
    content_type = str(meta.get("content_type") or "").lower()
    if not content_type:
        return False
    return not content_type.startswith("text/")


def _build_download_url(request: Request, file_id: str) -> str:
    try:
        return str(request.url_for("admin_download_document", file_id=file_id))
    except NoMatchFound:
        base = str(request.base_url).rstrip("/")
        return f"{base}/api/v1/admin/knowledge/documents/{file_id}"


def _collect_attachments(snippets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    attachments: list[dict[str, Any]] = []
    for item in snippets:
        att = item.get("attachment")
        if not att:
            continue
        key = att.get("url") or att.get("name")
        if not key or key in seen:
            continue
        seen.add(key)
        attachments.append(att)
    return attachments


async def _collect_knowledge_snippets(
    request: Request,
    question: str,
    project: str | None,
    *,
    limit: int = 6,
) -> list[dict[str, Any]]:
    question = (question or "").strip()
    if not question:
        return []

    snippets: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    try:
        docs = await asyncio.to_thread(retrieval_search.hybrid_search, question, limit * 3)
    except Exception as exc:  # noqa: BLE001
        logger.debug("knowledge_hybrid_failed", error=str(exc))
        docs = []

    for doc in docs:
        payload = getattr(doc, "payload", None)
        text = _extract_payload_text(payload)
        if not text:
            continue
        doc_id = str(getattr(doc, "id", "")) or None
        if doc_id and doc_id in seen_ids:
            continue
        snippets.append(
            {
                "id": doc_id,
                "name": _extract_payload_name(payload, default=doc_id),
                "text": text,
                "score": getattr(doc, "score", None),
                "url": _extract_payload_url(payload),
                "source": "qdrant",
            }
        )
        if doc_id:
            seen_ids.add(doc_id)
        if len(snippets) >= limit:
            break

    if len(snippets) >= limit:
        return snippets[:limit]

    mongo_client = getattr(request.state, "mongo", None)
    if not mongo_client or not hasattr(mongo_client, "search_documents"):
        return snippets[:limit]

    mongo_cfg = MongoSettings()
    collection = getattr(request.state, "documents_collection", mongo_cfg.documents)

    try:
        candidates = await mongo_client.search_documents(
            collection, question, project=project
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("knowledge_mongo_search_failed", error=str(exc))
        candidates = []

    if not candidates:
        try:
            query: dict[str, Any] = {}
            if project:
                query["project"] = project
            cursor = (
                mongo_client.db[collection]
                .find(query, {"_id": False})
                .sort("ts", -1)
                .limit(limit * 3)
            )
            candidates = [Document(**doc) async for doc in cursor]
        except Exception as exc:  # noqa: BLE001
            logger.debug("knowledge_mongo_fallback_failed", error=str(exc))
            candidates = []

    for doc in candidates:
        if len(snippets) >= limit:
            break
        file_id = getattr(doc, "fileId", None)
        if file_id and file_id in seen_ids:
            continue
        attachment_meta: dict[str, Any] | None = None
        doc_meta = doc.model_dump()
        text = ""
        doc_url = doc.url
        try:
            if file_id and _is_attachment_doc(doc_meta):
                text = doc.description or ""
            else:
                _meta, payload = await mongo_client.get_document_with_content(
                    collection, doc.fileId
                )
                text = payload.decode("utf-8", errors="ignore")
                if not doc_url:
                    doc_url = _meta.get("url")
        except Exception as exc:  # noqa: BLE001
            logger.debug("knowledge_content_fetch_failed", file_id=file_id, error=str(exc))
            text = doc.description or ""

        if file_id and _is_attachment_doc(doc_meta):
            download_url = _build_download_url(request, file_id)
            doc_url = doc_url or download_url
            attachment_meta = {
                "name": doc.name or file_id,
                "url": doc_url,
                "content_type": doc.content_type,
                "file_id": file_id,
            }
            if doc.description:
                attachment_meta["description"] = doc.description
            if doc.size_bytes is not None:
                attachment_meta["size_bytes"] = int(doc.size_bytes)
            if not text.strip():
                text = doc.description or ""

        if not text.strip() and not attachment_meta:
            continue

        item = {
            "id": file_id,
            "name": doc.name,
            "text": text,
            "score": getattr(doc, "ts", None),
            "url": doc_url,
            "source": "mongo",
        }
        if attachment_meta:
            item["attachment"] = attachment_meta
        snippets.append(item)
        if file_id:
            seen_ids.add(file_id)

    return snippets[:limit]


def _compose_knowledge_message(snippets: list[dict[str, Any]]) -> str:
    if not snippets:
        return ""
    blocks: list[str] = []
    has_attachments = any(bool(item.get("attachment")) for item in snippets)
    for idx, item in enumerate(snippets, 1):
        name = item.get("name") or f"Источник {idx}"
        snippet_text = _truncate_text(item.get("text", ""))
        attachment = item.get("attachment")
        url = item.get("url")
        if attachment:
            attachment_url = attachment.get("url") or url
            attachment_name = attachment.get("name") or name
            attachment_line = f"Документ: {attachment_name} ({attachment_url})" if attachment_url else f"Документ: {attachment_name}"
            if snippet_text:
                snippet_text = f"{snippet_text}\n{attachment_line}"
            else:
                snippet_text = attachment_line
            url = attachment_url or url
        footer = f"\nИсточник: {url}" if url and url not in snippet_text else ""
        blocks.append(f"Источник {idx} ({name}):\n{snippet_text}{footer}")
    prefix = [
        "Тебе доступны выдержки из базы знаний. Сначала проанализируй их, выдели ключевые факты и противоречия,",
        "затем дай итоговый ответ, ссылаясь на несколько источников, если это повышает точность.",
    ]
    if has_attachments:
        prefix.append(
            "Если посчитаешь нужным отправить документ, кратко опиши его, спроси подтверждение и жди явного согласия"
            " (например: 'да', 'пришли', 'отправь'). Не отправляй файлы без подтверждения пользователя."
        )
    header = " ".join(prefix)
    return header + "\n\n" + "\n\n".join(blocks)


def _limit_dialog_history(messages: list[dict[str, Any]], max_turns: int = _MAX_DIALOG_TURNS) -> list[dict[str, Any]]:
    """Return ``messages`` trimmed to the last ``max_turns`` user requests."""

    if max_turns <= 0 or len(messages) <= 2 * max_turns:
        return messages

    kept: list[dict[str, Any]] = []
    user_seen = 0

    for msg in reversed(messages):
        role = str(msg.get("role", "")).lower()
        if role == RoleEnum.user.value:
            user_seen += 1
        kept.append(msg)
        if user_seen >= max_turns:
            break

    return list(reversed(kept))


llm_router = APIRouter(
    prefix="/llm",
    tags=["llm"],
    responses={
        200: {"description": "LLM response"},
        404: {"description": "Can't find specified sessionId"},
        500: {"description": "Internal Server Error"},
    },
)

crawler_router = APIRouter(
    prefix="/crawler",
    tags=["crawler"],
)


@llm_router.post("/ask", response_class=ORJSONResponse, response_model=LLMResponse)
async def ask_llm(request: Request, llm_request: LLMRequest) -> ORJSONResponse:
    """Return a response from the language model for the given session.

    Parameters
    ----------
    request:
        Incoming request used to access application state.
    llm_request:
        Input payload specifying the ``session_id`` and optional project slug.

    Raises
    ------
    HTTPException
        If the session or preset cannot be found or if generation fails.
    """

    try:
        mongo_client = request.state.mongo
    except Exception as exc:
        logger.error("mongo_client_missing", error=str(exc))
        raise HTTPException(status_code=500, detail="Mongo client unavailable") from exc
    project_name = _normalize_project(llm_request.project)
    project: Project | None = None
    if project_name:
        try:
            project = await request.state.mongo.get_project(project_name)
            if project is None:
                project = await request.state.mongo.upsert_project(Project(name=project_name))
        except Exception as exc:
            logger.error("project_resolve_failed", project=project_name, error=str(exc))
            raise HTTPException(status_code=500, detail="Failed to resolve project") from exc
    emotions_enabled = True
    if project and project.llm_emotions_enabled is not None:
        emotions_enabled = bool(project.llm_emotions_enabled)

    logger.info(
        "ask",
        session=str(llm_request.session_id),
        project=project_name,
        emotions=emotions_enabled,
    )
    context = []

    try:
        preset = [
            {"role": message.role, "content": message.text}
            async for message in mongo_client.get_context_preset(
                request.state.context_presets_collection
            )
        ]
    except NotFound:
        logger.warning("preset_not_found", session=str(llm_request.session_id))
        raise HTTPException(status_code=404, detail="Preset not found")
    except Exception as exc:
        logger.error("preset_load_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to load preset") from exc
    try:
        async for message in mongo_client.get_sessions(
            request.state.contexts_collection, str(llm_request.session_id)
        ):
            context.append({"role": str(message.role), "content": message.text})
    except NotFound:
        logger.warning("session_not_found", session=str(llm_request.session_id))
        raise HTTPException(status_code=404, detail="Can't find specified sessionId")
    except Exception as exc:
        logger.error("session_load_failed", session=str(llm_request.session_id), error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to load session history") from exc

    if not context:
        raise HTTPException(status_code=400, detail="No conversation history provided")

    context = _limit_dialog_history(context)

    if context[-1]["role"] == RoleEnum.assistant:
        logger.error(
            "incorrect session state", session=str(llm_request.session_id)
        )
        raise HTTPException(
            status_code=400, detail="Last message role cannot be assistant"
        )

    knowledge_snippets: list[dict[str, Any]] = []
    attachments_payload: list[dict[str, Any]] = []
    knowledge_message = ""
    try:
        question_text = context[-1].get("content", "")
        knowledge_snippets = await _collect_knowledge_snippets(
            request, question_text, project_name
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "knowledge_lookup_failed",
            session=str(llm_request.session_id),
            project=project_name,
            error=str(exc),
        )
    else:
        knowledge_message = _compose_knowledge_message(knowledge_snippets)
        attachments_payload = _collect_attachments(knowledge_snippets)
        if knowledge_message:
            preset = preset + [{"role": "system", "content": knowledge_message}]
            _log_debug_event(
                "knowledge_context_attached",
                session=str(llm_request.session_id),
                project=project_name,
                docs=[
                    {
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "source": item.get("source"),
                        "url": item.get("url"),
                        "chars": len(item.get("text", "")),
                        "score": item.get("score"),
                    }
                    for item in knowledge_snippets
                ],
            )

    system_messages: list[dict[str, str]] = []
    if project and project.llm_prompt:
        prompt_text = project.llm_prompt.strip()
        if prompt_text:
            system_messages.append({"role": "system", "content": prompt_text})
            _log_debug_event(
                "project_prompt_attached",
                session=str(llm_request.session_id),
                project=project_name,
                prompt_length=len(prompt_text),
            )

    emotion_instruction = EMOTION_ON_PROMPT if emotions_enabled else EMOTION_OFF_PROMPT
    system_messages.append({"role": "system", "content": emotion_instruction})

    if system_messages:
        preset = system_messages + preset

    # Build a prompt similar to the HTTPModelClient/YaLLM formatting
    prompt_parts: list[str] = []
    for m in preset + context:
        role = m.get("role", "user")
        text = m.get("content", "")
        prompt_parts.append(f"{role}: {text}")
    prompt = "\n".join(prompt_parts)

    knowledge_log = [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "source": item.get("source"),
            "chars": len(item.get("text", "")),
            "url": item.get("url"),
        }
        for item in knowledge_snippets
    ]
    _log_debug_event(
        "llm_prompt_compiled",
        session=str(llm_request.session_id),
        project=project_name,
        emotions=emotions_enabled,
        prompt_preview=prompt[:500],
        prompt_length=len(prompt),
        knowledge=knowledge_log,
    )

    chunks: list[str] = []
    model_override = None
    if project and project.llm_model:
        trimmed_model = project.llm_model.strip()
        if trimmed_model:
            model_override = trimmed_model
    try:
        async for token in llm_client.generate(prompt, model=model_override):
            chunks.append(token)
    except Exception as exc:
        logger.error("llm_generate_failed", project=project_name, error=str(exc))
        raise HTTPException(status_code=500, detail="LLM generation failed") from exc
    text = "".join(chunks)
    logger.info("llm answered", length=len(text), emotions=emotions_enabled)

    response_payload = LLMResponse(
        text=text,
        attachments=[Attachment(**att) for att in attachments_payload],
        emotions_enabled=emotions_enabled,
    )
    await request.state.mongo.log_request_stat(
        project=project_name,
        question=context[-1].get("content", "") if context else None,
        response_chars=len(text),
        attachments=len(attachments_payload),
        prompt_chars=len(prompt),
        channel="api",
        session_id=str(llm_request.session_id),
        user_id=None,
        error=None,
    )
    return ORJSONResponse(response_payload.model_dump())


@llm_router.get("/chat")
async def chat(
    request: Request,
    question: str,
    project: str | None = None,
    channel: str | None = None,
    debug: bool | None = None,
    session_id: str | None = None,
    model: str | None = None,
) -> StreamingResponse:
    """Stream tokens from the language model using server-sent events.

    Parameters
    ----------
    question:
        Text sent as a query parameter. Example: ``/chat?question=hi``.
    """

    project_name, session_key, session_base, session_generated = _resolve_session_identifiers(
        request,
        project,
        session_id,
    )
    channel_name = (channel or "widget").strip() or "widget"
    project_obj: Project | None = None
    if project_name:
        project_obj = await request.state.mongo.get_project(project_name)
        if project_obj is None:
            project_obj = await request.state.mongo.upsert_project(Project(name=project_name))

    emotions_enabled = True
    if project_obj and project_obj.llm_emotions_enabled is not None:
        emotions_enabled = bool(project_obj.llm_emotions_enabled)

    request_debug_enabled = bool(debug) if debug is not None else False
    project_debug_enabled = bool(project_obj.debug_enabled) if project_obj and project_obj.debug_enabled is not None else False
    send_debug = request_debug_enabled or project_debug_enabled
    if send_debug:
        if request_debug_enabled and project_debug_enabled:
            debug_origin = "project+request"
        elif request_debug_enabled:
            debug_origin = "request"
        else:
            debug_origin = "project"
    else:
        debug_origin = None

    prompt_base = question
    if project_obj and project_obj.llm_prompt:
        prompt_text = project_obj.llm_prompt.strip()
        if prompt_text:
            prompt_base = f"{prompt_text}\n\n{question}"
            logger.info(
                "project_prompt_attached",
                project=project_name,
                prompt_length=len(prompt_text),
                mode="stream",
            )
    requested_model = model.strip() if isinstance(model, str) and model.strip() else None
    base_model_override = None
    if project_obj and project_obj.llm_model:
        model_text = project_obj.llm_model.strip()
        if model_text:
            base_model_override = model_text

    voice_model_override = None
    if project_obj and project_obj.llm_voice_model:
        voice_model_text = project_obj.llm_voice_model.strip()
        if voice_model_text:
            voice_model_override = voice_model_text

    voice_enabled = True
    if project_obj and project_obj.llm_voice_enabled is not None:
        voice_enabled = bool(project_obj.llm_voice_enabled)

    selected_model_override = base_model_override
    if channel_name.lower() == "voice-avatar":
        if not voice_enabled:
            logger.warning(
                "voice_channel_disabled",
                project=project_name,
                session=session_key,
                channel=channel_name,
            )
            raise HTTPException(status_code=403, detail="voice_mode_disabled")
        if voice_model_override:
            selected_model_override = voice_model_override

    if requested_model:
        selected_model_override = requested_model

    model_override = selected_model_override
    effective_model = model_override or getattr(llm_client, "MODEL_NAME", "unknown")

    if app_settings.debug:
        logger.info(
            "chat",
            question=question,
            project=project_name,
            emotions=emotions_enabled,
            session=session_key,
            debug=send_debug,
            channel=channel_name,
        )
    else:
        logger.info(
            "chat",
            question_chars=len(question or ""),
            project=project_name,
            emotions=emotions_enabled,
            session=session_key,
            debug=send_debug,
            channel=channel_name,
        )

    now_ts = time.time()
    await _prune_pending_attachments(request.app, now_ts)

    knowledge_snippets: list[dict[str, Any]] = []
    attachments_payload: list[dict[str, Any]] = []
    planned_attachments_count = 0
    pending_consumed = False

    if session_key and _detect_attachment_consent(question):
        stored_entry = await _pop_pending_attachments(request.app, session_key)
        attachments_from_store = (stored_entry or {}).get("attachments") or []
        if attachments_from_store:
            attachments_payload = attachments_from_store
            knowledge_snippets = (stored_entry or {}).get("snippets") or []
            planned_attachments_count = len(attachments_payload)
            pending_consumed = True

    if not knowledge_snippets:
        try:
            knowledge_snippets = await _collect_knowledge_snippets(
                request, question, project_name
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "knowledge_lookup_failed",
                project=project_name,
                error=str(exc),
                mode="stream",
            )
        else:
            attachments_to_queue = _collect_attachments(knowledge_snippets)
            if pending_consumed:
                # Attachments already confirmed for delivery; do not overwrite payload
                planned_attachments_count = len(attachments_payload)
            else:
                planned_attachments_count = len(attachments_to_queue)
                await _set_pending_attachments(
                    request.app,
                    session_key,
                    attachments_to_queue,
                    knowledge_snippets,
                    now_ts,
                )
                attachments_payload = []  # wait for explicit confirmation

    knowledge_message = _compose_knowledge_message(knowledge_snippets)
    if knowledge_message:
        _log_debug_event(
            "knowledge_context_attached",
            project=project_name,
            mode="stream",
            session=session_key,
            debug=send_debug,
            docs=[
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "source": item.get("source"),
                    "url": item.get("url"),
                    "chars": len(item.get("text", "")),
                    "score": item.get("score"),
                }
                for item in knowledge_snippets
            ],
        )

    emotion_instruction = EMOTION_ON_PROMPT if emotions_enabled else EMOTION_OFF_PROMPT
    prompt_segments = [emotion_instruction]
    if knowledge_message:
        prompt_segments.append(knowledge_message)
    prompt_segments.append(f"Вопрос: {prompt_base}")
    prompt_segments.append("Ответ:")
    prompt_base = "\n\n".join(segment for segment in prompt_segments if segment)

    knowledge_log_stream = [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "source": item.get("source"),
            "chars": len(item.get("text", "")),
            "url": item.get("url"),
        }
        for item in knowledge_snippets
    ]
    knowledge_source_counts: dict[str, int] = {}
    total_knowledge_chars = 0
    for item in knowledge_snippets:
        source_label = str(item.get("source") or "unknown").lower()
        knowledge_source_counts[source_label] = knowledge_source_counts.get(source_label, 0) + 1
        total_knowledge_chars += len(item.get("text", ""))

    knowledge_preview = [
        {
            "id": entry.get("id"),
            "name": entry.get("name"),
            "source": entry.get("source"),
            "score": entry.get("score"),
            "url": entry.get("url"),
        }
        for entry in knowledge_snippets[:3]
    ]
    _log_debug_event(
        "llm_prompt_compiled_stream",
        project=project_name,
        emotions=emotions_enabled,
        prompt_preview=prompt_base[:500],
        prompt_length=len(prompt_base),
        knowledge=knowledge_log_stream,
        session=session_key,
        debug=send_debug,
    )

    stream_chars = 0
    error_message: str | None = None

    async def event_stream():
        nonlocal stream_chars, error_message
        build_info = get_build_info()
        build_payload = {
            key: build_info.get(key)
            for key in ("version", "revision", "built_at", "built_at_iso")
            if build_info.get(key) is not None
        }
        components = build_info.get("components")
        if components:
            build_payload["components"] = components
        try:
            meta_payload = {
                "emotions_enabled": emotions_enabled,
                "session_id": session_key,
                "debug_enabled": send_debug,
                "debug_origin": debug_origin,
                "attachments_pending": planned_attachments_count,
                "model": effective_model,
            }
            if build_payload:
                meta_payload["build"] = build_payload
            yield "event: meta\n"
            yield f"data: {json.dumps(meta_payload, ensure_ascii=False)}\n\n"
            if send_debug:
                debug_start_payload = {
                    "stage": "begin",
                    "session_id": session_key,
                    "project": project_name,
                    "channel": channel_name,
                    "question_preview": question[:160],
                    "question_chars": len(question or ""),
                    "prompt_chars": len(prompt_base),
                    "knowledge_count": len(knowledge_snippets),
                    "knowledge_sources": knowledge_source_counts,
                    "knowledge_preview": knowledge_preview,
                    "attachments_planned": planned_attachments_count,
                    "emotions_enabled": emotions_enabled,
                    "model": effective_model,
                    "debug_origin": debug_origin,
                    "total_knowledge_chars": total_knowledge_chars,
                    "ts": time.time(),
                }
                if build_payload:
                    debug_start_payload["build"] = build_payload
                yield "event: debug\n"
                yield f"data: {json.dumps(debug_start_payload, ensure_ascii=False)}\n\n"
            if attachments_payload:
                for att in attachments_payload:
                    yield "event: attachment\n"
                    yield f"data: {json.dumps(att, ensure_ascii=False)}\n\n"
            async for token in llm_client.generate(prompt_base, model=model_override):
                stream_chars += len(token)
                payload = {
                    "text": token,
                    "role": "assistant",
                    "meta": {},
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as exc:  # keep connection graceful for the widget
            logger.warning("sse_generate_failed", error=str(exc))
            error_message = str(exc)
            yield "event: llm_error\ndata: generation_failed\n\n"
        finally:
            if send_debug:
                debug_summary_payload = {
                    "stage": "end",
                    "session_id": session_key,
                    "project": project_name,
                    "channel": channel_name,
                    "response_chars": stream_chars,
                    "attachments": len(attachments_payload),
                    "error": error_message,
                    "knowledge_count": len(knowledge_snippets),
                    "knowledge_sources": knowledge_source_counts,
                    "total_knowledge_chars": total_knowledge_chars,
                    "model": effective_model,
                    "emotions_enabled": emotions_enabled,
                    "ts": time.time(),
                }
                if build_payload:
                    debug_summary_payload["build"] = build_payload
                yield "event: debug\n"
                yield f"data: {json.dumps(debug_summary_payload, ensure_ascii=False)}\n\n"
            # Signal the client that stream has completed
            yield "event: end\ndata: [DONE]\n\n"
            await request.state.mongo.log_request_stat(
                project=project_name,
                question=question,
                response_chars=stream_chars,
                attachments=len(attachments_payload),
                prompt_chars=len(prompt_base),
                channel=channel_name,
                session_id=session_key,
                user_id=None,
                error=error_message,
            )

    model_header = effective_model
    headers = {"X-Model-Name": model_header}
    response = StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)
    if session_generated:
        response.set_cookie(
            "chat_session",
            session_base,
            max_age=30 * 24 * 3600,
            httponly=False,
            samesite="Lax",
        )
    return response


@llm_router.get("/project-config", response_class=ORJSONResponse)
async def project_config(request: Request, project: str | None = None) -> ORJSONResponse:
    """Expose limited project configuration for public widget usage."""

    mongo_client = getattr(request.state, "mongo", None)
    if mongo_client is None:
        mongo_client = getattr(request.app.state, "mongo", None)
    if mongo_client is None:
        raise HTTPException(status_code=503, detail="mongo_unavailable")

    normalized = _normalize_project(project)
    if not normalized:
        normalized = _normalize_project(backend_settings.project_name)

    project_obj: Project | None = None
    if normalized:
        project_obj = await mongo_client.get_project(normalized)
        if project_obj is None:
            logger.info("project_config_missing", project=normalized)

    if project_obj is None and normalized:
        # create placeholder to keep defaults if project not stored yet
        project_obj = Project(name=normalized)

    voice_enabled = True
    voice_model = None
    llm_model = getattr(llm_client, "MODEL_NAME", None)
    title = None

    if project_obj:
        title = project_obj.title
        if project_obj.llm_model:
            llm_model = project_obj.llm_model
        if project_obj.llm_voice_enabled is not None:
            voice_enabled = bool(project_obj.llm_voice_enabled)
        if project_obj.llm_voice_model:
            voice_model = project_obj.llm_voice_model

    payload = {
        "project": normalized,
        "title": title,
        "llm_model": llm_model,
        "llm_voice_enabled": voice_enabled,
        "llm_voice_model": voice_model,
    }
    return ORJSONResponse(payload)


class CrawlRequest(BaseModel):
    start_url: str
    max_pages: int = 500
    max_depth: int = 3
    project: str | None = None
    domain: str | None = None


crawler_router = APIRouter(prefix="/crawler", tags=["crawler"])


def _spawn_crawler(
    start_url: str,
    max_pages: int,
    max_depth: int,
    *,
    project: str | None,
    domain: str | None,
    mongo_uri: str | None,
) -> None:
    base_dir = Path(__file__).resolve().parent
    script = base_dir / "crawler" / "run_crawl.py"
    cmd = [
        sys.executable,
        str(script),
        "--url",
        start_url,
        "--max-pages",
        str(max_pages),
        "--max-depth",
        str(max_depth),
    ]
    if project:
        cmd.extend(["--project", project])
    if domain:
        cmd.extend(["--domain", domain])
    if mongo_uri:
        cmd.extend(["--mongo-uri", mongo_uri])
    env = os.environ.copy()
    python_paths = [str(base_dir)]
    existing_py_path = env.get("PYTHONPATH")
    if existing_py_path:
        python_paths.append(existing_py_path)
    env["PYTHONPATH"] = os.pathsep.join(python_paths)
    proc = subprocess.Popen(cmd, cwd=str(base_dir), env=env)
    try:
        (Path("/tmp") / "crawler.pid").write_text(str(proc.pid), encoding="utf-8")
    except Exception:
        pass


@crawler_router.post("/run", status_code=202)
async def run_crawler(
    req: CrawlRequest, background_tasks: BackgroundTasks, request: Request
) -> dict[str, str]:
    """Start the crawler in a background task."""

    parsed_host = urlparse.urlsplit(req.start_url).netloc
    allowed_domain = (req.domain or parsed_host or "").lower()
    project_name = _normalize_project(req.project) or _normalize_project(allowed_domain)
    if not project_name:
        raise HTTPException(status_code=400, detail="project is required")

    project = await request.state.mongo.get_project(project_name)
    if project is None:
        project = await request.state.mongo.upsert_project(
            Project(name=project_name, domain=allowed_domain or None)
        )

    background_tasks.add_task(
        _spawn_crawler,
        req.start_url,
        req.max_pages,
        req.max_depth,
        project=project_name,
        domain=allowed_domain or None,
        mongo_uri=backend_settings.mongo_uri,
    )
    return {
        "status": "started",
        "project": project_name,
        "domain": allowed_domain or None,
    }


@crawler_router.get("/status")
async def crawler_status(project: str | None = None) -> dict[str, object]:
    """Return current crawler and database status."""

    project_label = _normalize_project(project)
    data = status_dict(project_label)
    crawler = data.get("crawler") or {}
    note = get_crawler_note(project_label)
    if note:
        data["notes"] = note
    data.update(
        {
            "queued": crawler.get("queued", 0),
            "in_progress": crawler.get("in_progress", 0),
            "done": crawler.get("done", 0),
            "failed": crawler.get("failed", 0),
            "remaining": crawler.get("remaining", max(0, crawler.get("queued", 0) + crawler.get("in_progress", 0))),
            "recent_urls": crawler.get("recent_urls") or [],
            "last_url": crawler.get("last_url"),
        }
    )
    logger.info(
        "crawler_status_snapshot",
        project=project_label,
        ok=data.get("ok"),
        queued=data.get("queued"),
        in_progress=data.get("in_progress"),
        done=data.get("done"),
        failed=data.get("failed"),
        remaining=data.get("remaining"),
        last_url=data.get("last_url"),
        notes=data.get("notes"),
    )
    return data


@crawler_router.post("/reset", status_code=202)
async def crawler_reset(request: Request, project: str | None = None) -> dict[str, object]:
    """Reset crawler counters and recent URLs for the given project."""

    _require_super_admin(request)
    project_label = _normalize_project(project)
    removed = clear_crawler_state(project_label)
    return {"status": "reset", "project": project_label, "purged_jobs": removed}


@crawler_router.post("/deduplicate", status_code=200)
async def crawler_deduplicate(request: Request, project: str | None = None) -> dict[str, object]:
    """Deduplicate the recent URL list for the crawler."""

    _require_super_admin(request)
    project_label = _normalize_project(project)
    removed = deduplicate_recent_urls(project_label)
    return {"status": "deduplicated", "removed": removed, "project": project_label}


@crawler_router.post("/stop", status_code=202)
async def stop_crawler() -> dict[str, str]:
    """Attempt to stop the last started crawler process by PID file."""
    pid_path = Path("/tmp") / "crawler.pid"
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
    except Exception:
        return {"status": "unknown"}
    try:
        os.kill(pid, signal.SIGTERM)
        return {"status": "stopping", "pid": pid}
    except ProcessLookupError:
        return {"status": "not_running"}
    except Exception:
        return {"status": "error"}


@llm_router.get("/info")
def llm_info() -> dict[str, object]:
    """Expose basic LLM runtime details for the admin panel."""
    device = getattr(llm_client, "DEVICE", "unknown")
    model = getattr(llm_client, "MODEL_NAME", None)
    ollama = getattr(llm_client, "OLLAMA_BASE", None)
    backend = "ollama" if ollama else (device or "local")
    return {
        "model": model,
        "device": device,
        "backend": backend,
        "ollama_base": ollama,
    }


class LLMConfig(BaseModel):
    ollama_base: str | None = None
    model: str | None = None


@llm_router.post("/config", response_class=ORJSONResponse)
def llm_set_config(cfg: LLMConfig) -> ORJSONResponse:
    """Update LLM runtime parameters at runtime.

    This does not persist across process restarts; intended for quick ops.
    """
    if cfg.ollama_base is not None:
        llm_client.OLLAMA_BASE = cfg.ollama_base or None
    if cfg.model:
        llm_client.MODEL_NAME = cfg.model
    return ORJSONResponse(llm_info())


@llm_router.get("/ping")
async def llm_ping() -> dict[str, object]:
    """Ping the configured LLM backend.

    - If Ollama base is set, checks ``/api/tags``.
    - Otherwise returns enabled=False.
    """
    base = getattr(llm_client, "OLLAMA_BASE", None)
    if not base:
        return {"enabled": False, "reachable": None}
    import httpx
    url = f"{base.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            resp = await client.get(url)
            ok = bool(resp.status_code == 200)
            return {"enabled": True, "reachable": ok, "status": resp.status_code}
    except Exception as exc:
        return {"enabled": True, "reachable": False, "error": str(exc)}
