"""
Voice assistant API router.

Implements the first slice of the `/api/v1/voice` contract: session lifecycle,
basic analytics and placeholder speech endpoints that will be filled in next.
"""

from __future__ import annotations

import os
import base64
import hashlib
import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from voice.schemas import (
    DialogMessageRequest,
    IntentRequest,
    IntentResponse,
    RecognitionRequest,
    RecognitionResult,
    ResponseMessage,
    SynthesisRequest,
    SynthesisResponse,
    VoiceSessionRequest,
    VoiceSessionResponse,
)
from mongo import MongoClient
from voice.dialog_manager import DialogManager, DialogContext
from voice.recognizer import BaseRecognizer, SimpleRecognizer
from voice.synthesizer import TTSManager

logger = structlog.get_logger(__name__)

VOICE_SESSION_TIMEOUT = int(os.getenv("VOICE_SESSION_TIMEOUT", "3600"))
VOICE_MAX_CONCURRENT_SESSIONS = int(os.getenv("VOICE_MAX_CONCURRENT_SESSIONS", "100"))
WS_MAX_CONNECTIONS = int(os.getenv("WS_MAX_CONNECTIONS", "1000"))
WS_PING_INTERVAL = int(os.getenv("WS_PING_INTERVAL", "30"))

# Provider selection from environment
VOICE_STT_PROVIDER = os.getenv("VOICE_STT_PROVIDER", "simple")  # simple, whisper, vosk
VOICE_TTS_PROVIDER = os.getenv("VOICE_TTS_PROVIDER", "demo")  # demo, elevenlabs, azure

voice_assistant_router = APIRouter(
    prefix="/voice",
    tags=["voice assistant"],
)

# Initialize recognizer based on configuration
_recognizer: BaseRecognizer = SimpleRecognizer()
if VOICE_STT_PROVIDER == "whisper":
    try:
        from voice.providers.whisper_recognizer import WhisperRecognizer
        _recognizer = WhisperRecognizer()
        logger.info("voice_stt_provider", provider="whisper")
    except ImportError:
        logger.warning("whisper_not_available", fallback="simple")
        _recognizer = SimpleRecognizer()
elif VOICE_STT_PROVIDER == "vosk":
    try:
        from voice.providers.vosk_recognizer import VoskRecognizer
        _recognizer = VoskRecognizer()
        logger.info("voice_stt_provider", provider="vosk")
    except ImportError:
        logger.warning("vosk_not_available", fallback="simple")
        _recognizer = SimpleRecognizer()

# Initialize TTS manager and register providers
_tts_manager = TTSManager()

# Register TTS providers based on configuration
async def _initialize_tts_providers() -> None:
    """Initialize TTS providers based on environment configuration."""
    global _tts_manager
    
    # Always register simple provider as fallback
    from voice.synthesizer import SimpleTTSProvider
    await _tts_manager.register_provider(SimpleTTSProvider())
    
    # Register ElevenLabs if configured
    if VOICE_TTS_PROVIDER == "elevenlabs" or os.getenv("ELEVENLABS_API_KEY"):
        try:
            from voice.providers.elevenlabs_tts import ElevenLabsTTSProvider
            provider = ElevenLabsTTSProvider()
            await provider.setup()
            await _tts_manager.register_provider(provider)
            logger.info("voice_tts_provider_registered", provider="elevenlabs")
        except Exception as exc:  # noqa: BLE001
            logger.warning("elevenlabs_registration_failed", error=str(exc))
    
    # Register Azure if configured
    if VOICE_TTS_PROVIDER == "azure" or os.getenv("AZURE_SPEECH_KEY"):
        try:
            from voice.providers.azure_tts import AzureTTSPvider
            provider = AzureTTSPvider()
            await provider.setup()
            await _tts_manager.register_provider(provider)
            logger.info("voice_tts_provider_registered", provider="azure")
        except Exception as exc:  # noqa: BLE001
            logger.warning("azure_registration_failed", error=str(exc))

_dialog_manager = DialogManager()


