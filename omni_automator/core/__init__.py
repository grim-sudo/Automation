"""
Core automation engine components
"""

from .engine import OmniAutomator
from .command_parser import CommandParser
from .plugin_manager import PluginManager, AutomationPlugin

__all__ = ["OmniAutomator", "CommandParser", "PluginManager", "AutomationPlugin"]
