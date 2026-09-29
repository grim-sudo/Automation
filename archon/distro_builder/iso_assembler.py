"""ISO assembly and bootloader configuration for custom distro builds."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from loguru import logger
from rich.progress import Progress, SpinnerColumn, TextColumn

# GRUB config baked into the standalone EFI binary. It locates the live media by
# searching for a file it is guaranteed to contain, then boots it — self-contained
# so it does not depend on an on-disk grub.cfg being found first.
_GRUB_EMBED_CFG = """\
insmod all_video
insmod part_gpt
insmod part_msdos
insmod fat
insmod iso9660
search --set=root --file /live/vmlinuz
set timeout=5
set default=0

menuentry "Start {label} (Live)" {{
    linux /live/vmlinuz boot=live components quiet
    initrd /live/initrd.img
}}
menuentry "{label} (failsafe)" {{
    linux /live/vmlinuz boot=live components nomodeset noapic noapm nosplash
    initrd /live/initrd.img
}}
"""


def _stage_efi_boot(iso_dir: Path, label: str) -> bool:
    """Build a GRUB EFI boot image so the ISO boots on UEFI machines.

    Produces ``EFI/boot/efiboot.img`` (a FAT El Torito image) and a direct
    ``EFI/BOOT/BOOTX64.EFI`` copy. Best-effort: if the host lacks the GRUB EFI
    toolchain or mtools, UEFI boot is skipped and the ISO remains BIOS-bootable.

    Returns True if the EFI image was staged.
    """
    needed = ["grub-mkstandalone", "mkfs.vfat", "mmd", "mcopy"]
    missing = [t for t in needed if shutil.which(t) is None]
    if missing:
        logger.warning("UEFI boot skipped — host missing: {}", ", ".join(missing))
        return False
    if not Path("/usr/lib/grub/x86_64-efi").exists():
        logger.warning("UEFI boot skipped — GRUB x86_64-efi modules not installed on host.")
        return False

    safe_label = label.replace("\n", " ").strip() or "Custom Linux"
    efi_dir = iso_dir / "EFI" / "boot"
    efi_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="archon_efi_") as td:
        tmp = Path(td)
        cfg = tmp / "grub-embed.cfg"
        cfg.write_text(_GRUB_EMBED_CFG.format(label=safe_label), encoding="utf-8")
        bootx64 = tmp / "bootx64.efi"

        result = subprocess.run(
            [
                "grub-mkstandalone",
                "--format=x86_64-efi",
                f"--output={bootx64}",
                "--modules=part_gpt part_msdos fat iso9660 normal linux search "
                "search_fs_file configfile all_video",
                f"boot/grub/grub.cfg={cfg}",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not bootx64.exists():
            logger.warning("grub-mkstandalone failed; UEFI boot skipped:\n{}", result.stderr[:400])
            return False

        # A ~10 MiB FAT image is plenty for a single EFI binary.
        efi_img = efi_dir / "efiboot.img"
        for cmd in (
            ["dd", "if=/dev/zero", f"of={efi_img}", "bs=1M", "count=10", "status=none"],
            ["mkfs.vfat", "-n", "ARCHONEFI", str(efi_img)],
            ["mmd", "-i", str(efi_img), "::/EFI", "::/EFI/BOOT"],
            ["mcopy", "-i", str(efi_img), str(bootx64), "::/EFI/BOOT/BOOTX64.EFI"],
        ):
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                logger.warning("EFI image step {} failed; UEFI boot skipped:\n{}",
                               cmd[0], r.stderr[:300])
                return False

        # Also stage the binary directly for firmware that reads the ISO's EFI dir.
        direct = iso_dir / "EFI" / "BOOT"
        direct.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bootx64, direct / "BOOTX64.EFI")

    logger.info("UEFI GRUB boot image staged at EFI/boot/efiboot.img")
    return True


def prepare_bootloader(iso_dir: Path, label: str = "Custom Linux") -> bool:
    """
    Set up an isolinux bootloader that boots the live SquashFS.

    Locates the system's syslinux installation, copies the required binary and
    module files into ``iso_dir/isolinux/``, and writes a ``boot=live`` menu
    config pointing at the kernel and initrd staged under ``iso_dir/live/`` by
    :func:`archon.distro_builder.live_builder.build_live_layout`.

    Args:
        iso_dir: Staged ISO root (already contains ``live/``); ``isolinux/`` is
            created inside it.
        label: Human-readable name shown in the boot menu.

    Returns:
        True if bootloader setup succeeded.

    Raises:
        FileNotFoundError: If syslinux/isolinux is not installed on the host.
    """
    isolinux_dir = iso_dir / "isolinux"
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

    # Generate isolinux.cfg. ``boot=live`` tells the live-boot initramfs to find
    # and mount /live/filesystem.squashfs off the media — this is what makes the
    # ISO an actual live system rather than an unbootable rootfs dump.
    safe_label = label.replace("\n", " ").strip() or "Custom Linux"
    cfg_content = f"""\
