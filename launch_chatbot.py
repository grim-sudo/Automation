#!/usr/bin/env python3
"""
Interactive Chatbot Launcher — backward compatibility shim.
Delegates to `archon chatbot` via the unified archon._cli entry point.

Prefer using:  archon chatbot
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    """Start the Archon chatbot via the unified CLI."""
    sys.argv = [sys.argv[0], "chatbot"]
    from archon._cli import app  # type: ignore[import]
    app()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSession ended by user")
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"Error: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
