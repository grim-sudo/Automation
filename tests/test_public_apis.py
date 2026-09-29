"""Tests for the curated keyless public-API plugin.

The HTTP boundary is mocked; these verify capability discovery, per-action
request building (method/URL/params/body), argument validation, and honest
failure on HTTP errors.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from archon.plugins.public_apis import _ENDPOINTS, PublicApisPlugin


def _mock_response(json_body=None, *, content_type="application/json", text="", status=200):
    resp = MagicMock()
    resp.headers = {"content-type": content_type}
    resp.status_code = status
    resp.text = text
    resp.json.return_value = json_body if json_body is not None else {}
    resp.raise_for_status.return_value = None
    return resp


def _capture_request(plugin, action, params):
    """Run execute() with httpx.Client mocked; return (result, request_kwargs)."""
    resp = _mock_response({"ok": True})
    with patch("httpx.Client") as client_cls:
        client = client_cls.return_value.__enter__.return_value
        client.request.return_value = resp
        result = plugin.execute(action, params)
        call = client.request.call_args
    return result, call


def test_capabilities_and_identity():
    p = PublicApisPlugin()
    assert p.name == "public_apis"
    caps = p.get_capabilities()
    # Every registered endpoint is advertised.
    assert set(caps) == set(_ENDPOINTS.keys())
    assert "ip_geolocation" in caps
    assert "cve_lookup" in caps


def test_describe_actions_covers_all():
    p = PublicApisPlugin()
    described = p.describe_actions()
    assert set(described.keys()) == set(_ENDPOINTS.keys())
    assert all(isinstance(v, str) and v for v in described.values())


def test_unknown_action():
    p = PublicApisPlugin()
    res = p.execute("teleport", {})
    assert res["success"] is False
    assert "Unknown" in res["error"]


def test_missing_required_param():
    p = PublicApisPlugin()
    res = p.execute("dns_lookup", {})
    assert res["success"] is False
    assert "required parameter" in res["error"]


def test_dns_lookup_builds_google_doh_request():
    p = PublicApisPlugin()
    result, call = _capture_request(p, "dns_lookup", {"name": "example.com", "type": "aaaa"})
    method, url = call.args
    assert method == "GET"
    assert url == "https://dns.google/resolve"
    assert call.kwargs["params"] == {"name": "example.com", "type": "AAAA"}
    assert result["success"] is True
    assert result["action"] == "dns_lookup"


def test_ip_geolocation_without_ip_targets_self():
    p = PublicApisPlugin()
    _, call = _capture_request(p, "ip_geolocation", {})
    _, url = call.args
    assert url == "https://ipwho.is/"


def test_ip_geolocation_with_ip():
    p = PublicApisPlugin()
    _, call = _capture_request(p, "ip_geolocation", {"ip": "1.2.3.4"})
    _, url = call.args
    assert url == "https://ipwho.is/1.2.3.4"


def test_malware_url_check_posts_form():
    p = PublicApisPlugin()
    _, call = _capture_request(p, "malware_url_check", {"url": "http://bad.example"})
    method, url = call.args
    assert method == "POST"
    assert url == "https://urlhaus-api.abuse.ch/v1/url/"
    assert call.kwargs["data"] == {"url": "http://bad.example"}


def test_github_repo_accepts_owner_and_repo():
    p = PublicApisPlugin()
    _, call = _capture_request(p, "github_repo", {"owner": "torvalds", "repo": "linux"})
    _, url = call.args
    assert url == "https://api.github.com/repos/torvalds/linux"


def test_github_repo_accepts_slug():
    p = PublicApisPlugin()
    _, call = _capture_request(p, "github_repo", {"repo": "torvalds/linux"})
    _, url = call.args
    assert url == "https://api.github.com/repos/torvalds/linux"


def test_npm_scoped_package_keeps_slash():
    p = PublicApisPlugin()
    _, call = _capture_request(p, "npm_package", {"package": "@types/node"})
    _, url = call.args
    assert url == "https://registry.npmjs.org/@types/node"


def test_user_agent_header_always_sent():
    p = PublicApisPlugin()
    _, call = _capture_request(p, "public_ip", {})
    assert call.kwargs["headers"]["User-Agent"].startswith("Archon/")


def test_http_status_error_is_honest():
    import httpx

    p = PublicApisPlugin()
    err_resp = _mock_response(status=404)
    with patch("httpx.Client") as client_cls:
        client = client_cls.return_value.__enter__.return_value
        client.request.side_effect = httpx.HTTPStatusError(
            "not found", request=MagicMock(), response=err_resp
        )
        res = p.execute("cve_lookup", {"cve": "CVE-2021-44228"})
    assert res["success"] is False
    assert res["status_code"] == 404


def test_connection_error_is_honest():
    import httpx

    p = PublicApisPlugin()
    with patch("httpx.Client") as client_cls:
        client = client_cls.return_value.__enter__.return_value
        client.request.side_effect = httpx.ConnectError("refused")
        res = p.execute("weather", {"lat": 51.5, "lon": -0.1})
    assert res["success"] is False
    assert "failed" in res["error"]


def test_non_json_body_falls_back_to_text():
    p = PublicApisPlugin()
    resp = _mock_response(content_type="text/plain", text="1.2.3.4")
    resp.json.side_effect = ValueError("not json")
    with patch("httpx.Client") as client_cls:
        client = client_cls.return_value.__enter__.return_value
        client.request.return_value = resp
        res = p.execute("public_ip", {})
    assert res["success"] is True
    assert res["data"] == {"text": "1.2.3.4"}
