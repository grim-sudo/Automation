"""Keyless public-API integrations curated for Archon.

A single, declarative capability over a hand-picked set of **no-auth** REST APIs
from the `public-apis <https://github.com/public-apis/public-apis>`_ catalogue —
the ones that actually earn their keep for a security-focused OS/dev assistant:
network & threat intel (IP geolocation, DNS, TLS, CVEs, malware URLs), package
registries (PyPI/npm/crates/GitHub), and general reference (countries, weather,
geocoding, dictionary, Wikipedia, FX rates).

Only APIs that need **no API key** are included — anything key-gated would just
fail silently without credentials the user hasn't supplied, so it has no place
being "integrated". Rather than a bespoke method per API, each endpoint is a
declarative entry: an action name mapped to a small builder that turns params
into an HTTP request. One generic ``execute`` runs them all through ``httpx``
(already a core dependency) and returns the raw JSON, which the model consumes.

Every call performs its own error handling and returns an honest
``{"success": False, ...}`` on failure, so the capability stays usable even when
an upstream service is down or rate-limiting.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, quote_plus

from loguru import logger

from archon.core.plugin_manager import AutomationPlugin

try:
    import httpx

    HAS_HTTPX = True
except ImportError:  # pragma: no cover - httpx is a core dep
    HAS_HTTPX = False

_DEFAULT_TIMEOUT = 20.0
_DEFAULT_USER_AGENT = "Archon/1.0 (+https://github.com/public-apis/public-apis)"

# Header some hosts (GitHub, Nominatim, Wikipedia REST) expect for JSON.
_JSON_ACCEPT = {"Accept": "application/json"}


class _MissingParam(ValueError):
    """Raised by a builder when a required parameter is absent."""


@dataclass(frozen=True)
class _Request:
    """A prepared HTTP request for one public-API action."""

    method: str
    url: str
    params: dict[str, Any] | None = None
    data: dict[str, Any] | None = None
    headers: dict[str, str] | None = None


@dataclass(frozen=True)
class _Endpoint:
    """Metadata + request builder for a single public API."""

    description: str
    build: Callable[[dict[str, Any]], _Request]


def _first(params: dict[str, Any], *keys: str) -> Any:
    """Return the first present, non-empty value among *keys*."""
    for key in keys:
        val = params.get(key)
        if val not in (None, ""):
            return val
    return None


def _require(params: dict[str, Any], *keys: str) -> Any:
    val = _first(params, *keys)
    if val is None:
        raise _MissingParam(f"missing required parameter: one of {list(keys)}")
    return val


# ── Endpoint registry ────────────────────────────────────────────────────────
# Ordered by domain. Each builder receives the raw params dict and returns a
# _Request. Keep builders one expression where possible — the laziness is the
# point: no per-API response parsing, the caller gets the upstream JSON.


def _b_ip_geolocation(p: dict[str, Any]) -> _Request:
    # IP is optional — omitting it geolocates the caller's own address.
    ip = _first(p, "ip", "address", "target")
    return _Request("GET", f"https://ipwho.is/{quote(str(ip))}" if ip else "https://ipwho.is/")


def _b_public_ip(_p: dict[str, Any]) -> _Request:
    return _Request("GET", "https://api.ipify.org", params={"format": "json"})


def _b_dns_lookup(p: dict[str, Any]) -> _Request:
    name = _require(p, "name", "domain", "host", "query")
    rtype = _first(p, "type", "record_type") or "A"
    return _Request(
        "GET",
        "https://dns.google/resolve",
        params={"name": str(name), "type": str(rtype).upper()},
    )


def _b_ssl_scan(p: dict[str, Any]) -> _Request:
    host = _require(p, "host", "domain", "target")
    return _Request(
        "GET",
        "https://api.ssllabs.com/api/v3/analyze",
        params={"host": str(host)},
    )


def _b_cve_lookup(p: dict[str, Any]) -> _Request:
    cve = _require(p, "cve", "cve_id", "id")
    return _Request(
        "GET",
        "https://services.nvd.nist.gov/rest/json/cves/2.0",
        params={"cveId": str(cve).upper()},
    )


def _b_malware_url_check(p: dict[str, Any]) -> _Request:
    # URLhaus takes a form POST, not a query string.
    url = _require(p, "url", "target")
    return _Request(
        "POST",
        "https://urlhaus-api.abuse.ch/v1/url/",
        data={"url": str(url)},
    )


def _b_github_repo(p: dict[str, Any]) -> _Request:
    # Accept "owner/repo" in a single field, or separate owner + repo.
    repo = _first(p, "repo", "repository", "name")
    owner = _first(p, "owner", "user")
    if owner and repo and "/" not in str(repo):
        slug = f"{owner}/{repo}"
    else:
        slug = str(_require(p, "repo", "repository", "name"))
    return _Request("GET", f"https://api.github.com/repos/{slug.strip('/')}", headers=_JSON_ACCEPT)


def _b_github_user(p: dict[str, Any]) -> _Request:
    user = _require(p, "username", "user", "owner", "name")
    return _Request(
        "GET", f"https://api.github.com/users/{quote(str(user))}", headers=_JSON_ACCEPT
    )


def _b_pypi_package(p: dict[str, Any]) -> _Request:
    pkg = _require(p, "package", "name", "project")
    return _Request("GET", f"https://pypi.org/pypi/{quote(str(pkg))}/json")


def _b_npm_package(p: dict[str, Any]) -> _Request:
    pkg = _require(p, "package", "name")
    # npm scoped names (@scope/name) must keep the slash unescaped.
    return _Request("GET", f"https://registry.npmjs.org/{quote(str(pkg), safe='@/')}")


def _b_crates_package(p: dict[str, Any]) -> _Request:
    crate = _require(p, "crate", "package", "name")
    return _Request("GET", f"https://crates.io/api/v1/crates/{quote(str(crate))}")


def _b_rest_countries(p: dict[str, Any]) -> _Request:
    name = _require(p, "name", "country", "query")
    return _Request("GET", f"https://restcountries.com/v3.1/name/{quote(str(name))}")


def _b_geocode(p: dict[str, Any]) -> _Request:
    query = _require(p, "query", "q", "address", "location")
    return _Request(
        "GET",
        "https://nominatim.openstreetmap.org/search",
        params={"q": str(query), "format": "jsonv2", "limit": p.get("limit", 5)},
    )


def _b_weather(p: dict[str, Any]) -> _Request:
    lat = _require(p, "latitude", "lat")
    lon = _require(p, "longitude", "lon", "lng")
    return _Request(
        "GET",
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": lat, "longitude": lon, "current_weather": "true"},
    )


def _b_dictionary(p: dict[str, Any]) -> _Request:
    word = _require(p, "word", "term", "query")
    lang = _first(p, "language", "lang") or "en"
    return _Request(
        "GET",
        f"https://api.dictionaryapi.dev/api/v2/entries/{quote(str(lang))}/{quote(str(word))}",
    )


def _b_wikipedia_summary(p: dict[str, Any]) -> _Request:
    title = _require(p, "title", "query", "topic", "term")
    return _Request(
        "GET",
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(str(title))}",
        headers=_JSON_ACCEPT,
    )


def _b_exchange_rates(p: dict[str, Any]) -> _Request:
    base = _first(p, "base", "from", "currency") or "USD"
    return _Request("GET", f"https://open.er-api.com/v6/latest/{quote(str(base).upper())}")


_ENDPOINTS: dict[str, _Endpoint] = {
    # Network / threat intelligence
    "ip_geolocation": _Endpoint(
        "Geolocate an IP address (or the caller's own IP if none given)", _b_ip_geolocation
    ),
    "public_ip": _Endpoint("Return the caller's public IP address", _b_public_ip),
    "dns_lookup": _Endpoint(
        "Resolve DNS records for a name via Google DNS-over-HTTPS", _b_dns_lookup
    ),
    "ssl_scan": _Endpoint("Analyse a host's TLS/SSL configuration via SSL Labs", _b_ssl_scan),
    "cve_lookup": _Endpoint(
        "Look up a CVE in the NIST National Vulnerability Database", _b_cve_lookup
    ),
    "malware_url_check": _Endpoint(
        "Check a URL against the URLhaus malicious-URL database", _b_malware_url_check
    ),
    # Package registries / dev
    "github_repo": _Endpoint("Fetch GitHub repository metadata", _b_github_repo),
    "github_user": _Endpoint("Fetch GitHub user/organisation metadata", _b_github_user),
    "pypi_package": _Endpoint("Fetch PyPI package metadata and versions", _b_pypi_package),
    "npm_package": _Endpoint("Fetch npm package metadata and versions", _b_npm_package),
    "crates_package": _Endpoint("Fetch crates.io (Rust) crate metadata", _b_crates_package),
    # General reference
    "rest_countries": _Endpoint("Look up country data by name", _b_rest_countries),
    "geocode": _Endpoint(
        "Forward-geocode an address/place via OpenStreetMap Nominatim", _b_geocode
    ),
    "weather": _Endpoint(
        "Current weather for a latitude/longitude via Open-Meteo", _b_weather
    ),
    "dictionary": _Endpoint("Look up a word's definition (Free Dictionary API)", _b_dictionary),
    "wikipedia_summary": _Endpoint("Fetch a Wikipedia article summary", _b_wikipedia_summary),
    "exchange_rates": _Endpoint(
        "Latest foreign-exchange rates for a base currency", _b_exchange_rates
    ),
}


class PublicApisPlugin(AutomationPlugin):
    """One capability exposing a curated set of keyless public REST APIs."""

    def __init__(self) -> None:
        self._timeout = _DEFAULT_TIMEOUT
        self._user_agent = _DEFAULT_USER_AGENT
        self._configure_from_settings()

    @property
    def name(self) -> str:
        return "public_apis"

    @property
    def description(self) -> str:
        return "Curated keyless public APIs: IP/DNS/TLS/CVE/malware intel, package registries, reference data"

    @property
    def version(self) -> str:
        return "1.0.0"

    def _configure_from_settings(self) -> None:
        try:
            from archon.config import get_settings

            cfg = get_settings().public_apis
            self._timeout = float(cfg.timeout or _DEFAULT_TIMEOUT)
            self._user_agent = cfg.user_agent or _DEFAULT_USER_AGENT
        except Exception as exc:  # noqa: BLE001 - fall back to defaults
            logger.debug("public_apis settings unavailable, using defaults: {}", exc)

    def get_capabilities(self) -> list[str]:
        if not HAS_HTTPX:
            return []
        return list(_ENDPOINTS.keys())

    def initialize(self) -> bool:
        # Load whenever httpx is present; per-call reachability is handled in
        # execute() so a down upstream never breaks discovery.
        return HAS_HTTPX

    def describe_actions(self) -> dict[str, str]:
        """Action -> human description, for help/discovery surfaces."""
        return {name: ep.description for name, ep in _ENDPOINTS.items()}

    def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        if not HAS_HTTPX:
            return {"success": False, "error": "httpx is not installed."}
        endpoint = _ENDPOINTS.get(action)
        if endpoint is None:
            return {"success": False, "error": f"Unknown public API action '{action}'."}

        params = params or {}
        try:
            req = endpoint.build(params)
        except _MissingParam as exc:
            return {"success": False, "error": f"{action}: {exc}"}

        headers = {"User-Agent": self._user_agent}
        if req.headers:
            headers.update(req.headers)

        try:
            with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
                resp = client.request(
                    req.method,
                    req.url,
                    params=req.params,
                    data=req.data,
                    headers=headers,
                )
                resp.raise_for_status()
                data = self._parse_body(resp)
        except httpx.HTTPStatusError as exc:
            return {
                "success": False,
                "action": action,
                "status_code": exc.response.status_code,
                "error": f"{action} request returned HTTP {exc.response.status_code}.",
            }
        except httpx.HTTPError as exc:
            return {"success": False, "action": action, "error": f"{action} request failed: {exc}"}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "action": action, "error": f"{action} error: {exc}"}

        return {"success": True, "action": action, "data": data}

    @staticmethod
    def _parse_body(resp: httpx.Response) -> Any:
        """Return parsed JSON, or raw text when the body isn't JSON."""
        ctype = resp.headers.get("content-type", "")
        if "json" in ctype:
            return resp.json()
        try:
            return resp.json()
        except Exception:  # noqa: BLE001 - some hosts mislabel JSON; else give text
            return {"text": resp.text}
