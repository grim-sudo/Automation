"""Toggleable debug console: the raw log stream.

Where :class:`~archon.ui.tui.widgets.activity.ActivityLog` shows a curated
handful of high-level events, this shows *everything* — every loguru record
from every component (engine, plugins, adapters, agent) at ``DEBUG`` and up.

It installs its own loguru sink at mount and removes it at unmount, so it never
disturbs the existing stderr/file sinks configured in
:func:`archon.utils.logger.configure_logging`. The sink fires on whatever thread
emitted the log (agent work runs on a worker thread), so records land in a
thread-safe :class:`~collections.deque` and a UI-thread timer drains them into
the :class:`~textual.widgets.RichLog` — widgets are never mutated off-thread.

Records accumulate even while the console is hidden, so toggling it on reveals
the full backlog rather than starting blank.
"""

from __future__ import annotations

from collections import deque
from typing import Any

from loguru import logger
from rich.text import Text
from textual.widgets import RichLog

# Graphite/gold palette — no neon. Level → colour.
_LEVEL_STYLES: dict[str, str] = {
    "TRACE": "#6b7280",
    "DEBUG": "#6b7280",
    "INFO": "#8a8f98",
    "SUCCESS": "#5fae7f",
    "WARNING": "#8a6d3b",
    "ERROR": "#cc6666",
    "CRITICAL": "bold #cc6666",
}
_DEFAULT_STYLE = "#8a8f98"

_MAX_LINES = 2000


class DebugConsole(RichLog):
    """A scrolling console mirroring the full loguru log stream."""

    def __init__(self) -> None:
        super().__init__(
            id="debug-console",
            classes="debug-console",
            highlight=False,
            markup=False,
            wrap=True,
            auto_scroll=True,
            max_lines=_MAX_LINES,
        )
        self.border_title = "DEBUG CONSOLE"
        # Records arrive on arbitrary threads; deque append/popleft are atomic
        # under CPython, so no lock is needed for this producer/consumer pair.
        self._buffer: deque[dict[str, Any]] = deque(maxlen=_MAX_LINES)
        self._sink_id: int | None = None

    def on_mount(self) -> None:
        self._sink_id = logger.add(
            self._sink,
            level="DEBUG",
            format="{message}",  # unused; we render from the record ourselves
            enqueue=False,
            backtrace=False,
            diagnose=False,
        )
        self.set_interval(0.25, self._drain)

    def on_unmount(self) -> None:
        if self._sink_id is not None:
            logger.remove(self._sink_id)
            self._sink_id = None

    def _sink(self, message: Any) -> None:
        """loguru sink — runs on the emitting thread. Keep it cheap."""
        record = message.record
        self._buffer.append(
            {
                "time": record["time"].strftime("%H:%M:%S.%f")[:-3],
                "level": record["level"].name,
                "name": record["name"] or "?",
                "line": record["line"],
                "message": record["message"],
            }
        )

    def _drain(self) -> None:
        """Flush buffered records into the log on the UI thread."""
        while self._buffer:
            try:
                self.write(self._format(self._buffer.popleft()))
            except IndexError:  # drained concurrently by the sink's maxlen churn
                break

    @staticmethod
    def _format(rec: dict[str, Any]) -> Text:
        style = _LEVEL_STYLES.get(rec["level"], _DEFAULT_STYLE)
        line = Text()
        line.append(f"{rec['time']}  ", style="#4b4f57")
        line.append(f"{rec['level']:<8} ", style=style)
        line.append(f"{rec['name']}:{rec['line']}", style="#5a5f68")
        line.append("  ", style="#5a5f68")
        line.append(rec["message"], style="#8a8f98")
        return line
