"""
Processes view — live process table for the local machine.

Spec §11/§30: a compact instrument, not a wall of cards. Sortable by CPU / RAM,
refreshed off the GUI thread via a background sampler so the table never blocks.
Backed entirely by ``psutil`` (already a project dependency).
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from .. import theme as T
from ..components.panel import Panel

_COLUMNS = [
    ("pid", "PID", 0.12),
    ("name", "PROCESS", 0.40),
    ("cpu", "CPU %", 0.16),
    ("mem", "MEM %", 0.16),
    ("user", "USER", 0.16),
]


class ProcessesView(ctk.CTkFrame):
    """Live, sortable process table."""

    def __init__(
        self,
        parent: tk.Widget,
        engine: object = None,
        on_navigate: Callable[[str], None] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, fg_color=T.BG_DEEP, **kwargs)  # type: ignore[arg-type]
        self._engine = engine
        self._sort_key = "cpu"
        self._rows: list[ctk.CTkFrame] = []
        self._result_queue: queue.Queue = queue.Queue()
        self._sampling = False

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build()
        self._poll()
        self._schedule_sample()

    def _build(self) -> None:
        panel = Panel(self, title="Processes", eyebrow="localhost")
        panel.grid(row=0, column=0, sticky="nsew", padx=T.PAD_PAGE, pady=T.PAD_PAGE)
        panel.body.grid_rowconfigure(2, weight=1)
        panel.body.grid_columnconfigure(0, weight=1)

        # Sort controls in the header action slot.
        sort_row = ctk.CTkFrame(panel.action_parent, fg_color="transparent")
        panel.add_action(sort_row)
        ctk.CTkLabel(sort_row, text="SORT", font=(T.FONT_FAMILY, 10, "bold"),
                     text_color=T.TEXT_MUTED).pack(side="left", padx=(0, T.SPACE_SM))
        self._sort_btns: dict[str, ctk.CTkButton] = {}
        for key, label in (("cpu", "CPU"), ("mem", "MEM")):
            b = ctk.CTkButton(
                sort_row, text=label, width=52, height=26,
                **T.btn_ghost_kwargs(),
                command=lambda k=key: self._set_sort(k),
            )
            b.pack(side="left", padx=2)
            self._sort_btns[key] = b
        self._apply_sort_style()

        # Header row.
        header = ctk.CTkFrame(panel.body, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, T.SPACE_SM))
        for i, (_key, label, weight) in enumerate(_COLUMNS):
            header.grid_columnconfigure(i, weight=int(weight * 100))
            ctk.CTkLabel(
                header, text=label, font=(T.FONT_FAMILY, 10, "bold"),
                text_color=T.TEXT_MUTED,
                anchor="e" if _key in ("cpu", "mem") else "w",
            ).grid(row=0, column=i, sticky="ew", padx=T.SPACE_SM)

        ctk.CTkFrame(panel.body, height=1, fg_color=T.BORDER_SUBTLE).grid(
            row=1, column=0, sticky="ew")

        self._table = ctk.CTkScrollableFrame(
            panel.body, fg_color="transparent",
            scrollbar_button_color=T.BG_RAISED,
            scrollbar_button_hover_color=T.PURPLE,
        )
        self._table.grid(row=2, column=0, sticky="nsew", pady=(T.SPACE_SM, 0))
        self._table.grid_columnconfigure(0, weight=1)

    def _set_sort(self, key: str) -> None:
        self._sort_key = key
        self._apply_sort_style()

    def _apply_sort_style(self) -> None:
        for key, btn in self._sort_btns.items():
            active = key == self._sort_key
            btn.configure(
                text_color=T.TEXT_ACCENT if active else T.TEXT_SECONDARY,
                fg_color=T.BG_HIGHLIGHT if active else "transparent",
            )

    # ── Sampling (off-thread) ───────────────────────────────────────────────

    def _schedule_sample(self) -> None:
        if not self.winfo_exists():
            return
        if not self._sampling:
            self._sampling = True
            threading.Thread(target=self._sample, daemon=True).start()
        self.after(2500, self._schedule_sample)

    def _sample(self) -> None:
        procs: list[dict] = []
        try:
            import psutil

            for p in psutil.process_iter(["pid", "name", "cpu_percent",
                                          "memory_percent", "username"]):
                info = p.info
                procs.append({
                    "pid": info.get("pid", 0),
                    "name": (info.get("name") or "?")[:28],
                    "cpu": info.get("cpu_percent") or 0.0,
                    "mem": info.get("memory_percent") or 0.0,
                    "user": (info.get("username") or "—").split("\\")[-1][:12],
                })
        except Exception:
            pass
        self._result_queue.put(procs)

    def _poll(self) -> None:
        latest = None
        try:
            while True:
                latest = self._result_queue.get_nowait()
        except queue.Empty:
            pass
        if latest is not None:
            self._render(latest)
            self._sampling = False
        if self.winfo_exists():
            self.after(300, self._poll)

    def _render(self, procs: list[dict]) -> None:
        procs.sort(key=lambda p: p.get(self._sort_key, 0.0), reverse=True)
        for r in self._rows:
            r.destroy()
        self._rows.clear()
        for proc in procs[:60]:
            self._rows.append(_ProcRow(self._table, proc))
            self._rows[-1].pack(fill="x", pady=1)


class _ProcRow(ctk.CTkFrame):
    def __init__(self, parent: tk.Widget, proc: dict, **kwargs: object) -> None:
        super().__init__(parent, fg_color="transparent",
                         corner_radius=T.RADIUS_SM, **kwargs)  # type: ignore[arg-type]
        for i, (_key, _label, weight) in enumerate(_COLUMNS):
            self.grid_columnconfigure(i, weight=int(weight * 100))
        vals = {
            "pid": (str(proc["pid"]), T.TEXT_DIM, "w"),
            "name": (proc["name"], T.TEXT_PRIMARY, "w"),
            "cpu": (f"{proc['cpu']:.1f}", self._heat(proc["cpu"], 60), "e"),
            "mem": (f"{proc['mem']:.1f}", self._heat(proc["mem"], 25), "e"),
            "user": (proc["user"], T.TEXT_MUTED, "w"),
        }
        for i, (key, _label, _weight) in enumerate(_COLUMNS):
            text, color, anchor = vals[key]
            ctk.CTkLabel(
                self, text=text,
                font=T.FONT_CODE_SMALL if key != "name" else T.FONT_SMALL,
                text_color=color, anchor=anchor,
            ).grid(row=0, column=i, sticky="ew", padx=T.SPACE_SM, pady=3)

    @staticmethod
    def _heat(value: float, hot: float) -> str:
        if value >= hot:
            return T.WARNING
        if value >= hot * 0.5:
            return T.TEXT_ACCENT
        return T.TEXT_SECONDARY
