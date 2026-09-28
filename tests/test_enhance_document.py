"""Regression tests for the "enhance an existing document" flow.

Reproduces the failure where asking Archon to "add more information to the
markdown file at /data/test and make it more detailed" produced a fragile
3-step plan (read_file → invented generate_enhanced_content → create_file) that
no execution path could satisfy, so the model gave up with a false "I can't
access files" reply. The fix runs it as one real read → AI-enhance → write step.
"""

from __future__ import annotations

import pytest
from archon.ai.automation_ai import _DOCUMENT_TIMEOUT, OllamaAutomationAI
from archon.core.engine import Archon

# ── enhance_document facade ──────────────────────────────────────────────────


class _MsgCapturingProvider:
    """Records the messages a completion call receives."""

    def __init__(self) -> None:
        self.captured: dict[str, object] = {}

    async def complete(
        self,
        messages,  # noqa: ANN001
        *,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        model: str | None = None,
        timeout: float | None = None,
    ) -> str:
        self.captured = {"messages": messages, "timeout": timeout}
        return "# Expanded\n\nNow with much more detail."


def _ai_with_provider(provider) -> OllamaAutomationAI:  # noqa: ANN001
    ai = OllamaAutomationAI.__new__(OllamaAutomationAI)
    ai._is_available = True
    ai._ollama = provider
    return ai


def test_enhance_document_feeds_original_content_and_long_timeout():
    provider = _MsgCapturingProvider()
    ai = _ai_with_provider(provider)

    out = ai.enhance_document(
        "# Title\n\nOriginal body.", "make it more detailed", filename="note.md"
    )

    assert out.startswith("# Expanded")
    # The existing content must reach the model, or it can't expand it.
    user_msg = provider.captured["messages"][-1]["content"]
    assert "Original body." in user_msg
    assert "make it more detailed" in user_msg
    # Same generous ceiling as generate_document — expansion is not a chat turn.
    assert provider.captured["timeout"] == _DOCUMENT_TIMEOUT


def test_enhance_document_returns_empty_when_offline():
    ai = OllamaAutomationAI.__new__(OllamaAutomationAI)
    ai._is_available = False
    assert ai.enhance_document("x", "y") == ""


class _FlakyProvider:
    """Returns empty on the first call(s), then real content.

    Models the FreeLLMAPI 'auto' router intermittently returning an empty
    completion for an otherwise-valid request.
    """

    def __init__(self, replies: list[str]) -> None:
        self._replies = replies
        self.calls = 0

    async def complete(self, messages, **kwargs):  # noqa: ANN001, ANN003
        reply = self._replies[min(self.calls, len(self._replies) - 1)]
        self.calls += 1
        return reply


def test_enhance_document_retries_on_empty_completion():
    # First attempt returns nothing (the 'auto' quirk); retry yields real text.
    ai = _ai_with_provider(_FlakyProvider(["", "# Recovered\n\nReal content."]))
    out = ai.enhance_document("# Orig", "expand it", filename="n.md")
    assert out.startswith("# Recovered")
    assert ai._ollama.calls == 2


def test_enhance_document_gives_up_after_retry_when_still_empty():
    ai = _ai_with_provider(_FlakyProvider(["", ""]))
    out = ai.enhance_document("# Orig", "expand it")
    assert out == ""
    # Retried once, then stopped — no infinite loop.
    assert ai._ollama.calls == 2


# ── engine: path resolution + enhance handler ────────────────────────────────


class _FakeAI:
    """Stand-in AI facade that echoes a scripted enhanced body."""

    is_available = True

    def __init__(self, out: str) -> None:
        self._out = out
        self.calls: list[tuple[str, str, str]] = []

    def enhance_document(self, original: str, instruction: str, filename: str = "") -> str:
        self.calls.append((original, instruction, filename))
        return self._out


@pytest.fixture(scope="module")
def engine():
    eng = Archon()
    yield eng
    eng.shutdown()


def test_resolve_document_path_direct_file(engine, tmp_path):
    f = tmp_path / "a.md"
    f.write_text("hi", encoding="utf-8")
    assert engine._resolve_document_path(str(f)) == str(f)


def test_resolve_document_path_directory_single_doc(engine, tmp_path):
    f = tmp_path / "only.md"
    f.write_text("hi", encoding="utf-8")
    assert engine._resolve_document_path(str(tmp_path)) == str(f)