def _get_mongo(request: Request) -> MongoClient:
    mongo_client: MongoClient | None = getattr(request.state, "mongo", None)
    if mongo_client is None:
        mongo_client = getattr(request.app.state, "mongo", None)
    if mongo_client is None:
        raise HTTPException(status_code=503, detail="mongo_unavailable")
    return mongo_client


def _build_ws_url(request: Request, session_id: str) -> str:
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    scheme = forwarded_proto or request.url.scheme
    host = forwarded_host or request.url.netloc
    return f"{'wss' if scheme == 'https' else 'ws'}://{host}/api/v1/voice/ws/{session_id}"


def _build_initial_greeting(language: str) -> str:
    if language.startswith("en"):
        return "Voice assistant ready. How can I help you today?"
    return "Голосовой ассистент готов. Чем могу помочь?"


@voice_assistant_router.post(
    "/session/start",
    response_model=VoiceSessionResponse,
    status_code=201,
)
async def start_voice_session(
    payload: VoiceSessionRequest,
    request: Request,
) -> VoiceSessionResponse:
    """Create a new voice session and return websocket connection details."""

    mongo = _get_mongo(request)
    active_sessions = await mongo.count_active_voice_sessions()
    if active_sessions >= VOICE_MAX_CONCURRENT_SESSIONS:
        raise HTTPException(status_code=503, detail="voice_concurrency_limit")

    session_id = uuid4().hex
    expires_delta = timedelta(seconds=VOICE_SESSION_TIMEOUT)
    expires_at = datetime.now(timezone.utc) + expires_delta

    await mongo.create_voice_session(
        session_id=session_id,
        project=payload.project,
        user_id=payload.user_id or "anonymous",
        metadata={
            "language": payload.language,
            "voice_preference": payload.voice_preference or {},
        },
        expires_in=expires_delta,
    )

    logger.info(
        "voice_session_created",
        session_id=session_id,
        project=payload.project,
        user_id=payload.user_id,
    )

    return VoiceSessionResponse(
        session_id=session_id,
        websocket_url=_build_ws_url(request, session_id),
        expires_at=expires_at,
        initial_greeting=_build_initial_greeting(payload.language),
    )


@voice_assistant_router.get(
    "/session/{session_id}",
    response_model=VoiceSessionResponse,
)
async def get_voice_session(session_id: str, request: Request) -> VoiceSessionResponse:
    """Return metadata for an existing voice session."""

    mongo = _get_mongo(request)
    session = await mongo.get_voice_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="voice_session_not_found")

    expires_at = session.get("expires_at")
    if not isinstance(expires_at, datetime):
        expires_at = datetime.now(timezone.utc)

    metadata = session.get("metadata") or {}
    return VoiceSessionResponse(
        session_id=session_id,
        websocket_url=_build_ws_url(request, session_id),
        expires_at=expires_at,
        initial_greeting=_build_initial_greeting(metadata.get("language", "ru-RU")),
    )


@voice_assistant_router.delete(
    "/session/{session_id}",
    status_code=204,
)
async def delete_voice_session(session_id: str, request: Request) -> None:
    """Explicitly terminate a voice session."""

    mongo = _get_mongo(request)
    removed = await mongo.delete_voice_session(session_id)
    if not removed:
        raise HTTPException(status_code=404, detail="voice_session_not_found")
    logger.info("voice_session_deleted", session_id=session_id)


@voice_assistant_router.get("/session/{session_id}/history")
async def get_voice_session_history(
    session_id: str,
    request: Request,
    limit: int = 50,
) -> dict[str, Any]:
    """Return chronological interaction history."""

    mongo = _get_mongo(request)
    history = await mongo.get_session_history(session_id, limit=min(limit, 200))
    return {"session_id": session_id, "items": history}


@voice_assistant_router.get("/analytics/project/{project}")
async def get_project_voice_analytics(project: str, request: Request) -> dict[str, Any]:
    """Return lightweight analytics for a project."""

    mongo = _get_mongo(request)
    sessions_total = await mongo.count_voice_sessions(project=project)
    interactions_total = await mongo.count_voice_interactions(project=project)
    active_sessions = await mongo.count_active_voice_sessions(project=project)

    return {
        "project": project,
        "sessions_total": sessions_total,
        "interactions_total": interactions_total,
        "active_sessions": active_sessions,
        "ws_max_connections": WS_MAX_CONNECTIONS,
        "ws_ping_interval": WS_PING_INTERVAL,
    }


