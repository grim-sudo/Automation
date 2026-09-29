"""Regression tests for privileged file writes into a root-owned rootfs.

debootstrap/pacstrap create the rootfs owned by root. Config files (hostname,
timezone, locale) were once written with a plain ``Path.write_text`` from the
unprivileged build process, which raised ``[Errno 13] Permission denied:
.../rootfs/etc/hostname`` mid-build. These lock in that every such write is
routed through the privileged runner instead.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from archon.distro_builder import rootfs_builder as rb
from archon.distro_builder.models import DistroProfile, KernelConfig


def test_install_file_stages_to_tmp_and_runs_install(monkeypatch):
    recorded: list[list[str]] = []
    seen_content: dict[str, str] = {}

    def fake_run_logged(cmd, cwd=None, env=None):
        recorded.append(cmd)
        # The staged temp file must hold the content at call time (before unlink).
        if cmd and cmd[0] == "install":
            seen_content["content"] = Path(cmd[-2]).read_text(encoding="utf-8")
        return True, ""

    monkeypatch.setattr(rb, "_run_logged", fake_run_logged)

    ok, _ = rb._install_file("myhost\n", Path("/tmp/does-not-matter/etc/hostname"))

    assert ok is True
    assert recorded and recorded[0][0] == "install"
    assert recorded[0][1:3] == ["-m", "0644"]
    assert recorded[0][-1].endswith("etc/hostname")
    assert seen_content["content"] == "myhost\n"
    # Temp file is cleaned up regardless.
    assert not Path(recorded[0][-2]).exists()


def test_debian_rootfs_writes_config_through_privileged_runner(tmp_path, monkeypatch):
    commands: list[list[str]] = []

    def fake_run_logged(cmd, cwd=None, env=None):
        commands.append(cmd)
        return True, ""

    # Not root, but pretend escalation is available so the builder proceeds.
    monkeypatch.setattr(rb, "_require_root", lambda *_a, **_k: None)
    monkeypatch.setattr(rb, "_run_logged", fake_run_logged)
    # Don't hit the network probing mirrors during the orchestration test.
    monkeypatch.setattr(
        rb, "_select_debian_mirror", lambda *_a, **_k: "http://deb.debian.org/debian"
    )

    profile = DistroProfile(
        name="secos",
        base_distro="debian",
        hostname="secos-host",
        packages=[],
        kernel=KernelConfig(source="prebuilt"),
    )
    rootfs = tmp_path / "rootfs"
    # Seed an initrd so the prebuilt-kernel bootability check passes; this test
    # is about config-write routing, not initramfs generation.
    (rootfs / "boot").mkdir(parents=True)
    (rootfs / "boot" / "initrd.img-6.1.0-test").write_text("x", encoding="utf-8")

    ok = asyncio.run(rb.build_debian_rootfs(profile, rootfs))
    assert ok is True

    installs = [c for c in commands if c and c[0] == "install"]
    dests = [c[-1] for c in installs]
    # hostname, timezone, and locale.gen all written via install(1), never a
    # direct Path.write_text into the root-owned tree.
    assert any(d.endswith("etc/hostname") for d in dests)
    assert any(d.endswith("etc/timezone") for d in dests)
    assert any(d.endswith("etc/locale.gen") for d in dests)

    # And the config files must NOT have been written directly to disk (which,
    # against a real root-owned rootfs, would be the permission-denied bug).
    assert not (rootfs / "etc" / "hostname").exists()


def test_select_mirror_returns_explicit_url_untouched():
    # An explicit URL must be honored verbatim — no probing, no override.
    url = "http://my.local.mirror/debian"
    assert rb._select_debian_mirror(url, "bookworm") == url


def test_select_mirror_auto_picks_fastest(monkeypatch):
    import time

    import httpx

    # Each candidate "responds" after a real (tiny) delay proportional to its
    # rank, so the measured monotonic timing is deterministic without patching
    # the clock across probe threads. Fastest wins.
    delays = {
        "http://deb.debian.org/debian": 0.06,
        "http://ftp.us.debian.org/debian": 0.01,  # fastest
        "http://ftp.uk.debian.org/debian": 0.12,
    }
    monkeypatch.setattr(rb, "_DEBIAN_MIRROR_CANDIDATES", tuple(delays), raising=True)

    def fake_get(self, url, **kwargs):
        base = url.split("/dists/")[0]
        time.sleep(delays[base])
        return httpx.Response(200)

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    chosen = rb._select_debian_mirror("auto", "bookworm")
    assert chosen == "http://ftp.us.debian.org/debian"


def test_select_mirror_falls_back_when_all_fail(monkeypatch):
    import httpx

    def always_fail(self, url, **kwargs):
        raise httpx.ConnectError("unreachable")

    monkeypatch.setattr(httpx.Client, "get", always_fail)
    assert rb._select_debian_mirror("auto", "bookworm") == rb._DEFAULT_DEBIAN_MIRROR


def test_debian_rootfs_fails_when_no_initrd_produced(tmp_path, monkeypatch):
    # The build must refuse (not silently succeed) when the prebuilt-kernel path
    # produces no initramfs — that was the "initrd=None, live ISO cannot boot"
    # failure surfacing 200s too late in the live layout step.
    monkeypatch.setattr(rb, "_require_root", lambda *_a, **_k: None)
    monkeypatch.setattr(rb, "_run_logged", lambda *_a, **_k: (True, ""))
    monkeypatch.setattr(
        rb, "_select_debian_mirror", lambda *_a, **_k: "http://deb.debian.org/debian"
    )

    profile = DistroProfile(
        name="secos",
        base_distro="debian",
        hostname="secos-host",
        packages=[],
        kernel=KernelConfig(source="prebuilt"),
    )
    # No /boot/initrd.img-* seeded → verification must fail the build.
    assert asyncio.run(rb.build_debian_rootfs(profile, tmp_path / "rootfs")) is False


def test_debian_rootfs_binds_and_regenerates_initramfs(tmp_path, monkeypatch):
    commands: list[list[str]] = []

    def fake_run_logged(cmd, cwd=None, env=None):
        commands.append(cmd)
        return True, ""

    monkeypatch.setattr(rb, "_require_root", lambda *_a, **_k: None)
    monkeypatch.setattr(rb, "_run_logged", fake_run_logged)
    monkeypatch.setattr(
        rb, "_select_debian_mirror", lambda *_a, **_k: "http://deb.debian.org/debian"
    )

    profile = DistroProfile(
        name="secos",
        base_distro="debian",
        hostname="secos-host",
        packages=[],
        kernel=KernelConfig(source="prebuilt"),
    )
    rootfs = tmp_path / "rootfs"
    (rootfs / "boot").mkdir(parents=True)
    (rootfs / "boot" / "initrd.img-6.1.0-test").write_text("x", encoding="utf-8")

    assert asyncio.run(rb.build_debian_rootfs(profile, rootfs)) is True

    firsts = [c[0] for c in commands]
    # /proc, /sys, /dev bound before apt, and unmounted afterwards.
    assert firsts.count("mount") == len(rb._CHROOT_BINDS)
    assert firsts.count("umount") == len(rb._CHROOT_BINDS)
    # initramfs regenerated in-chroot after live-boot is installed.
    assert any(
        c[0] == "chroot" and "update-initramfs" in " ".join(c) for c in commands
    )
    # Mounts torn down before the (later) squashfs step — the last mount-family
    # command must be a umount, never a leftover mount.
    mount_family = [c[0] for c in commands if c[0] in ("mount", "umount")]
    assert mount_family[-1] == "umount"
