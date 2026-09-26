"""
Models view — the brains available to Archon.

Spec §16: models are not products, they are intelligence Archon routes tasks to.
Shows the active model + provider, the live router status, and the resolved
fallback chain (from OpenRouter). Status and the model list are fetched off the
GUI thread so a slow network call never blocks the interface.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from .. import theme as T
from ..components.panel import KeyValue, Panel, section_label


class ModelsView(ctk.CTkFrame):
    """Active model, router status, and fallback chain."""

    def __init__(
        self,
        parent: tk.Widget,
        engine: object = None,
        on_navigate: Callable[[str], None] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, fg_color=T.BG_DEEP, **kwargs)  # type: ignore[arg-type]
        self._engine = engine
        self._on_navigate = on_navigate
        self._result_queue: queue.Queue = queue.Queue()
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=2, uniform="mv")
        self.grid_columnconfigure(1, weight=3, uniform="mv")
        self._build()
        self._poll()
        self._refresh()

    def _build(self) -> None:
        # Left: router status.
        left = Panel(self, title="Intelligence Router")
        left.grid(row=0, column=0, sticky="nsew", padx=(T.PAD_PAGE, T.SPACE_MD),
                  pady=T.PAD_PAGE)
        left.body.grid_columnconfigure(0, weight=1)

        self._status_head = ctk.CTkLabel(
            left.body, text="Checking…", font=T.FONT_HEADING,
            text_color=T.TEXT_PRIMARY, anchor="w",
        )
        self._status_head.pack(fill="x")
        self._status_sub = ctk.CTkLabel(
            left.body, text="", font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED, anchor="w",
        )
        self._status_sub.pack(fill="x", pady=(0, T.SPACE_MD))

        self._kv: dict[str, KeyValue] = {}
        for key, label in (("provider", "Provider"), ("model", "Active Model"),
                           ("key", "API Key"), ("chain", "Fallback Depth")):
            kv = KeyValue(left.body, label, "—")
            kv.pack(fill="x", pady=3)
            self._kv[key] = kv

        section_label(left.body, "Task Routing").pack(fill="x", pady=(T.SPACE_LG, T.SPACE_SM))
        for cap in ("Reasoning", "Coding", "Vision", "Fast", "Long Context"):
            row = ctk.CTkFrame(left.body, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text="→", font=T.FONT_CODE_SMALL,
                         text_color=T.GOLD).pack(side="left", padx=(0, T.SPACE_SM))
            ctk.CTkLabel(row, text=cap, font=T.FONT_SMALL,
                         text_color=T.TEXT_SECONDARY, anchor="w").pack(side="left")

        # Right: fallback chain listing.
        right = Panel(self, title="Fallback Chain")
        right.grid(row=0, column=1, sticky="nsew", padx=(T.SPACE_MD, T.PAD_PAGE),
                   pady=T.PAD_PAGE)
        right.body.grid_rowconfigure(0, weight=1)
        right.body.grid_columnconfigure(0, weight=1)
        self._list = ctk.CTkScrollableFrame(
            right.body, fg_color="transparent",
            scrollbar_button_color=T.BG_RAISED,
            scrollbar_button_hover_color=T.PURPLE,
        )
        self._list.grid(row=0, column=0, sticky="nsew")
        self._list.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self._list, text="Resolving models…", font=T.FONT_SMALL,
                     text_color=T.TEXT_MUTED).pack(pady=T.SPACE_LG)

    def refresh(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        status: dict = {}
        try:
            if self._engine and hasattr(self._engine, "get_ai_status"):
                status = self._engine.get_ai_status() or {}
        except Exception as exc:
            status = {"available": False, "last_error": str(exc)}
        self._result_queue.put(status)

    def _poll(self) -> None:
        try:
            while True:
                status = self._result_queue.get_nowait()
                self._render(status)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(200, self._poll)

    def _render(self, status: dict) -> None:
        available = bool(status.get("available"))
        self._status_head.configure(
            text="● ONLINE" if available else "○ OFFLINE",
            text_color=T.SUCCESS if available else T.TEXT_MUTED,
        )
        if available:
            self._status_sub.configure(text="Archon intelligence layer is active.")
        else:
            err = status.get("last_error") or (
                "No API key configured." if not status.get("has_api_key")
                else "No model responded.")
            self._status_sub.configure(text=str(err)[:70])

        self._kv["provider"].set(status.get("provider") or "—")
        self._kv["model"].set(status.get("model") or "—",
                              T.TEXT_ACCENT if available else T.TEXT_MUTED)
        self._kv["key"].set("Present" if status.get("has_api_key") else "Missing",
                            T.SUCCESS if status.get("has_api_key") else T.WARNING)
        models = status.get("available_models") or []
        self._kv["chain"].set(str(len(models)) if models else "—")

        for child in self._list.winfo_children():
            child.destroy()
        if not models:
            ctk.CTkLabel(
                self._list, text="No models resolved.\nConnect an API key in Settings.",
                font=T.FONT_SMALL, text_color=T.TEXT_MUTED, justify="center",
            ).pack(pady=T.SPACE_2XL)
            return
        active = status.get("model")
        for i, model_id in enumerate(models):
            self._model_row(i + 1, model_id, model_id == active)

    def _model_row(self, rank: int, model_id: str, is_active: bool) -> None:
        row = ctk.CTkFrame(
            self._list, fg_color=T.BG_RAISED if is_active else "transparent",
            corner_radius=T.RADIUS_SM, border_width=1,
            border_color=T.BORDER_ACCENT if is_active else T.BORDER_SUBTLE,
        )
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=f"{rank:02d}", font=T.FONT_CODE_SMALL,
                     text_color=T.GOLD if is_active else T.TEXT_DIM,
                     width=28).pack(side="left", padx=(T.SPACE_SM, 0), pady=6)
        ctk.CTkLabel(row, text=model_id, font=T.FONT_CODE_SMALL,
                     text_color=T.TEXT_PRIMARY if is_active else T.TEXT_SECONDARY,
                     anchor="w").pack(side="left", fill="x", expand=True,
                                      padx=T.SPACE_SM)
        if is_active:
            ctk.CTkLabel(row, text="ACTIVE", font=(T.FONT_FAMILY, 9, "bold"),
                         text_color=T.GOLD).pack(side="right", padx=T.SPACE_MD)
