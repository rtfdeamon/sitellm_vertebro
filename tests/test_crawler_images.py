"""Tests for image extraction helpers used by the crawler."""

from __future__ import annotations

from crawler import run_crawl
from crawler.run_crawl import extract_image_links


def test_extract_image_links_handles_lazy_and_meta_sources() -> None:
    html = """
    <html>
      <head>
        <meta property="og:image" content="/static/og-cover.jpg">
        <link rel="image_src" href="https://cdn.example.com/hero.jpg" title="Главный баннер">
      </head>
      <body>
        <img data-src="/img/lazy.jpg" alt="Галерея">
        <img srcset="/img/small.jpg 480w, /img/large.jpg 960w" data-caption="Аудитория">
        <img src="data:image/png;base64,..." alt="Встроенная картинка">
      </body>
    </html>
    """

    links = extract_image_links(html, "https://example.com/post")
    urls = {item["url"] for item in links}

    assert urls == {
        "https://example.com/img/lazy.jpg",
        "https://example.com/img/small.jpg",
        "https://example.com/img/large.jpg",
    }

    alt_lookup = {item["url"]: item.get("alt") for item in links}
    assert alt_lookup["https://example.com/img/lazy.jpg"] == "Галерея"
    assert alt_lookup["https://example.com/img/small.jpg"] == "small"
    assert alt_lookup["https://example.com/img/large.jpg"] == "large"


def test_is_allowed_image_host_defaults_to_project_domain() -> None:
    assert run_crawl._is_allowed_image_host("cdn.example.com", "example.com")
    assert run_crawl._is_allowed_image_host("example.com", "www.example.com")
    assert run_crawl._is_allowed_image_host("www.example.com", "example.com")
    assert not run_crawl._is_allowed_image_host("static.cdn.com", "example.com")


def test_is_allowed_image_host_with_whitelist(monkeypatch) -> None:
    monkeypatch.setattr(run_crawl, "IMAGE_ALLOWED_HOST_SUFFIXES", {"examplecdn.com"})
    assert run_crawl._is_allowed_image_host("cdn.examplecdn.com", "example.com")
    assert run_crawl._is_allowed_image_host("examplecdn.com", "example.com")
    assert not run_crawl._is_allowed_image_host("assets.foreign.net", "example.com")
