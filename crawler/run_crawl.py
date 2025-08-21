#!/usr/bin/env python
"""run_crawl.py  ‒ минимальный веб‑краулер для первичного наполнения базы

Запускается контейнером после деплоя и рекурсивно обходит ссылки,
начиная с `CRAWL_START_URL` (или аргумента `--url`). Страницы
сохраняются в MongoDB (по умолчанию mongodb://root:changeme@mongo:27017,
можно переопределить переменной окружения `MONGO_URI`).

Поддерживает:
* загрузку и проверку `robots.txt`;
* разбор `sitemap.xml` и расширение начальной очереди ссылками из него;
* лёгкое расширение функциональности: расчёт эмбеддингов, Celery,
  дедубликация по MD5 и прочее.

Переменные окружения / CLI‑параметры
-----------------------------------
MONGO_URI          – строка подключения к Mongo ("mongodb://...").
CRAWL_START_URL    – стартовая точка обхода.
CRAWL_MAX_PAGES    – максимальное число страниц (по умолчанию 500).
CRAWL_MAX_DEPTH    – максимальная глубина (по умолчанию 3).
CRAWL_SITEMAP_URL  – явно указанный URL sitemap (по умолчанию /sitemap.xml).
CRAWL_IGNORE_ROBOTS – игнорировать `robots.txt` ("1"/"0").

Пример запуска вручную в контейнере:
$ python crawler/run_crawl.py --url "https://example.com" --max-pages 1000
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.parse as urlparse
from collections import deque
from typing import Iterable, List, Set, Tuple

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
r = Redis(host=os.getenv("REDIS_HOST", "redis"), port=int(os.getenv("REDIS_PORT", "6379")), decode_responses=True)

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

def on_crawler_start():
    _set("started_at", time.time())

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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; SiteLLM-VertebroCrawler/1.0; +https://example.com)"
    )
}
REQUEST_TIMEOUT = float(os.getenv("CRAWL_TIMEOUT", "10"))  # seconds
BATCH_SIZE = 50  # сколько документов пушим в Mongo за раз

# ------------------------- Вспомогательные функции ------------------- #

def fetch(url: str) -> Tuple[str | None, str | None]:
    """Скачивает страницу. Возвращает (html, content_type)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.text, resp.headers.get("content-type", "")
    except Exception as exc:  # noqa: BLE001
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


def get_robot_parser(start_url: str) -> robotparser.RobotFileParser:
    """Загружает и парсит robots.txt для домена."""
    robots_url = urlparse.urljoin(start_url, "/robots.txt")
    rp = robotparser.RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
    except Exception as exc:  # noqa: BLE001
        logger.warning("robots.txt fetch failed", url=robots_url, error=str(exc))
    return rp


