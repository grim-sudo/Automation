"""
Linux-specific OS adapter implementation
"""

import os
import shutil
import subprocess
import time
import psutil
import pyautogui
import requests
from typing import Dict, Any, List
from pathlib import Path

from .base_adapter import (
    BaseOSAdapter, BaseFilesystemAdapter, BaseProcessAdapter,
    BaseGUIAdapter, BaseSystemAdapter, BaseNetworkAdapter
)

# Linux-specific imports
try:
    import Xlib.display
    import Xlib.X
    HAS_XLIB = True
except ImportError:
    HAS_XLIB = False


class LinuxFilesystemAdapter(BaseFilesystemAdapter):
    """Linux filesystem operations - inherits most from Windows but with Linux-specific paths"""
    
    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        if action == 'create_folder':
            return self.create_folder(params.get('name'), params.get('location'))
        elif action == 'create_file':
            return self.create_file(params.get('name'), params.get('location'))
        elif action == 'delete':
            return self.delete(params.get('path'))
        elif action == 'copy':
            return self.copy(params.get('source'), params.get('destination'))
        elif action == 'move':
            return self.move(params.get('source'), params.get('destination'))
        elif action == 'list':
            return self.list_directory(params.get('path', '.'))
        else:
            raise ValueError(f"Unknown filesystem action: {action}")
    
    def get_capabilities(self) -> List[str]:
        return ['create_folder', 'create_file', 'delete', 'copy', 'move', 'list']
    
    def create_folder(self, name: str, location: str = None) -> bool:
        if location:
            path = os.path.join(location, name)
        else:
            path = name
        
        try:
            os.makedirs(path, exist_ok=True)
            # Set proper permissions on Linux
            os.chmod(path, 0o755)
            return True
        except Exception as e:
            raise Exception(f"Failed to create folder: {e}")
    
    def create_file(self, name: str, location: str = None, content: str = "") -> bool:
        if location:
            path = os.path.join(location, name)
        else:
            path = name
        
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            os.chmod(path, 0o644)
            return True
        except Exception as e:
            raise Exception(f"Failed to create file: {e}")
    
    def delete(self, path: str, recursive: bool = True) -> bool:
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
        try:
            if os.path.isfile(source):
                shutil.copy2(source, destination)
            elif os.path.isdir(source):
                shutil.copytree(source, destination)
            return True
        except Exception as e:
            raise Exception(f"Failed to copy: {e}")
    
    def move(self, source: str, destination: str) -> bool:
        try:
            shutil.move(source, destination)
            return True
        except Exception as e:
            raise Exception(f"Failed to move: {e}")
    
    def list_directory(self, path: str) -> List[Dict[str, Any]]:
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
                    'modified': stat.st_mtime,
                    'permissions': oct(stat.st_mode)[-3:]
                })
            return items
        except Exception as e:
            raise Exception(f"Failed to list directory: {e}")
    
    def get_file_info(self, path: str) -> Dict[str, Any]:
        try:
            stat = os.stat(path)
            return {
                'path': path,
                'type': 'directory' if os.path.isdir(path) else 'file',
                'size': stat.st_size,
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'accessed': stat.st_atime,
                'permissions': oct(stat.st_mode)[-3:],
                'owner_uid': stat.st_uid,
                'group_gid': stat.st_gid
            }
        except Exception as e:
            raise Exception(f"Failed to get file info: {e}")


class LinuxProcessAdapter(BaseProcessAdapter):
    """Linux process management"""
    
    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        if action == 'start':
            return self.start_process(params.get('program'), params.get('args'))
        elif action == 'terminate':
            return self.terminate_process(params.get('program'))
        elif action == 'list':
            return self.list_processes()
        else:
            raise ValueError(f"Unknown process action: {action}")
    
    def get_capabilities(self) -> List[str]:
        return ['start', 'terminate', 'list']
    
    def start_process(self, program: str, args: List[str] = None) -> int:
        try:
            cmd = [program]
            if args:
                if isinstance(args, str):
                    cmd.extend(args.split())
                else:
                    cmd.extend(args)
            
            process = subprocess.Popen(cmd)
            return process.pid
        except Exception as e:
            raise Exception(f"Failed to start process: {e}")
    
    def terminate_process(self, pid_or_name: Any) -> bool:
        try:
            if isinstance(pid_or_name, int):
                process = psutil.Process(pid_or_name)
                process.terminate()
            else:
                # Use pkill for name-based termination
                subprocess.run(['pkill', '-f', pid_or_name], check=True)
            return True
        except Exception as e:
            raise Exception(f"Failed to terminate process: {e}")
    
    def list_processes(self) -> List[Dict[str, Any]]:
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'username']):
                try:
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu_percent': proc.info['cpu_percent'],
                        'memory_mb': proc.info['memory_info'].rss / 1024 / 1024,
                        'username': proc.info['username']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return processes
        except Exception as e:
            raise Exception(f"Failed to list processes: {e}")
    
    def get_process_info(self, pid: int) -> Dict[str, Any]:
        try:
            proc = psutil.Process(pid)
            return {
                'pid': proc.pid,
                'name': proc.name(),
                'status': proc.status(),
                'cpu_percent': proc.cpu_percent(),
                'memory_info': proc.memory_info()._asdict(),
                'create_time': proc.create_time(),
                'username': proc.username(),
                'cwd': proc.cwd()
            }
        except Exception as e:
            raise Exception(f"Failed to get process info: {e}")


