#!/usr/bin/env python3
"""
Tyranos CLI launcher script.

Run directly:
    python tyranos.py run "create a folder named reports"
    python tyranos.py chatbot
    python tyranos.py --help

Or use the installed command:
    tyranos run "create a folder named reports"
    tyranos chatbot
    tyranos --help
"""

import os
import sys

# Ensure the project root is on sys.path so the tyranos package is importable
# when this file is invoked directly (e.g. python tyranos.py).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tyranos._cli import app  # noqa: E402

if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)
