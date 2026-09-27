"""Tests for the console presentation/input layer.

Covers the pure-presentation pieces added in the console redesign:
- :mod:`archon.ui.events` convenience constructors,
- :class:`archon.ui.renderer.OpsView` event bookkeeping (real state only),
- :class:`archon.ui.renderer.Renderer` rendering onto a captured console,
- :class:`archon.ui.theme` glyph selection / ASCII fallback.

These assert on rendered text and internal state, never on engine internals —
the layer stays presentational.
"""

from __future__ import annotations

from archon.ui import events
from archon.ui.events import EventKind
from archon.ui.renderer import OpsView, Renderer
from archon.ui.theme import Glyphs, make_console, supports_unicode

# ── events vocabulary ────────────────────────────────────────────────────────


def test_event_constructors_set_kind_and_fields():
    assert events.phase("EXECUTING").kind is EventKind.PHASE
    assert events.start("docker.ps", detail="all").label == "docker.ps"
    assert events.ok("docker.ps").kind is EventKind.OK
    err = events.error("docker.inspect", "permission denied")
    assert err.kind is EventKind.ERROR
    assert err.error == "permission denied"


# ── OpsView state machine (real events only) ─────────────────────────────────


def test_opsview_tracks_start_then_ok():
    view = OpsView(make_console(), Glyphs.unicode())
    view.handle(events.phase("EXECUTING"))
    view.handle(events.start("docker.ps"))
    view.handle(events.ok("docker.ps"))

    assert view._phase == "EXECUTING"
    assert len(view._ops) == 1
    assert view._ops[0].state == "ok"


def test_opsview_marks_matching_start_as_error():
    view = OpsView(make_console(), Glyphs.unicode())
    view.handle(events.start("docker.inspect"))
    view.handle(events.error("docker.inspect", "permission denied"))

    op = view._ops[0]
    assert op.state == "err"
    assert op.error == "permission denied"


def test_opsview_completion_without_start_is_not_lost():
    view = OpsView(make_console(), Glyphs.unicode())
    # An OK with no preceding START still records an op (nothing swallowed).
    view.handle(events.ok("filesystem.read"))

    assert len(view._ops) == 1
    assert view._ops[0].state == "ok"


def test_opsview_second_start_gets_its_own_row():
    view = OpsView(make_console(), Glyphs.unicode())
    view.handle(events.start("a"))
    view.handle(events.ok("a"))
    view.handle(events.start("a"))  # same label, new operation

    # Two distinct ops: the first ok, the second still running.
    assert [o.state for o in view._ops] == ["ok", "run"]


# ── Renderer output ──────────────────────────────────────────────────────────


def _capture(fn) -> str:
    console = make_console(width=80)
    r = Renderer(console)
    with console.capture() as cap:
        fn(r)
    return cap.get()


def test_startup_renders_facts_without_ascii_logo():
    text = _capture(
        lambda r: r.startup(
            {
                "system": "Arch Linux",
                "model": "qwen3.5:9b",
                "backend": "Ollama",
                "plugins": "5 active",
                "status": "ONLINE",
            }
        )
    )
    assert "ARCHON" in text
    assert "qwen3.5:9b" in text
    assert "ONLINE" in text
    # No giant ASCII banner: the identity line stays a single short mark.
    assert "======" not in text


def test_assistant_turn_renders_markdown():
    text = _capture(lambda r: r.assistant_turn("**bold** and `code`"))
    assert "ARCHON" in text
    assert "bold" in text


def test_assistant_turn_empty_shows_placeholder():
    text = _capture(lambda r: r.assistant_turn("   "))
    assert "(no response)" in text


def test_error_block_shows_reason_and_action():
    text = _capture(
        lambda r: r.error_block(
            "Unable to execute docker.inspect.",
            reason="Docker daemon is unavailable.",
            action="Start Docker and try again.",
        )
    )
    assert "ERROR" in text
    assert "Docker daemon is unavailable." in text
    assert "Start Docker and try again." in text


# ── theme / glyphs ───────────────────────────────────────────────────────────


def test_ascii_override_forces_ascii_glyphs(monkeypatch):
    monkeypatch.setenv("ARCHON_ASCII", "1")
    assert supports_unicode() is False


def test_unicode_and_ascii_glyph_sets_differ():
    uni = Glyphs.unicode()
    asc = Glyphs.ascii()
    assert uni.ok != asc.ok
    assert asc.brand.isascii()
