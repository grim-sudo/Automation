"""Natural language package resolution for distro builder profiles."""

from __future__ import annotations

from typing import Literal

from loguru import logger

from archon.distro_builder.models import DistroProfile

# Cybersecurity tool groups (Debian/Kali package names). These are installed
# resiliently — a name missing from the enabled repos is skipped, not fatal —
# and the heavy hitters (metasploit-framework, burpsuite, veracrypt) come from
# the Kali repo layered on the Debian base when a security build is requested.
_PENTEST_TOOLS = [
    "nmap", "masscan", "wireshark", "tcpdump", "netcat-traditional",
    "hydra", "john", "hashcat", "sqlmap", "nikto", "aircrack-ng",
    "dnsutils", "dnsrecon", "whatweb", "dirb", "gobuster", "wfuzz",
    "wpscan", "enum4linux", "metasploit-framework", "burpsuite",
]
_BLUETEAM_TOOLS = [
    "auditd", "rsyslog", "snort", "suricata", "fail2ban", "aide",
    "rkhunter", "chkrootkit", "clamav", "osquery",
]
_FORENSICS_TOOLS = [
    "sleuthkit", "autopsy", "foremost", "testdisk", "binwalk",
    "gddrescue", "volatility3", "yara",
]
_SPOOFING_TOOLS = [
    "macchanger", "ettercap-text-only", "dsniff", "bettercap",
    "tor", "openvpn", "proxychains4", "wireguard-tools",
]
_HARDENING_TOOLS = [
    "apparmor", "apparmor-utils", "ufw", "fail2ban", "auditd",
    "nftables", "unattended-upgrades", "libpam-pwquality", "veracrypt",
]
# The umbrella "cybersecurity" request pulls a curated must-have subset across
# every discipline so a bare "cybersecurity OS" is useful out of the box.
_CYBERSEC_ESSENTIALS = (
    ["nmap", "wireshark", "tcpdump", "hydra", "john", "sqlmap", "nikto",
     "aircrack-ng", "metasploit-framework", "burpsuite"]
    + ["auditd", "snort", "suricata", "sleuthkit", "volatility3", "rkhunter"]
    + ["macchanger", "tor", "openvpn", "proxychains4"]
    + ["apparmor", "apparmor-utils", "ufw", "fail2ban", "nftables", "veracrypt"]
)

# Phrases that indicate a security-focused build needing the Kali repo. Matched
# as case-insensitive substrings against the request.
KALI_TRIGGER_KEYWORDS = (
    "cybersecurity", "cyber security", "pentest", "pentesting",
    "penetration testing", "penetration test", "red team", "red-team",
    "blue team", "blue teaming", "blue-team", "forensics", "dfir",
    "incident response", "kali",
)

# The userland "omarchy" (an opinionated Arch + Hyprland setup) is known for, on
# top of the Hyprland desktop group. Kept to packages available in Arch's repos.
_OMARCHY_PACKAGES = [
    "alacritty", "neovim", "starship", "fzf", "ripgrep", "fastfetch",
    "hyprlock", "hypridle", "mako", "wl-clipboard", "brightnessctl",
    "playerctl", "polkit-gnome", "ttf-jetbrains-mono-nerd",
]

