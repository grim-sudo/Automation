"""
TopBar — page context, global command entry, and status cluster.

Left shows the active page title and a one-line context. The center is a global
command entry that hands off to the Command view. The right is a compact status
pill plus a settings shortcut. Kept deliberately short so it never eats vertical
space from the content area.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from .. import theme as T

# Human-facing (title, context) per page key.
_PAGE_META: dict[str, tuple[str, str]] = {
    "home": ("Overview", "System status and quick actions"),
    "automate": ("Command", "Describe an operation — Archon executes it"),
    "chat": ("Chat", "Converse with the Archon intelligence layer"),
    "n8n": ("Workflows", "Browse, trigger, and monitor n8n workflows"),
    "distro": ("OS Builder", "Compose and build a custom Linux image"),
    "history": ("History", "Past operations and their results"),
    "settings": ("Settings", "Configuration and preferences"),
}


class TopBar(ctk.CTkFrame):
    """Compact top context + command bar."""

    def __init__(
        self,
        parent: tk.Widget,
        on_command: Callable[[str], None] | None = None,
        on_settings: Callable[[], None] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(
            parent,
            fg_color=T.BG_SURFACE,
            corner_radius=0,
            height=T.TOPBAR_HEIGHT,
            **kwargs,  # type: ignore[arg-type]
        )
        self.grid_propagate(False)
        self._on_command = on_command
        self._on_settings = on_settings
        self._build()

    def _build(self) -> None:
        # Left: title + context.
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", padx=T.PAD_CARD)
        self._title = ctk.CTkLabel(
            left, text="Overview", font=(T.FONT_FAMILY, 16, "bold"), text_color=T.TEXT_PRIMARY
        )
        self._title.pack(side="top", anchor="w")
        self._context = ctk.CTkLabel(
            left, text="", font=T.FONT_MICRO, text_color=T.TEXT_MUTED
        )
        self._context.pack(side="top", anchor="w")

        # Right: status pill + settings.
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="right", padx=T.PAD_CARD)

        ctk.CTkButton(
            right,
            text="⚙",
            width=32,
            **T.btn_ghost_kwargs(),
            command=lambda: self._on_settings and self._on_settings(),
        ).pack(side="right", padx=(T.SPACE_SM, 0))

        pill = ctk.CTkFrame(right, fg_color=T.BG_RAISED, corner_radius=T.RADIUS_BADGE)
        pill.pack(side="right")
        self._status_dot = tk.Canvas(
            pill, width=8, height=8, bg=T.BG_RAISED, highlightthickness=0
        )
        self._status_dot.pack(side="left", padx=(10, 5), pady=6)
        self._status_dot_id = self._status_dot.create_oval(0, 0, 8, 8, fill=T.SUCCESS, outline="")
        self._status_text = ctk.CTkLabel(
            pill, text="ONLINE", font=(T.FONT_FAMILY, 10, "bold"), text_color=T.SUCCESS
        )
        self._status_text.pack(side="left", padx=(0, 12))

        # Center: global command entry.
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.pack(side="left", fill="x", expand=True, padx=T.SPACE_MD)
        self._entry = ctk.CTkEntry(
            center,
            placeholder_text="⌘  Run a command…",
            **T.input_kwargs(),
            height=32,
        )
        self._entry.pack(fill="x", padx=T.SPACE_LG)
        self._entry.bind("<Return>", self._submit)

    def _submit(self, _e: tk.Event) -> None:  # type: ignore[type-arg]
        text = self._entry.get().strip()
        if not text:
            return
        self._entry.delete(0, "end")
        if self._on_command:
            self._on_command(text)

    def set_page(self, page_key: str) -> None:
        title, context = _PAGE_META.get(page_key, (page_key.title(), ""))
        self._title.configure(text=title)
        self._context.configure(text=context)

    def set_status(self, ok: bool, label: str = "") -> None:
        color = T.SUCCESS if ok else T.ERROR
        text = label or ("ONLINE" if ok else "OFFLINE")
        try:
            self._status_dot.itemconfig(self._status_dot_id, fill=color)
            self._status_text.configure(text=text, text_color=color)
        except tk.TclError:
            pass
