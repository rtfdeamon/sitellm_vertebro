#!/usr/bin/env python
"""Minimal async crawler used for initial content collection.

This module intentionally keeps the public functions small and well-defined to
make testing straightforward:

- ``fetch(url)`` – synchronous fetch helper used in unit tests to verify
  content-type handling for non-HTML resources.
- ``crawl(...)`` – asynchronous BFS crawler that yields ``(url, payload, ctype, is_html)``.

The CLI entry point remains lightweight and is not exercised by tests.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import os
import re
import sys
import time
import urllib.parse as urlparse
from typing import AsyncIterator, Callable, Iterable, List, Optional, Set, Tuple

import httpx
import requests
from bs4 import BeautifulSoup
from contextlib import contextmanager
from gridfs import GridFS
from pypdf import PdfReader
from pymongo import MongoClient, UpdateOne
from pymongo.errors import ConfigurationError
from redis import Redis
import structlog
from urllib import robotparser
import xml.etree.ElementTree as ET
from bson import ObjectId

from observability.logging import configure_logging
from settings import MongoSettings


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
BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".bmp",
    ".ico",
    ".tiff",
    ".mp3",
    ".mp4",
    ".avi",
    ".mov",
    ".zip",
    ".rar",
    ".7z",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
}
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
    """Synchronously fetch a URL and return ``(text, content_type)``.

    HTML responses return the raw markup; PDF responses are converted to text;
    other content types are skipped and logged with their ``content_type``.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        ctype = resp.headers.get("content-type", "")
        main_type = ctype.split(";")[0].strip().lower()
        if main_type == "application/pdf" or url.lower().endswith(".pdf"):
            text = pdf_to_text(resp.content)
            if text:
                logger.info("pdf extracted", url=url, chars=len(text))
                return text, ctype or "application/pdf"
            logger.info("skip pdf", url=url, reason="no_text")
            return None, ctype or "application/pdf"
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
        if not abs_url.startswith("http"):
            continue
        parsed = urlparse.urlsplit(abs_url)
        path = parsed.path.lower()
        if any(path.endswith(ext) for ext in BINARY_EXTENSIONS):
            continue
        links.append(abs_url)
    return links


def html_to_text(html: str) -> str:
    """Extract readable text from ``html`` removing scripts/styles."""

    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript", "template"]):
        element.decompose()

    text = soup.get_text("\n")
    lines = [line.strip() for line in text.splitlines()]
    # Collapse multiple blank lines and remove empties
    cleaned = "\n".join(line for line in lines if line)
    return cleaned.strip()


def pdf_to_text(data: bytes) -> str:
    """Extract UTF-8 text from PDF ``data`` using :mod:`pypdf`."""

    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:  # pragma: no cover - PDF parsing failure
        logger.warning("pdf_parse_failed", error=str(exc))
        return ""

    chunks: list[str] = []
    for idx, page in enumerate(reader.pages):
        try:
            extracted = page.extract_text() or ""
        except Exception as exc:  # pragma: no cover - page level issues
            logger.warning("pdf_page_extract_failed", page=idx, error=str(exc))
            extracted = ""
        if extracted:
            chunks.append(extracted.strip())

    return "\n\n".join(part for part in chunks if part).strip()


def _filename_from_url(url: str, suffix: str = ".txt") -> str:
    """Return a filesystem-friendly name for ``url`` terminated by ``suffix``."""

    parsed = urlparse.urlsplit(url)
    base = f"{parsed.netloc}{parsed.path}".strip("/") or parsed.netloc or "document"
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base)
    if parsed.query:
        query_suffix = hashlib.sha1(parsed.query.encode("utf-8")).hexdigest()[:10]
        base = f"{base}_{query_suffix}"
    base = base[:80]
    if suffix and not base.endswith(suffix):
        if suffix.endswith(".pdf.txt") and base.endswith(".pdf"):
            base = base[:-4]
        base = f"{base}{suffix}"
    return base


