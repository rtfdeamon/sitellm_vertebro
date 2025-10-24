"""Crawler management service extracted from api.py."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import urllib.parse as urlparse
from pathlib import Path
from typing import Any, Callable

import structlog
from fastapi import BackgroundTasks, HTTPException
from starlette.requests import Request

from models import Project

logger = structlog.get_logger(__name__)


class CrawlerService:
    """Encapsulate crawler orchestration logic."""

    def __init__(
        self,
        *,
        normalize_project: Callable[[str | None], str | None],
        mongo_uri: str | None,
        status_provider: Callable[[str | None], dict[str, Any]],
        note_provider: Callable[[str | None], Any],
        clear_state: Callable[[str | None], int],
        deduplicate_urls: Callable[[str | None], int],
    ) -> None:
        self._normalize_project = normalize_project
        self._mongo_uri = mongo_uri
        self._status_provider = status_provider
        self._note_provider = note_provider
        self._clear_state = clear_state
        self._deduplicate_urls = deduplicate_urls

    def _spawn_crawler(
        self,
        start_url: str,
        max_pages: int,
        max_depth: int,
        *,
        project: str | None,
        domain: str | None,
        collect_medex: bool | None,
        collect_books: bool | None,
    ) -> None:
        base_dir = Path(__file__).resolve().parents[2]
        script = base_dir / "crawler" / "run_crawl.py"
        cmd = [
            sys.executable,
            str(script),
            "--url",
            start_url,
            "--max-pages",
            str(max_pages),
            "--max-depth",
            str(max_depth),
        ]
        if project:
            cmd.extend(["--project", project])
        if domain:
            cmd.extend(["--domain", domain])
        if self._mongo_uri:
            cmd.extend(["--mongo-uri", self._mongo_uri])
        if collect_medex is True:
            cmd.append("--collect-medex")
        elif collect_medex is False:
            cmd.append("--no-collect-medex")
        if collect_books is True:
            cmd.append("--collect-books")
        elif collect_books is False:
            cmd.append("--no-collect-books")

        env = os.environ.copy()
        python_paths = [str(base_dir)]
        existing_py_path = env.get("PYTHONPATH")
        if existing_py_path:
            python_paths.append(existing_py_path)
        env["PYTHONPATH"] = os.pathsep.join(python_paths)
        proc = subprocess.Popen(cmd, cwd=str(base_dir), env=env)
        try:
            (Path("/tmp") / "crawler.pid").write_text(str(proc.pid), encoding="utf-8")
        except Exception:  # pragma: no cover - best effort
            pass

    async def queue_run(self, request: Request, payload: Any, background_tasks: BackgroundTasks) -> dict[str, str]:
        parsed_host = urlparse.urlsplit(payload.start_url).netloc
        allowed_domain = (payload.domain or parsed_host or "").lower()
        project_name = self._normalize_project(payload.project) or self._normalize_project(allowed_domain)
        if not project_name:
            raise HTTPException(status_code=400, detail="project is required")

        project = await request.state.mongo.get_project(project_name)
        if project is None:
            await request.state.mongo.upsert_project(
                Project(name=project_name, domain=allowed_domain or None)
            )

        background_tasks.add_task(
            self._spawn_crawler,
            payload.start_url,
            payload.max_pages,
            payload.max_depth,
            project=project_name,
            domain=allowed_domain or None,
            collect_medex=payload.collect_medex,
            collect_books=payload.collect_books,
        )
        return {
            "status": "started",
            "project": project_name,
            "domain": allowed_domain or None,
        }

    def status(self, project: str | None) -> dict[str, Any]:
        project_label = self._normalize_project(project)
        data = self._status_provider(project_label)
        crawler = data.get("crawler") or {}
        note = self._note_provider(project_label)
        if note:
            data["notes"] = note
        data.update(
            {
                "queued": crawler.get("queued", 0),
                "in_progress": crawler.get("in_progress", 0),
                "done": crawler.get("done", 0),
                "failed": crawler.get("failed", 0),
                "remaining": crawler.get("remaining", max(0, crawler.get("queued", 0) + crawler.get("in_progress", 0))),
                "recent_urls": crawler.get("recent_urls") or [],
                "last_url": crawler.get("last_url"),
            }
        )
        logger.info(
            "crawler_status_snapshot",
            project=project_label,
            ok=data.get("ok"),
            queued=data.get("queued"),
            in_progress=data.get("in_progress"),
            done=data.get("done"),
            failed=data.get("failed"),
            remaining=data.get("remaining"),
            last_url=data.get("last_url"),
            notes=data.get("notes"),
        )
        return data

    def reset(self, project: str | None) -> dict[str, Any]:
        project_label = self._normalize_project(project)
        removed = self._clear_state(project_label)
        return {"status": "reset", "project": project_label, "purged_jobs": removed}

    def deduplicate(self, project: str | None) -> dict[str, Any]:
        project_label = self._normalize_project(project)
        removed = self._deduplicate_urls(project_label)
        return {"status": "deduplicated", "removed": removed, "project": project_label}

    def stop(self) -> dict[str, str | int]:
        pid_path = Path("/tmp") / "crawler.pid"
        try:
            pid = int(pid_path.read_text(encoding="utf-8").strip())
        except Exception:
            return {"status": "unknown"}
        try:
            os.kill(pid, signal.SIGTERM)
            return {"status": "stopping", "pid": pid}
        except ProcessLookupError:
            return {"status": "not_running"}
        except Exception:
            return {"status": "error"}
