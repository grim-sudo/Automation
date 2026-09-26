"""
OperationTimeline — a vertical action/result timeline for operations.

Spec §14: gold = active, silver = completed, dim = future, red = failed. Shows
only actions and results, never private reasoning. Each step is a state dot on a
connecting rail with a label and optional detail.
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from .. import theme as T

# state → (dot glyph, color)
_STATE = {
    "done": ("●", T.SUCCESS),
    "completed": ("●", T.SUCCESS),
    "active": ("◉", T.GOLD),
    "running": ("◉", T.GOLD),
    "pending": ("○", T.TEXT_DIM),
    "future": ("○", T.TEXT_DIM),
    "failed": ("✕", T.ERROR),
    "error": ("✕", T.ERROR),
}


class OperationTimeline(ctk.CTkScrollableFrame):
    """Vertical timeline of operation steps."""

    def __init__(self, parent: tk.Widget, **kwargs: object) -> None:
        super().__init__(
            parent, fg_color="transparent",
            scrollbar_button_color=T.BG_SURFACE,
            scrollbar_button_hover_color=T.BG_RAISED,
            **kwargs,  # type: ignore[arg-type]
        )
        self._rows: list[ctk.CTkFrame] = []

    def set_steps(self, steps: list[dict]) -> None:
        """
        Render steps. Each step: {label, state, detail?}.
        state ∈ done|active|pending|failed (aliases accepted).
        """
        for r in self._rows:
            r.destroy()
        self._rows.clear()

        for i, step in enumerate(steps):
            state = (step.get("state") or "pending").lower()
            glyph, color = _STATE.get(state, ("○", T.TEXT_DIM))
            last = i == len(steps) - 1

            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x")
            self._rows.append(row)
            row.grid_columnconfigure(1, weight=1)

            rail = tk.Canvas(row, width=20, height=44, bg=T.BG_SURFACE,
                             highlightthickness=0)
            rail.grid(row=0, column=0, sticky="ns")
            # connecting line above/below the dot
            if i > 0:
                rail.create_line(10, 0, 10, 16, fill=T.BORDER_STRONG, width=1)
            if not last:
                rail.create_line(10, 28, 10, 44, fill=T.BORDER_STRONG, width=1)
            rail.create_text(10, 22, text=glyph, fill=color,
                             font=(T.FONT_FAMILY, 12, "bold"))

            text_col = ctk.CTkFrame(row, fg_color="transparent")
            text_col.grid(row=0, column=1, sticky="ew", padx=(T.SPACE_SM, 0),
                          pady=(6, 0))
            label_color = (
                T.TEXT_PRIMARY if state in ("active", "running")
                else T.TEXT_SECONDARY if state in ("done", "completed")
                else T.ERROR if state in ("failed", "error")
                else T.TEXT_MUTED
            )
            ctk.CTkLabel(
                text_col, text=step.get("label", ""), font=T.FONT_BODY,
                text_color=label_color, anchor="w",
            ).pack(anchor="w")
            detail = step.get("detail")
            if detail:
                ctk.CTkLabel(
                    text_col, text=detail, font=T.FONT_CODE_SMALL,
                    text_color=T.TEXT_DIM, anchor="w",
                ).pack(anchor="w")
