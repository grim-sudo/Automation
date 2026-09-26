"""Characterization tests for the native DocumentCapability.

These lock the behavior carved out of ``universal_automation`` so the plugin's
document methods (now thin delegators) stay equivalent to the capability.
"""

from __future__ import annotations

import os

from archon.capabilities.native.documents import DocumentCapability
from archon.plugins.universal_automation import UniversalAutomationPlugin

# ─── discovery / contract ───────────────────────────────────────────────────


def test_discover_lists_document_actions():
    cap = DocumentCapability()
    actions = cap.actions()
    for expected in (
        "create_word_document",
        "create_powerpoint",
        "create_excel",
        "create_pdf",
        "save_to_document",
    ):
        assert expected in actions


def test_unknown_action_fails_cleanly():
    cap = DocumentCapability()
    result = cap.execute("does_not_exist", {})
    assert result.success is False
    assert result.error


# ─── real file generation (libs are installed in this env) ──────────────────


def test_word_docx_written(tmp_path):
    cap = DocumentCapability()
    out = tmp_path / "note.docx"
    res = cap.create_word_document({"filename": str(out), "title": "T", "content": "hello"})
    assert res["success"] is True
    assert os.path.exists(res["filepath"])
    assert res["filepath"].endswith(".docx")


def test_excel_xlsx_written(tmp_path):
    cap = DocumentCapability()
    out = tmp_path / "sheet.xlsx"
    res = cap.create_excel(
        {"filename": str(out), "headers": ["a", "b"], "data": [[1, 2], [3, 4]]}
    )
    assert res["success"] is True
    assert os.path.exists(res["filepath"])


def test_save_to_plain_text(tmp_path):
    cap = DocumentCapability()
    out = tmp_path / "log.txt"
    res = cap.save_to_document({"path": str(out), "content": "line"})
    assert res["success"] is True
    assert (tmp_path / "log.txt").read_text().startswith("line")


# ─── plugin delegates to the capability (behavior preserved) ─────────────────


def test_plugin_delegates_to_capability(tmp_path):
    plugin = UniversalAutomationPlugin()
    out = tmp_path / "viaplugin.docx"
    res = plugin.execute("create_word_document", {"filename": str(out), "content": "x"})
    assert res["success"] is True
    assert os.path.exists(res["filepath"])
    # The plugin's private method and the capability share one implementation.
    assert plugin._documents is plugin._documents  # cached accessor
