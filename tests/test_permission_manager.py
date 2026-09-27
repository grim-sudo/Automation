"""Characterization tests for the security policy layer.

These lock the *current* behavior of PermissionManager before further
refactoring.  The dangerous-command heuristic was recently consolidated out of
core.engine into PermissionManager; these tests pin that contract.
"""

from __future__ import annotations

import pytest
from archon.security.permission_manager import (
    ActionCategory,
    PermissionLevel,
    PermissionManager,
)


@pytest.fixture
def pm(tmp_path):
    # Isolate the on-disk permissions file so tests never touch ~/.archon.
    return PermissionManager(config_file=str(tmp_path / "permissions.json"))


# ─── check_permission ─────────────────────────────────────────────────────────


def test_safe_filesystem_write_allowed(pm):
    assert pm.check_permission(
        {"action": "create_folder", "category": "filesystem", "params": {"name": "reports"}}
    )


def test_delete_in_blocked_path_denied(pm):
    assert not pm.check_permission(
        {"action": "delete", "category": "filesystem", "params": {"path": "/etc/passwd"}}
    )


def test_unknown_category_allowed_with_warning(pm):
    # Historical behavior: unmapped actions are permitted (logged as warning).
    assert pm.check_permission(
        {"action": "do_something_novel", "category": "mystery", "params": {}}
    )


def test_missing_action_or_category_denied(pm):
    assert not pm.check_permission({"category": "filesystem", "params": {}})
    assert not pm.check_permission({"action": "create_folder", "params": {}})


def test_non_dict_denied(pm):
    assert not pm.check_permission("not a dict")  # type: ignore[arg-type]


def test_explicitly_blocked_operation_denied(pm):
    pm.block_operation("filesystem", "create_folder")
    assert not pm.check_permission(
        {"action": "create_folder", "category": "filesystem", "params": {"name": "x"}}
    )


def test_action_category_mapping(pm):
    assert (
        pm._map_to_action_category("filesystem", "delete") is ActionCategory.FILESYSTEM_DELETE
    )
    assert (
        pm._map_to_action_category("system", "power_action") is ActionCategory.POWER_MANAGEMENT
    )
    assert pm._map_to_action_category("mystery", "nope") is None


# ─── is_dangerous_command (consolidated from engine) ───────────────────────────


@pytest.mark.parametrize(
    "command",
    [
        "please format the disk",
        "rm -rf /",
        "sudo shutdown now",
        "dd if=/dev/zero of=/dev/sda",
        "mkfs.ext4 /dev/sdb1",
        "reg delete HKLM\\Software",
        "chmod 777 /etc",
    ],
)
def test_dangerous_commands_flagged(pm, command):
    assert pm.is_dangerous_command(command)


@pytest.mark.parametrize(
    "command",
    [
        "create a folder named reports",
        "list all files in ~/Projects",
        "install nginx",
        # Substring false-positives: these embed a keyword inside a longer
        # word ("in-format-ion", "re-format-ting") and must NOT be flagged.
        "create documentation about pizza information at /home/grim/test",
        "write guidelines on formatting the report",
        "",
    ],
)
def test_safe_commands_not_flagged(pm, command):
    assert not pm.is_dangerous_command(command)


def test_permission_levels_are_ordered_semantically():
    # The four levels the risk model maps onto must all exist.
    assert {level.value for level in PermissionLevel} == {
        "safe",
        "moderate",
        "high",
        "critical",
    }
