#!/usr/bin/env python
"""Minimal async crawler used for initial content collection.

This module intentionally keeps the public functions small and well-defined to
make testing straightforward:

- ``fetch(url)`` – synchronous fetch helper used in unit tests to verify
  content-type handling for non-HTML resources.
- ``crawl(...)`` – asynchronous BFS crawler that yields ``(url, payload, ctype, is_html, binary)``.

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
from contextlib import contextmanager, suppress
from gridfs import GridFS
from pypdf import PdfReader
from pymongo import MongoClient, UpdateOne
from pymongo.errors import ConfigurationError
from redis import Redis
import structlog
from urllib import robotparser
import xml.etree.ElementTree as ET
from bson import ObjectId
from PIL import Image

from knowledge.summary import generate_document_summary
from knowledge.text import extract_doc_text, extract_docx_text
from models import Project

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
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
}
DOCX_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-word.document.macroenabled.12",
}
DOC_MIME_TYPES = {
    "application/msword",
    "application/ms-word",
    "application/vnd.ms-word",
    "application/vnd.ms-word.document.macroenabled.12",
}
MAX_IMAGE_DIMENSION = int(os.getenv("CRAWL_IMAGE_MAX_DIM", "1280"))
IMAGE_JPEG_QUALITY = int(os.getenv("CRAWL_IMAGE_JPEG_QUALITY", "85"))
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


def _redis_key(name: str, project: str | None = None) -> str:
    if project:
        return f"{REDIS_PREFIX}{project}:{name}"
    return REDIS_PREFIX + name


def _incr(key: str, delta: int = 1, project: str | None = None):
    try:
        r.incrby(_redis_key(key, project), delta)
    except Exception:
        pass


def _set(key: str, value, project: str | None = None):
    try:
        r.set(_redis_key(key, project), value)
    except Exception:
        pass


def _push_recent(url: str, limit: int = 20, project: str | None = None) -> None:
    try:
        key = _redis_key("recent_urls", project)
        r.lpush(key, url)
        r.ltrim(key, 0, limit - 1)
    except Exception:
        pass

def on_crawler_start(project: str | None = None):
    _set("started_at", time.time(), project)


def reset_counters(project: str | None = None) -> None:
    """Reset queue counters before a new crawl run starts."""

    for key in ("queued", "in_progress", "done", "failed"):
        _set(key, 0, project)
    try:
        r.delete(_redis_key("recent_urls", project))
    except Exception:
        pass

@contextmanager
def mark_url(url: str, project: str | None):
    _incr("in_progress", 1, project)
    _incr("queued", -1, project)

    _set("last_url", url, project)
    try:
        yield
        _incr("done", 1, project)
    except Exception:
        _incr("failed", 1, project)
        raise
    finally:
        _incr("in_progress", -1, project)
        _push_recent(url, project=project)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; SiteLLM-VertebroCrawler/1.0; +https://example.com)"
    )
}
REQUEST_TIMEOUT = float(os.getenv("CRAWL_TIMEOUT", "10"))  # seconds
BATCH_SIZE = 50  # сколько документов пушим в Mongo за раз
PAGE_TIMEOUT = float(os.getenv("CRAWL_PAGE_TIMEOUT", "120"))
_js_render_setting = (os.getenv("CRAWL_JS_RENDER") or "auto").strip().lower()
if _js_render_setting in {"1", "true", "yes", "on"}:
    JS_RENDER_ENABLED = True
elif _js_render_setting in {"0", "false", "no", "off"}:
    JS_RENDER_ENABLED = False
else:  # auto mode
    JS_RENDER_ENABLED = True
JS_RENDER_WAIT = float(os.getenv("CRAWL_JS_WAIT", "2.0"))
JS_RENDER_TIMEOUT = int(float(os.getenv("CRAWL_JS_TIMEOUT", "10")) * 1000)
_playwright_instance = None
_playwright_browser = None
_playwright_context = None
_playwright_lock = None
_playwright_page_lock = None

NAVIGATION_TOKENS = {
    "главная",
    "контакты",
    "наши контакты",
    "личный кабинет",
    "поиск",
    "rss",
    "подписаться",
    "карта сайта",
    "наверх",
    "версия для печати",
    "страница не найдена",
}

RE_CAMEL_CASE = re.compile(r"(?<=[a-zа-яё])(?=[A-ZА-ЯЁ])")
RE_DIGIT_BOUNDARY = re.compile(r"(?<=[0-9])(?=[A-Za-zА-Яа-яЁё])|(?<=[A-Za-zА-Яа-яЁё])(?=[0-9])")

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


def extract_image_links(html: str, base_url: str) -> List[dict[str, str]]:
    """Extract image URLs with optional alt text from ``html``."""

    soup = BeautifulSoup(html, "html.parser")
    result: list[dict[str, str]] = []
    for img in soup.find_all("img", src=True):
        src = (img.get("src") or "").strip()
        if not src or src.startswith("data:"):
            continue
        abs_url = urlparse.urljoin(base_url, src)
        if not abs_url.lower().startswith(("http://", "https://")):
            continue
        alt = (img.get("alt") or img.get("title") or "").strip()
        result.append({"url": abs_url, "alt": alt})
    return result


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


def compress_image(data: bytes) -> tuple[bytes | None, str | None]:
    """Compress binary image data to JPEG suitable for messaging platforms."""

    try:
        image = Image.open(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        logger.debug("image_open_failed", error=str(exc))
        return None, None

    try:
        image = image.convert("RGB")
    except Exception as exc:  # noqa: BLE001
        logger.debug("image_convert_failed", error=str(exc))
        return None, None

    try:
        image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))
    except Exception as exc:  # noqa: BLE001
        logger.debug("image_thumbnail_failed", error=str(exc))
        return None, None

    buffer = io.BytesIO()
    try:
        image.save(buffer, format="JPEG", quality=IMAGE_JPEG_QUALITY, optimize=True)
    except Exception as exc:  # noqa: BLE001
        logger.debug("image_save_failed", error=str(exc))
        return None, None

    return buffer.getvalue(), "image/jpeg"


def _fix_missing_spaces(text: str) -> str:
    text = RE_CAMEL_CASE.sub(" ", text)
    text = RE_DIGIT_BOUNDARY.sub(" ", text)
    return text


def clean_text(raw: str) -> str:
    """Normalize whitespace, drop навигационные элементы и чинит переносы."""

    if not raw:
        return ""

    text = raw.replace("\xa0", " ").replace("\u202f", " ")
    text = re.sub(r"\r", "", text)
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    text = re.sub(r"(?<=\S)\n(?=\S)", " ", text)

    lines: list[str] = []
    seen: set[str] = set()
    blank_pending = False

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if not blank_pending and lines:
                lines.append("")
            blank_pending = True
            continue
        blank_pending = False

        lowered = line.lower()
        if lowered in NAVIGATION_TOKENS:
            continue
        if len(line) <= 3 and sum(ch.isalpha() for ch in line) <= 1:
            continue
        if lowered in seen:
            continue
        seen.add(lowered)

        line = _fix_missing_spaces(line)
        line = re.sub(r"\s{2,}", " ", line)
        lines.append(line)

    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


async def _ensure_playwright():
    global JS_RENDER_ENABLED, _playwright_instance, _playwright_browser, _playwright_context, _playwright_lock, _playwright_page_lock
    if not JS_RENDER_ENABLED:
        return None, None
    if _playwright_lock is None:
        _playwright_lock = asyncio.Lock()
    async with _playwright_lock:
        if _playwright_context is not None:
            return _playwright_context, _playwright_page_lock
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            JS_RENDER_ENABLED = False
            logger.warning(
                "playwright_missing",
                msg="Install playwright and run `playwright install chromium` to enable JS rendering",
            )
            return None, None
        try:
            _playwright_instance = await async_playwright().start()
            _playwright_browser = await _playwright_instance.chromium.launch(
                headless=True,
                args=["--disable-gpu", "--no-sandbox"],
            )
            _playwright_context = await _playwright_browser.new_context()
            _playwright_page_lock = asyncio.Lock()
        except Exception as exc:  # noqa: BLE001
            JS_RENDER_ENABLED = False
            logger.warning("playwright_init_failed", error=str(exc))
            return None, None
        return _playwright_context, _playwright_page_lock


async def _render_with_playwright(url: str) -> str | None:
    context, page_lock = await _ensure_playwright()
    if not context or not page_lock:
        return None
    async with page_lock:
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=JS_RENDER_TIMEOUT)
            if JS_RENDER_WAIT > 0:
                await asyncio.sleep(JS_RENDER_WAIT)
            return await page.content()
        except Exception as exc:  # noqa: BLE001
            logger.debug("playwright_render_failed", url=url, error=str(exc))
            return None
        finally:
            with suppress(Exception):
                await page.close()


async def _shutdown_playwright():
    global _playwright_instance, _playwright_browser, _playwright_context, _playwright_page_lock
    if _playwright_context is not None:
        with suppress(Exception):
            await _playwright_context.close()
    if _playwright_browser is not None:
        with suppress(Exception):
            await _playwright_browser.close()
    if _playwright_instance is not None:
        with suppress(Exception):
            await _playwright_instance.stop()
    _playwright_instance = None
    _playwright_browser = None
    _playwright_context = None
    _playwright_page_lock = None


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
    project_label: str | None = None,
) -> AsyncIterator[Tuple[str, str, str, bool, bytes | None]]:
    """Asynchronously crawl a site in BFS order.

    Yields tuples ``(url, payload, content_type, is_html, binary)`` where
    ``payload`` contains extracted text (or HTML) and ``binary`` holds the raw
    bytes for downloadable documents (PDF/DOC/DOCX). Accepts an optional
    ``client_factory`` for tests to inject a custom ``httpx.AsyncClient`` (e.g.,
    with ``MockTransport``).
    """

    visited: Set[str] = set()
    url_queue: asyncio.Queue[Tuple[str, int]] = asyncio.Queue()
    result_queue: asyncio.Queue[Tuple[str, str, str, bool, bytes | None]] = asyncio.Queue()
    visited_lock = asyncio.Lock()

    if project_label is None:
        reset_counters()
        on_crawler_start()
    else:
        reset_counters(project_label)
        on_crawler_start(project_label)

    await url_queue.put((start_url, 0))
    _incr("queued", 1, project_label)

    async def _fetch_async(
        client: httpx.AsyncClient, url: str
    ) -> Tuple[str | None, str | None, bool, bytes | None]:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "")
            main_type = ctype.split(";")[0].strip().lower()
            path_lower = urlparse.urlparse(url).path.lower()
            if main_type == "application/pdf" or path_lower.endswith(".pdf"):
                text = pdf_to_text(resp.content)
                if text:
                    logger.info("pdf extracted", url=url, chars=len(text))
                else:
                    logger.info("pdf extracted", url=url, chars=0, reason="empty_text")
                return text, (ctype or "application/pdf"), False, resp.content
            if main_type in DOCX_MIME_TYPES or path_lower.endswith(".docx"):
                text = extract_docx_text(resp.content)
                if text:
                    logger.info("docx extracted", url=url, chars=len(text))
                else:
                    logger.info("docx extracted", url=url, chars=0, reason="empty_text")
                return text, (ctype or "application/vnd.openxmlformats-officedocument.wordprocessingml.document"), False, resp.content
            if main_type in DOC_MIME_TYPES or path_lower.endswith(".doc"):
                text = extract_doc_text(resp.content)
                if text:
                    logger.info("doc extracted", url=url, chars=len(text))
                else:
                    logger.info("doc extracted", url=url, chars=0, reason="empty_text")
                return text, (ctype or "application/msword"), False, resp.content
            if main_type != "text/html":
                logger.info("skip non-html", url=url, content_type=ctype)
                return None, ctype, False, None
            if JS_RENDER_ENABLED:
                rendered = await _render_with_playwright(url)
                if rendered:
                    return rendered, ctype or "text/html", True, None
            return resp.text, ctype, True, None
        except Exception as exc:  # pragma: no cover - error path
            logger.warning("fetch failed", url=url, error=str(exc))
            return None, None, False, None

    async def _worker(client: httpx.AsyncClient) -> None:
        while True:
            url, depth = await url_queue.get()
            try:
                async with visited_lock:
                    if url in visited or depth > max_depth or len(visited) >= max_pages:
                        _incr("queued", -1, project_label)
                        continue
                    visited.add(url)
                try:
                    with mark_url(url, project_label):
                        payload, ctype, is_html, binary_data = await asyncio.wait_for(
                            _fetch_async(client, url),
                            timeout=PAGE_TIMEOUT,
                        )
                except asyncio.TimeoutError:
                    logger.warning(
                        "fetch timeout",
                        url=url,
                        timeout=PAGE_TIMEOUT,
                    )
                    continue

                if payload or binary_data:
                    logger.info(
                        "page fetched", url=url, depth=depth, content_length=len(payload), content_type=ctype
                    )
                    await result_queue.put((url, payload or "", ctype, is_html, binary_data))
                    if is_html and (not allowed_domain or urlparse.urlparse(url).netloc == allowed_domain):
                        for link in extract_links(payload, url):
                            async with visited_lock:
                                if link in visited:
                                    continue
                                if len(visited) + url_queue.qsize() >= max_pages:
                                    continue
                                await url_queue.put((link, depth + 1))
                                _incr("queued", 1, project_label)
                else:
                    logger.info("page skipped", url=url, reason="non_html_or_error")
            finally:
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
                url, payload, ctype, is_html, binary_data = item
                pages += 1
                yield url, payload, ctype, is_html, binary_data
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

    reset_counters(document_project)
    on_crawler_start(document_project)

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
        project_model: Project | None = None
        try:
            project_doc = db[os.getenv("MONGO_PROJECTS", "projects")].find_one(
                {"name": document_project}
            )
            if project_doc:
                project_model = Project(**project_doc)
        except Exception as exc:
            logger.debug("project_model_load_failed", project=document_project, error=str(exc))

        async def _store() -> None:
            img_client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)
            try:
                async for (
                    page_url,
                    raw_payload,
                    source_ct,
                    is_html,
                    binary_payload,
                ) in crawl(
                    start_url,
                    max_pages=max_pages,
                    max_depth=max_depth,
                    allowed_domain=allowed_domain,
                    project_label=document_project,
                ):
                    raw_text = html_to_text(raw_payload) if is_html else raw_payload
                    text = clean_text(raw_text) if raw_text else ""

                    main_type = (source_ct or "").split(";")[0].strip().lower()
                    lower_url = page_url.lower()
                    is_binary = not is_html and binary_payload is not None

                    image_links = extract_image_links(raw_payload, page_url) if is_html else []

                    if not text and not is_binary and not image_links:
                        logger.info("empty_page", url=page_url)
                        if progress_callback:
                            progress_callback(page_url)
                        continue

                    if is_binary:
                        if main_type in DOCX_MIME_TYPES or lower_url.endswith(".docx"):
                            suffix = ".docx"
                            storage_type = main_type or "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        elif main_type in DOC_MIME_TYPES or lower_url.endswith(".doc"):
                            suffix = ".doc"
                            storage_type = main_type or "application/msword"
                        elif main_type == "application/pdf" or lower_url.endswith(".pdf"):
                            suffix = ".pdf"
                            storage_type = main_type or "application/pdf"
                        else:
                            suffix = ".bin"
                            storage_type = main_type or "application/octet-stream"
                    else:
                        suffix = ".txt"
                        storage_type = "text/plain"

                    filename = _filename_from_url(page_url, suffix=suffix)

                    if is_binary:
                        description = await generate_document_summary(filename, text, project_model)
                        if not description.strip() and text:
                            description = text.replace("\n", " ").strip()[:200]
                        if not description.strip():
                            description = f"Документ «{filename}»."
                        payload_bytes = binary_payload or b""
                    else:
                        description = text.replace("\n", " ").strip()[:200]
                        payload_source = text if text else raw_payload
                        payload_bytes = payload_source.encode("utf-8")

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
                        content_type=storage_type,
                    )

                    doc: dict[str, object] = {
                        "name": filename,
                        "description": description,
                        "fileId": str(file_id),
                        "url": page_url,
                        "ts": time.time(),
                        "content_type": storage_type,
                        "domain": document_domain,
                        "project": document_project,
                        "size_bytes": len(payload_bytes),
                    }
                    if source_ct:
                        doc["source_content_type"] = source_ct
                    elif is_binary and storage_type != "text/plain":
                        doc["source_content_type"] = storage_type
                    elif is_html:
                        doc["source_content_type"] = "text/html"

                    operations.append(
                        UpdateOne(
                            {"url": page_url, "project": document_project},
                            {"$set": doc},
                            upsert=True,
                        )
                    )

                    for image_info in image_links:
                        image_url = image_info.get("url") or ""
                        if not image_url or image_url in downloaded_images:
                            continue
                        if allowed_domain:
                            parsed_image = urlparse.urlsplit(image_url)
                            if parsed_image.netloc and parsed_image.netloc.lower() != allowed_domain.lower():
                                continue
                        try:
                            img_resp = await img_client.get(image_url)
                            img_resp.raise_for_status()
                        except Exception as exc:
                            logger.debug("image_fetch_failed", url=image_url, error=str(exc))
                            continue
                        downloaded_images.add(image_url)
                        original_type = (img_resp.headers.get("content-type") or "").split(";")[0].strip().lower()
                        compressed, final_type = compress_image(img_resp.content)
                        if not compressed or not final_type:
                            continue
                        image_filename = _filename_from_url(image_url, suffix=".jpg")
                        image_description = image_info.get("alt") or f"Изображение со страницы {page_url}"
                        try:
                            image_file_id = gridfs.put(
                                compressed,
                                filename=image_filename,
                                content_type=final_type,
                            )
                        except Exception as exc:
                            logger.warning("gridfs_image_write_failed", url=image_url, error=str(exc))
                            continue
                        image_doc = {
                            "name": image_filename,
                            "description": image_description,
                            "fileId": str(image_file_id),
                            "url": image_url,
                            "ts": time.time(),
                            "content_type": final_type,
                            "domain": document_domain,
                            "project": document_project,
                            "size_bytes": len(compressed),
                        }
                        if original_type:
                            image_doc["source_content_type"] = original_type
                        operations.append(
                            UpdateOne(
                                {"url": image_url, "project": document_project},
                                {"$set": image_doc},
                                upsert=True,
                            )
                        )

                    if progress_callback:
                        progress_callback(page_url)

                    if len(operations) >= BATCH_SIZE:
                        try:
                            documents_collection.bulk_write(operations, ordered=False)
                        except Exception as exc:  # pragma: no cover - bulk failure
                            logger.warning("bulk_write_failed", error=str(exc))
                        finally:
                            operations.clear()
            finally:
                if JS_RENDER_ENABLED:
                    await _shutdown_playwright()
                await img_client.aclose()

        asyncio.run(_store())

        if operations:
            try:
                documents_collection.bulk_write(operations, ordered=False)
            except Exception as exc:  # pragma: no cover - bulk failure
                logger.warning("bulk_write_failed", error=str(exc))
            finally:
                operations.clear()

        logger.info("crawler finished")
    finally:
        _set("queued", 0, document_project)
        _set("in_progress", 0, document_project)
        client.close()
        if JS_RENDER_ENABLED:
            asyncio.run(_shutdown_playwright())

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
