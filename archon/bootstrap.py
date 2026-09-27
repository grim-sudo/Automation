"""
Startup bootstrap: environment setup.

:func:`load_env` folds a project ``.env`` into ``os.environ`` so every
subsystem that reads ``os.getenv(...)`` (the AI model manager, OpenRouter
integration, n8n bridge, …) sees the user's keys without any extra wiring.
It is idempotent and safe to call from any entry point.
"""

from __future__ import annotations

import os

_ENV_LOADED = False


def load_env() -> None:
    """Load a ``.env`` file into ``os.environ`` (real env vars win).

    Searches the current working directory and the project root (two levels up
    from this file). Missing files and a missing ``python-dotenv`` are non-fatal.
    """
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True

    try:
        from dotenv import load_dotenv
    except Exception:
        return

    candidates = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
    ]
    seen: set[str] = set()
    for path in candidates:
        real = os.path.realpath(path)
        if real in seen or not os.path.isfile(real):
            continue
        seen.add(real)
        # override=False: a value already exported in the shell beats the file.
        load_dotenv(real, override=False)
