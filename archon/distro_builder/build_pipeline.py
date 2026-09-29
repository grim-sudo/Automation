"""Full distro build pipeline orchestrating all build stages."""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from pathlib import Path

from loguru import logger
from rich.console import Console

from .iso_assembler import assemble_iso, prepare_bootloader, verify_iso
from .kernel_configurator import (
    apply_options,
    build_kernel,
    load_default_config,
    write_config,
)
from .kernel_fetcher import apply_patches, download_kernel, fetch_latest_stable_version
from .live_builder import build_live_layout, install_custom_kernel
from .models import BuildContext, BuildResult, DistroProfile
from .package_selector import nl_to_profile
from .rootfs_builder import build_debian_rootfs

console = Console()


def _invoking_user_home() -> Path | None:
    """Home directory of the user who launched the build, even under sudo.

    When Archon runs a privileged step (or the whole process is root), a bare
    ``~`` would resolve to ``/root``. We resolve it to the *invoking* user's home
    via ``SUDO_USER`` so caches never land in root's home. Returns ``None`` when
    no safe home can be determined (caller should fall back to /tmp).
    """
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user and sudo_user != "root":
        try:
            import pwd

            return Path(pwd.getpwnam(sudo_user).pw_dir)
        except (KeyError, ImportError):
            return None
    if os.geteuid() != 0:
        return Path.home()
    return None


def _resolve_kernel_cache() -> Path:
    """Resolve the kernel cache directory from config, safe under sudo/root.

    Honors ``distro_builder.kernel_cache_dir`` and expands a leading ``~`` to the
    invoking user's home (not root's). Falls back to ``/tmp/archon_kernel_cache``
    when the configured path would resolve into root's home unsafely.
    """
    configured = "~/.archon/kernel_cache"
    try:
        from ..config import get_config

        configured = get_config().distro_builder.kernel_cache_dir or configured
    except Exception:  # noqa: BLE001 - config is optional; fall back to the default
        pass

    raw = configured.strip() or "~/.archon/kernel_cache"
    if raw.startswith("~"):
        home = _invoking_user_home()
        if home is None:
            return Path("/tmp/archon_kernel_cache")
        raw = str(home) + raw[1:]
    return Path(raw).expanduser().resolve()


