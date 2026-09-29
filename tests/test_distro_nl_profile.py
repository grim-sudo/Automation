"""Tests for the distro builder's natural-language profile parsing.

Guards that a complicated OS spec (desktop + security hardening + specific
tools) is captured into the DistroProfile, not silently dropped. This is the
NL layer the chatbot reaches when a user asks to "build a custom OS".
"""

from __future__ import annotations

from archon.distro_builder.package_selector import nl_to_profile, resolve_packages


def test_complex_spec_is_captured() -> None:
    profile = nl_to_profile(
        "build a hardened arch linux with a hyprland desktop, wireguard and "
        "apparmor kconfig options, docker, nmap, wireshark, nftables, auditd, "
        "hostname fortress"
    )
    assert profile.base == "arch"
    assert profile.desktop == "hyprland"
    assert profile.hostname == "fortress"

    pkgs = set(profile.packages)
    for expected in {"hyprland", "docker", "nmap", "nftables", "wireguard-tools"}:
        assert expected in pkgs, f"missing package {expected}"

    kconfig = profile.kernel.kconfig_options
    assert kconfig.get("CONFIG_SECURITY_APPARMOR") == "y"
    assert kconfig.get("CONFIG_WIREGUARD") == "m"
    assert kconfig.get("CONFIG_NF_TABLES") == "m"


def test_individual_tool_names_resolve() -> None:
    # Naming a specific tool (not just a group like "network") must pull it in.
    pkgs = resolve_packages("i want nmap and docker", "debian")
    assert "nmap" in pkgs
    assert "docker.io" in pkgs


def test_headless_overrides_desktop() -> None:
    profile = nl_to_profile("minimal debian headless with nginx")
    assert profile.desktop is None
    assert "nginx" in profile.packages


def test_kernel_source_defaults_to_prebuilt() -> None:
    # No kernel-level hints -> reliable distro package.
    profile = nl_to_profile("minimal debian headless with nginx")
    assert profile.kernel.source == "prebuilt"


def test_explicit_custom_kernel_requested() -> None:
    profile = nl_to_profile("debian with a custom kernel and nginx")
    assert profile.kernel.source == "custom"


def test_explicit_prebuilt_beats_kconfig_options() -> None:
    # User explicitly wants the stock kernel; honor it even though apparmor would
    # otherwise imply a source build.
    profile = nl_to_profile("debian with prebuilt kernel and apparmor")
    assert profile.kernel.source == "prebuilt"


def test_kconfig_options_imply_custom_kernel() -> None:
    # Kernel-level options can only be applied to a source build, so they force
    # the custom path even without the word "custom".
    profile = nl_to_profile("debian with apparmor and wireguard")
    assert profile.kernel.kconfig_options
    assert profile.kernel.source == "custom"
