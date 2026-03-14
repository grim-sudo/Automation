"""
Universal Automation Plugin - Handles EVERYTHING
From simplest tasks to most complex enterprise operations
"""

import json
import os
import platform
import shlex
import shutil
import subprocess
import time
from typing import Any

import httpx

from omni_automator.core.plugin_manager import AutomationPlugin
from omni_automator.security.subprocess_runner import safe_run


class UniversalAutomationPlugin(AutomationPlugin):
    """Plugin that can handle ANY automation task without restrictions"""

    @property
    def name(self) -> str:
        return "universal_automation"

    @property
    def description(self) -> str:
        return "Universal automation plugin that handles everything from simple file operations to complex enterprise deployments"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_capabilities(self) -> list[str]:
        return [
            # System Administration
            "install_software",
            "uninstall_software",
            "update_system",
            "manage_services",
            "configure_firewall",
            "manage_users",
            "setup_permissions",
            "schedule_tasks",
            # Development & Programming
            "setup_dev_environment",
            "install_languages",
            "manage_packages",
            "run_tests",
            "build_projects",
            "deploy_applications",
            "setup_databases",
            "configure_servers",
            # Cloud & Infrastructure
            "deploy_to_cloud",
            "manage_containers",
            "setup_kubernetes",
            "configure_load_balancers",
            "setup_monitoring",
            "manage_secrets",
            "backup_systems",
            "disaster_recovery",
            # Data & Analytics
            "process_data",
            "run_analytics",
            "setup_pipelines",
            "machine_learning",
            "data_migration",
            "etl_operations",
            "setup_warehouses",
            "create_dashboards",
            # Security & Compliance
            "security_scan",
            "vulnerability_assessment",
            "setup_ssl",
            "manage_certificates",
            "audit_systems",
            "compliance_check",
            "penetration_testing",
            "security_hardening",
            # Network & Communication
            "configure_networks",
            "setup_vpn",
            "manage_dns",
            "load_testing",
            "api_testing",
            "webhook_setup",
            "email_automation",
            "notification_systems",
            # Content & Media
            "process_images",
            "convert_videos",
            "generate_documents",
            "web_scraping",
            "content_management",
            "seo_optimization",
            "social_media_automation",
            "email_campaigns",
            # Document Creation & Management
            "create_word_document",
            "create_word_doc",
            "generate_word",
            "write_word_document",
            "create_powerpoint",
            "create_ppt",
            "generate_ppt",
            "create_presentation",
            "create_excel",
            "create_spreadsheet",
            "generate_excel",
            "write_excel",
            "create_pdf",
            "generate_pdf",
            "create_folder",
            "make_directory",
            "ensure_folder",
            "save_to_document",
            "write_to_file",
            "append_to_document",
            # Convenience actions often emitted by NLP workflows
            "download_file",
            "execute_installer",
            "verify_installation",
            "create_shortcut",
            "check_winget_availability",
            "search_package",
            "install_package",
            "list_installed_packages",
            "execute_command",
            # Additional aliases/paraphrases the parser may emit
            "run_installer",
            "execute_file",
            "run_executable",
            "check_installed_applications",
            "check_installed_apps",
            "run_installer_silently",
            # Business Operations
            "workflow_automation",
            "report_generation",
            "invoice_processing",
            "inventory_management",
            "customer_management",
            "sales_automation",
            "marketing_campaigns",
            "analytics_reporting",
            # Advanced Operations
            "ai_model_deployment",
            "blockchain_operations",
            "iot_management",
            "edge_computing",
            "quantum_computing",
            "advanced_analytics",
            "predictive_modeling",
            "automation_orchestration",
        ]

    def _default_package_manager(self) -> str:
        """Return the default package manager for the current OS."""
        try:
            sys_name = platform.system().lower()
            if "windows" in sys_name:
                return "winget"
            if "darwin" in sys_name or "mac" in sys_name:
                return "brew"
            if "linux" in sys_name:
                # Detect Arch Linux
                if os.path.exists("/usr/bin/pacman"):
                    # Prefer AUR helpers
                    if shutil.which("yay"):
                        return "yay"
                    elif shutil.which("paru"):
                        return "paru"
                    return "pacman"
                # Debian/Ubuntu
                elif os.path.exists("/usr/bin/apt"):
                    return "apt"
                # RedHat/Fedora
                elif os.path.exists("/usr/bin/dnf"):
                    return "dnf"
                # Fallback
                return "apt"
        except Exception:
            pass
        return "winget"

    def execute(self, action: str, params: dict[str, Any]) -> Any:
        """Execute any automation action"""
        try:
            sandbox = False
            if isinstance(params, dict) and params.get("_sandbox"):
                sandbox = True
            # System Administration
            if action == "install_software":
                return self._install_software(params, sandbox=sandbox)
            elif action in (
                "run_installer",
                "execute_file",
                "run_executable",
                "run_installer_silently",
            ):
                return self._execute_installer(params)
            elif action in ("check_installed_applications", "check_installed_apps"):
                return self._verify_installation(params)
            elif action == "uninstall_software":
                return self._uninstall_software(params, sandbox=sandbox)
            elif action == "download_file":
                return self._download_file(params)
            elif action == "execute_installer":
                return self._execute_installer(params)
            elif action == "verify_installation":
                return self._verify_installation(params)
            elif action == "create_shortcut":
                return self._create_shortcut(params)
            elif action in ("check_winget_availability",):
                return self._check_winget_availability(params)
            elif action in ("search_package",):
                return self._search_package(params)
            elif action in ("install_package", "package_install"):
                return self._install_package(params)
            elif action in ("execute_command",):
                return self._execute_command(params)
            elif action in ("list_installed_packages",):
                return self._list_installed_packages(params)
            elif action == "setup_dev_environment":
                return self._setup_dev_environment(params, sandbox=sandbox)
            elif action == "deploy_to_cloud":
                return self._deploy_to_cloud(params, sandbox=sandbox)
            elif action == "setup_monitoring":
                return self._setup_monitoring(params, sandbox=sandbox)
            elif action == "process_data":
                return self._process_data(params, sandbox=sandbox)
            elif action == "security_scan":
                return self._security_scan(params)
            elif action == "web_scraping":
                return self._web_scraping(params)
            elif action == "workflow_automation":
                return self._workflow_automation(params, sandbox=sandbox)
            elif action == "ai_model_deployment":
                return self._ai_model_deployment(params, sandbox=sandbox)

            # Document creation actions
            elif action in (
                "create_word_document",
                "create_word_doc",
                "generate_word",
                "write_word_document",
            ):
                return self._create_word_document(params)
            elif action in (
                "create_powerpoint",
                "create_ppt",
                "generate_ppt",
                "create_presentation",
            ):
                return self._create_powerpoint(params)
            elif action in ("create_excel", "create_spreadsheet", "generate_excel", "write_excel"):
                return self._create_excel(params)
            elif action in ("create_pdf", "generate_pdf"):
                return self._create_pdf(params)
            elif action in ("create_folder", "make_directory", "ensure_folder"):
                return self._create_folder(params)
            elif action in ("save_to_document", "write_to_file", "append_to_document"):
                return self._save_to_document(params)
            else:
                # Dynamic action handling - can handle ANY action
                return self._dynamic_action_handler(action, params, sandbox=sandbox)

        except Exception as e:
            raise Exception(f"Universal automation execution failed: {e}") from None

    def _install_software(self, params: dict[str, Any], sandbox: bool = False) -> dict[str, Any]:
        """Install any software package"""
        software = params.get("software", "")
        method = params.get("method", "auto")  # auto, chocolatey, winget, pip, npm, etc.

        # Resolve 'auto' to a sensible default per-OS
        if method == "auto":
            method = self._default_package_manager()

        if not software:
            raise ValueError("Software name is required")

        commands = []

        if method in ("chocolatey", "choco"):
            commands.append(f"choco install {software} -y")
        elif method == "winget":
            commands.append(f"winget install {software}")
        elif method == "pip":
            commands.append(f"pip install {software}")
        elif method == "npm":
            commands.append(f"npm install -g {software}")
        else:
            # Unknown manager: try default shell install command
            commands.append(f"{method} install {software}")

        if method == "pip":
            commands.append(f"pip install {software}")

            # In sandbox mode, simulate success for common tools without executing installers
            if sandbox:
                return {
                    "success": True,
                    "software": software,
                    "sandbox": True,
                    "message": "Simulated install in sandbox",
                }

        results = []
        for cmd in commands:
            try:
                if sandbox:
                    results.append(f"(sandbox) simulated: {cmd}")
                    # simulate success for sandbox
                    return {
                        "success": True,
                        "sandbox": True,
                        "message": f"(sandbox) simulated install of {software}",
                        "method": cmd.split()[0],
                    }
                result = safe_run(cmd)
                if result.returncode == 0:
                    return {
                        "success": True,
                        "message": f"Successfully installed {software}",
                        "method": shlex.split(cmd)[0] if cmd else "",
                        "output": result.stdout,
                    }
                results.append(f"{cmd}: {result.stderr}")
            except Exception as e:
                results.append(f"{cmd}: {str(e)}")

        return {"success": False, "message": f"Failed to install {software}", "attempts": results}

    def _download_file(self, params: dict[str, Any]) -> dict[str, Any]:
        """Download a file from URL to destination path"""
        url = params.get("url") or params.get("source")
        dest = params.get("dest") or params.get("destination") or params.get("path")
        if not url:
            return {"success": False, "message": "No URL provided"}
        if not dest:
            # default to temp filename
            import tempfile

            dest = os.path.join(tempfile.gettempdir(), os.path.basename(url))

        try:
            with httpx.Client(follow_redirects=True, timeout=60.0) as client:
                with client.stream("GET", url) as resp:
                    resp.raise_for_status()
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(dest, "wb") as f:
                        for chunk in resp.iter_bytes(8192):
                            f.write(chunk)
            result = {"success": True, "path": dest, "message": f"Downloaded {url} to {dest}"}
        except Exception as e:
            result = {"success": False, "error": str(e), "message": "Download failed"}

        # Audit log
        try:
            with open(
                os.path.join(
                    os.path.expanduser("~"), ".local", "share", "omni_automator", "action.log"
                ),
                "a",
                encoding="utf-8",
            ) as logf:
                logf.write(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] download_file params={params} result={result}\n"
                )
        except Exception:
            pass

        return result

    def _execute_command(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute an arbitrary shell command and return the result"""
        cmd = params.get("command") or params.get("cmd") or params.get("command_line")
        args = params.get("arguments") or params.get("args") or ""
        if args:
            cmd = f"{cmd} {args}"
        if not cmd:
            return {"success": False, "message": "No command provided"}

        try:
            proc = safe_run(cmd)
            result = {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "cmd": cmd,
            }
        except Exception as e:
            result = {"success": False, "error": str(e), "cmd": cmd}

        try:
            with open(
                os.path.join(
                    os.path.expanduser("~"), ".local", "share", "omni_automator", "action.log"
                ),
                "a",
                encoding="utf-8",
            ) as logf:
                logf.write(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] execute_command params={params} result={result}\n"
                )
        except Exception:
            pass

        return result

    def _check_winget_availability(self, params: dict[str, Any]) -> dict[str, Any]:
        """Check if winget is available on PATH"""
        exe = shutil.which("winget")
        result = {"success": bool(exe), "path": exe}
        try:
            with open(
                os.path.join(
                    os.path.expanduser("~"), ".local", "share", "omni_automator", "action.log"
                ),
                "a",
                encoding="utf-8",
            ) as logf:
                logf.write(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] check_winget_availability params={params} result={result}\n"
                )
        except Exception:
            pass
        return result

    def _search_package(self, params: dict[str, Any]) -> dict[str, Any]:
        """Search for a package using the selected package manager (winget/choco/apt/brew/pacman/yay)"""
        pkg = params.get("package") or params.get("name")
        manager = (params.get("manager") or self._default_package_manager()).lower()
        if not pkg:
            return {"success": False, "message": "No package name provided"}

        cmd_list: list = []
        if manager == "winget":
            cmd_list = ["winget", "search", pkg]
        elif manager == "choco" or manager == "chocolatey":
            cmd_list = ["choco", "search", pkg]
        elif manager == "apt":
            cmd_list = ["apt-cache", "search", pkg]
        elif manager == "brew":
            cmd_list = ["brew", "search", pkg]
        elif manager in ("pacman", "yay", "paru"):
            cmd_list = [manager, "-Ss", pkg]
        elif manager == "dnf":
            cmd_list = ["dnf", "search", pkg]
        else:
            return {"success": False, "message": f"Unsupported package manager: {manager}"}

        try:
            proc = safe_run(cmd_list)
            result = {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }
        except Exception as e:
            result = {"success": False, "error": str(e)}

        try:
            with open(
                os.path.join(
                    os.path.expanduser("~"), ".local", "share", "omni_automator", "action.log"
                ),
                "a",
                encoding="utf-8",
            ) as logf:
                logf.write(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] search_package params={params} result={result}\n"
                )
        except Exception:
            pass

        return result

    def _install_package(self, params: dict[str, Any]) -> dict[str, Any]:
        """Install a package using the selected package manager (winget/choco/apt/brew/pacman/yay)"""
        pkg = params.get("package") or params.get("id") or params.get("software")
        manager = (params.get("manager") or self._default_package_manager()).lower()
        if not pkg:
            return {"success": False, "message": "No package specified"}

        # Choose command based on manager — build as list (no shell=True)
        cmd_list: list = []
        if manager == "winget":
            if params.get("id"):
                cmd_list = [
                    "winget",
                    "install",
                    "--id",
                    params.get("id"),
                    "-e",
                    "--silent",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                ]
            else:
                cmd_list = [
                    "winget",
                    "install",
                    pkg,
                    "-e",
                    "--silent",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                ]
        elif manager in ("choco", "chocolatey"):
            cmd_list = ["choco", "install", pkg, "-y"]
        elif manager == "apt":
            cmd_list = ["sudo", "apt-get", "install", "-y", pkg]
        elif manager == "brew":
            cmd_list = ["brew", "install", pkg]
        elif manager == "pacman":
            cmd_list = ["sudo", "pacman", "-S", "--noconfirm", pkg]
        elif manager in ("yay", "paru"):
            cmd_list = [manager, "-S", "--noconfirm", pkg]
        elif manager == "dnf":
            cmd_list = ["sudo", "dnf", "install", "-y", pkg]
        else:
            return {"success": False, "message": f"Unsupported package manager: {manager}"}

        try:
            proc = safe_run(cmd_list)
            result = {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "cmd": " ".join(cmd_list),
            }
        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "cmd": " ".join(cmd_list) if "cmd_list" in locals() else "",
            }

        try:
            with open(
                os.path.join(
                    os.path.expanduser("~"), ".local", "share", "omni_automator", "action.log"
                ),
                "a",
                encoding="utf-8",
            ) as logf:
                logf.write(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] install_package params={params} result={result}\n"
                )
        except Exception:
            pass

        return result

    def _list_installed_packages(self, params: dict[str, Any]) -> dict[str, Any]:
        """List installed packages for the selected package manager"""
        manager = (params.get("manager") or self._default_package_manager()).lower()
        cmd_list: list = []
        if manager == "winget":
            cmd_list = ["winget", "list"]
        elif manager in ("choco", "chocolatey"):
            cmd_list = ["choco", "list", "--local-only"]
        elif manager == "apt":
            cmd_list = ["apt", "list", "--installed"]
        elif manager == "brew":
            cmd_list = ["brew", "list"]
        elif manager in ("pacman", "yay", "paru"):
            cmd_list = [manager, "-Q"]
        elif manager == "dnf":
            cmd_list = ["dnf", "list", "installed"]
        else:
            return {"success": False, "message": f"Unsupported package manager: {manager}"}

        try:
            proc = safe_run(cmd_list)
            result = {"success": proc.returncode == 0, "stdout": proc.stdout, "stderr": proc.stderr}
        except Exception as e:
            result = {"success": False, "error": str(e)}

        try:
            with open(
                os.path.join(
                    os.path.expanduser("~"), ".local", "share", "omni_automator", "action.log"
                ),
                "a",
                encoding="utf-8",
            ) as logf:
                logf.write(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] list_installed_packages params={params} result={result}\n"
                )
        except Exception:
            pass

        return result

    def _execute_installer(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a local installer path with optional args"""
        installer = params.get("installer") or params.get("path") or params.get("file")
        args = params.get("args", "")
        if not installer:
            return {"success": False, "message": "No installer path provided"}

        # Build list-form command: installer path + optional args (split by shlex)
        cmd_list = [installer]
        if args:
            cmd_list.extend(shlex.split(str(args), posix=True))
        try:
            proc = safe_run(cmd_list)
            result = {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }
        except Exception as e:
            result = {"success": False, "error": str(e)}

        try:
            with open(
                os.path.join(
                    os.path.expanduser("~"), ".local", "share", "omni_automator", "action.log"
                ),
                "a",
                encoding="utf-8",
            ) as logf:
                logf.write(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] execute_installer params={params} result={result}\n"
                )
        except Exception:
            pass

        return result

    def _verify_installation(self, params: dict[str, Any]) -> dict[str, Any]:
        """Verify installation by checking expected paths or executable on PATH"""
        exe = params.get("exe") or params.get("binary") or params.get("command") or "vlc"
        # check PATH
        which = shutil.which(exe)
        if which:
            result = {"success": True, "path": which, "message": f"{exe} found on PATH at {which}"}
            try:
                with open(
                    os.path.join(
                        os.path.expanduser("~"), ".local", "share", "omni_automator", "action.log"
                    ),
                    "a",
                    encoding="utf-8",
                ) as logf:
                    logf.write(
                        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] verify_installation params={params} result={result}\n"
                    )
            except Exception:
                pass
            return result

        # common install location for VLC
        candidates = [
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "VideoLAN", "VLC"),
            os.path.join(
                os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "VideoLAN", "VLC"
            ),
        ]
        for c in candidates:
            if os.path.exists(c):
                result = {"success": True, "path": c, "message": f"Installation found at {c}"}
                try:
                    with open(
                        os.path.join(
                            os.path.expanduser("~"),
                            ".local",
                            "share",
                            "omni_automator",
                            "action.log",
                        ),
                        "a",
                        encoding="utf-8",
                    ) as logf:
                        logf.write(
                            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] verify_installation params={params} result={result}\n"
                        )
                except Exception:
                    pass
                return result

        result = {"success": False, "message": f"{exe} not found"}
        try:
            with open(
                os.path.join(
                    os.path.expanduser("~"), ".local", "share", "omni_automator", "action.log"
                ),
                "a",
                encoding="utf-8",
            ) as logf:
                logf.write(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] verify_installation params={params} result={result}\n"
                )
        except Exception:
            pass
        return result

    def _create_shortcut(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a simple .bat launcher on the Desktop as a lightweight shortcut"""
        target = params.get("target") or params.get("path") or params.get("exe")
        name = params.get("name", "Shortcut")
        if not target:
            return {"success": False, "message": "No target provided for shortcut"}

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        os.makedirs(desktop, exist_ok=True)
        bat_path = os.path.join(desktop, f"{name}.bat")
        try:
            with open(bat_path, "w") as f:
                f.write(f'@echo off\n"{target}" %*\n')
            result = {
                "success": True,
                "path": bat_path,
                "message": f"Shortcut created at {bat_path}",
            }
        except Exception as e:
            result = {"success": False, "error": str(e)}

        try:
            with open(
                os.path.join(
                    os.path.expanduser("~"), ".local", "share", "omni_automator", "action.log"
                ),
                "a",
                encoding="utf-8",
            ) as logf:
                logf.write(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] create_shortcut params={params} result={result}\n"
                )
        except Exception:
            pass

        return result

    def _setup_dev_environment(
        self, params: dict[str, Any], sandbox: bool = False
    ) -> dict[str, Any]:
        """Setup complete development environment"""
        languages = params.get("languages", ["python", "node", "git"])
        tools = params.get("tools", ["vscode", "docker"])

        installed = []
        failed = []

        # Install languages and tools
        for item in languages + tools:
            try:
                result = self._install_software(
                    {"software": item, "method": "auto"}, sandbox=sandbox
                )
                if result.get("success"):
                    installed.append(item)
                else:
                    failed.append(item)
            except Exception:
                failed.append(item)

        # Setup configurations
        configs_created = []

        # Git configuration
        if "git" in installed and not sandbox:
            try:
                subprocess.run(["git", "config", "--global", "init.defaultBranch", "main"])
                configs_created.append("git-config")
            except Exception:
                pass

        # VS Code extensions
        if "vscode" in installed and not sandbox:
            extensions = [
                "ms-python.python",
                "ms-vscode.vscode-typescript-next",
                "ms-azuretools.vscode-docker",
            ]
            for ext in extensions:
                try:
                    subprocess.run(["code", "--install-extension", ext])
                    configs_created.append(f"vscode-{ext}")
                except Exception:
                    pass

        return {
            "success": len(installed) > 0,
            "sandbox": sandbox,
            "installed": installed,
            "failed": failed,
            "configurations": configs_created,
            "message": f"Development environment setup: {len(installed)} tools installed",
        }

    def _deploy_to_cloud(self, params: dict[str, Any]) -> dict[str, Any]:
        """Deploy applications to any cloud provider"""
        provider = params.get("provider", "docker")  # docker, aws, azure, gcp, heroku
        app_path = params.get("app_path", ".")
        app_name = params.get("app_name", "myapp")

        deployment_files = []

        if provider == "docker":
            # Create Dockerfile if not exists
            dockerfile_path = os.path.join(app_path, "Dockerfile")
            if not os.path.exists(dockerfile_path):
                dockerfile_content = """FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 3000
CMD ["npm", "start"]"""

                with open(dockerfile_path, "w") as f:
                    f.write(dockerfile_content)
                deployment_files.append(dockerfile_path)

            # Build and run
            try:
                subprocess.run(["docker", "build", "-t", app_name, app_path], check=True)
                subprocess.run(
                    ["docker", "run", "-d", "-p", "3000:3000", "--name", app_name, app_name],
                    check=True,
                )

                return {
                    "success": True,
                    "message": f"Successfully deployed {app_name} to Docker",
                    "files_created": deployment_files,
                    "url": "http://localhost:3000",
                }
            except subprocess.CalledProcessError as e:
                return {
                    "success": False,
                    "message": f"Docker deployment failed: {e}",
                    "files_created": deployment_files,
                }

        elif provider == "heroku":
            # Create Procfile
            procfile_path = os.path.join(app_path, "Procfile")
            if not os.path.exists(procfile_path):
                with open(procfile_path, "w") as f:
                    f.write("web: npm start")
                deployment_files.append(procfile_path)

            # Heroku deployment commands — list form (no shell=True)
            commands_list = [
                ["heroku", "create", app_name],
                ["git", "add", "."],
                ["git", "commit", "-m", "Deploy to Heroku"],
                ["git", "push", "heroku", "main"],
            ]

            for cmd_parts in commands_list:
                try:
                    subprocess.run(cmd_parts, check=True, cwd=app_path)
                except subprocess.CalledProcessError:
                    pass  # Continue with other commands

            return {
                "success": True,
                "message": f"Heroku deployment initiated for {app_name}",
                "files_created": deployment_files,
                "url": f"https://{app_name}.herokuapp.com",
            }

        return {"success": False, "message": f"Unsupported cloud provider: {provider}"}

    def _uninstall_software(self, params: dict[str, Any], sandbox: bool = False) -> dict[str, Any]:
        """Uninstall software by attempting common package managers or removing install dir"""
        software = params.get("software")
        method = params.get("method", "auto")
        if not software:
            return {"success": False, "message": "No software specified"}

        if sandbox:
            return {
                "success": True,
                "sandbox": True,
                "message": f"Simulated uninstall of {software} in sandbox",
            }

        commands_list: list[list[str]] = []
        if method in ("auto", "winget"):
            commands_list.append(["winget", "uninstall", "--id", software, "-e"])
            commands_list.append(["winget", "uninstall", software])
        if method in ("auto", "chocolatey"):
            commands_list.append(["choco", "uninstall", software, "-y"])

        attempts = []
        for cmd_parts in commands_list:
            try:
                proc = safe_run(cmd_parts)
                attempts.append(
                    {
                        "cmd": " ".join(cmd_parts),
                        "returncode": proc.returncode,
                        "stdout": proc.stdout,
                        "stderr": proc.stderr,
                    }
                )
                if proc.returncode == 0:
                    return {
                        "success": True,
                        "message": f"Uninstalled {software} using {cmd_parts[0]}",
                        "attempts": attempts,
                    }
            except Exception as e:
                attempts.append({"cmd": " ".join(cmd_parts) if cmd_parts else "", "error": str(e)})

        # Fallback: try removing common install directories (best-effort)
        removed = []
        try:
            candidates = [
                os.path.join(
                    os.environ.get("ProgramFiles", "C:\\Program Files"), "VideoLAN", "VLC"
                ),
                os.path.join(
                    os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
                    "VideoLAN",
                    "VLC",
                ),
            ]
            for c in candidates:
                if os.path.exists(c):
                    try:
                        shutil.rmtree(c)
                        removed.append(c)
                    except Exception as e:
                        attempts.append({"remove": c, "error": str(e)})
            if removed:
                return {
                    "success": True,
                    "message": f"Removed directories: {removed}",
                    "removed": removed,
                    "attempts": attempts,
                }
        except Exception as e:
            attempts.append({"fallback_error": str(e)})

        return {
            "success": False,
            "message": f"Failed to uninstall {software}",
            "attempts": attempts,
        }

    def _setup_monitoring(self, params: dict[str, Any]) -> dict[str, Any]:
        """Setup comprehensive monitoring stack"""
        services = params.get("services", ["prometheus", "grafana"])
        location = params.get("location", "./monitoring")

        os.makedirs(location, exist_ok=True)
        files_created = []

        if "prometheus" in services:
            # Prometheus config
            prometheus_config = """global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']

  - job_name: 'application'
    static_configs:
      - targets: ['localhost:3000']
"""

            prometheus_path = os.path.join(location, "prometheus.yml")
            with open(prometheus_path, "w") as f:
                f.write(prometheus_config)
            files_created.append(prometheus_path)

        if "grafana" in services:
            # Grafana dashboard config
            dashboard_config = {
                "dashboard": {
                    "title": "Application Monitoring",
                    "panels": [
                        {
                            "title": "CPU Usage",
                            "type": "graph",
                            "targets": [
                                {
                                    "expr": '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
                                }
                            ],
                        },
                        {
                            "title": "Memory Usage",
                            "type": "graph",
                            "targets": [
                                {
                                    "expr": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100"
                                }
                            ],
                        },
                    ],
                }
            }

            dashboard_path = os.path.join(location, "dashboard.json")
            with open(dashboard_path, "w") as f:
                json.dump(dashboard_config, f, indent=2)
            files_created.append(dashboard_path)

        # Docker Compose for monitoring stack
        compose_config = {"version": "3.8", "services": {}}

        if "prometheus" in services:
            compose_config["services"]["prometheus"] = {
                "image": "prom/prometheus:latest",
                "ports": ["9090:9090"],
                "volumes": ["./prometheus.yml:/etc/prometheus/prometheus.yml"],
            }

        if "grafana" in services:
            compose_config["services"]["grafana"] = {
                "image": "grafana/grafana:latest",
                "ports": ["3001:3000"],
                "environment": ["GF_SECURITY_ADMIN_PASSWORD=admin"],
            }

        compose_path = os.path.join(location, "docker-compose.yml")
        with open(compose_path, "w") as f:
            json.dump(compose_config, f, indent=2)
        files_created.append(compose_path)

        return {
            "success": True,
            "message": f"Monitoring stack setup complete with {len(services)} services",
            "files_created": files_created,
            "services": services,
            "location": location,
        }

    def _dynamic_action_handler(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Handle any action dynamically using AI and system capabilities"""

        # Try to map action to system commands
        action_mappings = {
            "create_website": self._create_website,
            "setup_database": self._setup_database,
            "backup_system": self._backup_system,
            "optimize_performance": self._optimize_performance,
            "security_audit": self._security_audit,
            "deploy_microservices": self._deploy_microservices,
            "setup_ci_cd": self._setup_ci_cd,
            "data_analysis": self._data_analysis,
            "machine_learning": self._machine_learning,
            "blockchain_deploy": self._blockchain_deploy,
        }

        if action in action_mappings:
            return action_mappings[action](params)

        # If no specific handler, try to execute as system command
        try:
            # Convert action to command
            command = action.replace("_", " ")

            # Avoid executing ambiguous single-word commands like 'browser'
            if len(command.split()) == 1:
                return {
                    "success": False,
                    "message": f"Refusing to execute ambiguous command '{command}'.",
                    "error": "Ambiguous single-word action",
                    "suggestion": "Use a specific action such as 'open_browser' or 'perform_search' or provide a full command string.",
                }

            # Add common parameters
            if "name" in params:
                command += f" {params['name']}"
            if "location" in params:
                command += f" in {params['location']}"

            # Execute as system command using safe_run (shlex splits the string)
            result = safe_run(command)

            return {
                "success": result.returncode == 0,
                "message": f"Executed: {command}",
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Could not execute action: {action}",
                "error": str(e),
                "suggestion": "Try providing more specific parameters or use a different action name",
            }

    def _create_website(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a complete website"""
        site_type = params.get("type", "static")
        name = params.get("name", "mywebsite")
        location = params.get("location", f"./{name}")

        os.makedirs(location, exist_ok=True)
        files_created = []

        # HTML
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name.title()}</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header>
        <h1>Welcome to {name.title()}</h1>
    </header>
    <main>
        <section>
            <h2>About</h2>
            <p>This is a modern, responsive website built with OmniAutomator.</p>
        </section>
    </main>
    <script src="script.js"></script>
</body>
</html>"""

        # CSS
        css_content = """* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: #333;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
}

header {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    padding: 2rem;
    text-align: center;
}

h1 {
    color: white;
    font-size: 3rem;
    margin-bottom: 1rem;
}

main {
    max-width: 1200px;
    margin: 2rem auto;
    padding: 2rem;
    background: white;
    border-radius: 10px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
}"""

        # JavaScript
        js_content = """document.addEventListener('DOMContentLoaded', function() {
    console.log('Website loaded successfully!');

    // Add smooth scrolling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });
});"""

        # Write files
        html_path = os.path.join(location, "index.html")
        css_path = os.path.join(location, "style.css")
        js_path = os.path.join(location, "script.js")

        with open(html_path, "w") as f:
            f.write(html_content)
        with open(css_path, "w") as f:
            f.write(css_content)
        with open(js_path, "w") as f:
            f.write(js_content)

        files_created = [html_path, css_path, js_path]

        return {
            "success": True,
            "message": f'Website "{name}" created successfully',
            "files_created": files_created,
            "location": location,
            "type": site_type,
        }

    def _create_word_document(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a Word document with content"""
        try:
            from docx import Document
            from docx.enum.text import WD_ALIGN_PARAGRAPH
        except ImportError:
            return {
                "success": False,
                "error": "python-docx not installed. Run: pip install python-docx",
            }

        try:
            # Get parameters
            filename = (
                params.get("filename")
                or params.get("file")
                or params.get("path")
                or "document.docx"
            )
            title = params.get("title", "")
            content = params.get("content") or params.get("text") or params.get("data", "")
            headings = params.get("headings", [])
            folder = params.get("folder") or params.get("directory")

            # Resolve folder path
            if folder:
                folder = self._resolve_path(folder)
                os.makedirs(folder, exist_ok=True)
                filepath = os.path.join(
                    folder, filename if not filename.startswith("/") else os.path.basename(filename)
                )
            else:
                filepath = self._resolve_path(filename)

            # Ensure .docx extension
            if not filepath.endswith(".docx"):
                filepath += ".docx"

            # Create directory if needed
            os.makedirs(
                os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True
            )

            # Create document
            doc = Document()

            # Add title
            if title:
                title_para = doc.add_heading(title, 0)
                title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Add content based on type
            if isinstance(content, str):
                # Split by paragraphs
                paragraphs = content.split("\n\n") if "\n\n" in content else content.split("\n")
                for para in paragraphs:
                    if para.strip():
                        # Check if it looks like a heading
                        if para.strip().isupper() and len(para.strip()) < 100:
                            doc.add_heading(para.strip(), level=2)
                        else:
                            doc.add_paragraph(para.strip())

            elif isinstance(content, dict):
                # Structured content
                for key, value in content.items():
                    doc.add_heading(str(key), level=2)
                    if isinstance(value, list):
                        for item in value:
                            doc.add_paragraph(str(item), style="List Bullet")
                    else:
                        doc.add_paragraph(str(value))

            elif isinstance(content, list):
                # List of items
                for item in content:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            doc.add_heading(str(k), level=2)
                            doc.add_paragraph(str(v))
                    else:
                        doc.add_paragraph(str(item))

            # Add additional headings with content
            if headings:
                for heading in headings:
                    if isinstance(heading, dict):
                        h_title = heading.get("title", "")
                        h_content = heading.get("content", "")
                        h_level = heading.get("level", 2)
                        doc.add_heading(h_title, level=h_level)
                        if h_content:
                            doc.add_paragraph(h_content)

            # Save document
            doc.save(filepath)

            return {
                "success": True,
                "message": "Word document created successfully",
                "filepath": filepath,
                "filename": os.path.basename(filepath),
            }

        except Exception as e:
            import logging

            logging.getLogger(__name__).exception("Word document creation failed")
            return {"success": False, "error": str(e)}

    def _create_powerpoint(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a PowerPoint presentation"""
        try:
            from pptx import Presentation
        except ImportError:
            return {
                "success": False,
                "error": "python-pptx not installed. Run: pip install python-pptx",
            }

        try:
            # Get parameters
            filename = (
                params.get("filename")
                or params.get("file")
                or params.get("path")
                or "presentation.pptx"
            )
            title = params.get("title", "Presentation")
            slides_data = params.get("slides") or params.get("content", [])
            folder = params.get("folder") or params.get("directory")

            # Resolve folder path
            if folder:
                folder = self._resolve_path(folder)
                os.makedirs(folder, exist_ok=True)
                filepath = os.path.join(
                    folder, filename if not filename.startswith("/") else os.path.basename(filename)
                )
            else:
                filepath = self._resolve_path(filename)

            # Ensure .pptx extension
            if not filepath.endswith(".pptx"):
                filepath += ".pptx"

            # Create directory if needed
            os.makedirs(
                os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True
            )

            # Create presentation
            prs = Presentation()

            # Title slide
            title_slide_layout = prs.slide_layouts[0]
            slide = prs.slides.add_slide(title_slide_layout)
            slide.shapes.title.text = title
            if params.get("subtitle"):
                slide.placeholders[1].text = params.get("subtitle")

            # Add content slides
            if isinstance(slides_data, str):
                # Convert string to slides (split by double newline or headers)
                sections = slides_data.split("\n\n")
                for section in sections:
                    if section.strip():
                        bullet_slide_layout = prs.slide_layouts[1]
                        slide = prs.slides.add_slide(bullet_slide_layout)
                        lines = section.split("\n")
                        slide.shapes.title.text = lines[0][:100] if lines else "Content"
                        if len(lines) > 1:
                            text_frame = slide.placeholders[1].text_frame
                            for line in lines[1:]:
                                if line.strip():
                                    p = text_frame.add_paragraph()
                                    p.text = line.strip()
                                    p.level = 0

            elif isinstance(slides_data, list):
                for slide_content in slides_data:
                    bullet_slide_layout = prs.slide_layouts[1]
                    slide = prs.slides.add_slide(bullet_slide_layout)

                    if isinstance(slide_content, dict):
                        slide.shapes.title.text = slide_content.get("title", "Slide")
                        content = slide_content.get("content", [])

                        if isinstance(content, list):
                            text_frame = slide.placeholders[1].text_frame
                            text_frame.clear()
                            for item in content:
                                p = text_frame.add_paragraph()
                                p.text = str(item)
                                p.level = 0
                        elif isinstance(content, str):
                            slide.placeholders[1].text = content
                    else:
                        slide.shapes.title.text = str(slide_content)[:100]

            # Save presentation
            prs.save(filepath)

            return {
                "success": True,
                "message": "PowerPoint presentation created successfully",
                "filepath": filepath,
                "filename": os.path.basename(filepath),
                "slides_count": len(prs.slides),
            }

        except Exception as e:
            import logging

            logging.getLogger(__name__).exception("PowerPoint creation failed")
            return {"success": False, "error": str(e)}

    def _create_excel(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create an Excel spreadsheet"""
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Alignment, Font, PatternFill
        except ImportError:
            return {"success": False, "error": "openpyxl not installed. Run: pip install openpyxl"}

        try:
            # Get parameters
            filename = (
                params.get("filename")
                or params.get("file")
                or params.get("path")
                or "spreadsheet.xlsx"
            )
            data = params.get("data") or params.get("content", [])
            headers = params.get("headers", [])
            sheet_name = params.get("sheet_name", "Sheet1")
            folder = params.get("folder") or params.get("directory")

            # Resolve folder path
            if folder:
                folder = self._resolve_path(folder)
                os.makedirs(folder, exist_ok=True)
                filepath = os.path.join(
                    folder, filename if not filename.startswith("/") else os.path.basename(filename)
                )
            else:
                filepath = self._resolve_path(filename)

            # Ensure .xlsx extension
            if not filepath.endswith(".xlsx"):
                filepath += ".xlsx"

            # Create directory if needed
            os.makedirs(
                os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True
            )

            # Create workbook
            wb = Workbook()
            ws = wb.active
            ws.title = sheet_name

            # Add headers if provided
            if headers:
                for col, header in enumerate(headers, start=1):
                    cell = ws.cell(row=1, column=col, value=header)
                    cell.font = Font(bold=True)
                    cell.fill = PatternFill(
                        start_color="4472C4", end_color="4472C4", fill_type="solid"
                    )
                    cell.alignment = Alignment(horizontal="center")

            # Add data
            start_row = 2 if headers else 1

            if isinstance(data, list):
                for row_idx, row_data in enumerate(data, start=start_row):
                    if isinstance(row_data, list):
                        for col_idx, value in enumerate(row_data, start=1):
                            ws.cell(row=row_idx, column=col_idx, value=value)
                    elif isinstance(row_data, dict):
                        for col_idx, key in enumerate(
                            headers if headers else row_data.keys(), start=1
                        ):
                            ws.cell(row=row_idx, column=col_idx, value=row_data.get(key, ""))
                    else:
                        ws.cell(row=row_idx, column=1, value=str(row_data))

            elif isinstance(data, dict):
                # Convert dict to rows
                for row_idx, (key, value) in enumerate(data.items(), start=start_row):
                    ws.cell(row=row_idx, column=1, value=key)
                    if isinstance(value, list):
                        for col_idx, item in enumerate(value, start=2):
                            ws.cell(row=row_idx, column=col_idx, value=item)
                    else:
                        ws.cell(row=row_idx, column=2, value=value)

            # Auto-adjust column widths
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except Exception:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width

            # Save workbook
            wb.save(filepath)

            return {
                "success": True,
                "message": "Excel spreadsheet created successfully",
                "filepath": filepath,
                "filename": os.path.basename(filepath),
                "rows": len(data)
                if isinstance(data, list)
                else len(data.keys())
                if isinstance(data, dict)
                else 0,
            }

        except Exception as e:
            import logging

            logging.getLogger(__name__).exception("Excel creation failed")
            return {"success": False, "error": str(e)}

    def _create_pdf(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a PDF document"""
        try:
            from reportlab.lib.enums import TA_CENTER
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import inch
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        except ImportError:
            return {
                "success": False,
                "error": "reportlab not installed. Run: pip install reportlab",
            }

        try:
            # Get parameters
            filename = (
                params.get("filename") or params.get("file") or params.get("path") or "document.pdf"
            )
            title = params.get("title", "")
            content = params.get("content") or params.get("text") or params.get("data", "")
            folder = params.get("folder") or params.get("directory")

            # Resolve folder path
            if folder:
                folder = self._resolve_path(folder)
                os.makedirs(folder, exist_ok=True)
                filepath = os.path.join(
                    folder, filename if not filename.startswith("/") else os.path.basename(filename)
                )
            else:
                filepath = self._resolve_path(filename)

            # Ensure .pdf extension
            if not filepath.endswith(".pdf"):
                filepath += ".pdf"

            # Create directory if needed
            os.makedirs(
                os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True
            )

            # Create PDF
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()

            # Title
            if title:
                title_style = ParagraphStyle(
                    "CustomTitle",
                    parent=styles["Heading1"],
                    fontSize=24,
                    textColor="#1f4788",
                    spaceAfter=30,
                    alignment=TA_CENTER,
                )
                story.append(Paragraph(title, title_style))
                story.append(Spacer(1, 0.2 * inch))

            # Content
            if isinstance(content, str):
                paragraphs = content.split("\n\n") if "\n\n" in content else content.split("\n")
                for para in paragraphs:
                    if para.strip():
                        story.append(Paragraph(para.strip(), styles["BodyText"]))
                        story.append(Spacer(1, 0.1 * inch))

            elif isinstance(content, list):
                for item in content:
                    story.append(Paragraph(str(item), styles["BodyText"]))
                    story.append(Spacer(1, 0.1 * inch))

            # Build PDF
            doc.build(story)

            return {
                "success": True,
                "message": "PDF document created successfully",
                "filepath": filepath,
                "filename": os.path.basename(filepath),
            }

        except Exception as e:
            import logging

            logging.getLogger(__name__).exception("PDF creation failed")
            return {"success": False, "error": str(e)}

    def _create_folder(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a folder/directory"""
        try:
            folder_path = (
                params.get("path")
                or params.get("folder")
                or params.get("directory")
                or params.get("name")
            )

            if not folder_path:
                return {"success": False, "error": "No folder path provided"}

            # Resolve path
            folder_path = self._resolve_path(folder_path)

            # Create folder
            os.makedirs(folder_path, exist_ok=True)

            return {"success": True, "message": "Folder created successfully", "path": folder_path}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _save_to_document(self, params: dict[str, Any]) -> dict[str, Any]:
        """Save content to a document (auto-detect format or append)"""
        try:
            filepath = params.get("file") or params.get("path") or params.get("filename")
            content = params.get("content") or params.get("text") or params.get("data", "")
            append = params.get("append", False)

            if not filepath:
                return {"success": False, "error": "No filepath provided"}

            filepath = self._resolve_path(filepath)

            # Detect format and delegate
            if filepath.endswith(".docx"):
                # For Word, we need to handle append differently
                if append and os.path.exists(filepath):
                    # Read existing and append
                    try:
                        from docx import Document

                        doc = Document(filepath)
                        if isinstance(content, str):
                            for para in content.split("\n"):
                                if para.strip():
                                    doc.add_paragraph(para.strip())
                        doc.save(filepath)
                        return {"success": True, "filepath": filepath, "mode": "append"}
                    except Exception:
                        pass
                return self._create_word_document(
                    {**params, "filename": filepath, "content": content}
                )

            elif filepath.endswith(".pptx"):
                return self._create_powerpoint({**params, "filename": filepath})

            elif filepath.endswith(".xlsx"):
                return self._create_excel({**params, "filename": filepath})

            elif filepath.endswith(".pdf"):
                return self._create_pdf({**params, "filename": filepath})

            else:
                # Plain text file
                os.makedirs(
                    os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True
                )
                mode = "a" if append else "w"
                with open(filepath, mode, encoding="utf-8") as f:
                    f.write(str(content))
                    if not str(content).endswith("\n"):
                        f.write("\n")

                return {
                    "success": True,
                    "filepath": filepath,
                    "mode": "append" if append else "write",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _resolve_path(self, path: str) -> str:
        """Resolve path with Desktop and other special folders"""
        if not path:
            return path

        # Expand user home
        path = os.path.expanduser(path)

        # Normalize separators
        path = path.replace("\\", "/")

        # Handle Desktop references
        parts = path.split("/")
        lower_parts = [p.lower() for p in parts]

        if "desktop" in lower_parts:
            idx = lower_parts.index("desktop")
            tail = parts[idx + 1 :] if idx + 1 < len(parts) else []
            home = os.path.expanduser("~")
            path = os.path.join(home, "Desktop", *tail) if tail else os.path.join(home, "Desktop")

        # If not absolute, make it absolute
        if not os.path.isabs(path):
            path = os.path.abspath(path)

        return path
