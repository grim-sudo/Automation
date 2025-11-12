"""
OS-specific adapter implementations
"""

from .adapter_factory import OSAdapterFactory
from .base_adapter import BaseOSAdapter

__all__ = ["OSAdapterFactory", "BaseOSAdapter"]
