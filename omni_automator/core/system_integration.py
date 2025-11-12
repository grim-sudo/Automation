#!/usr/bin/env python3
"""
Deep System Integration for OmniAutomator
"""

import os
import sys
import winreg
import subprocess
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..utils.logger import get_logger

class SystemIntegration:
    """Deep system integration capabilities"""
    
    def __init__(self):
        self.logger = get_logger("SystemIntegration")
        self.app_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.is_admin = self._check_admin_privileges()
    
    def _check_admin_privileges(self) -> bool:
        """Check if running with administrator privileges"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def install_system_integration(self) -> Dict[str, Any]:
        """Install system-wide integration"""
        results = {}
        
        try:
            # 1. Add to system PATH
            results['path'] = self._add_to_system_path()
            
            # 2. Create desktop shortcut
            results['desktop_shortcut'] = self._create_desktop_shortcut()
            
            # 3. Add to start menu
            results['start_menu'] = self._add_to_start_menu()
            
            # 4. Register file associations
            results['file_associations'] = self._register_file_associations()
            
            # 5. Add context menu integration
            results['context_menu'] = self._add_context_menu_integration()
            
            # 6. Create Windows service (optional)
            results['service'] = self._create_windows_service()
            
            # 7. Add to Windows features
            results['windows_features'] = self._add_to_windows_features()
            
            return {
                'success': True,
                'results': results,
                'message': 'System integration completed successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'System integration failed: {e}',
                'results': results
            }
    
    def _add_to_system_path(self) -> Dict[str, Any]:
        """Add OmniAutomator to system PATH"""
        try:
            # Get current PATH
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                               r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                               0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
                
                current_path, _ = winreg.QueryValueEx(key, "Path")
                
                # Check if already in PATH
                if self.app_path not in current_path:
                    new_path = f"{current_path};{self.app_path}"
                    winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                    
                    # Broadcast change
                    import win32gui
                    import win32con
                    win32gui.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')
                    
                    return {'success': True, 'message': 'Added to system PATH'}
                else:
                    return {'success': True, 'message': 'Already in system PATH'}
                    
        except Exception as e:
            return {'success': False, 'error': f'Failed to add to PATH: {e}'}
    
    def _create_desktop_shortcut(self) -> Dict[str, Any]:
        """Create desktop shortcut"""
        try:
            import win32com.client
            
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            shortcut_path = os.path.join(desktop, "OmniAutomator.lnk")
            
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = sys.executable
            shortcut.Arguments = f'"{os.path.join(self.app_path, "launch_gui.py")}"'
            shortcut.WorkingDirectory = self.app_path
            shortcut.IconLocation = f"{self.app_path}\\icon.ico"
            shortcut.Description = "OmniAutomator - Universal OS Automation"
            shortcut.save()
            
            return {'success': True, 'message': 'Desktop shortcut created'}
            
        except Exception as e:
            return {'success': False, 'error': f'Failed to create desktop shortcut: {e}'}
    
    def _add_to_start_menu(self) -> Dict[str, Any]:
        """Add to Windows Start Menu"""
        try:
            start_menu = os.path.join(os.getenv('APPDATA'), 
                                     "Microsoft", "Windows", "Start Menu", "Programs")
            
            omni_folder = os.path.join(start_menu, "OmniAutomator")
            os.makedirs(omni_folder, exist_ok=True)
            
            # Create shortcuts
            shortcuts = [
                ("OmniAutomator GUI", "launch_gui.py", "Launch the graphical interface"),
                ("OmniAutomator CLI", "main.py", "Launch the command line interface"),
                ("OmniAutomator Interactive", "main.py interactive", "Launch interactive mode")
            ]
            
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            
            for name, script, description in shortcuts:
                shortcut_path = os.path.join(omni_folder, f"{name}.lnk")
                shortcut = shell.CreateShortCut(shortcut_path)
                shortcut.Targetpath = sys.executable
                shortcut.Arguments = f'"{os.path.join(self.app_path, script)}"'
                shortcut.WorkingDirectory = self.app_path
                shortcut.Description = description
                shortcut.save()
            
            return {'success': True, 'message': 'Added to Start Menu'}
            
        except Exception as e:
            return {'success': False, 'error': f'Failed to add to Start Menu: {e}'}
    
    def _register_file_associations(self) -> Dict[str, Any]:
        """Register file associations"""
        try:
            # Register .omni files
            associations = [
                ('.omni', 'OmniAutomator.Script', 'OmniAutomator Script File'),
                ('.oauto', 'OmniAutomator.Batch', 'OmniAutomator Batch File')
            ]
            
            for ext, prog_id, description in associations:
                # Register extension
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, ext) as key:
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, prog_id)
                
                # Register program ID
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, prog_id) as key:
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, description)
                
                # Register shell command
                shell_key = f"{prog_id}\\shell\\open\\command"
                with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, shell_key) as key:
                    command = f'"{sys.executable}" "{os.path.join(self.app_path, "main.py")}" batch "%1"'
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
            
            return {'success': True, 'message': 'File associations registered'}
            
        except Exception as e:
            return {'success': False, 'error': f'Failed to register file associations: {e}'}
    
    def _add_context_menu_integration(self) -> Dict[str, Any]:
        """Add right-click context menu integration"""
        try:
            # Add to folder context menu
            folder_key = r"Directory\\Background\\shell\\OmniAutomator"
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, folder_key) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Open OmniAutomator Here")
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f"{self.app_path}\\icon.ico")
            
            command_key = f"{folder_key}\\command"
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, command_key) as key:
                command = f'"{sys.executable}" "{os.path.join(self.app_path, "main.py")}" interactive'
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
            
            # Add to file context menu
            file_key = r"*\\shell\\OmniAutomator"
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, file_key) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Automate with OmniAutomator")
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f"{self.app_path}\\icon.ico")
            
            file_command_key = f"{file_key}\\command"
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, file_command_key) as key:
                command = f'"{sys.executable}" "{os.path.join(self.app_path, "main.py")}" execute "process file \\"%1\\""'
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
            
            return {'success': True, 'message': 'Context menu integration added'}
            
        except Exception as e:
            return {'success': False, 'error': f'Failed to add context menu: {e}'}
    
    def _create_windows_service(self) -> Dict[str, Any]:
        """Create Windows service for background automation"""
        try:
            service_script = f"""
