"""
Programmatic Linux kernel .config management using kconfiglib.

All blocking build operations run in asyncio.to_thread().
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any

from loguru import logger
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

__all__ = [
    "load_default_config",
    "apply_options",
    "write_config",
    "build_kernel",
    "install_modules",
]


def _require_kconfiglib() -> Any:
    try:
        import kconfiglib  # type: ignore[import]
        return kconfiglib
    except ImportError as exc:
        raise ImportError(
            "kconfiglib is required for kernel configuration. "
            "Install with: pip install kconfiglib"
        ) from exc


def load_default_config(kernel_dir: Path, arch: str = "x86_64") -> Any:
    """Load the kernel defconfig for *arch*.

    Args:
        kernel_dir: Extracted kernel source root.
        arch:       Target architecture (default ``x86_64``).

    Returns:
        kconfiglib.Kconfig instance loaded with the defconfig.

    Raises:
        ImportError: If kconfiglib is not installed.
        RuntimeError: If make defconfig fails.
    """
    kc = _require_kconfiglib()
    kernel_dir = kernel_dir.resolve()

    env = dict(os.environ)
    env["ARCH"] = arch

    # Generate .config via make defconfig
    result = subprocess.run(
        ["make", f"ARCH={arch}", "defconfig"],
        cwd=str(kernel_dir),
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(f"make defconfig failed:\n{result.stderr}")

    kconfig_path = kernel_dir / "Kconfig"
    kconfig = kc.Kconfig(str(kconfig_path))
    kconfig.load_config(str(kernel_dir / ".config"))
    logger.info("Kernel defconfig loaded for arch={}", arch)
    return kconfig


def apply_options(kconfig: Any, options: dict[str, str]) -> None:
    """Set kernel config options programmatically.

    Args:
        kconfig: kconfiglib.Kconfig instance.
        options: Mapping of option names (with or without ``CONFIG_`` prefix)
                 to values (``"y"``, ``"n"``, ``"m"``, or string value).

    Raises:
        KeyError: If an option is not found in the Kconfig tree.
    """
    kc = _require_kconfiglib()

    for name, value in options.items():
        # Strip optional CONFIG_ prefix
        sym_name = name.removeprefix("CONFIG_")
        sym = kconfig.syms.get(sym_name)
        if sym is None:
            logger.warning("Kconfig symbol not found: {}", sym_name)
            continue

        if value in ("y", "m", "n"):
            tri = {"y": kc.Symbol.TRI_YES, "m": kc.Symbol.TRI_MOD, "n": kc.Symbol.TRI_NO}
            # kconfiglib uses set_value; older API uses write_min_config
            try:
                sym.set_value(tri[value])
            except AttributeError:
                sym.set_value({"y": 2, "m": 1, "n": 0}[value])
        else:
            try:
                sym.set_value(value)
            except Exception as exc:
                logger.warning("Could not set {} = {}: {}", sym_name, value, exc)

    logger.info("Applied {} kernel config options", len(options))


def write_config(kconfig: Any, output_path: Path) -> None:
    """Write the current Kconfig state to *output_path*.

    Args:
        kconfig:     kconfiglib.Kconfig instance.
        output_path: Destination .config file path.
    """
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    kconfig.write_config(str(output_path))
    logger.info("Kernel .config written to {}", output_path)


def build_kernel(
    kernel_dir: Path,
    config_path: Path,
    jobs: int = 0,
) -> tuple[bool, str]:
    """Compile the kernel (bzImage + modules).

    Args:
        kernel_dir:  Kernel source root.
        config_path: Path to the .config file (copied to kernel_dir/.config).
        jobs:        Parallel jobs (0 = cpu_count).

    Returns:
        ``(success, log_output)`` tuple.
    """
    kernel_dir = kernel_dir.resolve()
    config_path = config_path.resolve()

    import shutil
    shutil.copy2(str(config_path), str(kernel_dir / ".config"))

    num_jobs = jobs or os.cpu_count() or 1
    cmd = ["make", f"-j{num_jobs}", "bzImage", "modules"]

    logger.info("Building kernel with {} jobs …", num_jobs)
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold yellow]{task.description}"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("Compiling kernel …", total=None)
        result = subprocess.run(
            cmd,
            cwd=str(kernel_dir),
            capture_output=True,
            text=True,
        )
        progress.update(task, completed=1, total=1)

    success = result.returncode == 0
    log = result.stdout + "\n" + result.stderr
    if success:
        logger.info("Kernel build completed successfully.")
    else:
        logger.error("Kernel build failed (exit {}).", result.returncode)
    return success, log


def install_modules(kernel_dir: Path, rootfs_path: Path) -> bool:
    """Install compiled kernel modules into the rootfs.

    Args:
        kernel_dir:  Kernel source root (must have been built already).
        rootfs_path: Root of the target filesystem.

    Returns:
        ``True`` on success.
    """
    kernel_dir = kernel_dir.resolve()
    rootfs_path = rootfs_path.resolve()
    rootfs_path.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["make", f"INSTALL_MOD_PATH={rootfs_path}", "modules_install"],
        cwd=str(kernel_dir),
        capture_output=True,
        text=True,
    )
    success = result.returncode == 0
    if success:
        logger.info("Kernel modules installed to {}", rootfs_path)
    else:
        logger.error("modules_install failed:\n{}", result.stderr)
    return success
