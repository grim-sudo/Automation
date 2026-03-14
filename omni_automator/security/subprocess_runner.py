"""
Safe subprocess utilities for OmniAutomator.

Provides helper functions that convert shell-string commands to list-form
subprocess calls, eliminating shell injection risks from shell=True.
"""
from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from loguru import logger


class SubprocessError(Exception):
    """Raised when a safe subprocess call fails unexpectedly."""

    def __init__(self, message: str, returncode: int = -1, stderr: str = "") -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


def safe_run(
    command: str | list[str],
    *,
    cwd: str | Path | None = None,
    capture_output: bool = True,
    text: bool = True,
    check: bool = False,
    timeout: int | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """
    Run a command safely without shell=True.

    If given a string, splits it using POSIX shlex rules (handles quoted tokens
    correctly but does NOT support shell metacharacters like |, &&, >).  Pass a
    list directly when you need precise argument control.

    Args:
        command: Command as a string or pre-split list of arguments.
        cwd: Working directory for the subprocess.
        capture_output: Capture stdout/stderr (equivalent to capture_output=True).
        text: Decode stdout/stderr as UTF-8 strings.
        check: Raise SubprocessError if return code != 0.
        timeout: Seconds before raising TimeoutExpired.
        env: Environment variables for the subprocess (None = inherit current env).

    Returns:
        subprocess.CompletedProcess instance.

    Raises:
        SubprocessError: If check=True and command exits with non-zero return code.
        FileNotFoundError: If the executable is not found on PATH.
        subprocess.TimeoutExpired: If the command times out.
    """
    if isinstance(command, str):
        args = shlex.split(command, posix=True)
    else:
        args = list(command)

    if not args:
        raise ValueError("Command must not be empty")

    executable = args[0]

    logger.debug(f"safe_run: {args!r} (cwd={cwd})")

    result = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        capture_output=capture_output,
        text=text,
        timeout=timeout,
        env=env,
        # NEVER shell=True
    )

    if check and result.returncode != 0:
        raise SubprocessError(
            f"Command failed (exit {result.returncode}): {' '.join(args)}",
            returncode=result.returncode,
            stderr=result.stderr or "",
        )

    return result


def safe_popen(
    command: str | list[str],
    *,
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.Popen[str]:
    """
    Launch a process without shell=True and return its Popen handle.

    Args:
        command: Command as a string or pre-split list.
        cwd: Working directory for the subprocess.
        env: Environment variables (None = inherit).

    Returns:
        subprocess.Popen handle.
    """
    if isinstance(command, str):
        args = shlex.split(command, posix=True)
    else:
        args = list(command)

    return subprocess.Popen(
        args,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def build_package_cmd(manager: str, sub: str, package: str, extra: list[str] | None = None) -> list[str]:
    """
    Build a package-manager command as a safe list.

    Args:
        manager: Package manager name (apt, brew, pacman, yay, paru, dnf, winget, choco).
        sub: Sub-command (install, remove, search, list, update).
        package: Package name.
        extra: Additional flags to append.

    Returns:
        List of command tokens suitable for subprocess.run.

    Raises:
        ValueError: If manager is not recognised.
    """
    extra = extra or []
    cmds: dict[str, dict[str, list[str]]] = {
        "apt": {
            "install": ["sudo", "apt-get", "install", "-y"],
            "remove": ["sudo", "apt-get", "remove", "-y"],
            "search": ["apt-cache", "search"],
            "list": ["apt", "list", "--installed"],
            "update": ["sudo", "apt-get", "update"],
        },
        "brew": {
            "install": ["brew", "install"],
            "remove": ["brew", "uninstall"],
            "search": ["brew", "search"],
            "list": ["brew", "list"],
            "update": ["brew", "update"],
        },
        "pacman": {
            "install": ["sudo", "pacman", "-S", "--noconfirm"],
            "remove": ["sudo", "pacman", "-R", "--noconfirm"],
            "search": ["pacman", "-Ss"],
            "list": ["pacman", "-Q"],
            "update": ["sudo", "pacman", "-Syu", "--noconfirm"],
        },
        "yay": {
            "install": ["yay", "-S", "--noconfirm"],
            "remove": ["yay", "-R", "--noconfirm"],
            "search": ["yay", "-Ss"],
            "list": ["yay", "-Q"],
            "update": ["yay", "-Syu", "--noconfirm"],
        },
        "paru": {
            "install": ["paru", "-S", "--noconfirm"],
            "remove": ["paru", "-R", "--noconfirm"],
            "search": ["paru", "-Ss"],
            "list": ["paru", "-Q"],
            "update": ["paru", "-Syu", "--noconfirm"],
        },
        "dnf": {
            "install": ["sudo", "dnf", "install", "-y"],
            "remove": ["sudo", "dnf", "remove", "-y"],
            "search": ["dnf", "search"],
            "list": ["dnf", "list", "installed"],
            "update": ["sudo", "dnf", "upgrade", "-y"],
        },
        "winget": {
            "install": ["winget", "install", "--silent",
                        "--accept-package-agreements", "--accept-source-agreements"],
            "remove": ["winget", "uninstall", "-e"],
            "search": ["winget", "search"],
            "list": ["winget", "list"],
            "update": ["winget", "upgrade", "--all"],
        },
        "choco": {
            "install": ["choco", "install", "-y"],
            "remove": ["choco", "uninstall", "-y"],
            "search": ["choco", "search"],
            "list": ["choco", "list", "--local-only"],
            "update": ["choco", "upgrade", "all", "-y"],
        },
    }

    manager_cmds = cmds.get(manager.lower())
    if not manager_cmds:
        raise ValueError(f"Unsupported package manager: {manager!r}")

    base = manager_cmds.get(sub)
    if not base:
        raise ValueError(f"Unsupported sub-command {sub!r} for manager {manager!r}")

    result = list(base)
    if package:
        result.append(package)
    result.extend(extra)
    return result
