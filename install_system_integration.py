#!/usr/bin/env python3
"""
System Integration Installer for OmniAutomator
"""

import os
import sys
import subprocess
import ctypes
from pathlib import Path

def check_admin():
    """Check if running as administrator"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    
    dependencies = [
        'customtkinter',
        'psutil', 
        'pywin32',
        'pillow',
        'requests',
        'beautifulsoup4',
        'pandas',
        'matplotlib',
        'openai'
    ]
    
    for dep in dependencies:
        try:
            print(f"Installing {dep}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', dep])
            print(f"✅ {dep} installed")
        except subprocess.CalledProcessError:
            print(f"⚠️ Failed to install {dep}")
    
    print("✅ Dependencies installation complete")

def run_system_integration():
    """Run system integration"""
    print("🔧 Running system integration...")
    
    try:
        from omni_automator.core.system_integration import SystemIntegration
        
        integration = SystemIntegration()
        
        if not integration.is_admin:
            print("⚠️ Administrator privileges required for full system integration")
            return False
        
        # Install system integration
        result = integration.install_system_integration()
        
        if result['success']:
            print("✅ System integration completed!")
            
            # Show results
            for component, status in result['results'].items():
                if status.get('success'):
                    print(f"  ✅ {component}: {status['message']}")
                else:
                    print(f"  ❌ {component}: {status['error']}")
            
            # Create system commands
            cmd_result = integration.create_system_commands()
            if cmd_result['success']:
                print(f"  ✅ System commands: {cmd_result['message']}")
            
            # Install PowerShell module
            ps_result = integration.install_powershell_module()
            if ps_result['success']:
                print(f"  ✅ PowerShell module: {ps_result['message']}")
            
            # Create uninstaller
            uninst_result = integration.create_uninstaller()
            if uninst_result['success']:
                print(f"  ✅ Uninstaller: {uninst_result['message']}")
            
            return True
        else:
            print(f"❌ System integration failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ System integration error: {e}")
        return False

def main():
    """Main installer function"""
    print("🚀 OmniAutomator System Integration Installer")
    print("=" * 60)
    
    # Check if running as admin
    if not check_admin():
        print("⚠️ This installer requires administrator privileges")
        print("Please run as administrator for full system integration")
        
        # Try to restart as admin
        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            return
        except:
            print("❌ Failed to restart as administrator")
            input("Press Enter to continue with limited installation...")
    
    try:
        # Step 1: Install dependencies
        install_dependencies()
        
        # Step 2: Run system integration
        success = run_system_integration()
        
        if success:
            print("\n🎉 Installation Complete!")
            print("\n🚀 OmniAutomator is now fully integrated into your system!")
            print("\n📋 Available Commands:")
            print("  • omni <command>           - Execute automation command")
            print("  • omni-gui                 - Launch GUI interface")
            print("  • omni-interactive         - Launch interactive mode")
            print("  • omni-status              - Check system status")
            print("\n📁 Available Features:")
            print("  • Right-click context menu integration")
            print("  • Desktop and Start Menu shortcuts")
            print("  • File associations for .omni and .oauto files")
            print("  • PowerShell module integration")
            print("  • System PATH integration")
            print("\n🎯 Quick Start:")
            print("  1. Type 'omni-gui' to launch the GUI")
            print("  2. Right-click in any folder → 'Open OmniAutomator Here'")
            print("  3. Use PowerShell: Import-Module OmniAutomator")
            
        else:
            print("\n⚠️ Installation completed with some issues")
            print("Check the messages above for details")
        
        print(f"\n📁 Installation Location: {os.path.dirname(os.path.abspath(__file__))}")
        
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
