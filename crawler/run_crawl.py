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
from typing import Any, AsyncIterator, Callable, Iterable, List, Optional, Set, Tuple

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

from knowledge.summary import generate_document_summary, generate_image_caption
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

    try:
        pipe = r.pipeline()
        for key in ("queued", "in_progress", "done", "failed"):
            pipe.set(_redis_key(key, project), 0)
        pipe.delete(_redis_key("recent_urls", project))
        pipe.execute()
    except Exception:
        for key in ("queued", "in_progress", "done", "failed"):
            _set(key, 0, project)
        try:
            r.delete(_redis_key("recent_urls", project))
        except Exception:
            pass


def clear_crawler_state(project: str | None = None) -> int:
    """Reset counters and recent URLs for the crawler."""

    reset_counters(project)
    try:
        pipe = r.pipeline()
        for key in ("last_url", "last_run", "started_at"):
            pipe.delete(_redis_key(key, project))
        pipe.execute()
    except Exception:
        for key in ("last_url", "last_run", "started_at"):
            try:
                r.delete(_redis_key(key, project))
            except Exception:
                pass
    removed = purge_project_progress(project)
    return removed


def purge_project_progress(project: str | None = None) -> int:
    """Remove cached crawler progress hashes belonging to ``project``."""

    project_key = (project or "").strip().lower() or None
    removed = 0
    try:
        for raw_key in r.scan_iter(match="crawler:progress:*"):
            key = raw_key  # redis-py returns bytes
            include = True
            if project_key is not None:
                try:
                    value = r.hget(key, "project")
                except Exception:
                    value = None
                if value is None:
                    include = False
                else:
                    try:
                        decoded = value.decode().strip().lower()
                    except Exception:
                        decoded = str(value).strip().lower()
                    include = decoded == project_key
            if include:
                try:
                    r.delete(key)
                    removed += 1
                except Exception:
                    continue
    except Exception:
        return removed
    return removed


def deduplicate_recent_urls(project: str | None = None) -> int:
    """Remove duplicate entries from the recent URL list.

    Returns the number of removed duplicates.
    """

    try:
        key = _redis_key("recent_urls", project)
        urls = r.lrange(key, 0, -1) or []
        seen: set[str] = set()
        unique: list[str] = []
        for url in urls:
            if url in seen:
                continue
            seen.add(url)
            unique.append(url)
        if unique == urls:
            return 0
        pipe = r.pipeline()
        pipe.delete(key)
        if unique:
            pipe.rpush(key, *unique)
        pipe.execute()
        return len(urls) - len(unique)
    except Exception:
        return 0

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

BREADCRUMB_SEPARATORS = re.compile(r"\s*[>/\\»|-]+\s*")
NAV_KEYWORDS = {
    "главная",
    "контакты",
    "о компании",
    "о нас",
    "услуги",
    "партнёры",
    "клиенты",
    "новости",
    "карта сайта",
    "помощь",
    "faq",
    "поиск",
    "support",
    "docs",
    "documentation",
    "download",
}
FOOTER_KEYWORDS = {
    "все права защищены",
    "all rights reserved",
    "политика конфиденциальности",
    "privacy policy",
    "terms of use",
    "соглашение",
    "copyright",
    "©",
    "mail",
    "phone",
}

# Query parameters that rarely affect page content and can be stripped to reduce noise.
DEFAULT_DROP_QUERY_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_referrer",
    "yclid",
    "ysclid",
    "gclid",
    "fbclid",
    "ga_source",
    "ga_medium",
    "ga_campaign",
    "ga_content",
    "ga_term",
    "cmpid",
    "mc_cid",
    "mc_eid",
    "mkt_tok",
    "msclkid",
    "icid",
    "igshid",
    "pk_campaign",
    "pk_kwd",
    "pk_source",
    "pk_medium",
    "source",
    "ref",
    "referrer",
    "sr_share",
    "sr_channel",
    "campaign",
    "openstat",
    "_openstat",
    "_ga",
    "_gl",
    "_gid",
    "_gac",
    "zanpid",
    "wt_mc",
    "wt_mc_o",
    "utm_reader",
    "hsCtaTracking",
    "fb_action_ids",
    "fb_action_types",
    "fb_source",
    "dclid",
    "srsltid",
    "twclid",
    "ttclid",
    "ver",
    "clid",
    "cid",
}

