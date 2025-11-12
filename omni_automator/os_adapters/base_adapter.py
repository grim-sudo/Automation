"""
Base OS adapter interface that all platform-specific adapters must implement
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseModuleAdapter(ABC):
    """Base class for OS module adapters (filesystem, process, etc.)"""
    
    @abstractmethod
    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute an action with given parameters"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Get list of supported actions"""
        pass


class BaseFilesystemAdapter(BaseModuleAdapter):
    """Base filesystem operations adapter"""
    
    @abstractmethod
    def create_folder(self, path: str, parents: bool = True) -> bool:
        """Create a folder"""
        pass
    
    @abstractmethod
    def create_file(self, path: str, content: str = "") -> bool:
        """Create a file"""
        pass
    
    @abstractmethod
    def delete(self, path: str, recursive: bool = False) -> bool:
        """Delete file or folder"""
        pass
    
    @abstractmethod
    def copy(self, source: str, destination: str) -> bool:
        """Copy file or folder"""
        pass
    
    @abstractmethod
    def move(self, source: str, destination: str) -> bool:
        """Move file or folder"""
        pass
    
    @abstractmethod
    def list_directory(self, path: str) -> List[Dict[str, Any]]:
        """List directory contents"""
        pass
    
    @abstractmethod
    def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get file/folder information"""
        pass


class BaseProcessAdapter(BaseModuleAdapter):
    """Base process management adapter"""
    
    @abstractmethod
    def start_process(self, program: str, args: List[str] = None) -> int:
        """Start a new process"""
        pass
    
    @abstractmethod
    def terminate_process(self, pid_or_name: Any) -> bool:
        """Terminate a process by PID or name"""
        pass
    
    @abstractmethod
    def list_processes(self) -> List[Dict[str, Any]]:
        """List running processes"""
        pass
    
    @abstractmethod
    def get_process_info(self, pid: int) -> Dict[str, Any]:
        """Get process information"""
        pass


class BaseGUIAdapter(BaseModuleAdapter):
    """Base GUI automation adapter"""
    
    @abstractmethod
    def click(self, x: int, y: int, button: str = 'left') -> bool:
        """Click at coordinates"""
        pass
    
    @abstractmethod
    def type_text(self, text: str) -> bool:
        """Type text"""
        pass
    
    @abstractmethod
    def press_key(self, key: str) -> bool:
        """Press a key"""
        pass
    
    @abstractmethod
    def take_screenshot(self, filename: str = None) -> str:
        """Take screenshot"""
        pass
    
    @abstractmethod
    def find_element(self, image_path: str) -> Dict[str, int]:
        """Find element by image"""
        pass


class BaseSystemAdapter(BaseModuleAdapter):
    """Base system operations adapter"""
    
    @abstractmethod
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        pass
    
    @abstractmethod
    def set_volume(self, level: int) -> bool:
        """Set system volume"""
        pass
    
    @abstractmethod
    def power_action(self, action: str) -> bool:
        """Perform power action (shutdown, restart, etc.)"""
        pass
    
    @abstractmethod
    def get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables"""
        pass


class BaseNetworkAdapter(BaseModuleAdapter):
    """Base network operations adapter"""
    
    @abstractmethod
    def download_file(self, url: str, filename: str = None) -> str:
        """Download file from URL"""
        pass
    
    @abstractmethod
    def http_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request"""
        pass
    
    @abstractmethod
    def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        pass


class BaseOSAdapter(ABC):
    """Base OS adapter that coordinates all module adapters"""
    
    def __init__(self):
        self.filesystem = self._create_filesystem_adapter()
        self.process = self._create_process_adapter()
        self.gui = self._create_gui_adapter()
        self.system = self._create_system_adapter()
        self.network = self._create_network_adapter()
    
    @abstractmethod
    def _create_filesystem_adapter(self) -> BaseFilesystemAdapter:
        """Create filesystem adapter"""
        pass
    
    @abstractmethod
    def _create_process_adapter(self) -> BaseProcessAdapter:
        """Create process adapter"""
        pass
    
    @abstractmethod
    def _create_gui_adapter(self) -> BaseGUIAdapter:
        """Create GUI adapter"""
        pass
    
    @abstractmethod
    def _create_system_adapter(self) -> BaseSystemAdapter:
        """Create system adapter"""
        pass
    
    @abstractmethod
    def _create_network_adapter(self) -> BaseNetworkAdapter:
        """Create network adapter"""
        pass
    
    def cleanup(self):
        """Cleanup adapter resources"""
        pass
