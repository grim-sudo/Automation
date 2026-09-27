"""Persistent bottom status bar.

A single reactive line summarising live state: current phase, plugin and
capability counts, model, accelerator and a rough context gauge. The app sets
the reactive fields; changing any of them re-renders the bar automatically.
Values it hasn't been given show as ``—`` rather than a fabricated figure.
"""

from __future__ import annotations

from rich.text import Text
from textual.reactive import reactive
from textual.widgets import Static

from .glyphs import GLYPHS


class StatusBar(Static):
    """One-line operational summary docked above the input."""

    state: reactive[str] = reactive("READY")
    plugins: reactive[int | None] = reactive(None)
    capabilities: reactive[int | None] = reactive(None)
    model: reactive[str] = reactive("—")
    accelerator: reactive[str] = reactive("—")
    context: reactive[str] = reactive("—")

    def _seg(self, value: object) -> str:
        return "—" if value is None else str(value)

    def render(self) -> Text:
        sep = Text("  │  ", style="#4b4f57")
        line = Text()
        line.append(f"{GLYPHS.brand} ", style="#d9a441 bold")
        line.append(self._seg(self.state), style="#d9a441 bold")
        parts = [
            f"{self._seg(self.plugins)} plugins",
            f"{self._seg(self.capabilities)} capabilities",
            self._seg(self.model),
            self._seg(self.accelerator),
            self._seg(self.context),
        ]
        for part in parts:
            line.append_text(sep)
            line.append(part, style="#8a8f98")
        return line
