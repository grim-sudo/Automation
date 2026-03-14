#!/usr/bin/env python3
"""Backward-compatible entry point — delegates to tyranos.py.

This file is kept so that any scripts or shell aliases that call
``python omni.py`` or ``omni`` (if installed from an old wheel) keep
working.  New code should use ``tyranos`` directly.
"""

import warnings

warnings.warn(
    "omni.py is deprecated; use tyranos.py or the 'tyranos' command instead.",
    DeprecationWarning,
    stacklevel=1,
)

from tyranos import app  # noqa: F401, E402 (re-export for console_script)

if __name__ == "__main__":
    import sys

    from tyranos import app

    try:
        app()
    except KeyboardInterrupt:
        sys.exit(0)
