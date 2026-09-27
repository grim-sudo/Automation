"""Real system/hardware/intelligence facts for the TUI sidebar.

Everything here reports *measured* values only. When a value cannot be obtained
(no GPU, a probe that failed, a backend that does not expose the metric) the
field is returned as ``None`` and the sidebar shows ``N/A`` rather than a
fabricated number.

This module is pure data collection — it holds no widgets and no engine
business logic, so it is cheap to unit-test and safe to call from a worker
thread on an interval.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

try:
    import psutil

    _HAVE_PSUTIL = True
except ImportError:  # pragma: no cover - psutil is a declared dependency
    _HAVE_PSUTIL = False


@dataclass
class GpuInfo:
    name: str | None = None
    util_percent: float | None = None
    vram_used_mb: float | None = None
    vram_total_mb: float | None = None


@dataclass
class SystemSnapshot:
    """One point-in-time reading of the host and model backend."""

    os_name: str | None = None
    kernel: str | None = None
    shell: str | None = None
    desktop: str | None = None
    uptime: str | None = None

    cpu_percent: float | None = None
    ram_used_gb: float | None = None
    ram_total_gb: float | None = None
    disk_used_gb: float | None = None
    disk_total_gb: float | None = None
    gpu: GpuInfo = field(default_factory=GpuInfo)

    accelerator: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class SystemProbe:
    """Collects host + accelerator metrics. Detection results are cached."""

    def __init__(self) -> None:
        self._nvidia_smi = shutil.which("nvidia-smi")
        self._static: dict[str, str | None] | None = None

    # ── static (rarely-changing) facts ───────────────────────────────────────

    def static(self) -> dict[str, str | None]:
        """OS/kernel/shell/desktop — read once and cached."""
        if self._static is None:
            self._static = {
                "os_name": _distro_name(),
                "kernel": platform.release() or None,
                "shell": _shell_name(),
                "desktop": _desktop_name(),
            }
        return self._static

    # ── live snapshot ─────────────────────────────────────────────────────────

    def snapshot(self) -> SystemSnapshot:
        """Return a fresh reading. Safe to call on an interval from a worker."""
        s = self.static()
        snap = SystemSnapshot(
            os_name=s["os_name"],
            kernel=s["kernel"],
            shell=s["shell"],
            desktop=s["desktop"],
            uptime=_uptime(),
        )
        if _HAVE_PSUTIL:
            try:
                snap.cpu_percent = float(psutil.cpu_percent(interval=None))
            except Exception:
                snap.cpu_percent = None
            try:
                vm = psutil.virtual_memory()
                snap.ram_used_gb = (vm.total - vm.available) / 1e9
                snap.ram_total_gb = vm.total / 1e9
            except Exception:
                pass
            try:
                du = psutil.disk_usage(os.path.expanduser("~"))
                snap.disk_used_gb = du.used / 1e9
                snap.disk_total_gb = du.total / 1e9
            except Exception:
                pass
        snap.gpu = self._gpu()
        snap.accelerator = "CUDA" if snap.gpu.name else "CPU"
        return snap

    def _gpu(self) -> GpuInfo:
        if not self._nvidia_smi:
            return GpuInfo()
        try:
            out = subprocess.run(
                [
                    self._nvidia_smi,
                    "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return GpuInfo()
        line = (out.stdout or "").strip().splitlines()
        if not line:
            return GpuInfo()
        parts = [p.strip() for p in line[0].split(",")]
        if len(parts) < 4:
            return GpuInfo(name=parts[0] if parts else None)
        return GpuInfo(
            name=parts[0] or None,
            util_percent=_to_float(parts[1]),
            vram_used_mb=_to_float(parts[2]),
            vram_total_mb=_to_float(parts[3]),
        )


# ── helpers ────────────────────────────────────────────────────────────────


def _to_float(text: str) -> float | None:
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _distro_name() -> str | None:
    if platform.system() == "Linux":
        try:
            with open("/etc/os-release", encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip().strip('"')
        except OSError:
            pass
    return platform.system() or None


def _shell_name() -> str | None:
    shell = os.environ.get("SHELL")
    return os.path.basename(shell) if shell else None


def _desktop_name() -> str | None:
    for key in ("XDG_CURRENT_DESKTOP", "DESKTOP_SESSION", "XDG_SESSION_DESKTOP"):
        val = os.environ.get(key)
        if val:
            return val
    if os.environ.get("WAYLAND_DISPLAY"):
        return "Wayland"
    if os.environ.get("DISPLAY"):
        return "X11"
    return None


def _uptime() -> str | None:
    """Human-readable uptime from ``psutil`` boot time, best effort."""
    if not _HAVE_PSUTIL:
        return None
    try:
        import time

        seconds = int(time.time() - psutil.boot_time())
    except Exception:
        return None
    if seconds < 0:
        return None
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
