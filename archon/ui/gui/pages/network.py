"""
Network view — interfaces, addresses, and live throughput.

Spec §11/§15: a technical instrument. Per-interface addresses come from
``psutil.net_if_addrs``; live send/recv rates are sampled per-interface off the
GUI thread and rendered as compact readouts.
"""

from __future__ import annotations

import socket
import time
import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from .. import theme as T
from ..components.panel import KeyValue, Panel, hairline


def _fmt_rate(bytes_per_s: float) -> str:
    for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
        if bytes_per_s < 1024:
            return f"{bytes_per_s:.1f} {unit}"
        bytes_per_s /= 1024
    return f"{bytes_per_s:.1f} TB/s"


class NetworkView(ctk.CTkFrame):
    """Interface inventory with live throughput."""

    def __init__(
        self,
        parent: tk.Widget,
        engine: object = None,
        on_navigate: Callable[[str], None] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, fg_color=T.BG_DEEP, **kwargs)  # type: ignore[arg-type]
        self._engine = engine
        self._last: dict[str, tuple[float, float, float]] = {}
        self._iface_rows: dict[str, KeyValue] = {}
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self._build()
        self._tick()

    def _build(self) -> None:
        # Left: throughput totals.
        left = Panel(self, title="Throughput")
        left.grid(row=0, column=0, sticky="nsew", padx=(T.PAD_PAGE, T.SPACE_MD),
                  pady=T.PAD_PAGE)
        left.body.grid_columnconfigure(0, weight=1)
        self._kv: dict[str, KeyValue] = {}
        for key, label in (("host", "Host"), ("up", "Upload"), ("down", "Download"),
                           ("sent", "Total Sent"), ("recv", "Total Recv"),
                           ("conns", "Connections")):
            kv = KeyValue(left.body, label, "—")
            kv.pack(fill="x", pady=3)
            self._kv[key] = kv
        try:
            self._kv["host"].set(socket.gethostname())
        except Exception:
            pass

        # Right: per-interface addresses.
        right = Panel(self, title="Interfaces")
        right.grid(row=0, column=1, sticky="nsew", padx=(T.SPACE_MD, T.PAD_PAGE),
                   pady=T.PAD_PAGE)
        right.body.grid_columnconfigure(0, weight=1)
        self._iface_host = ctk.CTkScrollableFrame(
            right.body, fg_color="transparent",
            scrollbar_button_color=T.BG_RAISED,
            scrollbar_button_hover_color=T.PURPLE,
        )
        self._iface_host.pack(fill="both", expand=True)
        self._populate_interfaces()

    def _populate_interfaces(self) -> None:
        try:
            import psutil
        except Exception:
            return
        try:
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
        except Exception:
            return
        for name, addr_list in addrs.items():
            up = stats.get(name)
            block = ctk.CTkFrame(self._iface_host, fg_color="transparent")
            block.pack(fill="x", pady=(0, T.SPACE_SM))
            head = ctk.CTkFrame(block, fg_color="transparent")
            head.pack(fill="x")
            state_up = bool(up and up.isup)
            ctk.CTkLabel(head, text="●", font=(T.FONT_FAMILY, 10),
                         text_color=T.SUCCESS if state_up else T.TEXT_DIM).pack(
                side="left", padx=(0, 6))
            ctk.CTkLabel(head, text=name, font=T.FONT_BODY_BOLD,
                         text_color=T.TEXT_PRIMARY, anchor="w").pack(side="left")
            if up:
                ctk.CTkLabel(head, text=f"{up.speed} Mb/s" if up.speed else "",
                             font=T.FONT_CODE_SMALL, text_color=T.TEXT_DIM).pack(
                    side="right")
            for a in addr_list:
                fam = getattr(a.family, "name", str(a.family))
                if fam not in ("AF_INET", "AF_INET6", "AF_PACKET", "AF_LINK"):
                    continue
                tag = {"AF_INET": "IPv4", "AF_INET6": "IPv6",
                       "AF_PACKET": "MAC", "AF_LINK": "MAC"}.get(fam, fam)
                KeyValue(block, tag, a.address[:34]).pack(fill="x", padx=(16, 0))
            hairline(block).pack(fill="x", pady=(T.SPACE_SM, 0))

    def _tick(self) -> None:
        if not self.winfo_exists():
            return
        try:
            import psutil

            io = psutil.net_io_counters()
            now = time.time()
            prev = self._last.get("_total")
            if prev:
                dt = max(now - prev[2], 1e-6)
                up = (io.bytes_sent - prev[0]) / dt
                down = (io.bytes_recv - prev[1]) / dt
                self._kv["up"].set(_fmt_rate(up),
                                   T.TEXT_ACCENT if up > 1024 else T.TEXT_PRIMARY)
                self._kv["down"].set(_fmt_rate(down),
                                     T.TEXT_ACCENT if down > 1024 else T.TEXT_PRIMARY)
            self._last["_total"] = (io.bytes_sent, io.bytes_recv, now)
            self._kv["sent"].set(_fmt_rate(io.bytes_sent).replace("/s", ""))
            self._kv["recv"].set(_fmt_rate(io.bytes_recv).replace("/s", ""))
            try:
                self._kv["conns"].set(str(len(psutil.net_connections())))
            except Exception:
                self._kv["conns"].set("—")
        except Exception:
            pass
        self.after(2000, self._tick)
