"""Execution widgets: a live, collapsible view of real tool activity.

``ExecutionView`` owns a set of ``ToolCallView`` rows and reflects only events
that actually happened in the agent loop (a tool started, succeeded or failed).
``PlanView`` renders an ordered plan when the planner surfaces one; it is never
populated with invented steps.
"""

from __future__ import annotations

import time
from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Collapsible, Static

from .glyphs import GLYPHS, PENDING


class ToolCallView(Static):
    """One tool operation row: glyph + name + elapsed time."""

    def __init__(self, name: str, state: str = "run") -> None:
        super().__init__(classes="tool-row")
        self._name = name
        self._state = state  # "pending" | "run" | "ok" | "err"
        self._error = ""
        self._start = time.monotonic()
        self._elapsed: float | None = None

    def _glyph(self) -> Text:
        if self._state == "ok":
            return Text(GLYPHS.ok, style="#5fae7f")
        if self._state == "err":
            return Text(GLYPHS.err, style="#cc6666")
        if self._state == "pending":
            return Text(PENDING, style="#4b4f57")
        return Text(GLYPHS.running, style="#8a8f98")

    def _elapsed_text(self) -> str:
        if self._elapsed is not None:
            return f"{self._elapsed:.2f}s"
        if self._state == "run":
            return f"{time.monotonic() - self._start:.1f}s"
        return ""

    def render(self) -> Text:
        line = Text()
        line.append_text(self._glyph())
        line.append(f"  {self._name}", style="#d7dae0" if self._state != "err" else "#cc6666")
        elapsed = self._elapsed_text()
        if elapsed:
            line.append(f"   {elapsed}", style="#4b4f57")
        if self._error:
            line.append(f"\n     {self._error}", style="#cc6666")
        return line

    def mark_ok(self) -> None:
        self._state = "ok"
        self._elapsed = time.monotonic() - self._start
        self.refresh()

    def mark_error(self, error: str) -> None:
        self._state = "err"
        self._error = error
        self._elapsed = time.monotonic() - self._start
        self.refresh()

    @property
    def name(self) -> str:
        return self._name

    @property
    def running(self) -> bool:
        return self._state == "run"


class ExecutionView(Collapsible):
    """A collapsible panel of live tool rows plus a completion summary."""

    def __init__(self) -> None:
        super().__init__(title="EXECUTION", collapsed=False, classes="execution")
        self._rows: list[ToolCallView] = []
        self._count = 0
        self._start = time.monotonic()
        self._done = False

    def compose(self) -> ComposeResult:
        # Collapsible yields its own contents; we provide a rows container and
        # a summary line.
        yield Vertical(id="exec-rows")
        yield Static("", id="exec-summary", classes="exec-summary")

    def _set_title(self, text: str) -> None:
        self.title = text

    def start_tool(self, name: str, args: dict[str, Any] | None = None) -> None:
        self._set_title("EXECUTION · RUNNING")
        row = ToolCallView(name)
        self._rows.append(row)
        self.query_one("#exec-rows", Vertical).mount(row)
        row.scroll_visible()

    def finish_tool(self, name: str, ok: bool, error: str = "") -> None:
        for row in reversed(self._rows):
            if row.name == name and row.running:
                if ok:
                    row.mark_ok()
                else:
                    row.mark_error(error)
                self._count += 1
                return
        # Completion without a matching start still shows, so nothing is lost.
        row = ToolCallView(name, state="ok" if ok else "err")
        if not ok:
            row._error = error
        self._rows.append(row)
        self.query_one("#exec-rows", Vertical).mount(row)
        self._count += 1

    def tick(self) -> None:
        """Refresh running-row timers; called on an interval by the app."""
        for row in self._rows:
            if row.running:
                row.refresh()

    def complete(self) -> None:
        if self._done:
            return
        self._done = True
        elapsed = time.monotonic() - self._start
        n = self._count
        if n:
            self._set_title("EXECUTION · COMPLETE")
            noun = "operation" if n == 1 else "operations"
            self.query_one("#exec-summary", Static).update(
                Text(f"{n} {noun} · {elapsed:.1f}s", style="#8a6d3b")
            )
        else:
            # No tools ran — the model answered directly. Hide the panel.
            self.display = False


class PlanView(Vertical):
    """An ordered plan block. Only rendered from real planner steps."""

    def __init__(self, steps: list[str]) -> None:
        super().__init__(classes="plan")
        self._steps = steps

    def compose(self) -> ComposeResult:
        yield Static(Text("PLAN", style="#8a6d3b bold"), classes="plan-label")
        body = Text()
        for i, step in enumerate(self._steps, 1):
            body.append(f"{i:02d}  ", style="#8a6d3b")
            body.append(f"{step}\n", style="#d7dae0")
        yield Static(body, classes="plan-body")
