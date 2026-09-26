"""
User interfaces for Archon.

The GUI (``ModernArchonGUI``) is imported lazily so that importing the CLI or
chatbot never requires a Tk/CustomTkinter toolkit to be installed.
"""

from __future__ import annotations

from typing import Any

from .chatbot import ChatbotMode, get_chatbot
from .cli import EnhancedCLI

__all__ = ["EnhancedCLI", "ChatbotMode", "get_chatbot", "ModernArchonGUI"]


def __getattr__(name: str) -> Any:
    """Lazily resolve ``ModernArchonGUI`` to avoid importing Tk at module load."""
    if name == "ModernArchonGUI":
        from .gui import ModernArchonGUI

        return ModernArchonGUI
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
