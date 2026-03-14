#!/usr/bin/env python3
"""
Tyranos legacy entry point — backward compatibility shim.
Delegates to the unified tyranos.py entry point via the typer CLI.

For the new interface, use:
  tyranos run "your command"
  tyranos chatbot
  tyranos gui
  tyranos batch commands.txt
"""
from __future__ import annotations

import io
import os
import sys

# Fix encoding on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    """Translate legacy argparse arguments to tyranos.py typer commands and execute."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Tyranos — legacy entry point (use `tyranos` for the new interface)",
        add_help=False,
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("-i", "--interactive", action="store_true")
    mode_group.add_argument("-g", "--gui", action="store_true")
    mode_group.add_argument("-b", "--batch", type=str, metavar="FILE")
    parser.add_argument("-m", "--model", type=str)
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--safe-mode", action="store_true")
    parser.add_argument("commands", nargs="*")
    # absorb unknown flags silently for forward-compat
    args, _ = parser.parse_known_args()

    # Build equivalent typer argv for omni.py
    new_argv = [sys.argv[0]]
    if args.debug:
        new_argv += ["--debug"]
    if args.safe_mode:
        new_argv += ["--safe-mode"]

    if args.list_models:
        # No direct equivalent; show message
        print("Use `tyranos --help` or check your config.toml for available model options.")
        sys.exit(0)

    if args.gui:
        new_argv.append("gui")
    elif args.interactive:
        new_argv.append("chatbot")
    elif args.batch:
        new_argv += ["batch", args.batch]
    elif args.commands:
        new_argv += ["run", " ".join(args.commands)]
    else:
        new_argv.append("chatbot")

    # Invoke tyranos app
    sys.argv = new_argv
    from tyranos import app  # type: ignore[import]
    app()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"\nError: {exc}")
        sys.exit(1)