def test_resolve_document_path_directory_ambiguous_is_none(engine, tmp_path):
    (tmp_path / "a.md").write_text("1", encoding="utf-8")
    (tmp_path / "b.md").write_text("2", encoding="utf-8")
    assert engine._resolve_document_path(str(tmp_path)) is None


def test_resolve_document_path_nonexistent_is_none(engine, tmp_path):
    assert engine._resolve_document_path(str(tmp_path / "nope.md")) is None


def test_handle_enhance_file_writes_expanded_content(engine, tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# Small\n\nOne line.", encoding="utf-8")
    engine.ai_parser.ai = _FakeAI("# Small\n\nOne line.\n\n## More\n\nLots more detail.")

    result = engine._handle_enhance_file(
        {"file_path": str(f), "instruction": "make it more detailed"}
    )

    assert result["success"] is True
    # The AI saw the original content, and the file now holds the expanded body.
    assert engine.ai_parser.ai.calls[0][0] == "# Small\n\nOne line."
    assert "Lots more detail." in f.read_text(encoding="utf-8")


def test_handle_enhance_file_empty_ai_result_leaves_file_unchanged(engine, tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# Keep me", encoding="utf-8")
    engine.ai_parser.ai = _FakeAI("")

    result = engine._handle_enhance_file({"file_path": str(f), "instruction": "expand"})

    assert result["success"] is False
    assert f.read_text(encoding="utf-8") == "# Keep me"


def test_maybe_enhance_document_routes_existing_file(engine, tmp_path):
    f = tmp_path / "readme.md"
    f.write_text("# Doc\n\nStub.", encoding="utf-8")
    engine.ai_parser.ai = _FakeAI("# Doc\n\nStub, now expanded with detail.")

    result = engine._maybe_enhance_document(
        f"add more information to the markdown file at {tmp_path} and make it more detailed"
    )

    assert result is not None
    assert result["success"] is True
    assert "expanded" in f.read_text(encoding="utf-8")


def test_maybe_enhance_document_ignores_plain_create_request(engine):
    # No enhance phrase and no existing file — must not hijack normal parsing.
    assert engine._maybe_enhance_document("create a file called notes.md") is None


def test_maybe_enhance_document_routes_paraphrased_modify_requests(engine, tmp_path):
    """The agent's model paraphrases the user's request unpredictably, so
    routing must fire for modify-intent phrasings beyond "add more detail" —
    provided the named path resolves to an existing document."""
    f = tmp_path / "doc.md"
    engine.ai_parser.ai = _FakeAI("# Doc\n\nnow expanded.")
    for phrasing in (
        f"open the markdown file at {tmp_path} and append detailed content",
        f"update the {tmp_path} markdown file with additional sections",
        f"expand the document at {tmp_path} with more detail",
    ):
        f.write_text("# Doc\n\nStub.", encoding="utf-8")
        result = engine._maybe_enhance_document(phrasing)
        assert result is not None, phrasing
        assert result["success"] is True, phrasing


def test_maybe_enhance_document_does_not_hijack_append_to_missing_file(engine, tmp_path):
    # "append" is a broad verb, but a non-existent target must fall through so
    # a real create/write path can handle it instead of the enhancer.
    missing = tmp_path / "nope.txt"
    assert engine._maybe_enhance_document(f"append a line to {missing}") is None


# ── workflow engine read_file support ────────────────────────────────────────


def test_workflow_engine_reads_file(engine, tmp_path):
    """A multi-step plan that begins by reading a file used to die on
    'Unknown filesystem action: read_file'; the workflow path now supports it."""
    from archon.parsers.command_parser import (
        CommandComplexity,
        ComplexCommand,
        ParsedStep,
    )

    f = tmp_path / "in.txt"
    f.write_text("payload", encoding="utf-8")
    cmd = ComplexCommand(
        original_command="read it",
        complexity=CommandComplexity.SIMPLE,
        steps=[ParsedStep(action="read_file", category="filesystem", params={"path": str(f)})],
        context={},
    )

    result = engine.workflow_engine.execute_workflow(cmd)

    assert result["success"] is True
    assert result["result"]["content"] == "payload"