def parse_sitemap(sitemap_url: str) -> List[str]:
    """Возвращает список URL из sitemap.xml."""
    try:
        resp = requests.get(sitemap_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        return [
            loc.text.strip()
            for loc in root.findall(
                ".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
            )
            if loc.text and loc.text.strip().startswith("http")
        ]
    except Exception as exc:  # noqa: BLE001
        logger.warning("sitemap fetch failed", url=sitemap_url, error=str(exc))
        return []


def crawl(
    start_url: str,
    *,
    max_pages: int = DEFAULT_MAX_PAGES,
    max_depth: int = DEFAULT_MAX_DEPTH,
    allowed_domain: str | None = None,
    robot_parser: robotparser.RobotFileParser | None = None,
    initial_urls: Iterable[str] | None = None,
) -> Iterable[Tuple[str, str, str]]:
    """BFS‑обход сайта (non‑blocking, без параллелизма).

    Yields:
        (url, html, content_type)
    """

    visited: Set[str] = set()
    queue: deque[Tuple[str, int]] = deque([(start_url, 0)])
    _incr("queued", 1)
    if initial_urls:
        for url in initial_urls:
            queue.append((url, 0))
            _incr("queued", 1)

    while queue and len(visited) < max_pages:
        url, depth = queue.popleft()
        if url in visited or depth > max_depth:
            continue
        if robot_parser and not robot_parser.can_fetch(HEADERS["User-Agent"], url):
            continue
        visited.add(url)

        with mark_url(url):
            html, ctype = fetch(url)
            if html is None:
                continue

            yield url, html, ctype

            # Ограничиваем домен, чтобы не уползти далеко
            if allowed_domain and urlparse.urlparse(url).netloc != allowed_domain:
                continue

            for link in extract_links(html, url):
                if link in visited:
                    continue
                if robot_parser and not robot_parser.can_fetch(
                    HEADERS["User-Agent"], link
                ):
                    continue
                queue.append((link, depth + 1))
                _incr("queued", 1)


# -------------------------- MongoDB utils ---------------------------- #

def get_mongo_collection(
    mongo_uri: str = DEFAULT_MONGO_URI,
    *,
    db_name: str = "crawler",
    collection_name: str = "pages",
):
    client = MongoClient(mongo_uri)
    return client[db_name][collection_name]


def store_batch(col, docs: List[dict]):  # noqa: ANN001
    """Upsert‑ит пачку документов."""
    requests_: list[UpdateOne] = []
    for doc in docs:
        requests_.append(
            UpdateOne({"url": doc["url"]}, {"$set": doc}, upsert=True)
        )
    if requests_:
        col.bulk_write(requests_)


# ------------------------------ main --------------------------------- #

def main() -> None:  # noqa: D401
    """CLI‑входная точка."""

    parser = argparse.ArgumentParser(description="Простой сайт‑краулер → MongoDB")
    parser.add_argument("--url", default=DEFAULT_START_URL, help="Start URL to crawl")
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    parser.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    parser.add_argument(
        "--domain",
        help="Restrict crawl to this domain (по умолчанию домен стартового URL)",
    )
    parser.add_argument(
        "--mongo-uri",
        default=DEFAULT_MONGO_URI,
        help="MongoDB connection string (mongodb://user:pass@host:port)",
    )
    parser.add_argument(
        "--sitemap-url",
        default=DEFAULT_SITEMAP_URL,
        help="Explicit sitemap URL to seed from (по умолчанию /sitemap.xml)",
    )
    parser.add_argument(
        "--ignore-robots",
        action="store_true",
        default=DEFAULT_IGNORE_ROBOTS,
        help="Ignore robots.txt rules",
    )
    args = parser.parse_args()

    if not args.url:
        sys.exit("❌ Need --url or set CRAWL_START_URL")

    domain = args.domain or urlparse.urlparse(args.url).netloc

    logger.info(
        "crawler started",
        url=args.url,
        depth=args.max_depth,
        pages=args.max_pages,
    )

    col = get_mongo_collection(args.mongo_uri)
    buffer: list[dict] = []

    on_crawler_start()

    robot = None if args.ignore_robots else get_robot_parser(args.url)
    sitemap_url = args.sitemap_url or urlparse.urljoin(args.url, "/sitemap.xml")
    initial_urls = parse_sitemap(sitemap_url)

    try:
        for url, html, ctype in crawl(
            args.url,
            max_pages=args.max_pages,
            max_depth=args.max_depth,
            allowed_domain=domain,
            robot_parser=robot,
            initial_urls=initial_urls,
        ):
            logger.info("page fetched", url=url)
            buffer.append(
                {
                    "url": url,
                    "content_type": ctype,
                    "html": html,
                    "ts": time.time(),
                }
            )
            if len(buffer) >= BATCH_SIZE:
                store_batch(col, buffer)
                buffer.clear()
        # финальный слив
        if buffer:
            store_batch(col, buffer)

        logger.info("crawl complete", pages=args.max_pages)
    except KeyboardInterrupt:
        logger.warning("interrupted by user, flushing buffer")
        if buffer:
            store_batch(col, buffer)


if __name__ == "__main__":
    main()
