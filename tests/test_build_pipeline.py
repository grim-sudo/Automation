"""Regression tests for the distro build pipeline orchestration.

Two properties are locked in here:

* The rootfs builder is an async coroutine and MUST be awaited directly. It was
  once dispatched via ``asyncio.to_thread(...)``, which only creates a
  never-awaited coroutine — the rootfs step silently did nothing and every build
  produced an empty ~1.6 MB ISO while reporting success.
* The kernel-source branch is honored: a ``prebuilt`` profile skips the
  from-source compile entirely, while a ``custom`` profile compiles the kernel
  and installs it (plus a matching initramfs) into the rootfs.

The heavy stages (debootstrap, mksquashfs, chroot, xorriso) require root and
network, so they are mocked; these tests exercise orchestration, not real I/O.
"""

from __future__ import annotations

import asyncio

from archon.distro_builder import build_pipeline
from archon.distro_builder.models import DistroProfile, KernelConfig


def _patch_common(monkeypatch, tmp_path, calls):
    """Install fakes for every stage and record which ones fire."""

    async def fake_fetch_version() -> str:
        calls["fetch"] = True
        return "7.2.8"

    async def fake_download(version, dest_dir):
        calls["download"] = True
        d = tmp_path / f"linux-{version}"
        d.mkdir(exist_ok=True)
        return d

    def fake_build_kernel(kernel_dir, config_path, jobs):
        calls["build_kernel"] = True
        return True, "ok"

    async def fake_build_debian_rootfs(prof, rootfs_path):
        calls["rootfs"] = True
        rootfs_path.mkdir(parents=True, exist_ok=True)
        return True

    async def fake_install_custom_kernel(kernel_dir, rootfs_path):
        calls["install_custom"] = True
        return "7.2.8-custom"

    async def fake_build_live_layout(rootfs_path, work_dir):
        calls["live_layout"] = True
        iso_dir = work_dir / "iso"
        (iso_dir / "live").mkdir(parents=True, exist_ok=True)
        return iso_dir

    def fake_prepare_bootloader(iso_dir, label="Custom Linux"):
        calls["bootloader"] = True
        return True

    def fake_assemble_iso(iso_dir, output_iso, label="CUSTOM"):
        calls["assemble"] = True
        output_iso.write_bytes(b"iso-bytes")
        return True

    def fake_verify_iso(iso_path):
        return True

    monkeypatch.setattr(build_pipeline, "fetch_latest_stable_version", fake_fetch_version)
    monkeypatch.setattr(build_pipeline, "download_kernel", fake_download)
    monkeypatch.setattr(build_pipeline, "build_kernel", fake_build_kernel)
    monkeypatch.setattr(build_pipeline, "build_debian_rootfs", fake_build_debian_rootfs)
    monkeypatch.setattr(build_pipeline, "install_custom_kernel", fake_install_custom_kernel)
    monkeypatch.setattr(build_pipeline, "build_live_layout", fake_build_live_layout)
    monkeypatch.setattr(build_pipeline, "prepare_bootloader", fake_prepare_bootloader)
    monkeypatch.setattr(build_pipeline, "assemble_iso", fake_assemble_iso)
    monkeypatch.setattr(build_pipeline, "verify_iso", fake_verify_iso)


def _run(profile, tmp_path):
    return asyncio.run(
        build_pipeline.build_distro(profile, tmp_path / "out", work_dir=tmp_path / "wd")
    )


def test_prebuilt_kernel_skips_source_compile(tmp_path, monkeypatch):
    calls: dict[str, bool] = {}
    _patch_common(monkeypatch, tmp_path, calls)

    profile = DistroProfile(base="debian", kernel=KernelConfig(source="prebuilt"))
    result = _run(profile, tmp_path)

    assert result.success is True
    # Prebuilt path never touches the from-source compile stages …
    assert "fetch" not in calls
    assert "download" not in calls
    assert "build_kernel" not in calls
    assert "install_custom" not in calls
    # … but does build the rootfs and the live SquashFS layout.
    assert calls["rootfs"] is True
    assert calls["live_layout"] is True
    assert calls["assemble"] is True


def test_custom_kernel_compiles_and_installs(tmp_path, monkeypatch):
    calls: dict[str, bool] = {}
    _patch_common(monkeypatch, tmp_path, calls)

    profile = DistroProfile(base="debian", kernel=KernelConfig(source="custom"))
    result = _run(profile, tmp_path)

    assert result.success is True
    assert calls["fetch"] is True
    assert calls["download"] is True
    assert calls["build_kernel"] is True
    assert calls["rootfs"] is True
    assert calls["install_custom"] is True
    assert calls["live_layout"] is True


def test_rootfs_builder_is_actually_awaited(tmp_path, monkeypatch):
    # If build_debian_rootfs were wrapped in asyncio.to_thread (the old bug) the
    # coroutine would never run and this flag would stay False.
    calls: dict[str, bool] = {}
    _patch_common(monkeypatch, tmp_path, calls)

    profile = DistroProfile(base="debian", kernel=KernelConfig(source="prebuilt"))
    result = _run(profile, tmp_path)

    assert calls.get("rootfs") is True, "rootfs builder coroutine was never awaited"
    assert result.success is True


def test_rootfs_failure_fails_the_build(tmp_path, monkeypatch):
    calls: dict[str, bool] = {}
    _patch_common(monkeypatch, tmp_path, calls)

    async def failing_rootfs(prof, rootfs_path):
        return False

    monkeypatch.setattr(build_pipeline, "build_debian_rootfs", failing_rootfs)

    profile = DistroProfile(base="debian", kernel=KernelConfig(source="prebuilt"))
    result = _run(profile, tmp_path)

    assert result.success is False
    assert "rootfs" in (result.error_message or "")


def test_non_debian_base_fails_clearly(tmp_path, monkeypatch):
    calls: dict[str, bool] = {}
    _patch_common(monkeypatch, tmp_path, calls)

    profile = DistroProfile(base="arch", kernel=KernelConfig(source="prebuilt"))
    result = _run(profile, tmp_path)

    assert result.success is False
    assert "debian" in (result.error_message or "").lower()
    assert "rootfs" not in calls
