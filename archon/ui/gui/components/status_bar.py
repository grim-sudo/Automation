"""
StatusBar — bottom system telemetry strip.

A compact operations readout: Archon core status on the left, live host metrics
(CPU / RAM / disk, and network counters) on the right. Metrics come from
``psutil`` (already a project dependency) and refresh on the Tk ``after()`` loop
so the GUI thread never blocks.
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from .. import theme as T


class StatusBar(ctk.CTkFrame):
    """Persistent bottom telemetry bar."""

    def __init__(self, parent: tk.Widget, **kwargs: object) -> None:
        super().__init__(
            parent,
            fg_color=T.BG_SURFACE,
            corner_radius=0,
            height=T.STATUSBAR_HEIGHT,
            **kwargs,  # type: ignore[arg-type]
        )
        self.grid_propagate(False)
        self._last_net: tuple[float, float] | None = None
        self._metric_labels: dict[str, ctk.CTkLabel] = {}
        self._build()
        self._tick()

    def _build(self) -> None:
        # Left: core status.
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", padx=T.SPACE_MD)

        self._dot = tk.Canvas(left, width=8, height=8, bg=T.BG_SURFACE, highlightthickness=0)
        self._dot.pack(side="left", padx=(0, 6), pady=2)
        self._dot_id = self._dot.create_oval(0, 0, 8, 8, fill=T.SUCCESS, outline="")

        ctk.CTkLabel(
            left, text="ARCHON CORE", font=(T.FONT_FAMILY, 9, "bold"),
            text_color=T.TEXT_SECONDARY,
        ).pack(side="left")

        ctk.CTkLabel(left, text="│", font=T.FONT_MICRO,
                     text_color=T.TEXT_DIM).pack(side="left", padx=T.SPACE_SM)
        self._ops_label = ctk.CTkLabel(
            left, text="0 OPERATIONS", font=(T.FONT_FAMILY, 9, "bold"),
            text_color=T.TEXT_MUTED,
        )
        self._ops_label.pack(side="left")

        # Right: metrics (packed right-to-left → visual order CPU RAM DISK NET).
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="right", padx=T.SPACE_MD)
        for key, label in (("net", "NET"), ("disk", "DISK"), ("ram", "RAM"), ("cpu", "CPU")):
            cell = ctk.CTkFrame(right, fg_color="transparent")
            cell.pack(side="right", padx=(0, T.SPACE_MD))
            ctk.CTkLabel(
                cell, text=label, font=(T.FONT_FAMILY, 9, "bold"), text_color=T.TEXT_MUTED
            ).pack(side="left", padx=(0, 4))
            val = ctk.CTkLabel(
                cell, text="—", font=T.FONT_CODE_SMALL, text_color=T.TEXT_ACCENT
            )
            val.pack(side="left")
            self._metric_labels[key] = val

    def set_core_status(self, ok: bool) -> None:
        try:
            self._dot.itemconfig(self._dot_id, fill=T.SUCCESS if ok else T.ERROR)
        except tk.TclError:
            pass

    def set_operations(self, count: int) -> None:
        """Update the active-operations counter in the strip."""
        try:
            self._ops_label.configure(
                text=f"{count} OPERATION{'S' if count != 1 else ''}",
                text_color=T.TEXT_ACCENT if count else T.TEXT_MUTED,
            )
        except tk.TclError:
            pass

    def _tick(self) -> None:
        if not self.winfo_exists():
            return
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=None)
            self._set("cpu", f"{cpu:>4.0f}%", cpu)

            vm = psutil.virtual_memory()
            self._set("ram", f"{vm.percent:>4.0f}%", vm.percent)

            disk = psutil.disk_usage("/").percent
            self._set("disk", f"{disk:>4.0f}%", disk)

            io = psutil.net_io_counters()
            now = (io.bytes_sent, io.bytes_recv)
            if self._last_net is not None:
                # 1.5s cadence → per-second rate over the interval.
                dtx = (now[0] - self._last_net[0]) / 1.5
                drx = (now[1] - self._last_net[1]) / 1.5
                self._metric_labels["net"].configure(
                    text=f"↑{_rate(dtx)} ↓{_rate(drx)}", text_color=T.TEXT_ACCENT
                )
            self._last_net = now
        except Exception:
            pass
        self.after(1500, self._tick)

    def _set(self, key: str, text: str, pct: float) -> None:
        color = T.ERROR if pct >= 90 else T.WARNING if pct >= 70 else T.TEXT_ACCENT
        self._metric_labels[key].configure(text=text, text_color=color)


def _rate(bps: float) -> str:
    """Human-readable per-second byte rate."""
    if bps < 1024:
        return f"{bps:.0f}B"
    if bps < 1024 * 1024:
        return f"{bps / 1024:.0f}K"
    return f"{bps / 1024 / 1024:.1f}M"
