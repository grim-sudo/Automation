"""
Core automation engine components
"""

from .engine import OmniAutomator
from .advanced_parser import AdvancedCommandParser as CommandParser
from .plugin_manager import PluginManager, AutomationPlugin

__all__ = ["OmniAutomator", "CommandParser", "PluginManager", "AutomationPlugin"]
