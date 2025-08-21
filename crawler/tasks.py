"""Celery‑задачи управления краулером."""

from __future__ import annotations

from uuid import uuid4
from typing import Optional

from worker import celery
from backend.crawler_reporting import Reporter, CrawlerProgress
from .run_crawl import run, DEFAULT_MAX_PAGES, DEFAULT_MAX_DEPTH, DEFAULT_MONGO_URI


@celery.task(name="crawler.start_crawl")
def start_crawl(
    url: str,
    *,
    max_pages: int = DEFAULT_MAX_PAGES,
    max_depth: int = DEFAULT_MAX_DEPTH,
    domain: str | None = None,
    mongo_uri: str = DEFAULT_MONGO_URI,
    job_id: Optional[str] = None,
) -> str:
    """Run the crawler asynchronously and report progress."""
    job_id = job_id or str(uuid4())
    reporter = Reporter()
    progress = CrawlerProgress(job_id=job_id)
    reporter.update(progress)

    def on_progress(page_url: str) -> None:
        progress.fetched += 1
        progress.last_url = page_url
        reporter.update(progress)

    run(
        url,
        max_pages=max_pages,
        max_depth=max_depth,
        domain=domain,
        mongo_uri=mongo_uri,
        progress_callback=on_progress,
    )

    progress.done = True
    reporter.update(progress)
    return job_id
