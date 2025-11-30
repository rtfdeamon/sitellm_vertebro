"""Tests for the voice training API flow."""

from __future__ import annotations

import asyncio
import sys
import time
import types
from dataclasses import dataclass

import pytest

_original_backend_ollama = sys.modules.get("backend.ollama")
fake_backend_ollama = types.ModuleType("backend.ollama")
fake_backend_ollama.list_installed_models = lambda *args, **kwargs: []
fake_backend_ollama.ollama_available = lambda *args, **kwargs: False
fake_backend_ollama.popular_models_with_size = lambda *args, **kwargs: []
sys.modules["backend.ollama"] = fake_backend_ollama

_original_worker = sys.modules.get("worker")
fake_worker = types.ModuleType("worker")
fake_worker.voice_train_model = types.SimpleNamespace(delay=lambda *args, **kwargs: None)
fake_worker.backup_execute = types.SimpleNamespace(delay=lambda *args, **kwargs: None)
fake_worker.get_mongo_client = lambda: None
fake_worker.settings = types.SimpleNamespace()
sys.modules["worker"] = fake_worker

from apps import api
from packages.core.models import VoiceTrainingJob, VoiceTrainingStatus

if _original_backend_ollama is not None:
    sys.modules["backend.ollama"] = _original_backend_ollama
else:  # pragma: no cover - cleanup when module absent originally
    sys.modules.pop("backend.ollama", None)

if _original_worker is not None:
    sys.modules["worker"] = _original_worker
else:  # pragma: no cover - cleanup when module absent originally
    sys.modules.pop("worker", None)


class _DummyResponse:
    def __init__(self, content, status_code: int = 200, headers=None, media_type=None, background=None):
        self.body = content
        self.status_code = status_code
        self.headers = headers or {}
        self.media_type = media_type
        self.background = background


api.ORJSONResponse = _DummyResponse


@dataclass
class _StubMongo:
    jobs: list[VoiceTrainingJob]

    def __post_init__(self) -> None:
        self.samples = [object(), object(), object()]

    async def list_voice_samples(self, project: str) -> list[object]:
        return self.samples

    async def list_voice_training_jobs(self, project: str, *, limit: int = 1) -> list[VoiceTrainingJob]:
        if limit <= 0:
            return []
        return self.jobs[:limit]

    async def create_voice_training_job(self, project: str) -> VoiceTrainingJob:
        job_id = f"job-{len(self.jobs) + 1}"
        now = time.time()
        payload = {
            "id": job_id,
            "project": project,
            "status": VoiceTrainingStatus.queued,
            "progress": 0.0,
            "createdAt": now,
            "updatedAt": now,
        }
        job = VoiceTrainingJob(**payload)
        self.jobs.insert(0, job)
        return job

    async def update_voice_training_job(self, job_id: str, **updates) -> VoiceTrainingJob | None:
        for idx, job in enumerate(self.jobs):
            if job.id != job_id:
                continue
            payload = job.model_dump(by_alias=True)
            payload.update({k: v for k, v in updates.items() if v is not None})
            status_value = payload.get("status")
            if isinstance(status_value, VoiceTrainingStatus):
                payload["status"] = status_value.value
            updated = VoiceTrainingJob(**payload)
            self.jobs[idx] = updated
            return updated
        return None


class _StubRequest:
    def __init__(self, mongo: _StubMongo):
        self.state = types.SimpleNamespace(mongo=mongo)
        self.app = types.SimpleNamespace(state=types.SimpleNamespace())


def _make_job(status: VoiceTrainingStatus, *, created: float | None = None, updated: float | None = None) -> VoiceTrainingJob:
    created_ts = created if created is not None else time.time()
    updated_ts = updated if updated is not None else created_ts
    payload = {
        "id": "job-queued",
        "project": "demo",
        "status": status,
        "progress": 0.1,
        "message": "queued",
        "createdAt": created_ts,
        "updatedAt": updated_ts,
    }
    return VoiceTrainingJob(**payload)


