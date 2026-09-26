"""
Toast notification system — slides up from bottom-right.
"""

from __future__ import annotations

import tkinter as tk
from typing import Literal

import customtkinter as ctk

from .. import theme as T

_ToastType = Literal["success", "error", "warning", "info"]


class Toast(ctk.CTkFrame):
    """A single toast notification."""

    _ICONS = {"success": "✓", "error": "✕", "warning": "!", "info": "i"}
    _COLORS = {
        "success": (T.SUCCESS, T.SUCCESS_GLOW),
        "error": (T.ERROR, T.ERROR_DIM),
        "warning": (T.WARNING, T.WARNING_DIM),
        "info": (T.CYAN, T.CYAN_GLOW),
    }

    def __init__(
        self,
        parent: tk.Widget,
        message: str,
        toast_type: _ToastType = "info",
        duration_ms: int = 3500,
        on_close: object = None,
    ) -> None:
        text_color, bg = self._COLORS.get(toast_type, (T.TEXT_PRIMARY, T.BG_SURFACE))
        super().__init__(
            parent,
            fg_color=bg,
            corner_radius=T.RADIUS_CARD,
            border_color=text_color,
            border_width=1,
        )

        icon = self._ICONS.get(toast_type, "i")
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=T.SPACE_MD, pady=T.SPACE_SM)

        ctk.CTkLabel(inner, text=icon, font=T.FONT_BODY).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            inner,
            text=message,
            text_color=T.TEXT_PRIMARY,
            font=T.FONT_BODY,
            wraplength=280,
            justify="left",
        ).pack(side="left", fill="x", expand=True)

        btn = ctk.CTkButton(
            inner,
            text="✕",
            width=24,
            height=24,
            fg_color="transparent",
            hover_color=T.BG_RAISED,
            text_color=T.TEXT_SECONDARY,
            command=lambda: self._dismiss(on_close),
        )
        btn.pack(side="right")

        self._duration_ms = duration_ms
        self._on_close = on_close
        self.after(duration_ms, lambda: self._dismiss(on_close))

    def _dismiss(self, on_close: object) -> None:
        if callable(on_close):
            on_close(self)
        try:
            self.destroy()
        except Exception:
            pass


class ToastManager:
    """
    Manages a stack of toast notifications anchored to a parent window.

    Usage:
        mgr = ToastManager(root_window)
        mgr.show("File saved!", "success")
        mgr.show("Connection failed", "error")
    """

    def __init__(self, root: tk.Tk | ctk.CTk) -> None:
        self._root = root
        self._toasts: list[Toast] = []
        self._margin_right = 20
        self._margin_bottom = 20
        self._gap = 8

    def show(
        self,
        message: str,
        toast_type: _ToastType = "info",
        duration_ms: int = 3500,
    ) -> None:
        toast = Toast(
            self._root,
            message=message,
            toast_type=toast_type,
            duration_ms=duration_ms,
            on_close=self._remove,
        )
        toast.place(x=-500, y=-500)  # off-screen initially
        self._toasts.append(toast)
        self._root.update_idletasks()
        self._reposition()

    def _remove(self, toast: Toast) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
        self._root.after(50, self._reposition)

    def _reposition(self) -> None:
        """Stack toasts from bottom-right."""
        w = self._root.winfo_width()
        h = self._root.winfo_height()
        y = h - self._margin_bottom
        for toast in reversed(self._toasts):
            try:
                toast.update_idletasks()
                th = toast.winfo_reqheight()
                tw = toast.winfo_reqwidth()
                x = w - tw - self._margin_right
                y -= th
                toast.place(x=max(x, 8), y=y)
                y -= self._gap
            except Exception:
                pass
