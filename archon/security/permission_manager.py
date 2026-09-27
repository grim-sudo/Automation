"""
Permission and security management for automation operations
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from loguru import logger


class PermissionLevel(Enum):
    """Permission levels for different operations"""

    SAFE = "safe"  # Safe operations (read-only, non-destructive)
    MODERATE = "moderate"  # Moderate risk operations (create files, start processes)
    HIGH = "high"  # High risk operations (delete, system changes)
    CRITICAL = "critical"  # Critical operations (shutdown, registry changes)


class ActionCategory(Enum):
    """Categories of automation actions"""

    FILESYSTEM_READ = "filesystem_read"
    FILESYSTEM_WRITE = "filesystem_write"
    FILESYSTEM_DELETE = "filesystem_delete"
    PROCESS_START = "process_start"
    PROCESS_TERMINATE = "process_terminate"
    GUI_AUTOMATION = "gui_automation"
    SYSTEM_SETTINGS = "system_settings"
    NETWORK_ACCESS = "network_access"
    POWER_MANAGEMENT = "power_management"


@dataclass
class PermissionRule:
    """A permission rule for specific actions"""

    category: ActionCategory
    permission_level: PermissionLevel
    allowed_paths: list[str] | None = None
    blocked_paths: list[str] | None = None
    requires_confirmation: bool = False
    description: str = ""


class PermissionManager:
    """Manages permissions and security for automation operations"""

    def __init__(self, config_file: str | None = None):
        self.config_file = config_file or self._get_default_config_path()
        self.sandbox_mode = False
        self.permission_rules = self._load_default_rules()
        self.user_permissions = self._load_user_permissions()
        self.blocked_operations: set[str] = set()

        # Load custom configuration if exists
        self._load_config()

    def _get_default_config_path(self) -> str:
        """Get default configuration file path"""
        config_dir = os.path.expanduser("~/.archon")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "permissions.json")

    def _load_default_rules(self) -> dict[ActionCategory, PermissionRule]:
        """Load default permission rules"""
        self.action_permissions = {
            # Safe operations
            "get_system_info": PermissionLevel.SAFE,
            "list_directory": PermissionLevel.SAFE,
            "take_screenshot": PermissionLevel.SAFE,
            "get_capabilities": PermissionLevel.SAFE,
            # Project generator actions
            "create_python_project": PermissionLevel.MODERATE,
            "create_c_project": PermissionLevel.MODERATE,
            "create_virtual_environment": PermissionLevel.MODERATE,
            "create_virtualenv": PermissionLevel.MODERATE,
            "initialize_git_repo": PermissionLevel.MODERATE,
            "create_web_scraping_project": PermissionLevel.MODERATE,
            "create_data_analysis_project": PermissionLevel.MODERATE,
            "create_news_scraper": PermissionLevel.MODERATE,
            "install_packages": PermissionLevel.MODERATE,
            "generate_sample_data": PermissionLevel.SAFE,
        }

        return {
            ActionCategory.FILESYSTEM_READ: PermissionRule(
                category=ActionCategory.FILESYSTEM_READ,
                permission_level=PermissionLevel.SAFE,
                description="Read files and directories",
            ),
            ActionCategory.FILESYSTEM_WRITE: PermissionRule(
                category=ActionCategory.FILESYSTEM_WRITE,
                permission_level=PermissionLevel.MODERATE,
                blocked_paths=["/system", "/windows", "C:\\Windows", "/etc"],
                description="Create and modify files",
            ),
            ActionCategory.FILESYSTEM_DELETE: PermissionRule(
                category=ActionCategory.FILESYSTEM_DELETE,
                permission_level=PermissionLevel.HIGH,
                blocked_paths=["/system", "/windows", "C:\\Windows", "/etc", "/usr"],
                requires_confirmation=True,
                description="Delete files and directories",
            ),
            ActionCategory.PROCESS_START: PermissionRule(
                category=ActionCategory.PROCESS_START,
                permission_level=PermissionLevel.MODERATE,
                description="Start new processes",
            ),
            ActionCategory.PROCESS_TERMINATE: PermissionRule(
                category=ActionCategory.PROCESS_TERMINATE,
                permission_level=PermissionLevel.HIGH,
                requires_confirmation=True,
                description="Terminate running processes",
            ),
            ActionCategory.GUI_AUTOMATION: PermissionRule(
                category=ActionCategory.GUI_AUTOMATION,
                permission_level=PermissionLevel.MODERATE,
                description="GUI automation (clicks, typing)",
            ),
            ActionCategory.SYSTEM_SETTINGS: PermissionRule(
                category=ActionCategory.SYSTEM_SETTINGS,
                permission_level=PermissionLevel.HIGH,
                requires_confirmation=True,
                description="Modify system settings",
            ),
            ActionCategory.NETWORK_ACCESS: PermissionRule(
                category=ActionCategory.NETWORK_ACCESS,
                permission_level=PermissionLevel.MODERATE,
                description="Network operations",
            ),
            ActionCategory.POWER_MANAGEMENT: PermissionRule(
                category=ActionCategory.POWER_MANAGEMENT,
                permission_level=PermissionLevel.CRITICAL,
                requires_confirmation=True,
                description="Power operations (shutdown, restart)",
            ),
        }

    def _load_user_permissions(self) -> dict[str, bool]:
        """Load user-granted permissions"""
        return {
            "filesystem_write": True,
            "filesystem_delete": True,
            "process_terminate": False,
            "system_settings": False,
            "power_management": False,
        }

    def _load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file) as f:
                    config = json.load(f)
                    self.user_permissions.update(config.get("permissions", {}))
                    self.blocked_operations.update(config.get("blocked_operations", []))
        except Exception as e:
            logger.warning(f"Could not load permission config: {e}")

    def _save_config(self):
        """Save configuration to file"""
        try:
            config = {
                "permissions": self.user_permissions,
                "blocked_operations": list(self.blocked_operations),
                "last_updated": datetime.now().isoformat(),
            }

            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save permission config: {e}")

    # Keyword-based screen for raw, unparsed command strings.  This is the
    # single source of truth for the "does this string look destructive?"
    # heuristic; the engine delegates here instead of keeping its own copy.
    DANGEROUS_KEYWORDS = (
        "format",
        "fdisk",
        "rm -rf",
        "del /f /s /q",
        "rmdir /s",
        "shutdown",
        "reboot",
        "halt",
        "poweroff",
        "registry delete",
        "reg delete",
        "regedit",
        "net user",
        "net localgroup administrators",
        "sc delete",
        "taskkill /f",
        "chmod 777",
        "chown root",
        "dd if=",
        "mkfs",
        "parted",
    )

    def is_dangerous_command(self, command: str) -> bool:
        """Heuristic screen for destructive raw command strings."""
        if not command:
            return False
        command_lower = command.lower()
        return any(keyword in command_lower for keyword in self.DANGEROUS_KEYWORDS)

    def check_permission(self, parsed_command: dict[str, Any]) -> bool:
        """Check if a parsed command is allowed to execute"""
        try:
            # Input validation
            if not isinstance(parsed_command, dict):
                logger.error("parsed_command must be a dictionary")
                return False

            action = parsed_command.get("action")
            category = parsed_command.get("category")
            params = parsed_command.get("params", {})

            # Validate required fields
            if not action or not category:
                logger.error("action and category are required")
                return False

            # Check if operation is explicitly blocked
            operation_id = f"{category}:{action}"
            if operation_id in self.blocked_operations:
                logger.info(f"Operation blocked: {operation_id}")
                return False

            # Sandbox mode has been removed; perform normal permission checks

            # Get action category
            action_category = self._map_to_action_category(category, action)
            if not action_category:
                # Log unknown actions but allow them (with warning)
                logger.warning(f"Unknown action category for {category}:{action}")
                return True

            # Check permission rule
            rule = self.permission_rules.get(action_category)
            if not rule:
                return True

            # Check user permissions
            permission_key = action_category.value
            if not self.user_permissions.get(permission_key, True):
                logger.warning(f"Permission denied: {permission_key}")
                return False

            # Check path restrictions
            if not self._check_path_permissions(rule, params):
                logger.warning(f"Path restriction violation for {category}:{action}")
                return False

            # All checks passed
            return True

        except Exception as e:
            logger.error(f"Error checking permissions: {e}")
            import traceback

            traceback.print_exc()
            return False  # Deny on error

    def _is_safe_operation(self, category: str, action: str, params: dict[str, Any]) -> bool:
        """Check if operation is safe for sandbox mode"""
        safe_operations = {
            "filesystem": ["list", "get_info", "create_folder", "create_file"],
            "process": ["list", "get_info"],
            "gui": ["screenshot", "wait"],
            "system": ["get_info"],
            "network": ["http_get"],
            "project_generator": [
                "create_python_project",
                "create_c_project",
                "create_web_scraping_project",
                "create_data_analysis_project",
                "create_news_scraper",
                "create_virtualenv",
                "create_virtual_environment",
                "initialize_git_repo",
            ],
            "package_manager": [
                "install_packages",
                "install_package",
                "check_package_installed",
                "check_installed_packages",
                "list_installed_packages",
                "check_package_manager",
                "check_version",
                "get_package_info",
                "check_package",
            ],
            "devops": [
                "initialize_git_repo",
                "check_docker_installed",
                "check_docker_installation",
                "check_docker_running",
                "check_kubectl_installed",
                "check_kubectl",
            ],
            "data_generator": ["generate_sample_data"],
        }

        # Allow virtualenv creation and git initialization as sandbox-safe no-op operations
        safe_operations["project_generator"].extend(
            ["create_virtual_environment", "initialize_git_repo"]
        )

        # If explicitly listed as safe for the category, allow it
        if action in safe_operations.get(category, []):
            return True

        # Allow common "check", "list", "get", and "verify" actions across categories
        if action.startswith(("check_", "list_", "get_", "verify_")):
            return True

        # Allow explicit install simulation names
        return action in ("install_package", "install_packages")

    def _map_to_action_category(self, category: str, action: str) -> ActionCategory | None:
        """Map command category/action to ActionCategory"""
        mapping = {
            ("filesystem", "list"): ActionCategory.FILESYSTEM_READ,
            ("filesystem", "list_folders"): ActionCategory.FILESYSTEM_READ,
            ("filesystem", "list_files"): ActionCategory.FILESYSTEM_READ,
            ("filesystem", "get_info"): ActionCategory.FILESYSTEM_READ,
            ("filesystem", "create_folder"): ActionCategory.FILESYSTEM_WRITE,
            ("filesystem", "create_file"): ActionCategory.FILESYSTEM_WRITE,
            ("filesystem", "write_file"): ActionCategory.FILESYSTEM_WRITE,
            ("filesystem", "create_text_file"): ActionCategory.FILESYSTEM_WRITE,
            ("filesystem", "save_file"): ActionCategory.FILESYSTEM_WRITE,
            ("filesystem", "write_to_file"): ActionCategory.FILESYSTEM_WRITE,
            ("filesystem", "save_to_document"): ActionCategory.FILESYSTEM_WRITE,
            ("filesystem", "copy"): ActionCategory.FILESYSTEM_WRITE,
            ("filesystem", "copy_file"): ActionCategory.FILESYSTEM_WRITE,
            ("filesystem", "move"): ActionCategory.FILESYSTEM_WRITE,
            ("filesystem", "move_file"): ActionCategory.FILESYSTEM_WRITE,
            ("filesystem", "move_folder"): ActionCategory.FILESYSTEM_WRITE,
            ("filesystem", "rename"): ActionCategory.FILESYSTEM_WRITE,
            ("filesystem", "delete"): ActionCategory.FILESYSTEM_DELETE,
            ("filesystem", "delete_folder"): ActionCategory.FILESYSTEM_DELETE,
            ("filesystem", "delete_file"): ActionCategory.FILESYSTEM_DELETE,
            ("filesystem", "verify_file_creation"): ActionCategory.FILESYSTEM_READ,
            ("filesystem", "verify_folder_exists"): ActionCategory.FILESYSTEM_READ,
            ("filesystem", "verify_files_created"): ActionCategory.FILESYSTEM_READ,
            ("filesystem", "verify_deletion"): ActionCategory.FILESYSTEM_READ,
            ("filesystem", "create_bulk_folders"): ActionCategory.FILESYSTEM_WRITE,
            ("filesystem", "create_nested_folders"): ActionCategory.FILESYSTEM_WRITE,
            ("filesystem", "create_nested_files"): ActionCategory.FILESYSTEM_WRITE,
            ("filesystem", "resolve_path"): ActionCategory.FILESYSTEM_READ,
            ("filesystem", "create_shortcut"): ActionCategory.FILESYSTEM_WRITE,
            ("process", "start"): ActionCategory.PROCESS_START,
            ("process", "terminate"): ActionCategory.PROCESS_TERMINATE,
            ("process", "execute_installer"): ActionCategory.PROCESS_START,
            ("process", "launch_application"): ActionCategory.PROCESS_START,
            ("process", "run_installer"): ActionCategory.PROCESS_START,
            ("process", "execute_file"): ActionCategory.PROCESS_START,
            ("process", "execute_command"): ActionCategory.PROCESS_START,
            ("gui", "click"): ActionCategory.GUI_AUTOMATION,
            ("gui", "type"): ActionCategory.GUI_AUTOMATION,
            ("gui", "press_key"): ActionCategory.GUI_AUTOMATION,
            ("gui", "open_browser"): ActionCategory.GUI_AUTOMATION,
            ("gui", "perform_search"): ActionCategory.GUI_AUTOMATION,
            ("gui", "navigate_to_search_engine"): ActionCategory.GUI_AUTOMATION,
            ("gui", "wait_for_page_load"): ActionCategory.GUI_AUTOMATION,
            ("gui", "type_text"): ActionCategory.GUI_AUTOMATION,
            ("gui", "press_enter"): ActionCategory.GUI_AUTOMATION,
            ("gui", "navigate_to_url"): ActionCategory.GUI_AUTOMATION,
            ("gui", "create_shortcut"): ActionCategory.GUI_AUTOMATION,
            ("system", "set_volume"): ActionCategory.SYSTEM_SETTINGS,
            ("system", "get_info"): ActionCategory.FILESYSTEM_READ,
            ("system", "power_action"): ActionCategory.POWER_MANAGEMENT,
            ("system", "verify_installation"): ActionCategory.FILESYSTEM_READ,
            ("system", "check_installed_applications"): ActionCategory.FILESYSTEM_READ,
            ("network", "download"): ActionCategory.NETWORK_ACCESS,
            ("network", "http_get"): ActionCategory.NETWORK_ACCESS,
            ("network", "download_file"): ActionCategory.NETWORK_ACCESS,
            ("package_manager", "check_winget_availability"): ActionCategory.PROCESS_START,
            ("package_manager", "check_package_manager"): ActionCategory.PROCESS_START,
            ("package_manager", "search_package"): ActionCategory.NETWORK_ACCESS,
            ("package_manager", "install_package"): ActionCategory.PROCESS_START,
            ("package_manager", "execute_command"): ActionCategory.PROCESS_START,
            ("package_manager", "verify_installation"): ActionCategory.FILESYSTEM_READ,
            ("package_manager", "list_installed_packages"): ActionCategory.FILESYSTEM_READ,
            # Web automation actions
            ("web_automation", "open_browser"): ActionCategory.NETWORK_ACCESS,
            ("web_automation", "extract_article"): ActionCategory.NETWORK_ACCESS,
            ("web_automation", "scrape_website"): ActionCategory.NETWORK_ACCESS,
            ("web_automation", "search_and_extract"): ActionCategory.NETWORK_ACCESS,
            ("web_automation", "extract_text"): ActionCategory.NETWORK_ACCESS,
            ("web_automation", "extract_links"): ActionCategory.NETWORK_ACCESS,
            ("web_automation", "extract_images"): ActionCategory.NETWORK_ACCESS,
            ("web_automation", "scrape_table"): ActionCategory.NETWORK_ACCESS,
            # Universal automation actions
            ("universal_automation", "create_word_document"): ActionCategory.FILESYSTEM_WRITE,
            ("universal_automation", "create_powerpoint"): ActionCategory.FILESYSTEM_WRITE,
            ("universal_automation", "create_excel"): ActionCategory.FILESYSTEM_WRITE,
            ("universal_automation", "create_pdf"): ActionCategory.FILESYSTEM_WRITE,
            ("universal_automation", "create_folder"): ActionCategory.FILESYSTEM_WRITE,
            ("universal_automation", "save_to_document"): ActionCategory.FILESYSTEM_WRITE,
            ("universal_automation", "install_software"): ActionCategory.PROCESS_START,
            ("universal_automation", "uninstall_software"): ActionCategory.PROCESS_START,
            ("universal_automation", "install_package"): ActionCategory.PROCESS_START,
            ("universal_automation", "update_system"): ActionCategory.PROCESS_START,
            # Project generator actions
            ("project_generator", "create_python_project"): ActionCategory.FILESYSTEM_WRITE,
            ("project_generator", "create_c_project"): ActionCategory.FILESYSTEM_WRITE,
            ("project_generator", "create_web_scraping_project"): ActionCategory.FILESYSTEM_WRITE,
            ("project_generator", "create_data_analysis_project"): ActionCategory.FILESYSTEM_WRITE,
            ("project_generator", "create_news_scraper"): ActionCategory.FILESYSTEM_WRITE,
            ("project_generator", "create_virtual_environment"): ActionCategory.PROCESS_START,
            ("project_generator", "initialize_git_repo"): ActionCategory.PROCESS_START,
            # Folder operations
            ("folder_operations", "create_folder"): ActionCategory.FILESYSTEM_WRITE,
            ("folder_operations", "create_bulk_folders"): ActionCategory.FILESYSTEM_WRITE,
            ("folder_operations", "create_nested_folders"): ActionCategory.FILESYSTEM_WRITE,
            ("folder_operations", "move_folder"): ActionCategory.FILESYSTEM_WRITE,
            ("folder_operations", "delete_folder"): ActionCategory.FILESYSTEM_DELETE,
            # DevOps generator actions
            ("devops_generator", "initialize_git_repo"): ActionCategory.PROCESS_START,
            ("devops_generator", "create_pipeline"): ActionCategory.FILESYSTEM_WRITE,
            ("devops_generator", "create_dockerfile"): ActionCategory.FILESYSTEM_WRITE,
            ("devops_generator", "check_docker_installed"): ActionCategory.FILESYSTEM_READ,
        }

        return mapping.get((category, action))

    def _check_path_permissions(self, rule: PermissionRule, params: dict[str, Any]) -> bool:
        """Check if paths in parameters are allowed"""
        # Extract paths from parameters
        paths_to_check = []

        for key in ["path", "source", "destination", "location", "name"]:
            if key in params and params[key]:
                paths_to_check.append(str(params[key]))

        # Check each path
        for path in paths_to_check:
            # Normalize path
            normalized_path = os.path.normpath(os.path.abspath(path))

            # Check blocked paths
            if rule.blocked_paths:
                for blocked_path in rule.blocked_paths:
                    if normalized_path.startswith(os.path.normpath(blocked_path)):
                        return False

            # Check allowed paths (if specified)
            if rule.allowed_paths:
                allowed = False
                for allowed_path in rule.allowed_paths:
                    if normalized_path.startswith(os.path.normpath(allowed_path)):
                        allowed = True
                        break
                if not allowed:
                    return False

        return True

    def request_permission(self, action_category: ActionCategory, description: str = "") -> bool:
        """Request permission from user for a specific action category"""
        rule = self.permission_rules.get(action_category)
        if not rule:
            return True

        if rule.requires_confirmation or not self.user_permissions.get(
            action_category.value, False
        ):
            # In a real implementation, this would show a GUI dialog or prompt
            logger.info("\nPermission Request:")
            logger.info(f"Action: {rule.description}")
            logger.info(f"Risk Level: {rule.permission_level.value}")
            if description:
                logger.info(f"Details: {description}")

            # For now, automatically grant moderate and below, deny high and critical
            if rule.permission_level in [PermissionLevel.SAFE, PermissionLevel.MODERATE]:
                self.user_permissions[action_category.value] = True
                self._save_config()
                return True
            else:
                return False

        return True

    def block_operation(self, category: str, action: str):
        """Block a specific operation"""
        operation_id = f"{category}:{action}"
        self.blocked_operations.add(operation_id)
        self._save_config()

    def unblock_operation(self, category: str, action: str):
        """Unblock a specific operation"""
        operation_id = f"{category}:{action}"
        self.blocked_operations.discard(operation_id)
        self._save_config()

    def enable_sandbox_mode(self):
        """Sandbox mode removed - no-op"""
        logger.info("Sandbox mode support removed; enable_sandbox_mode() is a no-op")

    def disable_sandbox_mode(self):
        """Sandbox mode removed - no-op"""
        logger.info("Sandbox mode support removed; disable_sandbox_mode() is a no-op")

    def get_permission_summary(self) -> dict[str, Any]:
        """Get summary of current permissions"""
        return {
            "sandbox_mode": self.sandbox_mode,
            "user_permissions": self.user_permissions.copy(),
            "blocked_operations": list(self.blocked_operations),
            "permission_rules": {
                category.value: {
                    "level": rule.permission_level.value,
                    "requires_confirmation": rule.requires_confirmation,
                    "description": rule.description,
                }
                for category, rule in self.permission_rules.items()
            },
        }

    def reset_permissions(self):
        """Reset all permissions to defaults"""
        self.user_permissions = self._load_user_permissions()
        self.blocked_operations.clear()
        self.sandbox_mode = False
        self._save_config()
