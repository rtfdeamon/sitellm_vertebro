import httpx
import pytest

from crawler.run_crawl import crawl


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
    async for url, payload, ctype, is_html in crawl(
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

    assert seen == set(pages)