@pytest.mark.asyncio
async def test_start_voice_training_creates_new_job(monkeypatch: pytest.MonkeyPatch) -> None:
    mongo = _StubMongo(jobs=[])
    request = _StubRequest(mongo)
    monkeypatch.setattr(api, "worker_mongo_client", None)
    monkeypatch.setattr(api, "worker_settings", None)

    inline_calls: list[tuple[str, _StubMongo]] = []

    async def _fake_run_inline(job_id: str, client: _StubMongo) -> None:
        inline_calls.append((job_id, client))

    monkeypatch.setattr(api, "_run_voice_job_inline", _fake_run_inline)

    response = await api.start_voice_training(request, project="demo")
    assert response.status_code == 202
    payload = response.body
    assert payload["detail"] == "job_queued"
    await asyncio.sleep(0)
    assert inline_calls == [("job-1", mongo)]


@pytest.mark.asyncio
async def test_start_voice_training_reports_in_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    job = _make_job(VoiceTrainingStatus.queued, created=time.time(), updated=time.time())
    mongo = _StubMongo(jobs=[job])
    request = _StubRequest(mongo)

    watchdog_calls: list[tuple[str, str]] = []

    async def _fake_watchdog(job_id: str, project: str, client: _StubMongo) -> None:
        watchdog_calls.append((job_id, project))

    monkeypatch.setattr(api, "_voice_job_watchdog", _fake_watchdog)

    response = await api.start_voice_training(request, project="demo")
    assert response.status_code == 202
    payload = response.body
    assert payload["detail"] == "job_in_progress"
    await asyncio.sleep(0)
    assert watchdog_calls == [("job-queued", "demo")]


@pytest.mark.asyncio
async def test_start_voice_training_resumes_stale_job(monkeypatch: pytest.MonkeyPatch) -> None:
    stale_updated = time.time() - (api.VOICE_JOB_STALE_TIMEOUT + 5)
    job = _make_job(VoiceTrainingStatus.queued, created=stale_updated - 10, updated=stale_updated)
    mongo = _StubMongo(jobs=[job])
    request = _StubRequest(mongo)

    inline_calls: list[str] = []

    async def _fake_inline(job_id: str, client: _StubMongo) -> None:
        inline_calls.append(job_id)

    monkeypatch.setattr(api, "_run_voice_job_inline", _fake_inline)
    monkeypatch.setattr(api, "_queue_voice_training_job", lambda job_id: False)

    response = await api.start_voice_training(request, project="demo")
    assert response.status_code == 202
    payload = response.body
    assert payload["detail"] == "job_resumed"
    await asyncio.sleep(0)
    assert inline_calls == ["job-queued"]


def test_limit_dialog_history_produces_summary() -> None:
    # Build alternating user/assistant turns with the final entry being a user prompt awaiting reply.
    conversation: list[dict[str, str]] = []
    for idx in range(1, 6):
        conversation.append({"role": "user", "content": f"question {idx}"})
        if idx < 5:
            conversation.append({"role": "assistant", "content": f"answer {idx}"})

    limited = api._limit_dialog_history(conversation, max_turns=3, max_chars=10_000)

    assert limited[0]["role"] == "system"
    assert "question 1" in limited[0]["content"]
    # Expect last message to remain the latest user question.
    assert limited[-1]["role"] == "user"
    assert limited[-1]["content"] == "question 5"
    # With max_turns=3 we keep three user turns (user3-user5) plus their assistant replies.
    # Added system summary makes total length 1 + 5 (assistant responses exist for user3/user4).
    assert len(limited) == 6


def test_limit_dialog_history_respects_char_budget() -> None:
    conversation = [
        {"role": "user", "content": "short"},
        {"role": "assistant", "content": "response"},
        {"role": "user", "content": "x" * 200},
        {"role": "assistant", "content": "y" * 200},
        {"role": "user", "content": "latest"},
    ]

    limited = api._limit_dialog_history(conversation, max_turns=5, max_chars=180)

    # Summary is inserted because truncation removed older turns.
    assert limited[0]["role"] == "system"
    total_chars = sum(len(item.get("content", "")) for item in limited)
    assert total_chars <= 180
    assert limited[-1]["content"] == "latest"
