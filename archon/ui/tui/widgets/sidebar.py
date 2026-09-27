"""Live system / hardware / intelligence / Archon inspector sidebar.

Renders only measured values. Anything unavailable shows ``N/A`` rather than a
fabricated figure. The app pushes fresh data in via :meth:`update_state`; the
sidebar owns no polling and no engine access of its own.
"""

from __future__ import annotations

from typing import Any

from rich.console import Group
from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from .glyphs import BAR_EMPTY, BAR_FULL


def _bar(fraction: float | None, width: int = 12) -> Text:
    """A restrained gold fill bar; empty/grey when the value is unknown."""
    if fraction is None:
        return Text(BAR_EMPTY * width, style="#4b4f57")
    fraction = max(0.0, min(1.0, fraction))
    filled = int(round(fraction * width))
    bar = Text()
    bar.append(BAR_FULL * filled, style="#d9a441")
    bar.append(BAR_EMPTY * (width - filled), style="#4b4f57")
    return bar


def _na(value: Any) -> str:
    return "N/A" if value is None else str(value)


class Sidebar(Static):
    """Four labelled sections; re-rendered whenever new data arrives.

    A single :class:`Static` (rather than a container) so it renders through
    ``render()`` and never needs child-widget bookkeeping. The app wraps it in a
    scroll container for independent scrolling on short terminals.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._snapshot: Any = None
        self._intel: dict[str, Any] = {}
        self._archon: dict[str, Any] = {}

    def update_state(
        self,
        *,
        snapshot: Any = None,
        intel: dict[str, Any] | None = None,
        archon: dict[str, Any] | None = None,
    ) -> None:
        if snapshot is not None:
            self._snapshot = snapshot
        if intel is not None:
            self._intel = intel
        if archon is not None:
            self._archon = archon
        self.refresh()

    # ── rendering ─────────────────────────────────────────────────────────────

    def _section(self, title: str) -> Text:
        return Text(title, style="#8a6d3b bold")

    def _kv(self) -> Table:
        grid = Table.grid(padding=(0, 1))
        grid.add_column(justify="left", style="#8a8f98", no_wrap=True, width=8)
        grid.add_column(justify="left", style="#d7dae0", overflow="fold")
        return grid

    def render(self) -> Group:
        snap = self._snapshot
        blocks: list[Any] = []

        # SYSTEM
        blocks.append(self._section("SYSTEM"))
        sys_t = self._kv()
        sys_t.add_row("OS", _na(getattr(snap, "os_name", None)))
        sys_t.add_row("Kernel", _na(getattr(snap, "kernel", None)))
        sys_t.add_row("Shell", _na(getattr(snap, "shell", None)))
        sys_t.add_row("Desktop", _na(getattr(snap, "desktop", None)))
        sys_t.add_row("Uptime", _na(getattr(snap, "uptime", None)))
        blocks.append(sys_t)
        blocks.append(Text())

        # HARDWARE
        blocks.append(self._section("HARDWARE"))
        blocks.append(self._hardware(snap))
        blocks.append(Text())

        # INTELLIGENCE
        blocks.append(self._section("INTELLIGENCE"))
        blocks.append(self._intelligence(snap))
        blocks.append(Text())

        # ARCHON
        blocks.append(self._section("ARCHON"))
        arch_t = self._kv()
        arch_t.add_row("Plugins", _na(self._archon.get("plugins")))
        arch_t.add_row("Caps", _na(self._archon.get("capabilities")))
        arch_t.add_row("State", _na(self._archon.get("state")))
        blocks.append(arch_t)

        return Group(*blocks)

    def _hardware(self, snap: Any) -> Table:
        grid = Table.grid(padding=(0, 1))
        grid.add_column(justify="left", style="#8a8f98", no_wrap=True, width=6)
        grid.add_column(justify="left", no_wrap=True)
        grid.add_column(justify="right", style="#d7dae0", no_wrap=True)

        cpu = getattr(snap, "cpu_percent", None)
        grid.add_row(
            "CPU",
            _bar(None if cpu is None else cpu / 100.0),
            "N/A" if cpu is None else f"{cpu:.0f}%",
        )
        gpu = getattr(snap, "gpu", None)
        gutil = getattr(gpu, "util_percent", None) if gpu else None
        grid.add_row(
            "GPU",
            _bar(None if gutil is None else gutil / 100.0),
            "N/A" if gutil is None else f"{gutil:.0f}%",
        )
        vu = getattr(gpu, "vram_used_mb", None) if gpu else None
        vt = getattr(gpu, "vram_total_mb", None) if gpu else None
        if vu is not None and vt:
            grid.add_row("VRAM", _bar(vu / vt), f"{vu / 1024:.1f}/{vt / 1024:.0f}G")
        else:
            grid.add_row("VRAM", _bar(None), "N/A")
        ru = getattr(snap, "ram_used_gb", None)
        rt = getattr(snap, "ram_total_gb", None)
        if ru is not None and rt:
            grid.add_row("RAM", _bar(ru / rt), f"{ru:.1f}/{rt:.0f}G")
        else:
            grid.add_row("RAM", _bar(None), "N/A")
        du = getattr(snap, "disk_used_gb", None)
        dt = getattr(snap, "disk_total_gb", None)
        if du is not None and dt:
            grid.add_row("Disk", _bar(du / dt), f"{du:.0f}/{dt:.0f}G")
        else:
            grid.add_row("Disk", _bar(None), "N/A")
        return grid

    def _intelligence(self, snap: Any) -> Group:
        blocks: list[Any] = []
        kv = self._kv()
        kv.add_row("Model", _na(self._intel.get("model")))
        kv.add_row("Backend", _na(self._intel.get("backend")))
        kv.add_row("Accel", _na(getattr(snap, "accelerator", None)))
        tps = self._intel.get("tokens_per_sec")
        kv.add_row("Speed", "N/A" if tps is None else f"{tps:.1f} tok/s")
        blocks.append(kv)

        used = self._intel.get("context_used")
        window = self._intel.get("context_window")
        if used is not None and window:
            frac = used / window if window else None
            ctx = Table.grid(padding=(0, 1))
            ctx.add_column(justify="left", style="#8a8f98", no_wrap=True, width=8)
            ctx.add_column(justify="left")
            label = f"{used / 1000:.1f}K/{window / 1000:.0f}K"
            ctx.add_row("Context", Text(label, style="#d7dae0"))
            ctx.add_row("", _bar(frac, width=14))
            blocks.append(ctx)
        return Group(*blocks)
