"""
Pydantic v2 models for the Archon custom distro builder.

These models describe the full configuration of a build and its result.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

__all__ = [
    "KernelConfig",
    "DistroProfile",
    "BuildResult",
    "BuildContext",
]


class KernelConfig(BaseModel):
    """Linux kernel build configuration.

    Attributes:
        version:         Kernel version string, e.g. ``"6.9.3"`` or ``"latest-stable"``.
        patches:         List of local patch file paths to apply with ``patch -p1``.
        kconfig_options: Mapping of CONFIG_ option names to values (``"y"``/``"n"``/``"m"``).
    """

    version: str = "latest-stable"
    patches: list[str] = Field(default_factory=list)
    kconfig_options: dict[str, str] = Field(default_factory=dict)


class DistroProfile(BaseModel):
    """Complete profile describing a custom Linux distribution build.

    Attributes:
        name:          Display name of the resulting distro.
        base:          Base system: ``"debian"``, ``"arch"``, or ``"unix"`` (Buildroot).
        kernel:        Kernel configuration block.
        packages:      List of packages to install in the rootfs.
        locale:        Locale string, e.g. ``"en_US.UTF-8"``.
        timezone:      Timezone string, e.g. ``"UTC"``.
        hostname:      Default hostname for the built image.
        desktop:       Optional desktop environment identifier.
        extra_scripts: List of shell script paths to run inside the chroot.
    """

    name: str = "custom-linux"
    base: Literal["debian", "arch", "unix"] = "debian"
    kernel: KernelConfig = Field(default_factory=KernelConfig)
    packages: list[str] = Field(default_factory=list)
    locale: str = "en_US.UTF-8"
    timezone: str = "UTC"
    hostname: str = "omni-custom"
    desktop: str | None = None
    extra_scripts: list[str] = Field(default_factory=list)

    @field_validator("packages", mode="before")
    @classmethod
    def _flatten_packages(cls, v: object) -> list[str]:
        """Accept either a flat list or a ``{base: [...], optional: [...]}`` dict."""
        if isinstance(v, dict):
            result: list[str] = []
            for sub in v.values():
                if isinstance(sub, list):
                    result.extend(str(p) for p in sub)
            return result
        if isinstance(v, list):
            return [str(p) for p in v]
        return []


class BuildResult(BaseModel):
    """Outcome of a full distro build.

    Attributes:
        success:              Whether the build completed without errors.
        iso_path:             Absolute path to the built ISO, or ``None`` on failure.
        log_path:             Absolute path to the combined build log.
        build_time_seconds:   Wall-clock seconds the build took.
        size_bytes:           Size of the ISO in bytes, or ``None`` if not built.
    """

    success: bool
    iso_path: str | None = None
    log_path: str = ""
    build_time_seconds: float = 0.0
    size_bytes: int | None = None


class BuildContext(BaseModel):
    """Runtime context passed between build pipeline stages.

    Attributes:
        profile:    DistroProfile being built.
        work_dir:   Scratch directory for intermediate files.
        output_dir: Where the final ISO is placed.
        jobs:       Number of parallel make jobs (0 = cpu_count).
    """

    profile: DistroProfile
    work_dir: Path
    output_dir: Path
    jobs: int = 0

    model_config = {"arbitrary_types_allowed": True}
