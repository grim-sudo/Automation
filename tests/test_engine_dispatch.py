"""Characterization tests for the engine's command dispatch.

These lock the exact behavior of ``_execute_parsed_command`` across its routing
branches BEFORE the registry becomes the execution router, so the refactor can
be proven behavior-preserving.  They assert both the success-path result dicts
and the raise-through semantics on plugin failure / unknown targets.
"""

from __future__ import annotations

import os

import pytest
from archon.core.engine import Archon


@pytest.fixture(scope="module")
def engine():
    t = Archon()
    yield t
    t.shutdown()


def test_capability_routing_create_folder(engine, tmp_path):
    target = tmp_path / "made"
    res = engine._execute_parsed_command(
        {"action": "create_folder", "category": "filesystem", "params": {"path": str(target)}}
    )
    assert res["success"] is True
    assert os.path.isdir(res["path"])


def test_capability_routing_create_word_document(engine, tmp_path):
    out = tmp_path / "doc.docx"
    res = engine._execute_parsed_command(
        {
            "action": "create_word_document",
            "category": "documents",
            "params": {"filename": str(out), "content": "hi"},
        }
    )
    assert res["success"] is True
    assert res["filepath"].endswith(".docx")


def test_native_error_dict_passed_through(engine):
    # download_file with no URL returns a failure dict (not a raise).
    res = engine._execute_parsed_command(
        {"action": "download_file", "category": "network", "params": {}}
    )
    assert res == {"success": False, "message": "No URL provided"}


def test_unknown_action_and_category_raises(engine):
    with pytest.raises(ValueError, match="zzz_no_cat"):
        engine._execute_parsed_command(
            {"action": "zzz_no_such", "category": "zzz_no_cat", "params": {}}
        )


def test_unknown_unknown_raises_clear_message(engine):
    # An unrecognised command parses to unknown/unknown. It must raise a clear,
    # honest error — not the misleading "Plugin 'unknown' not found".
    with pytest.raises(ValueError, match="known action"):
        engine._execute_parsed_command(
            {"action": "unknown", "category": "unknown", "params": {"raw_command": "xyz"}}
        )


def test_system_info_dispatch_returns_real_data(engine):
    # system:get_info must route to the OS adapter and return real host data,
    # not crash with "Plugin 'unknown' not found".
    res = engine._execute_parsed_command(
        {"action": "get_info", "category": "system", "params": {}}
    )
    assert isinstance(res, dict)
    assert res.get("os")


@pytest.mark.parametrize("action", ["write_file", "create_text_file", "create_file"])
def test_filesystem_write_with_path_and_content(engine, tmp_path, action):
    # The AI parser emits file-content writes as create_file/write_file with a
    # `path` + `content`, which the OS adapter's create_file(name, location)
    # can't consume. The engine must bridge that so the file is actually
    # written instead of silently returning False.
    target = tmp_path / "note.txt"
    res = engine._execute_parsed_command(
        {
            "action": action,
            "category": "filesystem",
            "params": {"path": str(target), "content": "hello bread"},
        }
    )
    assert isinstance(res, dict) and res.get("success") is True
    assert target.read_text() == "hello bread"


def test_filesystem_create_file_with_name_still_uses_adapter(engine, tmp_path):
    # A classic create_file(name, location) must still go through the OS adapter
    # (empty file), not the content-write bridge.
    res = engine._execute_parsed_command(
        {
            "action": "create_file",
            "category": "filesystem",
            "params": {"name": "empty.txt", "location": str(tmp_path)},
        }
    )
    assert res is True
    assert (tmp_path / "empty.txt").exists()


def test_prefix_action_falls_through_to_unknown_plugin(engine, tmp_path):
    # 'create_folder_deep' prefix-matches the 'create_folder' capability and is
    # dispatched to universal_automation's dynamic handler. That handler no
    # longer crashes (it used to raise AttributeError building a table of
    # unimplemented handlers); an unknown action now returns a structured
    # failure instead of blowing up.
    res = engine._execute_parsed_command(
        {
            "action": "create_folder_deep",
            "category": "misc",
            "params": {"path": str(tmp_path / "x")},
        }
    )
    assert isinstance(res, dict)
    assert res["success"] is False


# ── result interpretation (honest success/failure) ──────────────────────────


def test_interpret_result_bool_false_is_failure():
    # A filesystem rename/move returns a bare bool; False must not be reported as
    # success (the "changed md to txt" false positive came from assuming True).
    assert Archon._interpret_result(False) == (False, None)
    assert Archon._interpret_result(True) == (True, None)


