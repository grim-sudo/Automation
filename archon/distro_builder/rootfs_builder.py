"""
Root filesystem builders for Debian, Arch, and Buildroot (unix minimal).

Each builder function requires root privileges (os.geteuid() == 0)
and logs all subprocess output via loguru.

All blocking subprocess calls run in asyncio.to_thread().
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

from loguru import logger
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from .models import DistroProfile

__all__ = [
    "build_debian_rootfs",
    "build_arch_rootfs",
    "build_buildroot_rootfs",
]

_BUILDROOT_URL = "https://buildroot.org/downloads/buildroot-snapshot.tar.gz"


def _require_root(func_name: str) -> None:
    """Ensure privileged commands can run, or raise PermissionError.

    Root itself is fine. Otherwise an active :class:`PrivilegeEscalator` session
    (opened by the caller after prompting for the sudo password) lets the build
    proceed by running each command through ``sudo -S``. Only when neither is
    available do we refuse.

    Args:
        func_name: Name of the calling function for the error message.

    Raises:
        PermissionError: If not root and no sudo escalation session is active.
    """
    if os.geteuid() == 0:
        return
    try:
        from ..security.privilege import get_escalator

        if get_escalator().active_session is not None:
            return
    except Exception:  # noqa: BLE001 - fall through to the honest refusal
        pass
    raise PermissionError(
        f"{func_name}() requires root privileges. Re-run with sudo or as root."
    )


def _run_logged(
    cmd: list[str], cwd: str | None = None, env: dict | None = None
) -> tuple[bool, str]:
    """Run a command, log stdout/stderr, return (success, combined_log).

    When not root but a sudo-escalation session is active, the command runs
    through ``sudo -S`` transparently so the whole build can complete.
    """
    logger.debug("Running: {}", " ".join(cmd))
    session = None
    if os.geteuid() != 0:
        try:
            from ..security.privilege import get_escalator

            session = get_escalator().active_session
        except Exception:  # noqa: BLE001
            session = None
    run_env = env or dict(os.environ)
    if session is not None:
        result = session.run(cmd, cwd=cwd, env=run_env)
    else:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            env=run_env,
        )
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    if result.returncode != 0:
        logger.error("Command failed (exit {}):\n{}", result.returncode, result.stderr[:500])
    else:
        logger.debug("Command OK: {}", cmd[0])
    return result.returncode == 0, output


async def build_debian_rootfs(profile: DistroProfile, rootfs_path: Path) -> bool:
    """Build a Debian minimal rootfs using debootstrap.

    Args:
        profile:     DistroProfile with packages, locale, timezone, hostname.
        rootfs_path: Target rootfs directory (will be created if absent).

    Returns:
        ``True`` on success.

    Raises:
        PermissionError: If not running as root.
    """
    _require_root("build_debian_rootfs")
    rootfs_path = rootfs_path.resolve()
    rootfs_path.mkdir(parents=True, exist_ok=True)

    try:
        from ..config import get_config

        cfg = get_config()
        mirror = cfg.distro_builder.debian_mirror
        suite = cfg.distro_builder.debian_suite
    except Exception:
        mirror = "http://deb.debian.org/debian"
        suite = "bookworm"

    logger.info("Running debootstrap {} {} …", suite, rootfs_path)

    with Progress(
        SpinnerColumn(), TextColumn("[bold]{task.description}"), TimeElapsedColumn()
    ) as p:
        task = p.add_task("debootstrap …", total=None)

        ok, log = await asyncio.to_thread(
            _run_logged,
            ["debootstrap", "--arch=amd64", suite, str(rootfs_path), mirror],
        )
        p.update(task, completed=1, total=1)

    if not ok:
        logger.error("debootstrap failed.")
        return False

    # ── chroot setup ──────────────────────────────────────────────────────────
    chroot = ["chroot", str(rootfs_path)]

    # Set hostname
    (rootfs_path / "etc" / "hostname").write_text(profile.hostname + "\n", encoding="utf-8")

    # Set timezone
    tz_file = rootfs_path / "etc" / "timezone"
    tz_file.write_text(profile.timezone + "\n", encoding="utf-8")
    await asyncio.to_thread(
        _run_logged,
        chroot + ["ln", "-sf", f"/usr/share/zoneinfo/{profile.timezone}", "/etc/localtime"],
    )

    # Locale
    locale_gen = rootfs_path / "etc" / "locale.gen"
    existing = locale_gen.read_text(encoding="utf-8") if locale_gen.exists() else ""
    locale_gen.write_text(existing + f"\n{profile.locale} UTF-8\n", encoding="utf-8")
    await asyncio.to_thread(_run_logged, chroot + ["locale-gen"])

    # Install packages
    if profile.packages:
        env = dict(os.environ)
        env["DEBIAN_FRONTEND"] = "noninteractive"
        pkg_cmd = (
            chroot + ["apt-get", "install", "-y", "--no-install-recommends"] + profile.packages
        )
        logger.info("Installing {} packages …", len(profile.packages))
        ok, _ = await asyncio.to_thread(_run_logged, pkg_cmd, env=env)
        if not ok:
            logger.warning("Some packages failed to install; continuing.")

    # Cleanup
    await asyncio.to_thread(_run_logged, chroot + ["apt-get", "clean"])

    logger.info("Debian rootfs built at {}", rootfs_path)
    return True


async def build_arch_rootfs(profile: DistroProfile, rootfs_path: Path) -> bool:
    """Build an Arch Linux rootfs using pacstrap.

    Args:
        profile:     DistroProfile with packages, locale, timezone, hostname.
        rootfs_path: Target rootfs directory.

    Returns:
        ``True`` on success.

    Raises:
        PermissionError: If not running as root.
    """
    _require_root("build_arch_rootfs")
    rootfs_path = rootfs_path.resolve()
    rootfs_path.mkdir(parents=True, exist_ok=True)

    base_pkgs = ["base", "linux", "linux-firmware"] + profile.packages

    logger.info("Running pacstrap …")
    with Progress(
        SpinnerColumn(), TextColumn("[bold]{task.description}"), TimeElapsedColumn()
    ) as p:
        task = p.add_task("pacstrap …", total=None)
        ok, _ = await asyncio.to_thread(_run_logged, ["pacstrap", str(rootfs_path)] + base_pkgs)
        p.update(task, completed=1, total=1)

    if not ok:
        logger.error("pacstrap failed.")
        return False

    arch_chroot = ["arch-chroot", str(rootfs_path)]

    # Timezone
    await asyncio.to_thread(
        _run_logged,
        arch_chroot + ["ln", "-sf", f"/usr/share/zoneinfo/{profile.timezone}", "/etc/localtime"],
    )
    await asyncio.to_thread(_run_logged, arch_chroot + ["hwclock", "--systohc"])

    # Locale
    locale_gen = rootfs_path / "etc" / "locale.gen"
    existing = locale_gen.read_text(encoding="utf-8") if locale_gen.exists() else ""
    locale_gen.write_text(existing + f"\n{profile.locale} UTF-8\n", encoding="utf-8")
    await asyncio.to_thread(_run_logged, arch_chroot + ["locale-gen"])
    (rootfs_path / "etc" / "locale.conf").write_text(f"LANG={profile.locale}\n", encoding="utf-8")

    # Hostname
    (rootfs_path / "etc" / "hostname").write_text(profile.hostname + "\n", encoding="utf-8")

    logger.info("Arch rootfs built at {}", rootfs_path)
    return True


async def build_buildroot_rootfs(
    profile: DistroProfile,
    rootfs_path: Path,
    jobs: int = 0,
) -> bool:
    """Build a minimal rootfs using Buildroot.

    Args:
        profile:     DistroProfile (kconfig_options are treated as BR2_ options).
        rootfs_path: Where Buildroot output/images/ will be copied.
        jobs:        Parallel make jobs (0 = cpu_count).

    Returns:
        ``True`` on success.

    Raises:
        PermissionError: If not running as root.
    """
    _require_root("build_buildroot_rootfs")
    rootfs_path = rootfs_path.resolve()
    rootfs_path.mkdir(parents=True, exist_ok=True)

    import tempfile

    build_dir = Path(tempfile.mkdtemp(prefix="omni_buildroot_"))
    num_jobs = jobs or os.cpu_count() or 1

    # Download Buildroot snapshot
    logger.info("Downloading Buildroot snapshot …")
    import httpx

    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        resp = await client.get(_BUILDROOT_URL)
        resp.raise_for_status()
        tarball = build_dir / "buildroot.tar.gz"
        tarball.write_bytes(resp.content)

    # Extract
    await asyncio.to_thread(
        subprocess.run,
        ["tar", "-xzf", str(tarball), "-C", str(build_dir), "--strip-components=1"],
        check=True,
    )
    tarball.unlink()

    # Generate .config from profile BR2_ options + defaults
    config_lines = ['BR2_WGET="wget --passive-ftp -nd -t 3"']
    for key, val in profile.kernel.kconfig_options.items():
        if key.startswith("BR2_"):
            config_lines.append(f"{key}={val}")
    config_lines.append(f'BR2_TARGET_GENERIC_HOSTNAME="{profile.hostname}"')
    (build_dir / ".config").write_text("\n".join(config_lines) + "\n", encoding="utf-8")

    # Merge defconfig
    await asyncio.to_thread(
        _run_logged,
        ["make", "olddefconfig"],
        cwd=str(build_dir),
    )

    # Build
    logger.info("Building Buildroot rootfs with {} jobs …", num_jobs)
    with Progress(
        SpinnerColumn(), TextColumn("[bold]{task.description}"), TimeElapsedColumn()
    ) as p:
        task = p.add_task("Buildroot make …", total=None)
        ok, _ = await asyncio.to_thread(
            _run_logged,
            ["make", f"-j{num_jobs}"],
            cwd=str(build_dir),
        )
        p.update(task, completed=1, total=1)

    if not ok:
        logger.error("Buildroot make failed.")
        return False

    # Copy output
    import shutil

    images_dir = build_dir / "output" / "images"
    for f in images_dir.glob("rootfs.*"):
        dest = rootfs_path / f.name
        shutil.copy2(str(f), str(dest))
        logger.info("Copied {} to {}", f.name, dest)

    shutil.rmtree(str(build_dir), ignore_errors=True)
    logger.info("Buildroot rootfs complete at {}", rootfs_path)
    return True
