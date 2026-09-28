"""Textual message layer between Archon events and the widgets.

The controller runs the agent in a worker thread and translates Archon's
primitive event dicts into these strongly-typed Textual ``Message`` objects,
which are posted to the app and dispatched to widgets. This keeps the widgets
declarative (they react to messages) and the agent decoupled (it emits plain
dicts and never imports Textual).

Every message carries a ``gen`` (generation) id so that late messages from a
cancelled run are dropped instead of corrupting the current turn.
"""

from __future__ import annotations

from typing import Any

from textual.message import Message


class _GenMessage(Message):
    """Base for run-scoped messages tagged with a generation id."""

    def __init__(self, gen: int) -> None:
        super().__init__()
        self.gen = gen


class AssistantStarted(_GenMessage):
    """The model turn began (before any tokens)."""


class TokenReceived(_GenMessage):
    def __init__(self, gen: int, text: str) -> None:
        super().__init__(gen)
        self.text = text


class PhaseChanged(_GenMessage):
    def __init__(self, gen: int, phase: str) -> None:
        super().__init__(gen)
        self.phase = phase


class ToolStarted(_GenMessage):
    def __init__(self, gen: int, name: str, args: dict[str, Any], detail: str = "") -> None:
        super().__init__(gen)
        self.name = name
        self.args = args
        self.detail = detail


class ToolOk(_GenMessage):
    def __init__(self, gen: int, name: str, detail: str = "") -> None:
        super().__init__(gen)
        self.name = name
        self.detail = detail


class ToolError(_GenMessage):
    def __init__(self, gen: int, name: str, error: str, detail: str = "") -> None:
        super().__init__(gen)
        self.name = name
        self.error = error
        self.detail = detail


class ModelStats(_GenMessage):
    def __init__(self, gen: int, stats: dict[str, Any]) -> None:
        super().__init__(gen)
        self.stats = stats


class ReplyComplete(_GenMessage):
    def __init__(self, gen: int, reply: str) -> None:
        super().__init__(gen)
        self.reply = reply


class RunFailed(_GenMessage):
    def __init__(self, gen: int, summary: str, reason: str = "", action: str = "") -> None:
        super().__init__(gen)
        self.summary = summary
        self.reason = reason
        self.action = action


class SysInfo(Message):
    """A fresh system snapshot for the sidebar (not run-scoped)."""

    def __init__(self, snapshot: Any) -> None:
        super().__init__()
        self.snapshot = snapshot
