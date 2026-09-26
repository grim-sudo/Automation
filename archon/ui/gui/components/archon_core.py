"""
ArchonCore — the central-intelligence topology visualization.

Spec §10 / §2: one central node (ARCHON) with orbital subsystems connected by
thin rules. Gold marks active connections; a signal periodically travels an
active edge to show Archon invoking a subsystem. Deliberately restrained — a
slow, quiet orbit, not a spinning sci-fi reactor. Pure-canvas, driven by the Tk
``after()`` loop, no external deps.
"""

from __future__ import annotations

import math
import tkinter as tk

from .. import theme as T
from ..animations import hex_to_rgb, rgb_to_hex

_SUBSYSTEMS = ["AI", "SYSTEMS", "AUTOMATION", "MCP", "DATA", "BUILD", "CLOUD", "MEMORY"]


def _blend(fg: str, bg: str, t: float) -> str:
    fr, fg_, fb = hex_to_rgb(fg)
    br, bg_, bb = hex_to_rgb(bg)
    return rgb_to_hex(
        round(fr * t + br * (1 - t)),
        round(fg_ * t + bg_ * (1 - t)),
        round(fb * t + bb * (1 - t)),
    )


class ArchonCore(tk.Canvas):
    """
    Central Archon node orbited by subsystem nodes.

    ``set_active(name)`` lights a subsystem's connection gold and sends a
    traveling signal along it; ``clear_active()`` returns to the quiet state.
    """

    def __init__(
        self,
        parent: tk.Widget,
        size: int = 320,
        bg: str = T.BG_DEEP,
        subsystems: list[str] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(
            parent, width=size, height=size, bg=bg,
            highlightthickness=0, bd=0, **kwargs,  # type: ignore[arg-type]
        )
        self._size = size
        self._bg = bg
        self._names = subsystems or _SUBSYSTEMS
        self._phase = 0.0
        self._active: str | None = None
        self._signal = 0.0
        self._running = False
        self.bind("<Configure>", lambda _e: self._draw())

    def start(self) -> None:
        if not self._running:
            self._running = True
            self._tick()

    def stop(self) -> None:
        self._running = False

    def set_active(self, name: str | None) -> None:
        self._active = name
        self._signal = 0.0

    def clear_active(self) -> None:
        self.set_active(None)

    def _tick(self) -> None:
        if not self._running or not self.winfo_exists():
            return
        self._phase += 0.006
        if self._active:
            self._signal = (self._signal + 0.03) % 1.0
        self._draw()
        self.after(40, self._tick)

    def _draw(self) -> None:
        self.delete("all")
        w = self.winfo_width() or self._size
        h = self.winfo_height() or self._size
        cx, cy = w / 2, h / 2
        radius = min(w, h) * 0.38
        n = len(self._names)

        nodes: list[tuple[float, float, str]] = []
        for i, name in enumerate(self._names):
            ang = self._phase + (math.tau * i / n) - math.pi / 2
            nx = cx + radius * math.cos(ang)
            ny = cy + radius * math.sin(ang)
            nodes.append((nx, ny, name))

        # Connections (thin steel; gold when active).
        for nx, ny, name in nodes:
            active = name == self._active
            col = T.GOLD if active else _blend(T.CYAN, self._bg, 0.28)
            self.create_line(cx, cy, nx, ny, fill=col, width=2 if active else 1)

        # Traveling signal on the active edge.
        if self._active:
            for nx, ny, name in nodes:
                if name != self._active:
                    continue
                sx = cx + (nx - cx) * self._signal
                sy = cy + (ny - cy) * self._signal
                r = max(3, self._size * 0.012)
                self.create_oval(
                    sx - r * 2, sy - r * 2, sx + r * 2, sy + r * 2,
                    fill=_blend(T.GOLD, self._bg, 0.4), outline="",
                )
                self.create_oval(sx - r, sy - r, sx + r, sy + r,
                                 fill=T.GOLD_LIGHT, outline="")

        # Subsystem nodes + labels.
        for nx, ny, name in nodes:
            active = name == self._active
            nr = max(4, self._size * 0.016)
            self.create_oval(
                nx - nr, ny - nr, nx + nr, ny + nr,
                fill=T.GOLD if active else T.BG_RAISED,
                outline=T.GOLD if active else T.BORDER_STRONG, width=1,
            )
            self.create_text(
                nx, ny + nr + 9, text=name,
                fill=T.TEXT_ACCENT if active else T.TEXT_MUTED,
                font=(T.FONT_FAMILY, 8, "bold"),
            )

        # Central Archon node — diamond emblem with soft glow.
        core_r = max(10, self._size * 0.055)
        for frac, t in ((2.4, 0.10), (1.7, 0.16)):
            gr = core_r * frac
            self.create_oval(cx - gr, cy - gr, cx + gr, cy + gr,
                             fill=_blend(T.GOLD, self._bg, t), outline="")
        self.create_oval(
            cx - core_r, cy - core_r, cx + core_r, cy + core_r,
            fill=T.BG_SURFACE, outline=T.GOLD, width=2,
        )
        d = core_r * 0.5
        self.create_polygon(
            cx, cy - d, cx + d, cy, cx, cy + d, cx - d, cy,
            fill=T.GOLD, outline="",
        )
        self.create_text(
            cx, cy + core_r + 12, text="ARCHON",
            fill=T.TEXT_PRIMARY, font=(T.FONT_FAMILY, 9, "bold"),
        )
