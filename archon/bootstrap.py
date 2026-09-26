"""
Startup bootstrap: environment and native-runtime setup.

Two jobs, both aimed at making Archon "just work" from a bare ``archon`` call:

* :func:`load_env` folds a project ``.env`` into ``os.environ`` so every
  subsystem that reads ``os.getenv(...)`` (the AI model manager, OpenRouter
  integration, n8n bridge, …) sees the user's keys without any extra wiring.
* :func:`ensure_tk` makes the CustomTkinter GUI launchable even when Tcl/Tk
  ships in a non-standard prefix. ``_tkinter`` resolves ``libtk`` through the
  dynamic loader at import time, and glibc caches ``LD_LIBRARY_PATH`` at process
  start — so the only reliable fix is to set the vars and re-exec once.

Both functions are idempotent and safe to call from any entry point.
"""

from __future__ import annotations

import glob
import os
import sys

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


# Directories to probe for a bundled/side-loaded Tcl/Tk when the system copy is
# missing. An explicit ``ARCHON_TK_LIB`` always takes priority.
_TK_LIB_DIRS = [
    "/tmp/opencode/tklocal/usr/lib",
    "/usr/lib",
    "/usr/lib64",
    "/usr/local/lib",
]


def _tk_importable() -> bool:
    try:
        import tkinter  # noqa: F401

        return True
    except Exception:
        return False


def _find_tk_lib_dir() -> str | None:
    override = os.environ.get("ARCHON_TK_LIB", "").strip()
    dirs = ([override] if override else []) + _TK_LIB_DIRS
    for d in dirs:
        if d and glob.glob(os.path.join(d, "libtk8.*.so*")):
            return d
    return None


def ensure_tk() -> None:
    """Ensure ``tkinter`` can load, re-exec with the right env vars if not.

    No-op when Tk already imports (the common case on a properly configured
    machine). When it fails, we locate a usable Tcl/Tk prefix, export
    ``LD_LIBRARY_PATH`` / ``TCL_LIBRARY`` / ``TK_LIBRARY``, and re-exec the
    interpreter exactly once (guarded by ``ARCHON_TK_REEXEC``).
    """
    if _tk_importable():
        return
    if os.environ.get("ARCHON_TK_REEXEC") == "1":
        # We already re-exec'd once and Tk still won't load — don't loop.
        return

    lib_dir = _find_tk_lib_dir()
    if not lib_dir:
        return  # Nothing we can do; let the caller surface the ImportError.

    env = dict(os.environ)
    existing = env.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = lib_dir + (os.pathsep + existing if existing else "")

    for var, pattern in (("TCL_LIBRARY", "tcl8.*"), ("TK_LIBRARY", "tk8.*")):
        matches = sorted(
            p for p in glob.glob(os.path.join(lib_dir, pattern)) if os.path.isdir(p)
        )
        if matches:
            env[var] = matches[-1]

    env["ARCHON_TK_REEXEC"] = "1"
    os.execve(sys.executable, [sys.executable, *sys.argv], env)
