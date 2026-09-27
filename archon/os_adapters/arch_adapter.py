"""
Arch Linux-specific OS adapter implementation
Supports Arch Linux, Manjaro, EndeavourOS and other Arch-based distros
Uses pacman/yay for package management
"""

import os
import platform
import shutil
import subprocess
from typing import Any

import psutil
from loguru import logger

from .base_adapter import (
    BaseFilesystemAdapter,
    BaseGUIAdapter,
    BaseNetworkAdapter,
    BaseOSAdapter,
    BaseProcessAdapter,
    BaseSystemAdapter,
)


def detect_arch_distro() -> str:
    """Detect specific Arch-based distribution"""
    try:
        with open("/etc/os-release") as f:
            content = f.read().lower()
            if "manjaro" in content:
                return "manjaro"
            elif "endeavouros" in content:
                return "endeavouros"
            elif "garuda" in content:
                return "garuda"
            elif "arch" in content:
                return "arch"
    except Exception:
        pass
    return "arch"


class ArchFilesystemAdapter(BaseFilesystemAdapter):
    """Arch Linux filesystem operations with proper fallbacks"""

    def execute(self, action: str, params: dict[str, Any]) -> Any:
        """Execute filesystem action with fallback handling"""
        try:
            if action == "create_folder":
                return self.create_folder(params.get("name"), params.get("location"))
            elif action == "create_file":
                return self.create_file(
                    params.get("name"), params.get("location"), params.get("content", "")
                )
            elif action == "delete":
                return self.delete(params.get("path"), params.get("recursive", True))
            elif action == "copy":
                return self.copy(params.get("source"), params.get("destination"))
            elif action == "move":
                return self.move(params.get("source"), params.get("destination"))
            elif action == "rename":
                old = params.get("old_name") or params.get("source") or params.get("path")
                new = params.get("new_name") or params.get("destination")
                if old and new:
                    import shutil

                    if os.path.exists(old):
                        shutil.move(old, new)
                        return True
                    return False
                return False
            elif action == "list":
                return self.list_directory(params.get("path", "."))
            elif action in ("read_file", "read"):
                return self.read_file(
                    params.get("path") or params.get("name") or params.get("file_path")
                )
            else:
                raise ValueError(f"Unknown filesystem action: {action}")
        except Exception as e:
            # Fallback: log error and return safe default
            logger.warning(f"Filesystem action '{action}' failed: {e}")
            return False

    def get_capabilities(self) -> list[str]:
        return [
            "create_folder",
            "create_file",
            "read_file",
            "delete",
            "copy",
            "move",
            "rename",
            "list",
        ]

    def create_folder(self, name: str, location: str = None) -> bool:
        """Create folder with Arch-appropriate permissions"""
        path = os.path.join(location, name) if location else name

        try:
            os.makedirs(path, exist_ok=True)
            os.chmod(path, 0o755)  # rwxr-xr-x
            return True
        except PermissionError:
            logger.warning(f"Permission denied creating folder: {path}")
            return False
        except Exception as e:
            logger.warning(f"Failed to create folder: {e}")
            return False

    def create_file(self, name: str, location: str = None, content: str = "") -> bool:
        """Create file with proper encoding and permissions"""
        path = os.path.join(location, name) if location else name

        try:
            # Ensure parent directory exists
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            os.chmod(path, 0o644)  # rw-r--r--
            return True
        except PermissionError:
            logger.warning(f"Permission denied creating file: {path}")
            return False
        except Exception as e:
            logger.warning(f"Failed to create file: {e}")
            return False

    def read_file(self, path: str) -> dict[str, Any]:
        """Read a text file and return its contents.

        Returns a dict so callers (and the MCP layer) get structured output
        rather than a bare string, matching the other filesystem actions.
        """
        if not path:
            return {"success": False, "error": "read_file requires a path"}
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            return {"success": True, "path": path, "content": content}
        except FileNotFoundError:
            return {"success": False, "error": f"File not found: {path}"}
        except PermissionError:
            return {"success": False, "error": f"Permission denied reading: {path}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to read {path}: {e}"}

    def delete(self, path: str, recursive: bool = True) -> bool:
        """Delete file or directory with safety checks"""
        try:
            if not os.path.exists(path):
                logger.warning(f"Path does not exist: {path}")
                return False

            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                if recursive:
                    shutil.rmtree(path)
                else:
                    os.rmdir(path)
            return True
        except PermissionError:
            logger.warning(f"Permission denied deleting: {path}")
            return False
        except Exception as e:
            logger.warning(f"Failed to delete: {e}")
            return False

    def copy(self, source: str, destination: str) -> bool:
        """Copy file or directory with fallback"""
        try:
            if not os.path.exists(source):
                logger.warning(f"Source does not exist: {source}")
                return False

            if os.path.isfile(source):
                shutil.copy2(source, destination)
            elif os.path.isdir(source):
                shutil.copytree(source, destination, dirs_exist_ok=True)
            return True
        except Exception as e:
            logger.warning(f"Failed to copy: {e}")
            return False

    def move(self, source: str, destination: str) -> bool:
        """Move file or directory with fallback"""
        try:
            if not os.path.exists(source):
                logger.warning(f"Source does not exist: {source}")
                return False

            shutil.move(source, destination)
            return True
        except Exception as e:
            logger.warning(f"Failed to move: {e}")
            return False

    def list_directory(self, path: str = ".") -> list[dict[str, Any]]:
        """List directory contents with metadata"""
        try:
            items = []
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                try:
                    stat = os.stat(item_path)
                    items.append(
                        {
                            "name": item,
                            "path": item_path,
                            "type": "directory" if os.path.isdir(item_path) else "file",
                            "size": stat.st_size,
                            "modified": stat.st_mtime,
                        }
                    )
                except Exception:
                    items.append({"name": item, "path": item_path, "type": "unknown"})
            return items
        except Exception as e:
            logger.warning(f"Failed to list directory: {e}")
            return []

    def get_file_info(self, path: str) -> dict[str, Any]:
        """Get detailed file/folder information"""
        try:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Path does not exist: {path}")

            stat = os.stat(path)
            return {
                "path": path,
                "type": "directory" if os.path.isdir(path) else "file",
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "accessed": stat.st_atime,
                "permissions": oct(stat.st_mode)[-3:],
                "owner_uid": stat.st_uid,
                "group_gid": stat.st_gid,
            }
        except Exception as e:
            logger.warning(f"Failed to get file info: {e}")
            return {"error": str(e)}


