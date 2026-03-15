"""
WorkflowCard — card widget for n8n workflow listings.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from .. import theme as T
from .status_badge import StatusBadge


class WorkflowCard(ctk.CTkFrame):
    """
    Displays a single n8n workflow in a card with actions.

    Parameters
    ----------
    parent : tk.Widget
    name : str
    active : bool
    trigger : str
    last_run : str
    exec_count : int
    on_run : Callable
    on_toggle : Callable
    on_delete : Callable
    """

    def __init__(
        self,
        parent: tk.Widget,
        name: str = "Workflow",
        active: bool = False,
        trigger: str = "Manual",
        last_run: str = "Never",
        exec_count: int = 0,
        on_run: Callable | None = None,
        on_toggle: Callable | None = None,
        on_delete: Callable | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(
            parent,
            fg_color=T.BG_SURFACE,
            corner_radius=T.RADIUS_CARD,
            border_color=T.BORDER_SUBTLE,
            border_width=1,
            **kwargs,  # type: ignore[arg-type]
        )
        self._active = active
        self._name = name
        self._on_run = on_run
        self._on_toggle = on_toggle
        self._on_delete = on_delete

        self._build(name, active, trigger, last_run, exec_count)
        self._bind_hover()

    def _build(self, name: str, active: bool, trigger: str, last_run: str, exec_count: int) -> None:
        pad = T.PAD_CARD

        # ── Header: name + status ─────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=pad, pady=(pad, 4))

        ctk.CTkLabel(hdr, text=name, **T.label_heading_kwargs()).pack(side="left")

        status = "active" if active else "inactive"
        label = "● Active" if active else "○ Inactive"
        StatusBadge(hdr, text=label, status=status, pulse=active).pack(side="right")

        # ── Meta info ─────────────────────────────────────────────────────────
        meta = ctk.CTkFrame(self, fg_color="transparent")
        meta.pack(fill="x", padx=pad, pady=4)

        trigger_icon = {"Webhook": "🔗", "Schedule": "⏰", "Manual": "▶"}.get(trigger, "⚡")
        ctk.CTkLabel(
            meta,
            text=f"{trigger_icon} {trigger}",
            **T.label_secondary_kwargs(),
        ).pack(side="left")

        ctk.CTkLabel(
            meta,
            text=f"{exec_count} runs",
            **T.label_secondary_kwargs(),
        ).pack(side="right")

        ctk.CTkLabel(
            meta,
            text=f"Last run: {last_run}",
            **T.label_secondary_kwargs(),
        ).pack(side="right", padx=T.SPACE_SM)

        # ── Actions (hidden by default, show on hover) ───────────────────────
        self._actions = ctk.CTkFrame(self, fg_color="transparent")
        self._actions.pack(fill="x", padx=pad, pady=(4, pad))

        ctk.CTkButton(
            self._actions,
            text="▶ Run",
            width=70,
            **T.btn_primary_kwargs(),
            command=lambda: self._on_run and self._on_run(),  # type: ignore[misc]
        ).pack(side="left", padx=(0, 6))

        toggle_text = "⏸ Pause" if active else "▶ Enable"
        ctk.CTkButton(
            self._actions,
            text=toggle_text,
            width=80,
            **T.btn_outline_kwargs(),
            command=lambda: self._on_toggle and self._on_toggle(),  # type: ignore[misc]
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            self._actions,
            text="🗑",
            width=34,
            **T.btn_ghost_kwargs(),
            command=lambda: self._on_delete and self._on_delete(),  # type: ignore[misc]
        ).pack(side="right")

    def _bind_hover(self) -> None:
        for widget in [self, *self.winfo_children()]:
            widget.bind("<Enter>", self._on_enter, add="+")
            widget.bind("<Leave>", self._on_leave, add="+")

    def _on_enter(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        self.configure(border_color=T.BORDER_ACCENT)

    def _on_leave(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        self.configure(border_color=T.BORDER_SUBTLE)