@voice_assistant_router.post("/recognize", response_model=RecognitionResult, status_code=200)
async def recognize_speech(payload: RecognitionRequest) -> RecognitionResult:
    """Perform a lightweight speech recognition pass."""

    audio_bytes = b""
    if payload.audio_base64:
        try:
            audio_bytes = base64.b64decode(payload.audio_base64)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail="invalid_audio_payload") from exc
    result = await _recognizer.recognize(
        audio_bytes,
        language=payload.language,
        text_hint=payload.text_hint,
    )
    return result


@voice_assistant_router.post("/synthesize", response_model=SynthesisResponse, status_code=202)
async def synthesize_speech(payload: SynthesisRequest, request: Request) -> SynthesisResponse:
    """Generate speech audio using the demo provider and cache it."""

    mongo = _get_mongo(request)
    # Include emotion in cache key to ensure different emotions yield different cache entries
    cache_key = f"{payload.text}|{payload.voice}|{payload.language}|{payload.emotion or 'neutral'}"
    text_hash = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
    cached_entry = await mongo.get_cached_audio(
        text_hash=text_hash,
        voice=payload.voice,
        language=payload.language,
    )
    if cached_entry:
        audio_id = cached_entry["audio_id"]
        duration = cached_entry.get("duration_seconds", 0.0)
        return SynthesisResponse(
            audio_url=f"/api/v1/voice/audio/{audio_id}",
            duration_seconds=duration,
            cached=True,
        )

    synthesis_payload = await _tts_manager.synthesize(
        payload.text,
        voice=payload.voice,
        language=payload.language,
        emotion=payload.emotion,
        options=payload.options,
    )
    audio_id = uuid4().hex
    await mongo.cache_audio(
        audio_id,
        text=payload.text,
        voice=payload.voice,
        language=payload.language,
        provider=synthesis_payload.provider,
        audio_data=synthesis_payload.audio_bytes,
        duration_seconds=synthesis_payload.duration_seconds,
        cost=synthesis_payload.cost,
        text_hash=text_hash,
    )

    return SynthesisResponse(
        audio_url=f"/api/v1/voice/audio/{audio_id}",
        duration_seconds=synthesis_payload.duration_seconds,
        cached=False,
    )


@voice_assistant_router.get("/audio/{audio_id}")
async def get_synthesized_audio(audio_id: str, request: Request) -> StreamingResponse:
    """Return audio bytes from the cache."""

    mongo = _get_mongo(request)
    payload = await mongo.get_audio_data(audio_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="audio_not_found")
    return StreamingResponse(
        iter([payload]),
        media_type="audio/mpeg",
        headers={"Content-Disposition": f'inline; filename="{audio_id}.mp3"'},
    )


@voice_assistant_router.post("/dialog/intent", response_model=IntentResponse, status_code=200)
async def analyze_intent(payload: IntentRequest) -> IntentResponse:
    """Return a lightweight intent prediction."""

    context = DialogContext()
    result = await _dialog_manager.intent_classifier.classify(payload.text, context)
    return IntentResponse(
        intent=result["intent"],
        confidence=result["confidence"],
        entities=result["entities"],
        suggested_action=result.get("suggested_action"),
    )


@voice_assistant_router.post("/dialog/respond", response_model=ResponseMessage, status_code=202)
async def dialog_response(payload: DialogMessageRequest, request: Request) -> ResponseMessage:
    """Handle a simple dialog turn and log interactions."""

    mongo = _get_mongo(request)
    session = await mongo.get_voice_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="voice_session_not_found")

    await mongo.update_voice_session_activity(payload.session_id)
    await mongo.log_voice_interaction(
        session_id=payload.session_id,
        project=payload.project,
        user_id=session.get("user_id", "anonymous"),
        interaction_type="user",
        content={"text": payload.text, "metadata": payload.metadata or {}},
    )

    dialog_result = await _dialog_manager.handle_user_message(payload.text)
    response_payload = dialog_result["response"]

    await mongo.log_voice_interaction(
        session_id=payload.session_id,
        project=payload.project,
        user_id="assistant",
        interaction_type="assistant",
        content=response_payload,
    )

    return ResponseMessage(
        type="response",
        text=response_payload["text"],
        audio_url=None,
        sources=response_payload.get("sources", []),
        suggested_actions=response_payload.get("actions", []),
    )


