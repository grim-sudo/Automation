"""Tests for the privilege-escalation input layer.

These never actually run ``sudo``; they exercise the decision logic (when to
prompt, when to refuse, that the password is not retained past an operation)
with the ``subprocess`` boundary mocked.
"""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest
from archon.security.privilege import PrivilegeError, PrivilegeEscalator


def _completed(returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=["sudo"], returncode=returncode, stdout="", stderr="")


def test_no_provider_and_not_root_refuses():
    esc = PrivilegeEscalator()
    with patch.object(PrivilegeEscalator, "is_root", staticmethod(lambda: False)):
        with pytest.raises(PrivilegeError):
            with esc.session("op"):
                pass


def test_cancelled_prompt_refuses():
    esc = PrivilegeEscalator(provider=lambda reason: None)
    with patch.object(PrivilegeEscalator, "is_root", staticmethod(lambda: False)), patch.object(
        PrivilegeEscalator, "sudo_available", staticmethod(lambda: True)
    ):
        with pytest.raises(PrivilegeError):
            with esc.session("op"):
                pass


def test_wrong_password_refuses():
    esc = PrivilegeEscalator(provider=lambda reason: "bad")
    with patch.object(PrivilegeEscalator, "is_root", staticmethod(lambda: False)), patch.object(
        PrivilegeEscalator, "sudo_available", staticmethod(lambda: True)
    ), patch("subprocess.run", return_value=_completed(returncode=1)):
        with pytest.raises(PrivilegeError):
            with esc.session("op"):
                pass


def test_session_prompts_once_and_password_not_retained():
    calls: list[str] = []
    esc = PrivilegeEscalator(provider=lambda reason: calls.append(reason) or "secret")
    with patch.object(PrivilegeEscalator, "is_root", staticmethod(lambda: False)), patch.object(
        PrivilegeEscalator, "sudo_available", staticmethod(lambda: True)
    ), patch("subprocess.run", return_value=_completed(returncode=0)) as run:
        assert esc.active_session is None
        with esc.session("build") as sess:
            assert sess is not None
            assert esc.active_session is sess
            # Prompted exactly once up front for the whole operation.
            assert calls == ["build"]
            # Sub-commands reuse the held password — no further prompts.
            sess.run(["a"])
            sess.run(["b"])
            assert calls == ["build"]
        # After the operation the session (and its password) is dropped.
        assert esc.active_session is None
        # The validation call fed the password on stdin to `sudo -S`.
        _, kwargs = run.call_args
        assert kwargs.get("input", "").startswith("secret")


def test_root_yields_no_session_and_runs_directly():
    esc = PrivilegeEscalator()
    with patch.object(PrivilegeEscalator, "is_root", staticmethod(lambda: True)), patch(
        "subprocess.run", return_value=_completed(returncode=0)
    ) as run:
        with esc.session("op") as sess:
            assert sess is None  # root => no sudo wrapper needed
        esc.run(["ls"])
        argv = run.call_args[0][0]
        assert argv == ["ls"]  # ran directly, no sudo prefix


def test_session_run_prefixes_sudo():
    esc = PrivilegeEscalator(provider=lambda reason: "pw")
    with patch.object(PrivilegeEscalator, "is_root", staticmethod(lambda: False)), patch.object(
        PrivilegeEscalator, "sudo_available", staticmethod(lambda: True)
    ), patch("subprocess.run", return_value=_completed(returncode=0)) as run:
        with esc.session("op") as sess:
            sess.run(["pacstrap", "/mnt"])
        # Last call is the real command, prefixed with sudo -S.
        argv = run.call_args[0][0]
        assert argv[:2] == ["sudo", "-S"]
        assert "pacstrap" in argv
