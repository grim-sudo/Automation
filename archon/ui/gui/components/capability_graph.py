"""
CapabilityGraph — a clickable capability network around the Archon core.

Spec §17: Archon at the center, capabilities radiating out, each with a
connection status (connected / available / degraded / offline). Clicking a node
invokes ``on_select`` with the capability name so a view can open an inspector.
"""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable

from .. import theme as T
from ..animations import hex_to_rgb, rgb_to_hex

# status → (dot color, connection color, is_active)
_STATUS = {
    "connected": (T.SUCCESS, T.GOLD, True),
    "available": (T.TEXT_SECONDARY, T.BORDER_STRONG, False),
    "degraded": (T.WARNING, T.WARNING, True),
    "offline": (T.TEXT_DIM, T.BORDER_SUBTLE, False),
}


def _blend(fg: str, bg: str, t: float) -> str:
    fr, fg_, fb = hex_to_rgb(fg)
    br, bg_, bb = hex_to_rgb(bg)
    return rgb_to_hex(
        round(fr * t + br * (1 - t)),
        round(fg_ * t + bg_ * (1 - t)),
        round(fb * t + bb * (1 - t)),
    )


class CapabilityGraph(tk.Canvas):
    """Radial capability network. ``capabilities`` = [{name, status}]."""

    def __init__(
        self,
        parent: tk.Widget,
        bg: str = T.BG_SURFACE,
        on_select: Callable[[str], None] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(
            parent, bg=bg, highlightthickness=0, bd=0, **kwargs,  # type: ignore[arg-type]
        )
        self._bg = bg
        self._on_select = on_select
        self._caps: list[dict] = []
        self._hitboxes: list[tuple[float, float, float, str]] = []
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Button-1>", self._on_click)

    def set_capabilities(self, capabilities: list[dict]) -> None:
        self._caps = capabilities
        self._draw()

    def _on_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        for hx, hy, hr, name in self._hitboxes:
            if (event.x - hx) ** 2 + (event.y - hy) ** 2 <= (hr + 6) ** 2:
                if self._on_select:
                    self._on_select(name)
                return

    def _draw(self) -> None:
        self.delete("all")
        self._hitboxes.clear()
        w = self.winfo_width() or 600
        h = self.winfo_height() or 400
        cx, cy = w / 2, h / 2
        n = len(self._caps)
        if n == 0:
            return
        radius = min(w, h) * 0.34

        for i, cap in enumerate(self._caps):
            ang = (math.tau * i / n) - math.pi / 2
            nx = cx + radius * math.cos(ang)
            ny = cy + radius * math.sin(ang)
            dot_c, conn_c, active = _STATUS.get(
                (cap.get("status") or "available").lower(),
                (T.TEXT_SECONDARY, T.BORDER_STRONG, False),
            )
            self.create_line(cx, cy, nx, ny, fill=conn_c, width=2 if active else 1)

            nr = 22
            self.create_oval(nx - nr, ny - nr, nx + nr, ny + nr,
                             fill=T.BG_RAISED, outline=conn_c, width=1)
            self.create_oval(nx - nr - 4, ny - nr, nx - nr + 4, ny - nr + 8,
                             fill=dot_c, outline="")
            self.create_text(nx, ny, text=cap.get("name", "")[:9],
                             fill=T.TEXT_PRIMARY, font=(T.FONT_FAMILY, 8, "bold"))
            self._hitboxes.append((nx, ny, nr, cap.get("name", "")))

        # Central Archon core.
        core_r = min(w, h) * 0.06
        self.create_oval(cx - core_r * 1.8, cy - core_r * 1.8,
                         cx + core_r * 1.8, cy + core_r * 1.8,
                         fill=_blend(T.GOLD, self._bg, 0.10), outline="")
        self.create_oval(cx - core_r, cy - core_r, cx + core_r, cy + core_r,
                         fill=T.BG_SURFACE, outline=T.GOLD, width=2)
        self.create_text(cx, cy, text="ARCHON", fill=T.TEXT_ACCENT,
                         font=(T.FONT_FAMILY, 9, "bold"))