@voice_assistant_router.websocket("/ws/{session_id}")
async def voice_websocket(websocket: WebSocket, session_id: str) -> None:
    """WebSocket endpoint for bidirectional audio streaming.
    
    Handles:
    - Audio chunks from client (base64 encoded)
    - Real-time speech recognition
    - Dialog responses with synthesized audio
    - Session lifecycle management
    """
    await websocket.accept()
    
    # Verify session exists
    try:
        mongo = _get_mongo_from_app(websocket.app)
        session = await mongo.get_voice_session(session_id)
        if not session:
            await websocket.close(code=1008, reason="Session not found")
            return
    except Exception as exc:  # noqa: BLE001
        logger.error("voice_websocket_session_check_failed", session_id=session_id, error=str(exc))
        await websocket.close(code=1011, reason="Internal error")
        return
    
    # Initialize recognizer for streaming
    recognizer = _recognizer
    audio_buffer = bytearray()
    
    try:
        await recognizer.start_stream()
        
        # Send initial greeting
        greeting = _build_initial_greeting(session.get("metadata", {}).get("language", "ru-RU"))
        await websocket.send_json({
            "type": "greeting",
            "text": greeting,
            "audio_url": None,  # Synthesize audio if needed
        })
        
        # Main message loop
        while True:
            try:
                # Receive message with timeout
                message = await asyncio.wait_for(websocket.receive(), timeout=WS_PING_INTERVAL)
                
                if message["type"] == "websocket.receive":
                    if "text" in message:
                        # JSON message
                        data = json.loads(message["text"])
                        await _handle_websocket_message(
                            websocket,
                            data,
                            session_id,
                            recognizer,
                            audio_buffer,
                        )
                    elif "bytes" in message:
                        # Binary audio chunk
                        chunk = message["bytes"]
                        audio_buffer.extend(chunk)
                        
                        # Process chunk for recognition
                        result = await recognizer.process_stream_chunk(bytes(chunk))
                        if result and result.is_final:
                            # Send recognition result
                            await websocket.send_json({
                                "type": "recognition",
                                "text": result.text,
                                "confidence": result.confidence,
                                "language": result.language,
                                "is_final": True,
                            })
                            audio_buffer.clear()
                        elif result:
                            # Partial result
                            await websocket.send_json({
                                "type": "recognition",
                                "text": result.text,
                                "confidence": result.confidence,
                                "is_final": False,
                            })
                    else:
                        logger.warning("voice_websocket_unexpected_message", message_type=message.get("type"))
                
                elif message["type"] == "websocket.disconnect":
                    logger.info("voice_websocket_disconnected", session_id=session_id)
                    break
                    
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({"type": "ping"})
                # Update session activity
                try:
                    mongo = _get_mongo_from_app(websocket.app)
                    await mongo.update_voice_session_activity(session_id)
                except Exception:  # noqa: BLE001
                    pass
            except json.JSONDecodeError as exc:
                logger.warning("voice_websocket_invalid_json", error=str(exc))
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })
            except Exception as exc:  # noqa: BLE001
                logger.error("voice_websocket_message_failed", error=str(exc))
                await websocket.send_json({
                    "type": "error",
                    "message": "Internal error",
                })
    
    except WebSocketDisconnect:
        logger.info("voice_websocket_client_disconnected", session_id=session_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("voice_websocket_failed", session_id=session_id, error=str(exc))
        try:
            await websocket.close(code=1011, reason="Internal error")
        except Exception:  # noqa: BLE001
            pass
    finally:
        # Finalize recognition stream
        try:
            final_result = await recognizer.finish_stream()
            if final_result:
                await websocket.send_json({
                    "type": "recognition",
                    "text": final_result.text,
                    "confidence": final_result.confidence,
                    "is_final": True,
                })
        except Exception:  # noqa: BLE001
            pass
        
        # Update session activity one last time
        try:
            mongo = _get_mongo_from_app(websocket.app)
            await mongo.update_voice_session_activity(session_id)
        except Exception:  # noqa: BLE001
            pass


async def _handle_websocket_message(
    websocket: WebSocket,
    data: dict[str, Any],
    session_id: str,
    recognizer: BaseRecognizer,
    audio_buffer: bytearray,
) -> None:
    """Handle WebSocket JSON message."""
    message_type = data.get("type")
    
    if message_type == "audio":
        # Process base64 encoded audio
        audio_b64 = data.get("audio")
        if audio_b64:
            try:
                audio_bytes = base64.b64decode(audio_b64)
                audio_buffer.extend(audio_bytes)
                
                # Process chunk
                result = await recognizer.process_stream_chunk(audio_bytes)
                if result:
                    await websocket.send_json({
                        "type": "recognition",
                        "text": result.text,
                        "confidence": result.confidence,
                        "language": result.language,
                        "is_final": result.is_final,
                    })
            except Exception as exc:  # noqa: BLE001
                logger.error("voice_websocket_audio_process_failed", error=str(exc))
    
    elif message_type == "text":
        # Process text message (as if recognized)
        text = data.get("text", "")
        if text:
            # Get dialog response
            dialog_result = await _dialog_manager.handle_user_message(text)
            response = dialog_result["response"]
            
            # Synthesize audio if needed
            audio_url = None
            if data.get("synthesize", False):
                try:
                    mongo = _get_mongo_from_app(websocket.app)
                    session = await mongo.get_voice_session(session_id)
                    language = session.get("metadata", {}).get("language", "ru-RU") if session else "ru-RU"
                    
                    synthesis_payload = await _tts_manager.synthesize(
                        response["text"],
                        voice="default",
                        language=language,
                    )
                    audio_id = uuid4().hex
                    await mongo.cache_audio(
                        audio_id,
                        text=response["text"],
                        voice="default",
                        language=language,
                        provider=synthesis_payload.provider,
                        audio_data=synthesis_payload.audio_bytes,
                        duration_seconds=synthesis_payload.duration_seconds,
                        cost=synthesis_payload.cost,
                    )
                    audio_url = f"/api/v1/voice/audio/{audio_id}"
                except Exception as exc:  # noqa: BLE001
                    logger.error("voice_websocket_synthesis_failed", error=str(exc))
            
            # Send response
            await websocket.send_json({
                "type": "response",
                "text": response["text"],
                "audio_url": audio_url,
                "sources": response.get("sources", []),
                "suggested_actions": response.get("actions", []),
            })
            
            # Log interaction
            try:
                mongo = _get_mongo_from_app(websocket.app)
                session = await mongo.get_voice_session(session_id)
                await mongo.log_voice_interaction(
                    session_id=session_id,
                    project=session.get("project") if session else None,
                    user_id=session.get("user_id", "anonymous") if session else "anonymous",
                    interaction_type="user",
                    content={"text": text},
                )
                await mongo.log_voice_interaction(
                    session_id=session_id,
                    project=session.get("project") if session else None,
                    user_id="assistant",
                    interaction_type="assistant",
                    content=response,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("voice_websocket_logging_failed", error=str(exc))
    
    elif message_type == "ping":
        # Respond to ping
        await websocket.send_json({"type": "pong"})
    
    elif message_type == "close":
        # Client requested close
        await websocket.close(code=1000, reason="Client requested close")


def _get_mongo_from_app(app: Any) -> MongoClient:
    """Get MongoDB client from app state."""
    mongo_client: MongoClient | None = getattr(app.state, "mongo", None)
    if mongo_client is None:
        raise HTTPException(status_code=503, detail="mongo_unavailable")
    return mongo_client


# Initialize TTS providers on module import (will be called from lifespan)
async def initialize_voice_providers() -> None:
    """Initialize voice providers (called from app lifespan)."""
    await _initialize_tts_providers()
    if _recognizer:
        try:
            if hasattr(_recognizer, "setup"):
                await _recognizer.setup()
            logger.info("voice_recognizer_initialized", provider=getattr(_recognizer, "name", "unknown"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("voice_recognizer_setup_failed", error=str(exc))

