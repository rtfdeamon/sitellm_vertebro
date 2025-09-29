"""Tests for tg_bot.bot handlers."""

import importlib.util
import sys
import types
import asyncio
from pathlib import Path
from typing import Optional
fake_pydantic = types.ModuleType("pydantic")
fake_pydantic.AnyUrl = str
fake_pydantic.BaseSettings = object
fake_pydantic.ConfigDict = dict
fake_pydantic.Field = lambda default=None, **kwargs: default
_real_pydantic = sys.modules.get("pydantic")
sys.modules["pydantic"] = fake_pydantic
fake_structlog = types.ModuleType("structlog")
fake_structlog.get_logger = lambda *a, **k: types.SimpleNamespace(
    info=lambda *x, **y: None,
    warning=lambda *x, **y: None,
    debug=lambda *x, **y: None,
)
sys.modules["structlog"] = fake_structlog
fake_httpx = types.ModuleType("httpx")
fake_httpx.AsyncClient = None
fake_httpx.HTTPError = Exception
sys.modules["httpx"] = fake_httpx

fake_filters = types.ModuleType("aiogram.filters")
fake_filters.CommandStart = object
fake_filters.Command = object
sys.modules["aiogram.filters"] = fake_filters

fake_types = types.ModuleType("aiogram.types")
fake_types.Message = type("Message", (), {"__init__": lambda self, **k: None})
fake_types.URLInputFile = lambda url, filename=None: {"url": url, "filename": filename}
fake_types.BufferedInputFile = lambda data, filename=None: {"data": data, "filename": filename}
sys.modules["aiogram.types"] = fake_types

pkg = types.ModuleType("tg_bot")
pkg.__path__ = [str(Path(__file__).resolve().parents[2] / "tg_bot")]
sys.modules["tg_bot"] = pkg
fake_config = types.ModuleType("tg_bot.config")
fake_config.get_settings = lambda: types.SimpleNamespace(
    api_base_url="http://api",
    backend_url="http://api",
    request_timeout=10,
    resolve_status_url=lambda: "http://api/status",
    speech_to_text_url=None,
    speech_to_text_language=None,
    speech_to_text_api_key=None,
)
sys.modules["tg_bot.config"] = fake_config
fake_client = types.ModuleType("tg_bot.client")

async def _default_rag_answer(text, project=None, session_id=None, debug=None):
    return {"text": "ok", "attachments": []}

fake_client.rag_answer = _default_rag_answer
sys.modules["tg_bot.client"] = fake_client

module_path = Path(__file__).resolve().parents[2] / "tg_bot" / "bot.py"
spec = importlib.util.spec_from_file_location("tg_bot.bot", module_path)
bot_mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bot_mod

fake_aiogram = types.ModuleType("aiogram")
fake_aiogram.Bot = object
fake_aiogram.Dispatcher = object
fake_aiogram.types = fake_types
fake_aiogram.filters = fake_filters
sys.modules["aiogram"] = fake_aiogram

spec.loader.exec_module(bot_mod)

if _real_pydantic is None:
    del sys.modules["pydantic"]
else:
    sys.modules["pydantic"] = _real_pydantic


class FakeMessage:
    """Capture messages sent by handlers during tests."""
    def __init__(self, text="hi"):
        self.text = text
        self.sent = []
        self.documents = []
        self.photos = []
        self.chat = types.SimpleNamespace(id=1, do=lambda action: asyncio.sleep(0))
        self.from_user = types.SimpleNamespace(id=1)
        self.voice = None
        async def _download(_file, destination):
            if hasattr(destination, 'write'):
                destination.write(b"")
        self.bot = types.SimpleNamespace(download=_download)

    async def answer(self, text, **kwargs):
        self.sent.append(text)

    async def answer_document(self, document, **kwargs):
        self.documents.append((document, kwargs))
        self.sent.append(("document", document, kwargs))

    async def answer_photo(self, photo, **kwargs):
        self.photos.append((photo, kwargs))
        self.sent.append(("photo", photo, kwargs))


def test_unknown_command():
    """Handler should reply with unknown message."""
    msg = FakeMessage("/unknown")
    asyncio.run(bot_mod.unknown_handler(msg, "demo", "session"))
    assert msg.sent == ["Unknown command"]


