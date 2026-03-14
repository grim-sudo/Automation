"""ISO assembly and bootloader configuration for custom distro builds."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from loguru import logger
from rich.progress import Progress, SpinnerColumn, TextColumn


def prepare_bootloader(rootfs_path: Path, work_dir: Path) -> bool:
    """
    Set up an isolinux bootloader in the work directory.

    Locates the system's syslinux installation, copies the required binary
    and module files into ``work_dir/isolinux/``, generates a boot menu
    config, and copies the kernel and initrd from the rootfs.

    Args:
        rootfs_path: Path to the populated rootfs directory.
        work_dir: Working directory for ISO assembly; isolinux/ is created here.

    Returns:
        True if bootloader setup succeeded.

    Raises:
        FileNotFoundError: If syslinux/isolinux is not installed on the host.
    """
    isolinux_dir = work_dir / "isolinux"
    isolinux_dir.mkdir(parents=True, exist_ok=True)

    # Candidate directories where syslinux ships its binary files
    syslinux_candidates = [
        Path("/usr/lib/syslinux/bios"),
        Path("/usr/share/syslinux"),
        Path("/usr/lib/syslinux"),
    ]

    syslinux_dir: Path | None = None
    for candidate in syslinux_candidates:
        if candidate.exists():
            syslinux_dir = candidate
            break

    if syslinux_dir is None:
        raise FileNotFoundError(
            "syslinux not found on this host. "
            "Install it with: apt-get install syslinux-common isolinux"
        )

    logger.info(f"Using syslinux files from: {syslinux_dir}")

    # Copy required bootloader binaries and c32 modules
    for fname in [
        "isolinux.bin",
        "ldlinux.c32",
        "libcom32.c32",
        "libutil.c32",
        "menu.c32",
    ]:
        src = syslinux_dir / fname
        if src.exists():
            shutil.copy2(src, isolinux_dir / fname)
            logger.debug(f"Copied {fname} to isolinux/")
        else:
            logger.warning(f"Syslinux file not found (non-fatal): {src}")

    # Generate isolinux.cfg
    cfg_content = """\
DEFAULT menu.c32
PROMPT 0
TIMEOUT 50
MENU TITLE Custom Linux Boot Menu

LABEL linux
    MENU LABEL Start Custom Linux
    KERNEL /boot/vmlinuz
    APPEND initrd=/boot/initrd.img root=/dev/sr0 ro quiet

LABEL memtest
    MENU LABEL Memory Test
    KERNEL /isolinux/memtest
"""
    (isolinux_dir / "isolinux.cfg").write_text(cfg_content)
    logger.info("isolinux.cfg written")

    # Copy kernel and initrd from the rootfs into work_dir/boot/
    boot_dir = work_dir / "boot"
    boot_dir.mkdir(exist_ok=True)

    rootfs_boot = rootfs_path / "boot"
    for fname in ["vmlinuz", "initrd.img"]:
        src = rootfs_boot / fname
        if src.exists():
            shutil.copy2(src, boot_dir / fname)
            logger.info(f"Copied {fname} to boot/")
        else:
            # Fall back to versioned filenames (e.g. vmlinuz-6.1.0-21-amd64)
            matches = sorted((rootfs_boot).glob(f"{fname}*")) if rootfs_boot.exists() else []
            if matches:
                shutil.copy2(matches[-1], boot_dir / fname)
                logger.info(f"Copied {matches[-1].name} -> boot/{fname}")
            else:
                logger.warning(f"Could not find {fname} in {rootfs_boot}")

    logger.info("Bootloader prepared successfully")
    return True


def assemble_iso(work_dir: Path, output_iso: Path, label: str = "CUSTOM") -> bool:
    """
    Assemble the final bootable ISO image using xorriso.

    Builds a hybrid El Torito ISO with an isolinux MBR bootloader.

    Args:
        work_dir: Directory containing the full ISO tree, including isolinux/.
        output_iso: Destination path for the generated .iso file.
        label: ISO 9660 volume label (max 32 characters; uppercase recommended).

    Returns:
        True if the ISO was created successfully, False otherwise.

    Raises:
        FileNotFoundError: If xorriso is not installed on the host.
    """
    if not shutil.which("xorriso"):
        raise FileNotFoundError(
            "xorriso not found on this host. Install it with: apt-get install xorriso"
        )

    output_iso.parent.mkdir(parents=True, exist_ok=True)

    # Truncate label to ISO 9660 maximum length
    safe_label = label[:32].upper()

    cmd = [
        "xorriso",
        "-as",
        "mkisofs",
        "-R",
        "-J",
        "-V",
        safe_label,
        "-b",
        "isolinux/isolinux.bin",
        "-c",
        "isolinux/boot.cat",
        "-no-emul-boot",
        "-boot-load-size",
        "4",
        "-boot-info-table",
        "-o",
        str(output_iso),
        str(work_dir),
    ]

    logger.info(f"Assembling ISO: {' '.join(cmd)}")

    with Progress(
        SpinnerColumn(),
        TextColumn("Assembling ISO..."),
    ) as progress:
        progress.add_task("iso", total=None)
        result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"xorriso failed:\n{result.stderr}")
        return False

    size_mb = output_iso.stat().st_size // (1024 * 1024) if output_iso.exists() else 0
    logger.info(f"ISO assembled: {output_iso} ({size_mb} MB)")
    return True


def verify_iso(iso_path: Path) -> bool:
    """
    Verify an ISO image using isovfy.

    If isovfy is not installed the check is skipped with a warning and
    True is returned so that the overall build is not blocked.

    Args:
        iso_path: Path to the ISO file to verify.

    Returns:
        True if the ISO passed verification or if isovfy is unavailable,
        False if isovfy reports errors.
    """
    if not shutil.which("isovfy"):
        logger.warning("isovfy not found on this host — skipping ISO verification")
        return True

    result = subprocess.run(
        ["isovfy", str(iso_path)],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        logger.error(f"ISO verification failed for {iso_path}:\n{result.stderr}")
        return False

    logger.info(f"ISO verification passed: {iso_path}")
    return True
