"""Privilege escalation input layer.

Archon normally runs unprivileged (uid != 0). When an operation genuinely needs
root — a distro build's ``pacstrap``/``debootstrap``/``chroot`` steps, for
example — this layer asks the UI for the sudo password through an injected
*provider*, runs the privileged command via ``sudo -S`` (password on stdin), and
never persists the password itself.

Design
------
* The password *provider* is set by the presentation layer (a masked modal in
  the TUI, ``getpass`` in the REPL/CLI). The core never imports a UI.
* A privileged *operation* (which may fan out into many ``sudo`` sub-commands,
  like a build) opens a :meth:`PrivilegeEscalator.session`. The session is only
  a lightweight scope marking that a privileged operation is authorized; it does
  **not** hold a password. Every individual ``sudo -S`` sub-command prompts the
  provider fresh, uses the password for that one command, and lets it fall out
  of scope immediately. Archon therefore prompts for every sub-command and never
  caches the password anywhere — honoring the "prompt every time, never cache"
  contract literally.
* A process-wide singleton (:func:`get_escalator`) lets deep code (the distro
  builder's subprocess helpers) reach the active session without threading a
  runner through every call site.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterator
from typing import Any

from ..utils.logger import get_logger

logger = get_logger("Privilege")

# provider(reason) -> password, or None if the user cancels/declines.
PasswordProvider = Callable[[str], "str | None"]


class PrivilegeError(PermissionError):
    """Raised when a privileged operation cannot proceed (no sudo, cancelled)."""


class _Session:
    """An active privileged operation.

    Holds no password. Each :meth:`run` prompts the escalator's provider afresh
    so every sub-command is authorized individually.
    """

    def __init__(self, escalator: PrivilegeEscalator, reason: str) -> None:
        self._escalator = escalator
        self._reason = reason

    def run(self, argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
        """Run ``argv`` as root via ``sudo -S``, prompting for the password now."""
        return self._escalator._run_privileged(argv, self._reason, **kwargs)


class PrivilegeEscalator:
    """Obtains root for privileged operations without storing the password."""

    def __init__(self, provider: PasswordProvider | None = None) -> None:
        self._provider = provider
        # The session bound to the *current privileged operation*. Kept as a
        # plain attribute (not thread-local) on purpose: a distro build fans its
        # sudo sub-commands out across worker threads via ``asyncio.to_thread``,
        # so the session must be reachable from any thread for the operation's
        # lifetime. It holds no password — only a marker + reason. ponytail:
        # assumes one privileged operation at a time (no concurrent builds); a
        # concurrent design would need per-operation keys.
        self._session: _Session | None = None

    def set_provider(self, provider: PasswordProvider | None) -> None:
        """Register (or clear) the UI callback that supplies the sudo password."""
        self._provider = provider

    @staticmethod
    def is_root() -> bool:
        if sys.platform == "win32":
            try:
                import ctypes

                return bool(ctypes.windll.shell32.IsUserAnAdmin())
            except Exception:
                return False
        return os.geteuid() == 0

    @staticmethod
    def sudo_available() -> bool:
        return shutil.which("sudo") is not None

    def can_escalate(self) -> bool:
        """True if this process is root, or can prompt+sudo to become root."""
        return self.is_root() or (self._provider is not None and self.sudo_available())

    @property
    def active_session(self) -> _Session | None:
        """The session for the current privileged operation, if one is open."""
        return self._session

    def _prompt(self, reason: str) -> str | None:
        if self._provider is None:
            return None
        try:
            pw = self._provider(reason)
        except Exception as exc:  # noqa: BLE001 - a broken UI must not crash a run
            logger.debug("sudo password provider raised: {}", exc)
            return None
        return pw or None

    @contextlib.contextmanager
    def session(self, reason: str = "a privileged operation") -> Iterator[_Session | None]:
        """Open a privileged operation.

        Yields a :class:`_Session` runner when escalation is possible, or ``None``
        when the process is already root (callers just run commands directly).

        No password is prompted here — each sub-command run through the session
        prompts on its own so the "prompt every time" contract holds per command.
        We only verify up front that escalation is *possible* (sudo present and a
        provider registered) so a misconfigured run fails fast.

        Raises:
            PrivilegeError: if not root and escalation is impossible.
        """
        if self.is_root():
            yield None
            return
        if not self.sudo_available():
            raise PrivilegeError(
                f"{reason} requires root, but 'sudo' is not available on this system."
            )
        if self._provider is None:
            raise PrivilegeError(
                f"{reason} requires root, but no sudo password provider is registered."
            )

        session = _Session(self, reason)
        previous = self._session
        self._session = session
        try:
            yield session
        finally:
            # Restore the prior session (supports nesting). Nothing sensitive is
            # retained: the session never held a password.
            self._session = previous

    def _run_privileged(
        self, argv: list[str], reason: str, **kwargs: Any
    ) -> subprocess.CompletedProcess:
        """Prompt for the password, run one ``sudo -S`` command, discard the password.

        ``-k`` ignores any cached sudo timestamp so each command re-authenticates;
        ``-p ''`` suppresses sudo's own prompt (we supply the password on stdin).
        The password lives only as a local here and is gone when this returns.
        """
        password = self._prompt(reason)
        if password is None:
            raise PrivilegeError(f"{reason} requires root; sudo password was not provided.")
        kwargs.setdefault("capture_output", True)
        kwargs.setdefault("text", True)
        return subprocess.run(
            ["sudo", "-S", "-k", "-p", "", *argv],
            input=password + "\n",
            **kwargs,
        )

    def run(
        self, argv: list[str], reason: str = "a privileged operation", **kwargs: Any
    ) -> subprocess.CompletedProcess:
        """Run one privileged command.

        If already root, run directly. Otherwise prompt for the password, run via
        ``sudo -S``, and discard it. Each call re-prompts.
        """
        if self.is_root():
            kwargs.setdefault("capture_output", True)
            kwargs.setdefault("text", True)
            return subprocess.run(argv, **kwargs)
        return self._run_privileged(argv, reason, **kwargs)


_escalator: PrivilegeEscalator | None = None


def get_escalator() -> PrivilegeEscalator:
    """Return the process-wide escalator singleton."""
    global _escalator
    if _escalator is None:
        _escalator = PrivilegeEscalator()
    return _escalator


def configure_escalator(provider: PasswordProvider | None) -> PrivilegeEscalator:
    """Register the UI's sudo-password provider on the singleton."""
    esc = get_escalator()
    esc.set_provider(provider)
    return esc


__all__ = [
    "PrivilegeError",
    "PrivilegeEscalator",
    "configure_escalator",
    "get_escalator",
]