_extra_drop = {
    token.strip().lower()
    for token in (os.getenv("CRAWL_EXTRA_DROP_PARAMS") or "").split(",")
    if token.strip()
}
DROP_QUERY_PARAMS = DEFAULT_DROP_QUERY_PARAMS | _extra_drop

_essential_params_default = {
    token.strip().lower()
    for token in (os.getenv("CRAWL_KEEP_PARAMS") or "p,id,page,q,doc,slug").split(",")
    if token.strip()
}
ESSENTIAL_QUERY_PARAMS = _essential_params_default

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
    """Extract image URLs (including lazy-loaded variants) from ``html``."""

    soup = BeautifulSoup(html, "html.parser")
    found: list[dict[str, str]] = []
    seen: set[str] = set()

    def _push(raw_url: str | None, alt_text: str | None = None) -> None:
        if not raw_url:
            return
        candidate = raw_url.strip()
        if not candidate or candidate.startswith("data:"):
            return
        absolute = urlparse.urljoin(base_url, candidate)
        if not absolute.lower().startswith(("http://", "https://")):
            return
        absolute = absolute.split("#")[0]
        if absolute in seen:
            return
        alt_clean = (alt_text or "").strip()
        if not alt_clean:
            return
        entry: dict[str, str] = {"url": absolute, "alt": alt_clean}
        found.append(entry)
        seen.add(absolute)

    def _iter_src_candidates(img_tag: Any) -> list[str]:
        candidates: list[str] = []
        for attr in (
            "src",
            "data-src",
            "data-original",
            "data-lazy-src",
            "data-url",
            "data-preview",
            "data-small",
            "data-medium",
            "data-large",
        ):
            value = img_tag.get(attr)
            if isinstance(value, str):
                trimmed = value.strip()
                if trimmed:
                    candidates.append(trimmed)
        srcset = img_tag.get("srcset")
        if isinstance(srcset, str):
            for item in srcset.split(","):
                parts = item.strip().split()
                if parts:
                    candidates.append(parts[0])
        return list(dict.fromkeys(candidates))

    for img in soup.find_all("img"):
        alt_text = img.get("alt") or ""
        for candidate in _iter_src_candidates(img):
            _push(candidate, alt_text)

    return found


def extract_links(
    html: str,
    base_url: str,
    *,
    base_scheme: str = "https",
    canonical_host: str | None = None,
    clean_params: set[str] | None = None,
) -> List[str]:
    """Extract absolute, normalised links from ``html`` relative to ``base_url``."""

    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []

    for anchor in soup.find_all("a", href=True):
        href: str = anchor["href"]
        candidate = urlparse.urljoin(base_url, href)
        candidate = candidate.split("#", 1)[0].strip()
        if not candidate.lower().startswith(("http://", "https://")):
            continue
        normalized = normalize_url(
            candidate,
            base_scheme=base_scheme,
            canonical_host=canonical_host,
            clean_params=clean_params,
        )
        if not normalized:
            continue
        path_lower = urlparse.urlsplit(normalized).path.lower()
        if any(path_lower.endswith(ext) for ext in BINARY_EXTENSIONS):
            continue
        links.append(normalized)

    return links


def _is_allowed_host(url: str, suffixes: set[str]) -> bool:
    host = urlparse.urlsplit(url).hostname
    if not host:
        return False
    host = host.lower()
    bare = host.split(":")[0]
    if bare in suffixes:
        return True
    return any(bare.endswith(f".{suffix}") for suffix in suffixes if suffix)


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


