"""
ChatBubble — individual message bubble for the chat page.
"""

from __future__ import annotations

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
            text_color=T.TEXT_WHITE,
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
        avatar = _TyranosAvatar(row, size=32)
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
            text=text,
            text_color=T.TEXT_PRIMARY,
            font=T.FONT_BODY,
            wraplength=440,
            justify="left",
        ).pack(padx=T.SPACE_MD, pady=(T.SPACE_SM, T.SPACE_SM))

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
            text=f"❌  {text}",
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


class _TyranosAvatar(tk.Canvas):
    """Small 32px circular Tyranos avatar for assistant bubbles."""

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
        # Circle background
        pad = 2
        self.create_oval(pad, pad, s - pad, s - pad, fill=T.PURPLE_DARK, outline=T.PURPLE, width=1.5)
        # "T" shape
        cx, cy = s // 2, s // 2
        bar_w, bar_h = int(s * 0.55), int(s * 0.1)
        stem_w, stem_h = int(s * 0.15), int(s * 0.28)
        # Top bar
        self.create_rectangle(
            cx - bar_w // 2, cy - bar_h // 2 - stem_h // 2,
            cx + bar_w // 2, cy - bar_h // 2 - stem_h // 2 + bar_h,
            fill=T.CYAN_LIGHT, outline="",
        )
        # Vertical stem
        self.create_rectangle(
            cx - stem_w // 2, cy - bar_h // 2 - stem_h // 2 + bar_h,
            cx + stem_w // 2, cy - bar_h // 2 - stem_h // 2 + bar_h + stem_h,
            fill=T.PURPLE_LIGHT, outline="",
        )
