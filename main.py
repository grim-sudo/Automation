#!/usr/bin/env python3
"""
OmniAutomator - Universal OS Automation Framework
Main entry point for the application
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from omni_automator.ui.cli import cli

if __name__ == '__main__':
    cli()