def normalize_url(
    raw_url: str,
    *,
    base_scheme: str = "https",
    canonical_host: str | None = None,
    clean_params: set[str] | None = None,
) -> str | None:
    """Return a canonical representation of ``raw_url`` suitable for deduplication."""

    if not raw_url:
        return None

    candidate = raw_url.strip()
    if not candidate:
        return None

    parsed = urlparse.urlsplit(candidate)
    scheme = (parsed.scheme or base_scheme or "https").lower()

    netloc = parsed.netloc.strip().lower()
    if not netloc:
        netloc = (canonical_host or "").strip().lower()
    if not netloc:
        return None

    host, sep, port = netloc.partition(":")
    if not host and sep:
        host, port = port, ""
    if canonical_host:
        canon = canonical_host.strip().lower()
        if canon.startswith("www."):
            canon = canon[4:]
        if host == f"www.{canon}":
            host = canon
    if port:
        if (scheme == "https" and port == "443") or (scheme == "http" and port == "80"):
            netloc = host
        else:
            netloc = f"{host}:{port}"
    else:
        netloc = host

    path = parsed.path or ""
    if path:
        path = re.sub(r"/{2,}", "/", path)
    if path.endswith("/") and path not in {"", "/"}:
        path = path.rstrip("/")
    if path == "/":
        path = ""

    drop_params = set(DROP_QUERY_PARAMS)
    if clean_params:
        drop_params.update({p.lower() for p in clean_params if p.lower() not in ESSENTIAL_QUERY_PARAMS})

    query_pairs = urlparse.parse_qsl(parsed.query, keep_blank_values=False)
    filtered_pairs = [
        (k, v)
        for k, v in query_pairs
        if k and k.lower() not in drop_params
    ]
    filtered_pairs.sort()
    query = urlparse.urlencode(filtered_pairs, doseq=True)

    return urlparse.urlunsplit((scheme, netloc, path, query, ""))


def _extract_clean_params(robots_body: str) -> set[str]:
    params: set[str] = set()
    for line in robots_body.splitlines():
        stripped = line.strip()
        if not stripped or not stripped.lower().startswith("clean-param:"):
            continue
        payload = stripped.split(":", 1)[1].strip()
        if not payload:
            continue
        # ``Clean-param: a&b /path`` – only capture parameter list before optional path.
        tokens = payload.replace("&amp", "&").split()
        if not tokens:
            continue
        for item in tokens[0].split("&"):
            param = item.strip().lower()
            if param:
                params.add(param)
    return params


def _extract_sitemap_urls(robots_body: str) -> list[str]:
    urls: list[str] = []
    for line in robots_body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith("sitemap:"):
            candidate = stripped.split(":", 1)[1].strip()
            if candidate:
                urls.append(candidate)
    return urls


