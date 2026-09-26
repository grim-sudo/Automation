"""
Security and permission management for Archon.
Includes permission enforcement, path validation, and safe subprocess utilities.
"""

from __future__ import annotations

from .permission_manager import ActionCategory, PermissionLevel, PermissionManager
from .subprocess_runner import SubprocessError, build_package_cmd, safe_popen, safe_run

__all__ = [
    "PermissionManager",
    "PermissionLevel",
    "ActionCategory",
    "safe_run",
    "safe_popen",
    "build_package_cmd",
    "SubprocessError",
]

# path_validator is imported lazily to avoid circular imports
try:
    from .path_validator import PathValidator, get_path_validator  # type: ignore[import]

    __all__ += ["PathValidator", "get_path_validator"]
except ImportError:
    pass
