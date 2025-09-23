"""Helper utilities for interacting with the local Ollama runtime."""

from __future__ import annotations

import json
import math
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

POPULAR_MODELS: list[dict[str, Any]] = [
    {"name": "yandex/YandexGPT-5-Lite-8B-instruct-GGUF:latest", "size_gb": 4.5},
    {"name": "mistral:7b", "size_gb": 4.1},
    {"name": "llama3.1:8b", "size_gb": 4.9},
    {"name": "qwen2.5:14b", "size_gb": 8.6},
    {"name": "phi3:mini", "size_gb": 2.7},
]


@dataclass(slots=True)
class OllamaModel:
    """Metadata about an installed Ollama model."""

    name: str
    size_bytes: int
    size_human: str
    modified_at: str | None = None
    digest: str | None = None


def _to_human_size(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    step = int(math.log(size_bytes, 1024))
    step = max(0, min(step, len(units) - 1))
    value = size_bytes / (1024**step)
    return f"{value:.1f} {units[step]}"


def _parse_size(value: str | int | float | None) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    raw = str(value).strip().lower()
    if not raw:
        return 0
    multipliers = {
        "kb": 1024,
        "mb": 1024**2,
        "gb": 1024**3,
        "tb": 1024**4,
    }
    parts = raw.split()
    if len(parts) == 2:
        try:
            number = float(parts[0].replace(",", "."))
        except ValueError:
            return 0
        unit = parts[1].strip().lower()
        factor = multipliers.get(unit, 1)
        return int(number * factor)
    try:
        return int(float(raw))
    except ValueError:
        return 0


def ollama_available() -> bool:
    return shutil.which("ollama") is not None


def list_installed_models() -> list[OllamaModel]:
    if not ollama_available():
        return []

    try:
        proc = subprocess.run(
            ["ollama", "list", "--json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return []

    output = (proc.stdout or "").strip()
    if not output:
        return []

    models: list[OllamaModel] = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        payload: dict[str, Any] | None = None
        if line.startswith("{") and line.endswith("}"):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                payload = None
        if payload is None:
            # fallback for tabtable output, expect columns: name size modified
            parts = [part for part in line.split() if part]
            if not parts:
                continue
            name = parts[0]
            size = _parse_size(parts[1]) if len(parts) > 1 else 0
            models.append(
                OllamaModel(
                    name=name,
                    size_bytes=size,
                    size_human=_to_human_size(size),
                    modified_at=None,
                )
            )
            continue
        name = str(payload.get("name") or payload.get("model") or "").strip()
        if not name:
            continue
        size_bytes = _parse_size(payload.get("size"))
        models.append(
            OllamaModel(
                name=name,
                size_bytes=size_bytes,
                size_human=_to_human_size(size_bytes),
                modified_at=payload.get("modified_at"),
                digest=payload.get("digest"),
            )
        )
    return models


def installed_model_names() -> list[str]:
    return [model.name for model in list_installed_models()]


def popular_models_with_size() -> list[dict[str, Any]]:
    """Return a copy of the curated popular models list."""

    items: list[dict[str, Any]] = []
    for entry in POPULAR_MODELS:
        name = str(entry.get("name") or "").strip()
        if not name:
            continue
        size_gb = float(entry.get("size_gb") or 0)
        items.append(
            {
                "name": name,
                "size_gb": round(size_gb, 2) if size_gb else None,
                "approx_size_human": f"{size_gb:.1f} GB" if size_gb else None,
            }
        )
    return items
