#!/usr/bin/env python3
"""
Enhanced Windows OS Adapter with deep system integration
"""

import os
import sys
import subprocess
import winreg
import ctypes
from ctypes import wintypes
import psutil
import win32api
import win32con
import win32gui
import win32process
import win32service
import win32serviceutil
from typing import Dict, List, Any, Optional
import json
import time
from pathlib import Path

from .base_adapter import BaseOSAdapter
from ..utils.logger import get_logger

class EnhancedWindowsAdapter(BaseOSAdapter):
    """Enhanced Windows adapter with deep OS integration"""
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("EnhancedWindowsAdapter")
        self.is_admin = self._check_admin_privileges()
        
    def _check_admin_privileges(self) -> bool:
        """Check if running with administrator privileges"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def _run_as_admin(self, command: str) -> Dict[str, Any]:
        """Run command with administrator privileges"""
        if self.is_admin:
            return self._execute_command(command)
        
        try:
            # Use PowerShell to elevate
            ps_command = f'Start-Process powershell -ArgumentList "-Command {command}" -Verb RunAs -Wait'
            result = subprocess.run(['powershell', '-Command', ps_command], 
                                  capture_output=True, text=True, timeout=30)
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr,
                'return_code': result.returncode
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to run as admin: {e}",
                'return_code': -1
            }
    
    # Enhanced System Operations
    def manage_system_service(self, service_name: str, action: str) -> Dict[str, Any]:
        """Manage Windows services (start, stop, restart, install, uninstall)"""
        try:
            if action == 'start':
                win32serviceutil.StartService(service_name)
                return {'success': True, 'message': f'Service {service_name} started'}
            
            elif action == 'stop':
                win32serviceutil.StopService(service_name)
                return {'success': True, 'message': f'Service {service_name} stopped'}
            
            elif action == 'restart':
                win32serviceutil.RestartService(service_name)
                return {'success': True, 'message': f'Service {service_name} restarted'}
            
            elif action == 'status':
                status = win32serviceutil.QueryServiceStatus(service_name)
                return {'success': True, 'status': status}
            
            else:
                return {'success': False, 'error': f'Unknown action: {action}'}
                
        except Exception as e:
            return {'success': False, 'error': f'Service operation failed: {e}'}
    
    def manage_registry(self, operation: str, key_path: str, value_name: str = None, 
                       value_data: Any = None, value_type: int = winreg.REG_SZ) -> Dict[str, Any]:
        """Advanced registry operations"""
        try:
            # Parse registry path
            parts = key_path.split('\\', 1)
            root_key_name = parts[0]
            subkey_path = parts[1] if len(parts) > 1 else ""
            
            # Map root key names to constants
            root_keys = {
                'HKEY_CURRENT_USER': winreg.HKEY_CURRENT_USER,
                'HKEY_LOCAL_MACHINE': winreg.HKEY_LOCAL_MACHINE,
                'HKEY_CLASSES_ROOT': winreg.HKEY_CLASSES_ROOT,
                'HKEY_USERS': winreg.HKEY_USERS,
                'HKEY_CURRENT_CONFIG': winreg.HKEY_CURRENT_CONFIG,
                'HKCU': winreg.HKEY_CURRENT_USER,
                'HKLM': winreg.HKEY_LOCAL_MACHINE,
            }
            
            root_key = root_keys.get(root_key_name)
            if not root_key:
                return {'success': False, 'error': f'Invalid root key: {root_key_name}'}
            
            if operation == 'read':
                with winreg.OpenKey(root_key, subkey_path) as key:
                    if value_name:
                        value, reg_type = winreg.QueryValueEx(key, value_name)
                        return {'success': True, 'value': value, 'type': reg_type}
                    else:
                        # List all values
                        values = {}
                        i = 0
                        try:
                            while True:
                                name, value, reg_type = winreg.EnumValue(key, i)
                                values[name] = {'value': value, 'type': reg_type}
                                i += 1
                        except WindowsError:
                            pass
                        return {'success': True, 'values': values}
            
            elif operation == 'write':
                with winreg.CreateKey(root_key, subkey_path) as key:
                    winreg.SetValueEx(key, value_name, 0, value_type, value_data)
                    return {'success': True, 'message': f'Registry value set: {value_name}'}
            
            elif operation == 'delete':
                if value_name:
                    with winreg.OpenKey(root_key, subkey_path, 0, winreg.KEY_SET_VALUE) as key:
                        winreg.DeleteValue(key, value_name)
                        return {'success': True, 'message': f'Registry value deleted: {value_name}'}
                else:
                    winreg.DeleteKey(root_key, subkey_path)
                    return {'success': True, 'message': f'Registry key deleted: {subkey_path}'}
            
        except Exception as e:
            return {'success': False, 'error': f'Registry operation failed: {e}'}
    
    def manage_scheduled_tasks(self, operation: str, task_name: str, **kwargs) -> Dict[str, Any]:
        """Manage Windows scheduled tasks"""
        try:
            if operation == 'create':
                command = kwargs.get('command', '')
                schedule = kwargs.get('schedule', 'DAILY')
                time_str = kwargs.get('time', '09:00')
                
                cmd = f'schtasks /create /tn "{task_name}" /tr "{command}" /sc {schedule} /st {time_str} /f'
                result = self._run_as_admin(cmd)
                return result
            
            elif operation == 'delete':
                cmd = f'schtasks /delete /tn "{task_name}" /f'
                result = self._run_as_admin(cmd)
                return result
            
            elif operation == 'run':
                cmd = f'schtasks /run /tn "{task_name}"'
                result = self._run_as_admin(cmd)
                return result
            
            elif operation == 'list':
                cmd = 'schtasks /query /fo csv'
                result = self._execute_command(cmd)
                return result
            
        except Exception as e:
            return {'success': False, 'error': f'Task scheduler operation failed: {e}'}
    
    def manage_firewall(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Manage Windows Firewall"""
        try:
            if operation == 'add_rule':
                rule_name = kwargs.get('rule_name', 'OmniAutomator Rule')
                program = kwargs.get('program', '')
                port = kwargs.get('port', '')
                protocol = kwargs.get('protocol', 'TCP')
                direction = kwargs.get('direction', 'in')
                action = kwargs.get('action', 'allow')
                
                if program:
                    cmd = f'netsh advfirewall firewall add rule name="{rule_name}" dir={direction} action={action} program="{program}"'
                elif port:
                    cmd = f'netsh advfirewall firewall add rule name="{rule_name}" dir={direction} action={action} protocol={protocol} localport={port}'
                else:
                    return {'success': False, 'error': 'Must specify either program or port'}
                
                return self._run_as_admin(cmd)
            
            elif operation == 'delete_rule':
                rule_name = kwargs.get('rule_name')
                cmd = f'netsh advfirewall firewall delete rule name="{rule_name}"'
                return self._run_as_admin(cmd)
            
            elif operation == 'enable':
                cmd = 'netsh advfirewall set allprofiles state on'
                return self._run_as_admin(cmd)
            
            elif operation == 'disable':
                cmd = 'netsh advfirewall set allprofiles state off'
                return self._run_as_admin(cmd)
            
        except Exception as e:
            return {'success': False, 'error': f'Firewall operation failed: {e}'}
    
    def manage_user_accounts(self, operation: str, username: str, **kwargs) -> Dict[str, Any]:
        """Manage Windows user accounts"""
        try:
            if operation == 'create':
                password = kwargs.get('password', 'TempPass123!')
                fullname = kwargs.get('fullname', username)
                
                cmd = f'net user {username} {password} /add /fullname:"{fullname}"'
                result = self._run_as_admin(cmd)
                
                # Add to users group
                if result.get('success'):
                    group_cmd = f'net localgroup Users {username} /add'
                    self._run_as_admin(group_cmd)
                
                return result
            
            elif operation == 'delete':
                cmd = f'net user {username} /delete'
                return self._run_as_admin(cmd)
            
            elif operation == 'enable':
                cmd = f'net user {username} /active:yes'
                return self._run_as_admin(cmd)
            
            elif operation == 'disable':
                cmd = f'net user {username} /active:no'
                return self._run_as_admin(cmd)
            
            elif operation == 'change_password':
                new_password = kwargs.get('new_password')
                cmd = f'net user {username} {new_password}'
                return self._run_as_admin(cmd)
            
        except Exception as e:
            return {'success': False, 'error': f'User account operation failed: {e}'}
    
    def manage_network_settings(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Manage network settings"""
        try:
            if operation == 'set_ip':
                interface = kwargs.get('interface', 'Ethernet')
                ip_address = kwargs.get('ip_address')
                subnet_mask = kwargs.get('subnet_mask', '255.255.255.0')
                gateway = kwargs.get('gateway')
                
                cmd = f'netsh interface ip set address "{interface}" static {ip_address} {subnet_mask} {gateway}'
                return self._run_as_admin(cmd)
            
            elif operation == 'set_dns':
                interface = kwargs.get('interface', 'Ethernet')
                primary_dns = kwargs.get('primary_dns')
                secondary_dns = kwargs.get('secondary_dns')
                
                cmd = f'netsh interface ip set dns "{interface}" static {primary_dns}'
                result = self._run_as_admin(cmd)
                
                if secondary_dns and result.get('success'):
                    cmd2 = f'netsh interface ip add dns "{interface}" {secondary_dns} index=2'
                    self._run_as_admin(cmd2)
                
                return result
            
            elif operation == 'enable_dhcp':
                interface = kwargs.get('interface', 'Ethernet')
                cmd = f'netsh interface ip set address "{interface}" dhcp'
                return self._run_as_admin(cmd)
            
        except Exception as e:
            return {'success': False, 'error': f'Network operation failed: {e}'}
    
    def get_system_performance(self) -> Dict[str, Any]:
        """Get detailed system performance metrics"""
        try:
            # CPU information
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory information
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk information
            disk_usage = {}
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage[partition.device] = {
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent': (usage.used / usage.total) * 100
                    }
                except:
                    continue
            
            # Network information
            network_io = psutil.net_io_counters()
            
            # Process information
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except:
                    continue
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            
            return {
                'success': True,
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                    'frequency': cpu_freq._asdict() if cpu_freq else None
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'used': memory.used,
                    'percent': memory.percent
                },
                'swap': {
                    'total': swap.total,
                    'used': swap.used,
                    'free': swap.free,
                    'percent': swap.percent
                },
                'disk': disk_usage,
                'network': {
                    'bytes_sent': network_io.bytes_sent,
                    'bytes_recv': network_io.bytes_recv,
                    'packets_sent': network_io.packets_sent,
                    'packets_recv': network_io.packets_recv
                },
                'top_processes': processes[:10]
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Performance monitoring failed: {e}'}
    
    def manage_system_startup(self, operation: str, program_name: str, program_path: str = None) -> Dict[str, Any]:
        """Manage system startup programs"""
        try:
            startup_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
            
            if operation == 'add':
                return self.manage_registry('write', f'HKLM\\{startup_key}', program_name, program_path)
            
            elif operation == 'remove':
                return self.manage_registry('delete', f'HKLM\\{startup_key}', program_name)
            
            elif operation == 'list':
                return self.manage_registry('read', f'HKLM\\{startup_key}')
            
        except Exception as e:
            return {'success': False, 'error': f'Startup management failed: {e}'}
    
    def manage_environment_variables(self, operation: str, var_name: str, var_value: str = None, scope: str = 'user') -> Dict[str, Any]:
        """Manage environment variables"""
        try:
            if scope == 'system':
                reg_path = r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
            else:
                reg_path = r"HKCU\Environment"
            
            if operation == 'set':
                result = self.manage_registry('write', reg_path, var_name, var_value)
                if result.get('success'):
                    # Broadcast change
                    win32gui.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')
                return result
            
            elif operation == 'get':
                return self.manage_registry('read', reg_path, var_name)
            
            elif operation == 'delete':
                result = self.manage_registry('delete', reg_path, var_name)
                if result.get('success'):
                    win32gui.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')
                return result
            
        except Exception as e:
            return {'success': False, 'error': f'Environment variable operation failed: {e}'}
    
    def create_system_restore_point(self, description: str = "OmniAutomator Restore Point") -> Dict[str, Any]:
        """Create a system restore point"""
        try:
            cmd = f'powershell "Checkpoint-Computer -Description \\"{description}\\" -RestorePointType MODIFY_SETTINGS"'
            return self._run_as_admin(cmd)
        except Exception as e:
            return {'success': False, 'error': f'System restore point creation failed: {e}'}
    
    def get_installed_software(self) -> Dict[str, Any]:
        """Get list of installed software"""
        try:
            software_list = []
            
            # Check both 32-bit and 64-bit registry locations
            registry_paths = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
            ]
            
            for reg_path in registry_paths:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                        i = 0
                        while True:
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, subkey_name) as subkey:
                                    try:
                                        display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                        try:
                                            display_version = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                                        except:
                                            display_version = "Unknown"
                                        
                                        try:
                                            publisher = winreg.QueryValueEx(subkey, "Publisher")[0]
                                        except:
                                            publisher = "Unknown"
                                        
                                        software_list.append({
                                            'name': display_name,
                                            'version': display_version,
                                            'publisher': publisher
                                        })
                                    except:
                                        pass
                                i += 1
                            except WindowsError:
                                break
                except:
                    continue
            
            return {'success': True, 'software': software_list}
            
        except Exception as e:
            return {'success': False, 'error': f'Software enumeration failed: {e}'}
    
    def execute_advanced_operation(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute advanced OS-level operations"""
        
        operation_map = {
            'manage_service': lambda: self.manage_system_service(
                params.get('service_name'), params.get('action')
            ),
            'manage_registry': lambda: self.manage_registry(
                params.get('operation'), params.get('key_path'),
                params.get('value_name'), params.get('value_data'),
                params.get('value_type', winreg.REG_SZ)
            ),
            'manage_scheduled_task': lambda: self.manage_scheduled_tasks(
                params.get('operation'), params.get('task_name'), **params
            ),
            'manage_firewall': lambda: self.manage_firewall(
                params.get('operation'), **params
            ),
            'manage_user': lambda: self.manage_user_accounts(
                params.get('operation'), params.get('username'), **params
            ),
            'manage_network': lambda: self.manage_network_settings(
                params.get('operation'), **params
            ),
            'get_performance': lambda: self.get_system_performance(),
            'manage_startup': lambda: self.manage_system_startup(
                params.get('operation'), params.get('program_name'),
                params.get('program_path')
            ),
            'manage_environment': lambda: self.manage_environment_variables(
                params.get('operation'), params.get('var_name'),
                params.get('var_value'), params.get('scope', 'user')
            ),
            'create_restore_point': lambda: self.create_system_restore_point(
                params.get('description', 'OmniAutomator Restore Point')
            ),
            'get_installed_software': lambda: self.get_installed_software()
        }
        
        if operation in operation_map:
            return operation_map[operation]()
        else:
            return {'success': False, 'error': f'Unknown advanced operation: {operation}'}
