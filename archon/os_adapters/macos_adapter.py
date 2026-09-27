"""
macOS-specific OS adapter implementation
"""

import os
import shutil
import subprocess
import time
from typing import Any

import httpx
import psutil

# Make pyautogui optional (may not be available on headless systems)
try:
    import pyautogui
except (ImportError, SystemExit, Exception):
    pyautogui = None

from .base_adapter import (
    BaseFilesystemAdapter,
    BaseGUIAdapter,
    BaseNetworkAdapter,
    BaseOSAdapter,
    BaseProcessAdapter,
    BaseSystemAdapter,
)

# macOS-specific imports
try:
    import AppKit  # noqa: F401
    import Quartz  # noqa: F401

    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False


class MacOSFilesystemAdapter(BaseFilesystemAdapter):
    """macOS filesystem operations"""

    def execute(self, action: str, params: dict[str, Any]) -> Any:
        if action == "create_folder":
            return self.create_folder(params.get("name"), params.get("location"))
        elif action == "create_file":
            return self.create_file(params.get("name"), params.get("location"))
        elif action == "delete":
            return self.delete(params.get("path"))
        elif action == "copy":
            return self.copy(params.get("source"), params.get("destination"))
        elif action == "move":
            return self.move(params.get("source"), params.get("destination"))
        elif action == "list":
            return self.list_directory(params.get("path", "."))
        elif action in ("read_file", "read"):
            return self.read_file(
                params.get("path") or params.get("name") or params.get("file_path")
            )
        else:
            raise ValueError(f"Unknown filesystem action: {action}")

    def get_capabilities(self) -> list[str]:
        return ["create_folder", "create_file", "read_file", "delete", "copy", "move", "list"]

    def read_file(self, path: str) -> dict[str, Any]:
        """Read a text file and return ``{success, path, content}``.

        Structured output mirrors the other filesystem actions so the MCP
        layer and the agent's verify-what-I-wrote step get a consistent shape.
        """
        if not path:
            return {"success": False, "error": "read_file requires a path"}
        try:
            with open(path, encoding="utf-8") as f:
                return {"success": True, "path": path, "content": f.read()}
        except FileNotFoundError:
            return {"success": False, "error": f"File not found: {path}"}
        except PermissionError:
            return {"success": False, "error": f"Permission denied reading: {path}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to read {path}: {e}"}

    def create_folder(self, name: str, location: str = None) -> bool:
        path = os.path.join(location, name) if location else name

        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            raise Exception(f"Failed to create folder: {e}") from None

    def create_file(self, name: str, location: str = None, content: str = "") -> bool:
        path = os.path.join(location, name) if location else name

        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            raise Exception(f"Failed to create file: {e}") from None

    def delete(self, path: str, recursive: bool = True) -> bool:
        try:
            if os.path.isfile(path):
                # Move to Trash instead of permanent deletion on macOS
                try:
                    subprocess.run(
                        ["osascript", "-e", f'tell app "Finder" to delete POSIX file "{path}"'],
                        check=True,
                    )
                except subprocess.CalledProcessError:
                    os.remove(path)
            elif os.path.isdir(path):
                if recursive:
                    shutil.rmtree(path)
                else:
                    os.rmdir(path)
            return True
        except Exception as e:
            raise Exception(f"Failed to delete: {e}") from None

    def copy(self, source: str, destination: str) -> bool:
        try:
            if os.path.isfile(source):
                shutil.copy2(source, destination)
            elif os.path.isdir(source):
                shutil.copytree(source, destination)
            return True
        except Exception as e:
            raise Exception(f"Failed to copy: {e}") from None

    def move(self, source: str, destination: str) -> bool:
        try:
            shutil.move(source, destination)
            return True
        except Exception as e:
            raise Exception(f"Failed to move: {e}") from None

    def list_directory(self, path: str) -> list[dict[str, Any]]:
        try:
            items = []
            for item in os.listdir(path):
                if item.startswith(".") and item not in [".", ".."]:
                    continue  # Skip hidden files by default on macOS

                item_path = os.path.join(path, item)
                stat = os.stat(item_path)
                items.append(
                    {
                        "name": item,
                        "path": item_path,
                        "type": "directory" if os.path.isdir(item_path) else "file",
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "permissions": oct(stat.st_mode)[-3:],
                    }
                )
            return items
        except Exception as e:
            raise Exception(f"Failed to list directory: {e}") from None

    def get_file_info(self, path: str) -> dict[str, Any]:
        try:
            stat = os.stat(path)
            return {
                "path": path,
                "type": "directory" if os.path.isdir(path) else "file",
                "size": stat.st_size,
                "created": stat.st_birthtime if hasattr(stat, "st_birthtime") else stat.st_ctime,
                "modified": stat.st_mtime,
                "accessed": stat.st_atime,
                "permissions": oct(stat.st_mode)[-3:],
            }
        except Exception as e:
            raise Exception(f"Failed to get file info: {e}") from None


