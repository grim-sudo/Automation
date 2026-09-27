"""
Archon - Universal OS Automation Framework
"""

from .bootstrap import load_env as _load_env

# Fold a project .env into os.environ before anything reads os.getenv(...).
_load_env()

from .core.engine import Archon  # noqa: E402
from .parsers.command_parser import AdvancedCommandParser as CommandParser  # noqa: E402
from .security.permission_manager import PermissionManager  # noqa: E402

__version__ = "2.0.0"
__author__ = "Archon Team"

__all__ = ["Archon", "CommandParser", "PermissionManager"]
