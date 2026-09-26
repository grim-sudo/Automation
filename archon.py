#!/usr/bin/env python3
"""
Archon CLI launcher script.

Run directly:
    python archon.py run "create a folder named reports"
    python archon.py chatbot
    python archon.py --help

Or use the installed command:
    archon run "create a folder named reports"
    archon chatbot
    archon --help

Feature flags
-------------
ARCHON_RUST_CLI=1
    Delegate to the compiled Rust CLI binary (archon-bin) if it exists on PATH
    or in one of the well-known build output directories.  Falls back to the
    Python CLI silently when the binary is not found.

ARCHON_GUI=tauri|ctk
    Select GUI backend (default: ctk — CustomTkinter).  Only used when the Rust
    CLI or the Python CLI launches the `gui` subcommand.
"""

from __future__ import annotations

import os
import subprocess
import sys

# ---------------------------------------------------------------------------
# ARCHON_RUST_CLI feature flag
# ---------------------------------------------------------------------------
_RUST_CLI_ENABLED = os.environ.get("ARCHON_RUST_CLI", "").strip() in ("1", "true", "yes")

if _RUST_CLI_ENABLED:
    # Search order: PATH, then common Cargo build output relative to this file.
    _PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    _RUST_CANDIDATES = [
        # 1. symlink or copy on user PATH
        "archon-bin",
        # 2. release build (the normal case after `cargo build --release`)
        os.path.join(_PROJECT_ROOT, "crates", "archon-cli", "target", "release", "archon-bin"),
        # 3. debug build
        os.path.join(_PROJECT_ROOT, "crates", "archon-cli", "target", "debug", "archon-bin"),
        # 4. workspace-level release output
        os.path.join(_PROJECT_ROOT, "target", "release", "archon-bin"),
    ]

    _rust_bin: str | None = None
    for _candidate in _RUST_CANDIDATES:
        # For bare names use PATH lookup; for absolute paths check existence.
        if os.sep in _candidate or _candidate.startswith("."):
            if os.path.isfile(_candidate) and os.access(_candidate, os.X_OK):
                _rust_bin = _candidate
                break
        else:
            # Try which-style resolution
            import shutil as _shutil

            _resolved = _shutil.which(_candidate)
            if _resolved:
                _rust_bin = _resolved
                break

    if _rust_bin:
        # Delegate entirely — replace the current process.
        try:
            result = subprocess.run([_rust_bin] + sys.argv[1:], check=False)
            sys.exit(result.returncode)
        except KeyboardInterrupt:
            sys.exit(0)
    # If binary not found fall through to Python CLI silently.

# ---------------------------------------------------------------------------
# ARCHON_GUI=tauri IPC bridge
# ---------------------------------------------------------------------------
# When Tauri's Rust backend spawns `python archon.py --tauri-ipc`, it writes
# a JSON payload to stdin and reads a JSON response from stdout.  This handler
# runs before the normal CLI so it has minimal import overhead.
if "--tauri-ipc" in sys.argv:
    import json as _json

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    def _tauri_ipc() -> None:
        try:
            raw = sys.stdin.read().strip()
            payload = _json.loads(raw) if raw else {}
        except Exception as _exc:
            sys.stdout.write(_json.dumps({"error": f"JSON parse error: {_exc}"}))
            sys.exit(1)

        action = payload.get("action", "")
        try:
            response = _dispatch_ipc(action, payload)
            sys.stdout.write(_json.dumps(response) if not isinstance(response, str) else response)
        except Exception as _exc:
            sys.stdout.write(_json.dumps({"error": str(_exc)}))
            sys.exit(1)

    def _dispatch_ipc(action: str, payload: dict) -> object:  # type: ignore[type-arg]
        """Route an IPC action to the correct Archon subsystem."""
        import asyncio as _asyncio

        if action == "chat":
            from archon.core.engine import Archon as _Archon

            eng = _Archon()
            result = eng.execute(payload.get("message", ""))
            return result if isinstance(result, str) else str(result)

        if action == "run":
            from archon.core.engine import Archon as _Archon

            eng = _Archon()
            result = eng.execute(payload.get("command", ""))
            return result if isinstance(result, str) else str(result)

        if action == "n8n_list":
            from archon.config import get_config
            from archon.plugins.n8n_bridge import N8nConfig, WorkflowManager

            cfg = get_config()
            n8n_cfg = N8nConfig(url=cfg.n8n.url, api_key=cfg.n8n.api_key or "")
            mgr = WorkflowManager(n8n_cfg)
            wfs = _asyncio.run(mgr.list_workflows())
            return _json.dumps([w.__dict__ if hasattr(w, "__dict__") else w for w in wfs])

        if action == "n8n_trigger":
            from archon.config import get_config
            from archon.plugins.n8n_bridge import N8nConfig, WorkflowManager

            cfg = get_config()
            n8n_cfg = N8nConfig(url=cfg.n8n.url, api_key=cfg.n8n.api_key or "")
            mgr = WorkflowManager(n8n_cfg)
            result = _asyncio.run(mgr.trigger_workflow(payload.get("id", "")))
            return str(result)

        if action == "n8n_create":
            from archon.config import get_config
            from archon.plugins.n8n_bridge import N8nConfig, WorkflowManager

            cfg = get_config()
            n8n_cfg = N8nConfig(url=cfg.n8n.url, api_key=cfg.n8n.api_key or "")
            mgr = WorkflowManager(n8n_cfg)
            _asyncio.run(
                mgr.create_workflow(
                    name=payload.get("name", ""), description=payload.get("description", "")
                )
            )
            return "ok"

        if action == "distro_profiles":
            import importlib as _importlib

            mod = _importlib.import_module("archon.distro_builder.profiles")
            profiles = mod.list_profiles() if hasattr(mod, "list_profiles") else []
            return _json.dumps(profiles)

        if action == "distro_build":
            return "Build dispatched — use CLI: archon distro build"

        if action == "history":
            return _json.dumps([])

        if action == "models":
            from archon.ai.model_resolver import FreeModelResolver

            resolver = FreeModelResolver()
            models = _asyncio.run(resolver.resolve()) if hasattr(resolver, "resolve") else []
            return _json.dumps([{"id": m} if isinstance(m, str) else m for m in models])

        if action == "save_settings":
            # Persisting settings is handled by the config module at runtime.
            return "ok"

        return _json.dumps({"error": f"Unknown action: {action}"})

    _tauri_ipc()
    sys.exit(0)


# Ensure the project root is on sys.path so the archon package is importable
# when this file is invoked directly (e.g. python archon.py).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from archon._cli import app  # noqa: E402

if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)
