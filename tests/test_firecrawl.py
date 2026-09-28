"""Tests for the self-hosted Firecrawl web-tools plugin.

The HTTP boundary is mocked; these verify action routing, argument validation,
and honest failure when the server is unreachable.
"""

from __future__ import annotations

from unittest.mock import patch

from archon.plugins.firecrawl_tools import FirecrawlPlugin


def test_capabilities_and_identity():
    p = FirecrawlPlugin()
    assert p.name == "firecrawl"
    assert p.get_capabilities() == [
        "firecrawl_scrape",
        "firecrawl_crawl",
        "firecrawl_search",
    ]


def test_scrape_requires_url():
    p = FirecrawlPlugin()
    res = p.execute("firecrawl_scrape", {})
    assert res["success"] is False
    assert "url" in res["error"]


def test_search_requires_query():
    p = FirecrawlPlugin()
    res = p.execute("firecrawl_search", {})
    assert res["success"] is False
    assert "query" in res["error"]


def test_scrape_posts_to_v1_scrape():
    p = FirecrawlPlugin()
    body = {"success": True, "data": {"markdown": "# Hi", "metadata": {"title": "T"}}}

    with patch.object(p, "_post", return_value=body) as post:
        res = p.execute("firecrawl_scrape", {"url": "https://example.com"})

    post.assert_called_once()
    path, payload = post.call_args[0]
    assert path == "/v1/scrape"
    assert payload["url"] == "https://example.com"
    assert res["success"] is True
    assert res["markdown"] == "# Hi"


def test_search_returns_results():
    p = FirecrawlPlugin()
    body = {"success": True, "data": [{"url": "a"}, {"url": "b"}]}
    with patch.object(p, "_post", return_value=body):
        res = p.execute("firecrawl_search", {"query": "cats", "limit": 2})
    assert res["success"] is True
    assert len(res["results"]) == 2


def test_server_down_is_honest_error():
    import httpx

    p = FirecrawlPlugin()
    with patch("httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.post.side_effect = httpx.ConnectError(
            "refused"
        )
        res = p.execute("firecrawl_scrape", {"url": "https://example.com"})
    assert res["success"] is False
    assert "Firecrawl" in res["error"]


def test_unknown_action():
    p = FirecrawlPlugin()
    res = p.execute("firecrawl_teleport", {})
    assert res["success"] is False
