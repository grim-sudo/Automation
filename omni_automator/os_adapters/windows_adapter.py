"""
Windows-specific OS adapter implementation
"""

import os
import sys
import shutil
import subprocess
import time
import psutil
import pyautogui
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path

from .base_adapter import (
    BaseOSAdapter, BaseFilesystemAdapter, BaseProcessAdapter,
    BaseGUIAdapter, BaseSystemAdapter, BaseNetworkAdapter
)

# Windows-specific imports
try:
    import win32api
    import win32con
    import win32gui
    import win32process
    import winreg
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


class WindowsFilesystemAdapter(BaseFilesystemAdapter):
    """Windows filesystem operations"""
    
    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute filesystem action"""
        try:
            # Input validation
            if not isinstance(action, str) or not action:
                raise ValueError("Action must be a non-empty string")
            if not isinstance(params, dict):
                raise ValueError("Params must be a dictionary")
            
            if action == 'create_folder':
                # Handle both old and new parameter formats
                name = params.get('name') or params.get('folder_name')
                location = params.get('location')
                if not name:
                    raise ValueError("Folder name is required")
                return self.create_folder(name, location)
            elif action == 'create_folders_batch':
                # Handle batch folder creation
                count = params.get('count', 1)
                start_name = params.get('start_name')
                end_name = params.get('end_name')
                location = params.get('location')
                return self.create_folders_batch(count, start_name, end_name, location)
            elif action == 'create_file':
                name = params.get('name')
                if not name:
                    raise ValueError("File name is required")
                return self.create_file(name, params.get('location'), params.get('content', ''))
            elif action == 'delete':
                path = params.get('path')
                if not path:
                    raise ValueError("Path is required for delete operation")
                return self.delete(path)
            elif action == 'copy':
                source = params.get('source')
                destination = params.get('destination')
                if not source or not destination:
                    raise ValueError("Source and destination are required for copy operation")
                return self.copy(source, destination)
            elif action == 'move':
                source = params.get('source')
                destination = params.get('destination')
                if not source or not destination:
                    raise ValueError("Source and destination are required for move operation")
                return self.move(source, destination)
            elif action == 'list':
                return self.list_directory(params.get('path', '.'))
            else:
                raise ValueError(f"Unknown filesystem action: {action}")
        except Exception as e:
            raise Exception(f"Filesystem operation failed: {e}")
    
    def get_capabilities(self) -> List[str]:
        return ['create_folder', 'create_file', 'delete', 'copy', 'move', 'list']
    
    def create_folder(self, name: str, location: str = None) -> bool:
        """Create a folder"""
        try:
            # Input validation
            if not name or not isinstance(name, str):
                raise ValueError("Folder name must be a non-empty string")
            
            # Sanitize folder name
            name = self._sanitize_filename(name)
            
            if location:
                if not isinstance(location, str):
                    raise ValueError("Location must be a string")
                # Validate location exists or can be created
                if not os.path.exists(location):
                    os.makedirs(location, exist_ok=True)
                path = os.path.join(location, name)
            else:
                path = name
            
            # Security check - prevent path traversal
            if '..' in path:
                raise ValueError("Invalid path detected - path traversal not allowed")
            
            os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            raise Exception(f"Failed to create folder '{name}': {e}")
    
    def create_folders_batch(self, count: int, start_name: str, end_name: str, location: str = None) -> dict:
        """Create multiple folders with names generated from start_name to end_name"""
        try:
            # Extract base name and number from start_name
            import re
            
            # Match pattern like "project1"
            match = re.match(r'([a-zA-Z_]+)(\d+)', start_name)
            if not match:
                raise ValueError(f"Invalid start_name format: {start_name}. Expected format like 'project1'")
            
            base_name = match.group(1)
            start_num = int(match.group(2))
            
            # Extract number from end_name
            match_end = re.match(r'([a-zA-Z_]+)(\d+)', end_name)
            if not match_end:
                raise ValueError(f"Invalid end_name format: {end_name}. Expected format like 'project10'")
            
            end_num = int(match_end.group(2))
            
            # Verify base names match
            if base_name != match_end.group(1):
                raise ValueError(f"Base names don't match: {base_name} vs {match_end.group(1)}")
            
            # Generate folder names and create them
            created_folders = []
            failed_folders = []
            
            for num in range(start_num, end_num + 1):
                folder_name = f"{base_name}{num}"
                try:
                    self.create_folder(folder_name, location)
                    created_folders.append(folder_name)
                except Exception as e:
                    failed_folders.append({
                        'name': folder_name,
                        'error': str(e)
                    })
            
            return {
                'success': len(failed_folders) == 0,
                'created': created_folders,
                'failed': failed_folders,
                'total_requested': count,
                'total_created': len(created_folders)
            }
            
        except Exception as e:
            raise Exception(f"Failed to create batch folders: {e}")

    def create_file(self, name: str, location: str = None, content: str = "") -> bool:
        """Create a file"""
        try:
            # Input validation
            if not name or not isinstance(name, str):
                raise ValueError("File name must be a non-empty string")
            if not isinstance(content, str):
                raise ValueError("Content must be a string")
            
            # Sanitize filename
            name = self._sanitize_filename(name)
            
            if location:
                if not isinstance(location, str):
                    raise ValueError("Location must be a string")
                path = os.path.join(location, name)
            else:
                path = name
            
            # Security check - prevent path traversal
            if '..' in path:
                raise ValueError("Invalid path detected - path traversal not allowed")
            
            # Ensure directory exists
            dir_path = os.path.dirname(path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            raise Exception(f"Failed to create file '{name}': {e}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent issues"""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove leading/trailing spaces and dots
        filename = filename.strip(' .')
        
        # Ensure filename is not empty after sanitization
        if not filename:
            filename = 'unnamed'
        
        return filename
    
    def delete(self, path: str, recursive: bool = True) -> bool:
        """Delete file or folder"""
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                if recursive:
                    shutil.rmtree(path)
                else:
                    os.rmdir(path)
            return True
        except Exception as e:
            raise Exception(f"Failed to delete: {e}")
    
    def copy(self, source: str, destination: str) -> bool:
        """Copy file or folder"""
        try:
            if os.path.isfile(source):
                shutil.copy2(source, destination)
            elif os.path.isdir(source):
                shutil.copytree(source, destination)
            return True
        except Exception as e:
            raise Exception(f"Failed to copy: {e}")
    
    def move(self, source: str, destination: str) -> bool:
        """Move file or folder"""
        try:
            shutil.move(source, destination)
            return True
        except Exception as e:
            raise Exception(f"Failed to move: {e}")
    
    def list_directory(self, path: str) -> List[Dict[str, Any]]:
        """List directory contents"""
        try:
            items = []
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                stat = os.stat(item_path)
                items.append({
                    'name': item,
                    'path': item_path,
                    'type': 'directory' if os.path.isdir(item_path) else 'file',
                    'size': stat.st_size,
                    'modified': stat.st_mtime
                })
            return items
        except Exception as e:
            raise Exception(f"Failed to list directory: {e}")
    
    def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get file/folder information"""
        try:
            stat = os.stat(path)
            return {
                'path': path,
                'type': 'directory' if os.path.isdir(path) else 'file',
                'size': stat.st_size,
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'accessed': stat.st_atime
            }
        except Exception as e:
            raise Exception(f"Failed to get file info: {e}")


class WindowsProcessAdapter(BaseProcessAdapter):
    """Windows process management"""
    
    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute process action"""
        if action == 'start' or action == 'launch_application':
            # Accept both 'start' and 'launch_application' as aliases
            # normalize parameter names: program or application or exe
            prog = params.get('program') or params.get('application') or params.get('exe') or params.get('path')
            return self.start_process(prog, params.get('args'))
        elif action == 'terminate':
            return self.terminate_process(params.get('program'))
        elif action == 'list':
            return self.list_processes()
        else:
            raise ValueError(f"Unknown process action: {action}")
    
    def get_capabilities(self) -> List[str]:
        return ['start', 'launch_application', 'terminate', 'list']
    
    def start_process(self, program: str, args: List[str] = None) -> int:
        """Start a new process"""
        try:
            cmd = [program]
            if args:
                if isinstance(args, str):
                    cmd.extend(args.split())
                else:
                    cmd.extend(args)
            
            process = subprocess.Popen(cmd, shell=True)
            return process.pid
        except Exception as e:
            raise Exception(f"Failed to start process: {e}")
    
    def terminate_process(self, pid_or_name: Any) -> bool:
        """Terminate a process by PID or name"""
        try:
            if isinstance(pid_or_name, int):
                # Terminate by PID
                process = psutil.Process(pid_or_name)
                process.terminate()
            else:
                # Terminate by name
                for proc in psutil.process_iter(['pid', 'name']):
                    if proc.info['name'].lower() == pid_or_name.lower():
                        proc.terminate()
            return True
        except Exception as e:
            raise Exception(f"Failed to terminate process: {e}")
    
    def list_processes(self) -> List[Dict[str, Any]]:
        """List running processes"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                try:
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu_percent': proc.info['cpu_percent'],
                        'memory_mb': proc.info['memory_info'].rss / 1024 / 1024
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return processes
        except Exception as e:
            raise Exception(f"Failed to list processes: {e}")
    
    def get_process_info(self, pid: int) -> Dict[str, Any]:
        """Get process information"""
        try:
            proc = psutil.Process(pid)
            return {
                'pid': proc.pid,
                'name': proc.name(),
                'status': proc.status(),
                'cpu_percent': proc.cpu_percent(),
                'memory_info': proc.memory_info()._asdict(),
                'create_time': proc.create_time()
            }
        except Exception as e:
            raise Exception(f"Failed to get process info: {e}")


class WindowsGUIAdapter(BaseGUIAdapter):
    """Windows GUI automation"""
    
    def __init__(self):
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1
    
    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute GUI action"""
        if action == 'click':
            return self.click(params.get('x'), params.get('y'), params.get('button', 'left'))
        elif action == 'type':
            return self.type_text(params.get('text'))
        elif action == 'press_key':
            return self.press_key(params.get('key'))
        elif action == 'screenshot':
            return self.take_screenshot(params.get('filename'))
        elif action == 'wait':
            time.sleep(float(params.get('duration', 1)))
            return True
        elif action == 'wait_for_page_load':
            # Best-effort: wait a short time for browser to load content
            time.sleep(float(params.get('timeout', 2)))
            return True
        else:
            raise ValueError(f"Unknown GUI action: {action}")
    
    def get_capabilities(self) -> List[str]:
        # Windows GUI capabilities (no headless browser on Windows)
        return ['click', 'type', 'press_key', 'screenshot', 'wait', 'wait_for_page_load', 'open_browser', 'navigate_to_url', 'take_screenshot', 'close_browser']
    
    def click(self, x: int = None, y: int = None, button: str = 'left') -> bool:
        """Click at coordinates or current position"""
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y, button=button)
            else:
                pyautogui.click(button=button)
            return True
        except Exception as e:
            raise Exception(f"Failed to click: {e}")
    
    def type_text(self, text: str) -> bool:
        """Type text"""
        try:
            pyautogui.typewrite(text)
            return True
        except Exception as e:
            raise Exception(f"Failed to type text: {e}")
    
    def press_key(self, key: str) -> bool:
        """Press a key"""
        try:
            pyautogui.press(key)
            return True
        except Exception as e:
            raise Exception(f"Failed to press key: {e}")
    
    def take_screenshot(self, filename: str = None) -> str:
        """Take screenshot"""
        try:
            if not filename:
                filename = f"screenshot_{int(time.time())}.png"
            
            screenshot = pyautogui.screenshot()
            screenshot.save(filename)
            return filename
        except Exception as e:
            raise Exception(f"Failed to take screenshot: {e}")
    
    def find_element(self, image_path: str) -> Dict[str, int]:
        """Find element by image"""
        try:
            location = pyautogui.locateOnScreen(image_path)
            if location:
                center = pyautogui.center(location)
                return {'x': center.x, 'y': center.y}
            else:
                raise Exception("Element not found")
        except Exception as e:
            raise Exception(f"Failed to find element: {e}")


