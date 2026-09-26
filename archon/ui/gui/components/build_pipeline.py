"""
BuildPipeline — horizontal architectural stage pipeline.

Spec §18 / §26: SPEC → ROOTFS → KERNEL → IMAGE → QEMU → VERIFY. The active
stage is gold, completed stages metallic, future stages dim, failures red.
Drawn on a single canvas so the connecting rail and stage chips stay aligned at
any width.
"""

from __future__ import annotations

import tkinter as tk

from .. import theme as T


class BuildPipeline(tk.Canvas):
    """A horizontal stage pipeline with connecting rail."""

    def __init__(
        self,
        parent: tk.Widget,
        stages: list[str],
        bg: str = T.BG_SURFACE,
        height: int = 72,
        **kwargs: object,
    ) -> None:
        super().__init__(
            parent, height=height, bg=bg, highlightthickness=0, bd=0,
            **kwargs,  # type: ignore[arg-type]
        )
        self._stages = stages
        self._bg = bg
        # state per stage index: done | active | future | failed
        self._states = ["future"] * len(stages)
        self.bind("<Configure>", lambda _e: self._draw())

    def set_states(self, states: list[str]) -> None:
        self._states = states + ["future"] * (len(self._stages) - len(states))
        self._draw()

    def set_active(self, index: int) -> None:
        """Mark stages before ``index`` done, ``index`` active, rest future."""
        states = []
        for i in range(len(self._stages)):
            states.append("done" if i < index else "active" if i == index else "future")
        self.set_states(states)

    def _draw(self) -> None:
        self.delete("all")
        w = self.winfo_width() or 600
        h = self.winfo_height() or 72
        n = len(self._stages)
        if n == 0:
            return
        cy = h * 0.42
        margin = w / (n * 2)
        xs = [margin + (w - 2 * margin) * (i / (n - 1) if n > 1 else 0.5)
              for i in range(n)]

        # Rail segments colored by the left node's completion.
        for i in range(n - 1):
            st = self._states[i]
            col = (T.GOLD if st in ("done", "active")
                   else T.ERROR if st == "failed" else T.BORDER_STRONG)
            self.create_line(xs[i], cy, xs[i + 1], cy, fill=col, width=2)

        for i, (x, name) in enumerate(zip(xs, self._stages, strict=False)):
            st = self._states[i]
            if st in ("done", "completed"):
                fill, outline, txt = T.GOLD_DARK, T.GOLD_DARK, T.TEXT_SECONDARY
                glyph = "✓"
            elif st in ("active", "running"):
                fill, outline, txt = T.BG_SURFACE, T.GOLD, T.TEXT_ACCENT
                glyph = "●"
            elif st in ("failed", "error"):
                fill, outline, txt = T.BG_SURFACE, T.ERROR, T.ERROR
                glyph = "✕"
            else:
                fill, outline, txt = T.BG_SURFACE, T.BORDER_STRONG, T.TEXT_DIM
                glyph = "○"
            r = 11
            self.create_oval(x - r, cy - r, x + r, cy + r, fill=fill,
                             outline=outline, width=2)
            self.create_text(x, cy, text=glyph, fill=txt,
                             font=(T.FONT_FAMILY, 10, "bold"))
            self.create_text(
                x, cy + r + 12, text=name,
                fill=T.TEXT_ACCENT if st in ("active", "running") else T.TEXT_MUTED,
                font=(T.FONT_FAMILY, 8, "bold"),
            )
