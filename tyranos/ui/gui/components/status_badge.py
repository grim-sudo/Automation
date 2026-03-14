"""
StatusBadge — colored pill badge with optional pulsing dot.
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from .. import theme as T


class StatusBadge(ctk.CTkFrame):
    """
    A pill-shaped status badge.

    Parameters
    ----------
    parent : tk.Widget
        Parent widget.
    text : str
        Label text.
    status : str
        One of "active", "inactive", "warning", "error", "info", "building".
    pulse : bool
        If True, draws a small pulsing circle before the text.
    """

    _STATUS_COLORS: dict[str, tuple[str, str]] = {
        "active": (T.SUCCESS, "#064e3b"),
        "inactive": (T.TEXT_SECONDARY, T.BG_RAISED),
        "warning": (T.WARNING, T.WARNING_DIM),
        "error": (T.ERROR, T.ERROR_DIM),
        "info": (T.CYAN, "#164e63"),
        "building": (T.PURPLE, T.PURPLE_DARK),
        "online": (T.SUCCESS, "#064e3b"),
        "offline": (T.ERROR, T.ERROR_DIM),
    }

    def __init__(
        self,
        parent: tk.Widget,
        text: str = "Active",
        status: str = "active",
        pulse: bool = False,
        **kwargs: object,
    ) -> None:
        text_color, bg = self._STATUS_COLORS.get(status, (T.TEXT_SECONDARY, T.BG_RAISED))
        super().__init__(
            parent,
            fg_color=bg,
            corner_radius=T.RADIUS_BADGE,
            **kwargs,  # type: ignore[arg-type]
        )
        self._pulse = pulse
        self._text_color = text_color
        self._canvas: tk.Canvas | None = None
        self._dot_id: int | None = None
        self._anim_running = False

        if pulse:
            self._canvas = tk.Canvas(
                self,
                width=10,
                height=10,
                bg=bg,
                highlightthickness=0,
            )
            self._canvas.grid(row=0, column=0, padx=(8, 0), pady=4)
            self._dot_id = self._canvas.create_oval(1, 1, 9, 9, fill=text_color, outline="")
            self._start_pulse(text_color, bg)

        col = 1 if pulse else 0
        px = (4, 8) if pulse else (10, 10)
        self._label = ctk.CTkLabel(
            self,
            text=text,
            text_color=text_color,
            font=T.FONT_SMALL,
        )
        self._label.grid(row=0, column=col, padx=px, pady=(4, 4))

    def _start_pulse(self, active: str, bg: str) -> None:
        from ..animations import interpolate_color
        self._anim_running = True
        self._phase = 0.0

        def _tick() -> None:
            if not self._anim_running or self._canvas is None or self._dot_id is None:
                return
            import math
            self._phase += 0.1
            alpha = (math.sin(self._phase) + 1) / 2
            color = interpolate_color(bg, active, alpha)
            try:
                self._canvas.itemconfig(self._dot_id, fill=color)
                self._canvas.after(80, _tick)
            except Exception:
                pass

        _tick()

    def configure_text(self, text: str) -> None:
        self._label.configure(text=text)

    def destroy(self) -> None:
        self._anim_running = False
        super().destroy()
