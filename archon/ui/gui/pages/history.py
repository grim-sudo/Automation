"""
History page — filterable log of all past automation runs.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from datetime import datetime

import customtkinter as ctk

from .. import theme as T
from ..components.status_badge import StatusBadge


def _map_record(rec: dict) -> dict:
    """Map an engine execution record to the history table's display shape."""
    ts = rec.get("timestamp", "")
    try:
        ts = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        pass
    dur = rec.get("duration")
    duration = f"{dur:.1f}s" if isinstance(dur, (int, float)) else ""
    return {
        "ts": ts,
        "cmd": rec.get("original_command", ""),
        "status": "ok" if rec.get("success", True) else "error",
        "duration": duration,
    }


class HistoryPage(ctk.CTkFrame):
    """
    Command execution history with search, filter, and export.
    """

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
        self._history: list[dict] = self._load_history()

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_topbar()
        self._build_body()

    def _load_history(self) -> list[dict]:
        """Pull recent runs from the engine's audit trail (newest first)."""
        getter = getattr(self._engine, "get_execution_history", None)
        if not callable(getter):
            return []
        try:
            records = getter(200)
        except Exception:
            return []
        return [_map_record(r) for r in reversed(records)]

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_topbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color=T.BG_SURFACE, corner_radius=0, height=52)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=1)

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right", padx=T.PAD_CARD)
        ctk.CTkButton(
            right,
            text="⬇  Export",
            width=90,
            **T.btn_outline_kwargs(),
            command=self._export,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            right,
            text="Clear",
            width=70,
            **T.btn_ghost_kwargs(),
            command=self._clear_history,
        ).pack(side="left")

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=T.PAD_PAGE, pady=T.PAD_CARD)
        body.grid_rowconfigure(1, weight=1)
        body.grid_columnconfigure(0, weight=1)

        # Filter bar
        filter_row = ctk.CTkFrame(body, fg_color="transparent")
        filter_row.grid(row=0, column=0, sticky="ew", pady=(0, T.SPACE_MD))
        filter_row.grid_columnconfigure(0, weight=1)

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_filter)

        ctk.CTkEntry(
            filter_row,
            textvariable=self._search_var,
            placeholder_text="Search history…",
            **T.input_kwargs(),
        ).grid(row=0, column=0, sticky="ew", padx=(0, T.SPACE_SM))

        self._status_filter = ctk.CTkSegmentedButton(
            filter_row,
            values=["All", "✓ OK", "✗ Error", "⚠ Warn"],
            command=self._on_filter,
            font=T.FONT_SMALL,
            fg_color=T.BG_RAISED,
            selected_color=T.PURPLE,
            selected_hover_color=T.PURPLE_DIM,
            unselected_color=T.BG_RAISED,
            unselected_hover_color=T.BG_HIGHLIGHT,
            text_color=T.TEXT_PRIMARY,
        )
        self._status_filter.set("All")
        self._status_filter.grid(row=0, column=1)

        # Table card
        card = ctk.CTkFrame(body, **T.card_kwargs())
        card.grid(row=1, column=0, sticky="nsew")
        card.grid_rowconfigure(1, weight=1)
        card.grid_columnconfigure(0, weight=1)

        # Column headers
        header = ctk.CTkFrame(card, fg_color=T.BG_RAISED, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        for text, width in [("Timestamp", 160), ("Command", 0), ("Status", 80), ("Duration", 80)]:
            ctk.CTkLabel(
                header,
                text=text,
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                width=width or 1,
                anchor="w",
            ).pack(
                side="left",
                padx=T.SPACE_SM,
                pady=T.SPACE_XS,
                expand=(width == 0),
                fill="x" if width == 0 else "none",
            )

        self._list_frame = ctk.CTkScrollableFrame(
            card,
            fg_color=T.BG_DEEP,
            corner_radius=0,
            scrollbar_button_color=T.BG_RAISED,
            scrollbar_button_hover_color=T.PURPLE,
        )
        self._list_frame.grid(row=1, column=0, sticky="nsew")
        self._list_frame.grid_columnconfigure(0, weight=1)

        self._render_history(self._history)

    # ── Filtering & rendering ─────────────────────────────────────────────────

    def _on_filter(self, *_args: object) -> None:
        q = self._search_var.get().lower()
        sf = self._status_filter.get()

        status_map = {"✓ OK": "ok", "✗ Error": "error", "⚠ Warn": "warn"}
        status_filter = status_map.get(sf)

        filtered = self._history
        if q:
            filtered = [h for h in filtered if q in h["cmd"].lower()]
        if status_filter:
            filtered = [h for h in filtered if h["status"] == status_filter]

        self._render_history(filtered)

    def _render_history(self, items: list[dict]) -> None:
        for child in self._list_frame.winfo_children():
            child.destroy()

        if not items:
            ctk.CTkLabel(
                self._list_frame,
                text="No history entries match your filter.",
                **T.label_secondary_kwargs(),
            ).pack(pady=T.SPACE_2XL)
            return

        for item in items:
            _HistoryEntry(self._list_frame, entry=item).pack(fill="x", pady=1)

    def _export(self) -> None:
        import csv
        from pathlib import Path

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = Path.home() / f"archon_history_{ts}.csv"
        try:
            with out.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["ts", "cmd", "status", "duration"])
                writer.writeheader()
                writer.writerows(self._history)
        except Exception:
            pass

    def _clear_history(self) -> None:
        self._history = []
        self._render_history([])

    def refresh(self) -> None:
        """Re-pull history from the engine (called when re-entering the page)."""
        self._history = self._load_history()
        self._on_filter()


class _HistoryEntry(ctk.CTkFrame):
    """Single row in the history table."""

    def __init__(self, parent: tk.Widget, entry: dict, **kwargs: object) -> None:
        super().__init__(
            parent,
            fg_color=T.BG_SURFACE,
            corner_radius=T.RADIUS_SM,
            **kwargs,  # type: ignore[arg-type]
        )

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=T.SPACE_SM, pady=T.SPACE_XS)

        ctk.CTkLabel(
            inner,
            text=entry.get("ts", ""),
            font=T.FONT_CODE_SMALL,
            text_color=T.TEXT_MUTED,
            width=160,
            anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            inner,
            text=entry.get("cmd", ""),
            font=T.FONT_SMALL,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left", fill="x", expand=True, padx=(T.SPACE_SM, 0))

        status = entry.get("status", "ok")
        badge_status = {"ok": "active", "error": "error", "warn": "warning"}.get(status, "inactive")
        badge_text = {"ok": "✓  OK", "error": "✗  Error", "warn": "⚠  Warn"}.get(status, status)
        StatusBadge(inner, text=badge_text, status=badge_status).pack(side="right", padx=T.SPACE_SM)

        ctk.CTkLabel(
            inner,
            text=entry.get("duration", ""),
            font=T.FONT_CODE_SMALL,
            text_color=T.TEXT_SECONDARY,
            width=70,
            anchor="e",
        ).pack(side="right")

        for w in [self, inner]:
            w.bind("<Enter>", self._enter, add="+")
            w.bind("<Leave>", self._leave, add="+")

    def _enter(self, _e: tk.Event) -> None:  # type: ignore[type-arg]
        self.configure(fg_color=T.BG_RAISED)

    def _leave(self, _e: tk.Event) -> None:  # type: ignore[type-arg]
        self.configure(fg_color=T.BG_SURFACE)
