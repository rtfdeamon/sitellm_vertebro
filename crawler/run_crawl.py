#!/usr/bin/env python
"""Minimal async crawler used for initial content collection.

This module intentionally keeps the public functions small and well-defined to
make testing straightforward:

- ``fetch(url)`` – synchronous fetch helper used in unit tests to verify
  content-type handling for non-HTML resources.
- ``crawl(...)`` – asynchronous BFS crawler that yields ``(url, html, ctype)``.

The CLI entry point remains lightweight and is not exercised by tests.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
import urllib.parse as urlparse
from typing import AsyncIterator, Callable, Iterable, List, Optional, Set, Tuple

import httpx
import requests
from bs4 import BeautifulSoup
from contextlib import contextmanager
from pymongo import MongoClient, UpdateOne
from redis import Redis
import structlog
from urllib import robotparser
import xml.etree.ElementTree as ET

from observability.logging import configure_logging


configure_logging()
logger = structlog.get_logger(__name__)

# ----------------------------- Константы ----------------------------- #
DEFAULT_MAX_PAGES: int = int(os.getenv("CRAWL_MAX_PAGES", "500"))
DEFAULT_MAX_DEPTH: int = int(os.getenv("CRAWL_MAX_DEPTH", "3"))
DEFAULT_START_URL: str | None = os.getenv("CRAWL_START_URL")
DEFAULT_MONGO_URI: str = os.getenv(
    "MONGO_URI", "mongodb://root:changeme@mongo:27017"
)
DEFAULT_SITEMAP_URL: str | None = os.getenv("CRAWL_SITEMAP_URL")
DEFAULT_IGNORE_ROBOTS: bool = os.getenv("CRAWL_IGNORE_ROBOTS", "0") == "1"
REDIS_PREFIX = os.getenv("STATUS_PREFIX", "crawl:")
_redis_url = os.getenv("REDIS_URL")
if _redis_url:
    r = Redis.from_url(_redis_url, decode_responses=True)
else:
    r = Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD") or None,
        decode_responses=True,
    )

def _incr(key: str, delta: int = 1):
    try:
        r.incrby(REDIS_PREFIX + key, delta)
    except Exception:
        pass

def _set(key: str, value):
    try:
        r.set(REDIS_PREFIX + key, value)
    except Exception:
        pass

def _push_recent(url: str, limit: int = 20) -> None:
    try:
        key = REDIS_PREFIX + "recent_urls"
        r.lpush(key, url)
        r.ltrim(key, 0, limit - 1)
    except Exception:
        pass

def on_crawler_start():
    _set("started_at", time.time())


def reset_counters() -> None:
    """Reset queue counters before a new crawl run starts."""

    for key in ("queued", "in_progress", "done", "failed"):
        _set(key, 0)
    try:
        r.delete(REDIS_PREFIX + "recent_urls")
    except Exception:
        pass

@contextmanager
def mark_url(url: str):
    _incr("in_progress", 1)
    _incr("queued", -1)

    _set("last_url", url)
    try:
        yield
        _incr("done", 1)
    except Exception:
        _incr("failed", 1)
        raise
    finally:
        _incr("in_progress", -1)
        _push_recent(url)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; SiteLLM-VertebroCrawler/1.0; +https://example.com)"
    )
}
REQUEST_TIMEOUT = float(os.getenv("CRAWL_TIMEOUT", "10"))  # seconds
BATCH_SIZE = 50  # сколько документов пушим в Mongo за раз

# ------------------------- Вспомогательные функции ------------------- #

def fetch(url: str) -> Tuple[str | None, str | None]:
    """Synchronously fetch a URL and return ``(html, content_type)``.

    Non-HTML responses are skipped and logged with their ``content_type``.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        ctype = resp.headers.get("content-type", "")
        main_type = ctype.split(";")[0].strip().lower()
        if main_type != "text/html":
            logger.info("skip non-html", url=url, content_type=ctype)
            return None, ctype
        # ``requests`` uses ``text`` for decoded body
        return resp.text, ctype
    except Exception as exc:  # pragma: no cover - error path is logged
        logger.warning("fetch failed", url=url, error=str(exc))
        return None, None


