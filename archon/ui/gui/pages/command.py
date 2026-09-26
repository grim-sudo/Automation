"""
Command view — Archon's primary control surface.

Spec §9/§10: not a dashboard and not a chat window. A single powerful command
box ("WHAT DO YOU WANT TO ACCOMPLISH?"), the Archon Core topology, a compact
instrument strip, and an active-operations panel. Commands run off the GUI
thread and their results surface as operations, not conversation turns.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable
from datetime import datetime

import customtkinter as ctk

from .. import theme as T
from ..components.archon_core import ArchonCore
from ..components.panel import KeyValue, Panel, section_label

# Which subsystem a command most likely touches — used to light the core edge.
_ROUTE_HINTS = [
    (("build", "iso", "distro", "kernel", "os "), "BUILD"),
    (("workflow", "n8n", "automat"), "AUTOMATION"),
    (("deploy", "kubernetes", "k8s", "cluster", "cloud", "server"), "CLOUD"),
    (("analyz", "dataset", "telemetry", "query", "data"), "DATA"),
    (("remember", "prefer", "memory"), "MEMORY"),
    (("model", "route", "reason"), "AI"),
    (("system", "process", "cpu", "disk", "hardware", "file"), "SYSTEMS"),
]


def _route_for(text: str) -> str:
    low = text.lower()
    for keys, name in _ROUTE_HINTS:
        if any(k in low for k in keys):
            return name
    return "AI"


class CommandView(ctk.CTkFrame):
    """The command center home screen."""

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
        self._operations: list[dict] = []

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=3, uniform="cc")
        self.grid_columnconfigure(1, weight=2, uniform="cc")

        self._build_left()
        self._build_right()
        self._poll()

    # ── Left column: command + operations ──────────────────────────────────────

    def _build_left(self) -> None:
        col = ctk.CTkFrame(self, fg_color="transparent")
        col.grid(row=0, column=0, sticky="nsew", padx=(T.PAD_PAGE, T.SPACE_MD),
                 pady=T.PAD_PAGE)
        col.grid_columnconfigure(0, weight=1)
        col.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            col, text="WHAT DO YOU WANT TO ACCOMPLISH?",
            font=(T.FONT_FAMILY, 22, "bold"), text_color=T.TEXT_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        # Command box.
        box = ctk.CTkFrame(col, fg_color=T.BG_SURFACE, corner_radius=T.RADIUS_PANEL,
                           border_color=T.BORDER_ACCENT, border_width=1)
        box.grid(row=1, column=0, sticky="ew", pady=(T.SPACE_MD, T.SPACE_LG))
        box.grid_columnconfigure(0, weight=1)

        self._input = ctk.CTkTextbox(
            box, height=96, fg_color="transparent", border_width=0,
            text_color=T.TEXT_PRIMARY, font=T.FONT_BODY, wrap="word",
        )
        self._input.grid(row=0, column=0, sticky="ew", padx=T.SPACE_MD,
                         pady=(T.SPACE_MD, 0))
        self._input.insert("1.0", _PLACEHOLDER)
        self._placeholder_on = True
        self._input.bind("<FocusIn>", self._clear_ph)
        self._input.bind("<FocusOut>", self._restore_ph)
        self._input.bind("<Control-Return>", lambda _e: self._execute())

        bar = ctk.CTkFrame(box, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=T.SPACE_MD,
                 pady=(T.SPACE_SM, T.SPACE_MD))
        bar.grid_columnconfigure(0, weight=1)

        chips = ctk.CTkFrame(bar, fg_color="transparent")
        chips.grid(row=0, column=0, sticky="w")
        for label, key in (("+ Attach", None), ("Capabilities", "mcp"),
                           ("Target system", "systems"), ("Execution mode", None)):
            ctk.CTkButton(
                chips, text=label, height=26, **T.btn_ghost_kwargs(),
                command=(lambda k=key: self._on_navigate and k and self._on_navigate(k)),
            ).pack(side="left", padx=(0, T.SPACE_SM))

        self._exec_btn = ctk.CTkButton(
            bar, text="EXECUTE  →", width=130, height=36,
            **T.btn_primary_kwargs(), command=self._execute,
        )
        self._exec_btn.grid(row=0, column=1, sticky="e")

        # Active operations.
        section_label(col, "Active Operations").grid(row=2, column=0, sticky="nw",
                                                      pady=(0, T.SPACE_SM))
        self._ops_panel = ctk.CTkScrollableFrame(
            col, fg_color=T.BG_SURFACE, corner_radius=T.RADIUS_PANEL,
            scrollbar_button_color=T.BG_RAISED,
            scrollbar_button_hover_color=T.PURPLE,
        )
        self._ops_panel.grid(row=3, column=0, sticky="nsew")
        col.grid_rowconfigure(3, weight=1)
        self._render_ops()

    # ── Right column: core + instruments ────────────────────────────────────────

    def _build_right(self) -> None:
        col = ctk.CTkFrame(self, fg_color="transparent")
        col.grid(row=0, column=1, sticky="nsew", padx=(T.SPACE_MD, T.PAD_PAGE),
                 pady=T.PAD_PAGE)
        col.grid_columnconfigure(0, weight=1)
        col.grid_rowconfigure(0, weight=1)

        core_panel = Panel(col, title="Archon Core")
        core_panel.grid(row=0, column=0, sticky="nsew", pady=(0, T.SPACE_MD))
        self._core = ArchonCore(core_panel.body, size=300, bg=T.BG_SURFACE)
        self._core.pack(fill="both", expand=True)
        self._core.start()

        instr = Panel(col, title="System Status")
        instr.grid(row=1, column=0, sticky="ew")
        instr.body.grid_columnconfigure(0, weight=1)
        self._kv: dict[str, KeyValue] = {}
        for key, label in (("core", "Core"), ("cpu", "CPU"), ("ram", "RAM"),
                           ("disk", "Disk"), ("caps", "Capabilities"),
                           ("ops", "Operations")):
            kv = KeyValue(instr.body, label, "—")
            kv.pack(fill="x", pady=2)
            self._kv[key] = kv
        self._kv["core"].set("● ONLINE", T.SUCCESS)
        self._refresh_caps()
        self._tick_metrics()

    # ── Placeholder handling ────────────────────────────────────────────────────

    def _clear_ph(self, _e: tk.Event) -> None:  # type: ignore[type-arg]
        if self._placeholder_on:
            self._input.delete("1.0", "end")
            self._input.configure(text_color=T.TEXT_PRIMARY)
            self._placeholder_on = False

    def _restore_ph(self, _e: tk.Event) -> None:  # type: ignore[type-arg]
        if not self._input.get("1.0", "end").strip():
            self._input.insert("1.0", _PLACEHOLDER)
            self._input.configure(text_color=T.TEXT_MUTED)
            self._placeholder_on = True

    # ── Execute ───────────────────────────────────────────────────────────────

    def submit_command(self, text: str) -> None:
        """Public hook so the top bar / palette can run a command here."""
        self._clear_ph(None)  # type: ignore[arg-type]
        self._input.delete("1.0", "end")
        self._input.insert("1.0", text)
        self._placeholder_on = False
        self._execute()

    def _execute(self) -> None:
        if self._placeholder_on:
            return
        text = self._input.get("1.0", "end").strip()
        if not text:
            return
        self._input.delete("1.0", "end")
        self._restore_ph(None)  # type: ignore[arg-type]

        op = {
            "title": text[:60] + ("…" if len(text) > 60 else ""),
            "command": text, "state": "running",
            "route": _route_for(text),
            "started": datetime.now(), "detail": "Dispatching…",
        }
        self._operations.insert(0, op)
        self._core.set_active(op["route"])
        self._render_ops()

        threading.Thread(target=self._worker, args=(op,), daemon=True).start()

    def _worker(self, op: dict) -> None:
        try:
            if self._engine and hasattr(self._engine, "chat"):
                result = self._engine.chat(op["command"])
            else:
                result = {"success": False, "reply": "Engine unavailable."}
            self._result_queue.put((op, result))
        except Exception as exc:  # pragma: no cover - defensive
            self._result_queue.put((op, {"success": False, "reply": str(exc)}))

    def _poll(self) -> None:
        try:
            while True:
                op, result = self._result_queue.get_nowait()
                self._finish(op, result)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(120, self._poll)

    def _finish(self, op: dict, result: dict) -> None:
        ok = bool(result.get("success", True))
        op["state"] = "done" if ok else "failed"
        if result.get("kind") == "conversation":
            op["detail"] = (result.get("reply") or "")[:120]
        else:
            op["detail"] = (result.get("result") or result.get("reply")
                            or result.get("error") or "Complete")[:120]
        if not any(o["state"] == "running" for o in self._operations):
            self._core.clear_active()
        self._render_ops()

    # ── Rendering ───────────────────────────────────────────────────────────────

    def _render_ops(self) -> None:
        for child in self._ops_panel.winfo_children():
            child.destroy()
        active = sum(1 for o in self._operations if o["state"] == "running")
        if "ops" in getattr(self, "_kv", {}):
            self._kv["ops"].set(str(active), T.TEXT_ACCENT if active else T.TEXT_MUTED)

        if not self._operations:
            ctk.CTkLabel(
                self._ops_panel,
                text="Archon is standing by.\nDescribe an operation above to begin.",
                font=T.FONT_BODY, text_color=T.TEXT_MUTED, justify="center",
            ).pack(expand=True, pady=T.SPACE_2XL)
            return
        for op in self._operations[:12]:
            _OperationRow(self._ops_panel, op).pack(fill="x", pady=(0, T.SPACE_SM))

    # ── Live data ─────────────────────────────────────────────────────────────

    def _refresh_caps(self) -> None:
        n = 0
        try:
            if self._engine and hasattr(self._engine, "describe_capabilities"):
                n = len(self._engine.describe_capabilities())
        except Exception:
            n = 0
        if "caps" in self._kv:
            self._kv["caps"].set(str(n) if n else "—")

    def _tick_metrics(self) -> None:
        if not self.winfo_exists():
            return
        try:
            import psutil

            self._kv["cpu"].set(f"{psutil.cpu_percent():.0f}%")
            self._kv["ram"].set(f"{psutil.virtual_memory().percent:.0f}%")
            self._kv["disk"].set(f"{psutil.disk_usage('/').percent:.0f}%")
        except Exception:
            pass
        self.after(2000, self._tick_metrics)


class _OperationRow(ctk.CTkFrame):
    """A single active/finished operation card."""

    def __init__(self, parent: tk.Widget, op: dict, **kwargs: object) -> None:
        super().__init__(
            parent, fg_color=T.BG_RAISED, corner_radius=T.RADIUS_SM,
            border_color=T.BORDER_SUBTLE, border_width=1, **kwargs,  # type: ignore[arg-type]
        )
        state = op["state"]
        color = T.status_color(state)
        glyph = "◉" if state == "running" else "✓" if state == "done" else "✕"

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=T.SPACE_MD, pady=(T.SPACE_SM, 2))
        ctk.CTkLabel(head, text=glyph, font=(T.FONT_FAMILY, 12, "bold"),
                     text_color=color).pack(side="left", padx=(0, T.SPACE_SM))
        ctk.CTkLabel(head, text=op["title"], font=T.FONT_BODY_BOLD,
                     text_color=T.TEXT_PRIMARY, anchor="w").pack(side="left",
                                                                 fill="x", expand=True)
        ctk.CTkLabel(head, text=op["route"], font=T.FONT_CODE_SMALL,
                     text_color=T.TEXT_DIM).pack(side="right")

        ctk.CTkLabel(self, text=op.get("detail", ""), font=T.FONT_SMALL,
                     text_color=T.TEXT_SECONDARY, anchor="w",
                     wraplength=360, justify="left").pack(
            fill="x", padx=T.SPACE_MD, pady=(0, T.SPACE_SM))


_PLACEHOLDER = (
    "Build me a personalized Arch Linux environment for cybersecurity and AI "
    "development…"
)
