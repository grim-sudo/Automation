"""
Tyranos - Universal OS Automation Framework
"""

from .core.engine import Tyranos
from .parsers.command_parser import AdvancedCommandParser as CommandParser
from .security.permission_manager import PermissionManager

__version__ = "1.0.0"
__author__ = "Tyranos Team"

__all__ = ["Tyranos", "CommandParser", "PermissionManager"]