DEFAULT live
PROMPT 0
TIMEOUT 50
MENU TITLE {safe_label} Live Boot Menu

LABEL live
    MENU LABEL Start {safe_label} (Live)
    KERNEL /live/vmlinuz
    APPEND initrd=/live/initrd.img boot=live components quiet

LABEL live-failsafe
    MENU LABEL {safe_label} (failsafe)
    KERNEL /live/vmlinuz
    APPEND initrd=/live/initrd.img boot=live components nomodeset noapic noapm nosplash
"""
    (isolinux_dir / "isolinux.cfg").write_text(cfg_content)
    logger.info("isolinux.cfg (boot=live) written")

    # Best-effort UEFI boot image; BIOS boot works regardless of the outcome.
    _stage_efi_boot(iso_dir, safe_label)

    logger.info("Bootloader prepared successfully")
    return True


# Where syslinux ships the isohybrid MBR boot code that makes the ISO bootable
# when written directly to a USB stick (BIOS mode).
_ISOHDPFX_CANDIDATES = (
    Path("/usr/lib/syslinux/bios/isohdpfx.bin"),
    Path("/usr/lib/ISOLINUX/isohdpfx.bin"),
    Path("/usr/share/syslinux/isohdpfx.bin"),
    Path("/usr/lib/syslinux/isohdpfx.bin"),
)


def _find_isohdpfx() -> Path | None:
    for p in _ISOHDPFX_CANDIDATES:
        if p.exists():
            return p
    return None


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

    work_dir = Path(work_dir)
    isohdpfx = _find_isohdpfx()
    has_efi = (work_dir / "EFI" / "boot" / "efiboot.img").exists()

    # Base ISO 9660 + Rock Ridge + Joliet.
    cmd = ["xorriso", "-as", "mkisofs", "-iso-level", "3", "-R", "-J", "-V", safe_label]

    # isohybrid MBR makes the ISO boot when dd'd to a USB stick in BIOS mode.
    if isohdpfx is not None:
        cmd += ["-isohybrid-mbr", str(isohdpfx)]
    else:
        logger.warning("isohdpfx.bin not found — ISO won't be USB-bootable in BIOS mode.")

    # BIOS El Torito boot via isolinux.
    cmd += [
        "-b", "isolinux/isolinux.bin",
        "-c", "isolinux/boot.cat",
        "-no-emul-boot", "-boot-load-size", "4", "-boot-info-table",
    ]

    # UEFI El Torito boot via the GRUB EFI image, plus a GPT so the same image
    # boots on UEFI machines and from a USB stick.
    if has_efi:
        cmd += [
            "-eltorito-alt-boot",
            "-e", "EFI/boot/efiboot.img",
            "-no-emul-boot",
            "-isohybrid-gpt-basdat",
        ]
    else:
        logger.warning("No EFI boot image present — ISO will be BIOS-only.")

    cmd += ["-o", str(output_iso), str(work_dir)]

    logger.info(f"Assembling ISO ({'BIOS+UEFI' if has_efi else 'BIOS'}): {' '.join(cmd)}")

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
