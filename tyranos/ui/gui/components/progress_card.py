"""
ProgressCard — animated progress bar card for build/task tracking.
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from .. import theme as T


class ProgressCard(ctk.CTkFrame):
    """
    A card with a title, subtitle, and animated gradient progress bar.

    Parameters
    ----------
    parent : tk.Widget
    title : str
    subtitle : str
    initial_value : float
        Progress 0.0 – 1.0.
    bar_color : str
        Solid override color for bar (or use gradient).
    """

    def __init__(
        self,
        parent: tk.Widget,
        title: str = "Task",
        subtitle: str = "",
        initial_value: float = 0.0,
        bar_color: str = T.PURPLE,
        **kwargs: object,
    ) -> None:
        super().__init__(
            parent,
            fg_color=T.BG_SURFACE,
            corner_radius=T.RADIUS_CARD,
            **kwargs,  # type: ignore[arg-type]
        )
        self._value = initial_value
        self._bar_color = bar_color

        # Header row
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=T.PAD_CARD, pady=(T.PAD_CARD, 4))

        self._title_lbl = ctk.CTkLabel(hdr, text=title, **T.label_heading_kwargs())
        self._title_lbl.pack(side="left")

        self._pct_lbl = ctk.CTkLabel(
            hdr,
            text=f"{int(initial_value * 100)}%",
            text_color=T.TEXT_ACCENT,
            font=T.FONT_BODY_BOLD,
        )
        self._pct_lbl.pack(side="right")

        if subtitle:
            self._sub_lbl = ctk.CTkLabel(
                self, text=subtitle, **T.label_secondary_kwargs(), anchor="w"
            )
            self._sub_lbl.pack(fill="x", padx=T.PAD_CARD, pady=(0, 8))

        # Progress bar track
        self._track = tk.Canvas(
            self,
            height=8,
            bg=T.BG_RAISED,
            highlightthickness=0,
        )
        self._track.pack(fill="x", padx=T.PAD_CARD, pady=(4, T.PAD_CARD))
        self._track.bind("<Configure>", lambda _e: self._draw_bar())
        self._draw_bar()

    # ── Public ─────────────────────────────────────────────────────────────────

    def set_progress(self, value: float, subtitle: str | None = None) -> None:
        """Update progress. value in [0, 1]."""
        self._value = max(0.0, min(1.0, value))
        self._pct_lbl.configure(text=f"{int(self._value * 100)}%")
        if subtitle is not None and hasattr(self, "_sub_lbl"):
            self._sub_lbl.configure(text=subtitle)
        self._draw_bar()

    def set_title(self, title: str) -> None:
        self._title_lbl.configure(text=title)

    # ── Internal ───────────────────────────────────────────────────────────────

    def _draw_bar(self) -> None:
        self._track.delete("all")
        w = self._track.winfo_width()
        h = 8
        if w < 4:
            return

        # Track background
        r = 4
        self._track.create_rounded_rect = _rounded_rect  # type: ignore[attr-defined]
        _rounded_rect(self._track, 0, 0, w, h, r, fill=T.BG_RAISED, outline="")

        # Fill
        fill_w = int(w * self._value)
        if fill_w > 0:
            _rounded_rect(self._track, 0, 0, fill_w, h, r, fill=self._bar_color, outline="")

            # Glow highlight at leading edge
            if fill_w > 8:
                self._track.create_oval(
                    fill_w - 6, 1, fill_w + 1, h - 1,
                    fill=T.PURPLE_LIGHT, outline="",
                )


def _rounded_rect(
    canvas: tk.Canvas,
    x1: int, y1: int, x2: int, y2: int,
    r: int,
    **kwargs: object,
) -> None:
    """Draw a rounded rectangle on a canvas."""
    r = min(r, (x2 - x1) // 2, (y2 - y1) // 2)
    points = [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]
    canvas.create_polygon(points, smooth=True, **kwargs)  # type: ignore[arg-type]
