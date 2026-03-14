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
    install_modules,
    load_default_config,
    write_config,
)
from .kernel_fetcher import apply_patches, download_kernel, fetch_latest_stable_version
from .models import BuildContext, BuildResult, DistroProfile
from .package_selector import nl_to_profile
from .rootfs_builder import build_arch_rootfs, build_buildroot_rootfs, build_debian_rootfs

console = Console()


async def build_distro(
    profile: DistroProfile,
    output_dir: Path,
    jobs: int = 0,
) -> BuildResult:
    """
    Orchestrate the full distro build pipeline.

    Pipeline stages:
        1. Resolve kernel version (if "latest-stable")
        2. Download kernel source tarball
        3. Apply any requested patches
        4. Configure kernel (.config generation)
        5. Compile kernel (bzImage + modules)
        6. Build rootfs (debootstrap / pacstrap / Buildroot)
        7. Install kernel modules into rootfs
        8. Prepare isolinux bootloader
        9. Assemble ISO with xorriso
        10. Verify ISO with isovfy

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

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    work_dir = Path(f"/tmp/omni_distro_{profile.name}_{int(time.time())}").resolve()
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

    try:
        # ------------------------------------------------------------------ #
        # Step 1 – Resolve kernel version                                      #
        # ------------------------------------------------------------------ #
        console.print("[bold cyan]Step 1/7:[/bold cyan] Resolving kernel version")
        logger.info("Step 1/7: Resolving kernel version")

        kernel_version = profile.kernel.version
        if kernel_version == "latest-stable":
            kernel_version = await fetch_latest_stable_version()
            logger.info(f"Latest stable kernel: {kernel_version}")
        console.print(f"  Kernel: [green]{kernel_version}[/green]")

        # ------------------------------------------------------------------ #
        # Step 2 – Download kernel source                                      #
        # ------------------------------------------------------------------ #
        console.print("[bold cyan]Step 2/7:[/bold cyan] Downloading kernel source")
        logger.info(f"Step 2/7: Downloading kernel {kernel_version}")

        kernel_cache = Path.home() / ".omniautomator" / "kernel_cache"
        kernel_cache.mkdir(parents=True, exist_ok=True)
        kernel_dir = await download_kernel(kernel_version, kernel_cache)

        # ------------------------------------------------------------------ #
        # Step 2b – Apply patches (optional)                                   #
        # ------------------------------------------------------------------ #
        if profile.kernel.patches:
            logger.info(f"Applying {len(profile.kernel.patches)} patch(es)")
            patch_paths = [Path(p) for p in profile.kernel.patches]
            patches_ok = await apply_patches(kernel_dir, patch_paths)
            if not patches_ok:
                logger.warning("One or more patches did not apply cleanly — continuing")

        # ------------------------------------------------------------------ #
        # Step 3 – Configure kernel                                            #
        # ------------------------------------------------------------------ #
        console.print("[bold cyan]Step 3/7:[/bold cyan] Configuring kernel")
        logger.info("Step 3/7: Configuring kernel")

        if profile.kernel.kconfig_options:
            kconfig = await asyncio.to_thread(load_default_config, kernel_dir)
            await asyncio.to_thread(apply_options, kconfig, profile.kernel.kconfig_options)
            config_path = work_dir / ".config"
            await asyncio.to_thread(write_config, kconfig, config_path)
            logger.info(
                f"Custom .config with {len(profile.kernel.kconfig_options)} option(s) written"
            )
        else:
            # Use whatever defconfig make produces; build_kernel will run defconfig
            config_path = kernel_dir / ".config"
            logger.info("No custom kconfig_options — will use defconfig")

        # ------------------------------------------------------------------ #
        # Step 4 – Build kernel                                                #
        # ------------------------------------------------------------------ #
        console.print(f"[bold cyan]Step 4/7:[/bold cyan] Building kernel (jobs={jobs})")
        logger.info(f"Step 4/7: Building kernel with {jobs} job(s)")

        success, build_log = await asyncio.to_thread(build_kernel, kernel_dir, config_path, jobs)
        if not success:
            logger.error(f"Kernel build failed. Last output:\n{build_log[-1000:]}")
            return BuildResult(
                success=False,
                log_path=str(log_path),
                build_time_seconds=time.time() - start_time,
                error_message=f"Kernel build failed: {build_log[:500]}",
            )
        logger.info("Kernel build finished successfully")

        # ------------------------------------------------------------------ #
        # Step 5 – Build rootfs                                                #
        # ------------------------------------------------------------------ #
        console.print(f"[bold cyan]Step 5/7:[/bold cyan] Building {profile.base} rootfs")
        logger.info(f"Step 5/7: Building {profile.base} rootfs at {rootfs_path}")

        if profile.base == "debian":
            rootfs_ok = await asyncio.to_thread(build_debian_rootfs, profile, rootfs_path)
        elif profile.base == "arch":
            rootfs_ok = await asyncio.to_thread(build_arch_rootfs, profile, rootfs_path)
        else:
            rootfs_ok = await asyncio.to_thread(build_buildroot_rootfs, profile, rootfs_path, jobs)

        if not rootfs_ok:
            return BuildResult(
                success=False,
                log_path=str(log_path),
                build_time_seconds=time.time() - start_time,
                error_message=f"{profile.base} rootfs build failed",
            )

        # Install kernel modules into the freshly-built rootfs
        modules_ok = await asyncio.to_thread(install_modules, kernel_dir, rootfs_path)
        if not modules_ok:
            logger.warning("modules_install reported a failure — proceeding anyway")

        # ------------------------------------------------------------------ #
        # Step 6 – Prepare bootloader                                          #
        # ------------------------------------------------------------------ #
        console.print("[bold cyan]Step 6/7:[/bold cyan] Preparing isolinux bootloader")
        logger.info("Step 6/7: Preparing bootloader")

        await asyncio.to_thread(prepare_bootloader, rootfs_path, work_dir)

        # ------------------------------------------------------------------ #
        # Step 7 – Assemble and verify ISO                                     #
        # ------------------------------------------------------------------ #
        console.print("[bold cyan]Step 7/7:[/bold cyan] Assembling ISO")
        logger.info("Step 7/7: Assembling ISO")

        iso_ok = await asyncio.to_thread(assemble_iso, work_dir, iso_path, profile.name.upper())
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


async def build_from_nl(nl_command: str, output_dir: Path) -> BuildResult:
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
    return await build_distro(profile, output_dir)


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

    # Kernel compilation cost
    if profile.kernel.kconfig_options:
        estimate += " + ~20-40 minutes (custom kernel compile)"
    else:
        estimate += " + ~20-40 minutes (kernel compile)"

    # Desktop environment adds time for package installation
    if profile.desktop:
        estimate += f" + ~10-15 minutes ({profile.desktop} desktop packages)"

    return estimate
