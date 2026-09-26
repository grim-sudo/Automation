"""
Systems view — the machines Archon can see and control.

Spec §15: a topology (Archon → machines) with a per-machine inspector. Only the
local host has a real backend today (psutil); it renders as a connected node
whose inspector shows live hardware. Remote machines are shown as an honest
"connect a system" affordance rather than fabricated nodes.
"""

from __future__ import annotations

import platform
import socket
import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from .. import theme as T
from ..components.panel import KeyValue, Panel, hairline


def _fmt_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.0f} PB"


class SystemsView(ctk.CTkFrame):
    """Local + (future) remote machine topology with an inspector."""

    def __init__(
        self,
        parent: tk.Widget,
        engine: object = None,
        on_navigate: Callable[[str], None] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, fg_color=T.BG_DEEP, **kwargs)  # type: ignore[arg-type]
        self._engine = engine
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=3, uniform="sv")
        self.grid_columnconfigure(1, weight=2, uniform="sv")
        self._build()
        self._tick()

    def _build(self) -> None:
        left = Panel(self, title="Topology")
        left.grid(row=0, column=0, sticky="nsew", padx=(T.PAD_PAGE, T.SPACE_MD),
                  pady=T.PAD_PAGE)
        self._canvas = tk.Canvas(left.body, bg=T.BG_SURFACE, highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)
        self._canvas.bind("<Configure>", lambda _e: self._draw_topology())

        insp = Panel(self, title="System", eyebrow=socket.gethostname())
        insp.grid(row=0, column=1, sticky="nsew", padx=(T.SPACE_MD, T.PAD_PAGE),
                  pady=T.PAD_PAGE)
        insp.body.grid_columnconfigure(0, weight=1)

        uname = platform.uname()
        ctk.CTkLabel(insp.body, text=f"{uname.system} {uname.release}".upper(),
                     font=T.FONT_HEADING, text_color=T.TEXT_PRIMARY,
                     anchor="w").pack(fill="x")
        ctk.CTkLabel(insp.body, text="● Connected", font=T.FONT_SMALL,
                     text_color=T.SUCCESS, anchor="w").pack(fill="x", pady=(0, T.SPACE_MD))
        hairline(insp.body).pack(fill="x", pady=(0, T.SPACE_MD))

        self._kv: dict[str, KeyValue] = {}
        rows = [
            ("host", "Host"), ("platform", "Platform"), ("arch", "Arch"),
            ("cpu", "CPU"), ("cores", "Cores"), ("ram", "Memory"),
            ("disk", "Storage"), ("ip", "Address"), ("agent", "Archon Agent"),
        ]
        for key, label in rows:
            kv = KeyValue(insp.body, label, "—")
            kv.pack(fill="x", pady=2)
            self._kv[key] = kv

        self._populate_static()

    def _populate_static(self) -> None:
        uname = platform.uname()
        self._kv["host"].set(uname.node or socket.gethostname())
        self._kv["platform"].set(f"{uname.system} {uname.release}")
        self._kv["arch"].set(uname.machine)
        self._kv["cpu"].set((uname.processor or "unknown")[:22])
        try:
            import psutil

            self._kv["cores"].set(
                f"{psutil.cpu_count(logical=False)}c / {psutil.cpu_count()}t")
            self._kv["ram"].set(_fmt_bytes(psutil.virtual_memory().total))
            self._kv["disk"].set(_fmt_bytes(psutil.disk_usage("/").total))
        except Exception:
            pass
        try:
            self._kv["ip"].set(socket.gethostbyname(socket.gethostname()))
        except Exception:
            self._kv["ip"].set("—")
        self._kv["agent"].set("● Running", T.SUCCESS)

    def _tick(self) -> None:
        if not self.winfo_exists():
            return
        try:
            import psutil

            vm = psutil.virtual_memory()
            self._kv["ram"].set(
                f"{_fmt_bytes(vm.used)} / {_fmt_bytes(vm.total)}",
                T.WARNING if vm.percent >= 80 else T.TEXT_PRIMARY,
            )
            du = psutil.disk_usage("/")
            self._kv["disk"].set(
                f"{_fmt_bytes(du.used)} / {_fmt_bytes(du.total)}",
                T.WARNING if du.percent >= 85 else T.TEXT_PRIMARY,
            )
        except Exception:
            pass
        self.after(3000, self._tick)

    def _draw_topology(self) -> None:
        c = self._canvas
        c.delete("all")
        w = c.winfo_width() or 400
        h = c.winfo_height() or 400
        cx = w / 2
        top_y = h * 0.22
        node_y = h * 0.62

        # Archon core at top.
        r = 26
        c.create_oval(cx - r * 1.7, top_y - r * 1.7, cx + r * 1.7, top_y + r * 1.7,
                      fill=T.BG_RAISED, outline="")
        c.create_oval(cx - r, top_y - r, cx + r, top_y + r,
                      fill=T.BG_SURFACE, outline=T.GOLD, width=2)
        c.create_text(cx, top_y, text="ARCHON", fill=T.TEXT_ACCENT,
                      font=(T.FONT_FAMILY, 9, "bold"))

        # This machine node (connected).
        c.create_line(cx, top_y + r, cx, node_y - 22, fill=T.GOLD, width=2)
        nr = 22
        c.create_oval(cx - nr, node_y - nr, cx + nr, node_y + nr,
                      fill=T.BG_SURFACE, outline=T.SUCCESS, width=2)
        c.create_text(cx, node_y, text="THIS\nMACHINE", fill=T.TEXT_PRIMARY,
                      font=(T.FONT_FAMILY, 8, "bold"), justify="center")
        c.create_text(cx, node_y + nr + 14, text=platform.system().upper(),
                      fill=T.TEXT_MUTED, font=(T.FONT_FAMILY, 8, "bold"))

        # Placeholder future systems (dim, dashed).
        for dx, label in ((-w * 0.28, "REMOTE"), (w * 0.28, "CLOUD")):
            fx = cx + dx
            c.create_line(cx, node_y, fx, node_y + h * 0.16,
                          fill=T.BORDER_STRONG, width=1, dash=(2, 4))
            c.create_oval(fx - 16, node_y + h * 0.16 - 16, fx + 16, node_y + h * 0.16 + 16,
                          fill=T.BG_SURFACE, outline=T.BORDER_STRONG, width=1, dash=(2, 4))
            c.create_text(fx, node_y + h * 0.16, text=label, fill=T.TEXT_DIM,
                          font=(T.FONT_FAMILY, 7, "bold"))
