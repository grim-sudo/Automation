"""Live-boot ISO assembly: squashfs the rootfs and stage kernel + initramfs.

A bootable *live* ISO is not just a rootfs on ISO 9660. It needs:

* a SquashFS image of the rootfs at ``live/filesystem.squashfs`` that the
  ``live-boot`` initramfs hooks mount off the media at boot, and
* a kernel + a *matching* initramfs (one that contains those live-boot hooks)
  staged at ``live/vmlinuz`` and ``live/initrd.img``.

The distro's prebuilt kernel package produces both of those in ``/boot`` during
rootfs build. A custom-compiled kernel does not, so :func:`install_custom_kernel`
installs its modules, image, and generates a matching initramfs inside the
chroot before the layout is staged.

Every filesystem-touching command routes through the same privileged runner the
rootfs builders use (root, or an active sudo-escalation session), because the
rootfs is owned by root after debootstrap.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

from loguru import logger

from .rootfs_builder import _run_logged

__all__ = [
    "kernel_release",
    "install_custom_kernel",
    "build_live_layout",
]


def _invoking_user_ids() -> tuple[int, int]:
    """(uid, gid) to hand build artifacts back to, never root.

    Under ``sudo`` the original user is in ``SUDO_UID``/``SUDO_GID``. When Archon
    runs unprivileged and escalates individual commands, the current process ids
    are already the invoking user's.
    """
    sudo_uid = os.environ.get("SUDO_UID")
    sudo_gid = os.environ.get("SUDO_GID")
    if sudo_uid and sudo_gid:
        return int(sudo_uid), int(sudo_gid)
    return os.getuid(), os.getgid()


def kernel_release(kernel_dir: Path) -> str:
    """Return the kernel's release string (e.g. ``7.2.8-custom``) via ``make``.

    Runs unprivileged: the extracted source tree is owned by the invoking user.
    """
    result = subprocess.run(
        ["make", "-s", "kernelrelease"],
        cwd=str(kernel_dir.resolve()),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"could not determine kernel release:\n{result.stderr}")
    return result.stdout.strip().splitlines()[-1].strip()


async def install_custom_kernel(kernel_dir: Path, rootfs_path: Path) -> str:
    """Install a compiled-from-source kernel into *rootfs_path* and build its initramfs.

    Copies modules and the kernel image into the rootfs, then runs
    ``update-initramfs`` in the chroot so the generated initrd carries the
    live-boot hooks for this exact kernel version.

    Args:
        kernel_dir:  Built kernel source root (``make bzImage modules`` already ran).
        rootfs_path: Populated rootfs (root-owned) with live-boot installed.

    Returns:
        The kernel release string, so the caller can locate the staged files.

    Raises:
        RuntimeError: If a required privileged step fails.
    """
    kernel_dir = kernel_dir.resolve()
    rootfs_path = rootfs_path.resolve()
    release = kernel_release(kernel_dir)
    logger.info("Installing custom kernel {} into rootfs", release)

    # Modules first (into /lib/modules/<release>), then the kernel image and its
    # metadata so update-initramfs can build against a complete /boot.
    ok, out = await asyncio.to_thread(
        _run_logged,
        ["make", f"INSTALL_MOD_PATH={rootfs_path}", "modules_install"],
        str(kernel_dir),
    )
    if not ok:
        raise RuntimeError(f"kernel modules_install failed:\n{out[-500:]}")

    bzimage = kernel_dir / "arch" / "x86" / "boot" / "bzImage"
    if not bzimage.exists():
        raise RuntimeError(f"compiled kernel image not found at {bzimage}")
    boot = rootfs_path / "boot"
    copies = [
        (bzimage, boot / f"vmlinuz-{release}"),
        (kernel_dir / "System.map", boot / f"System.map-{release}"),
        (kernel_dir / ".config", boot / f"config-{release}"),
    ]
    for src, dst in copies:
        if src.exists():
            ok, out = await asyncio.to_thread(_run_logged, ["cp", str(src), str(dst)])
            if not ok:
                raise RuntimeError(f"failed to copy {src.name} into rootfs:\n{out[-300:]}")

    # Generate the live-capable initramfs for this exact kernel version.
    ok, out = await asyncio.to_thread(
        _run_logged,
        ["chroot", str(rootfs_path), "update-initramfs", "-c", "-k", release],
    )
    if not ok:
        raise RuntimeError(f"update-initramfs failed for {release}:\n{out[-500:]}")

    logger.info("Custom kernel {} installed with matching initramfs", release)
    return release


def _pick_boot_file(boot_dir: Path, stem: str) -> Path | None:
    """Return the highest-versioned ``<stem>-*`` (or bare ``<stem>``) in *boot_dir*."""
    exact = boot_dir / stem
    if exact.exists() and not exact.is_symlink():
        return exact
    if exact.is_symlink():
        target = exact.resolve()
        if target.exists():
            return target
    matches = sorted(p for p in boot_dir.glob(f"{stem}-*") if not p.name.endswith(".old"))
    return matches[-1] if matches else None


async def build_live_layout(rootfs_path: Path, work_dir: Path) -> Path:
    """SquashFS the rootfs and stage kernel + initrd into an ISO tree.

    Produces ``<work_dir>/iso/live/{filesystem.squashfs,vmlinuz,initrd.img}`` and
    hands the whole ``iso`` tree back to the invoking user so the unprivileged
    xorriso step can read it and the final ISO is not root-owned.

    Args:
        rootfs_path: Populated, root-owned rootfs directory.
        work_dir:    Build scratch directory (user-owned).

    Returns:
        Path to the staged ISO root directory (contains ``live/``).

    Raises:
        RuntimeError: If squashfs creation fails or no kernel/initrd is present.
    """
    rootfs_path = rootfs_path.resolve()
    iso_dir = (work_dir / "iso").resolve()
    live_dir = iso_dir / "live"
    live_dir.mkdir(parents=True, exist_ok=True)

    # SquashFS via the privileged runner so root-owned rootfs files are readable
    # and their ownership/permissions are preserved inside the image.
    squashfs = live_dir / "filesystem.squashfs"
    if squashfs.exists():
        squashfs.unlink()
    logger.info("Compressing rootfs into {}", squashfs)
    ok, out = await asyncio.to_thread(
        _run_logged,
        ["mksquashfs", str(rootfs_path), str(squashfs), "-noappend", "-e", "boot"],
    )
    if not ok:
        raise RuntimeError(f"mksquashfs failed:\n{out[-500:]}")

    # Stage the kernel and its matching initramfs from the rootfs /boot.
    boot = rootfs_path / "boot"
    vmlinuz = _pick_boot_file(boot, "vmlinuz")
    initrd = _pick_boot_file(boot, "initrd.img")
    if vmlinuz is None or initrd is None:
        raise RuntimeError(
            f"no bootable kernel/initrd found in {boot} "
            f"(vmlinuz={vmlinuz}, initrd={initrd}); the live ISO cannot boot"
        )
    for src, name in ((vmlinuz, "vmlinuz"), (initrd, "initrd.img")):
        ok, out = await asyncio.to_thread(
            _run_logged, ["cp", str(src), str(live_dir / name)]
        )
        if not ok:
            raise RuntimeError(f"failed to stage {name}:\n{out[-300:]}")
        logger.info("Staged {} -> live/{}", src.name, name)

    # Hand the staged tree back to the invoking user (squashfs is root-owned).
    uid, gid = _invoking_user_ids()
    await asyncio.to_thread(
        _run_logged, ["chown", "-R", f"{uid}:{gid}", str(iso_dir)]
    )

    return iso_dir