class LinuxGUIAdapter(BaseGUIAdapter):
    """Linux GUI automation using X11"""
    
    def __init__(self):
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1
    
    def execute(self, action: str, params: Dict[str, Any]) -> Any:
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
        else:
            raise ValueError(f"Unknown GUI action: {action}")
    
    def get_capabilities(self) -> List[str]:
        return ['click', 'type', 'press_key', 'screenshot', 'wait']
    
    def click(self, x: int = None, y: int = None, button: str = 'left') -> bool:
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y, button=button)
            else:
                pyautogui.click(button=button)
            return True
        except Exception as e:
            raise Exception(f"Failed to click: {e}")
    
    def type_text(self, text: str) -> bool:
        try:
            pyautogui.typewrite(text)
            return True
        except Exception as e:
            raise Exception(f"Failed to type text: {e}")
    
    def press_key(self, key: str) -> bool:
        try:
            pyautogui.press(key)
            return True
        except Exception as e:
            raise Exception(f"Failed to press key: {e}")
    
    def take_screenshot(self, filename: str = None) -> str:
        try:
            if not filename:
                filename = f"screenshot_{int(time.time())}.png"
            
            # Use scrot for better Linux screenshot support
            try:
                subprocess.run(['scrot', filename], check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback to pyautogui
                screenshot = pyautogui.screenshot()
                screenshot.save(filename)
            
            return filename
        except Exception as e:
            raise Exception(f"Failed to take screenshot: {e}")
    
    def find_element(self, image_path: str) -> Dict[str, int]:
        try:
            location = pyautogui.locateOnScreen(image_path)
            if location:
                center = pyautogui.center(location)
                return {'x': center.x, 'y': center.y}
            else:
                raise Exception("Element not found")
        except Exception as e:
            raise Exception(f"Failed to find element: {e}")


class LinuxSystemAdapter(BaseSystemAdapter):
    """Linux system operations"""
    
    def execute(self, action: str, params: Dict[str, Any]) -> Any:
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
        try:
            import platform
            
            # Get additional Linux-specific info
            distro_info = {}
            try:
                with open('/etc/os-release', 'r') as f:
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            distro_info[key] = value.strip('"')
            except FileNotFoundError:
                pass
            
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
                },
                'distro_info': distro_info
            }
        except Exception as e:
            raise Exception(f"Failed to get system info: {e}")
    
    def set_volume(self, level: int) -> bool:
        try:
            # Try different volume control methods
            volume_percent = max(0, min(100, level))
            
            # Try pactl (PulseAudio)
            try:
                subprocess.run(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', f'{volume_percent}%'], check=True)
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
            
            # Try amixer (ALSA)
            try:
                subprocess.run(['amixer', 'set', 'Master', f'{volume_percent}%'], check=True)
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
            
            raise Exception("No volume control method available")
        except Exception as e:
            raise Exception(f"Failed to set volume: {e}")
    
    def power_action(self, action: str) -> bool:
        try:
            if action.lower() in ['shutdown', 'poweroff']:
                subprocess.run(['sudo', 'shutdown', '-h', 'now'], check=True)
            elif action.lower() in ['restart', 'reboot']:
                subprocess.run(['sudo', 'reboot'], check=True)
            elif action.lower() == 'suspend':
                subprocess.run(['sudo', 'systemctl', 'suspend'], check=True)
            else:
                raise ValueError(f"Unknown power action: {action}")
            return True
        except Exception as e:
            raise Exception(f"Failed to perform power action: {e}")
    
    def get_environment_variables(self) -> Dict[str, str]:
        return dict(os.environ)


class LinuxNetworkAdapter(BaseNetworkAdapter):
    """Linux network operations - same as Windows"""
    
    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        if action == 'download':
            return self.download_file(params.get('url'), params.get('filename'))
        elif action == 'http_get':
            return self.http_request('GET', params.get('url'))
        else:
            raise ValueError(f"Unknown network action: {action}")
    
    def get_capabilities(self) -> List[str]:
        return ['download', 'http_get', 'http_post']
    
    def download_file(self, url: str, filename: str = None) -> str:
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


class LinuxAdapter(BaseOSAdapter):
    """Linux OS adapter"""
    
    def _create_filesystem_adapter(self) -> BaseFilesystemAdapter:
        return LinuxFilesystemAdapter()
    
    def _create_process_adapter(self) -> BaseProcessAdapter:
        return LinuxProcessAdapter()
    
    def _create_gui_adapter(self) -> BaseGUIAdapter:
        return LinuxGUIAdapter()
    
    def _create_system_adapter(self) -> BaseSystemAdapter:
        return LinuxSystemAdapter()
    
    def _create_network_adapter(self) -> BaseNetworkAdapter:
        return LinuxNetworkAdapter()