async def crawl(
    start_url: str,
    *,
    max_pages: int = DEFAULT_MAX_PAGES,
    max_depth: int = DEFAULT_MAX_DEPTH,
    allowed_domain: Optional[str] = None,
    client_factory: Optional[Callable[[], httpx.AsyncClient]] = None,
    concurrency: int = 5,
) -> AsyncIterator[Tuple[str, str, str, bool]]:
    """Asynchronously crawl a site in BFS order.

    Yields tuples ``(url, payload, content_type, is_html)`` where ``payload`` is
    the raw HTML for pages or extracted text for supported binary formats
    (currently PDFs). Accepts an optional ``client_factory`` for tests to
    inject a custom ``httpx.AsyncClient`` (e.g., with ``MockTransport``).
    """

    visited: Set[str] = set()
    url_queue: asyncio.Queue[Tuple[str, int]] = asyncio.Queue()
    result_queue: asyncio.Queue[Tuple[str, str, str, bool]] = asyncio.Queue()
    visited_lock = asyncio.Lock()

    reset_counters()
    on_crawler_start()

    await url_queue.put((start_url, 0))
    _incr("queued", 1)

    async def _fetch_async(client: httpx.AsyncClient, url: str) -> Tuple[str | None, str | None, bool]:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "")
            main_type = ctype.split(";")[0].strip().lower()
            if main_type == "application/pdf" or url.lower().endswith(".pdf"):
                text = pdf_to_text(resp.content)
                if text:
                    logger.info("pdf extracted", url=url, chars=len(text))
                    return text, ctype or "application/pdf", False
                logger.info("skip pdf", url=url, reason="no_text")
                return None, ctype or "application/pdf", False
            if main_type != "text/html":
                logger.info("skip non-html", url=url, content_type=ctype)
                return None, ctype, False
            return resp.text, ctype, True
        except Exception as exc:  # pragma: no cover - error path
            logger.warning("fetch failed", url=url, error=str(exc))
            return None, None, False

    async def _worker(client: httpx.AsyncClient) -> None:
        while True:
            url, depth = await url_queue.get()
            async with visited_lock:
                if url in visited or depth > max_depth or len(visited) >= max_pages:
                    url_queue.task_done()
                    continue
                visited.add(url)
            with mark_url(url):
                payload, ctype, is_html = await _fetch_async(client, url)
            if payload:
                logger.info(
                    "page fetched", url=url, depth=depth, content_length=len(payload), content_type=ctype
                )
                await result_queue.put((url, payload, ctype, is_html))
                if is_html and (not allowed_domain or urlparse.urlparse(url).netloc == allowed_domain):
                    for link in extract_links(payload, url):
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
                url, payload, ctype, is_html = item
                pages += 1
                yield url, payload, ctype, is_html
        finally:
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)


