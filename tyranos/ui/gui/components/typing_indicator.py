"""
TypingIndicator — animated three-dot bubble shown while AI responds.
"""

from __future__ import annotations

import math
import tkinter as tk

import customtkinter as ctk

from .. import theme as T


class TypingIndicator(ctk.CTkFrame):
    """
    Three animated dots in a chat bubble shape.
    Dots pulse in sequence: ●○○ → ○●○ → ○○●
    """

    DOT_R = 5
    DOT_GAP = 14
    W = 60
    H = 32

    def __init__(self, parent: tk.Widget, **kwargs: object) -> None:
        super().__init__(
            parent,
            fg_color=T.BG_RAISED,
            corner_radius=T.RADIUS_CARD,
            **kwargs,  # type: ignore[arg-type]
        )
        self._canvas = tk.Canvas(
            self,
            width=self.W,
            height=self.H,
            bg=T.BG_RAISED,
            highlightthickness=0,
        )
        self._canvas.pack(padx=8, pady=4)

        # Create 3 dots
        cx = self.W // 2
        cy = self.H // 2
        starts = [cx - self.DOT_GAP, cx, cx + self.DOT_GAP]
        self._dot_ids = [
            self._canvas.create_oval(
                x - self.DOT_R,
                cy - self.DOT_R,
                x + self.DOT_R,
                cy + self.DOT_R,
                fill=T.BG_SURFACE,
                outline="",
            )
            for x in starts
        ]

        self._running = False
        self._phase = 0.0

    def start(self) -> None:
        """Begin animation."""
        self._running = True
        self._tick()

    def stop(self) -> None:
        """Stop animation and hide dots."""
        self._running = False
        for dot_id in self._dot_ids:
            try:
                self._canvas.itemconfig(dot_id, fill=T.BG_SURFACE)
            except Exception:
                pass

    def _tick(self) -> None:
        if not self._running:
            return
        self._phase += 0.15
        for i, dot_id in enumerate(self._dot_ids):
            # Each dot is offset by 120° (2π/3)
            angle = self._phase + i * (2 * math.pi / 3)
            intensity = (math.sin(angle) + 1) / 2
            r = int(intensity * 0xA7) + (0xFF - int(intensity * 0x58))
            g = int(intensity * 0x8B) + (0xFF - int(intensity * 0x75))
            b = 0xFA
            color = f"#{min(r, 255):02x}{min(g, 255):02x}{min(b, 255):02x}"
            try:
                self._canvas.itemconfig(dot_id, fill=color)
            except Exception:
                return
        self._canvas.after(60, self._tick)

    def destroy(self) -> None:
        self._running = False
        super().destroy()
