#!/usr/bin/env python3
"""Update per-component container versions based on source changes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VERSIONS_FILE = REPO_ROOT / "versions.json"


@dataclass(frozen=True)
class Component:
    name: str
    env_var: str
    paths: tuple[str, ...]


COMPONENTS: tuple[Component, ...] = (
    Component(
        name="backend",
        env_var="BACKEND_VERSION",
        paths=(
            "Dockerfile",
            "pyproject.toml",
            "uv.lock",
            "app.py",
            "api.py",
            "worker.py",
            "mongo.py",
            "models.py",
            "settings.py",
            "vectors.py",
            "textnorm.py",
            "knowledge",
            "backend",
            "core",
            "crawler",
            "observability",
            "retrieval",
            "additional",
            "knowledge_service",
        ),
    ),
    Component(
        name="telegram",
        env_var="TELEGRAM_VERSION",
        paths=(
            "docker/Dockerfile.tg_bot",
            "tg_bot",
            "pyproject.toml",
            "uv.lock",
        ),
    ),
)

IGNORE_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", ".ruff_cache"}
IGNORE_SUFFIXES = {".pyc", ".pyo", ".DS_Store"}


def iter_files(paths: Iterable[str]) -> Iterable[Path]:
    for rel in paths:
        path = (REPO_ROOT / rel).resolve()
        if not path.exists():
            continue
        if path.is_file():
            yield path
            continue
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in sorted(dirs) if d not in IGNORE_DIRS]
            for fname in sorted(files):
                if fname in IGNORE_DIRS:
                    continue
                full = Path(root) / fname
                if full.suffix in IGNORE_SUFFIXES:
                    continue
                if not full.is_file():
                    continue
                yield full


def compute_hash(component: Component) -> str:
    digest = hashlib.sha256()
    for file_path in iter_files(component.paths):
        rel = file_path.relative_to(REPO_ROOT)
        digest.update(str(rel).encode("utf-8"))
        with file_path.open("rb") as fh:
            while chunk := fh.read(65536):
                digest.update(chunk)
    return digest.hexdigest()


def load_versions(path: Path) -> dict[str, dict[str, object]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError:
            raise SystemExit(f"[update_versions] Failed to parse JSON from {path}")
    if not isinstance(data, dict):
        raise SystemExit(f"[update_versions] Expected object in {path}")
    return data


def save_versions(path: Path, data: dict[str, dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Update service versions based on source changes")
    parser.add_argument("--versions-file", default=DEFAULT_VERSIONS_FILE, type=Path)
    parser.add_argument("--format", choices={"shell", "json"}, default="shell")
    args = parser.parse_args()

    versions_path: Path = args.versions_file.resolve()
    data = load_versions(versions_path)

    changed_components: list[str] = []
    env_versions: dict[str, int] = {}

    for component in COMPONENTS:
        info = data.get(component.name, {}) if isinstance(data.get(component.name), dict) else {}
        old_hash = str(info.get("hash", "") or "")
        version = int(info.get("version", 1) or 1)

        new_hash = compute_hash(component)
        if not new_hash:
            # No files found; skip but keep previous values
            env_versions[component.env_var] = version
            continue

        if old_hash != new_hash:
            changed_components.append(component.name)
            if old_hash:
                version += 1
            info["hash"] = new_hash
            info["version"] = version
            data[component.name] = info
        else:
            info.setdefault("hash", old_hash)
            info.setdefault("version", version)
            data[component.name] = info

        env_versions[component.env_var] = version

    save_versions(versions_path, data)

    if args.format == "json":
        payload = {
            "versions": env_versions,
            "changed": changed_components,
        }
        json.dump(payload, fp=os.sys.stdout, ensure_ascii=False)
        os.sys.stdout.write("\n")
        return

    # shell format
    for key, value in env_versions.items():
        os.sys.stdout.write(f"{key}={value}\n")
    changed_str = " ".join(changed_components)
    os.sys.stdout.write(f"CHANGED_COMPONENTS=\"{changed_str}\"\n")


if __name__ == "__main__":
    main()
