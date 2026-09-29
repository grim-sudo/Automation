"""Natural language package resolution for distro builder profiles."""

from __future__ import annotations

from typing import Literal

from loguru import logger

from archon.distro_builder.models import DistroProfile

PACKAGE_MAP: dict[str, dict[str, list[str]]] = {
    "debian": {
        "web server": ["nginx"],
        "nginx": ["nginx"],
        "apache": ["apache2"],
        "database": ["postgresql"],
        "mysql": ["mysql-server"],
        "mariadb": ["mariadb-server"],
        "gui": ["xorg", "lightdm", "xterm"],
        "kde": ["kde-plasma-desktop", "sddm"],
        "gnome": ["gnome-core", "gdm3"],
        "xfce": ["xfce4", "lightdm"],
        "lxde": ["lxde", "lightdm"],
        "lxqt": ["lxqt", "sddm"],
        "mate": ["mate-desktop-environment", "lightdm"],
        "cinnamon": ["cinnamon-desktop-environment", "lightdm"],
        "hyprland": ["hyprland", "waybar", "wofi"],
        "sway": ["sway", "swaybg", "waybar"],
        "development": ["build-essential", "git", "python3", "python3-pip", "cmake"],
        "gaming": ["steam", "wine", "lutris"],
        "audio workstation": ["jackd2", "ardour", "hydrogen", "qjackctl"],
        "docker": ["docker.io", "docker-compose"],
        "podman": ["podman"],
        "kubernetes": ["kubectl", "helm"],
        "virtualization": ["qemu-kvm", "libvirt-daemon-system", "virt-manager"],
        "security": ["ufw", "fail2ban", "apparmor"],
        "apparmor": ["apparmor", "apparmor-utils"],
        "auditd": ["auditd"],
        "nftables": ["nftables"],
        "iptables": ["iptables"],
        "wireguard": ["wireguard-tools"],
        "nmap": ["nmap"],
        "wireshark": ["wireshark"],
        "tcpdump": ["tcpdump"],
        "media": ["vlc", "ffmpeg", "imagemagick"],
        "office": ["libreoffice"],
        "minimal": [],
        "editor": ["vim", "nano", "emacs"],
        "network": ["nmap", "wireshark", "tcpdump", "netcat"],
        "python": ["python3", "python3-pip", "python3-venv"],
        "nodejs": ["nodejs", "npm"],
        "java": ["default-jdk"],
        "rust": ["rustc", "cargo"],
        "go": ["golang"],
    },
    "arch": {
        "web server": ["nginx"],
        "nginx": ["nginx"],
        "apache": ["apache"],
        "database": ["postgresql"],
        "mysql": ["mariadb"],
        "mariadb": ["mariadb"],
        "gui": ["xorg-server", "lightdm", "xterm"],
        "kde": ["plasma", "sddm", "kde-applications"],
        "gnome": ["gnome", "gdm"],
        "xfce": ["xfce4", "lightdm"],
        "lxde": ["lxde", "lightdm"],
        "lxqt": ["lxqt", "sddm"],
        "mate": ["mate", "lightdm"],
        "cinnamon": ["cinnamon", "lightdm"],
        "hyprland": ["hyprland", "waybar", "wofi"],
        "sway": ["sway", "swaybg", "waybar"],
        "development": ["base-devel", "git", "python", "python-pip", "cmake"],
        "gaming": ["steam", "wine", "lutris"],
        "audio workstation": ["jack2", "ardour", "hydrogen"],
        "docker": ["docker", "docker-compose"],
        "podman": ["podman"],
        "kubernetes": ["kubectl", "helm"],
        "virtualization": ["qemu", "libvirt", "virt-manager"],
        "security": ["ufw", "fail2ban", "apparmor"],
        "apparmor": ["apparmor"],
        "auditd": ["audit"],
        "nftables": ["nftables"],
        "iptables": ["iptables"],
        "wireguard": ["wireguard-tools"],
        "nmap": ["nmap"],
        "wireshark": ["wireshark-qt"],
        "tcpdump": ["tcpdump"],
        "media": ["vlc", "ffmpeg", "imagemagick"],
        "office": ["libreoffice-fresh"],
        "minimal": [],
        "editor": ["vim", "nano", "emacs"],
        "network": ["nmap", "wireshark-qt", "tcpdump", "openbsd-netcat"],
        "python": ["python", "python-pip"],
        "nodejs": ["nodejs", "npm"],
        "java": ["jdk-openjdk"],
        "rust": ["rust"],
        "go": ["go"],
    },
    "unix": {
        "web server": ["BR2_PACKAGE_NGINX=y"],
        "database": ["BR2_PACKAGE_SQLITE=y"],
        "development": [
            "BR2_PACKAGE_GCC_FINAL=y",
            "BR2_PACKAGE_MAKE=y",
            "BR2_PACKAGE_PYTHON3=y",
        ],
        "network": ["BR2_PACKAGE_NMAP=y", "BR2_PACKAGE_TCPDUMP=y"],
        "minimal": [],
        "editor": ["BR2_PACKAGE_VIM=y"],
        "media": ["BR2_PACKAGE_FFMPEG=y"],
    },
}


