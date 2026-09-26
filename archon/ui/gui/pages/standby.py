"""
Standby views — capabilities Archon is designed for but does not yet back.

Spec §24: empty states must reinforce Archon's identity, never a generic
"Nothing here yet." Each view below is an honest, designed "standing by" surface
for a capability with no backend today (agents, memory, projects, datasets,
analytics). They share :class:`EmptyState` so they stay consistent and cheap.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from .. import theme as T
from ..components.empty_state import EmptyState


class _Standby(ctk.CTkFrame):
    """Base standby view — a centered emblem, title, message, and note."""

    title = "STANDING BY"
    message = ""
    note = ""

    def __init__(
        self,
        parent: tk.Widget,
        engine: object = None,
        on_navigate: Callable[[str], None] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, fg_color=T.BG_DEEP, **kwargs)  # type: ignore[arg-type]
        EmptyState(
            self, title=self.title, message=self.message, note=self.note,
        ).place(relx=0, rely=0, relwidth=1, relheight=1)


class AgentsView(_Standby):
    title = "No Agents Deployed"
    message = ("Autonomous agents will run long operations on Archon's behalf.\n"
               "None are active yet.")
    note = "agent runtime not connected"


class MemoryView(_Standby):
    title = "Memory Is Empty"
    message = ("Archon will remember your environment, preferences, and projects\n"
               "as knowledge topology. Nothing is stored yet.")
    note = "memory store not connected"


class ProjectsView(_Standby):
    title = "No Projects"
    message = ("Architecture, decisions, tasks, and artifacts will live here\n"
               "once you start a project with Archon.")
    note = "project store not connected"


class DatasetsView(_Standby):
    title = "No Datasets Attached"
    message = ("Attach a dataset to query and summarize it as a research\n"
               "instrument — never loaded whole into the interface.")
    note = "data engine not connected"


class AnalyticsView(_Standby):
    title = "No Analytics"
    message = ("Aggregations and insights over your data and operations\n"
               "will surface here once a data engine is connected.")
    note = "analytics engine not connected"
