from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from voice.router import voice_assistant_router


class InMemoryVoiceStore:
    def __init__(self) -> None:
        self.sessions: dict[str, dict[str, Any]] = {}
        self.interactions: list[dict[str, Any]] = []
        self.audio_cache: dict[str, dict[str, Any]] = {}

    # Session helpers -----------------------------------------------------
    async def count_active_voice_sessions(self, project: str | None = None) -> int:
        return sum(
            1
            for session in self.sessions.values()
            if session["status"] == "active" and (not project or session["project"] == project)
        )

    async def count_voice_sessions(self, project: str | None = None) -> int:
        return sum(1 for session in self.sessions.values() if not project or session["project"] == project)

    async def count_voice_interactions(self, project: str | None = None) -> int:
        return sum(
            1 for item in self.interactions if not project or item["project"] == project
        )

    async def create_voice_session(
        self,
        session_id: str,
        project: str,
        user_id: str,
        metadata: dict[str, Any],
        *,
        expires_in: timedelta,
    ) -> str:
        now = datetime.now(timezone.utc)
        self.sessions[session_id] = {
            "session_id": session_id,
            "project": project,
            "user_id": user_id,
            "metadata": metadata,
            "created_at": now,
            "expires_at": now + expires_in,
            "last_activity": now,
            "total_interactions": 0,
            "status": "active",
        }
        return session_id

    async def get_voice_session(self, session_id: str) -> dict[str, Any] | None:
        return self.sessions.get(session_id)

    async def delete_voice_session(self, session_id: str) -> bool:
        existed = session_id in self.sessions
        self.sessions.pop(session_id, None)
        self.interactions = [item for item in self.interactions if item["session_id"] != session_id]
        return existed

    async def update_voice_session_activity(self, session_id: str) -> None:
        if session_id in self.sessions:
            self.sessions[session_id]["last_activity"] = datetime.now(timezone.utc)
            self.sessions[session_id]["total_interactions"] += 1

    async def get_session_history(self, session_id: str, *, limit: int) -> list[dict[str, Any]]:
        items = [item for item in self.interactions if item["session_id"] == session_id]
        return items[:limit]

    async def cleanup_expired_sessions(self) -> int:  # pragma: no cover
        return 0

    # Analytics helpers ---------------------------------------------------
    async def log_voice_interaction(
        self,
        session_id: str,
        project: str,
        user_id: str,
        interaction_type: str,
        content: dict[str, Any],
        **extra: Any,
    ) -> str:
        payload = {
            "session_id": session_id,
            "project": project,
            "user_id": user_id,
            "interaction_type": interaction_type,
            "content": content,
            **extra,
        }
        self.interactions.append(payload)
        return "interaction"

    # Audio cache ---------------------------------------------------------
    async def cache_audio(
        self,
        audio_id: str,
        *,
        text: str,
        voice: str,
        language: str,
        provider: str,
        audio_data: bytes,
        duration_seconds: float,
        cost: float,
        text_hash: str | None = None,
    ) -> str:
        if text_hash is None:
            text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self.audio_cache[audio_id] = {
            "audio_id": audio_id,
            "text": text,
            "text_hash": text_hash,
            "voice": voice,
            "language": language,
            "provider": provider,
            "duration_seconds": duration_seconds,
            "audio_bytes": audio_data,
        }
        return audio_id

    async def get_cached_audio(
        self,
        *,
        text_hash: str,
        voice: str,
        language: str,
    ) -> dict[str, Any] | None:
        for entry in self.audio_cache.values():
            if entry["text_hash"] == text_hash and entry["voice"] == voice and entry["language"] == language:
                return entry
        return None

    async def get_audio_data(self, audio_id: str) -> bytes | None:
        entry = self.audio_cache.get(audio_id)
        if not entry:
            return None
        return entry["audio_bytes"]


def make_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(voice_assistant_router, prefix="/api/v1")
    app.state.mongo = InMemoryVoiceStore()
    return TestClient(app)


def test_session_lifecycle_and_history():
    client = make_test_client()

    # Create
    response = client.post(
        "/api/v1/voice/session/start",
        json={"project": "demo", "user_id": "u1", "language": "ru-RU"},
    )
    assert response.status_code == 201
    data = response.json()
    session_id = data["session_id"]

    # Fetch
    get_response = client.get(f"/api/v1/voice/session/{session_id}")
    assert get_response.status_code == 200

    # Dialog turn
    dialog_response = client.post(
        "/api/v1/voice/dialog/respond",
        json={"session_id": session_id, "project": "demo", "text": "navigate to pricing"},
    )
    assert dialog_response.status_code == 202
    assert dialog_response.json()["suggested_actions"]

    # History
    history_response = client.get(f"/api/v1/voice/session/{session_id}/history")
    assert history_response.status_code == 200
    assert len(history_response.json()["items"]) == 2

    # Analytics
    analytics_response = client.get("/api/v1/voice/analytics/project/demo")
    assert analytics_response.status_code == 200
    assert analytics_response.json()["sessions_total"] == 1

    # Delete
    delete_response = client.delete(f"/api/v1/voice/session/{session_id}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/v1/voice/session/{session_id}").status_code == 404


def test_recognize_and_synthesize_endpoints():
    client = make_test_client()

    # Recognize
    audio_payload = base64.b64encode(b"demo audio").decode("ascii")
    recognition = client.post("/api/v1/voice/recognize", json={"audio_base64": audio_payload})
    assert recognition.status_code == 200
    assert "audio" in recognition.json()["text"]

    # Synthesize and cache
    synth = client.post(
        "/api/v1/voice/synthesize",
        json={"text": "Привет!", "voice": "default", "language": "ru-RU"},
    )
    assert synth.status_code == 202
    audio_url = synth.json()["audio_url"]
    assert audio_url.endswith(".mp3") is False  # path format

    # Fetch cached audio
    audio_id = audio_url.rsplit("/", 1)[-1]
    audio_response = client.get(audio_url)
    assert audio_response.status_code == 200
    assert audio_response.headers["content-type"] == "audio/mpeg"

    # Second call should be cached
    synth_cached = client.post(
        "/api/v1/voice/synthesize",
        json={"text": "Привет!", "voice": "default", "language": "ru-RU"},
    )
    assert synth_cached.json()["cached"] is True

