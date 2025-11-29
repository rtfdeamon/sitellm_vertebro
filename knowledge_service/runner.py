import time
import asyncio
from typing import Any, Dict

import structlog
from mongo import MongoClient
from worker import update_vector_store
from .configuration import (
    DEFAULT_MODE,
    ALLOWED_MODES,
    DEFAULT_PROCESSING_PROMPT,
    KEY as SETTINGS_KEY,
)

logger = structlog.get_logger(__name__)

class KnowledgeServiceRunner:
    """Runner for manual or API-triggered knowledge service execution."""

    def __init__(self, mongo: MongoClient) -> None:
        self._mongo = mongo

    async def run_once(self, mode_override: str | None = None, force: bool = False) -> Dict[str, Any]:
        """Execute a single processing run."""
        
        doc = await self._mongo.get_setting(SETTINGS_KEY) or {}
        
        # Determine effective mode
        if mode_override:
            mode = mode_override.strip().lower()
        else:
            raw_mode = str(doc.get("mode") or "").strip().lower()
            mode = raw_mode if raw_mode in ALLOWED_MODES else DEFAULT_MODE

        # Check if we should run
        if not force and mode != "auto" and not mode_override:
            return {
                "status": "skipped",
                "reason": "manual_mode_requires_force",
                "mode": mode
            }

        # Update status to running
        await self._merge_setting({
            "running": True,
            "last_seen_ts": time.time(),
            "message": "Запуск обработки по запросу API"
        })

        try:
            # Run processing
            loop = asyncio.get_running_loop()
            try:
                await loop.run_in_executor(None, update_vector_store)
                error_text = None
            except Exception as exc:
                logger.exception("knowledge_processing_failed", error=str(exc))
                error_text = str(exc)

            now = time.time()
            result = {
                "status": "error" if error_text else "success",
                "last_run_ts": now,
                "last_error": error_text,
                "mode": mode,
            }
            
            # Update status
            status_update = {
                "running": False,
                "last_run_ts": now,
                "last_error": error_text,
                "message": f"Обработка завершена: {'Ошибка' if error_text else 'Успешно'}",
                "last_reason": "api_trigger"
            }
            await self._merge_setting(status_update)
            
            return result

        except Exception as exc:
            await self._merge_setting({
                "running": False,
                "message": f"Сбой сервиса: {exc}"
            })
            raise

    async def _merge_setting(self, updates: Dict[str, Any]) -> None:
        doc = await self._mongo.get_setting(SETTINGS_KEY) or {}
        doc.update(updates)
        await self._mongo.set_setting(SETTINGS_KEY, doc)
