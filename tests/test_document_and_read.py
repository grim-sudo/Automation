"""Regression tests for the document-generation + file-read fixes.

Covers the failures seen when asking the agent to write a documentation file:
- document generation aborted at the chat-tier ~120s timeout, so the body was
  never produced (now uses a generous document timeout),
- the follow-up "read the file" step died on an unknown ``read_file``
  filesystem action (now supported by the Arch adapter and the permission map).
"""

from __future__ import annotations

from archon.ai.automation_ai import _DOCUMENT_TIMEOUT, OllamaAutomationAI
from archon.os_adapters.arch_adapter import ArchFilesystemAdapter
from archon.security.permission_manager import ActionCategory, PermissionManager

# ── document generation timeout wiring ───────────────────────────────────────


class _CapturingProvider:
    """Records the kwargs a completion call receives."""

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
        self.captured = {"timeout": timeout, "max_tokens": max_tokens}
        return "# Pizza\n\nDough, sauce, cheese."


def _ai_with_provider(provider) -> OllamaAutomationAI:  # noqa: ANN001
    ai = OllamaAutomationAI.__new__(OllamaAutomationAI)
    ai._is_available = True
    ai._ollama = provider
    return ai


def test_generate_document_uses_long_timeout_not_chat_default():
    provider = _CapturingProvider()
    ai = _ai_with_provider(provider)

    out = ai.generate_document("write about pizza", filename="pizza.md")

    assert out.startswith("# Pizza")
    # The chat-tier ~120s ceiling would abort a valid document mid-stream.
    assert provider.captured["timeout"] == _DOCUMENT_TIMEOUT
    assert _DOCUMENT_TIMEOUT >= 300


def test_generate_document_returns_empty_when_offline():
    ai = OllamaAutomationAI.__new__(OllamaAutomationAI)
    ai._is_available = False
    assert ai.generate_document("anything") == ""


# ── filesystem read_file support ─────────────────────────────────────────────


def test_read_file_roundtrip(tmp_path):
    fs = ArchFilesystemAdapter()
    target = tmp_path / "note.txt"
    fs.execute("create_file", {"name": "note.txt", "location": str(tmp_path), "content": "hi"})

    result = fs.execute("read_file", {"path": str(target)})

    assert result["success"] is True
    assert result["content"] == "hi"


def test_read_alias_matches_read_file(tmp_path):
    fs = ArchFilesystemAdapter()
    target = tmp_path / "a.md"
    target.write_text("# Doc", encoding="utf-8")

    assert fs.execute("read", {"path": str(target)})["content"] == "# Doc"


def test_read_file_missing_is_reported_not_raised(tmp_path):
    fs = ArchFilesystemAdapter()
    result = fs.execute("read_file", {"path": str(tmp_path / "nope.txt")})
    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_read_file_in_capabilities():
    assert "read_file" in ArchFilesystemAdapter().get_capabilities()


# ── permission mapping ───────────────────────────────────────────────────────


def test_read_file_maps_to_filesystem_read():
    pm = PermissionManager()
    assert pm._map_to_action_category("filesystem", "read_file") is ActionCategory.FILESYSTEM_READ
    assert pm._map_to_action_category("filesystem", "read") is ActionCategory.FILESYSTEM_READ
