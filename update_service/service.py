"""Background service that keeps the repository in sync with a Git remote."""

from __future__ import annotations

import asyncio
import shlex
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import structlog

from mongo import MongoClient
from settings import Settings


logger = structlog.get_logger(__name__)


SETTINGS_KEY = "git_auto_update"
DEFAULT_REMOTE = "origin"
DEFAULT_BRANCH = "main"
DEFAULT_POLL_INTERVAL_SECONDS = 300
DEFAULT_DEPLOY_COMMAND = "./deploy_project.sh"


@dataclass(slots=True)
class GitUpdateConfig:
    """Runtime configuration for the Git auto-update service."""

    enabled: bool
    remote: str
    branch: str
    repo_url: Optional[str]
    repo_path: Path
    poll_interval_seconds: int
    auto_deploy: bool
    deploy_command: Optional[str]


class GitAutoUpdateService:
    """Service that periodically fetches updates from a Git remote and applies them."""

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
        self._loop = asyncio.get_event_loop()

    async def run(self) -> None:
        """Run the monitoring loop until cancelled."""

        self._register_signal_handlers()
        try:
            while not self._stop.is_set():
                result = await self.run_once()
                interval = max(30, int(result.get("poll_interval_seconds") or DEFAULT_POLL_INTERVAL_SECONDS))
                await self._wait(interval)
        finally:
            await self._merge_setting({"running": False, "last_seen_ts": time.time(), "message": "Сервис остановлен"})
            await self.shutdown()

    async def run_once(
        self,
        *,
        force_deploy: bool | None = None,
        force_run: bool = False,
    ) -> Dict[str, Any]:
        """Perform a single update check (optionally forcing deployment)."""

        config = await self._load_config()
        if force_deploy is not None:
            config.auto_deploy = bool(force_deploy)

        now = time.time()
        if not config.enabled and not force_run:
            await self._merge_setting(
                {
                    "enabled": False,
                    "running": True,
                    "last_seen_ts": now,
                    "message": "Автообновление выключено",
                }
            )
            return {
                "enabled": False,
                "running": True,
                "poll_interval_seconds": config.poll_interval_seconds,
            }

        updates = await asyncio.to_thread(self._check_and_update, config)
        updates.update(
            {
                "enabled": config.enabled,
                "running": True,
                "remote": config.remote,
                "branch": config.branch,
                "repo_url": config.repo_url,
                "repo_path": str(config.repo_path),
                "poll_interval_seconds": config.poll_interval_seconds,
                "auto_deploy": config.auto_deploy,
                "deploy_command": config.deploy_command,
                "last_seen_ts": now,
            }
        )
        await self._merge_setting(updates)
        return updates

    def stop(self) -> None:
        """Signal the loop to stop."""

        self._stop.set()

    async def shutdown(self) -> None:
        """Release resources acquired by the service."""

        await self._mongo.close()

    def _register_signal_handlers(self) -> None:
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                self._loop.add_signal_handler(sig, self.stop)
            except NotImplementedError:  # pragma: no cover - Windows fallback
                signal.signal(sig, lambda *_: self.stop())

    async def _wait(self, duration: int) -> None:
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=max(10, duration))
        except asyncio.TimeoutError:
            return

    async def _load_config(self) -> GitUpdateConfig:
        doc = await self._mongo.get_setting(SETTINGS_KEY) or {}
        remote = (doc.get("remote") or DEFAULT_REMOTE).strip() or DEFAULT_REMOTE
        branch = (doc.get("branch") or DEFAULT_BRANCH).strip() or DEFAULT_BRANCH
        repo_url = (doc.get("repo_url") or "").strip() or None
        repo_path_str = (doc.get("repo_path") or "").strip()
        if repo_path_str:
            repo_path = Path(repo_path_str)
        else:
            repo_path = Path(__file__).resolve().parents[1]
        poll = int(doc.get("poll_interval_seconds") or DEFAULT_POLL_INTERVAL_SECONDS)
        auto_deploy = bool(doc.get("auto_deploy", False))
        deploy_command = (doc.get("deploy_command") or DEFAULT_DEPLOY_COMMAND).strip() or None
        enabled = bool(doc.get("enabled", False))

        return GitUpdateConfig(
            enabled=enabled,
            remote=remote,
            branch=branch,
            repo_url=repo_url,
            repo_path=repo_path,
            poll_interval_seconds=max(60, poll),
            auto_deploy=auto_deploy,
            deploy_command=deploy_command,
        )

    async def _merge_setting(self, updates: Dict[str, Any]) -> None:
        doc = await self._mongo.get_setting(SETTINGS_KEY) or {}
        doc.update(updates)
        doc["updated_at"] = time.time()
        await self._mongo.set_setting(SETTINGS_KEY, doc)

    def _check_and_update(self, config: GitUpdateConfig) -> Dict[str, Any]:
        repo_path = config.repo_path
        result: Dict[str, Any] = {
            "update_available": False,
            "last_check_ts": time.time(),
        }

        if not repo_path.exists():
            result.update(
                {
                    "message": f"Путь репозитория не найден: {repo_path}",
                    "last_error": f"missing_repo:{repo_path}",
                }
            )
            return result

        try:
            self._ensure_remote(config)
            self._git(repo_path, "fetch", config.remote, config.branch, "--prune")
        except Exception as exc:  # noqa: BLE001
            logger.warning("git_fetch_failed", error=str(exc))
            result.update(
                {
                    "message": f"Не удалось выполнить git fetch: {exc}",
                    "last_error": str(exc),
                }
            )
            return result

        local_commit = self._safe_git(repo_path, "rev-parse", "HEAD")
        remote_ref = f"{config.remote}/{config.branch}"
        remote_commit = self._safe_git(repo_path, "rev-parse", remote_ref)
        result.update(
            {
                "local_commit": local_commit,
                "remote_commit": remote_commit,
            }
        )

        if not remote_commit:
            result.update(
                {
                    "message": f"Ветка {remote_ref} не найдена на удалённом репозитории",
                    "last_error": "remote_branch_missing",
                }
            )
            return result

        update_needed = local_commit != remote_commit
        result["update_available"] = update_needed

        if not update_needed:
            result.update(
                {
                    "message": "Локальный репозиторий актуален",
                    "last_error": None,
                }
            )
            return result

        if not config.auto_deploy:
            result.update(
                {
                    "message": "Доступно обновление. Запустите обновление вручную.",
                    "last_error": None,
                }
            )
            return result

        try:
            self._git(repo_path, "reset", "--hard", remote_ref)
            self._git(repo_path, "clean", "-fd")
            self._git(repo_path, "submodule", "update", "--init", "--recursive", check=False)
            if config.deploy_command:
                self._run_command(repo_path, config.deploy_command)
            result.update(
                {
                    "message": "Репозиторий обновлён до последней версии",
                    "last_error": None,
                    "update_available": False,
                    "local_commit": remote_commit,
                    "remote_commit": remote_commit,
                    "last_update_ts": time.time(),
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("git_auto_update_failed", error=str(exc))
            result.update(
                {
                    "message": f"Ошибка автообновления: {exc}",
                    "last_error": str(exc),
                    "update_available": True,
                }
            )
        return result

    def _ensure_remote(self, config: GitUpdateConfig) -> None:
        repo_path = config.repo_path
        remote = config.remote
        repo_url = config.repo_url

        existing_url = self._safe_git(repo_path, "remote", "get-url", remote)
        if repo_url:
            if existing_url:
                if existing_url != repo_url:
                    self._git(repo_path, "remote", "set-url", remote, repo_url)
            else:
                self._git(repo_path, "remote", "add", remote, repo_url)
        elif not existing_url:
            # Try to detect origin URL if not provided
            detected = self._safe_git(repo_path, "remote", "get-url", DEFAULT_REMOTE)
            if detected and remote != DEFAULT_REMOTE:
                self._git(repo_path, "remote", "add", remote, detected)

    def _git(self, repo_path: Path, *args: str, check: bool = True) -> str:
        cmd = ["git", *args]
        proc = subprocess.run(
            cmd,
            cwd=repo_path,
            check=check,
            capture_output=True,
            text=True,
        )
        output = proc.stdout.strip()
        if proc.stderr and proc.returncode == 0:
            logger.debug("git", cmd=" ".join(cmd), stderr=proc.stderr.strip())
        return output

    def _safe_git(self, repo_path: Path, *args: str) -> str | None:
        try:
            return self._git(repo_path, *args)
        except subprocess.CalledProcessError as exc:  # noqa: BLE001
            logger.debug("git_command_failed", cmd=" ".join(args), error=str(exc))
            return None

    def _run_command(self, repo_path: Path, command: str) -> None:
        pieces = shlex.split(command)
        proc = subprocess.run(
            pieces,
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "deploy_command_failed")


def main() -> None:
    """Entry point for standalone execution."""

    service = GitAutoUpdateService()
    try:
        asyncio.run(service.run())
    except KeyboardInterrupt:  # pragma: no cover - graceful shutdown
        pass


if __name__ == "__main__":  # pragma: no cover - module execution
    main()
