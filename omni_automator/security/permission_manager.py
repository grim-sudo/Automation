"""
Permission and security management for automation operations
"""

import os
import json
import hashlib
from typing import Dict, Any, List, Optional, Set
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class PermissionLevel(Enum):
    """Permission levels for different operations"""
    SAFE = "safe"           # Safe operations (read-only, non-destructive)
    MODERATE = "moderate"   # Moderate risk operations (create files, start processes)
    HIGH = "high"          # High risk operations (delete, system changes)
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
    allowed_paths: Optional[List[str]] = None
    blocked_paths: Optional[List[str]] = None
    requires_confirmation: bool = False
    description: str = ""


class PermissionManager:
    """Manages permissions and security for automation operations"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._get_default_config_path()
        self.sandbox_mode = False
        self.permission_rules = self._load_default_rules()
        self.user_permissions = self._load_user_permissions()
        self.blocked_operations: Set[str] = set()
        
        # Load custom configuration if exists
        self._load_config()
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path"""
        config_dir = os.path.expanduser("~/.omni_automator")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "permissions.json")
    
    def _load_default_rules(self) -> Dict[ActionCategory, PermissionRule]:
        """Load default permission rules"""
        self.action_permissions = {
            # Safe operations
            'get_system_info': PermissionLevel.SAFE,
            'list_directory': PermissionLevel.SAFE,
            'take_screenshot': PermissionLevel.SAFE,
            'get_capabilities': PermissionLevel.SAFE,
            
            # Project generator actions
            'create_python_project': PermissionLevel.MODERATE,
            'create_c_project': PermissionLevel.MODERATE,
            'create_web_scraping_project': PermissionLevel.MODERATE,
            'create_data_analysis_project': PermissionLevel.MODERATE,
            'create_news_scraper': PermissionLevel.MODERATE,
            'install_packages': PermissionLevel.MODERATE,
            'generate_sample_data': PermissionLevel.SAFE,
        }
        
        return {
            ActionCategory.FILESYSTEM_READ: PermissionRule(
                category=ActionCategory.FILESYSTEM_READ,
                permission_level=PermissionLevel.SAFE,
                description="Read files and directories"
            ),
            ActionCategory.FILESYSTEM_WRITE: PermissionRule(
                category=ActionCategory.FILESYSTEM_WRITE,
                permission_level=PermissionLevel.MODERATE,
                blocked_paths=["/system", "/windows", "C:\\Windows", "/etc"],
                description="Create and modify files"
            ),
            ActionCategory.FILESYSTEM_DELETE: PermissionRule(
                category=ActionCategory.FILESYSTEM_DELETE,
                permission_level=PermissionLevel.HIGH,
                blocked_paths=["/system", "/windows", "C:\\Windows", "/etc", "/usr"],
                requires_confirmation=True,
                description="Delete files and directories"
            ),
            ActionCategory.PROCESS_START: PermissionRule(
                category=ActionCategory.PROCESS_START,
                permission_level=PermissionLevel.MODERATE,
                description="Start new processes"
            ),
            ActionCategory.PROCESS_TERMINATE: PermissionRule(
                category=ActionCategory.PROCESS_TERMINATE,
                permission_level=PermissionLevel.HIGH,
                requires_confirmation=True,
                description="Terminate running processes"
            ),
            ActionCategory.GUI_AUTOMATION: PermissionRule(
                category=ActionCategory.GUI_AUTOMATION,
                permission_level=PermissionLevel.MODERATE,
                description="GUI automation (clicks, typing)"
            ),
            ActionCategory.SYSTEM_SETTINGS: PermissionRule(
                category=ActionCategory.SYSTEM_SETTINGS,
                permission_level=PermissionLevel.HIGH,
                requires_confirmation=True,
                description="Modify system settings"
            ),
            ActionCategory.NETWORK_ACCESS: PermissionRule(
                category=ActionCategory.NETWORK_ACCESS,
                permission_level=PermissionLevel.MODERATE,
                description="Network operations"
            ),
            ActionCategory.POWER_MANAGEMENT: PermissionRule(
                category=ActionCategory.POWER_MANAGEMENT,
                permission_level=PermissionLevel.CRITICAL,
                requires_confirmation=True,
                description="Power operations (shutdown, restart)"
            )
        }
    
    def _load_user_permissions(self) -> Dict[str, bool]:
        """Load user-granted permissions"""
        return {
            'filesystem_write': True,
            'filesystem_delete': True,
            'process_terminate': False,
            'system_settings': False,
            'power_management': False
        }
    
    def _load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.user_permissions.update(config.get('permissions', {}))
                    self.blocked_operations.update(config.get('blocked_operations', []))
        except Exception as e:
            print(f"Warning: Could not load permission config: {e}")
    
    def _save_config(self):
        """Save configuration to file"""
        try:
            config = {
                'permissions': self.user_permissions,
                'blocked_operations': list(self.blocked_operations),
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save permission config: {e}")
    
    def check_permission(self, parsed_command: Dict[str, Any]) -> bool:
        """Check if a parsed command is allowed to execute"""
        try:
            # Input validation
            if not isinstance(parsed_command, dict):
                print("Error: parsed_command must be a dictionary")
                return False
            
            action = parsed_command.get('action')
            category = parsed_command.get('category')
            params = parsed_command.get('params', {})
            
            # Validate required fields
            if not action or not category:
                print("Error: action and category are required")
                return False
            
            # Check if operation is explicitly blocked
            operation_id = f"{category}:{action}"
            if operation_id in self.blocked_operations:
                print(f"Operation blocked: {operation_id}")
                return False
            
            # In sandbox mode, only allow safe operations
            if self.sandbox_mode:
                is_safe = self._is_safe_operation(category, action, params)
                if not is_safe:
                    print(f"Operation not allowed in sandbox mode: {category}:{action}")
                return is_safe
            
            # Get action category
            action_category = self._map_to_action_category(category, action)
            if not action_category:
                # Log unknown actions but allow them (with warning)
                print(f"Warning: Unknown action category for {category}:{action}")
                return True
            
            # Check permission rule
            rule = self.permission_rules.get(action_category)
            if not rule:
                return True
            
            # Check user permissions
            permission_key = action_category.value
            if not self.user_permissions.get(permission_key, True):
                print(f"Permission denied: {permission_key}")
                return False
            
            # Check path restrictions
            if not self._check_path_permissions(rule, params):
                print(f"Path restriction violation for {category}:{action}")
                return False
            
            # All checks passed
            return True
            
        except Exception as e:
            print(f"Error checking permissions: {e}")
            import traceback
            traceback.print_exc()
            return False  # Deny on error
    
    def _is_safe_operation(self, category: str, action: str, params: Dict[str, Any]) -> bool:
        """Check if operation is safe for sandbox mode"""
        safe_operations = {
            'filesystem': ['list', 'get_info', 'create_folder', 'create_file'],
            'process': ['list', 'get_info'],
            'gui': ['screenshot', 'wait'],
            'system': ['get_info'],
            'network': ['http_get'],
            'project_generator': ['create_python_project', 'create_c_project', 'create_web_scraping_project', 'create_data_analysis_project', 'create_news_scraper'],
            'package_manager': ['install_packages'],
            'data_generator': ['generate_sample_data']
        }
        
        return action in safe_operations.get(category, [])
    
    def _map_to_action_category(self, category: str, action: str) -> Optional[ActionCategory]:
        """Map command category/action to ActionCategory"""
        mapping = {
            ('filesystem', 'list'): ActionCategory.FILESYSTEM_READ,
            ('filesystem', 'list_folders'): ActionCategory.FILESYSTEM_READ,
            ('filesystem', 'list_files'): ActionCategory.FILESYSTEM_READ,
            ('filesystem', 'get_info'): ActionCategory.FILESYSTEM_READ,
            ('filesystem', 'create_folder'): ActionCategory.FILESYSTEM_WRITE,
            ('filesystem', 'create_file'): ActionCategory.FILESYSTEM_WRITE,
            ('filesystem', 'copy'): ActionCategory.FILESYSTEM_WRITE,
            ('filesystem', 'copy_file'): ActionCategory.FILESYSTEM_WRITE,
            ('filesystem', 'move'): ActionCategory.FILESYSTEM_WRITE,
            ('filesystem', 'move_file'): ActionCategory.FILESYSTEM_WRITE,
            ('filesystem', 'delete'): ActionCategory.FILESYSTEM_DELETE,
            ('filesystem', 'delete_folder'): ActionCategory.FILESYSTEM_DELETE,
            ('filesystem', 'delete_file'): ActionCategory.FILESYSTEM_DELETE,
            ('filesystem', 'verify_file_creation'): ActionCategory.FILESYSTEM_READ,
            ('filesystem', 'verify_folder_exists'): ActionCategory.FILESYSTEM_READ,
            ('filesystem', 'verify_files_created'): ActionCategory.FILESYSTEM_READ,
            ('filesystem', 'verify_deletion'): ActionCategory.FILESYSTEM_READ,
            ('filesystem', 'create_bulk_folders'): ActionCategory.FILESYSTEM_WRITE,
            ('filesystem', 'create_nested_folders'): ActionCategory.FILESYSTEM_WRITE,
            ('process', 'start'): ActionCategory.PROCESS_START,
            ('process', 'terminate'): ActionCategory.PROCESS_TERMINATE,
            ('gui', 'click'): ActionCategory.GUI_AUTOMATION,
            ('gui', 'type'): ActionCategory.GUI_AUTOMATION,
            ('gui', 'press_key'): ActionCategory.GUI_AUTOMATION,
            ('system', 'set_volume'): ActionCategory.SYSTEM_SETTINGS,
            ('system', 'power_action'): ActionCategory.POWER_MANAGEMENT,
            ('network', 'download'): ActionCategory.NETWORK_ACCESS,
            ('network', 'http_get'): ActionCategory.NETWORK_ACCESS,
        }
        
        return mapping.get((category, action))
    
    def _check_path_permissions(self, rule: PermissionRule, params: Dict[str, Any]) -> bool:
        """Check if paths in parameters are allowed"""
        # Extract paths from parameters
        paths_to_check = []
        
        for key in ['path', 'source', 'destination', 'location', 'name']:
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
        
        if rule.requires_confirmation or not self.user_permissions.get(action_category.value, False):
            # In a real implementation, this would show a GUI dialog or prompt
            print(f"\nPermission Request:")
            print(f"Action: {rule.description}")
            print(f"Risk Level: {rule.permission_level.value}")
            if description:
                print(f"Details: {description}")
            
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
        """Enable sandbox mode (only safe operations allowed)"""
        self.sandbox_mode = True
    
    def disable_sandbox_mode(self):
        """Disable sandbox mode"""
        self.sandbox_mode = False
    
    def get_permission_summary(self) -> Dict[str, Any]:
        """Get summary of current permissions"""
        return {
            'sandbox_mode': self.sandbox_mode,
            'user_permissions': self.user_permissions.copy(),
            'blocked_operations': list(self.blocked_operations),
            'permission_rules': {
                category.value: {
                    'level': rule.permission_level.value,
                    'requires_confirmation': rule.requires_confirmation,
                    'description': rule.description
                }
                for category, rule in self.permission_rules.items()
            }
        }
    
    def reset_permissions(self):
        """Reset all permissions to defaults"""
        self.user_permissions = self._load_user_permissions()
        self.blocked_operations.clear()
        self.sandbox_mode = False
        self._save_config()
