"""Tests for natural-language package/profile resolution.

The key regression: a "cybersecurity" build request must actually select the
security toolset (and flag the Kali repo), instead of matching only the generic
"security" keyword and producing a bare live ISO with ufw/fail2ban/apparmor.
"""

from __future__ import annotations

from archon.distro_builder.package_selector import nl_to_profile, resolve_packages


def test_cybersecurity_request_selects_real_tools_and_enables_kali():
    profile = nl_to_profile(
        "make an operating system for cybersecurity with pentesting and blue teaming "
        "tools along with spoofing"
    )
    pkgs = set(profile.packages)
    # Pentest, blue-team, and spoofing tools all made it in.
    assert {"nmap", "metasploit-framework", "wireshark"} <= pkgs
    assert {"snort", "suricata"} <= pkgs
    assert {"macchanger", "tor"} <= pkgs
    # A Debian security build must enable the Kali repo for the non-Debian tools.
    assert profile.base == "debian"
    assert profile.kali_repo is True


def test_plain_request_does_not_enable_kali():
    profile = nl_to_profile("minimal debian with nginx")
    assert profile.kali_repo is False
    assert "nginx" in profile.packages


def test_resolve_packages_dedupes_overlapping_groups():
    # "cybersecurity" contains "security"; overlapping packages must appear once.
    pkgs = resolve_packages("a cybersecurity build", "debian")
    assert pkgs.count("apparmor") == 1
    assert "nmap" in pkgs


def test_new_compositors_are_selectable():
    # A tiling-WM request pulls the compositor's package group.
    prof = nl_to_profile("arch with i3 tiling window manager")
    assert prof.desktop == "i3"
    assert "i3-wm" in prof.packages
    prof2 = nl_to_profile("debian with the budgie desktop")
    assert prof2.desktop == "budgie"
    assert "budgie-desktop" in prof2.packages


def test_omarchy_implies_arch_hyprland_and_userland():
    prof = nl_to_profile("build me an omarchy setup")
    assert prof.base == "arch"
    assert prof.desktop == "hyprland"
    # Hyprland group + curated omarchy userland.
    assert "hyprland" in prof.packages
    assert "hyprlock" in prof.packages
    assert prof.name == "archon-omarchy"


def test_kernel_flavor_detection():
    # Performance kernels only resolve on Arch; Debian falls back to standard.
    assert nl_to_profile("arch with the cachy kernel").kernel.flavor == "cachyos"
    assert nl_to_profile("arch gaming build").kernel.flavor == "zen"
    assert nl_to_profile("arch with a hardened kernel").kernel.flavor == "hardened"
    assert nl_to_profile("arch lts kernel server").kernel.flavor == "lts"
    # Debian can't ship cachy/zen/lts variants → standard.
    assert nl_to_profile("debian with the cachy kernel").kernel.flavor == "standard"
    # A Debian security build gets Kali's kernel line.
    assert nl_to_profile("debian cybersecurity distro").kernel.flavor == "kali"


def test_descriptive_naming():
    assert nl_to_profile("a cybersecurity os").name == "archon-secops-debian"
    assert nl_to_profile("arch development workstation").name == "archon-devbox-arch"
    # No recognizable intent → plain base name.
    assert nl_to_profile("plain debian").name == "archon-debian"
