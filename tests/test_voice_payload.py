"""Unit tests for voice training payload validation helpers."""

from __future__ import annotations

import sys
import types

import pytest

# Provide lightweight stubs so that ``api`` can be imported without FastAPI.
_original_fastapi = sys.modules.get("fastapi")
_original_fastapi_responses = sys.modules.get("fastapi.responses")
_original_backend_ollama = sys.modules.get("backend.ollama")
_original_worker = sys.modules.get("worker")

fake_fastapi = types.ModuleType("fastapi")


class DummyRouter:
    def __init__(self, *args, **kwargs):
        pass

    def get(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def post(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def delete(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str | None = None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _placeholder(*args, **kwargs):
    return None


fake_fastapi.APIRouter = DummyRouter
fake_fastapi.Request = object
fake_fastapi.HTTPException = HTTPException
fake_fastapi.UploadFile = object
fake_fastapi.File = _placeholder
fake_fastapi.Form = _placeholder

fake_responses = types.ModuleType("fastapi.responses")


class ORJSONResponse:  # pragma: no cover - minimal stub used only during import
    def __init__(self, content, status_code: int = 200):
        self.body = content
        self.status_code = status_code


class StreamingResponse:  # pragma: no cover - minimal stub used only during import
    def __init__(self, *args, **kwargs):
        pass


fake_responses.ORJSONResponse = ORJSONResponse
fake_responses.StreamingResponse = StreamingResponse
fake_fastapi.responses = fake_responses
sys.modules["fastapi"] = fake_fastapi
sys.modules["fastapi.responses"] = fake_responses

fake_ollama = types.ModuleType("backend.ollama")
fake_ollama.list_installed_models = lambda *args, **kwargs: []
fake_ollama.ollama_available = lambda *args, **kwargs: False
fake_ollama.popular_models_with_size = lambda *args, **kwargs: []
sys.modules["backend.ollama"] = fake_ollama

fake_worker = types.ModuleType("worker")
fake_worker.voice_train_model = types.SimpleNamespace(delay=lambda *args, **kwargs: None)
fake_worker.backup_execute = types.SimpleNamespace(delay=lambda *args, **kwargs: None)
sys.modules["worker"] = fake_worker

from apps.api import _validate_voice_payload, VOICE_MAX_SAMPLE_BYTES  # noqa: E402

if _original_fastapi is not None:
    sys.modules["fastapi"] = _original_fastapi
else:
    sys.modules.pop("fastapi", None)

if _original_fastapi_responses is not None:
    sys.modules["fastapi.responses"] = _original_fastapi_responses
else:
    sys.modules.pop("fastapi.responses", None)

if _original_backend_ollama is not None:
    sys.modules["backend.ollama"] = _original_backend_ollama
else:
    sys.modules.pop("backend.ollama", None)

if _original_worker is not None:
    sys.modules["worker"] = _original_worker
else:
    sys.modules.pop("worker", None)


def test_validate_voice_payload_accepts_supported_extension():
    data = b"0" * 1024
    name, content_type, payload = _validate_voice_payload('sample.wav', None, data)
    assert name == 'sample.wav'
    assert payload == data
    assert content_type is None


def test_validate_voice_payload_rejects_empty():
    with pytest.raises(Exception) as excinfo:
        _validate_voice_payload('voice.mp3', 'audio/mpeg', b'')
    assert getattr(excinfo.value, 'detail', None) == 'empty_sample'


def test_validate_voice_payload_rejects_large():
    big_blob = b"0" * (VOICE_MAX_SAMPLE_BYTES + 1)
    with pytest.raises(Exception) as excinfo:
        _validate_voice_payload('voice.mp3', 'audio/mpeg', big_blob)
    assert getattr(excinfo.value, 'detail', None) == 'sample_too_large'


def test_validate_voice_payload_requires_audio_type():
    with pytest.raises(Exception) as excinfo:
        _validate_voice_payload('notes.txt', 'text/plain', b'data')
    assert getattr(excinfo.value, 'detail', None) == 'unsupported_content_type'