class WindowsSystemAdapter(BaseSystemAdapter):
    """Windows system operations"""
    
    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute system action"""
        if action == 'get_info':
            return self.get_system_info()
        elif action == 'set_volume':
            return self.set_volume(int(params.get('level', 50)))
        elif action == 'power_action':
            return self.power_action(params.get('action'))
        else:
            raise ValueError(f"Unknown system action: {action}")
    
    def get_capabilities(self) -> List[str]:
        return ['get_info', 'set_volume', 'power_action']
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            import platform
            
            return {
                'platform': platform.platform(),
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'memory_available': psutil.virtual_memory().available,
                'disk_usage': {
                    'total': psutil.disk_usage('/').total,
                    'used': psutil.disk_usage('/').used,
                    'free': psutil.disk_usage('/').free
                }
            }
        except Exception as e:
            raise Exception(f"Failed to get system info: {e}")
    
    def set_volume(self, level: int) -> bool:
        """Set system volume (0-100)"""
        try:
            if HAS_WIN32:
                # Use Windows API to set volume
                import pycaw.pycaw as pycaw
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = interface.QueryInterface(IAudioEndpointVolume)
                volume.SetMasterScalarVolume(level / 100.0, None)
                return True
            else:
                # Fallback using nircmd or other tools
                subprocess.run(['nircmd', 'setsysvolume', str(int(level * 655.35))], check=True)
                return True
        except Exception as e:
            raise Exception(f"Failed to set volume: {e}")
    
    def power_action(self, action: str) -> bool:
        """Perform power action"""
        try:
            if action.lower() in ['shutdown', 'poweroff']:
                subprocess.run(['shutdown', '/s', '/t', '0'], check=True)
            elif action.lower() in ['restart', 'reboot']:
                subprocess.run(['shutdown', '/r', '/t', '0'], check=True)
            elif action.lower() == 'hibernate':
                subprocess.run(['shutdown', '/h'], check=True)
            else:
                raise ValueError(f"Unknown power action: {action}")
            return True
        except Exception as e:
            raise Exception(f"Failed to perform power action: {e}")
    
    def get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables"""
        return dict(os.environ)


