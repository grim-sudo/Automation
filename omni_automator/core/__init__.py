"""
Core automation engine components
"""

from ..parsers.command_parser import AdvancedCommandParser as CommandParser
from .engine import OmniAutomator
from .plugin_manager import AutomationPlugin, PluginManager

__all__ = ["OmniAutomator", "CommandParser", "PluginManager", "AutomationPlugin"]
