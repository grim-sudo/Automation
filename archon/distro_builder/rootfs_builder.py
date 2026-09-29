"""
Root filesystem builders for Debian, Arch, and Buildroot (unix minimal).

Each builder function requires root privileges (os.geteuid() == 0)
and logs all subprocess output via loguru.

All blocking subprocess calls run in asyncio.to_thread().
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import subprocess
import tempfile
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

# Fallback used when mirror selection is disabled or every candidate fails. The
# deb.debian.org CDN is geo-routed, so it is a safe default even when slow.
_DEFAULT_DEBIAN_MIRROR = "http://deb.debian.org/debian"

# Curated set of well-maintained, full Debian mirrors probed when the configured
# mirror is "auto". Kept short on purpose — the point is to pick the fastest
# reachable one, not to mirror the whole official list.
_DEBIAN_MIRROR_CANDIDATES = (
    "http://deb.debian.org/debian",
    "http://ftp.us.debian.org/debian",
    "http://ftp.uk.debian.org/debian",
    "http://ftp.de.debian.org/debian",
    "http://mirror.leaseweb.com/debian",
    "http://mirrors.kernel.org/debian",
)


def _select_debian_mirror(configured: str, suite: str) -> str:
    """Resolve the Debian mirror to use, probing for the fastest when 'auto'.

    An explicit URL is returned untouched. When *configured* is ``"auto"`` (or
    blank), each candidate's ``dists/<suite>/Release`` is fetched concurrently and
    the fastest responder wins. If probing is impossible (no httpx) or every
    candidate fails, we fall back to the geo-routed CDN.
    """
    if configured and configured.strip().lower() != "auto":
        return configured

    try:
        import concurrent.futures
        import time

        import httpx
    except Exception:  # noqa: BLE001 - no probing available, use the safe default
        logger.debug("Mirror probing unavailable; using {}", _DEFAULT_DEBIAN_MIRROR)
        return _DEFAULT_DEBIAN_MIRROR

    def _probe(base: str) -> float | None:
        url = f"{base.rstrip('/')}/dists/{suite}/Release"
        try:
            start = time.monotonic()
            with httpx.Client(follow_redirects=True, timeout=5.0) as client:
                resp = client.get(url, headers={"Range": "bytes=0-0"})
            if resp.status_code >= 400:
                return None
            return time.monotonic() - start
        except httpx.HTTPError:
            return None

    timings: dict[str, float] = {}
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=len(_DEBIAN_MIRROR_CANDIDATES)
    ) as pool:
        for base, elapsed in zip(
            _DEBIAN_MIRROR_CANDIDATES,
            pool.map(_probe, _DEBIAN_MIRROR_CANDIDATES),
            strict=True,
        ):
            if elapsed is not None:
                timings[base] = elapsed

    if not timings:
        logger.warning("No Debian mirror responded; falling back to {}", _DEFAULT_DEBIAN_MIRROR)
        return _DEFAULT_DEBIAN_MIRROR

    fastest = min(timings, key=timings.__getitem__)
    logger.info("Fastest Debian mirror: {} ({:.0f} ms)", fastest, timings[fastest] * 1000)
    return fastest


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


def _install_file(content: str, dest: Path, mode: str = "0644") -> tuple[bool, str]:
    """Write *content* to *dest* inside a root-owned rootfs, with privilege.

    debootstrap/pacstrap create the rootfs tree owned by root, so the
    unprivileged build process cannot write into it directly — a plain
    ``Path.write_text`` raises ``PermissionError`` (this is the ``/etc/hostname``
    failure). The escalation session's stdin is already consumed by the sudo
    password, so we can't pipe content through ``sudo tee`` either.

    Instead, stage the content in a user-owned temp file and ``install`` it into
    place through :func:`_run_logged` (which sudo-wraps when escalated). ``install``
    sets ownership to the running user (root) and an explicit mode in one step,
    and passing content via a file sidesteps any shell-quoting of the payload.
    """
    fd, tmp = tempfile.mkstemp(prefix="archon_rootfs_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        return _run_logged(["install", "-m", mode, "-T", tmp, str(dest)])
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp)


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
        mirror = "auto"
        suite = "bookworm"

    mirror = await asyncio.to_thread(_select_debian_mirror, mirror, suite)

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
    # The rootfs is root-owned (debootstrap ran as root), so config files must be
    # written through the privilege session, not with a direct Path.write_text.
    chroot = ["chroot", str(rootfs_path)]

    # Set hostname
    await asyncio.to_thread(
        _install_file, profile.hostname + "\n", rootfs_path / "etc" / "hostname"
    )

    # Set timezone
    await asyncio.to_thread(
        _install_file, profile.timezone + "\n", rootfs_path / "etc" / "timezone"
    )
    await asyncio.to_thread(
        _run_logged,
        chroot + ["ln", "-sf", f"/usr/share/zoneinfo/{profile.timezone}", "/etc/localtime"],
    )

    # Locale (read is fine — the file is world-readable; only the write needs root)
    locale_gen = rootfs_path / "etc" / "locale.gen"
    existing = locale_gen.read_text(encoding="utf-8") if locale_gen.exists() else ""
    await asyncio.to_thread(
        _install_file, existing + f"\n{profile.locale} UTF-8\n", locale_gen
    )
    await asyncio.to_thread(_run_logged, chroot + ["locale-gen"])

    # Live-boot infrastructure is mandatory for a bootable live ISO: live-boot
    # supplies the initramfs hooks that mount live/filesystem.squashfs off the
    # media, live-config handles first-boot setup, and systemd-sysv provides the
    # init a debootstrap --variant=minbase tree otherwise lacks. When the profile
    # asks for the distro's prebuilt kernel, install it here too so its postinst
    # generates a live-capable initramfs (live-boot is configured in the same
    # transaction). A custom-source kernel is installed separately afterwards.
    live_pkgs = ["live-boot", "live-config", "live-config-systemd", "systemd-sysv"]
    if profile.kernel.source == "prebuilt":
        live_pkgs.append("linux-image-amd64")

    install_pkgs = live_pkgs + list(profile.packages)

    env = dict(os.environ)
    env["DEBIAN_FRONTEND"] = "noninteractive"

    # apt needs a package index inside the chroot before it can install anything.
    await asyncio.to_thread(_run_logged, chroot + ["apt-get", "update"], env=env)

    pkg_cmd = chroot + ["apt-get", "install", "-y", "--no-install-recommends"] + install_pkgs
    logger.info("Installing {} packages (incl. live-boot infra) …", len(install_pkgs))
    ok, _ = await asyncio.to_thread(_run_logged, pkg_cmd, env=env)
    if not ok:
        # live-boot failing is fatal — without it the ISO cannot boot. Profile
        # packages failing is not, so only refuse when the live infra is missing.
        live_boot_present = (rootfs_path / "usr" / "share" / "initramfs-tools" / "scripts"
                             / "live").exists()
        if not live_boot_present:
            logger.error("live-boot infrastructure failed to install — ISO would not boot.")
            return False
        logger.warning("Some profile packages failed to install; continuing.")

    # Cleanup
    await asyncio.to_thread(_run_logged, chroot + ["apt-get", "clean"], env=env)

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

    # Locale — the pacstrap tree is root-owned, so writes go through the session.
    locale_gen = rootfs_path / "etc" / "locale.gen"
    existing = locale_gen.read_text(encoding="utf-8") if locale_gen.exists() else ""
    await asyncio.to_thread(
        _install_file, existing + f"\n{profile.locale} UTF-8\n", locale_gen
    )
    await asyncio.to_thread(_run_logged, arch_chroot + ["locale-gen"])
    await asyncio.to_thread(
        _install_file, f"LANG={profile.locale}\n", rootfs_path / "etc" / "locale.conf"
    )

    # Hostname
    await asyncio.to_thread(
        _install_file, profile.hostname + "\n", rootfs_path / "etc" / "hostname"
    )

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

    build_dir = Path(tempfile.mkdtemp(prefix="archon_buildroot_"))
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