class ArchProcessAdapter(BaseProcessAdapter):
    """Arch Linux process management with fallbacks"""

    def execute(self, action: str, params: dict[str, Any]) -> Any:
        """Execute process action with fallback handling"""
        try:
            if action == "start":
                return self.start_process(params.get("command"), params.get("args", []))
            elif action == "kill":
                return self.kill_process(params.get("pid") or params.get("name"))
            elif action == "list":
                return self.list_processes()
            else:
                raise ValueError(f"Unknown process action: {action}")
        except Exception as e:
            logger.warning(f"Process action '{action}' failed: {e}")
            return None

    def get_capabilities(self) -> list[str]:
        return ["start", "kill", "list", "monitor"]

    def start_process(self, command: str, args: list[str] = None) -> int:
        """Start a process with fallback"""
        try:
            cmd = [command] + (args or [])
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return process.pid
        except Exception as e:
            logger.warning(f"Failed to start process: {e}")
            return -1

    def kill_process(self, identifier: Any) -> bool:
        """Kill process by PID or name with fallback"""
        try:
            if isinstance(identifier, int):
                # Kill by PID
                os.kill(identifier, 9)
                return True
            elif isinstance(identifier, str):
                # Kill by name using pkill
                subprocess.run(["pkill", "-9", identifier], check=True)
                return True
        except ProcessLookupError:
            logger.warning(f"Process not found: {identifier}")
            return False
        except Exception as e:
            logger.warning(f"Failed to kill process: {e}")
            return False

    def terminate_process(self, pid_or_name: Any) -> bool:
        """Terminate process by PID or name with fallback"""
        try:
            if isinstance(pid_or_name, int):
                # Terminate by PID using psutil
                process = psutil.Process(pid_or_name)
                process.terminate()
                return True
            else:
                # Terminate by name using pkill
                subprocess.run(["pkill", "-f", str(pid_or_name)], check=True)
                return True
        except ProcessLookupError:
            logger.warning(f"Process not found: {pid_or_name}")
            return False
        except Exception as e:
            logger.warning(f"Failed to terminate process: {e}")
            return False

    def list_processes(self) -> list[dict[str, Any]]:
        """List running processes with fallback"""
        try:
            processes = []
            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                try:
                    processes.append(proc.info)
                except Exception:
                    continue
            return processes
        except Exception as e:
            logger.warning(f"Failed to list processes: {e}")
            return []

    def get_process_info(self, pid: int) -> dict[str, Any]:
        """Get detailed process information"""
        try:
            proc = psutil.Process(pid)
            return {
                "pid": proc.pid,
                "name": proc.name(),
                "status": proc.status(),
                "cpu_percent": proc.cpu_percent(),
                "memory_info": proc.memory_info()._asdict(),
                "create_time": proc.create_time(),
                "username": proc.username(),
                "cwd": proc.cwd() if proc.cwd() else "N/A",
            }
        except psutil.NoSuchProcess:
            logger.warning(f"Process {pid} not found")
            return {"error": f"Process {pid} not found"}
        except psutil.AccessDenied:
            logger.warning(f"Access denied for process {pid}")
            return {"error": f"Access denied for process {pid}"}
        except Exception as e:
            logger.warning(f"Failed to get process info: {e}")
            return {"error": str(e)}


