"""Native filesystem capability.

Owns folder creation and file download, carved out of the
``universal_automation`` god plugin.  The plugin now delegates here, so the
legacy dispatch path is unchanged while this becomes a first-class native
capability the registry can expose directly.

Behavior (including the audit-log side effect on downloads and the exact
result-dict shapes) is preserved verbatim from the plugin.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from ...utils.file_resolver import resolve_desktop_path
from ..base import ActionSpec, Capability, CapabilityResult, RiskLevel

_FOLDER_ACTIONS = ("create_folder", "make_directory", "ensure_folder")
_DOWNLOAD_ACTIONS = ("download_file",)


class FilesystemCapability(Capability):
    """Create folders and download files to disk."""

    name = "filesystem"
    description = "Create folders/directories and download files to disk"
    risk = RiskLevel.MEDIUM

    def discover(self) -> list[ActionSpec]:
        actions = _FOLDER_ACTIONS + _DOWNLOAD_ACTIONS
        return [ActionSpec(name=a, risk=RiskLevel.MEDIUM) for a in actions]

    def execute(self, action: str, params: dict[str, Any]) -> CapabilityResult:
        ok, err = self.validate(action, params)
        if not ok:
            return CapabilityResult.fail(err or "validation failed")
        result = self.run(action, params or {})
        return CapabilityResult(
            success=bool(result.get("success")),
            data=result,
            error=result.get("error"),
            metadata={"action": action, "capability": self.name},
            raw=result,
        )

    def run(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Dispatch to the right operation and return the legacy result dict."""
        if action in _FOLDER_ACTIONS:
            return self.create_folder(params)
        if action in _DOWNLOAD_ACTIONS:
            return self.download_file(params)
        return {"success": False, "error": f"Unknown filesystem action '{action}'"}

    # ── operations (behavior copied verbatim from universal_automation) ──────

    def create_folder(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a folder/directory"""
        try:
            folder_path = (
                params.get("path")
                or params.get("folder")
                or params.get("directory")
                or params.get("name")
            )

            if not folder_path:
                return {"success": False, "error": "No folder path provided"}

            # Resolve path
            folder_path = resolve_desktop_path(folder_path)

            # Create folder
            os.makedirs(folder_path, exist_ok=True)

            return {"success": True, "message": "Folder created successfully", "path": folder_path}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def download_file(self, params: dict[str, Any]) -> dict[str, Any]:
        """Download a file from URL to destination path"""
        url = params.get("url") or params.get("source")
        dest = params.get("dest") or params.get("destination") or params.get("path")
        if not url:
            return {"success": False, "message": "No URL provided"}
        if not dest:
            # default to temp filename
            import tempfile

            dest = os.path.join(tempfile.gettempdir(), os.path.basename(url))

        try:
            with httpx.Client(follow_redirects=True, timeout=60.0) as client:
                with client.stream("GET", url) as resp:
                    resp.raise_for_status()
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(dest, "wb") as f:
                        for chunk in resp.iter_bytes(8192):
                            f.write(chunk)
            result = {"success": True, "path": dest, "message": f"Downloaded {url} to {dest}"}
        except Exception as e:
            result = {"success": False, "error": str(e), "message": "Download failed"}

        # Audit log
        try:
            with open(
                os.path.join(os.path.expanduser("~"), ".local", "share", "archon", "action.log"),
                "a",
                encoding="utf-8",
            ) as logf:
                logf.write(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] download_file params={params} result={result}\n"
                )
        except Exception:
            pass

        return result
