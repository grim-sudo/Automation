"""Compact, toggleable activity log.

A timestamped stream of real events (plugin loaded, tool started, response
complete). Backed by Textual's :class:`RichLog` so it scrolls independently and
never grows the main transcript. Toggled from the app; hidden by default so it
never permanently consumes space.
"""

from __future__ import annotations

from datetime import datetime

from rich.text import Text
from textual.widgets import RichLog

from .glyphs import GLYPHS


class ActivityLog(RichLog):
    """A scrolling, timestamped event log."""

    def __init__(self) -> None:
        super().__init__(
            id="activity",
            classes="activity",
            highlight=False,
            markup=False,
            wrap=True,
            auto_scroll=True,
        )
        self.border_title = "ACTIVITY"

    def _line(self, glyph: str, style: str, text: str) -> Text:
        stamp = datetime.now().strftime("%H:%M:%S")
        line = Text()
        line.append(f"{stamp}  ", style="#4b4f57")
        line.append(f"{glyph} ", style=style)
        line.append(text, style="#8a8f98")
        return line

    def ok(self, text: str) -> None:
        self.write(self._line(GLYPHS.ok, "#5fae7f", text))

    def run(self, text: str) -> None:
        self.write(self._line(GLYPHS.running, "#8a8f98", text))

    def err(self, text: str) -> None:
        self.write(self._line(GLYPHS.err, "#cc6666", text))
