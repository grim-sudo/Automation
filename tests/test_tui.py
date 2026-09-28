"""Tests for the Textual TUI layer and the streaming path that feeds it.

These lock the behaviour the UI depends on without touching a live model:

* streaming forwards only ``content`` fragments (never hidden ``thinking``);
* tool calls still accumulate through a stream;
* real generation stats are surfaced;
* the app streams tokens into the assistant turn, reflects tool events in the
  execution view, finalises on completion and re-enables input;
* a cancelled run's late messages are dropped via the generation counter.
"""

from __future__ import annotations

import json

import pytest

# ─── streaming: mocked httpx NDJSON ─────────────────────────────────────────


class _FakeStreamResponse:
    """Minimal async stand-in for httpx's streaming response."""

    def __init__(self, lines: list[str], status_code: int = 200) -> None:
        self._lines = lines
        self.status_code = status_code

    async def __aenter__(self) -> _FakeStreamResponse:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    async def aread(self) -> bytes:
        return b""


class _FakeClient:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    async def __aenter__(self) -> _FakeClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    def stream(self, method: str, url: str, json: dict | None = None):
        return _FakeStreamResponse(self._lines)


@pytest.mark.asyncio
async def test_stream_forwards_content_not_thinking(monkeypatch):
    from archon.ai import ollama_integration as oi

    # A reasoning model emits hidden `thinking` deltas first, then `content`,
    # then a tool call, then a done-object with real stats.
    lines = [
        json.dumps({"message": {"thinking": "let me think"}}),
        json.dumps({"message": {"content": "Hello "}}),
        json.dumps({"message": {"content": "world"}}),
        json.dumps(
            {
                "message": {
                    "tool_calls": [
                        {"function": {"name": "filesystem.read_file", "arguments": {}}}
                    ]
                }
            }
        ),
        json.dumps(
            {"done": True, "eval_count": 20, "eval_duration": 1_000_000_000}
        ),
    ]
    monkeypatch.setattr(
        oi.httpx, "AsyncClient", lambda *a, **k: _FakeClient(lines)
    )

    tokens: list[str] = []
    stats: dict = {}
    provider = oi.OllamaProvider(model="fake")
    message = await provider.chat(
        [{"role": "user", "content": "hi"}],
        on_token=tokens.append,
        on_stats=stats.update,
    )

    # Only content was streamed — the hidden `thinking` delta never leaked.
    assert tokens == ["Hello ", "world"]
    assert message["content"] == "Hello world"
    # Tool calls survived the stream and are on the assembled message.
    assert message["tool_calls"][0]["function"]["name"] == "filesystem.read_file"
    # Real tok/s came from the done-object: 20 tokens / 1s.
    assert stats["tokens_per_sec"] == pytest.approx(20.0)


def test_extract_stats_omits_missing_fields():
    from archon.ai.ollama_integration import _extract_stats

    # No eval data → no fabricated tokens/sec.
    assert "tokens_per_sec" not in _extract_stats({})
    # Zero duration must not divide-by-zero.
    assert "tokens_per_sec" not in _extract_stats(
        {"eval_count": 5, "eval_duration": 0}
    )
    stats = _extract_stats({"eval_count": 10, "eval_duration": 2_000_000_000})
    assert stats["tokens_per_sec"] == pytest.approx(5.0)


# ─── app: pipeline with a fake controller ───────────────────────────────────


class _FakeController:
    """A controller double that scripts a realistic turn without a model."""

    def __init__(self) -> None:
        self.on_event = None
        self.confirmer = None
        self.shutdown_called = False

    def run(self, message, *, on_token=None, on_stats=None):
        self.on_event({"kind": "phase", "phase": "EXECUTING"})
        self.on_event(
            {"kind": "tool_start", "name": "filesystem.create_file", "args": {}}
        )
        self.on_event({"kind": "tool_ok", "name": "filesystem.create_file"})
        if on_token:
            for tok in ["Hello ", "there."]:
                on_token(tok)
        if on_stats:
            on_stats({"tokens_per_sec": 20.0})
        return "Hello there. Done."

    def intelligence(self):
        return {"model": "fake", "backend": "Ollama", "online": True}

    def context_usage(self):
        return (100, 8000)

    def plugin_count(self):
        return 5

    def capability_count(self):
        return 14

    def shutdown(self):
        self.shutdown_called = True


