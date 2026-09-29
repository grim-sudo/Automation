"""Tests for the web automation plugin's browser-open fast path.

A plain "open the browser" (optionally at a URL) is a launch, not a scripted
session. It must use the OS default browser — instant — rather than spinning up
a WebDriver-controlled Chrome, which downloads a driver and can take ~80s. These
tests lock that in and confirm scripted automation still opts into WebDriver.
"""

from __future__ import annotations

import pytest
from archon.core.engine import Archon
from archon.plugins import web_automation
from archon.plugins.web_automation import WebAutomationPlugin


def test_open_browser_uses_system_launcher_by_default(monkeypatch):
    plugin = WebAutomationPlugin()
    calls: list[str | None] = []

    def fake_system(url=None):
        calls.append(url)
        return True

    monkeypatch.setattr(plugin, "_open_system_browser", fake_system)

    res = plugin.execute("open_browser", {"url": "https://example.com"})

    assert res["success"] is True
    assert res["backend"] == "system"
    assert calls == ["https://example.com"]
    # The heavy WebDriver stack must not have been touched.
    assert plugin.driver is None
    assert plugin._system_browser_active is True


def test_open_browser_without_url_still_launches_system(monkeypatch):
    plugin = WebAutomationPlugin()
    monkeypatch.setattr(plugin, "_open_system_browser", lambda url=None: True)

    res = plugin.execute("open_browser", {})

    assert res["success"] is True
    assert res["backend"] == "system"


def test_scripted_automation_bypasses_system_browser(monkeypatch):
    # automation=True means the caller needs DOM control, so the system launcher
    # must be skipped in favor of a WebDriver. With both backends unavailable it
    # fails fast instead of silently using the system browser.
    plugin = WebAutomationPlugin()
    called = {"system": False}

    def fake_system(url=None):
        called["system"] = True
        return True

    monkeypatch.setattr(plugin, "_open_system_browser", fake_system)
    monkeypatch.setattr(web_automation, "HAS_SELENIUM", False)
    monkeypatch.setattr(web_automation, "HAS_PLAYWRIGHT", False)

    res = plugin.execute("open_browser", {"automation": True})

    assert called["system"] is False
    assert res["success"] is False


def test_open_system_browser_falls_back_to_xdg_open(monkeypatch):
    plugin = WebAutomationPlugin()
    import webbrowser

    monkeypatch.setattr(webbrowser, "open_new_tab", lambda *_a, **_k: False)

    popen_calls: list[list[str]] = []

    class _FakePopen:
        def __init__(self, args, **_kw):
            popen_calls.append(args)

    monkeypatch.setattr(web_automation.shutil, "which", lambda _n: "/usr/bin/xdg-open")
    monkeypatch.setattr(web_automation.subprocess, "Popen", _FakePopen)

    assert plugin._open_system_browser("https://example.com") is True
    assert popen_calls and popen_calls[0][0] == "/usr/bin/xdg-open"


# ── engine fast-path routing ─────────────────────────────────────────────────
# "open chrome and search for bread" must reach the one-shot system-browser
# perform_search, not a slow multi-step WebDriver plan. These exercise the
# engine's intent detector in isolation (the web action is stubbed) so the
# routing decision is what's under test.


@pytest.fixture(scope="module")
def engine():
    t = Archon()
    yield t
    t.shutdown()


@pytest.fixture
def captured_web(engine, monkeypatch):
    calls: list[tuple[str, dict]] = []

    def fake(action, params):
        calls.append((action, params))
        return {"success": True}

    monkeypatch.setattr(engine, "_run_web_action", fake)
    return calls


def test_browser_search_routes_to_perform_search(engine, captured_web):
    out = engine._maybe_browser_search("open chrome and search for bread")

    assert out is not None
    assert out["route"] == "web_automation.perform_search"
    assert captured_web == [("perform_search", {"query": "bread", "use_system_browser": True})]


def test_bare_google_verb_routes_to_search(engine, captured_web):
    out = engine._maybe_browser_search("google sourdough starter recipes")

    assert out["route"] == "web_automation.perform_search"
    assert captured_web[0][1]["query"] == "sourdough starter recipes"


def test_navigate_url_routes_to_open_browser(engine, captured_web):
    out = engine._maybe_browser_search("go to example.com")

    assert out["route"] == "web_automation.open_browser"
    assert captured_web == [("open_browser", {"url": "https://example.com"})]


def test_plain_open_browser_routes_to_launch(engine, captured_web):
    out = engine._maybe_browser_search("open firefox")

    assert out["route"] == "web_automation.open_browser"
    assert captured_web == [("open_browser", {"browser": "firefox"})]


def test_scripted_scrape_is_not_hijacked(engine, captured_web):
    # A scrape needs a real WebDriver — the fast path must decline it.
    assert engine._maybe_browser_search("open chrome and scrape example.com") is None
    assert captured_web == []


def test_filesystem_search_is_not_hijacked(engine, captured_web):
    assert engine._maybe_browser_search("search for a file named notes.txt") is None
    assert captured_web == []


def test_question_is_not_hijacked(engine, captured_web):
    # A how-to question is conversational, not a launch instruction.
    assert engine._maybe_browser_search("how do I google things effectively") is None
    assert captured_web == []


def test_plain_create_request_is_ignored(engine, captured_web):
    assert engine._maybe_browser_search("create a document about dogs") is None
    assert captured_web == []
