"""Background service that processes the knowledge base on queue idle periods."""

from __future__ import annotations

import asyncio
import signal
import time
from dataclasses import dataclass
from typing import Any, Dict

import structlog

from packages.core.status import status_dict
from packages.core.mongo import MongoClient
from packages.core.settings import Settings
from apps.worker.main import update_vector_store
from .configuration import (
    DEFAULT_MODE,
    ALLOWED_MODES,
    DEFAULT_PROCESSING_PROMPT,
    MANUAL_MODE_MESSAGE,
)


logger = structlog.get_logger(__name__)


SETTINGS_KEY = "knowledge_service"
DEFAULT_IDLE_THRESHOLD_SECONDS = 300
DEFAULT_POLL_INTERVAL_SECONDS = 60
DEFAULT_COOLDOWN_SECONDS = 900


@dataclass(slots=True)
class ServiceConfig:
    """Runtime configuration for the knowledge processing service."""

    enabled: bool
    idle_threshold_seconds: int
    poll_interval_seconds: int
    cooldown_seconds: int
    mode: str
    processing_prompt: str
    metadata: Dict[str, Any]


class KnowledgeProcessingService:
    """Monitor crawler queues and update the knowledge base when idle."""

    def __init__(self) -> None:
        self._settings = Settings()
        mongo_cfg = self._settings.mongo
        self._mongo = MongoClient(
            mongo_cfg.host,
            mongo_cfg.port,
            mongo_cfg.username,
            mongo_cfg.password,
            mongo_cfg.database,
            mongo_cfg.auth,
        )
        self._stop = asyncio.Event()
        self._last_activity = time.time()
        self._last_run = 0.0
        self._loop = asyncio.get_event_loop()

    async def run(self) -> None:
        """Run the monitoring loop until cancelled."""

        self._register_signal_handlers()
        await self._merge_setting({"running": True, "last_seen_ts": time.time(), "message": "Сервис запущен"})
        try:
            while not self._stop.is_set():
                config = await self._load_config()
                now = time.time()

                if not config.enabled:
                    self._last_activity = now
                    await self._merge_setting(
                        {
                            "running": True,
                            "enabled": False,
                            "mode": config.mode,
                            "last_seen_ts": now,
                            "message": "Сервис выключен",
                        }
                    )
                    await self._wait(config.poll_interval_seconds)
                    continue

                queued = await asyncio.to_thread(self._read_queue_depth)
                idle_duration = max(0.0, now - self._last_activity) if queued == 0 else 0.0

                status_update = {
                    "running": True,
                    "enabled": True,
                    "last_queue": queued,
                    "idle_seconds": idle_duration,
                    "last_seen_ts": now,
                    "mode": config.mode,
                }

                if queued > 0:
                    self._last_activity = now

                if config.mode != "auto":
                    if config.metadata.get("last_reason") != "manual":
                        status_update["message"] = MANUAL_MODE_MESSAGE
                    await self._merge_setting(status_update)
                    await self._wait(config.poll_interval_seconds)
                    continue

                should_trigger = False
                if queued > 0:
                    status_update["message"] = f"Очередь активна ({queued}) — ждём простоя"
                else:
                    threshold = config.idle_threshold_seconds
                    cooldown = max(config.cooldown_seconds, threshold)
                    if now - self._last_run >= cooldown and idle_duration >= threshold:
                        should_trigger = True
                    else:
                        remaining = max(0, threshold - int(idle_duration))
                        status_update["message"] = (
                            f"Очередь пуста {int(idle_duration)} с — ждём {remaining} с до запуска"
                        )

                if should_trigger:
                    logger.info(
                        "knowledge_processing_trigger",
                        idle_seconds=idle_duration,
                        queue=queued,
                    )
                    await self._merge_setting(
                        {
                            **status_update,
                            "last_reason": "queue_idle",
                            "message": "Интеллектуальная обработка: запускаем обновление",
                            "manual_reason": None,
                        }
                    )
                    error_text = await self._run_processing()
                    now = time.time()
                    self._last_run = now
                    self._last_activity = now
                    if error_text:
                        completion_msg = f"Интеллектуальная обработка завершена с ошибкой: {error_text}"
                    else:
                        completion_msg = "Интеллектуальная обработка завершена успешно"
                    status_update.update(
                        {
                            "last_run_ts": now,
                            "last_reason": "queue_idle",
                            "idle_seconds": 0.0,
                            "last_error": error_text,
                            "message": completion_msg,
                            "manual_reason": None,
                        }
                    )

                await self._merge_setting(status_update)
                await self._wait(config.poll_interval_seconds)
        finally:
            await self._merge_setting({"running": False, "last_seen_ts": time.time(), "message": "Сервис остановлен"})
            await self._mongo.close()

    def stop(self) -> None:
        """Signal the loop to stop."""

        self._stop.set()

    def _register_signal_handlers(self) -> None:
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                self._loop.add_signal_handler(sig, self.stop)
            except NotImplementedError:  # pragma: no cover - Windows fallback
                signal.signal(sig, lambda *_: self.stop())

    async def _wait(self, duration: int) -> None:
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=max(5, duration))
        except asyncio.TimeoutError:
            return

    async def _load_config(self) -> ServiceConfig:
        doc = await self._mongo.get_setting(SETTINGS_KEY) or {}
        enabled = bool(doc.get("enabled", False))
        idle_threshold = int(doc.get("idle_threshold_seconds") or DEFAULT_IDLE_THRESHOLD_SECONDS)
        poll_interval = int(doc.get("poll_interval_seconds") or DEFAULT_POLL_INTERVAL_SECONDS)
        cooldown = int(doc.get("cooldown_seconds") or DEFAULT_COOLDOWN_SECONDS)
        raw_mode = str(doc.get("mode") or "").strip().lower()
        if raw_mode not in ALLOWED_MODES:
            raw_mode = "auto" if enabled else DEFAULT_MODE
        prompt_value = doc.get("processing_prompt")
        if not isinstance(prompt_value, str) or not prompt_value.strip():
            prompt_value = DEFAULT_PROCESSING_PROMPT
        else:
            prompt_value = prompt_value.strip()
        return ServiceConfig(
            enabled=enabled,
            idle_threshold_seconds=max(60, idle_threshold),
            poll_interval_seconds=max(15, poll_interval),
            cooldown_seconds=max(60, cooldown),
            mode=raw_mode,
            processing_prompt=prompt_value,
            metadata=doc,
        )

    async def _merge_setting(self, updates: Dict[str, Any]) -> None:
        doc = await self._mongo.get_setting(SETTINGS_KEY) or {}
        doc.update(updates)
        await self._mongo.set_setting(SETTINGS_KEY, doc)

    def _read_queue_depth(self) -> int:
        status = status_dict()
        try:
            crawler = status.get("crawler", {})
            return int(crawler.get("queued", 0))
        except Exception:  # pragma: no cover - defensive
            return 0

    async def _run_processing(self) -> str | None:
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, update_vector_store)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.exception("knowledge_processing_failed", error=str(exc))
            return str(exc)


def main() -> None:
    """Entry point for the standalone service."""

    service = KnowledgeProcessingService()
    try:
        asyncio.run(service.run())
    except KeyboardInterrupt:  # pragma: no cover - graceful shutdown
        pass


if __name__ == "__main__":  # pragma: no cover - module execution
    main()
