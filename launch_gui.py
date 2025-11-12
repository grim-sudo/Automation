#!/usr/bin/env python3
"""
GUI Launcher for OmniAutomator
Handles dependency installation and GUI startup
"""

import os
import sys
import subprocess
import importlib.util

def check_dependencies():
    """Check and install required dependencies"""
    required_packages = {
        'customtkinter': 'customtkinter',
        'psutil': 'psutil',
        'pywin32': 'pywin32'
    }
    
    missing_packages = []
    
    for package_name, pip_name in required_packages.items():
        if importlib.util.find_spec(package_name) is None:
            missing_packages.append(pip_name)
    
    if missing_packages:
        print("Installing missing dependencies...")
        for package in missing_packages:
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                print(f"Installed {package}")
            except subprocess.CalledProcessError:
                print(f"Failed to install {package}")
    
    return len(missing_packages) == 0

def launch_gui():
    """Launch the OmniAutomator GUI"""
    try:
        print("Starting OmniAutomator GUI...")
        
        # Check dependencies
        if not check_dependencies():
            print("Some dependencies failed to install. GUI may not work properly.")
        
        # Set API key if provided
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            print("Tip: Set OPENROUTER_API_KEY environment variable for AI features")
        
        # Import and run GUI
        from omni_automator.ui.gui_app import ModernOmniAutomatorGUI
        
        app = ModernOmniAutomatorGUI()
        app.run()
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Trying to install missing dependencies...")
        
        # Try to install customtkinter
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'customtkinter', 'psutil', 'pywin32'])
            print("Dependencies installed. Please run again.")
        except:
            print("Failed to install dependencies automatically.")
            print("Please run: pip install customtkinter psutil pywin32")
    
    except Exception as e:
        print(f"Failed to start GUI: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    launch_gui()
