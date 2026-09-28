"""Firecrawl web tools (self-hosted).

A thin capability over a self-hosted `Firecrawl <https://github.com/firecrawl/firecrawl>`_
instance. It complements the Selenium-based :mod:`web_automation` plugin with
clean, LLM-ready extraction: single-URL ``scrape``, whole-site ``crawl``, and
web ``search``.

This talks to Firecrawl's v1 REST API directly with ``httpx`` (already a
dependency) — no SDK, no API key. The base URL comes from configuration
(``FIRECRAWL_BASE_URL``), defaulting to a local instance. Every action performs
its own reachability check and returns an honest ``{"success": False, ...}``
when the server is down, so the capability loads even when Firecrawl isn't
running.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from archon.core.plugin_manager import AutomationPlugin

try:
    import httpx

    HAS_HTTPX = True
except ImportError:  # pragma: no cover - httpx is a core dep
    HAS_HTTPX = False

_DEFAULT_BASE_URL = "http://localhost:3002"
_DEFAULT_TIMEOUT = 120.0


class FirecrawlPlugin(AutomationPlugin):
    """Scrape / crawl / search via a self-hosted Firecrawl server."""

    def __init__(self) -> None:
        self._base_url = _DEFAULT_BASE_URL
        self._timeout = _DEFAULT_TIMEOUT
        self._configure_from_settings()

    @property
    def name(self) -> str:
        return "firecrawl"

    @property
    def description(self) -> str:
        return "Clean web scraping, crawling, and search via a self-hosted Firecrawl server"

    @property
    def version(self) -> str:
        return "1.0.0"

    def _configure_from_settings(self) -> None:
        try:
            from archon.config import get_settings

            fc = get_settings().firecrawl
            self._base_url = (fc.base_url or _DEFAULT_BASE_URL).rstrip("/")
            self._timeout = float(fc.timeout or _DEFAULT_TIMEOUT)
        except Exception as exc:  # noqa: BLE001 - fall back to defaults
            logger.debug("Firecrawl settings unavailable, using defaults: {}", exc)

    def get_capabilities(self) -> list[str]:
        if not HAS_HTTPX:
            return []
        return ["firecrawl_scrape", "firecrawl_crawl", "firecrawl_search"]

    def initialize(self) -> bool:
        # Load unconditionally when httpx is present; reachability is checked per
        # action so the capability is discoverable even when the server is down.
        return HAS_HTTPX

    def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        if not HAS_HTTPX:
            return {"success": False, "error": "httpx is not installed."}
        params = params or {}
        try:
            if action == "firecrawl_scrape":
                return self._scrape(params)
            if action == "firecrawl_crawl":
                return self._crawl(params)
            if action == "firecrawl_search":
                return self._search(params)
        except httpx.HTTPError as exc:
            return {
                "success": False,
                "error": (
                    f"Firecrawl request failed ({exc}). Is a Firecrawl server "
                    f"running at {self._base_url}?"
                ),
            }
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": f"Firecrawl error: {exc}"}
        return {"success": False, "error": f"Unknown Firecrawl action '{action}'."}

    # ── actions ────────────────────────────────────────────────────────────────

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(f"{self._base_url}{path}", json=payload)
            resp.raise_for_status()
            return resp.json()

    def _get(self, path: str) -> dict[str, Any]:
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(f"{self._base_url}{path}")
            resp.raise_for_status()
            return resp.json()

    def _scrape(self, params: dict[str, Any]) -> dict[str, Any]:
        url = params.get("url") or params.get("target") or params.get("location")
        if not url:
            return {"success": False, "error": "scrape requires a 'url'."}
        formats = params.get("formats") or ["markdown"]
        body = self._post("/v1/scrape", {"url": url, "formats": formats})
        data = body.get("data", body)
        return {
            "success": bool(body.get("success", True)),
            "url": url,
            "markdown": data.get("markdown"),
            "html": data.get("html"),
            "metadata": data.get("metadata", {}),
        }

    def _crawl(self, params: dict[str, Any]) -> dict[str, Any]:
        url = params.get("url") or params.get("target") or params.get("location")
        if not url:
            return {"success": False, "error": "crawl requires a 'url'."}
        payload: dict[str, Any] = {"url": url}
        if params.get("limit") is not None:
            payload["limit"] = int(params["limit"])
        if params.get("formats"):
            payload["scrapeOptions"] = {"formats": params["formats"]}
        started = self._post("/v1/crawl", payload)
        # Firecrawl crawl is asynchronous: it returns a job id/url. Surface the
        # handle so the caller can poll, plus a convenience immediate status.
        job_id = started.get("id") or started.get("jobId")
        if not job_id:
            return {
                "success": bool(started.get("success", False)),
                "url": url,
                "raw": started,
            }
        status = self._get(f"/v1/crawl/{job_id}")
        return {
            "success": bool(status.get("success", True)),
            "url": url,
            "job_id": job_id,
            "status": status.get("status"),
            "completed": status.get("completed"),
            "total": status.get("total"),
            "pages": status.get("data", []),
        }

    def _search(self, params: dict[str, Any]) -> dict[str, Any]:
        query = params.get("query") or params.get("q") or params.get("text")
        if not query:
            return {"success": False, "error": "search requires a 'query'."}
        payload: dict[str, Any] = {"query": query}
        if params.get("limit") is not None:
            payload["limit"] = int(params["limit"])
        body = self._post("/v1/search", payload)
        return {
            "success": bool(body.get("success", True)),
            "query": query,
            "results": body.get("data", []),
        }