async def _drain_turn(app, pilot, text: str) -> None:
    app._start_turn(text)
    for _ in range(60):
        await pilot.pause(0.05)
        if not app._busy:
            return
    raise AssertionError("turn did not complete")


@pytest.mark.asyncio
async def test_app_streams_and_finalizes_turn():
    from archon.ui.tui.app import ArchonApp
    from archon.ui.tui.widgets import AssistantMessage, ExecutionView, UserMessage

    app = ArchonApp()
    app.controller = _FakeController()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(1.8)  # let the startup splash dismiss
        await _drain_turn(app, pilot, "create a pizza doc")

        user = app.query_one(UserMessage)
        assert user is not None
        assistant = app.query_one(AssistantMessage)
        assert assistant._final is True
        assert assistant._buffer == "Hello there."  # streamed content only

        execution = app.query_one(ExecutionView)
        assert execution._count == 1  # one real tool op recorded
        assert app._busy is False  # input re-enabled


@pytest.mark.asyncio
async def test_app_drops_stale_messages_after_cancel():
    from archon.ui.tui import events as ev
    from archon.ui.tui.app import ArchonApp
    from archon.ui.tui.widgets import AssistantMessage

    app = ArchonApp()
    app.controller = _FakeController()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(1.8)
        # Start a turn, then bump the generation as a cancel would.
        app._busy = True
        app._gen = 5
        from archon.ui.tui.widgets import UserMessage
        from textual.containers import VerticalScroll

        conv = app.query_one("#conversation", VerticalScroll)
        conv.mount(UserMessage("q"))
        assistant = AssistantMessage()
        conv.mount(assistant)
        app._current_assistant = assistant
        await pilot.pause(0.05)

        # A token tagged with the *old* generation must be ignored.
        app.post_message(ev.TokenReceived(4, "stale"))
        await pilot.pause(0.05)
        assert assistant._buffer == ""

        # A token for the current generation is applied.
        app.post_message(ev.TokenReceived(5, "fresh"))
        await pilot.pause(0.05)
        assert assistant._buffer == "fresh"


@pytest.mark.asyncio
async def test_assistant_working_indicator_lifecycle():
    """The spinner animates while quiet, stops on first token, and on cancel."""
    from archon.ui.tui.app import ArchonApp
    from archon.ui.tui.widgets import AssistantMessage
    from textual.containers import VerticalScroll

    app = ArchonApp()
    app.controller = _FakeController()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(1.8)
        conv = app.query_one("#conversation", VerticalScroll)

        # A fresh, quiet turn spins while it waits for content.
        assistant = AssistantMessage()
        conv.mount(assistant)
        await pilot.pause(0.15)
        assert assistant._spin_timer is not None
        assert assistant._final is False

        # First visible token replaces the spinner and stops the timer.
        assistant.append_token("Hi")
        await pilot.pause(0.05)
        assert assistant._spin_timer is None
        assert assistant._buffer == "Hi"

        # A second, still-quiet turn that gets cancelled: spinner stops, the
        # turn is marked final, and a note is left in place of a frozen frame.
        other = AssistantMessage()
        conv.mount(other)
        await pilot.pause(0.15)
        assert other._spin_timer is not None
        other.cancel_working("(cancelled)")
        await pilot.pause(0.05)
        assert other._spin_timer is None
        assert other._final is True
        # A late token after cancel is ignored.
        other.append_token("stale")
        assert other._buffer == ""


@pytest.mark.asyncio
async def test_app_toggles_and_clear():
    from archon.ui.tui.app import ArchonApp
    from archon.ui.tui.widgets import ActivityLog
    from textual.containers import VerticalScroll

    app = ArchonApp()
    app.controller = _FakeController()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(1.8)

        sidebar = app.query_one("#sidebar", VerticalScroll)
        assert sidebar.display is True
        app.action_toggle_sidebar()
        await pilot.pause(0.05)
        assert sidebar.display is False

        activity = app.query_one("#activity", ActivityLog)
        assert activity.display is False
        app.action_toggle_activity()
        await pilot.pause(0.05)
        assert activity.display is True

        # Clearing empties the transcript back to a single system note.
        await _drain_turn(app, pilot, "hi")
        app.action_clear_conversation()
        await pilot.pause(0.05)
        conv = app.query_one("#conversation", VerticalScroll)
        assert app._current_assistant is None
        assert len(conv.children) == 1  # just the "cleared" system note