class ArchSystemAdapter(BaseSystemAdapter):
    """Arch Linux system management with pacman/yay support"""

    def __init__(self):
        self.distro = detect_arch_distro()
        self.aur_helper = self._detect_aur_helper()

    def _detect_aur_helper(self) -> str:
        """Detect available AUR helper"""
        helpers = ["yay", "paru", "pikaur", "trizen"]
        for helper in helpers:
            if shutil.which(helper):
                return helper
        return "pacman"

    def execute(self, action: str, params: dict[str, Any]) -> Any:
        """Execute system action with fallback handling"""
        try:
            if action == "install_package":
                return self.install_package(params.get("package"))
            elif action == "remove_package":
                return self.remove_package(params.get("package"))
            elif action == "update_system":
                return self.update_system()
            elif action == "get_info":
                return self.get_system_info()
            else:
                raise ValueError(f"Unknown system action: {action}")
        except Exception as e:
            logger.warning(f"System action '{action}' failed: {e}")
            return False

    def get_capabilities(self) -> list[str]:
        return ["install_package", "remove_package", "update_system", "get_info", "service_control"]

    def install_package(self, package: str) -> bool:
        """Install package using pacman/yay with fallback"""
        try:
            logger.info(f"Installing package: {package} (using {self.aur_helper})")

            if self.aur_helper == "pacman":
                # Official repos only
                cmd = ["sudo", "pacman", "-S", "--noconfirm", package]
            else:
                # AUR helper (no sudo needed for yay/paru)
                cmd = [self.aur_helper, "-S", "--noconfirm", package]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Package '{package}' installed successfully")
                return True
            else:
                logger.warning(f"Package installation failed: {result.stderr}")
                return False
        except FileNotFoundError:
            logger.warning(f"Package manager not found. Install {self.aur_helper} first.")
            return False
        except Exception as e:
            logger.warning(f"Failed to install package: {e}")
            return False

    def remove_package(self, package: str) -> bool:
        """Remove package with fallback"""
        try:
            logger.info(f"Removing package: {package}")
            cmd = ["sudo", "pacman", "-R", "--noconfirm", package]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Package '{package}' removed successfully")
                return True
            else:
                logger.warning(f"Package removal failed: {result.stderr}")
                return False
        except Exception as e:
            logger.warning(f"Failed to remove package: {e}")
            return False

    def update_system(self) -> bool:
        """Update system packages with fallback"""
        try:
            logger.info(f"Updating system using {self.aur_helper}...")

            if self.aur_helper == "pacman":
                cmd = ["sudo", "pacman", "-Syu", "--noconfirm"]
            else:
                cmd = [self.aur_helper, "-Syu", "--noconfirm"]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("System updated successfully")
                return True
            else:
                logger.warning(f"System update failed: {result.stderr}")
                return False
        except Exception as e:
            logger.warning(f"Failed to update system: {e}")
            return False

    def get_system_info(self) -> dict[str, Any]:
        """Get Arch system information with fallback"""
        try:
            info = {
                "os": "Arch Linux",
                "distro": self.distro,
                "kernel": platform.release(),
                "architecture": platform.machine(),
                "aur_helper": self.aur_helper,
                "hostname": platform.node(),
                "cpu_count": os.cpu_count(),
                "python_version": platform.python_version(),
            }

            # Try to get more detailed info
            try:
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME"):
                            info["pretty_name"] = line.split("=")[1].strip().strip('"')
            except Exception:
                pass

            return info
        except Exception as e:
            logger.warning(f"Failed to get system info: {e}")
            return {"os": "Arch Linux", "error": str(e)}

    def set_volume(self, level: int) -> bool:
        """Set system volume with multiple fallbacks"""
        try:
            volume_percent = max(0, min(100, level))

            # Try pactl (PulseAudio/PipeWire)
            if shutil.which("pactl"):
                try:
                    subprocess.run(
                        ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{volume_percent}%"],
                        check=True,
                        capture_output=True,
                    )
                    logger.info(f"Volume set to {volume_percent}%")
                    return True
                except Exception:
                    pass

            # Try amixer (ALSA)
            if shutil.which("amixer"):
                try:
                    subprocess.run(
                        ["amixer", "set", "Master", f"{volume_percent}%"],
                        check=True,
                        capture_output=True,
                    )
                    logger.info(f"Volume set to {volume_percent}%")
                    return True
                except Exception:
                    pass

            # Try wpctl (WirePlumber for PipeWire)
            if shutil.which("wpctl"):
                try:
                    volume_decimal = volume_percent / 100.0
                    subprocess.run(
                        ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", str(volume_decimal)],
                        check=True,
                        capture_output=True,
                    )
                    logger.info(f"Volume set to {volume_percent}%")
                    return True
                except Exception:
                    pass

            logger.warning("No volume control method available")
            return False
        except Exception as e:
            logger.warning(f"Failed to set volume: {e}")
            return False

    def power_action(self, action: str) -> bool:
        """Perform power actions with fallback"""
        try:
            action_lower = action.lower()

            if action_lower in ["shutdown", "poweroff"]:
                logger.info("Initiating system shutdown...")
                subprocess.run(["sudo", "shutdown", "-h", "now"], check=True, capture_output=True)
            elif action_lower in ["restart", "reboot"]:
                logger.info("Initiating system restart...")
                subprocess.run(["sudo", "reboot"], check=True, capture_output=True)
            elif action_lower == "suspend":
                logger.info("Suspending system...")
                subprocess.run(["systemctl", "suspend"], check=True, capture_output=True)
            elif action_lower == "hibernate":
                logger.info("Hibernating system...")
                subprocess.run(["systemctl", "hibernate"], check=True, capture_output=True)
            elif action_lower == "logout":
                logger.info("Logging out...")
                # Try different logout methods
                if os.environ.get("XDG_CURRENT_DESKTOP") == "KDE":
                    subprocess.run(
                        ["qdbus", "org.kde.ksmserver", "/KSMServer", "logout", "0", "0", "0"],
                        check=True,
                        capture_output=True,
                    )
                else:
                    subprocess.run(
                        ["loginctl", "terminate-user", os.environ.get("USER", "")],
                        check=True,
                        capture_output=True,
                    )
            else:
                logger.warning(f"Unknown power action: {action}")
                return False

            return True
        except Exception as e:
            logger.warning(f"Failed to perform power action: {e}")
            return False

    def get_environment_variables(self) -> dict[str, str]:
        """Get environment variables"""
        try:
            return dict(os.environ)
        except Exception as e:
            logger.warning(f"Failed to get environment variables: {e}")
            return {}


