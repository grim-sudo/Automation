"""
Factory for creating OS-specific adapters
"""

import platform
import os
from typing import Any

from .base_adapter import BaseOSAdapter
from .windows_adapter import WindowsAdapter
from .linux_adapter import LinuxAdapter
from .macos_adapter import MacOSAdapter
from .arch_adapter import ArchLinuxAdapter


def is_arch_based() -> bool:
    """Detect if the system is Arch-based"""
    try:
        # Check /etc/os-release
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release', 'r') as f:
                content = f.read().lower()
                if any(distro in content for distro in ['arch', 'manjaro', 'endeavour', 'garuda']):
                    return True
        
        # Check for pacman
        if os.path.exists('/usr/bin/pacman'):
            return True
        
        # Check /etc/arch-release
        if os.path.exists('/etc/arch-release'):
            return True
            
    except:
        pass
    
    return False


class OSAdapterFactory:
    """Factory class for creating appropriate OS adapters"""
    
    @staticmethod
    def create_adapter() -> BaseOSAdapter:
        """Create an OS adapter based on the current platform"""
        system = platform.system().lower()
        
        if system == 'windows':
            return WindowsAdapter()
        elif system == 'linux':
            # Detect specific Linux distribution
            if is_arch_based():
                print("🐧 Detected Arch Linux-based system")
                return ArchLinuxAdapter()
            else:
                print("🐧 Detected Linux system (generic)")
                return LinuxAdapter()
        elif system == 'darwin':  # macOS
            return MacOSAdapter()
        else:
            raise NotImplementedError(f"OS '{system}' is not supported")
    
    @staticmethod
    def get_supported_platforms() -> list:
        """Get list of supported platforms"""
        return ['windows', 'linux', 'linux-arch', 'darwin']