async def build_distro(
    profile: DistroProfile,
    output_dir: Path,
    jobs: int = 0,
    work_dir: Path | None = None,
) -> BuildResult:
    """
    Orchestrate the full live-ISO build pipeline.

    Pipeline stages (Debian base):
        For a custom kernel: resolve version, download source, apply patches,
        configure (.config), and compile (bzImage + modules).
        Then, always: build the rootfs with live-boot infrastructure (and the
        distro kernel package on the prebuilt path), install the custom kernel
        + a matching initramfs when applicable, SquashFS the rootfs into
        ``live/filesystem.squashfs``, stage kernel + initrd, write a
        ``boot=live`` isolinux config, assemble the ISO with xorriso, and verify.

    Args:
        profile: The DistroProfile describing what to build.
        output_dir: Directory where the final ISO and build log will be written.
        jobs: Number of parallel compilation jobs. 0 means os.cpu_count().

    Returns:
        A BuildResult capturing success/failure, timings, ISO path, and any
        error message.
    """
    if jobs == 0:
        jobs = os.cpu_count() or 4

    # Live boot is implemented on the Debian live-boot stack (SquashFS +
    # live-boot initramfs hooks). Arch/Buildroot use entirely different live
    # mechanisms (archiso, custom init), so fail clearly — before allocating any
    # work dirs or log handlers — rather than emit a non-booting image.
    if profile.base != "debian":
        return BuildResult(
            success=False,
            log_path="",
            error_message=(
                f"Live ISO builds currently support the 'debian' base only; "
                f"requested base '{profile.base}' is not yet supported."
            ),
        )

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    base_work = Path(work_dir) if work_dir else Path("/tmp")
    work_dir = (base_work / f"archon_distro_{profile.name}_{int(time.time())}").resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    rootfs_path = work_dir / "rootfs"
    rootfs_path.mkdir(exist_ok=True)

    log_path = output_dir / f"{profile.name}_build.log"
    # Attach a plain file handler so all loguru records land in the log file
    log_handler_id = logger.add(str(log_path), level="DEBUG", enqueue=True)

    iso_path = output_dir / f"{profile.name}.iso"
    start_time = time.time()

    BuildContext(
        profile=profile,
        work_dir=work_dir,
        output_dir=output_dir,
        jobs=jobs,
    )

    # Live boot is implemented on the Debian live-boot stack (SquashFS +
    # live-boot initramfs hooks); the base was already validated above.
    custom_kernel = profile.kernel.source == "custom"

    try:
        kernel_dir: Path | None = None
        if custom_kernel:
            # ── Step 1 – Resolve kernel version ──────────────────────────── #
            console.print("[bold cyan]Step 1/6:[/bold cyan] Resolving kernel version")
            logger.info("Step 1/6: Resolving kernel version (custom source build)")

            kernel_version = profile.kernel.version
            if kernel_version == "latest-stable":
                kernel_version = await fetch_latest_stable_version()
                logger.info(f"Latest stable kernel: {kernel_version}")
            console.print(f"  Kernel: [green]{kernel_version}[/green]")

            # ── Step 2 – Download kernel source ──────────────────────────── #
            console.print("[bold cyan]Step 2/6:[/bold cyan] Downloading kernel source")
            logger.info(f"Step 2/6: Downloading kernel {kernel_version}")

            kernel_cache = _resolve_kernel_cache()
            kernel_cache.mkdir(parents=True, exist_ok=True)
            kernel_dir = await download_kernel(kernel_version, kernel_cache)

            # ── Step 2b – Apply patches (optional) ───────────────────────── #
            if profile.kernel.patches:
                logger.info(f"Applying {len(profile.kernel.patches)} patch(es)")
                patch_paths = [Path(p) for p in profile.kernel.patches]
                patches_ok = await apply_patches(kernel_dir, patch_paths)
                if not patches_ok:
                    logger.warning("One or more patches did not apply cleanly — continuing")

            # ── Step 3 – Configure kernel ────────────────────────────────── #
            console.print("[bold cyan]Step 3/6:[/bold cyan] Configuring kernel")
            logger.info("Step 3/6: Configuring kernel")

            if profile.kernel.kconfig_options:
                kconfig = await asyncio.to_thread(load_default_config, kernel_dir)
                await asyncio.to_thread(apply_options, kconfig, profile.kernel.kconfig_options)
                config_path = work_dir / ".config"
                await asyncio.to_thread(write_config, kconfig, config_path)
                logger.info(
                    f"Custom .config with {len(profile.kernel.kconfig_options)} option(s) written"
                )
            else:
                config_path = kernel_dir / ".config"
                logger.info("No custom kconfig_options — will use defconfig")

            # ── Step 4 – Build kernel ────────────────────────────────────── #
            console.print(f"[bold cyan]Step 4/6:[/bold cyan] Building kernel (jobs={jobs})")
            logger.info(f"Step 4/6: Building kernel with {jobs} job(s)")

            success, build_log = await asyncio.to_thread(
                build_kernel, kernel_dir, config_path, jobs
            )
            if not success:
                logger.error(f"Kernel build failed. Last output:\n{build_log[-1000:]}")
                return BuildResult(
                    success=False,
                    log_path=str(log_path),
                    build_time_seconds=time.time() - start_time,
                    error_message=f"Kernel build failed: {build_log[:500]}",
                )
            logger.info("Kernel build finished successfully")
        else:
            console.print(
                "[bold cyan]Steps 1-4/6:[/bold cyan] Skipped "
                "(using distro prebuilt kernel package)"
            )
            logger.info("Using prebuilt distro kernel — skipping source download/compile")

        # ── Step 5 – Build rootfs (installs live-boot + kernel package) ──── #
        console.print("[bold cyan]Step 5/6:[/bold cyan] Building debian rootfs")
        logger.info(f"Step 5/6: Building debian rootfs at {rootfs_path}")

        # Async coroutine — must be awaited directly (wrapping in
        # asyncio.to_thread only creates a never-awaited coroutine, the old
        # "empty 1.6 MB ISO" bug).
        rootfs_ok = await build_debian_rootfs(profile, rootfs_path)
        if not rootfs_ok:
            return BuildResult(
                success=False,
                log_path=str(log_path),
                build_time_seconds=time.time() - start_time,
                error_message="debian rootfs build failed",
            )

        # A custom kernel isn't in the rootfs yet — install its modules, image,
        # and a matching live-boot initramfs. The prebuilt package already did
        # all of this during rootfs build.
        if custom_kernel and kernel_dir is not None:
            await install_custom_kernel(kernel_dir, rootfs_path)

        # ── Step 6 – Assemble live ISO ───────────────────────────────────── #
        console.print("[bold cyan]Step 6/6:[/bold cyan] Assembling live ISO")
        logger.info("Step 6/6: SquashFS + bootloader + ISO")

        iso_dir = await build_live_layout(rootfs_path, work_dir)
        await asyncio.to_thread(prepare_bootloader, iso_dir, profile.name)

        iso_ok = await asyncio.to_thread(assemble_iso, iso_dir, iso_path, profile.name.upper())
        if not iso_ok:
            return BuildResult(
                success=False,
                log_path=str(log_path),
                build_time_seconds=time.time() - start_time,
                error_message="ISO assembly failed",
            )

        # Verification is best-effort — failure does not abort the result
        await asyncio.to_thread(verify_iso, iso_path)

        build_time = time.time() - start_time
        size = iso_path.stat().st_size if iso_path.exists() else None

        console.print(
            f"[bold green]Build complete![/bold green] ISO: [cyan]{iso_path}[/cyan] "
            f"({size // 1024 // 1024 if size else 0} MB, {build_time:.1f}s)"
        )
        logger.info(f"Build completed in {build_time:.1f}s, ISO at {iso_path}")

        return BuildResult(
            success=True,
            iso_path=str(iso_path),
            log_path=str(log_path),
            build_time_seconds=build_time,
            size_bytes=size,
        )

    except Exception as exc:
        build_time = time.time() - start_time
        logger.error(f"Build pipeline failed after {build_time:.1f}s: {exc}", exc_info=True)
        console.print(f"[bold red]Build failed:[/bold red] {exc}")
        return BuildResult(
            success=False,
            log_path=str(log_path),
            build_time_seconds=build_time,
            error_message=str(exc),
        )
    finally:
        # Always remove the loguru file handler added for this build
        logger.remove(log_handler_id)
        shutil.rmtree(work_dir, ignore_errors=True)


