"""Presentation layer for the Archon console.

Turns high-level state — startup info, conversation turns, execution events,
errors — into restrained Rich output. This module renders; it never decides.
All rendering input arrives as plain data or :class:`~archon.ui.events.UIEvent`
records, so no engine/business logic leaks in here.
"""

from __future__ import annotations

from dataclasses import dataclass

from rich.console import Console, Group, RenderableType
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from .events import Channel, EventKind, UIEvent
from .theme import Glyphs, glyphs_for, make_console


class Renderer:
    """Draws the Archon console. Presentation only."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or make_console()
        self.glyphs: Glyphs = glyphs_for(self.console)

    # ── Chrome ────────────────────────────────────────────────────────────────

    def rule(self, width: int = 48) -> None:
        self.console.print(Text(self.glyphs.rule * width, style="archon.rule"))

    def startup(self, info: dict[str, str]) -> None:
        """Compact, intentional startup block (no giant ASCII logo).

        *info* keys used: ``system``, ``model``, ``backend``, ``plugins``,
        ``status``, ``online`` (bool-ish).
        """
        g = self.glyphs
        online = str(info.get("status", "")).upper() == "ONLINE"
        brand = Text()
        brand.append(f"{g.brand} ", style="archon.accent")
        brand.append("ARCHON", style="archon.accent")
        self.console.print(brand)
        self.console.print(Text("One to rule them all.", style="archon.dim"))
        self.console.print()
        self.rule()

        table = Table(show_header=False, box=None, padding=(0, 3, 0, 0))
        table.add_column(style="archon.dim", no_wrap=True)
        table.add_column(style="archon.text")
        for key in ("system", "model", "backend", "plugins"):
            if info.get(key):
                table.add_row(key.upper(), str(info[key]))
        status_style = "archon.ok" if online else "archon.warn"
        table.add_row(
            "STATUS",
            Text(f"{g.online} {info.get('status', 'UNKNOWN')}", style=status_style),
        )
        self.console.print(table)
        self.rule()
        self.console.print(Text("Ready.", style="archon.dim"))
        self.console.print()

    def header_line(self, model: str, backend: str, online: bool) -> None:
        """A one-line identity/state header for ``/clear`` and reconnects."""
        g = self.glyphs
        line = Text()
        line.append(f"{g.brand} ARCHON", style="archon.accent")
        line.append("   ", style="archon.dim")
        line.append(f"LOCAL \u2022 {model.upper()}", style="archon.dim")
        line.append("   ", style="archon.dim")
        state = "ONLINE" if online else "OFFLINE"
        line.append(f"{g.online} {state}", style="archon.ok" if online else "archon.warn")
        self.console.print(line)
        self.rule()

    # ── Conversation ────────────────────────────────────────────────────────────

    def user_turn(self, text: str) -> None:
        """Echo a user message with a distinct, quiet label.

        (The composer already shows what was typed live; this keeps the
        transcript readable when scrolling back.)
        """
        self.console.print()
        self.console.print(Text("YOU", style="archon.user"))
        body = Text()
        body.append(f"{self.glyphs.prompt} ", style="archon.accent.dim")
        body.append(text, style="archon.text")
        self.console.print(body)

    def assistant_turn(self, markdown_text: str) -> None:
        """Render an assistant reply as Markdown with syntax-highlighted code."""
        self.console.print()
        self.console.print(Text("ARCHON", style="archon.accent"))
        text = (markdown_text or "").strip()
        if not text:
            self.console.print(Text("(no response)", style="archon.dim"))
            return
        self.console.print(Markdown(text, code_theme="ansi_dark"))

    def note(self, text: str) -> None:
        self.console.print(Text(text, style="archon.dim"))

    # ── Errors ────────────────────────────────────────────────────────────────

    def error_block(self, summary: str, reason: str = "", action: str = "") -> None:
        """Human-readable error. Full tracebacks stay in the logging system."""
        self.console.print()
        self.console.print(Text("ARCHON \u00b7 ERROR", style="archon.err"))
        self.console.print(Text(summary, style="archon.text"))
        if reason:
            self.console.print(Text("Reason", style="archon.dim"))
            self.console.print(Text(f"  {reason}", style="archon.text"))
        if action:
            self.console.print(Text("Suggested action", style="archon.dim"))
            self.console.print(Text(f"  {action}", style="archon.text"))

    # ── Status bar ──────────────────────────────────────────────────────────────

    def status_bar(self, fields: list[str]) -> None:
        g = self.glyphs
        sep = Text(" \u2502 ", style="archon.dim")
        line = Text(f"{g.brand} ", style="archon.accent.dim")
        for i, field in enumerate(fields):
            if i:
                line.append_text(sep)
            line.append(field, style="archon.dim")
        self.console.print(line)

    # ── Live execution view ─────────────────────────────────────────────────────

    def ops_view(self) -> OpsView:
        """Create a live tool-execution view bound to this renderer's console."""
        return OpsView(self.console, self.glyphs)


