import httpx
import pytest
import sys
import types

pymongo_stub = types.ModuleType("pymongo")
pymongo_stub.MongoClient = object  # type: ignore[attr-defined]
pymongo_stub.UpdateOne = object  # type: ignore[attr-defined]
pymongo_stub.ASCENDING = 1  # type: ignore[attr-defined]
sys.modules.setdefault("pymongo", pymongo_stub)
pymongo_errors_stub = types.ModuleType("pymongo.errors")
pymongo_errors_stub.PyMongoError = Exception  # type: ignore[attr-defined]
pymongo_errors_stub.InvalidOperation = Exception  # type: ignore[attr-defined]
pymongo_errors_stub.ConfigurationError = Exception  # type: ignore[attr-defined]
sys.modules.setdefault("pymongo.errors", pymongo_errors_stub)
pymongo_common_stub = types.ModuleType("pymongo.common")
pymongo_common_stub.MAX_MESSAGE_SIZE = 16 * 1024 * 1024  # type: ignore[attr-defined]
sys.modules.setdefault("pymongo.common", pymongo_common_stub)

gridfs_stub = types.ModuleType("gridfs")
gridfs_stub.GridFS = object  # type: ignore[attr-defined]
sys.modules.setdefault("gridfs", gridfs_stub)

settings_stub = types.ModuleType("settings")


class _MongoSettings:
    def __init__(self) -> None:
        self.host = "localhost"
        self.port = 27017
        self.username = None
        self.password = None
        self.database = "testdb"
        self.auth = "admin"
        self.documents = "documents"


settings_stub.MongoSettings = _MongoSettings  # type: ignore[attr-defined]
sys.modules.setdefault("settings", settings_stub)

from packages.crawler.run_crawl import crawl


@pytest.mark.asyncio
async def test_crawl_collects_pages():
    pages = {
        "https://example.com": '<a href="https://example.com/a">a</a><a href="/b">b</a>',
        "https://example.com/a": "<html>a</html>",
        "https://example.com/b": "<html>b</html>",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        html = pages.get(str(request.url))
        if html is None:
            return httpx.Response(404)
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})

    transport = httpx.MockTransport(handler)

    def client_factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=transport)

    seen = set()
    async for url, payload, ctype, is_html, binary in crawl(
        "https://example.com",
        max_pages=3,
        max_depth=2,
        allowed_domain="example.com",
        client_factory=client_factory,
    ):
        seen.add(url)
        assert ctype.startswith("text/html")
        assert is_html is True
        assert payload
        assert binary is None

    assert seen == set(pages)


@pytest.mark.asyncio
async def test_crawl_respects_robots_and_sitemap_clean_params():
    robots_txt = (
        "User-agent: *\n"
        "Disallow: /blocked\n"
        "Sitemap: https://example.com/sitemap.xml\n"
        "Clean-param: utm_source&utm_medium\n"
    )
    sitemap_xml = (
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
        "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
        "<url><loc>https://example.com/allowed?utm_source=ads</loc></url>"
        "<url><loc>https://example.com/blocked</loc></url>"
        "</urlset>"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url in {"https://example.com", "https://example.com/"}:
            body = '<a href="/allowed?utm_source=ads">allowed</a><a href="/blocked">blocked</a>'
            return httpx.Response(200, text=body, headers={"content-type": "text/html"})
        if url == "https://example.com/allowed":
            return httpx.Response(200, text="<html>allowed</html>", headers={"content-type": "text/html"})
        if url == "https://example.com/blocked":
            return httpx.Response(200, text="<html>blocked</html>", headers={"content-type": "text/html"})
        if url == "https://example.com/robots.txt":
            return httpx.Response(200, text=robots_txt, headers={"content-type": "text/plain"})
        if url == "https://example.com/sitemap.xml":
            return httpx.Response(200, text=sitemap_xml, headers={"content-type": "application/xml"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)

    def client_factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=transport)

    seen = set()
    async for url, payload, ctype, is_html, binary in crawl(
        "https://example.com",
        max_pages=5,
        max_depth=2,
        allowed_domain="example.com",
        client_factory=client_factory,
    ):
        seen.add(url)
        assert binary is None

    assert seen == {"https://example.com", "https://example.com/allowed"}