def extract_links(html: str, base_url: str) -> List[str]:
    """Вытаскивает все <a href="..."> и приводит к абсолютному URL."""
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href: str = a["href"]
        abs_url: str = urlparse.urljoin(base_url, href)
        # убираем якоря, query‑параметры можно оставить
        abs_url = abs_url.split("#")[0]
        if abs_url.startswith("http"):
            links.append(abs_url)
    return links


async def crawl(
    start_url: str,
    *,
    max_pages: int = DEFAULT_MAX_PAGES,
    max_depth: int = DEFAULT_MAX_DEPTH,
    allowed_domain: Optional[str] = None,
    client_factory: Optional[Callable[[], httpx.AsyncClient]] = None,
    concurrency: int = 5,
) -> AsyncIterator[Tuple[str, str, str]]:
    """Asynchronously crawl a site in BFS order.

    Yields tuples ``(url, html, content_type)`` for HTML pages only.
    Accepts an optional ``client_factory`` for tests to inject a custom
    ``httpx.AsyncClient`` (e.g., with ``MockTransport``).
    """

    visited: Set[str] = set()
    url_queue: asyncio.Queue[Tuple[str, int]] = asyncio.Queue()
    result_queue: asyncio.Queue[Tuple[str, str, str]] = asyncio.Queue()
    visited_lock = asyncio.Lock()

    reset_counters()
    on_crawler_start()

    await url_queue.put((start_url, 0))
    _incr("queued", 1)

    async def _fetch_async(client: httpx.AsyncClient, url: str) -> Tuple[str | None, str | None]:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "")
            main_type = ctype.split(";")[0].strip().lower()
            if main_type != "text/html":
                logger.info("skip non-html", url=url, content_type=ctype)
                return None, ctype
            return resp.text, ctype
        except Exception as exc:  # pragma: no cover - error path
            logger.warning("fetch failed", url=url, error=str(exc))
            return None, None

    async def _worker(client: httpx.AsyncClient) -> None:
        while True:
            url, depth = await url_queue.get()
            async with visited_lock:
                if url in visited or depth > max_depth or len(visited) >= max_pages:
                    url_queue.task_done()
                    continue
                visited.add(url)
            with mark_url(url):
                html, ctype = await _fetch_async(client, url)
            if html:
                logger.info("page fetched", url=url, depth=depth, content_length=len(html))
                await result_queue.put((url, html, ctype))
                if not allowed_domain or urlparse.urlparse(url).netloc == allowed_domain:
                    for link in extract_links(html, url):
                        async with visited_lock:
                            if link not in visited:
                                await url_queue.put((link, depth + 1))
                                _incr("queued", 1)
            else:
                logger.info("page skipped", url=url, reason="non_html_or_error")
            url_queue.task_done()

    # Create client
    if client_factory is None:
        context = httpx.AsyncClient(headers=HEADERS, timeout=REQUEST_TIMEOUT)
        created_client = True
    else:
        context = client_factory()
        created_client = True  # ensure context is closed via async context manager

    async with context as client:
        workers = [asyncio.create_task(_worker(client)) for _ in range(concurrency)]

        pages = 0
        try:
            while pages < max_pages:
                try:
                    item = await asyncio.wait_for(result_queue.get(), timeout=1)
                except asyncio.TimeoutError:
                    if url_queue.empty():
                        break
                    continue
                url, html, ctype = item
                pages += 1
                yield url, html, ctype
        finally:
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

# ------------------------------ main --------------------------------- #

def main() -> None:  # pragma: no cover - convenience CLI
    parser = argparse.ArgumentParser(description="Simple async site crawler")
    parser.add_argument("--url", default=DEFAULT_START_URL, help="Start URL to crawl")
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    parser.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    args = parser.parse_args()

    if not args.url:
        sys.exit("❌ Need --url or set CRAWL_START_URL")

    async def _run() -> None:
        count = 0
        async for _ in crawl(args.url, max_pages=args.max_pages, max_depth=args.max_depth):
            count += 1
        logger.info("crawl complete", pages=count)

    asyncio.run(_run())


if __name__ == "__main__":  # pragma: no cover
    main()
