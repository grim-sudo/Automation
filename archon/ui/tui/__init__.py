"""Archon's full-screen Textual TUI.

``archon chatbot`` launches :func:`run_tui`, which takes over the terminal with
a live system inspector, a streaming conversation, a collapsible execution view
and a command palette. The UI is a client of Archon's engine/agent — all
business logic stays behind :class:`~archon.ui.tui.controller.AgentController`.
"""

from __future__ import annotations

from typing import Any


def run_tui(engine: Any = None) -> None:
    """Launch the Archon TUI. Imported lazily so importing the package is cheap."""
    from .app import run_tui as _run

    _run(engine)


__all__ = ["run_tui"]
