"""Native (Archon-owned) capabilities.

These are first-class capabilities implemented directly in Archon code, as
opposed to plugin-backed or remote (MCP) ones.  They are carved out of the
legacy plugins so the registry can expose them directly over time.
"""

from .documents import DocumentCapability
from .filesystem import FilesystemCapability

__all__ = ["DocumentCapability", "FilesystemCapability"]
