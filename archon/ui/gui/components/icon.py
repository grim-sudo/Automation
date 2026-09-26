"""
Icon — small, monochrome, line-drawn navigation glyphs.

A tiny hand-drawn icon set so the sidebar reads as a technical control plane
rather than a wall of colored emoji. Each glyph is defined in a 0..1 unit box
and scaled to the requested size; a single stroke color keeps them monochrome
and recolorable for hover/active states.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from .. import theme as T


def _line(c: tk.Canvas, s: int, pts: list[tuple[float, float]], color: str, w: int) -> None:
    flat: list[float] = []
    for x, y in pts:
        flat.extend((x * s, y * s))
    c.create_line(*flat, fill=color, width=w, capstyle="round", joinstyle="round")


def _oval(c: tk.Canvas, s: int, box: tuple[float, float, float, float], color: str, w: int) -> None:
    x0, y0, x1, y1 = box
    c.create_oval(x0 * s, y0 * s, x1 * s, y1 * s, outline=color, width=w)


def _rect(c: tk.Canvas, s: int, box: tuple[float, float, float, float], color: str, w: int) -> None:
    x0, y0, x1, y1 = box
    c.create_rectangle(x0 * s, y0 * s, x1 * s, y1 * s, outline=color, width=w)


# Each drawer paints one glyph into a size-s canvas with the given stroke.
def _overview(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _rect(c, s, (0.18, 0.18, 0.46, 0.46), col, w)
    _rect(c, s, (0.54, 0.18, 0.82, 0.46), col, w)
    _rect(c, s, (0.18, 0.54, 0.46, 0.82), col, w)
    _rect(c, s, (0.54, 0.54, 0.82, 0.82), col, w)


def _command(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _line(c, s, [(0.22, 0.30), (0.42, 0.50), (0.22, 0.70)], col, w)
    _line(c, s, [(0.50, 0.70), (0.78, 0.70)], col, w)


def _chat(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _line(
        c, s,
        [(0.20, 0.24), (0.80, 0.24), (0.80, 0.62), (0.44, 0.62),
         (0.30, 0.76), (0.30, 0.62), (0.20, 0.62), (0.20, 0.24)],
        col, w,
    )


def _workflows(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _oval(c, s, (0.14, 0.40, 0.30, 0.56), col, w)  # source
    _oval(c, s, (0.62, 0.18, 0.78, 0.34), col, w)  # up branch
    _oval(c, s, (0.62, 0.62, 0.78, 0.78), col, w)  # down branch
    _line(c, s, [(0.30, 0.48), (0.62, 0.26)], col, w)
    _line(c, s, [(0.30, 0.48), (0.62, 0.70)], col, w)


def _osbuilder(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _line(
        c, s,
        [(0.50, 0.16), (0.80, 0.33), (0.80, 0.67),
         (0.50, 0.84), (0.20, 0.67), (0.20, 0.33), (0.50, 0.16)],
        col, w,
    )
    _oval(c, s, (0.42, 0.42, 0.58, 0.58), col, w)


def _history(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _oval(c, s, (0.20, 0.20, 0.80, 0.80), col, w)
    _line(c, s, [(0.50, 0.34), (0.50, 0.52), (0.64, 0.60)], col, w)


def _capabilities(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _rect(c, s, (0.20, 0.20, 0.80, 0.80), col, w)
    _line(c, s, [(0.20, 0.42), (0.80, 0.42)], col, w)
    _line(c, s, [(0.42, 0.20), (0.42, 0.42)], col, w)


def _logs(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _line(c, s, [(0.24, 0.30), (0.32, 0.30)], col, w)
    _line(c, s, [(0.40, 0.30), (0.78, 0.30)], col, w)
    _line(c, s, [(0.24, 0.50), (0.32, 0.50)], col, w)
    _line(c, s, [(0.40, 0.50), (0.78, 0.50)], col, w)
    _line(c, s, [(0.24, 0.70), (0.32, 0.70)], col, w)
    _line(c, s, [(0.40, 0.70), (0.78, 0.70)], col, w)


def _settings(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _line(c, s, [(0.22, 0.32), (0.78, 0.32)], col, w)
    _oval(c, s, (0.36, 0.24, 0.48, 0.40), col, w)
    _line(c, s, [(0.22, 0.68), (0.78, 0.68)], col, w)
    _oval(c, s, (0.56, 0.60, 0.68, 0.76), col, w)


def _systems(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _rect(c, s, (0.20, 0.24, 0.80, 0.60), col, w)
    _line(c, s, [(0.36, 0.60), (0.36, 0.72)], col, w)
    _line(c, s, [(0.64, 0.60), (0.64, 0.72)], col, w)
    _line(c, s, [(0.28, 0.74), (0.72, 0.74)], col, w)


def _processes(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _rect(c, s, (0.30, 0.30, 0.70, 0.70), col, w)
    for t in (0.40, 0.50, 0.60):
        _line(c, s, [(t, 0.16), (t, 0.30)], col, w)
        _line(c, s, [(t, 0.70), (t, 0.84)], col, w)
        _line(c, s, [(0.16, t), (0.30, t)], col, w)
        _line(c, s, [(0.70, t), (0.84, t)], col, w)


def _network(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _oval(c, s, (0.42, 0.16, 0.58, 0.32), col, w)
    _oval(c, s, (0.16, 0.66, 0.32, 0.82), col, w)
    _oval(c, s, (0.68, 0.66, 0.84, 0.82), col, w)
    _line(c, s, [(0.50, 0.32), (0.24, 0.66)], col, w)
    _line(c, s, [(0.50, 0.32), (0.76, 0.66)], col, w)


def _files(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _line(
        c, s,
        [(0.20, 0.28), (0.44, 0.28), (0.52, 0.38), (0.80, 0.38),
         (0.80, 0.74), (0.20, 0.74), (0.20, 0.28)],
        col, w,
    )


def _models(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _oval(c, s, (0.42, 0.14, 0.58, 0.30), col, w)
    _oval(c, s, (0.16, 0.66, 0.30, 0.80), col, w)
    _oval(c, s, (0.44, 0.66, 0.56, 0.80), col, w)
    _oval(c, s, (0.70, 0.66, 0.84, 0.80), col, w)
    _line(c, s, [(0.50, 0.30), (0.50, 0.50)], col, w)
    _line(c, s, [(0.23, 0.66), (0.50, 0.50), (0.77, 0.66)], col, w)


def _agents(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _oval(c, s, (0.36, 0.20, 0.64, 0.48), col, w)
    _line(c, s, [(0.24, 0.80), (0.30, 0.58), (0.70, 0.58), (0.76, 0.80)], col, w)


def _memory(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _oval(c, s, (0.22, 0.20, 0.78, 0.80), col, w)
    _line(c, s, [(0.50, 0.20), (0.50, 0.80)], col, w)
    _line(c, s, [(0.30, 0.36), (0.44, 0.36)], col, w)
    _line(c, s, [(0.56, 0.60), (0.70, 0.60)], col, w)


def _mcp(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _oval(c, s, (0.44, 0.44, 0.56, 0.56), col, w)
    for bx, by in ((0.44, 0.14), (0.14, 0.66), (0.74, 0.66)):
        _oval(c, s, (bx, by, bx + 0.12, by + 0.12), col, w)
    _line(c, s, [(0.50, 0.44), (0.50, 0.26)], col, w)
    _line(c, s, [(0.44, 0.52), (0.26, 0.66)], col, w)
    _line(c, s, [(0.56, 0.52), (0.74, 0.66)], col, w)


def _projects(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _rect(c, s, (0.20, 0.26, 0.80, 0.74), col, w)
    _line(c, s, [(0.20, 0.40), (0.80, 0.40)], col, w)
    _line(c, s, [(0.32, 0.26), (0.32, 0.20), (0.48, 0.20), (0.48, 0.26)], col, w)


def _datasets(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _oval(c, s, (0.24, 0.18, 0.76, 0.34), col, w)
    _line(c, s, [(0.24, 0.26), (0.24, 0.74)], col, w)
    _line(c, s, [(0.76, 0.26), (0.76, 0.74)], col, w)
    c.create_arc(0.24 * s, 0.66 * s, 0.76 * s, 0.82 * s, start=180, extent=180,
                 style="arc", outline=col, width=w)
    c.create_arc(0.24 * s, 0.42 * s, 0.76 * s, 0.58 * s, start=180, extent=180,
                 style="arc", outline=col, width=w)


def _analytics(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _line(c, s, [(0.20, 0.80), (0.20, 0.20)], col, w)
    _line(c, s, [(0.20, 0.80), (0.80, 0.80)], col, w)
    _line(c, s, [(0.32, 0.66), (0.48, 0.48), (0.60, 0.58), (0.78, 0.32)], col, w)


def _core(c: tk.Canvas, s: int, col: str, w: int) -> None:
    _oval(c, s, (0.20, 0.20, 0.80, 0.80), col, w)
    _oval(c, s, (0.42, 0.42, 0.58, 0.58), col, w)


_DRAWERS: dict[str, Callable[[tk.Canvas, int, str, int], None]] = {
    "overview": _overview,
    "command": _command,
    "chat": _chat,
    "workflows": _workflows,
    "osbuilder": _osbuilder,
    "history": _history,
    "capabilities": _capabilities,
    "logs": _logs,
    "settings": _settings,
    "systems": _systems,
    "processes": _processes,
    "network": _network,
    "files": _files,
    "models": _models,
    "agents": _agents,
    "memory": _memory,
    "mcp": _mcp,
    "projects": _projects,
    "datasets": _datasets,
    "analytics": _analytics,
    "core": _core,
}


class Icon(tk.Canvas):
    """A small recolorable line glyph. ``name`` keys into the icon set."""

    def __init__(
        self,
        parent: tk.Widget,
        name: str,
        size: int = 18,
        color: str = T.TEXT_SECONDARY,
        bg: str = T.BG_SURFACE,
    ) -> None:
        super().__init__(parent, width=size, height=size, bg=bg, highlightthickness=0)
        self._name = name
        self._size = size
        self._color = color
        self._stroke = max(1, round(size * 0.09))
        self._render()

    def _render(self) -> None:
        self.delete("all")
        drawer = _DRAWERS.get(self._name)
        if drawer:
            drawer(self, self._size, self._color, self._stroke)

    def set_color(self, color: str) -> None:
        if color != self._color:
            self._color = color
            self._render()

    def set_bg(self, bg: str) -> None:
        self.configure(bg=bg)
