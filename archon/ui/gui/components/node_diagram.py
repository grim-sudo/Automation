"""
NodeDiagram — canvas-drawn workflow node visualization.
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from .. import theme as T

_NODE_ICONS = {
    "webhook": "◈",
    "schedule": "○",
    "http": "◍",
    "email": "▫",
    "slack": "❯",
    "github": "◆",
    "database": "▤",
    "transform": "⚙",
    "filter": "◇",
    "default": "•",
}


class NodeDiagram(ctk.CTkFrame):
    """
    Canvas-based visual representation of an n8n workflow as connected nodes.

    Parameters
    ----------
    parent : tk.Widget
    nodes : list[dict]
        Each dict: {"label": str, "type": str, "x": int, "y": int}
    edges : list[tuple[int, int]]
        List of (from_index, to_index) pairs.
    width, height : int
        Canvas dimensions.
    animated : bool
        If True, shows a traveling dot along edges.
    """

    NODE_W = 80
    NODE_H = 44
    NODE_R = 10

    def __init__(
        self,
        parent: tk.Widget,
        nodes: list[dict] | None = None,
        edges: list[tuple[int, int]] | None = None,
        width: int = 500,
        height: int = 180,
        animated: bool = True,
        **kwargs: object,
    ) -> None:
        super().__init__(
            parent,
            fg_color=T.BG_RAISED,
            corner_radius=T.RADIUS_CARD,
            **kwargs,  # type: ignore[arg-type]
        )
        self._nodes = nodes or []
        self._edges = edges or []
        self._animated = animated
        self._anim_phase: dict[int, float] = {}
        self._running = False

        self._canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=T.BG_RAISED,
            highlightthickness=0,
        )
        self._canvas.pack(padx=T.SPACE_SM, pady=T.SPACE_SM)
        self._render()
        if animated and edges:
            self._start_animation()

    def set_workflow(self, nodes: list[dict], edges: list[tuple[int, int]]) -> None:
        """Replace displayed workflow."""
        self._nodes = nodes
        self._edges = edges
        self._anim_phase = {}
        self._render()

    def _render(self) -> None:
        c = self._canvas
        c.delete("all")
        if not self._nodes:
            c.create_text(
                int(c.winfo_reqwidth()) // 2,
                int(c.winfo_reqheight()) // 2,
                text="No nodes",
                fill=T.TEXT_MUTED,
                font=T.FONT_SMALL,
            )
            return

        # Auto-layout: evenly space nodes horizontally
        n = len(self._nodes)
        cw = c.winfo_reqwidth()
        ch = c.winfo_reqheight()
        pad_x = 40
        step_x = max((cw - 2 * pad_x) // max(n - 1, 1), self.NODE_W + 20)
        cy = ch // 2

        positions: list[tuple[int, int]] = []
        for i, node in enumerate(self._nodes):
            nx = node.get("x", pad_x + i * step_x)
            ny = node.get("y", cy)
            positions.append((int(nx), int(ny)))

        # Draw edges
        for ei, (a, b) in enumerate(self._edges):
            if a >= len(positions) or b >= len(positions):
                continue
            ax, ay = positions[a]
            bx, by = positions[b]
            # Edge line
            c.create_line(
                ax + self.NODE_W,
                ay,
                bx,
                by,
                fill=T.BORDER_ACCENT,
                width=2,
                smooth=True,
            )
            # Arrow head
            c.create_polygon(
                bx - 8,
                by - 5,
                bx,
                by,
                bx - 8,
                by + 5,
                fill=T.PURPLE,
                outline="",
            )
            if self._animated:
                self._anim_phase[ei] = 0.0

        # Draw nodes
        for i, node in enumerate(self._nodes):
            x, y = positions[i]
            label = node.get("label", "Node")
            node_type = node.get("type", "default")
            icon = _NODE_ICONS.get(node_type, _NODE_ICONS["default"])

            # Node bg
            c.create_rectangle(
                x,
                y - self.NODE_H // 2,
                x + self.NODE_W,
                y + self.NODE_H // 2,
                fill=T.BG_SURFACE,
                outline=T.BORDER_ACCENT,
                width=1,
            )
            # Icon + label
            c.create_text(x + self.NODE_W // 2, y - 8, text=icon, fill=T.TEXT_ACCENT, font=("", 14))
            c.create_text(
                x + self.NODE_W // 2,
                y + 10,
                text=label[:10],
                fill=T.TEXT_PRIMARY,
                font=T.FONT_MICRO,
            )

    def _start_animation(self) -> None:
        self._running = True
        self._anim_tick()

    def _anim_tick(self) -> None:
        if not self._running:
            return
        c = self._canvas
        c.delete("anim_dot")
        if not self._nodes or not self._edges:
            return

        n = len(self._nodes)
        cw = c.winfo_reqwidth()
        pad_x = 40
        ch = c.winfo_reqheight()
        cy = ch // 2
        step_x = max((cw - 2 * pad_x) // max(n - 1, 1), self.NODE_W + 20)

        positions: list[tuple[int, int]] = []
        for node in self._nodes:
            nx = node.get("x", pad_x + len(positions) * step_x)
            ny = node.get("y", cy)
            positions.append((int(nx), int(ny)))

        for ei, (a, b) in enumerate(self._edges):
            if a >= len(positions) or b >= len(positions):
                continue
            self._anim_phase[ei] = (self._anim_phase.get(ei, 0.0) + 0.02) % 1.0
            t = self._anim_phase[ei]
            ax, ay = positions[a]
            bx, by = positions[b]
            sx = ax + self.NODE_W
            ex = bx
            px = sx + int((ex - sx) * t)
            py = ay + int((by - ay) * t)
            r = 4
            try:
                c.create_oval(
                    px - r,
                    py - r,
                    px + r,
                    py + r,
                    fill=T.CYAN_LIGHT,
                    outline="",
                    tags="anim_dot",
                )
            except Exception:
                return

        c.after(50, self._anim_tick)

    def destroy(self) -> None:
        self._running = False
        super().destroy()
