"""
OmniAutomator - Universal OS Automation Framework
"""

from .core.engine import OmniAutomator
from .core.advanced_parser import AdvancedCommandParser as CommandParser
from .security.permission_manager import PermissionManager

__version__ = "1.0.0"
__author__ = "OmniAutomator Team"

__all__ = ["OmniAutomator", "CommandParser", "PermissionManager"]