@dataclass
class _Op:
    label: str
    state: str  # "run" | "ok" | "err"
    channel: Channel
    error: str = ""


class OpsView:
    """Live, in-place view of real execution events.

    Consumes :class:`UIEvent` records and renders the operational transcript:

        ARCHON \u00b7 EXECUTING
        \u2713 docker.list_containers
        \u25c7 docker.inspect

    Exposes :meth:`start`/:meth:`stop` so a caller can pause the live refresh
    while prompting for confirmation (a running live display owns the terminal
    and would otherwise swallow the prompt).
    """

    def __init__(self, console: Console, glyphs: Glyphs) -> None:
        self._console = console
        self._g = glyphs
        self._ops: list[_Op] = []
        self._phase: str = ""
        self._channel: Channel = Channel.ARCHON
        self._live: object | None = None
        self._spinner = Spinner("dots", style="archon.dim")

    # -- lifecycle -------------------------------------------------------------

    def __enter__(self) -> OpsView:
        from rich.live import Live

        self._live = Live(
            self._render(),
            console=self._console,
            refresh_per_second=12,
            transient=True,
        )
        self._live.start()  # type: ignore[attr-defined]
        return self

    def __exit__(self, *exc: object) -> None:
        if self._live is not None:
            self._live.stop()  # type: ignore[attr-defined]
            self._live = None

    # rich Status-compatible surface so the confirmer's pause logic is uniform.
    def start(self) -> None:
        if self._live is not None:
            self._live.start()  # type: ignore[attr-defined]

    def stop(self) -> None:
        if self._live is not None:
            self._live.stop()  # type: ignore[attr-defined]

    # -- event intake ----------------------------------------------------------

    def handle(self, event: UIEvent) -> None:
        """Apply one real execution event and refresh the display."""
        if event.kind is EventKind.PHASE:
            self._phase = event.label
            self._channel = event.channel
        elif event.kind is EventKind.START:
            self._ops.append(_Op(event.label, "run", event.channel))
        elif event.kind is EventKind.OK:
            self._mark(event.label, "ok")
        elif event.kind is EventKind.ERROR:
            self._mark(event.label, "err", event.error)
        elif event.kind is EventKind.NOTE:
            self._ops.append(_Op(event.label, "ok", event.channel))
        self._refresh()

    def _mark(self, label: str, state: str, err: str = "") -> None:
        for op in reversed(self._ops):
            if op.label == label and op.state == "run":
                op.state = state
                op.error = err
                return
        # Completion without a matching start still shows up, so nothing is lost.
        self._ops.append(_Op(label, state, self._channel, err))

    def _refresh(self) -> None:
        if self._live is not None:
            self._live.update(self._render())  # type: ignore[attr-defined]

    # -- rendering -------------------------------------------------------------

    def _glyph_for(self, state: str) -> Text:
        g = self._g
        if state == "ok":
            return Text(g.ok, style="archon.ok")
        if state == "err":
            return Text(g.err, style="archon.err")
        return Text(g.running, style="archon.run")

    def _render(self) -> RenderableType:
        lines: list[RenderableType] = []
        running = any(o.state == "run" for o in self._ops)
        header = Text()
        channel = (self._channel or Channel.ARCHON).value
        phase = self._phase or "WORKING"
        header.append(f"{channel} \u00b7 {phase}", style="archon.accent.dim")
        lines.append(header)

        if not self._ops:
            waiting = Table.grid(padding=(0, 1))
            waiting.add_row(self._spinner, Text("thinking", style="archon.dim"))
            lines.append(waiting)
        for op in self._ops:
            row = Table.grid(padding=(0, 1))
            row.add_column(no_wrap=True)
            row.add_column(overflow="fold")
            label = Text(op.label, style="archon.text")
            row.add_row(self._glyph_for(op.state), label)
            lines.append(row)
            if op.error:
                lines.append(Text(f"  {op.error}", style="archon.err"))
        # keep the header spinner animating while work is in flight
        if running:
            self._spinner.update()
        return Group(*lines)