def resolve_packages(description: str, base: str) -> list[str]:
    """
    Resolve a natural language package description to actual package names.

    Performs case-insensitive substring matching of known keywords from
    PACKAGE_MAP against the provided description string.

    Args:
        description: Natural language description, e.g. "web server and development tools".
        base: Distro base identifier: "debian", "arch", or "unix".

    Returns:
        Deduplicated list of package names appropriate for the given base distro,
        preserving the order in which keywords were encountered.
    """
    desc_lower = description.lower()
    base_map = PACKAGE_MAP.get(base, {})
    packages: list[str] = []

    for keyword, pkgs in base_map.items():
        if keyword in desc_lower:
            packages.extend(pkgs)

    # Deduplicate while preserving insertion order
    seen: set[str] = set()
    result: list[str] = []
    for pkg in packages:
        if pkg not in seen:
            seen.add(pkg)
            result.append(pkg)

    return result


def nl_to_profile(nl_command: str) -> DistroProfile:
    """
    Parse a natural language distro description into a DistroProfile.

    Detects the target base distro, optional desktop environment, hostname,
    packages, and kernel config flags from free-form text.

    Args:
        nl_command: Natural language build description, e.g.
            "build minimal debian iso with nginx and no GUI"

    Returns:
        A DistroProfile constructed from the parsed command.

    Examples:
        "minimal arch with KDE"
            -> DistroProfile(base="arch", desktop="kde", ...)
        "debian with nginx and postgres"
            -> DistroProfile(base="debian", packages=["nginx", "postgresql"])
        "minimal unix headless"
            -> DistroProfile(base="unix", desktop=None, ...)
    """
    import re

    from .models import DistroProfile, KernelConfig

    nl_lower = nl_command.lower()

    # Detect base distro
    base: Literal["debian", "arch", "unix"] = "debian"
    if "arch" in nl_lower:
        base = "arch"
    elif "buildroot" in nl_lower or "minimal unix" in nl_lower or "unix" in nl_lower:
        base = "unix"

    # Detect desktop environment
    desktop: str | None = None
    for de in ["kde", "gnome", "xfce", "lxqt", "lxde", "mate", "cinnamon", "hyprland", "sway"]:
        if de in nl_lower:
            desktop = de
            break
    # Headless / server / no GUI overrides any desktop detection
    if "no gui" in nl_lower or "headless" in nl_lower or "server" in nl_lower:
        desktop = None

    # Detect explicit hostname directive
    hostname_match = re.search(r"hostname[:\s]+([a-zA-Z0-9-]+)", nl_lower)
    hostname = hostname_match.group(1) if hostname_match else f"{base}-custom"

    # Resolve packages from description text
    packages = resolve_packages(nl_command, base)

    # If a desktop was detected, pull its package group in as well
    if desktop and base in PACKAGE_MAP:
        for pkg in PACKAGE_MAP[base].get(desktop, []):
            if pkg not in packages:
                packages.append(pkg)

    # Detect kernel-level config hints
    kconfig: dict[str, str] = {}
    if "kvm" in nl_lower:
        kconfig["CONFIG_KVM"] = "y"
    if "modules" in nl_lower:
        kconfig["CONFIG_MODULES"] = "y"
    if "apparmor" in nl_lower:
        kconfig["CONFIG_SECURITY_APPARMOR"] = "y"
    if "selinux" in nl_lower:
        kconfig["CONFIG_SECURITY_SELINUX"] = "y"
    if "wireguard" in nl_lower:
        kconfig["CONFIG_WIREGUARD"] = "m"
    if "nftables" in nl_lower or "netfilter" in nl_lower:
        kconfig["CONFIG_NF_TABLES"] = "m"
    if "audit" in nl_lower:
        kconfig["CONFIG_AUDIT"] = "y"

    # Decide which kernel Archon builds around, driven by the request itself:
    #   * explicit "custom/compiled/from-source/hardened kernel" -> compile from source
    #   * explicit "prebuilt/stock/distro/packaged kernel"       -> distro kernel package
    #   * otherwise default to the reliable prebuilt package, UNLESS kernel-level
    #     kconfig options were requested — those can only be applied to a source
    #     build, so they imply a custom kernel.
    source = _detect_kernel_source(nl_lower, has_kconfig=bool(kconfig))

    logger.debug(
        f"nl_to_profile: base={base} desktop={desktop} kernel_source={source} "
        f"hostname={hostname} packages={packages} kconfig={kconfig}"
    )

    return DistroProfile(
        name=f"custom-{base}",
        base=base,
        kernel=KernelConfig(version="latest-stable", source=source, kconfig_options=kconfig),
        packages=list(dict.fromkeys(packages)),  # dedupe, preserve order
        hostname=hostname,
        desktop=desktop,
    )


_CUSTOM_KERNEL_HINTS = (
    "custom kernel",
    "custom-compiled kernel",
    "compile kernel",
    "compiled kernel",
    "kernel from source",
    "from-source kernel",
    "build kernel",
    "hardened kernel",
)
_PREBUILT_KERNEL_HINTS = (
    "prebuilt kernel",
    "pre-built kernel",
    "prebuilt",
    "stock kernel",
    "distro kernel",
    "packaged kernel",
    "package kernel",
)


def _detect_kernel_source(nl_lower: str, has_kconfig: bool) -> Literal["prebuilt", "custom"]:
    """Choose the kernel source from the user's phrasing (explicit wins over default).

    Explicit "custom"/"prebuilt" language in the request takes precedence. With no
    explicit signal we default to the distro's prebuilt package because it boots
    reliably; the one exception is a request that carries kernel-level kconfig
    options, which are only applicable to a source build and therefore imply custom.
    """
    if any(h in nl_lower for h in _CUSTOM_KERNEL_HINTS):
        return "custom"
    if any(h in nl_lower for h in _PREBUILT_KERNEL_HINTS):
        return "prebuilt"
    return "custom" if has_kconfig else "prebuilt"