def run(
    start_url: str,
    *,
    max_pages: int = DEFAULT_MAX_PAGES,
    max_depth: int = DEFAULT_MAX_DEPTH,
    domain: str | None = None,
    mongo_uri: str = DEFAULT_MONGO_URI,
    progress_callback: Callable[[str], None] | None = None,
    project_name: str | None = None,
) -> None:
    """Synchronous entry point that stores crawled pages as plain text.

    Parameters
    ----------
    project_name:
        Logical project identifier used to label stored documents. Falls back
        to the allowed domain when not provided.
    """

    parsed = urlparse.urlsplit(start_url)
    allowed_domain = domain or parsed.netloc or None
    document_project = (project_name or allowed_domain or MongoSettings().host or "default").lower()
    document_domain = allowed_domain or None

    logger.info(
        "run crawler",
        start_url=start_url,
        max_pages=max_pages,
        max_depth=max_depth,
        allowed_domain=allowed_domain,
        project=document_project,
    )

    mongo_cfg = MongoSettings()
    uri_candidates: list[str] = []
    if mongo_uri:
        uri_candidates.append(mongo_uri)
    from urllib.parse import quote_plus

    def build_uri(user: str | None, pwd: str | None, host: str, port: int, db: str, auth_db: str) -> str:
        auth = ""
        if user and pwd:
            auth = f"{quote_plus(str(user))}:{quote_plus(str(pwd))}@"
        return f"mongodb://{auth}{host}:{port}/{db}?authSource={auth_db}"

    cfg_uri = build_uri(
        mongo_cfg.username,
        mongo_cfg.password,
        mongo_cfg.host,
        mongo_cfg.port,
        mongo_cfg.database,
        mongo_cfg.auth,
    )
    if cfg_uri not in uri_candidates:
        uri_candidates.append(cfg_uri)

    client: MongoClient | None = None
    last_error: Exception | None = None
    for uri in uri_candidates:
        candidate: MongoClient | None = None
        try:
            candidate = MongoClient(uri, serverSelectionTimeoutMS=2000)
            candidate.admin.command("ping")
            client = candidate
            break
        except Exception as exc:  # pragma: no cover - fallback path
            last_error = exc
            if candidate is not None:
                try:
                    candidate.close()
                except Exception:
                    pass
            continue

    if client is None:
        raise RuntimeError("Cannot connect to MongoDB") from last_error

    try:
        logger.info(
            "mongo resolved",
            uri=client.address,
            db=mongo_cfg.database,
            auth_db=mongo_cfg.auth,
        )
        try:
            db = client.get_default_database()
        except ConfigurationError:
            db = client[mongo_cfg.database]

        documents_collection = db[os.getenv("MONGO_DOCUMENTS", "documents")]
        gridfs = GridFS(db)
        try:
            documents_collection.create_index(
                [("domain", 1), ("url", 1)], unique=True, name="domain_url_unique"
            )
        except Exception:
            pass

        try:
            db[os.getenv("MONGO_PROJECTS", "projects")].update_one(
                {"name": document_project},
                {
                    "$setOnInsert": {
                        "name": document_project,
                        "domain": document_domain,
                    }
                },
                upsert=True,
            )
        except Exception:
            logger.warning("project_upsert_failed", project=document_project)

        operations: list[UpdateOne] = []

        async def _store() -> None:
            async for page_url, raw_payload, source_ct, is_html in crawl(
                start_url,
                max_pages=max_pages,
                max_depth=max_depth,
                allowed_domain=allowed_domain,
            ):
                text = html_to_text(raw_payload) if is_html else raw_payload
                if not text:
                    logger.info("empty_page", url=page_url)
                    if progress_callback:
                        progress_callback(page_url)
                    continue

                suffix = ".txt"
                if (source_ct and "pdf" in source_ct.lower()) or page_url.lower().endswith(".pdf"):
                    suffix = ".pdf.txt"
                filename = _filename_from_url(page_url, suffix=suffix)
                description = text.replace("\n", " ").strip()[:200]
                payload_bytes = text.encode("utf-8")

                existing = documents_collection.find_one(
                    {"url": page_url, "project": document_project},
                    {"fileId": 1},
                )
                if existing and existing.get("fileId"):
                    try:
                        gridfs.delete(ObjectId(existing["fileId"]))
                    except Exception:
                        logger.warning("gridfs_delete_failed", file_id=existing["fileId"])

                file_id = gridfs.put(
                    payload_bytes,
                    filename=filename,
                    content_type="text/plain",
                    encoding="utf-8",
                )

                doc: dict[str, object] = {
                    "name": filename,
                    "description": description,
                    "fileId": str(file_id),
                    "url": page_url,
                    "ts": time.time(),
                    "content_type": "text/plain",
                    "domain": document_domain,
                    "project": document_project,
                }
                if source_ct:
                    doc["source_content_type"] = source_ct

                operations.append(
                    UpdateOne(
                        {"url": page_url, "project": document_project},
                        {"$set": doc},
                        upsert=True,
                    )
                )

                if progress_callback:
                    progress_callback(page_url)

                if len(operations) >= BATCH_SIZE:
                    documents_collection.bulk_write(operations, ordered=False)
                    operations.clear()

        asyncio.run(_store())

        if operations:
            documents_collection.bulk_write(operations, ordered=False)

        logger.info("crawler finished")
    finally:
        client.close()

# ------------------------------ main --------------------------------- #

def main() -> None:  # pragma: no cover - convenience CLI
    parser = argparse.ArgumentParser(description="Simple async site crawler")
    parser.add_argument("--url", default=DEFAULT_START_URL, help="Start URL to crawl")
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    parser.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    parser.add_argument("--domain", help="Domain label to store documents under", default=None)
    parser.add_argument("--project", help="Project identifier (lowercase, ASCII)", default=None)
    parser.add_argument("--mongo-uri", default=DEFAULT_MONGO_URI, help="MongoDB connection URI")
    args = parser.parse_args()

    if not args.url:
        sys.exit("❌ Need --url or set CRAWL_START_URL")

    run(
        args.url,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        domain=args.domain or urlparse.urlsplit(args.url).netloc,
        mongo_uri=args.mongo_uri,
        project_name=args.project,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