class MacOSProcessAdapter(BaseProcessAdapter):
    """macOS process management"""

    def execute(self, action: str, params: dict[str, Any]) -> Any:
        if action == "start":
            return self.start_process(params.get("program"), params.get("args"))
        elif action == "terminate":
            return self.terminate_process(params.get("program"))
        elif action == "list":
            return self.list_processes()
        else:
            raise ValueError(f"Unknown process action: {action}")

    def get_capabilities(self) -> list[str]:
        return ["start", "terminate", "list"]

    def start_process(self, program: str, args: list[str] = None) -> int:
        try:
            # Handle macOS app bundles
            if program.endswith(".app") or "/" not in program:
                # Use 'open' command for macOS applications
                cmd = ["open", "-a", program]
                if args:
                    cmd.extend(["--args"] + (args if isinstance(args, list) else args.split()))
            else:
                cmd = [program]
                if args:
                    cmd.extend(args if isinstance(args, list) else args.split())

            process = subprocess.Popen(cmd)
            return process.pid
        except Exception as e:
            raise Exception(f"Failed to start process: {e}") from None

    def terminate_process(self, pid_or_name: Any) -> bool:
        try:
            if isinstance(pid_or_name, int):
                process = psutil.Process(pid_or_name)
                process.terminate()
            else:
                # Use pkill for name-based termination
                subprocess.run(["pkill", "-f", pid_or_name], check=True)
            return True
        except Exception as e:
            raise Exception(f"Failed to terminate process: {e}") from None

    def list_processes(self) -> list[dict[str, Any]]:
        try:
            processes = []
            for proc in psutil.process_iter(
                ["pid", "name", "cpu_percent", "memory_info", "username"]
            ):
                try:
                    processes.append(
                        {
                            "pid": proc.info["pid"],
                            "name": proc.info["name"],
                            "cpu_percent": proc.info["cpu_percent"],
                            "memory_mb": proc.info["memory_info"].rss / 1024 / 1024,
                            "username": proc.info["username"],
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return processes
        except Exception as e:
            raise Exception(f"Failed to list processes: {e}") from None

    def get_process_info(self, pid: int) -> dict[str, Any]:
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
            }
        except Exception as e:
            raise Exception(f"Failed to get process info: {e}") from None


class MacOSGUIAdapter(BaseGUIAdapter):
    """macOS GUI automation using Quartz and AppKit"""

    def __init__(self):
        if pyautogui is not None:
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1

    def execute(self, action: str, params: dict[str, Any]) -> Any:
        if action == "click":
            return self.click(params.get("x"), params.get("y"), params.get("button", "left"))
        elif action == "type":
            return self.type_text(params.get("text"))
        elif action == "press_key":
            return self.press_key(params.get("key"))
        elif action == "screenshot":
            return self.take_screenshot(params.get("filename"))
        elif action == "wait":
            time.sleep(float(params.get("duration", 1)))
            return True
        else:
            raise ValueError(f"Unknown GUI action: {action}")

    def get_capabilities(self) -> list[str]:
        return ["click", "type", "press_key", "screenshot", "wait"]

    def click(self, x: int = None, y: int = None, button: str = "left") -> bool:
        if pyautogui is None:
            raise RuntimeError("pyautogui not available on this system")
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y, button=button)
            else:
                pyautogui.click(button=button)
            return True
        except Exception as e:
            raise Exception(f"Failed to click: {e}") from None

    def type_text(self, text: str) -> bool:
        if pyautogui is None:
            raise RuntimeError("pyautogui not available on this system")
        try:
            pyautogui.typewrite(text)
            return True
        except Exception as e:
            raise Exception(f"Failed to type text: {e}") from None

    def press_key(self, key: str) -> bool:
        if pyautogui is None:
            raise RuntimeError("pyautogui not available on this system")
        try:
            pyautogui.press(key)
            return True
        except Exception as e:
            raise Exception(f"Failed to press key: {e}") from None

    def take_screenshot(self, filename: str = None) -> str:
        try:
            if not filename:
                filename = f"screenshot_{int(time.time())}.png"
            try:
                subprocess.run(["screencapture", "-x", filename], check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                if pyautogui is None:
                    raise RuntimeError("pyautogui not available and screencapture failed") from None
                screenshot = pyautogui.screenshot()
                screenshot.save(filename)
            return filename
        except Exception as e:
            raise Exception(f"Failed to take screenshot: {e}") from None

    def find_element(self, image_path: str) -> dict[str, int]:
        if pyautogui is None:
            raise RuntimeError("pyautogui not available on this system")
        try:
            location = pyautogui.locateOnScreen(image_path)
            if location:
                center = pyautogui.center(location)
                return {"x": center.x, "y": center.y}
            else:
                raise Exception("Element not found")
        except Exception as e:
            raise Exception(f"Failed to find element: {e}") from None


class MacOSSystemAdapter(BaseSystemAdapter):
    """macOS system operations"""

    def execute(self, action: str, params: dict[str, Any]) -> Any:
        if action == "get_info":
            return self.get_system_info()
        elif action == "set_volume":
            return self.set_volume(int(params.get("level", 50)))
        elif action == "power_action":
            return self.power_action(params.get("action"))
        else:
            raise ValueError(f"Unknown system action: {action}")

    def get_capabilities(self) -> list[str]:
        return ["get_info", "set_volume", "power_action"]

    def get_system_info(self) -> dict[str, Any]:
        try:
            import platform

            # Get macOS version info
            macos_version = platform.mac_ver()[0]

            return {
                "platform": platform.platform(),
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "macos_version": macos_version,
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "disk_usage": {
                    "total": psutil.disk_usage("/").total,
                    "used": psutil.disk_usage("/").used,
                    "free": psutil.disk_usage("/").free,
                },
            }
        except Exception as e:
            raise Exception(f"Failed to get system info: {e}") from None

    def set_volume(self, level: int) -> bool:
        try:
            volume_percent = max(0, min(100, level))
            volume_percent / 100.0

            # Use AppleScript to set volume
            script = f"set volume output volume {volume_percent}"
            subprocess.run(["osascript", "-e", script], check=True)
            return True
        except Exception as e:
            raise Exception(f"Failed to set volume: {e}") from None

    def power_action(self, action: str) -> bool:
        try:
            if action.lower() in ["shutdown", "poweroff"]:
                subprocess.run(["sudo", "shutdown", "-h", "now"], check=True)
            elif action.lower() in ["restart", "reboot"]:
                subprocess.run(["sudo", "shutdown", "-r", "now"], check=True)
            elif action.lower() == "sleep":
                subprocess.run(["pmset", "sleepnow"], check=True)
            else:
                raise ValueError(f"Unknown power action: {action}")
            return True
        except Exception as e:
            raise Exception(f"Failed to perform power action: {e}") from None

    def get_environment_variables(self) -> dict[str, str]:
        return dict(os.environ)


class MacOSNetworkAdapter(BaseNetworkAdapter):
    """macOS network operations - same as other platforms"""

    def execute(self, action: str, params: dict[str, Any]) -> Any:
        if action == "download":
            return self.download_file(params.get("url"), params.get("filename"))
        elif action == "http_get":
            return self.http_request("GET", params.get("url"))
        else:
            raise ValueError(f"Unknown network action: {action}")

    def get_capabilities(self) -> list[str]:
        return ["download", "http_get", "http_post"]

    def download_file(self, url: str, filename: str = None) -> str:
        try:
            if not filename:
                filename = url.split("/")[-1] or "downloaded_file"

            with httpx.Client(follow_redirects=True, timeout=60.0) as client:
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    with open(filename, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)

            return filename
        except Exception as e:
            raise Exception(f"Failed to download file: {e}") from None

    def http_request(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        try:
            with httpx.Client(follow_redirects=True, timeout=30.0) as client:
                response = client.request(method, url, **kwargs)
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": response.text,
                "json": response.json()
                if "application/json" in response.headers.get("content-type", "")
                else None,
            }
        except Exception as e:
            raise Exception(f"Failed to make HTTP request: {e}") from None

    def get_network_info(self) -> dict[str, Any]:
        try:
            import socket

            return {
                "hostname": socket.gethostname(),
                "ip_address": socket.gethostbyname(socket.gethostname()),
                "network_interfaces": [
                    {"name": interface, "addresses": [addr.address for addr in addrs]}
                    for interface, addrs in psutil.net_if_addrs().items()
                ],
            }
        except Exception as e:
            raise Exception(f"Failed to get network info: {e}") from None


class MacOSAdapter(BaseOSAdapter):
    """macOS OS adapter"""

    def _create_filesystem_adapter(self) -> BaseFilesystemAdapter:
        return MacOSFilesystemAdapter()

    def _create_process_adapter(self) -> BaseProcessAdapter:
        return MacOSProcessAdapter()

    def _create_gui_adapter(self) -> BaseGUIAdapter:
        return MacOSGUIAdapter()

    def _create_system_adapter(self) -> BaseSystemAdapter:
        return MacOSSystemAdapter()

    def _create_network_adapter(self) -> BaseNetworkAdapter:
        return MacOSNetworkAdapter()