def test_interpret_result_dict_and_other_values():
    ok, err = Archon._interpret_result({"success": False, "error": "boom"})
    assert ok is False and err == "boom"
    assert Archon._interpret_result({"success": True})[0] is True
    # A dict with no explicit flag is treated as success; None is a failure.
    assert Archon._interpret_result({"path": "/x"})[0] is True
    assert Archon._interpret_result(None)[0] is False
    assert Archon._interpret_result("wrote it")[0] is True


def test_failed_rename_is_reported_not_a_false_positive(engine, tmp_path):
    # Renaming a file that doesn't exist returns False from the adapter; feeding
    # that through the interpreter must yield failure, not the old false positive
    # where the simple-command path hardcoded success=True.
    missing = tmp_path / "nope.md"
    result = engine._execute_parsed_command(
        {
            "action": "rename",
            "category": "filesystem",
            "params": {"source": str(missing), "destination": str(tmp_path / "nope.txt")},
        }
    )
    assert result is False
    assert Archon._interpret_result(result)[0] is False


# ── change-filetype rename fast-path ─────────────────────────────────────────


def test_change_extension_renames_named_file(engine, tmp_path):
    src = tmp_path / "quantum.md"
    src.write_text("# Quantum\n\nbody", encoding="utf-8")

    res = engine._maybe_change_extension(f"change the filetype of {src} from md to txt")

    assert res["success"] is True
    assert (tmp_path / "quantum.txt").is_file()
    assert not src.exists()
    assert (tmp_path / "quantum.txt").read_text() == "# Quantum\n\nbody"


def test_change_extension_uses_last_touched_file_from_history(tmp_path, monkeypatch):
    # No path in the request → resolve the file the previous turn created.
    eng = Archon()
    try:
        monkeypatch.chdir(tmp_path)
        doc = tmp_path / "notes.md"
        doc.write_text("hi", encoding="utf-8")
        eng.execution_history.append(
            {
                "timestamp": "t",
                "original_command": "make notes",
                "parsed_command": {
                    "action": "create_file",
                    "category": "filesystem",
                    "params": {"path": str(doc)},
                },
                "result_summary": "ok",
                "success": True,
                "duration": 1,
            }
        )
        res = eng._maybe_change_extension("change the filetype from md to txt")
        assert res["success"] is True
        assert (tmp_path / "notes.txt").is_file()
    finally:
        eng.shutdown()


def test_change_extension_ignores_real_conversion_and_full_rename(engine):
    # md → pdf is a content conversion, not a rename → leave it to normal parsing.
    assert engine._maybe_change_extension("convert report.md to pdf") is None
    # "a.md to summary.txt" is a full rename with a new basename → not our job.
    assert engine._maybe_change_extension("rename a.md to summary.txt") is None


def test_change_extension_reports_honestly_when_file_not_found(tmp_path, monkeypatch):
    eng = Archon()
    try:
        monkeypatch.chdir(tmp_path)  # empty dir, no history match
        res = eng._maybe_change_extension("change the file type from md to txt")
        assert res is not None
        assert res["success"] is False
        assert "couldn't tell which file" in res["error"].lower()
    finally:
        eng.shutdown()


# ── chat() seamless router ──────────────────────────────────────────────────


def test_chat_routes_question_to_conversation(engine, monkeypatch):
    # A question must not execute; it should get a conversational AI reply.
    called = {"execute": False}
    monkeypatch.setattr(
        engine, "execute", lambda *_a, **_k: called.__setitem__("execute", True)
    )

    class _AI:
        is_available = True

        def converse(self, msg, history=None):
            return "I can build operating systems and projects."

    monkeypatch.setattr(engine.ai_parser, "ai", _AI())

    res = engine.chat("what can you build?")
    assert res["kind"] == "conversation"
    assert res["success"] is True
    assert "build" in res["reply"].lower()
    assert called["execute"] is False


def test_chat_routes_command_to_execution(engine, monkeypatch):
    monkeypatch.setattr(
        engine, "execute", lambda *_a, **_k: {"success": True, "result": "ok"}
    )
    res = engine.chat("create a folder named reports")
    assert res["kind"] == "automation"
    assert res["success"] is True


def test_chat_conversation_without_ai_gives_guidance(engine, monkeypatch):
    class _AI:
        is_available = False

    monkeypatch.setattr(engine.ai_parser, "ai", _AI())
    res = engine.chat("how do I get started?")
    assert res["kind"] == "conversation"
    assert "Ollama" in res["reply"]
