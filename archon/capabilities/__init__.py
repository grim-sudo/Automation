"""Archon capability layer.

The capability system is the stable seam between the agent core and the many
things Archon can do.  Sources of capabilities (native code, legacy plugins,
and — later — MCP servers) all register into one :class:`CapabilityRegistry`
and expose the same ``capability -> action -> params -> CapabilityResult``
contract.

This package is additive; it does not alter the legacy execution path.
"""

from __future__ import annotations

from .base import ActionSpec, Capability, CapabilityResult, RiskLevel
from .plugin_adapter import PluginCapability, build_registry_from_plugin_manager
from .registry import CapabilityRegistry

__all__ = [
    "ActionSpec",
    "Capability",
    "CapabilityResult",
    "RiskLevel",
    "CapabilityRegistry",
    "PluginCapability",
    "build_registry_from_plugin_manager",
]