async def build_from_nl(
    nl_command: str, output_dir: Path, work_dir: Path | None = None
) -> BuildResult:
    """
    Build a distro ISO from a natural language command string.

    Parses the command into a DistroProfile via the NL package selector and
    then delegates to the full build_distro pipeline.

    Args:
        nl_command: Free-form description, e.g. "minimal debian with nginx headless".
        output_dir: Directory where the ISO and build log will be written.

    Returns:
        A BuildResult from the full build pipeline.
    """
    profile = nl_to_profile(nl_command)
    console.print(f"Parsed profile: [bold]{profile.name}[/bold] (base={profile.base})")
    logger.info(f"Parsed NL profile:\n{profile.model_dump_json(indent=2)}")
    return await build_distro(profile, output_dir, work_dir=work_dir)


def estimate_build_time(profile: DistroProfile) -> str:
    """
    Return a human-readable estimate of the total build time.

    Provides a rough wall-clock estimate based on the distro base, kernel
    compilation requirements, and desktop environment selection.

    Args:
        profile: The DistroProfile to estimate for.

    Returns:
        A descriptive string such as
        "~35-50 minutes (debootstrap + package install) + ~20-40 minutes (kernel compile)".
    """
    base_estimates: dict[str, str] = {
        "debian": "~35-50 minutes (debootstrap + package install)",
        "arch": "~25-40 minutes (pacstrap + configuration)",
        "unix": "~60-120 minutes (Buildroot full build)",
    }
    estimate = base_estimates.get(profile.base, "~45 minutes (base rootfs)")

    # Kernel cost depends on whether we compile from source or use the package.
    if profile.kernel.source == "custom":
        estimate += " + ~20-40 minutes (custom kernel compile + initramfs)"
    else:
        estimate += " + ~2-5 minutes (prebuilt kernel package + initramfs)"

    # SquashFS compression of the rootfs into a live image
    estimate += " + ~3-8 minutes (SquashFS + ISO assembly)"

    # Desktop environment adds time for package installation
    if profile.desktop:
        estimate += f" + ~10-15 minutes ({profile.desktop} desktop packages)"

    return estimate