class ArchGUIAdapter(BaseGUIAdapter):
    """Arch Linux GUI operations with Wayland/X11 fallbacks"""

    def __init__(self):
        self.display_server = self._detect_display_server()

    def _detect_display_server(self) -> str:
        """Detect if running Wayland or X11"""
        if os.environ.get("WAYLAND_DISPLAY"):
            return "wayland"
        elif os.environ.get("DISPLAY"):
            return "x11"
        return "unknown"

    def execute(self, action: str, params: dict[str, Any]) -> Any:
        """Execute GUI action with fallback"""
        try:
            if action == "screenshot":
                return self.take_screenshot(params.get("path", "screenshot.png"))
            elif action == "click":
                return self.click(params.get("x"), params.get("y"))
            elif action == "type":
                return self.type_text(params.get("text"))
            else:
                raise ValueError(f"Unknown GUI action: {action}")
        except Exception as e:
            logger.warning(f"GUI action '{action}' failed: {e}")
            return False

    def get_capabilities(self) -> list[str]:
        caps = ["screenshot"]
        if self.display_server != "unknown":
            caps.extend(["click", "type", "get_window"])
        return caps

    def take_screenshot(self, path: str = "screenshot.png") -> bool:
        """Take screenshot with fallback to multiple tools"""
        tools = []

        if self.display_server == "wayland":
            tools = ["grim", "grimshot", "spectacle"]
        else:  # X11 or unknown
            tools = ["scrot", "import", "spectacle", "gnome-screenshot"]

        for tool in tools:
            if shutil.which(tool):
                try:
                    if tool == "grim":
                        subprocess.run(["grim", path], check=True)
                    elif tool == "scrot":
                        subprocess.run(["scrot", path], check=True)
                    elif tool == "import":
                        subprocess.run(["import", "-window", "root", path], check=True)
                    elif tool == "spectacle":
                        subprocess.run(["spectacle", "-b", "-n", "-o", path], check=True)
                    elif tool == "gnome-screenshot":
                        subprocess.run(["gnome-screenshot", "-f", path], check=True)

                    logger.info(f"Screenshot saved: {path} (using {tool})")
                    return True
                except Exception:
                    continue

        # Ultimate fallback: try pyautogui
        try:
            import pyautogui

            screenshot = pyautogui.screenshot()
            screenshot.save(path)
            logger.info(f"Screenshot saved: {path} (using pyautogui)")
            return True
        except Exception as e:
            logger.warning(f"Failed to take screenshot: {e}")
            logger.info("Install: sudo pacman -S scrot (X11) or grim (Wayland)")
            return False

    def click(self, x: int, y: int) -> bool:
        """Click at position with fallback"""
        try:
            import pyautogui

            pyautogui.click(x, y)
            return True
        except Exception as e:
            logger.warning(f"Failed to click: {e}")
            return False

    def type_text(self, text: str) -> bool:
        """Type text with fallback"""
        try:
            import pyautogui

            pyautogui.write(text, interval=0.05)
            return True
        except Exception as e:
            logger.warning(f"Failed to type text: {e}")
            return False

    def press_key(self, key: str) -> bool:
        """Press a key with fallback"""
        try:
            import pyautogui

            pyautogui.press(key)
            return True
        except Exception as e:
            logger.warning(f"Failed to press key: {e}")
            return False

    def find_element(self, image_path: str) -> dict[str, int]:
        """Find element on screen by image with fallback"""
        try:
            import pyautogui

            location = pyautogui.locateOnScreen(image_path, confidence=0.8)
            if location:
                center = pyautogui.center(location)
                return {"x": center.x, "y": center.y}
            else:
                logger.warning(f"Element not found: {image_path}")
                return {"x": 0, "y": 0}
        except Exception as e:
            logger.warning(f"Failed to find element: {e}")
            return {"x": 0, "y": 0}


