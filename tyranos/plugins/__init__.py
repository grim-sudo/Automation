"""
Tyranos plugins package.

Plugins are loaded dynamically by the PluginManager at runtime.
This __init__.py provides lazy imports so optional feature plugins
(n8n_bridge, distro_builder) do not fail if their dependencies are absent.
"""

from __future__ import annotations

__all__ = [
    "DevOpsGeneratorPlugin",
    "FolderOperations",
    "ProjectGeneratorPlugin",
    "UniversalAutomationPlugin",
    "WebAutomationPlugin",
    "get_available_plugins",
]

# Core plugins — always available
from .devops_generator import DevOpsGeneratorPlugin
from .folder_operations import FolderOperations
from .project_generator import ProjectGeneratorPlugin
from .universal_automation import UniversalAutomationPlugin
from .web_automation import WebAutomationPlugin

# Optional: n8n bridge — requires aiohttp
try:
    from .n8n_bridge import (  # noqa: F401
        N8nConfig,
        TriggerEngine,
        WorkflowManager,
        build_linear_workflow,
        parse_nl_to_steps,
    )

    __all__ += [
        "WorkflowManager",
        "TriggerEngine",
        "N8nConfig",
        "build_linear_workflow",
        "parse_nl_to_steps",
    ]
    _N8N_AVAILABLE = True
except ImportError:
    _N8N_AVAILABLE = False

# Optional: distro builder — requires root + Linux build tools
try:
    from ..distro_builder import (  # noqa: F401
        DistroProfile,
        build_distro,
        build_from_nl,
        estimate_build_time,
    )

    __all__ += ["build_distro", "build_from_nl", "estimate_build_time", "DistroProfile"]
    _DISTRO_AVAILABLE = True
except ImportError:
    _DISTRO_AVAILABLE = False


def get_available_plugins() -> dict[str, bool]:
    """Return a dict of plugin names and their availability status."""
    return {
        "devops_generator": True,
        "folder_operations": True,
        "project_generator": True,
        "universal_automation": True,
        "web_automation": True,
        "n8n_bridge": _N8N_AVAILABLE,
        "distro_builder": _DISTRO_AVAILABLE,
    }
