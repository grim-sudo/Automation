"""Conversation turn widgets: user, assistant, system, error and status.

The assistant widget supports live token streaming (plain text while
generating) and a final Markdown render on completion. It never displays model
chain-of-thought — only content the model emits as its answer.
"""

from __future__ import annotations

import time

from rich.markdown import Markdown
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.timer import Timer
from textual.widgets import Static

from .glyphs import GLYPHS, SPINNER


class UserMessage(Vertical):
    """A submitted user turn, echoed for a readable scrollback."""

    def __init__(self, text: str) -> None:
        super().__init__(classes="turn user-turn")
        self._text = text

    def compose(self) -> ComposeResult:
        yield Static(Text("YOU", style="#b8bec9 bold"), classes="turn-label")
        body = Text()
        body.append(f"{GLYPHS.prompt} ", style="#8a6d3b")
        body.append(self._text, style="#d7dae0")
        yield Static(body, classes="turn-body")


class AssistantMessage(Vertical):
    """An assistant turn that streams tokens then renders Markdown.

    While the model is working but has produced no visible text yet (e.g. a
    reasoning model emitting hidden ``thinking`` tokens, or a tool round in
    progress), an animated spinner with an elapsed-time counter is shown so the
    user always sees that something is happening.
    """

    def __init__(self) -> None:
        super().__init__(classes="turn archon-turn")
        self._buffer = ""
        self._final = False
        self._phase = "Thinking"
        self._frame = 0
        self._start = time.monotonic()
        self._spin_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Static(Text("ARCHON", style="#d9a441 bold"), classes="turn-label")
        yield Static("", classes="turn-body", id="assistant-body")

    def on_mount(self) -> None:
        self.start_working()

    @property
    def _body(self) -> Static:
        return self.query_one("#assistant-body", Static)

    # ── working indicator ─────────────────────────────────────────────────────

    def start_working(self, phase: str = "Thinking") -> None:
        """Begin (or resume) the animated spinner until real text arrives."""
        if self._final:
            return
        self._phase = phase
        self._start = time.monotonic()
        if self._spin_timer is None:
            self._spin_timer = self.set_interval(0.1, self._tick_spinner)
        self._tick_spinner()

    def set_phase(self, phase: str) -> None:
        """Relabel the spinner (e.g. 'Executing', 'Writing') without resetting."""
        self._phase = phase

    def _stop_working(self) -> None:
        if self._spin_timer is not None:
            self._spin_timer.stop()
            self._spin_timer = None

    def _tick_spinner(self) -> None:
        # Once real content exists (or the turn is done), the text is the
        # indicator; stop spinning.
        if self._final or self._buffer:
            self._stop_working()
            return
        self._frame = (self._frame + 1) % len(SPINNER)
        elapsed = time.monotonic() - self._start
        line = Text()
        line.append(f"{SPINNER[self._frame]} ", style="#d9a441")
        line.append(f"{self._phase}\u2026 ", style="#8a8f98")
        line.append(f"{elapsed:.0f}s", style="#4b4f57")
        self._body.update(line)

    # ── streaming ───────────────────────────────────────────────────────────────

    def append_token(self, text: str) -> None:
        """Append a streamed fragment (plain text while generating)."""
        if self._final:
            return
        self._stop_working()  # first visible token replaces the spinner
        self._buffer += text
        self._body.update(Text(self._buffer, style="#d7dae0"))
        self.scroll_visible()

    def reset_stream(self) -> None:
        """Drop any preliminary text — used when a turn pivots to tool calls."""
        if self._final:
            return
        self._buffer = ""
        self._body.update("")
        # Back to waiting on the model: show the spinner again.
        self.start_working("Executing")

    def finalize(self, text: str) -> None:
        """Render the final answer as Markdown with highlighted code."""
        self._final = True
        self._stop_working()
        clean = (text or "").strip()
        if not clean:
            self._body.update(Text("(no response)", style="#8a8f98"))
            return
        self._body.update(Markdown(clean, code_theme="ansi_dark"))

    def cancel_working(self, note: str = "(cancelled)") -> None:
        """Stop the spinner on an abandoned turn (cancel or failure).

        Marks the turn final so late tokens are ignored, and leaves a quiet
        note in place of a frozen spinner frame if no text had arrived yet.
        """
        self._final = True
        self._stop_working()
        if not self._buffer:
            self._body.update(Text(note, style="#8a8f98 italic"))


class SystemMessage(Static):
    """A quiet, italic system/info line in the transcript."""

    def __init__(self, text: str) -> None:
        super().__init__(Text(text, style="#8a8f98 italic"), classes="system-line")


class StatusView(Static):
    """A one-line operational status note (e.g. 'Cancelled')."""

    def __init__(self, text: str) -> None:
        super().__init__(Text(text, style="#8a8f98"), classes="status-line")


class ErrorView(Vertical):
    """A human-readable error block; tracebacks stay in the log file."""

    def __init__(self, summary: str, reason: str = "", action: str = "") -> None:
        super().__init__(classes="turn error-turn")
        self._summary = summary
        self._reason = reason
        self._action = action

    def compose(self) -> ComposeResult:
        yield Static(Text("ARCHON · ERROR", style="#cc6666 bold"), classes="turn-label")
        body = Text()
        body.append(self._summary, style="#d7dae0")
        if self._reason:
            body.append("\nReason  ", style="#8a8f98")
            body.append(self._reason, style="#d7dae0")
        if self._action:
            body.append("\nTry     ", style="#8a8f98")
            body.append(self._action, style="#d7dae0")
        yield Static(body, classes="turn-body")