class ArchNetworkAdapter(BaseNetworkAdapter):
    """Arch Linux network operations with fallbacks"""

    def execute(self, action: str, params: dict[str, Any]) -> Any:
        """Execute network action with fallback"""
        try:
            if action == "download":
                return self.download_file(params.get("url"), params.get("destination"))
            elif action == "test_connection":
                return self.test_connection(params.get("host", "google.com"))
            else:
                raise ValueError(f"Unknown network action: {action}")
        except Exception as e:
            logger.warning(f"Network action '{action}' failed: {e}")
            return False

    def get_capabilities(self) -> list[str]:
        return ["download", "test_connection", "get_ip"]

    def download_file(self, url: str, destination: str) -> bool:
        """Download file with multiple fallbacks"""
        # Try curl first (usually installed on Arch)
        if shutil.which("curl"):
            try:
                subprocess.run(["curl", "-L", "-o", destination, url], check=True)
                logger.info(f"Downloaded: {destination}")
                return True
            except Exception:
                pass

        # Try wget
        if shutil.which("wget"):
            try:
                subprocess.run(["wget", "-O", destination, url], check=True)
                logger.info(f"Downloaded: {destination}")
                return True
            except Exception:
                pass

        # Fallback to Python httpx
        try:
            import httpx

            with httpx.Client(follow_redirects=True, timeout=60.0) as client:
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    with open(destination, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)

            logger.info(f"Downloaded: {destination}")
            return True
        except Exception as e:
            logger.warning(f"Failed to download file: {e}")
            return False

    def test_connection(self, host: str = "google.com") -> bool:
        """Test network connection with fallback"""
        try:
            subprocess.run(["ping", "-c", "1", "-W", "2", host], check=True, capture_output=True)
            return True
        except Exception:
            return False

    def http_request(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        """Make HTTP request with fallback"""
        try:
            import httpx

            with httpx.Client(follow_redirects=True, timeout=30.0) as client:
                response = client.request(method, url, **kwargs)
            return {
                "success": True,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": response.text,
                "json": response.json()
                if "application/json" in response.headers.get("content-type", "")
                else None,
            }
        except Exception as e:
            logger.warning(f"HTTP request failed: {e}")
            return {"success": False, "error": str(e)}

    def get_network_info(self) -> dict[str, Any]:
        """Get network information with fallback"""
        try:
            import socket

            info = {
                "hostname": socket.gethostname(),
            }

            # Try to get IP address
            try:
                info["ip_address"] = socket.gethostbyname(socket.gethostname())
            except Exception:
                info["ip_address"] = "unknown"

            # Try to get network interfaces
            try:
                info["network_interfaces"] = [
                    {"name": interface, "addresses": [addr.address for addr in addrs]}
                    for interface, addrs in psutil.net_if_addrs().items()
                ]
            except Exception:
                info["network_interfaces"] = []

            return info
        except Exception as e:
            logger.warning(f"Failed to get network info: {e}")
            return {"error": str(e)}


class ArchLinuxAdapter(BaseOSAdapter):
    """Main Arch Linux adapter with all sub-adapters"""

    def __init__(self):
        super().__init__()
        logger.info("Arch Linux Adapter initialized")
        logger.info(f"Distro: {self.system.distro}")
        logger.info(f"AUR Helper: {self.system.aur_helper}")
        logger.info(f"Display: {self.gui.display_server}")

    def _create_filesystem_adapter(self) -> BaseFilesystemAdapter:
        """Create Arch filesystem adapter"""
        return ArchFilesystemAdapter()

    def _create_process_adapter(self) -> BaseProcessAdapter:
        """Create Arch process adapter"""
        return ArchProcessAdapter()

    def _create_gui_adapter(self) -> BaseGUIAdapter:
        """Create Arch GUI adapter"""
        return ArchGUIAdapter()

    def _create_system_adapter(self) -> BaseSystemAdapter:
        """Create Arch system adapter"""
        return ArchSystemAdapter()

    def _create_network_adapter(self) -> BaseNetworkAdapter:
        """Create Arch network adapter"""
        return ArchNetworkAdapter()

    def execute(self, category: str, action: str, params: dict[str, Any]) -> Any:
        """Execute action with robust fallback chain"""
        try:
            if category == "filesystem":
                return self.filesystem.execute(action, params)
            elif category == "process":
                return self.process.execute(action, params)
            elif category == "system":
                return self.system.execute(action, params)
            elif category == "gui":
                return self.gui.execute(action, params)
            elif category == "network":
                return self.network.execute(action, params)
            else:
                logger.warning(f"Unknown category: {category}")
                return None
        except Exception as e:
            logger.warning(f"Adapter execution failed: {e}")
            logger.warning(f"Category: {category}, Action: {action}")
            return None

    def get_all_capabilities(self) -> dict[str, list[str]]:
        """Get all capabilities with fallback"""
        try:
            return {
                "filesystem": self.filesystem.get_capabilities(),
                "process": self.process.get_capabilities(),
                "system": self.system.get_capabilities(),
                "gui": self.gui.get_capabilities(),
                "network": self.network.get_capabilities(),
            }
        except Exception as e:
            logger.warning(f"Failed to get capabilities: {e}")
            return {}
