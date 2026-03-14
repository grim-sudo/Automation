"""
Animation helpers for the Tyranos GUI.
Uses tkinter's after() for smooth transitions without external deps.
"""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable

from . import theme as T


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolate between a and b by factor t (0..1)."""
    return a + (b - a) * t


def ease_out_cubic(t: float) -> float:
    """Ease-out cubic easing function."""
    return 1 - (1 - t) ** 3


def ease_in_out(t: float) -> float:
    """Smooth ease-in-out."""
    return t * t * (3 - 2 * t)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert CSS hex color to (r, g, b) tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 8:  # RRGGBBAA
        hex_color = hex_color[:6]
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert (r, g, b) tuple to CSS hex color."""
    return f"#{r:02x}{g:02x}{b:02x}"


def interpolate_color(color_a: str, color_b: str, t: float) -> str:
    """Smoothly interpolate between two hex colors."""
    ra, ga, ba = hex_to_rgb(color_a)
    rb, gb, bb = hex_to_rgb(color_b)
    r = int(lerp(ra, rb, t))
    g = int(lerp(ga, gb, t))
    b = int(lerp(ba, bb, t))
    return rgb_to_hex(r, g, b)


def gradient_stops(color_a: str, color_b: str, n: int) -> list[str]:
    """Return n gradient color stops between color_a and color_b."""
    return [interpolate_color(color_a, color_b, i / max(n - 1, 1)) for i in range(n)]


class FadeAnimator:
    """Fade a widget in or out by animating its alpha via a Canvas overlay."""

    def __init__(self, widget: tk.Widget, duration_ms: int = T.ANIM_NORMAL) -> None:
        self.widget = widget
        self.duration_ms = duration_ms
        self._steps = 20
        self._interval = duration_ms // self._steps

    def fade_in(self, callback: Callable | None = None) -> None:
        """Animate fade in (widget appears)."""
        self._animate(0, 1, callback)

    def fade_out(self, callback: Callable | None = None) -> None:
        """Animate fade out (widget disappears)."""
        self._animate(1, 0, callback)

    def _animate(self, start: float, end: float, callback: Callable | None) -> None:
        step = [0]

        def _step() -> None:
            if step[0] >= self._steps:
                if callback:
                    callback()
                return
            t = ease_out_cubic(step[0] / self._steps)
            alpha = lerp(start, end, t)
            try:
                self.widget.attributes("-alpha", alpha)  # type: ignore[attr-defined]
            except Exception:
                pass
            step[0] += 1
            self.widget.after(self._interval, _step)

        _step()


class PulseAnimator:
    """Make a canvas item pulse by oscillating its color between two values."""

    def __init__(
        self,
        canvas: tk.Canvas,
        item_id: int,
        color_a: str,
        color_b: str,
        period_ms: int = 2000,
        attr: str = "fill",
    ) -> None:
        self.canvas = canvas
        self.item_id = item_id
        self.color_a = color_a
        self.color_b = color_b
        self.period_ms = period_ms
        self.attr = attr
        self._running = False
        self._t: float = 0.0
        self._step_ms = 50

    def start(self) -> None:
        self._running = True
        self._tick()

    def stop(self) -> None:
        self._running = False

    def _tick(self) -> None:
        if not self._running:
            return
        self._t += self._step_ms / self.period_ms
        phase = (math.sin(self._t * math.pi * 2) + 1) / 2
        color = interpolate_color(self.color_a, self.color_b, phase)
        try:
            self.canvas.itemconfig(self.item_id, **{self.attr: color})
        except Exception:
            return
        self.canvas.after(self._step_ms, self._tick)


class TypingDotAnimator:
    """Animate 3 pulsing dots (typing indicator)."""

    def __init__(
        self,
        canvas: tk.Canvas,
        dot_ids: list[int],
        active_color: str = T.PURPLE,
        inactive_color: str = T.BG_RAISED,
        step_ms: int = 400,
    ) -> None:
        self.canvas = canvas
        self.dot_ids = dot_ids
        self.active_color = active_color
        self.inactive_color = inactive_color
        self.step_ms = step_ms
        self._running = False
        self._phase = 0

    def start(self) -> None:
        self._running = True
        self._tick()

    def stop(self) -> None:
        self._running = False
        for dot_id in self.dot_ids:
            try:
                self.canvas.itemconfig(dot_id, fill=self.inactive_color)
            except Exception:
                pass

    def _tick(self) -> None:
        if not self._running:
            return
        for i, dot_id in enumerate(self.dot_ids):
            color = self.active_color if i == self._phase else self.inactive_color
            try:
                self.canvas.itemconfig(dot_id, fill=color)
            except Exception:
                return
        self._phase = (self._phase + 1) % len(self.dot_ids)
        self.canvas.after(self.step_ms, self._tick)


class SlideInAnimator:
    """Slide a frame into view from a given direction."""

    def __init__(
        self,
        widget: tk.Widget,
        target_x: int,
        target_y: int,
        from_offset: int = 40,
        duration_ms: int = T.ANIM_NORMAL,
    ) -> None:
        self.widget = widget
        self.target_x = target_x
        self.target_y = target_y
        self.from_offset = from_offset
        self.duration_ms = duration_ms
        self._steps = 16
        self._interval = max(1, duration_ms // self._steps)

    def slide_from_bottom(self, callback: Callable | None = None) -> None:
        start_y = self.target_y + self.from_offset
        step = [0]

        def _step() -> None:
            if step[0] >= self._steps:
                try:
                    self.widget.place(x=self.target_x, y=self.target_y)
                except Exception:
                    pass
                if callback:
                    callback()
                return
            t = ease_out_cubic(step[0] / self._steps)
            y = int(lerp(start_y, self.target_y, t))
            try:
                self.widget.place(x=self.target_x, y=y)
            except Exception:
                return
            step[0] += 1
            self.widget.after(self._interval, _step)

        _step()
