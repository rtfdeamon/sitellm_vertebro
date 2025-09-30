"""Shared defaults for the knowledge processing service."""

from __future__ import annotations

DEFAULT_MODE = "manual"
ALLOWED_MODES = {"auto", "manual"}
DEFAULT_PROCESSING_PROMPT = (
    "Ты — сервис интеллектуальной обработки базы знаний. "
    "Обрабатывай документы последовательно, разбивая каждый документ на части, "
    "которые помещаются в контекст модели. "
    "Для каждой части выполняй необходимые преобразования и обновляй содержимое "
    "по частям, чтобы итоговые изменения оставались согласованными."
)
MANUAL_MODE_MESSAGE = "Ручной режим: используйте команду запуска."