import win32serviceutil
import win32service
import win32event
import servicemanager
import sys
import os

sys.path.insert(0, r"{self.app_path}")

class OmniAutomatorService(win32serviceutil.ServiceFramework):
    _svc_name_ = "OmniAutomatorService"
    _svc_display_name_ = "OmniAutomator Background Service"
    _svc_description_ = "Provides background automation capabilities for OmniAutomator"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        
    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                            servicemanager.PYS_SERVICE_STARTED,
                            (self._svc_name_, ''))
        self.main()
        
    def main(self):
        # Service main loop
        while True:
            rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
            if rc == win32event.WAIT_OBJECT_0:
                break

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(OmniAutomatorService)
"""
            
            service_path = os.path.join(self.app_path, "omni_service.py")
            with open(service_path, 'w') as f:
                f.write(service_script)
            
            return {'success': True, 'message': 'Service script created (manual installation required)'}
            
        except Exception as e:
            return {'success': False, 'error': f'Failed to create service: {e}'}
    
    def _add_to_windows_features(self) -> Dict[str, Any]:
        """Add to Windows optional features"""
        try:
            # Create uninstall entry
            uninstall_key = r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\OmniAutomator"
            
            with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, uninstall_key) as key:
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "OmniAutomator")
                winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.0.0")
                winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "OmniAutomator Team")
                winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, self.app_path)
                winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, 
                                f'"{sys.executable}" "{os.path.join(self.app_path, "uninstall.py")}"')
                winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
            
            return {'success': True, 'message': 'Added to Windows Programs and Features'}
            
        except Exception as e:
            return {'success': False, 'error': f'Failed to add to Windows features: {e}'}
    
    def create_system_commands(self) -> Dict[str, Any]:
        """Create system-wide commands"""
        try:
            # Create batch files for common commands
            commands = {
                'omni': 'main.py',
                'omni-gui': 'launch_gui.py',
                'omni-interactive': 'main.py interactive',
                'omni-status': 'main.py execute "get system info"'
            }
            
            system32_path = os.path.join(os.getenv('WINDIR'), 'System32')
            
            for cmd_name, script in commands.items():
                batch_content = f'''@echo off
cd /d "{self.app_path}"
python {script} %*
'''
                batch_path = os.path.join(system32_path, f"{cmd_name}.bat")
                
                try:
                    with open(batch_path, 'w') as f:
                        f.write(batch_content)
                except PermissionError:
                    # Try alternative location
                    user_path = os.path.join(os.getenv('USERPROFILE'), 'AppData', 'Local', 'Microsoft', 'WindowsApps')
                    os.makedirs(user_path, exist_ok=True)
                    batch_path = os.path.join(user_path, f"{cmd_name}.bat")
                    with open(batch_path, 'w') as f:
                        f.write(batch_content)
            
            return {'success': True, 'message': 'System commands created'}
            
        except Exception as e:
            return {'success': False, 'error': f'Failed to create system commands: {e}'}
    
    def install_powershell_module(self) -> Dict[str, Any]:
        """Install PowerShell module"""
        try:
            # Create PowerShell module
            ps_module_content = f'''
# OmniAutomator PowerShell Module

function Invoke-OmniAutomator {{
    param(
        [Parameter(Mandatory=$true)]
        [string]$Command
    )
    
    $pythonPath = "python"
    $scriptPath = "{self.app_path}\\main.py"
    
    & $pythonPath $scriptPath execute $Command
}}

function Start-OmniAutomatorGUI {{
    $pythonPath = "python"
    $scriptPath = "{self.app_path}\\launch_gui.py"
    
    Start-Process $pythonPath -ArgumentList $scriptPath
}}

function Get-OmniAutomatorStatus {{
    $pythonPath = "python"
    $scriptPath = "{self.app_path}\\main.py"
    
    & $pythonPath $scriptPath execute "ai-status"
}}

# Aliases
Set-Alias omni Invoke-OmniAutomator
Set-Alias omni-gui Start-OmniAutomatorGUI
Set-Alias omni-status Get-OmniAutomatorStatus

Export-ModuleMember -Function Invoke-OmniAutomator, Start-OmniAutomatorGUI, Get-OmniAutomatorStatus
Export-ModuleMember -Alias omni, omni-gui, omni-status
'''
            
            # Get PowerShell modules path
            ps_modules_path = os.path.join(os.getenv('USERPROFILE'), 'Documents', 'WindowsPowerShell', 'Modules')
            omni_module_path = os.path.join(ps_modules_path, 'OmniAutomator')
            
            os.makedirs(omni_module_path, exist_ok=True)
            
            module_file = os.path.join(omni_module_path, 'OmniAutomator.psm1')
            with open(module_file, 'w') as f:
                f.write(ps_module_content)
            
            return {'success': True, 'message': 'PowerShell module installed'}
            
        except Exception as e:
            return {'success': False, 'error': f'Failed to install PowerShell module: {e}'}
    
    def create_uninstaller(self) -> Dict[str, Any]:
        """Create uninstaller script"""
        try:
            uninstaller_content = f'''#!/usr/bin/env python3
"""
OmniAutomator Uninstaller
"""

import os
import sys
import winreg
import shutil
from tkinter import messagebox

def uninstall():
    """Uninstall OmniAutomator"""
    try:
        # Remove from registry
        keys_to_remove = [
            r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\OmniAutomator",
            r"Directory\\Background\\shell\\OmniAutomator",
            r"*\\shell\\OmniAutomator",
            ".omni",
            ".oauto",
            "OmniAutomator.Script",
            "OmniAutomator.Batch"
        ]
        
        for key_path in keys_to_remove:
            try:
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path)
            except:
                try:
                    winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, key_path)
                except:
                    pass
        
        # Remove shortcuts
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        shortcut_path = os.path.join(desktop, "OmniAutomator.lnk")
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)
        
        # Remove from Start Menu
        start_menu = os.path.join(os.getenv('APPDATA'), 
                                 "Microsoft", "Windows", "Start Menu", "Programs", "OmniAutomator")
        if os.path.exists(start_menu):
            shutil.rmtree(start_menu)
        
        messagebox.showinfo("Uninstall Complete", "OmniAutomator has been uninstalled successfully.")
        
    except Exception as e:
        messagebox.showerror("Uninstall Error", f"Failed to uninstall: {{e}}")

if __name__ == "__main__":
    uninstall()
'''
            
            uninstaller_path = os.path.join(self.app_path, "uninstall.py")
            with open(uninstaller_path, 'w') as f:
                f.write(uninstaller_content)
            
            return {'success': True, 'message': 'Uninstaller created'}
            
        except Exception as e:
            return {'success': False, 'error': f'Failed to create uninstaller: {e}'}

def main():
    """Main function for testing"""
    integration = SystemIntegration()
    
    if not integration.is_admin:
        print("⚠️ Administrator privileges required for full system integration")
        print("Run as administrator for complete installation")
        return
    
    print("🚀 Installing OmniAutomator system integration...")
    
    result = integration.install_system_integration()
    
    if result['success']:
        print("✅ System integration completed successfully!")
        for component, status in result['results'].items():
            if status.get('success'):
                print(f"  ✅ {component}: {status['message']}")
            else:
                print(f"  ❌ {component}: {status['error']}")
    else:
        print(f"❌ System integration failed: {result['error']}")

if __name__ == "__main__":
    main()
