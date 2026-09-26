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


def test_prefix_action_falls_through_to_unknown_plugin(engine, tmp_path):
    # 'create_folder_deep' prefix-matches the 'create_folder' capability, is
    # dispatched to universal_automation, whose dynamic handler raises; the
    # engine falls through to the category-name fallback and raises for 'misc'.
    with pytest.raises(ValueError, match="misc"):
        engine._execute_parsed_command(
            {
                "action": "create_folder_deep",
                "category": "misc",
                "params": {"path": str(tmp_path / "x")},
            }
        )


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

    monkeypatch.setattr(engine.ai_parser, "openrouter_ai", _AI())

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

    monkeypatch.setattr(engine.ai_parser, "openrouter_ai", _AI())
    res = engine.chat("how do I get started?")
    assert res["kind"] == "conversation"
    assert "OPENROUTER_API_KEY" in res["reply"]
