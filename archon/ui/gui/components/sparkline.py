"""
Sparkline — mini canvas-based line chart for live CPU/RAM data.
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from .. import theme as T


class Sparkline(ctk.CTkFrame):
    """
    A small line graph that tracks a rolling window of float values.

    Parameters
    ----------
    parent : tk.Widget
    width, height : int
        Canvas dimensions.
    max_points : int
        Number of data points to retain.
    line_color : str
        Color of the sparkline.
    fill_color : str
        Area fill color (set "" to disable fill).
    bg : str
        Background color.
    min_val, max_val : float
        Y-axis bounds. If both are 0, auto-scales.
    """

    def __init__(
        self,
        parent: tk.Widget,
        width: int = 120,
        height: int = 36,
        max_points: int = 30,
        line_color: str = T.CYAN,
        fill_color: str = T.CYAN_GLOW,
        bg: str = T.BG_RAISED,
        min_val: float = 0.0,
        max_val: float = 100.0,
        **kwargs: object,
    ) -> None:
        super().__init__(
            parent,
            fg_color=bg,
            corner_radius=T.RADIUS_SM,
            **kwargs,  # type: ignore[arg-type]
        )
        self._width = width
        self._height = height
        self._max_points = max_points
        self._line_color = line_color
        self._fill_color = fill_color
        self._bg = bg
        self._min_val = min_val
        self._max_val = max_val
        self._data: list[float] = []

        self._canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=bg,
            highlightthickness=0,
        )
        self._canvas.pack(padx=2, pady=2)

    def push(self, value: float) -> None:
        """Add a new data point and redraw."""
        self._data.append(value)
        if len(self._data) > self._max_points:
            self._data.pop(0)
        self._render()

    def _render(self) -> None:
        self._canvas.delete("all")
        data = self._data
        if not data:
            return

        n = len(data)
        w, h = self._width, self._height
        pad = 2

        lo = min(data) if self._min_val == self._max_val == 0 else self._min_val
        hi = max(data) if self._min_val == self._max_val == 0 else self._max_val
        rng = max(hi - lo, 1e-9)

        def _px(i: int) -> int:
            return pad + int(i * (w - 2 * pad) / max(n - 1, 1))

        def _py(v: float) -> int:
            return h - pad - int((v - lo) / rng * (h - 2 * pad))

        pts = [(_px(i), _py(v)) for i, v in enumerate(data)]

        # Fill area
        if self._fill_color:
            poly = [pad, h - pad]
            for x, y in pts:
                poly.extend([x, y])
            poly.extend([_px(n - 1), h - pad])
            if len(poly) >= 6:
                self._canvas.create_polygon(
                    poly,
                    fill=self._fill_color,
                    outline="",
                    smooth=True,
                )

        # Line
        if len(pts) >= 2:
            flat = [c for pt in pts for c in pt]
            self._canvas.create_line(
                flat,
                fill=self._line_color,
                width=1.5,
                smooth=True,
            )

        # Dot at right end
        lx, ly = pts[-1]
        r = 3
        self._canvas.create_oval(
            lx - r,
            ly - r,
            lx + r,
            ly + r,
            fill=self._line_color,
            outline="",
        )
