"""Characterization tests for the native FilesystemCapability.

Locks the folder/download behavior carved out of ``universal_automation`` so
the plugin's delegators stay equivalent to the capability.
"""

from __future__ import annotations

import os

from archon.capabilities.native.filesystem import FilesystemCapability
from archon.plugins.universal_automation import UniversalAutomationPlugin


def test_discover_lists_filesystem_actions():
    cap = FilesystemCapability()
    actions = cap.actions()
    for expected in ("create_folder", "make_directory", "ensure_folder", "download_file"):
        assert expected in actions


def test_create_folder_makes_directory(tmp_path):
    cap = FilesystemCapability()
    target = tmp_path / "new" / "nested"
    res = cap.create_folder({"path": str(target)})
    assert res["success"] is True
    assert os.path.isdir(res["path"])


def test_create_folder_requires_path():
    cap = FilesystemCapability()
    res = cap.create_folder({})
    assert res["success"] is False
    assert "No folder path" in res["error"]


def test_download_requires_url():
    cap = FilesystemCapability()
    res = cap.download_file({})
    assert res["success"] is False
    assert "No URL" in res["message"]


def test_unknown_action_fails_cleanly():
    cap = FilesystemCapability()
    res = cap.execute("nope", {})
    assert res.success is False
    assert res.error


def test_plugin_delegates_folder_creation(tmp_path):
    plugin = UniversalAutomationPlugin()
    target = tmp_path / "viaplugin"
    res = plugin.execute("create_folder", {"path": str(target)})
    assert res["success"] is True
    assert os.path.isdir(res["path"])
    assert plugin._filesystem is plugin._filesystem  # cached accessor


def test_dynamic_action_in_sandbox_simulates_and_does_not_crash():
    # Regression: the sandbox path used to pass a `sandbox=` kwarg the dynamic
    # handler did not accept, raising "unexpected keyword argument 'sandbox'".
    # It must now simulate (no system execution) and report success.
    plugin = UniversalAutomationPlugin()
    res = plugin.execute("run_tests", {"_sandbox": True})
    assert res["success"] is True
    assert res.get("sandbox") is True
    assert "simulated" in res["message"].lower()