async def _load_robot_rules(
    client: httpx.AsyncClient,
    *,
    base_scheme: str,
    canonical_host: str | None,
    ignore_robots: bool,
) -> tuple[robotparser.RobotFileParser | None, set[str], list[str]]:
    if ignore_robots or not canonical_host:
        return None, set(), []

    robots_url = urlparse.urlunsplit((base_scheme, canonical_host, "/robots.txt", "", ""))
    try:
        resp = await client.get(robots_url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
    except Exception as exc:  # noqa: BLE001
        logger.debug("robots_fetch_failed", url=robots_url, error=str(exc))
        return None, set(), []

    if resp.status_code != 200 or not resp.text.strip():
        return None, set(), []

    body = resp.text
    parser: robotparser.RobotFileParser | None = robotparser.RobotFileParser()
    parser.set_url(robots_url)
    try:
        parser.parse(body.splitlines())
    except Exception as exc:  # noqa: BLE001
        logger.debug("robots_parse_failed", url=robots_url, error=str(exc))
        parser = None

    clean_params = _extract_clean_params(body)
    sitemap_urls = _extract_sitemap_urls(body)
    return parser, clean_params, sitemap_urls


def _parse_sitemap_document(xml_text: str) -> tuple[list[str], list[str]]:
    """Return (urls, nested_sitemaps) contained in ``xml_text``."""

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return [], []

    urls: list[str] = []
    nested: list[str] = []

    tag = root.tag.lower()
    if tag.endswith("urlset"):
        for url_el in root.findall(".//{*}url"):
            loc_el = url_el.find("{*}loc")
            if loc_el is not None and isinstance(loc_el.text, str):
                value = loc_el.text.strip()
                if value:
                    urls.append(value)
    elif tag.endswith("sitemapindex"):
        for sm in root.findall(".//{*}sitemap"):
            loc_el = sm.find("{*}loc")
            if loc_el is not None and isinstance(loc_el.text, str):
                value = loc_el.text.strip()
                if value:
                    nested.append(value)
    else:
        for loc_el in root.findall(".//{*}loc"):
            if loc_el is not None and isinstance(loc_el.text, str):
                value = loc_el.text.strip()
                if value:
                    urls.append(value)

    return urls, nested


async def _collect_sitemap_urls(
    client: httpx.AsyncClient,
    seeds: Iterable[str],
    *,
    base_scheme: str,
    canonical_host: str | None,
    clean_params: set[str],
    allowed_host_suffixes: set[str] | None,
    robot_parser: robotparser.RobotFileParser | None,
    max_pages: int,
) -> list[str]:
    """Fetch sitemap documents recursively and return discovered page URLs."""

    collected: list[str] = []
    pending: list[str] = list(seeds)
    seen_sitemaps: set[str] = set()
    user_agent = HEADERS.get("User-Agent", "*")

    while pending and len(collected) < max_pages:
        raw_sitemap = pending.pop(0)
        normalized_sitemap = normalize_url(
            raw_sitemap,
            base_scheme=base_scheme,
            canonical_host=canonical_host,
            clean_params=None,
        )
        if not normalized_sitemap or normalized_sitemap in seen_sitemaps:
            continue
        seen_sitemaps.add(normalized_sitemap)

        try:
            resp = await client.get(normalized_sitemap, timeout=REQUEST_TIMEOUT)
        except Exception as exc:  # noqa: BLE001
            logger.debug("sitemap_fetch_failed", url=normalized_sitemap, error=str(exc))
            continue

        if resp.status_code != 200:
            continue

        urls, nested = _parse_sitemap_document(resp.text)
        pending.extend(nested)

        for entry in urls:
            normalized_entry = normalize_url(
                entry,
                base_scheme=base_scheme,
                canonical_host=canonical_host,
                clean_params=clean_params,
            )
            if not normalized_entry:
                continue
            if allowed_host_suffixes and not _is_allowed_host(normalized_entry, allowed_host_suffixes):
                continue
            if robot_parser and not robot_parser.can_fetch(user_agent, normalized_entry):
                continue
            collected.append(normalized_entry)
            if len(collected) >= max_pages:
                break

    return collected


def _resolve_canonical_host(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if "//" in candidate:
        host = urlparse.urlsplit(candidate).hostname
    else:
        host = urlparse.urlsplit(f"https://{candidate}").hostname
    if not host:
        return None
    host = host.strip().lower()
    if host.endswith(":80") or host.endswith(":443"):
        host = host.rsplit(":", 1)[0]
    if host.startswith("www."):
        return host[4:]
    return host


def _normalize_for_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text or "").strip().lower()
    return normalized


def _is_probably_navigation(text: str) -> bool:
    candidate = text.strip().lower()
    if not candidate:
        return True
    parts = [part.strip() for part in BREADCRUMB_SEPARATORS.split(candidate) if part.strip()]
    if parts and all(part in NAV_KEYWORDS for part in parts):
        return True
    if len(candidate) <= 48 and candidate.count(" ") <= 6:
        tokens = [token for token in re.split(r"\W+", candidate) if token]
        if tokens and all(token in NAV_KEYWORDS for token in tokens):
            return True
    for marker in FOOTER_KEYWORDS:
        if marker in candidate and len(candidate) <= 160:
            return True
    return False


def _should_skip_text_document(text: str) -> bool:
    normalized = _normalize_for_hash(text)
    if not normalized:
        return True
    if len(normalized) < 60:
        return True
    if normalized.count("paragraph") > 12:
        return True
    if _is_probably_navigation(normalized):
        return True
    return False


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
    ignore_robots: bool | None = None,
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
    enqueued: Set[str] = set()

    parsed_start = urlparse.urlsplit(start_url)
    base_scheme = (parsed_start.scheme or "https").lower()
    start_host = parsed_start.hostname or ""
    canonical_host = (
        _resolve_canonical_host(start_host)
        or _resolve_canonical_host(allowed_domain)
        or (start_host.strip().lower() if start_host else None)
    )

    allowed_host_suffixes: set[str] | None = None
    if allowed_domain:
        allowed_host_suffixes = set()

        def _register_host(value: str | None) -> None:
            if not value:
                return
            host = value.lower().strip()
            if not host:
                return
            allowed_host_suffixes.add(host)
            if host.startswith("www."):
                allowed_host_suffixes.add(host[4:])
            else:
                allowed_host_suffixes.add(f"www.{host}")

        parsed_allowed = urlparse.urlsplit(
            allowed_domain if allowed_domain.startswith("http") else f"https://{allowed_domain}"
        )
        _register_host(parsed_allowed.hostname or allowed_domain.split(":")[0])
        if start_host:
            _register_host(start_host)
        if canonical_host:
            _register_host(canonical_host)

        # Normalize to bare hostnames (without ports)
        allowed_host_suffixes = {host.split(":")[0] for host in allowed_host_suffixes if host}

    ignore_robots = DEFAULT_IGNORE_ROBOTS if ignore_robots is None else ignore_robots

    normalized_seed = normalize_url(
        start_url,
        base_scheme=base_scheme,
        canonical_host=canonical_host,
        clean_params=None,
    ) or start_url.strip()

    if project_label is None:
        clear_crawler_state()
        on_crawler_start()
    else:
        clear_crawler_state(project_label)
        on_crawler_start(project_label)

    def _fallback_fetch(url: str) -> str | None:
        try:
            resp = requests.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )
            resp.raise_for_status()
            if not resp.encoding:
                resp.encoding = resp.apparent_encoding or "utf-8"
            text = resp.text
            if not text and resp.content:
                text = resp.content.decode("utf-8", errors="ignore")
            return text if text and text.strip() else None
        except Exception as exc:  # noqa: BLE001
            logger.debug("fallback_fetch_failed", url=url, error=str(exc))
            return None

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
            text = resp.text
            if (not text or len(text.strip()) < 50) and resp.content:
                fallback = await asyncio.to_thread(_fallback_fetch, url)
                if fallback:
                    return fallback, ctype or "text/html", True, None
            return text, ctype, True, None
        except Exception as exc:  # pragma: no cover - error path
            logger.warning("fetch failed", url=url, error=str(exc))
            return None, None, False, None

    # Create client
    if client_factory is None:
        context = httpx.AsyncClient(
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
        )
        created_client = True
    else:
        context = client_factory()
        created_client = True  # ensure context is closed via async context manager

    async with context as client:
        robot_parser, robot_params, robot_sitemaps = await _load_robot_rules(
            client,
            base_scheme=base_scheme,
            canonical_host=canonical_host,
            ignore_robots=ignore_robots,
        )
        clean_params: set[str] = set(robot_params)

        normalized_seed_final = normalize_url(
            normalized_seed,
            base_scheme=base_scheme,
            canonical_host=canonical_host,
            clean_params=clean_params,
        ) or normalized_seed

        sitemap_candidates: list[str] = []
        sitemap_candidates.extend(robot_sitemaps)
        if DEFAULT_SITEMAP_URL:
            sitemap_candidates.append(DEFAULT_SITEMAP_URL)
        if canonical_host:
            fallback_sitemap = urlparse.urlunsplit(
                (base_scheme, canonical_host, "/sitemap.xml", "", "")
            )
            sitemap_candidates.append(fallback_sitemap)

        dedup_candidates: list[str] = []
        seen_candidate: set[str] = set()
        for item in sitemap_candidates:
            candidate = (item or "").strip()
            if not candidate or candidate in seen_candidate:
                continue
            seen_candidate.add(candidate)
            dedup_candidates.append(candidate)

        sitemap_seed_urls: list[str] = []
        if dedup_candidates:
            sitemap_seed_urls = await _collect_sitemap_urls(
                client,
                dedup_candidates,
                base_scheme=base_scheme,
                canonical_host=canonical_host,
                clean_params=clean_params,
                allowed_host_suffixes=allowed_host_suffixes,
                robot_parser=robot_parser,
                max_pages=max_pages,
            )

        user_agent = HEADERS.get("User-Agent", "*")

        async def enqueue_url(raw: str, depth: int, *, force: bool = False) -> None:
            normalized = normalize_url(
                raw,
                base_scheme=base_scheme,
                canonical_host=canonical_host,
                clean_params=clean_params,
            )
            if not normalized:
                return
            if not force and depth > max_depth:
                return
            if allowed_host_suffixes and not _is_allowed_host(normalized, allowed_host_suffixes):
                if not force:
                    return
            if robot_parser and not robot_parser.can_fetch(user_agent, normalized):
                if not force:
                    return
            async with visited_lock:
                if normalized in visited or normalized in enqueued:
                    return
                if not force and len(visited) + url_queue.qsize() >= max_pages:
                    return
                await url_queue.put((normalized, depth))
                enqueued.add(normalized)
                _incr("queued", 1, project_label)

        await enqueue_url(normalized_seed_final, 0, force=True)
        for extra_url in sitemap_seed_urls:
            await enqueue_url(extra_url, 1)

        async def _worker(client: httpx.AsyncClient) -> None:
            while True:
                url, depth = await url_queue.get()
                try:
                    async with visited_lock:
                        if url in visited or depth > max_depth or len(visited) >= max_pages:
                            enqueued.discard(url)
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
                        logger.warning("fetch timeout", url=url, timeout=PAGE_TIMEOUT)
                        continue

                    if payload or binary_data:
                        content_length = len(payload) if payload else len(binary_data or b"")
                        logger.info(
                            "page fetched",
                            url=url,
                            depth=depth,
                            content_length=content_length,
                            content_type=ctype,
                        )
                        await result_queue.put((url, payload or "", ctype, is_html, binary_data))
                        if is_html:
                            for link in extract_links(
                                payload,
                                url,
                                base_scheme=base_scheme,
                                canonical_host=canonical_host,
                                clean_params=clean_params,
                            ):
                                await enqueue_url(link, depth + 1)
                    else:
                        logger.info("page skipped", url=url, reason="non_html_or_error")
                finally:
                    enqueued.discard(url)
                    url_queue.task_done()

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
    ignore_robots: bool | None = None,
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

    clear_crawler_state(document_project)
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
            seen_text_hashes: set[str] = set()
            seen_binary_hashes: set[str] = set()
            downloaded_images: set[str] = set()
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
                    ignore_robots=ignore_robots,
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

                    store_document = True
                    skip_reason: str | None = None
                    content_hash: str | None = None

                    if is_binary:
                        payload_bytes = binary_payload or b""
                        if payload_bytes:
                            content_hash = hashlib.sha1(payload_bytes).hexdigest()
                            if content_hash in seen_binary_hashes:
                                store_document = False
                                skip_reason = "duplicate_binary"
                            else:
                                seen_binary_hashes.add(content_hash)
                        description = await generate_document_summary(filename, text, project_model)
                        if not description.strip() and text:
                            description = text.replace("\n", " ").strip()[:200]
                        if not description.strip():
                            description = f"Документ «{filename}»."
                    else:
                        payload_source = text if text else raw_payload
                        payload_bytes = payload_source.encode("utf-8") if isinstance(payload_source, str) else (payload_source or b"")
                        if _should_skip_text_document(text):
                            store_document = False
                            skip_reason = "low_value_text"
                        else:
                            canonical = _normalize_for_hash(text)
                            if canonical:
                                content_hash = hashlib.sha1(canonical.encode("utf-8")).hexdigest()
                                if content_hash in seen_text_hashes:
                                    store_document = False
                                    skip_reason = "duplicate_text"
                                else:
                                    seen_text_hashes.add(content_hash)
                        description = text.replace("\n", " ").strip()[:200]

                    if store_document:
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
                        if content_hash:
                            doc["content_hash"] = content_hash

                        operations.append(
                            UpdateOne(
                                {"url": page_url, "project": document_project},
                                {"$set": doc},
                                upsert=True,
                            )
                        )
                    else:
                        logger.info(
                            "knowledge_document_skipped",
                            url=page_url,
                            reason=skip_reason or "filtered",
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
                        image_description = await generate_image_caption(
                            image_filename,
                            image_info.get("alt"),
                            text,
                            project_model,
                        )
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
