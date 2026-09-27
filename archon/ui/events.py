"""The event vocabulary Archon's execution layer speaks to the UI.

The renderer never inspects engine internals; instead the execution layer emits
small, declarative :class:`UIEvent` records describing *real* state transitions
(a tool started, a capability finished, a step failed). This keeps business
logic out of the renderer and gives future subsystems — MCP tools, Basic Memory
retrieval, alternate model backends, TurboQuant — a ready-made way to surface
their activity without touching presentation code.

Nothing here fabricates model reasoning. Events represent events that actually
happened in the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventKind(str, Enum):
    """What a :class:`UIEvent` represents."""

    PHASE = "phase"  # a new operational phase began (PLANNING / EXECUTING …)
    START = "start"  # an operation started running
    OK = "ok"  # an operation completed successfully
    ERROR = "error"  # an operation failed
    NOTE = "note"  # a neutral informational line (e.g. memory retrieved)


class Channel(str, Enum):
    """Which subsystem produced an event — becomes the section header.

    Only ``ARCHON`` is emitted today; the rest are declared so future
    subsystems slot into the same transcript without renderer changes.
    """

    ARCHON = "ARCHON"
    MCP = "MCP"
    MEMORY = "MEMORY"
    MODEL = "MODEL"
    CAPABILITY = "CAPABILITY"


@dataclass
class UIEvent:
    """A single, real state transition in the execution pipeline.

    Attributes:
        kind:    The transition type.
        channel: The producing subsystem (header the renderer groups under).
        label:   Short operation label, e.g. ``docker.list_containers``.
        detail:  Optional extra context (arguments preview, phase step text).
        error:   Human-readable error message when ``kind`` is ``ERROR``.
    """

    kind: EventKind
    channel: Channel = Channel.ARCHON
    label: str = ""
    detail: str = ""
    error: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


# Convenience constructors — keep call sites terse and intention-revealing.


def phase(name: str, channel: Channel = Channel.ARCHON) -> UIEvent:
    return UIEvent(EventKind.PHASE, channel, label=name)


def start(label: str, detail: str = "", channel: Channel = Channel.ARCHON) -> UIEvent:
    return UIEvent(EventKind.START, channel, label=label, detail=detail)


def ok(label: str, channel: Channel = Channel.ARCHON) -> UIEvent:
    return UIEvent(EventKind.OK, channel, label=label)


def error(label: str, message: str, channel: Channel = Channel.ARCHON) -> UIEvent:
    return UIEvent(EventKind.ERROR, channel, label=label, error=message)


__all__ = [
    "EventKind",
    "Channel",
    "UIEvent",
    "phase",
    "start",
    "ok",
    "error",
]
