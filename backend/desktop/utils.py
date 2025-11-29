"""Desktop widget build utilities."""

import asyncio
import os
from pathlib import Path
from typing import Any

# This assumes the file is in backend/desktop.py, so we go up one level to backend, then up to root
# app.py was in root, so it did Path(__file__).parent / "widget"
# backend/desktop.py is in backend/, so parent is backend, parent.parent is root.
# Wait, app.py: DESKTOP_BUILD_ROOT = (Path(__file__).resolve().parent / "widget" / "desktop").resolve()
# backend/desktop.py: Path(__file__).resolve().parent.parent / "widget" / "desktop"
DESKTOP_BUILD_ROOT = (Path(__file__).resolve().parent.parent / "widget" / "desktop").resolve()

DESKTOP_BUILD_COMMANDS: dict[str, list[str]] = {
    "windows": ["npm", "run", "build:windows"],
    "linux": ["npm", "run", "build:linux"],
}

DESKTOP_BUILD_ARTIFACTS: dict[str, dict[str, Any]] = {
    "windows": {
        "command_key": "windows",
        "patterns": ["dist/*.exe"],
        "content_type": "application/octet-stream",
        "download_name": "SiteLLMAssistant-Setup.exe",
    },
    "linux-appimage": {
        "command_key": "linux",
        "patterns": ["dist/*.AppImage"],
        "content_type": "application/octet-stream",
        "download_name": "SiteLLMAssistant.AppImage",
    },
    "linux-deb": {
        "command_key": "linux",
        "patterns": ["dist/*.deb"],
        "content_type": "application/x-debian-package",
        "download_name": "sitellm-assistant.deb",
    },
}

DESKTOP_BUILD_LOCKS = {key: asyncio.Lock() for key in DESKTOP_BUILD_COMMANDS}


def desktop_latest_source_mtime() -> float:
    """Get the latest modification time of desktop source files."""
    if not DESKTOP_BUILD_ROOT.exists():
        return 0.0
    tracked_files = [
        DESKTOP_BUILD_ROOT / "package.json",
        DESKTOP_BUILD_ROOT / "package-lock.json",
        DESKTOP_BUILD_ROOT / "main.js",
        DESKTOP_BUILD_ROOT / "preload.js",
        DESKTOP_BUILD_ROOT / "config.json",
    ]
    mtimes: list[float] = []
    for path in tracked_files:
        if path.exists():
            try:
                mtimes.append(path.stat().st_mtime)
            except FileNotFoundError:
                continue
    src_dir = DESKTOP_BUILD_ROOT / "src"
    if src_dir.exists():
        for dirpath, _, filenames in os.walk(src_dir):
            base = Path(dirpath)
            for name in filenames:
                file_path = base / name
                try:
                    mtimes.append(file_path.stat().st_mtime)
                except FileNotFoundError:
                    continue
    return max(mtimes) if mtimes else 0.0


def desktop_find_latest_artifact(patterns: list[str]) -> Path | None:
    """Find the latest build artifact matching patterns."""
    if not DESKTOP_BUILD_ROOT.exists():
        return None
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(
            path for path in DESKTOP_BUILD_ROOT.glob(pattern) if path.is_file()
        )
    if not candidates:
        return None
    # Return the most recently modified file
    return max(candidates, key=lambda p: p.stat().st_mtime)


def resolve_command(command: list[str]) -> list[str]:
    """Resolve executable path for command."""
    import shutil

    if not command:
        raise RuntimeError("Desktop build command is empty")
    binary = shutil.which(command[0])
    if binary is None:
        raise RuntimeError(f"Не найден исполняемый файл '{command[0]}' (npm). Установите его на сервере.")
    return [binary, *command[1:]]


def run_desktop_command(command: list[str]) -> None:
    """Run a desktop build command."""
    import subprocess

    resolved = resolve_command(command)
    env = os.environ.copy()
    env.setdefault("NODE_ENV", "production")
    try:
        subprocess.run(
            resolved,
            cwd=DESKTOP_BUILD_ROOT,
            check=True,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:  # noqa: PERF203 - surface build errors
        stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else str(exc)
        raise RuntimeError(stderr.strip() or str(exc)) from exc


def ensure_desktop_dependencies() -> None:
    """Ensure desktop widget dependencies are installed."""
    if not DESKTOP_BUILD_ROOT.exists():
        raise RuntimeError("Каталог widget/desktop не найден в проекте")
    node_modules = DESKTOP_BUILD_ROOT / "node_modules"
    if node_modules.exists():
        return
    run_desktop_command(["npm", "install"])


def prepare_desktop_artifact_blocking(platform_key: str) -> Path:
    """Build desktop artifact synchronously."""
    if platform_key not in DESKTOP_BUILD_ARTIFACTS:
        raise RuntimeError("Unsupported platform")
    meta = DESKTOP_BUILD_ARTIFACTS[platform_key]
    artifact = desktop_find_latest_artifact(meta["patterns"])
    latest_source = desktop_latest_source_mtime()
    if artifact and artifact.stat().st_mtime >= latest_source:
        return artifact
    ensure_desktop_dependencies()
    command_key = meta["command_key"]
    command = DESKTOP_BUILD_COMMANDS.get(command_key)
    if not command:
        raise RuntimeError("Build command is not configured")
    run_desktop_command(command)
    artifact = desktop_find_latest_artifact(meta["patterns"])
    if not artifact:
        raise RuntimeError("Сборка завершилась без артефактов — проверьте журнал electron-builder")
    return artifact
