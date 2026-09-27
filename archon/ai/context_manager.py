"""Sliding-window conversation context manager with token counting."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Optional tiktoken import
# ---------------------------------------------------------------------------

try:
    import tiktoken as _tiktoken

    def _make_encoder(model: str) -> Any:
        """Return a tiktoken encoder, falling back to cl100k_base."""
        try:
            return _tiktoken.encoding_for_model(model)
        except (KeyError, Exception):
            return _tiktoken.get_encoding("cl100k_base")

    def _encode(encoder: Any, text: str) -> int:
        """Return the number of tokens in *text* using *encoder*."""
        return len(encoder.encode(text))

    _HAS_TIKTOKEN = True

except ImportError:
    _HAS_TIKTOKEN = False

    def _make_encoder(model: str) -> None:  # type: ignore[misc]
        return None

    def _encode(encoder: Any, text: str) -> int:  # type: ignore[misc]
        # Heuristic: ~4 chars per token (GPT tokeniser average)
        return max(1, len(text) // 4)


__all__ = [
    "Message",
    "ContextManager",
    # Backward-compat alias kept for existing imports
    "ContextWindow",
]


# ---------------------------------------------------------------------------
# Message dataclass
# ---------------------------------------------------------------------------


@dataclass
class Message:
    """A single chat message in the conversation history.

    Attributes:
        role:        One of ``"system"``, ``"user"``, ``"assistant"``.
        content:     Text content of the message.
        token_count: Cached token count (populated on creation).
        timestamp:   Unix timestamp of when the message was created.
    """

    role: str
    content: str
    token_count: int = field(default=0)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, str]:
        """Return the OpenAI-compatible message dict.

        Returns:
            ``{"role": ..., "content": ...}``
        """
        return {"role": self.role, "content": self.content}


# ---------------------------------------------------------------------------
# ContextManager
# ---------------------------------------------------------------------------


class ContextManager:
    """Sliding-window conversation context manager with token counting.

    Maintains a rolling window of ``(role, content)`` message pairs that
    fits within a configurable token budget.  The system prompt is *always*
    kept; the most-recent N user/assistant turns that still fit are retained.

    Token counting uses ``tiktoken`` when installed, falling back to a
    character-count heuristic (``len(text) // 4``) if not.

    Args:
        max_tokens: Maximum total tokens allowed in the window.
        model:      Model name passed to ``tiktoken.encoding_for_model``.
                    Falls back to ``"cl100k_base"`` for unknown models.

    Example::

        ctx = ContextManager(max_tokens=8000)
        ctx.set_system_prompt("You are a helpful assistant.")
        ctx.add_message("user", "Open my browser")
        ctx.add_message("assistant", '{"steps": []}')
        messages = ctx.get_messages()  # pass directly to the Ollama chat API
    """

    def __init__(self, max_tokens: int = 8000, model: str = "cl100k_base") -> None:
        self.max_tokens = max_tokens
        self._model = model
        self._messages: list[Message] = []
        self._system_prompt: str = ""
        self._system_message: Message | None = None
        # Initialise the tiktoken encoder (or the fallback stub)
        self._encoder: Any = _make_encoder(model)

    # ── System prompt ─────────────────────────────────────────────────────────

    def set_system_prompt(self, prompt: str) -> None:
        """Replace the system prompt.

        The system prompt is always included in :meth:`get_messages` and is
        never evicted by the sliding-window trim.

        Args:
            prompt: New system prompt text.
        """
        self._system_prompt = prompt
        if prompt:
            msg = Message(role="system", content=prompt)
            msg.token_count = self._count_tokens(prompt)
            self._system_message = msg
        else:
            self._system_message = None

    # ── Adding messages ───────────────────────────────────────────────────────

    def add_message(self, role: str, content: str) -> None:
        """Append a message to the conversation history.

        After appending, :meth:`_trim_to_fit` is called so the window always
        stays within budget.

        Args:
            role:    One of ``"system"``, ``"user"``, ``"assistant"``.
            content: Text of the message.
        """
        if role == "system":
            # Treat system messages as a set_system_prompt call
            self.set_system_prompt(content)
            return

        msg = Message(role=role, content=content)
        msg.token_count = self._count_tokens(content)
        self._messages.append(msg)
        self._trim_to_fit()

    # ── Querying ──────────────────────────────────────────────────────────────

    def get_messages(self) -> list[dict[str, str]]:
        """Return the current window in OpenAI message-list format.

        The system message is always first; user/assistant turns follow in
        chronological order.

        Returns:
            List of ``{"role": ..., "content": ...}`` dicts.
        """
        result: list[dict[str, str]] = []
        if self._system_message is not None:
            result.append(self._system_message.to_dict())

        budget = self.max_tokens - (self._system_message.token_count if self._system_message else 0)

        # Walk newest-to-oldest, collect turns that fit within budget
        fitting: list[Message] = []
        used = 0
        for msg in reversed(self._messages):
            if used + msg.token_count > budget:
                break
            fitting.append(msg)
            used += msg.token_count

        result.extend(m.to_dict() for m in reversed(fitting))
        return result

    def token_usage(self) -> dict[str, int]:
        """Return a summary of the current token budget usage.

        Returns:
            A dict with keys ``"used"``, ``"max"``, and ``"remaining"``.
        """
        used = self._total_tokens()
        return {
            "used": used,
            "max": self.max_tokens,
            "remaining": max(0, self.max_tokens - used),
        }

    # ── Mutation ──────────────────────────────────────────────────────────────

    def clear(self) -> None:
        """Remove all messages, including the system prompt."""
        self._messages.clear()
        self._system_prompt = ""
        self._system_message = None

    def clear_turns(self) -> None:
        """Remove all user/assistant turns but keep the system prompt."""
        self._messages.clear()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _count_tokens(self, text: str) -> int:
        """Return the token count for *text* using the configured encoder.

        Args:
            text: String to count.

        Returns:
            Integer token count.
        """
        return _encode(self._encoder, text)

    def _total_tokens(self) -> int:
        """Return the total token count of the currently visible messages.

        Mirrors the logic in :meth:`get_messages`: counts the system message
        (always present) plus the newest turns that fit the budget.

        Returns:
            Integer token count.
        """
        system_tokens = self._system_message.token_count if self._system_message else 0
        budget = self.max_tokens - system_tokens
        used = 0
        for msg in reversed(self._messages):
            if used + msg.token_count > budget:
                break
            used += msg.token_count
        return system_tokens + used

    def _trim_to_fit(self) -> None:
        """Remove the oldest non-system messages until the window fits budget.

        Called automatically by :meth:`add_message` after each insertion.
        """
        system_tokens = self._system_message.token_count if self._system_message else 0
        budget = self.max_tokens - system_tokens
        total = sum(m.token_count for m in self._messages)

        # Drop from the front (oldest) until we fit
        while total > budget and self._messages:
            removed = self._messages.pop(0)
            total -= removed.token_count

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialise the context window to a plain dict for persistence.

        Returns:
            Dict with keys ``system``, ``turns``, ``max_tokens``, and ``model``.
        """
        return {
            "system": self._system_prompt or None,
            "turns": [
                {
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp,
                    "token_count": m.token_count,
                }
                for m in self._messages
            ],
            "max_tokens": self.max_tokens,
            "model": self._model,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContextManager:
        """Reconstruct a :class:`ContextManager` from a serialised dict.

        Args:
            data: Dict as returned by :meth:`to_dict`.

        Returns:
            New :class:`ContextManager` instance.
        """
        obj = cls(
            max_tokens=data.get("max_tokens", 8000),
            model=data.get("model", "cl100k_base"),
        )
        if data.get("system"):
            obj.set_system_prompt(data["system"])
        for t in data.get("turns", []):
            role = t.get("role", "user")
            content = t.get("content", "")
            msg = Message(
                role=role,
                content=content,
                timestamp=t.get("timestamp", time.time()),
                token_count=t.get("token_count", 0),
            )
            if msg.token_count == 0:
                msg.token_count = obj._count_tokens(content)
            obj._messages.append(msg)
        obj._trim_to_fit()
        return obj

    def __repr__(self) -> str:
        usage = self.token_usage()
        return (
            f"ContextManager(max={self.max_tokens}, "
            f"used={usage['used']}, "
            f"turns={len(self._messages)})"
        )


# ---------------------------------------------------------------------------
# ContextWindow — backward-compat wrapper for existing imports
# ---------------------------------------------------------------------------


class ContextWindow:
    """Backward-compatible sliding-window API used by existing code.

    Delegates to :class:`ContextManager` internally.  New code should use
    :class:`ContextManager` directly.

    Args:
        max_tokens:    Maximum total tokens in the window.
        system_prompt: Initial system prompt (can be changed later via
                       :meth:`set_system_prompt`).
    """

    def __init__(self, max_tokens: int = 8000, system_prompt: str = "") -> None:
        self._ctx = ContextManager(max_tokens=max_tokens)
        if system_prompt:
            self._ctx.set_system_prompt(system_prompt)

    def set_system_prompt(self, text: str) -> None:
        """Replace the system prompt."""
        self._ctx.set_system_prompt(text)

    def add_user(self, content: str) -> None:
        """Append a user message."""
        self._ctx.add_message("user", content)

    def add_assistant(self, content: str) -> None:
        """Append an assistant message."""
        self._ctx.add_message("assistant", content)

    def clear_turns(self) -> None:
        """Drop all user/assistant turns but keep the system prompt."""
        self._ctx.clear_turns()

    def get_messages(self) -> list[dict[str, str]]:
        """Return the current window as an OpenAI-compatible message list."""
        return self._ctx.get_messages()

    def token_count(self) -> int:
        """Return total token count of the current window."""
        return self._ctx._total_tokens()

    def remaining_budget(self) -> int:
        """Return how many tokens remain before the window is full."""
        return self._ctx.token_usage()["remaining"]

    @property
    def turn_count(self) -> int:
        """Total number of stored turns (before trimming)."""
        return len(self._ctx._messages)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict."""
        return self._ctx.to_dict()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContextWindow:
        """Reconstruct from a serialised dict."""
        obj = cls.__new__(cls)
        obj._ctx = ContextManager.from_dict(data)
        return obj

    def __repr__(self) -> str:
        return (
            f"ContextWindow(max={self._ctx.max_tokens}, "
            f"used={self._ctx._total_tokens()}, "
            f"turns={self.turn_count})"
        )
