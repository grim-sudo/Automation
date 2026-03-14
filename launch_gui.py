#!/usr/bin/env python3
"""
GUI Launcher — backward compatibility shim.
Delegates to `omni gui` via the unified omni.py entry point.

Prefer using:  omni gui
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    """Launch the OmniAutomator GUI via the unified CLI."""
    sys.argv = [sys.argv[0], "gui"]
    from omni import app  # type: ignore[import]
    app()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGUI closed")
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"Failed to start GUI: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
