"""
ChatBubble — individual message bubble for the chat page.
"""

from __future__ import annotations

import math
import tkinter as tk

import customtkinter as ctk

from .. import theme as T


class ChatBubble(ctk.CTkFrame):
    """
    A single chat message bubble.

    Parameters
    ----------
    parent : tk.Widget
    text : str
        Message content.
    role : str
        "user" | "assistant" | "error"
    timestamp : str
        Display timestamp string.
    """

    def __init__(
        self,
        parent: tk.Widget,
        text: str = "",
        role: str = "assistant",
        timestamp: str = "",
        **kwargs: object,
    ) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)  # type: ignore[arg-type]
        self._role = role
        self._text = text
        self._build(text, role, timestamp)

    def _build(self, text: str, role: str, timestamp: str) -> None:
        if role == "user":
            self._build_user(text, timestamp)
        elif role == "error":
            self._build_error(text, timestamp)
        else:
            self._build_assistant(text, timestamp)

    def _build_user(self, text: str, timestamp: str) -> None:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(4, 0))

        # Spacer to push bubble right
        ctk.CTkFrame(row, fg_color="transparent").pack(side="left", fill="x", expand=True)

        bubble = ctk.CTkFrame(
            row,
            fg_color=T.PURPLE,
            corner_radius=T.RADIUS_CARD,
        )
        bubble.pack(side="right", padx=(0, 8))

        ctk.CTkLabel(
            bubble,
            text=text,
            text_color=T.BG_DEEP,
            font=T.FONT_BODY,
            wraplength=420,
            justify="left",
        ).pack(padx=T.SPACE_MD, pady=(T.SPACE_SM, 4))

        if timestamp:
            ctk.CTkLabel(
                self,
                text=timestamp,
                text_color=T.TEXT_MUTED,
                font=T.FONT_MICRO,
                anchor="e",
            ).pack(fill="x", padx=12, pady=(0, 4))

    def _build_assistant(self, text: str, timestamp: str) -> None:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(4, 0))

        # Avatar
        avatar = _ArchonAvatar(row, size=32)
        avatar.pack(side="left", padx=(8, 6), anchor="n", pady=4)

        bubble = ctk.CTkFrame(
            row,
            fg_color=T.BG_RAISED,
            corner_radius=T.RADIUS_CARD,
            border_color=T.BORDER_ACCENT,
            border_width=1,
        )
        bubble.pack(side="left", padx=(0, 40))

        ctk.CTkLabel(
            bubble,
            text="Archon",
            text_color=T.TEXT_ACCENT,
            font=T.FONT_MICRO,
            anchor="w",
        ).pack(anchor="w", padx=T.SPACE_MD, pady=(T.SPACE_SM, 0))

        ctk.CTkLabel(
            bubble,
            text=text,
            text_color=T.TEXT_PRIMARY,
            font=T.FONT_BODY,
            wraplength=440,
            justify="left",
        ).pack(padx=T.SPACE_MD, pady=(2, T.SPACE_SM))

        if timestamp:
            ctk.CTkLabel(
                self,
                text=timestamp,
                text_color=T.TEXT_MUTED,
                font=T.FONT_MICRO,
                anchor="w",
            ).pack(fill="x", padx=52, pady=(0, 4))

    def _build_error(self, text: str, timestamp: str) -> None:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(4, 0))

        bubble = ctk.CTkFrame(
            row,
            fg_color=T.ERROR_DIM,
            corner_radius=T.RADIUS_CARD,
            border_color=T.ERROR,
            border_width=2,
        )
        bubble.pack(fill="x", padx=8)

        ctk.CTkLabel(
            bubble,
            text=f"✕  {text}",
            text_color=T.TEXT_PRIMARY,
            font=T.FONT_BODY,
            wraplength=500,
            justify="left",
        ).pack(padx=T.SPACE_MD, pady=T.SPACE_SM)

        if timestamp:
            ctk.CTkLabel(
                bubble,
                text=timestamp,
                text_color=T.TEXT_MUTED,
                font=T.FONT_MICRO,
                anchor="w",
            ).pack(fill="x", padx=T.SPACE_MD, pady=(0, 6))

    def update_text(self, text: str) -> None:
        """Rebuild bubble with new text (for streaming)."""
        for child in self.winfo_children():
            child.destroy()
        self._text = text
        self._build(text, self._role, "")


class _ArchonAvatar(tk.Canvas):
    """Small circular Archon avatar (mini tri-blade sigil) for assistant bubbles."""

    def __init__(self, parent: tk.Widget, size: int = 32) -> None:
        super().__init__(
            parent,
            width=size,
            height=size,
            bg=T.BG_DEEP,
            highlightthickness=0,
        )
        self._draw(size)

    def _draw(self, s: int) -> None:
        c = s / 2
        # Obsidian disc with a thin gold rim.
        pad = 1.5
        self.create_oval(
            pad, pad, s - pad, s - pad, fill=T.BG_RAISED, outline=T.PURPLE, width=1.4
        )
        # Three compact blades radiating from center — apex up, swept down.
        r_tip, r_in, half = s * 0.32, s * 0.05, s * 0.09
        for k in range(3):
            a = -math.pi / 2 + k * (math.tau / 3)
            dx, dy = math.cos(a), math.sin(a)
            px, py = -math.sin(a), math.cos(a)
            tip = (c + r_tip * dx, c + r_tip * dy)
            inner = (c + r_in * dx, c + r_in * dy)
            sl = (c + s * 0.16 * dx - half * px, c + s * 0.16 * dy - half * py)
            sr = (c + s * 0.16 * dx + half * px, c + s * 0.16 * dy + half * py)
            self.create_polygon(*tip, *sl, *inner, fill=T.BG_HIGHLIGHT, outline="")
            self.create_polygon(*tip, *sr, *inner, fill=T.PURPLE_DARK, outline="")
            self.create_line(*tip, *sr, fill=T.PURPLE_LIGHT, width=1)
        # Gold core spark.
        kr = max(1.0, s * 0.05)
        self.create_oval(c - kr, c - kr, c + kr, c + kr, fill=T.GOLD, outline="")
