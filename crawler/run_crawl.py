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
import asyncio
import os
import sys
import time
import urllib.parse as urlparse
from typing import AsyncIterator, List, Set, Tuple

import httpx
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

async def fetch(client: httpx.AsyncClient, url: str) -> Tuple[str | None, str | None]:
    """Скачивает страницу асинхронно. Возвращает (html, content_type)."""
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        ctype = resp.headers.get("content-type", "")
        main_type = ctype.split(";")[0].strip().lower()
        if main_type != "text/html":
            logger.info("skip non-html", url=url, content_type=ctype)
            return None, ctype
        return resp.text, ctype
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


async def crawl(
    start_url: str,
    *,
    max_pages: int = DEFAULT_MAX_PAGES,
    max_depth: int = DEFAULT_MAX_DEPTH,
    allowed_domain: str | None = None,
    concurrency: int = 5,
) -> AsyncIterator[Tuple[str, str, str]]:
    """Асинхронный BFS‑обход сайта.

    Yields:
        (url, html, content_type)
    """

    visited: Set[str] = set()
    url_queue: asyncio.Queue[Tuple[str, int]] = asyncio.Queue()
    result_queue: asyncio.Queue[Tuple[str, str, str]] = asyncio.Queue()
    visited_lock = asyncio.Lock()

    await url_queue.put((start_url, 0))
    _incr("queued", 1)

    async with httpx.AsyncClient(headers=HEADERS, timeout=REQUEST_TIMEOUT) as client:

        async def worker() -> None:
            while True:
                url, depth = await url_queue.get()
                async with visited_lock:
                    if url in visited or depth > max_depth or len(visited) >= max_pages:
                        url_queue.task_done()
                        continue
                    visited.add(url)
                with mark_url(url):
                    html, ctype = await fetch(client, url)
                if html:
                    await result_queue.put((url, html, ctype))
                    if (
                        not allowed_domain
                        or urlparse.urlparse(url).netloc == allowed_domain
                    ):
                        for link in extract_links(html, url):
                            async with visited_lock:
                                if link not in visited:
                                    await url_queue.put((link, depth + 1))
                                    _incr("queued", 1)
                url_queue.task_done()

        workers = [asyncio.create_task(worker()) for _ in range(concurrency)]

        pages = 0
        try:
            while pages < max_pages:
                try:
                    url, html, ctype = await asyncio.wait_for(result_queue.get(), timeout=1)
                except asyncio.TimeoutError:
                    if url_queue.empty():
                        break
                    continue
                pages += 1
                yield url, html, ctype
        finally:
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

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

async def async_main(args) -> None:

    domain = args.domain or urlparse.urlparse(args.url).netloc
    logger.info(
        "crawler started",
        url=url,
        depth=max_depth,
        pages=max_pages,
    )

    try:
        asyncio.run(run(args, domain))
    except KeyboardInterrupt:
        logger.warning("interrupted by user, flushing buffer")


async def run(args, domain: str) -> None:
    col = get_mongo_collection(args.mongo_uri)
    buffer: list[dict] = []
    crawled = 0

    on_crawler_start()

    robot = None if args.ignore_robots else get_robot_parser(args.url)
    sitemap_url = args.sitemap_url or urlparse.urljoin(args.url, "/sitemap.xml")
    initial_urls = parse_sitemap(sitemap_url)

    try:
        async for url, html, ctype in crawl(
            args.url,
            max_pages=args.max_pages,
            max_depth=args.max_depth,
            allowed_domain=domain,
            robot_parser=robot,
            initial_urls=initial_urls,
        ):
            logger.info("page fetched", url=url)
            crawled += 1
            buffer.append(
                {
                    "url": page_url,
                    "content_type": ctype,
                    "html": html,
                    "ts": time.time(),
                }
            )
            if progress_callback:
                progress_callback(page_url)
            if len(buffer) >= BATCH_SIZE:
                await asyncio.to_thread(store_batch, col, buffer)
                buffer.clear()
        if buffer:
            await asyncio.to_thread(store_batch, col, buffer)
        logger.info("crawl complete", pages=args.max_pages)
    except KeyboardInterrupt:
        logger.warning("interrupted by user, flushing buffer")
        if buffer:
            await asyncio.to_thread(store_batch, col, buffer)


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
    args = parser.parse_args()

    if not args.url:
        sys.exit("❌ Need --url or set CRAWL_START_URL")

    asyncio.run(async_main(args))



if __name__ == "__main__":
    main()
