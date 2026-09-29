"""Tests for hybrid BIOS+UEFI ISO assembly command construction.

The privileged/real xorriso run is not exercised here; these lock in that the
command is built for a USB-bootable hybrid ISO (isohybrid MBR + UEFI alt-boot)
when the pieces are present, and degrades cleanly when they are not.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from archon.distro_builder import iso_assembler as ia


def _fake_run_capture(recorded):
    def _run(cmd, capture_output=True, text=True):
        recorded.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    return _run


def test_assemble_iso_builds_hybrid_bios_uefi_command(tmp_path, monkeypatch):
    work = tmp_path / "iso"
    (work / "isolinux").mkdir(parents=True)
    (work / "isolinux" / "isolinux.bin").write_text("x")
    # Pretend an EFI boot image was staged.
    (work / "EFI" / "boot").mkdir(parents=True)
    (work / "EFI" / "boot" / "efiboot.img").write_text("x")

    monkeypatch.setattr(ia.shutil, "which", lambda _n: "/usr/bin/xorriso")
    monkeypatch.setattr(ia, "_find_isohdpfx", lambda: Path("/usr/lib/syslinux/bios/isohdpfx.bin"))
    recorded: list[list[str]] = []
    monkeypatch.setattr(ia.subprocess, "run", _fake_run_capture(recorded))

    assert ia.assemble_iso(work, tmp_path / "out.iso", "SECOS") is True

    cmd = " ".join(recorded[0])
    assert "-isohybrid-mbr" in cmd  # USB-bootable in BIOS mode
    assert "isolinux/isolinux.bin" in cmd  # BIOS El Torito
    assert "-eltorito-alt-boot" in cmd and "EFI/boot/efiboot.img" in cmd  # UEFI
    assert "-isohybrid-gpt-basdat" in cmd  # GPT for UEFI USB


def test_assemble_iso_degrades_to_bios_only_without_efi(tmp_path, monkeypatch):
    work = tmp_path / "iso"
    (work / "isolinux").mkdir(parents=True)
    (work / "isolinux" / "isolinux.bin").write_text("x")
    # No EFI image staged.

    monkeypatch.setattr(ia.shutil, "which", lambda _n: "/usr/bin/xorriso")
    monkeypatch.setattr(ia, "_find_isohdpfx", lambda: Path("/usr/lib/syslinux/bios/isohdpfx.bin"))
    recorded: list[list[str]] = []
    monkeypatch.setattr(ia.subprocess, "run", _fake_run_capture(recorded))

    assert ia.assemble_iso(work, tmp_path / "out.iso", "SECOS") is True

    cmd = " ".join(recorded[0])
    assert "isolinux/isolinux.bin" in cmd
    assert "-eltorito-alt-boot" not in cmd  # no UEFI when no EFI image
