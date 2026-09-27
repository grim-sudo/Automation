"""
User interfaces for Archon.

The desktop GUI is the Tauri command center under ``ui-tauri/`` (launched via
``archon gui``). This package holds the terminal interfaces: the CLI and the
chatbot.
"""

from __future__ import annotations

from .chatbot import ChatbotMode, get_chatbot
from .cli import EnhancedCLI

__all__ = ["EnhancedCLI", "ChatbotMode", "get_chatbot"]
