"""Build metadata helpers shared between API endpoints and UI."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


def _coerce_timestamp(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if value <= 0:
            return None
        return float(value)
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return None
        try:
            numeric = float(trimmed)
            if numeric <= 0:
                return None
            return numeric
        except ValueError:
            normalized = trimmed.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(normalized)
                return dt.replace(tzinfo=dt.tzinfo or timezone.utc).timestamp()
            except ValueError:
                try:
                    parsed = datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S")
                    return parsed.replace(tzinfo=timezone.utc).timestamp()
                except ValueError:
                    return None
    return None


def _normalize_component_info(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    version = raw.get("version")
    revision = raw.get("hash") or raw.get("commit")
    info: dict[str, Any] = {}
    if version is not None:
        info["version"] = str(version)
    if revision:
        info["revision"] = str(revision)
    return info


@lru_cache(maxsize=1)
def get_build_info() -> Dict[str, Any]:
    """Return cached build metadata (version, revision, timestamp)."""

    root = Path(__file__).resolve().parent.parent
    versions_path = root / "versions.json"

    version = os.getenv("APP_BUILD_VERSION") or os.getenv("BUILD_VERSION")
    revision = (
        os.getenv("APP_BUILD_COMMIT")
        or os.getenv("BUILD_COMMIT")
        or os.getenv("GIT_COMMIT")
    )
    built_at = _coerce_timestamp(
        os.getenv("APP_BUILD_TS")
        or os.getenv("APP_BUILD_TIME")
        or os.getenv("BUILD_TIMESTAMP")
        or os.getenv("BUILD_TIME")
    )

    versions_payload: dict[str, Any] | None = None
    if versions_path.exists():
        try:
            versions_payload = json.loads(versions_path.read_text(encoding="utf-8"))
        except Exception:
            versions_payload = None

    components: dict[str, Any] = {}
    if isinstance(versions_payload, dict):
        for name, meta in versions_payload.items():
            normalized = _normalize_component_info(meta if isinstance(meta, dict) else None)
            if normalized:
                components[name] = normalized
        backend_meta = components.get("backend")
        if backend_meta:
            version = version or backend_meta.get("version")
            revision = revision or backend_meta.get("revision")

    if not version:
        version = "unknown"

    if versions_path.exists() and built_at is None:
        built_at = float(versions_path.stat().st_mtime)
    if built_at is None:
        built_at = float(root.stat().st_mtime)

    built_at_iso = None
    if built_at:
        built_at_iso = (
            datetime.fromtimestamp(built_at, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )

    build_info: Dict[str, Any] = {
        "version": str(version) if version is not None else "unknown",
        "revision": str(revision) if revision else None,
        "built_at": built_at,
        "built_at_iso": built_at_iso,
    }
    if components:
        build_info["components"] = components
    if versions_payload is not None:
        build_info["versions"] = versions_payload

    return build_info

