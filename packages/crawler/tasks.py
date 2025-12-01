"""Celery‑задачи управления краулером."""

from __future__ import annotations

from uuid import uuid4
from typing import Optional

import structlog

from apps.worker.main import celery
from packages.backend.crawler_reporting import Reporter, CrawlerProgress
from .run_crawl import run, DEFAULT_MAX_PAGES, DEFAULT_MAX_DEPTH, DEFAULT_MONGO_URI


logger = structlog.get_logger(__name__)


@celery.task(name="crawler.start_crawl")
def start_crawl(
    url: str,
    *,
    max_pages: int = DEFAULT_MAX_PAGES,
    max_depth: int = DEFAULT_MAX_DEPTH,
    domain: str | None = None,
    project: str | None = None,
    mongo_uri: str = DEFAULT_MONGO_URI,
    job_id: Optional[str] = None,
    collect_medex: Optional[bool] = None,
    collect_books: Optional[bool] = None,
) -> str:
    """Run the crawler asynchronously and report progress."""
    job_id = job_id or str(uuid4())
    reporter = Reporter()
    progress = CrawlerProgress(job_id=job_id, project=project)
    reporter.update(progress)

    def on_progress(page_url: str, counters: dict[str, int] | None = None) -> None:
        progress.fetched += 1
        progress.last_url = page_url
        if counters:
            progress.queued = counters.get("queued", progress.queued)
            progress.errors = counters.get("failed", progress.errors)
            progress.remaining = counters.get("remaining", progress.queued)
        reporter.update(progress)

    run(
        url,
        max_pages=max_pages,
        max_depth=max_depth,
        domain=domain,
        project_name=project,
        mongo_uri=mongo_uri,
        progress_callback=on_progress,
        collect_medex=collect_medex,
        collect_books=collect_books,
    )

    try:
        from worker import update_vector_store as refresh_vectors

        refresh_vectors()
    except Exception as exc:  # noqa: BLE001
        logger.warning("vector_store_refresh_failed", error=str(exc))

    progress.done = True
    progress.remaining = 0
    reporter.update(progress)
    return job_id
