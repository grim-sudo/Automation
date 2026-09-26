"""
EmptyState — a designed "standing by" state for views without live data yet.

Spec §24: empty states must reinforce Archon's identity, never a generic
"Nothing here yet." A small emblem, a declarative title, one line of context,
and an optional primary action.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from .. import theme as T
from ..particles import draw_archon_sigil


class EmptyState(ctk.CTkFrame):
    """Centered emblem + message + optional action for empty/standby views."""

    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        message: str = "",
        action_label: str = "",
        on_action: Callable[[], None] | None = None,
        emblem: bool = True,
        note: str = "",
        **kwargs: object,
    ) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)  # type: ignore[arg-type]

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.place(relx=0.5, rely=0.44, anchor="center")

        if emblem:
            canvas = tk.Canvas(
                inner, width=76, height=76, bg=T.BG_DEEP, highlightthickness=0
            )
            draw_archon_sigil(canvas, size=76, phase=0.6)
            canvas.pack(pady=(0, T.SPACE_LG))

        ctk.CTkLabel(
            inner, text=title.upper(),
            font=(T.FONT_FAMILY, 15, "bold"),
            text_color=T.TEXT_SECONDARY,
        ).pack()

        if message:
            ctk.CTkLabel(
                inner, text=message, font=T.FONT_BODY,
                text_color=T.TEXT_MUTED, justify="center",
            ).pack(pady=(T.SPACE_SM, 0))

        if action_label and on_action:
            ctk.CTkButton(
                inner, text=action_label, width=180, height=38,
                **T.btn_outline_kwargs(), command=on_action,
            ).pack(pady=(T.SPACE_LG, 0))

        if note:
            ctk.CTkLabel(
                inner, text=note, font=T.FONT_CODE_SMALL,
                text_color=T.TEXT_DIM, justify="center",
            ).pack(pady=(T.SPACE_MD, 0))