class WindowsNetworkAdapter(BaseNetworkAdapter):
    """Windows network operations"""
    
    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute network action"""
        if action == 'download':
            return self.download_file(params.get('url'), params.get('filename'))
        elif action == 'http_get':
            return self.http_request('GET', params.get('url'))
        else:
            raise ValueError(f"Unknown network action: {action}")
    
    def get_capabilities(self) -> List[str]:
        return ['download', 'http_get', 'http_post']
    
    def download_file(self, url: str, filename: str = None) -> str:
        """Download file from URL"""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            if not filename:
                filename = url.split('/')[-1] or 'downloaded_file'
            
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return filename
        except Exception as e:
            raise Exception(f"Failed to download file: {e}")
    
    def http_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request"""
        try:
            response = requests.request(method, url, **kwargs)
            return {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'content': response.text,
                'json': response.json() if 'application/json' in response.headers.get('content-type', '') else None
            }
        except Exception as e:
            raise Exception(f"Failed to make HTTP request: {e}")
    
    def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        try:
            import socket
            
            return {
                'hostname': socket.gethostname(),
                'ip_address': socket.gethostbyname(socket.gethostname()),
                'network_interfaces': [
                    {
                        'name': interface,
                        'addresses': [addr.address for addr in addrs]
                    }
                    for interface, addrs in psutil.net_if_addrs().items()
                ]
            }
        except Exception as e:
            raise Exception(f"Failed to get network info: {e}")


class WindowsAdapter(BaseOSAdapter):
    """Windows OS adapter"""
    
    def _create_filesystem_adapter(self) -> BaseFilesystemAdapter:
        return WindowsFilesystemAdapter()
    
    def _create_process_adapter(self) -> BaseProcessAdapter:
        return WindowsProcessAdapter()
    
    def _create_gui_adapter(self) -> BaseGUIAdapter:
        return WindowsGUIAdapter()
    
    def _create_system_adapter(self) -> BaseSystemAdapter:
        return WindowsSystemAdapter()
    
    def _create_network_adapter(self) -> BaseNetworkAdapter:
        return WindowsNetworkAdapter()
