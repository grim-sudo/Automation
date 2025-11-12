"""
Factory for creating OS-specific adapters
"""

import platform
from typing import Any

from .base_adapter import BaseOSAdapter
from .windows_adapter import WindowsAdapter
from .linux_adapter import LinuxAdapter
from .macos_adapter import MacOSAdapter


class OSAdapterFactory:
    """Factory class for creating appropriate OS adapters"""
    
    @staticmethod
    def create_adapter() -> BaseOSAdapter:
        """Create an OS adapter based on the current platform"""
        system = platform.system().lower()
        
        if system == 'windows':
            return WindowsAdapter()
        elif system == 'linux':
            return LinuxAdapter()
        elif system == 'darwin':  # macOS
            return MacOSAdapter()
        else:
            raise NotImplementedError(f"OS '{system}' is not supported")
    
    @staticmethod
    def get_supported_platforms() -> list:
        """Get list of supported platforms"""
        return ['windows', 'linux', 'darwin']
