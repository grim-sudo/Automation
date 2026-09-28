"""Tests for Archon's persistent cross-session memory.

Covers the store (SQLite persistence, keyword recall, dedup, forget) and the
manager policy layer (prompt injection, explicit commands, best-effort LLM
extraction). Extraction is exercised with a fake provider coroutine so no
network or model is needed and the behaviour is deterministic.
"""

from __future__ import annotations

import pytest
from archon.ai.memory import MemoryManager, MemoryStore, _parse_facts

# ── MemoryStore ──────────────────────────────────────────────────────────────


def _store() -> MemoryStore:
    return MemoryStore(":memory:")


def test_remember_and_count():
    s = _store()
    assert s.remember("User prefers dark mode") is not None
    assert s.count() == 1


def test_remember_skips_exact_duplicate():
    s = _store()
    s.remember("User uses Arch Linux")
    assert s.remember("User uses Arch Linux") is None
    assert s.count() == 1


def test_remember_ignores_blank():
    s = _store()
    assert s.remember("   ") is None
    assert s.count() == 0


def test_recall_ranks_by_keyword_overlap():
    s = _store()
    s.remember("User prefers the Vim editor for coding")
    s.remember("User lives in Berlin")
    s.remember("User is writing a Vim plugin in Lua")

    hits = s.recall("what editor plugin does the user write")
    assert hits, "expected keyword matches"
    # The plugin/Vim memory shares the most tokens with the query.
    assert "plugin" in hits[0].content.lower()
    # The unrelated Berlin fact must not surface for this query.
    assert all("Berlin" not in h.content for h in hits)


def test_recall_empty_for_tokenless_query():
    s = _store()
    s.remember("User prefers dark mode")
    assert s.recall("the a an") == []


def test_recent_returns_newest_first():
    s = _store()
    s.remember("first fact about python")
    s.remember("second fact about rust")
    recent = s.recent(limit=2)
    assert recent[0].content == "second fact about rust"


def test_forget_by_substring():
    s = _store()
    s.remember("User dislikes tabs")
    s.remember("User likes spaces")
    assert s.forget("tabs") == 1
    assert s.count() == 1


def test_clear_removes_all():
    s = _store()
    s.remember("a fact one")
    s.remember("b fact two")
    assert s.clear() == 2
    assert s.count() == 0


def test_store_persists_across_reopen(tmp_path):
    db = tmp_path / "mem.db"
    s1 = MemoryStore(db)
    s1.remember("User's name is Grim")
    s1.close()

    s2 = MemoryStore(db)
    assert s2.count() == 1
    assert "Grim" in s2.recent()[0].content


# ── MemoryManager: injection ─────────────────────────────────────────────────


def test_context_block_includes_relevant_memory():
    mgr = MemoryManager(_store(), max_inject=5)
    mgr.store.remember("User prefers TypeScript and functional patterns")
    block = mgr.context_block("what language should I use")
    assert "TypeScript" in block


def test_context_block_empty_when_no_memories():
    mgr = MemoryManager(_store())
    assert mgr.context_block("anything") == ""


def test_context_block_tops_up_with_recent_when_query_unmatched():
    mgr = MemoryManager(_store(), max_inject=5)
    mgr.store.remember("User is a senior engineer")
    # Query shares no tokens, but recent facts should still be injected so a
    # stable profile is always present.
    block = mgr.context_block("zzz qqq")
    assert "senior engineer" in block


# ── MemoryManager: explicit commands ─────────────────────────────────────────


def test_handle_remember_command_stores_fact():
    mgr = MemoryManager(_store())
    reply = mgr.handle_command("remember that I use PostgreSQL")
    assert reply is not None
    assert mgr.store.count() == 1
    assert "PostgreSQL" in mgr.store.recent()[0].content


def test_handle_remember_duplicate_is_reported():
    mgr = MemoryManager(_store())
    mgr.handle_command("remember that I use PostgreSQL")
    reply = mgr.handle_command("remember that I use PostgreSQL")
    assert "already" in reply.lower()
    assert mgr.store.count() == 1


def test_handle_forget_all():
    mgr = MemoryManager(_store())
    mgr.store.remember("fact one alpha")
    mgr.store.remember("fact two beta")
    reply = mgr.handle_command("forget everything")
    assert "2" in reply
    assert mgr.store.count() == 0


def test_handle_forget_specific():
    mgr = MemoryManager(_store())
    mgr.store.remember("User uses zsh shell")
    mgr.store.remember("User uses tmux")
    reply = mgr.handle_command("forget about zsh")
    assert reply is not None
    assert mgr.store.count() == 1


def test_handle_recall_command_lists_memories():
    mgr = MemoryManager(_store())
    mgr.store.remember("User works remotely")
    reply = mgr.handle_command("what do you remember about me")
    assert "works remotely" in reply


def test_handle_command_returns_none_for_normal_message():
    mgr = MemoryManager(_store())
    assert mgr.handle_command("write me a python script") is None


# ── MemoryManager: extraction ─────────────────────────────────────────────────


class _FakeComplete:
    """Async stand-in for a provider's ``complete`` coroutine."""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls: list[list[dict]] = []

    async def __call__(self, messages, **kwargs):  # noqa: ANN001, ANN003
        self.calls.append(messages)
        return self.reply


@pytest.mark.asyncio
async def test_learn_stores_extracted_json_facts():
    mgr = MemoryManager(_store(), auto_extract=True)
    complete = _FakeComplete('["User prefers dark mode", "User uses Neovim"]')

    stored = await mgr.learn(complete, "I love neovim and dark themes", "Noted.")

    assert len(stored) == 2
    assert mgr.store.count() == 2
    assert complete.calls, "extraction should call the provider"


@pytest.mark.asyncio
async def test_learn_noop_when_auto_extract_disabled():
    mgr = MemoryManager(_store(), auto_extract=False)
    complete = _FakeComplete('["something"]')
    stored = await mgr.learn(complete, "msg", "reply")
    assert stored == []
    assert not complete.calls
    assert mgr.store.count() == 0


@pytest.mark.asyncio
async def test_learn_survives_provider_error():
    class _Boom:
        async def __call__(self, messages, **kwargs):  # noqa: ANN001, ANN003
            raise RuntimeError("provider down")

    mgr = MemoryManager(_store(), auto_extract=True)
    stored = await mgr.learn(_Boom(), "msg", "reply")
    assert stored == []
    assert mgr.store.count() == 0


@pytest.mark.asyncio
async def test_learn_handles_empty_array():
    mgr = MemoryManager(_store(), auto_extract=True)
    stored = await mgr.learn(_FakeComplete("[]"), "hi", "hello")
    assert stored == []
    assert mgr.store.count() == 0


# ── fact parsing ─────────────────────────────────────────────────────────────


def test_parse_facts_json_array():
    assert _parse_facts('["a fact", "another"]') == ["a fact", "another"]


def test_parse_facts_bullet_fallback():
    raw = "- User likes coffee\n- User dislikes tea"
    assert _parse_facts(raw) == ["User likes coffee", "User dislikes tea"]


def test_parse_facts_empty_and_sentinels():
    assert _parse_facts("") == []
    assert _parse_facts("[]") == []
    assert _parse_facts("nothing") == []


def test_parse_facts_drops_overlong():
    long = "x" * 500
    assert _parse_facts(f'["{long}"]') == []