def test_status_handler():
    """Handler should fetch and format status data asynchronously."""
    calls = {}

    class FakeResp:
        def json(self):
            return {
                "db": {
                    "mongo_collections": {"users": 1},
                    "qdrant_points": 2,
                },
                "crawler": {
                    "main": {
                        "queued": 1,
                        "in_progress": 2,
                        "fetched": 2,
                        "parsed": 3,
                        "indexed": 4,
                        "errors": 0,
                        "remaining": 3,
                    }
                },
            }

        def raise_for_status(self):
            pass

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def get(self, url, **kwargs):
            calls["url"] = (url, kwargs)
            return FakeResp()

    fake_httpx.AsyncClient = lambda timeout=None, verify=True: FakeClient()
    bot_mod.get_settings = lambda: types.SimpleNamespace(
        api_base_url="http://api",
        backend_url="http://api",
        request_timeout=1,
        backend_verify_ssl=True,
        backend_ca_path=None,
        resolve_status_url=lambda: "http://api/status",
        speech_to_text_url=None,
        speech_to_text_language=None,
        speech_to_text_api_key=None,
    )
    msg = FakeMessage("/status")
    asyncio.run(bot_mod.status_handler(msg, "demo", "session"))
    assert calls["url"] == ("http://api/status", {"params": {"project": "demo"}})
    expected = (
        "<b>DB</b>\n"
        "• users: 1\n"
        "• qdrant_points: 2\n\n"
        "<b>Crawler</b>\n"
        "• main: queued=1 left=3 fetched=2 parsed=3 indexed=4 errors=0"
    )
    assert msg.sent == [expected]


def test_text_handler_sends_image(monkeypatch):
    """Binary attachments with image content type should be sent as photos."""
    bot_mod.PENDING_BITRIX.clear()

    async def fake_rag_answer(question, project=None, session_id=None, debug=None):
        return {
            "text": "ok",
            "attachments": [
                {
                    "name": "license.jpg",
                    "url": "http://api/doc/license.jpg",
                    "content_type": "image/jpeg",
                    "description": "Фото лицензии",
                }
            ],
        }

    bot_mod.rag_answer = fake_rag_answer

    async def fake_features(project):
        return {
            "emotions_enabled": True,
            "debug_enabled": False,
            "debug_info_enabled": False,
        }

    bot_mod._get_project_features = fake_features

    msg = FakeMessage("show license")
    asyncio.run(bot_mod.text_handler(msg, project="demo", session_id="abc"))

    assert msg.documents == []
    assert msg.photos == []
    assert any('Отправить?' in str(item) or 'Отправить' in str(item) for item in msg.sent)


def test_voice_handler_without_stt():
    """Voice handler should decline when STT URL is not configured."""

    bot_mod.PENDING_BITRIX.clear()
    msg = FakeMessage()
    msg.voice = types.SimpleNamespace(mime_type="audio/ogg")

    asyncio.run(bot_mod.voice_handler(msg, project="demo", session_id="abc"))

    assert msg.sent == ["🎙️ Голосовые сообщения пока не поддерживаются. Попробуйте отправить текст."]


def test_bitrix_pending_prompt_and_confirm(monkeypatch):
    """Bot should prompt for Bitrix confirmation and send on approval."""

    bot_mod.PENDING_BITRIX.clear()

    async def fake_rag_answer(question, project=None, session_id=None, debug=None):
        return {
            "text": "ok",
            "attachments": [],
            "meta": {
                "bitrix_pending": {
                    "plan_id": "plan1",
                    "preview": "Bitrix24 задача (предварительно):\n• Название: Test",
                    "method": "tasks.task.add",
                }
            },
        }

    bot_mod.rag_answer = fake_rag_answer

    async def fake_features(project):
        return {
            "emotions_enabled": True,
            "debug_enabled": False,
            "debug_info_enabled": False,
        }

    bot_mod._get_project_features = fake_features

    calls: list[tuple[str, dict | None]] = []

    class FakeResp:
        def json(self):
            return {"status": "sent"}

        def raise_for_status(self):
            pass

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def post(self, url, json=None, **kwargs):
            calls.append((url, json))
            return FakeResp()

    bot_mod.httpx.AsyncClient = lambda timeout=None: FakeClient()

    msg = FakeMessage("создай задачу")
    asyncio.run(bot_mod.text_handler(msg, project="demo", session_id="abc"))
    assert any('Bitrix24 задача' in str(item) for item in msg.sent)
    pending_key = _pending_key_helper(bot_mod, "demo", "abc")
    assert 'plan1' in bot_mod.PENDING_BITRIX[pending_key]['plan_id']

    confirm_msg = FakeMessage("да")
    asyncio.run(bot_mod.text_handler(confirm_msg, project="demo", session_id="abc"))
    assert calls[-1][0].endswith("/api/v1/llm/bitrix/confirm")
    assert any(str(item).startswith('✅') for item in confirm_msg.sent)
    assert bot_mod.PENDING_BITRIX == {}