# Kernel-flavor keywords → flavor. Checked in order; first hit wins.
_KERNEL_FLAVOR_HINTS = (
    ("cachyos", "cachyos"),
    ("cachy", "cachyos"),
    ("linux-zen", "zen"),
    ("zen kernel", "zen"),
    ("hardened kernel", "hardened"),
    ("hardened", "hardened"),
    ("lts kernel", "lts"),
    ("long-term", "lts"),
    ("long term", "lts"),
    ("kali kernel", "kali"),
    ("performance kernel", "zen"),
    ("gaming", "zen"),
)

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
        "hyprland": ["hyprland", "waybar", "wofi", "xdg-desktop-portal-hyprland"],
        "sway": ["sway", "swaybg", "waybar", "wofi"],
        "budgie": ["budgie-desktop", "lightdm"],
        "cosmic": ["cosmic-session", "cosmic-greeter"],
        "deepin": ["deepin-desktop-environment", "lightdm"],
        "enlightenment": ["enlightenment", "lightdm"],
        "i3": ["i3", "i3status", "dmenu", "lightdm"],
        "bspwm": ["bspwm", "sxhkd", "dmenu", "lightdm"],
        "awesome": ["awesome", "lightdm"],
        "openbox": ["openbox", "obconf", "lightdm"],
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
        # Cybersecurity discipline groups (Kali-backed on the Debian base).
        "cybersecurity": _CYBERSEC_ESSENTIALS,
        "cyber security": _CYBERSEC_ESSENTIALS,
        "pentest": _PENTEST_TOOLS,
        "pentesting": _PENTEST_TOOLS,
        "penetration testing": _PENTEST_TOOLS,
        "red team": _PENTEST_TOOLS,
        "blue team": _BLUETEAM_TOOLS,
        "blue teaming": _BLUETEAM_TOOLS,
        "forensics": _FORENSICS_TOOLS,
        "dfir": _FORENSICS_TOOLS,
        "spoofing": _SPOOFING_TOOLS,
        "hardening": _HARDENING_TOOLS,
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
        "hyprland": ["hyprland", "waybar", "wofi", "xdg-desktop-portal-hyprland"],
        "sway": ["sway", "swaybg", "waybar", "wofi"],
        "budgie": ["budgie-desktop", "lightdm"],
        "cosmic": ["cosmic"],
        "niri": ["niri", "waybar", "wofi"],
        "deepin": ["deepin", "deepin-extra", "lightdm"],
        "enlightenment": ["enlightenment", "lightdm"],
        "i3": ["i3-wm", "i3status", "dmenu", "lightdm"],
        "bspwm": ["bspwm", "sxhkd", "dmenu", "lightdm"],
        "awesome": ["awesome", "lightdm"],
        "openbox": ["openbox", "obconf", "lightdm"],
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

    # Detect base distro. "omarchy" is an opinionated Arch + Hyprland setup, so it
    # implies the Arch base regardless of the word "arch" appearing.
    base: Literal["debian", "arch", "unix"] = "debian"
    if "arch" in nl_lower or "omarchy" in nl_lower:
        base = "arch"
    elif "buildroot" in nl_lower or "minimal unix" in nl_lower or "unix" in nl_lower:
        base = "unix"

    # Detect desktop environment / compositor. Longer, more specific names are
    # checked first so e.g. "lxqt" wins over a bare "lx" and "i3" doesn't shadow
    # a fuller name. omarchy is Hyprland-based.
    desktop: str | None = None
    _DE_KEYWORDS = [
        "hyprland", "cinnamon", "enlightenment", "openbox", "budgie", "cosmic",
        "deepin", "awesome", "bspwm", "gnome", "plasma", "kde", "xfce", "lxqt",
        "lxde", "mate", "sway", "niri", "i3",
    ]
    if "omarchy" in nl_lower:
        desktop = "hyprland"
    else:
        for de in _DE_KEYWORDS:
            if de in nl_lower:
                # "plasma" is KDE's package group keyword.
                desktop = "kde" if de == "plasma" else de
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

    # "omarchy" is a curated Arch + Hyprland desktop. Pull the tiling-desktop
    # userland it is known for on top of the Hyprland group already added above.
    if "omarchy" in nl_lower and base == "arch":
        for pkg in _OMARCHY_PACKAGES:
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

    # Pick which prebuilt kernel line best fits the request (performance, hardened,
    # LTS, Kali, …). Only meaningful for the prebuilt path; a custom source build
    # compiles its own kernel from kconfig.
    flavor = _detect_kernel_flavor(nl_lower, base)

    # A security-focused request on the Debian base needs the Kali repo so tools
    # absent from Debian (metasploit, burpsuite, veracrypt, …) are installable.
    kali_repo = base == "debian" and any(k in nl_lower for k in KALI_TRIGGER_KEYWORDS)

    name = _derive_name(nl_lower, base, desktop)

    logger.debug(
        f"nl_to_profile: name={name} base={base} desktop={desktop} kernel_source={source} "
        f"flavor={flavor} hostname={hostname} kali_repo={kali_repo} "
        f"packages={packages} kconfig={kconfig}"
    )

    return DistroProfile(
        name=name,
        base=base,
        kernel=KernelConfig(
            version="latest-stable", source=source, flavor=flavor, kconfig_options=kconfig
        ),
        packages=list(dict.fromkeys(packages)),  # dedupe, preserve order
        hostname=hostname,
        desktop=desktop,
        kali_repo=kali_repo,
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


def _detect_kernel_flavor(
    nl_lower: str, base: str
) -> Literal["standard", "hardened", "lts", "zen", "cachyos", "kali"]:
    """Pick the prebuilt kernel line that best matches the request.

    A security build on Debian gets Kali's kernel (it rides in on the Kali repo).
    Otherwise keyword hints select hardened/lts/zen/cachyos. The result is then
    constrained to what the chosen base can actually provide — the rootfs builder
    maps flavor → package per base, but keeping the profile honest here avoids
    promising e.g. a CachyOS kernel on Debian.
    """
    if base == "debian" and any(k in nl_lower for k in KALI_TRIGGER_KEYWORDS):
        detected = "kali"
    else:
        detected = "standard"
        for hint, flavor in _KERNEL_FLAVOR_HINTS:
            if hint in nl_lower:
                detected = flavor
                break

    # Debian ships neither zen/cachyos nor an LTS-tagged image; Arch has no Kali
    # kernel. Fall back to the base default rather than a name that won't resolve.
    if base == "debian" and detected in ("zen", "cachyos", "lts"):
        return "standard"
    if base != "debian" and detected == "kali":
        return "standard"
    return detected


# Recognizable build intents → a short, descriptive name segment. First match wins.
_NAME_INTENTS = (
    (("cybersecurity", "cyber security", "pentest", "penetration", "red team",
      "blue team", "forensics", "dfir", "hardening", "security"), "secops"),
    (("privacy", "anonymous", "anonymity", "spoofing", "tor "), "ghostshell"),
    (("machine learning", "deep learning", " ml ", " ai ", "data science",
      "data analysis", "transformer"), "datalab"),
    (("gaming", "game "), "playdeck"),
    (("media", "audio", "video", "content creation"), "mediaforge"),
    (("developer", "development", "programming", "coding"), "devbox"),
    (("server", "headless"), "server"),
)


def _derive_name(nl_lower: str, base: str, desktop: str | None) -> str:
    """Build a descriptive, filesystem-safe distro/ISO name from the request.

    Replaces the old generic ``custom-<base>`` with something that reflects intent,
    e.g. ``archon-secops-debian`` or ``archon-omarchy``. The name doubles as the
    ISO filename and boot label, so it stays lowercase, hyphenated, and short.
    """
    if "omarchy" in nl_lower:
        return "archon-omarchy"

    intent: str | None = None
    for keywords, label in _NAME_INTENTS:
        if any(k in nl_lower for k in keywords):
            intent = label
            break

    parts = ["archon"]
    if intent:
        parts.append(intent)
    parts.append(base)
    return "-".join(parts)
