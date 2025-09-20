"""Tests for tg_bot.bot handlers."""

import importlib.util
import sys
import types
import asyncio
from pathlib import Path
fake_pydantic = types.ModuleType("pydantic")
fake_pydantic.AnyUrl = str
fake_pydantic.BaseSettings = object
fake_pydantic.ConfigDict = dict
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
sys.modules["aiogram.types"] = fake_types

pkg = types.ModuleType("tg_bot")
pkg.__path__ = [str(Path(__file__).resolve().parents[2] / "tg_bot")]
sys.modules["tg_bot"] = pkg
fake_config = types.ModuleType("tg_bot.config")
fake_config.get_settings = lambda: types.SimpleNamespace(
    api_base_url="http://api",
    request_timeout=10,
    resolve_status_url=lambda: "http://api/status",
)
sys.modules["tg_bot.config"] = fake_config
fake_client = types.ModuleType("tg_bot.client")

async def _default_rag_answer(text, project=None, session_id=None):
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
        self.chat = types.SimpleNamespace(do=lambda action: asyncio.sleep(0))
        self.from_user = types.SimpleNamespace(id=1)

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
                        "fetched": 2,
                        "parsed": 3,
                        "indexed": 4,
                        "errors": 0,
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

    fake_httpx.AsyncClient = lambda timeout=None: FakeClient()
    bot_mod.get_settings = lambda: types.SimpleNamespace(
        api_base_url="http://api",
        request_timeout=1,
        resolve_status_url=lambda: "http://api/status",
    )
    msg = FakeMessage("/status")
    asyncio.run(bot_mod.status_handler(msg, "demo", "session"))
    assert calls["url"] == ("http://api/status", {"params": {"project": "demo"}})
    expected = (
        "<b>DB</b>\n"
        "• users: 1\n"
        "• qdrant_points: 2\n\n"
        "<b>Crawler</b>\n"
        "• main: queued=1 fetched=2 parsed=3 indexed=4 errors=0"
    )
    assert msg.sent == [expected]


def test_text_handler_sends_image(monkeypatch):
    """Binary attachments with image content type should be sent as photos."""

    async def fake_rag_answer(question, project=None, session_id=None):
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

    msg = FakeMessage("show license")
    asyncio.run(bot_mod.text_handler(msg, project="demo", session_id="abc"))

    assert msg.documents == []
    assert len(msg.photos) == 1
    photo, kwargs = msg.photos[0]
    assert hasattr(photo, "__class__")
    assert kwargs.get("caption") == "Фото лицензии"
