"""TUI widgets for the Archon console.

Each widget is a small, reusable component that reacts to state pushed in from
the app (which in turn reacts to Archon events). No widget reaches into engine
business logic: they render what they are given.
"""

from __future__ import annotations

from .activity import ActivityLog
from .composer import CommandInput
from .conversation import (
    AssistantMessage,
    ErrorView,
    StatusView,
    SystemMessage,
    UserMessage,
)
from .execution import ExecutionView, PlanView, ToolCallView
from .header import ArchonHeader
from .sidebar import Sidebar
from .status import StatusBar

__all__ = [
    "ActivityLog",
    "ArchonHeader",
    "AssistantMessage",
    "CommandInput",
    "ErrorView",
    "ExecutionView",
    "PlanView",
    "Sidebar",
    "StatusBar",
    "StatusView",
    "SystemMessage",
    "ToolCallView",
    "UserMessage",
]