def test_bitrix_pending_cancel(monkeypatch):
    """Bot should cancel Bitrix plan on negative reply."""

    bot_mod.PENDING_BITRIX.clear()

    async def fake_rag_answer(question, project=None, session_id=None, debug=None):
        return {
            "text": "ok",
            "attachments": [],
            "meta": {
                "bitrix_pending": {
                    "plan_id": "plan2",
                    "preview": "Задача: Тест",
                    "method": "tasks.task.add",
                }
            },
        }

    bot_mod.rag_answer = fake_rag_answer
    async def fake_features_cancel(project):
        return {
            "emotions_enabled": False,
            "debug_enabled": False,
            "debug_info_enabled": False,
        }

    bot_mod._get_project_features = fake_features_cancel

    calls: list[tuple[str, dict | None]] = []

    class FakeResp:
        def json(self):
            return {"status": "cancelled"}

        def raise_for_status(self):
            pass

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def post(self, url, json=None, **kwargs):
            calls.append((url, json))
            return FakeResp()

    bot_mod.httpx.AsyncClient = lambda timeout=None: FakeClient()

    msg = FakeMessage("создай задачу")
    asyncio.run(bot_mod.text_handler(msg, project="demo", session_id="abc"))

    cancel_msg = FakeMessage("нет")
    asyncio.run(bot_mod.text_handler(cancel_msg, project="demo", session_id="abc"))
    assert calls[-1][0].endswith("/api/v1/llm/bitrix/cancel")
    assert any('Задача не будет создана' in str(item) or 'Создание задачи отменено' in str(item) for item in cancel_msg.sent)
    assert bot_mod.PENDING_BITRIX == {}


def test_mail_pending_prompt_and_confirm(monkeypatch):
    """Bot should prompt for mail confirmation and send on approval."""

    bot_mod.PENDING_MAIL.clear()

    async def fake_rag_answer(question, project=None, session_id=None, debug=None):
        return {
            "text": "Проверьте письмо",
            "attachments": [],
            "meta": {
                "mail_pending": {
                    "plan_id": "mail-plan-1",
                    "preview": "Черновик письма:\n• Кому: user@example.com",
                }
            },
        }

    bot_mod.rag_answer = fake_rag_answer

    async def fake_features(project):
        return {
            "emotions_enabled": True,
            "debug_enabled": False,
            "debug_info_enabled": False,
        }

    bot_mod._get_project_features = fake_features

    calls: list[tuple[str, dict | None]] = []

    class FakeResp:
        def json(self):
            return {"status": "sent", "message_id": "msg-1"}

        def raise_for_status(self):
            pass

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def post(self, url, json=None, **kwargs):
            calls.append((url, json))
            return FakeResp()

    bot_mod.httpx.AsyncClient = lambda timeout=None: FakeClient()

    msg = FakeMessage("отправь письмо")
    asyncio.run(bot_mod.text_handler(msg, project="demo", session_id="abc"))
    assert any('Черновик письма' in str(item) for item in msg.sent)
    pending_key = _pending_key_helper(bot_mod, "demo", "abc")
    assert 'mail-plan-1' in bot_mod.PENDING_MAIL[pending_key]['plan_id']

    confirm_msg = FakeMessage("да")
    asyncio.run(bot_mod.text_handler(confirm_msg, project="demo", session_id="abc"))
    assert calls[-1][0].endswith("/api/v1/llm/mail/confirm")
    assert any('Письмо отправлено' in str(item) for item in confirm_msg.sent)
    assert bot_mod.PENDING_MAIL == {}


def test_mail_pending_cancel(monkeypatch):
    """Bot should cancel mail plan on negative reply."""

    bot_mod.PENDING_MAIL.clear()

    async def fake_rag_answer(question, project=None, session_id=None, debug=None):
        return {
            "text": "Проверьте письмо",
            "attachments": [],
            "meta": {
                "mail_pending": {
                    "plan_id": "mail-plan-2",
                    "preview": "Черновик письма",
                }
            },
        }

    bot_mod.rag_answer = fake_rag_answer

    async def fake_features(project):
        return {
            "emotions_enabled": False,
            "debug_enabled": False,
            "debug_info_enabled": False,
        }

    bot_mod._get_project_features = fake_features

    calls: list[tuple[str, dict | None]] = []

    class FakeResp:
        def json(self):
            return {"status": "cancelled"}

        def raise_for_status(self):
            pass

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def post(self, url, json=None, **kwargs):
            calls.append((url, json))
            return FakeResp()

    bot_mod.httpx.AsyncClient = lambda timeout=None: FakeClient()

    msg = FakeMessage("отправь письмо")
    asyncio.run(bot_mod.text_handler(msg, project="demo", session_id="abc"))

    cancel_msg = FakeMessage("нет")
    asyncio.run(bot_mod.text_handler(cancel_msg, project="demo", session_id="abc"))
    assert calls[-1][0].endswith("/api/v1/llm/mail/cancel")
    assert any('письмо не будет отправлено' in str(item).lower() or 'отправка письма отменена' in str(item) for item in cancel_msg.sent)
    assert bot_mod.PENDING_MAIL == {}


# helpers for tests


def _pending_key_helper(bot_module, project: str, session_id: Optional[str]) -> str:
    return bot_module._pending_key(project, session_id, 1)


def test_voice_handler_without_stt():
    """Voice handler should decline when STT URL is not configured."""

    msg = FakeMessage()
    msg.voice = types.SimpleNamespace(mime_type="audio/ogg")

    asyncio.run(bot_mod.voice_handler(msg, project="demo", session_id="abc"))

    assert msg.sent == ["🎙️ Голосовые сообщения пока не поддерживаются. Попробуйте отправить текст."]
