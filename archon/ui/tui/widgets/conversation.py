"""Conversation turn widgets: user, assistant, system, error and status.

The assistant widget supports live token streaming (plain text while
generating) and a final Markdown render on completion. It never displays model
chain-of-thought — only content the model emits as its answer.
"""

from __future__ import annotations

from rich.markdown import Markdown
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from .glyphs import GLYPHS


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
    """An assistant turn that streams tokens then renders Markdown."""

    def __init__(self) -> None:
        super().__init__(classes="turn archon-turn")
        self._buffer = ""
        self._final = False

    def compose(self) -> ComposeResult:
        yield Static(Text("ARCHON", style="#d9a441 bold"), classes="turn-label")
        yield Static("", classes="turn-body", id="assistant-body")

    @property
    def _body(self) -> Static:
        return self.query_one("#assistant-body", Static)

    def append_token(self, text: str) -> None:
        """Append a streamed fragment (plain text while generating)."""
        if self._final:
            return
        self._buffer += text
        self._body.update(Text(self._buffer, style="#d7dae0"))
        self.scroll_visible()

    def reset_stream(self) -> None:
        """Drop any preliminary text — used when a turn pivots to tool calls."""
        if self._final:
            return
        self._buffer = ""
        self._body.update("")

    def finalize(self, text: str) -> None:
        """Render the final answer as Markdown with highlighted code."""
        self._final = True
        clean = (text or "").strip()
        if not clean:
            self._body.update(Text("(no response)", style="#8a8f98"))
            return
        self._body.update(Markdown(clean, code_theme="ansi_dark"))


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
