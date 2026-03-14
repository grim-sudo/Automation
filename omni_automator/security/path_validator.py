"""Path validation, traversal prevention, and safe-mode confirmation."""

from __future__ import annotations

import os
import sys
import urllib.parse
from pathlib import Path

from loguru import logger

__all__ = [
    "PathValidationError",
    "PathValidator",
    "get_path_validator",
    "validate_path",
]

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULT_ALLOWED_ROOTS: list[Path] = [
    Path.home(),
    Path("/tmp"),
    Path("/var/tmp"),
]

# System directories that can never be written by OmniAutomator
_BLOCKED_PREFIXES: list[Path] = [
    Path("/etc"),
    Path("/usr"),
    Path("/bin"),
    Path("/sbin"),
    Path("/lib"),
    Path("/lib64"),
    Path("/boot"),
    Path("/sys"),
    Path("/proc"),
    Path("/dev"),
]


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class PathValidationError(PermissionError):
    """Raised when a path fails security validation."""


# ---------------------------------------------------------------------------
# PathValidator
# ---------------------------------------------------------------------------


class PathValidator:
    """Validate filesystem paths and prevent directory traversal attacks.

    All operations that write to or delete from the filesystem should pass
    their target paths through :meth:`validate` before proceeding.

    Args:
        allowed_roots: Directories under which operations are permitted.
                       If ``None`` defaults to ``[home_dir, /tmp, cwd]``.
        safe_mode:     When ``True``, :meth:`require_confirmation` actually
                       prompts the user; otherwise it returns ``True``
                       immediately.
    """

    def __init__(
        self,
        allowed_roots: list[Path] | None = None,
        safe_mode: bool = False,
    ) -> None:
        if allowed_roots is None:
            # Default: home dir, /tmp, and the current working directory
            roots = [
                Path.home(),
                Path("/tmp"),
                Path(os.getcwd()),
            ]
        else:
            roots = list(allowed_roots)

        # Resolve to canonical absolute paths; skip non-existent roots
        self._allowed: list[Path] = []
        for r in roots:
            try:
                resolved = Path(r).expanduser().resolve()
                if resolved not in self._allowed:
                    self._allowed.append(resolved)
            except Exception:
                pass

        self.safe_mode = safe_mode

    # ── Core validation ───────────────────────────────────────────────────────

    def validate(self, path: str | Path, must_exist: bool = False) -> Path:
        """Resolve *path* and verify it is within the allowed roots.

        Steps:
        1. URL-decode the path string to catch encoded traversal sequences.
        2. Detect ``..`` and null-byte sequences.
        3. Resolve to a canonical absolute path.
        4. Check against blocked system prefixes.
        5. Verify the resolved path is under at least one allowed root.
        6. Optionally assert the path already exists.

        Args:
            path:       Path string or :class:`pathlib.Path` to validate.
            must_exist: If ``True`` the path must exist; raises
                        :exc:`PathValidationError` if it does not.

        Returns:
            Resolved, validated :class:`pathlib.Path`.

        Raises:
            PathValidationError:   On traversal sequences, null bytes,
                                   blocked/disallowed directories, or when
                                   the path does not exist and *must_exist*
                                   is set.
        """
        raw = str(path)

        # 1. Detect encoded traversal
        decoded = urllib.parse.unquote(raw)
        if ".." in decoded:
            raise PathValidationError(f"Path traversal sequence ('..') detected in path: {raw!r}")
        if "\x00" in decoded:
            raise PathValidationError(f"Null byte detected in path: {raw!r}")

        # 2. Resolve to canonical absolute path
        resolved = Path(os.path.realpath(os.path.abspath(raw)))

        # 3. Reject blocked system prefixes
        for blocked in _BLOCKED_PREFIXES:
            try:
                resolved.relative_to(blocked)
                raise PathValidationError(
                    f"Path {resolved!r} is inside a protected system directory "
                    f"({blocked}). OmniAutomator will not write there."
                )
            except ValueError:
                pass  # Not under this blocked prefix — continue checking

        # 4. Must be under at least one allowed root
        if not self._is_under_allowed_root(resolved):
            raise PathValidationError(
                f"Path {resolved!r} is outside all allowed directories.\n"
                f"Allowed roots: {[str(r) for r in self._allowed]}\n"
                "Use add_allowed_root() to extend the allowed set."
            )

        # 5. Existence check
        if must_exist and not resolved.exists():
            raise PathValidationError(f"Path does not exist: {resolved!r}")

        logger.debug("Path validated: {}", resolved)
        return resolved

    def is_safe(self, path: str | Path) -> bool:
        """Non-raising version of :meth:`validate`.

        Args:
            path: Path to check.

        Returns:
            ``True`` if the path passes all validation checks, ``False``
            otherwise.
        """
        try:
            self.validate(path)
            return True
        except (ValueError, PathValidationError, OSError):
            return False

    # ── Safe-mode confirmation ────────────────────────────────────────────────

    def require_confirmation(self, operation: str, target: str) -> bool:
        """In safe mode, print a warning and require ``yes`` confirmation.

        When :attr:`safe_mode` is ``False`` this method returns ``True``
        immediately without prompting.

        Args:
            operation: Human-readable description of the destructive operation,
                       e.g. ``"delete directory"``.
            target:    The target path or resource being operated on.

        Returns:
            ``True`` if the user confirmed (or safe mode is disabled).
            ``False`` if the user declined.
        """
        if not self.safe_mode:
            return True

        print(
            f"\n[SAFE MODE] WARNING: About to perform a potentially destructive "
            f"operation.\n"
            f"  Operation : {operation}\n"
            f"  Target    : {target}\n"
        )
        try:
            answer = input("Type 'yes' to continue, anything else to abort: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return False

        confirmed = answer == "yes"
        if confirmed:
            logger.info(
                "Safe-mode confirmation received for operation={!r} target={!r}",
                operation,
                target,
            )
        else:
            logger.info(
                "Safe-mode operation cancelled by user: operation={!r} target={!r}",
                operation,
                target,
            )
        return confirmed

    # ── Root management ───────────────────────────────────────────────────────

    def add_allowed_root(self, path: Path) -> None:
        """Extend the allowed-roots list with *path*.

        Args:
            path: New directory root to permit.  Expanded and resolved.
        """
        resolved = Path(path).expanduser().resolve()
        if resolved not in self._allowed:
            self._allowed.append(resolved)
            logger.debug("Added allowed root: {}", resolved)

    # ── Static helpers ────────────────────────────────────────────────────────

    @staticmethod
    def check_root_required(operation: str) -> None:
        """Raise :exc:`PermissionError` with a helpful message if not root.

        On Linux/macOS, "root" means ``os.geteuid() == 0``.  On Windows it
        means the process has elevation (checked via ``ctypes``).

        Args:
            operation: Human-readable name of the privileged operation, used
                       in the error message.

        Raises:
            PermissionError: If the process is not running with administrator
                             privileges.
        """
        is_root = False
        if sys.platform == "win32":
            try:
                import ctypes

                is_root = bool(ctypes.windll.shell32.IsUserAnAdmin())
            except Exception:
                is_root = False
        else:
            is_root = os.geteuid() == 0

        if not is_root:
            raise PermissionError(
                f"Operation '{operation}' requires administrator/root privileges.\n"
                "Re-run the command with 'sudo' (Linux/macOS) or from an elevated "
                "terminal (Windows)."
            )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _is_under_allowed_root(self, resolved: Path) -> bool:
        """Return ``True`` if *resolved* is under at least one allowed root."""
        for root in self._allowed:
            try:
                resolved.relative_to(root)
                return True
            except ValueError:
                continue
        return False

    def __repr__(self) -> str:
        return (
            f"PathValidator(allowed_roots={[str(r) for r in self._allowed]}, "
            f"safe_mode={self.safe_mode})"
        )


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_validator_instance: PathValidator | None = None


def get_path_validator() -> PathValidator:
    """Return the process-wide :class:`PathValidator` singleton.

    On first call the validator is constructed using the global
    :func:`~omni_automator.config.get_settings` to read ``safe_mode``.
    Falls back to a default instance if the config cannot be loaded.

    To force a fresh instance (e.g. after changing ``safe_mode``)::

        from omni_automator.security import path_validator
        path_validator._validator_instance = None
        validator = path_validator.get_path_validator()

    Returns:
        Process-wide :class:`PathValidator` singleton.
    """
    global _validator_instance
    if _validator_instance is None:
        try:
            from ..config import get_settings

            settings = get_settings()
            _validator_instance = PathValidator(safe_mode=settings.safe_mode)
        except Exception:
            _validator_instance = PathValidator()
    return _validator_instance


def validate_path(path: str | Path, must_exist: bool = False) -> Path:
    """Convenience function: validate *path* via the global singleton.

    Args:
        path:       Path to validate.
        must_exist: Raise if the path does not yet exist on disk.

    Returns:
        Resolved :class:`pathlib.Path`.

    Raises:
        ValueError:          On traversal sequences.
        PathValidationError: On security violations.
    """
    return get_path_validator().validate(path, must_exist=must_exist)
