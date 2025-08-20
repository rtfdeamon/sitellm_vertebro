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
sys.modules["aiogram.types"] = fake_types

pkg = types.ModuleType("tg_bot")
pkg.__path__ = [str(Path(__file__).resolve().parents[2] / "tg_bot")]
sys.modules["tg_bot"] = pkg
fake_config = types.ModuleType("tg_bot.config")
fake_config.get_settings = lambda: types.SimpleNamespace(
    api_base_url="http://api", request_timeout=10
)
sys.modules["tg_bot.config"] = fake_config
fake_client = types.ModuleType("tg_bot.client")
fake_client.rag_answer = lambda text: "ok"
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
        self.chat = types.SimpleNamespace(do=lambda action: asyncio.sleep(0))

    async def answer(self, text, **kwargs):
        self.sent.append(text)


def test_unknown_command():
    """Handler should reply with unknown message."""
    msg = FakeMessage("/unknown")
    asyncio.run(bot_mod.unknown_handler(msg))
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

        async def get(self, url):
            calls["url"] = url
            return FakeResp()

    fake_httpx.AsyncClient = lambda timeout=None: FakeClient()
    bot_mod.get_settings = lambda: types.SimpleNamespace(
        api_base_url="http://api", request_timeout=1
    )
    msg = FakeMessage("/status")
    asyncio.run(bot_mod.status_handler(msg))
    assert calls["url"] == "http://api/status"
    expected = (
        "<b>DB</b>\n"
        "• users: 1\n"
        "• qdrant_points: 2\n\n"
        "<b>Crawler</b>\n"
        "• main: queued=1 fetched=2 parsed=3 indexed=4 errors=0"
    )
    assert msg.sent == [expected]
