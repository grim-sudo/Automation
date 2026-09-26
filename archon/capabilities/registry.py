"""Central registry for Archon capabilities.

Small on purpose.  It holds capability instances, resolves them by name,
reports availability, and defers dangerous-action decisions to the security
policy layer.  It is *not* an execution engine and must not grow into one —
the agent core owns orchestration.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from .base import Capability, RiskLevel


class CapabilityRegistry:
    """Registers and resolves capabilities from any source (native, plugin, MCP)."""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability, *, replace: bool = False) -> None:
        """Register a capability.

        Raises ``ValueError`` on duplicate names unless ``replace=True``.
        """
        name = capability.name
        if not name:
            raise ValueError("Capability must have a non-empty name")
        if name in self._capabilities and not replace:
            raise ValueError(f"Capability '{name}' is already registered")
        self._capabilities[name] = capability
        logger.debug(f"Registered capability: {name}")

    def unregister(self, name: str) -> bool:
        """Remove a capability by name.  Returns True if it existed."""
        return self._capabilities.pop(name, None) is not None

    def get(self, name: str) -> Capability | None:
        """Resolve a capability by name, or None if absent."""
        return self._capabilities.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self._capabilities

    def list(self) -> list[str]:
        """All registered capability names."""
        return list(self._capabilities.keys())

    def describe(self) -> dict[str, dict[str, Any]]:
        """Metadata for every capability — for discovery/exposure to the agent."""
        out: dict[str, dict[str, Any]] = {}
        for name, cap in self._capabilities.items():
            out[name] = {
                "description": cap.description,
                "risk": cap.risk.value,
                "actions": [
                    {"name": spec.name, "risk": spec.risk.value, "description": spec.description}
                    for spec in _safe_discover(cap)
                ],
            }
        return out

    def available(self) -> list[str]:
        """Names of capabilities whose health probe reports available."""
        names = []
        for name, cap in self._capabilities.items():
            try:
                if cap.health().get("available", True):
                    names.append(name)
            except Exception as e:  # a broken capability must not break discovery
                logger.warning(f"Health check failed for capability '{name}': {e}")
        return names

    def find_by_action(self, action: str) -> list[str]:
        """Capabilities that advertise ``action`` (exact match)."""
        return [name for name, cap in self._capabilities.items() if action in _safe_actions(cap)]

    def route(self, action: str) -> list[str]:
        """Ordered capability names that can handle ``action`` (exact, then prefix).

        Single source of truth for capability resolution, replacing the
        duplicated ``PluginManager.get_plugin_by_capability`` logic.  A capability
        matches if it advertises ``action`` exactly, or advertises a prefix of it
        (e.g. ``navigate_to`` handles ``navigate_to_search_engine``).
        """
        matches: list[str] = []
        for name, cap in self._capabilities.items():
            acts = _safe_actions(cap)
            if action in acts or any(
                isinstance(a, str) and action.startswith(a) for a in acts
            ):
                matches.append(name)
        return matches

    def dispatch(self, name: str, action: str, params: dict[str, Any] | None = None) -> Any:
        """Execute ``action`` on capability ``name`` and return the raw result.

        The registry is the execution router: this mirrors the old
        ``PluginManager.execute`` contract exactly — an unknown capability or an
        unsupported action raises ``ValueError``, and the underlying
        implementation's own exceptions propagate untouched.
        """
        cap = self.get(name)
        if cap is None:
            raise ValueError(f"Plugin '{name}' not found")
        acts = _safe_actions(cap)
        supported = action in acts or any(
            isinstance(a, str) and action.startswith(a) for a in acts
        )
        if not supported:
            raise ValueError(f"Action '{action}' not supported by plugin '{name}'")
        return cap.invoke(action, params or {})

    def check_permission(
        self, name: str, action: str, params: dict[str, Any] | None = None
    ) -> bool:
        """Whether ``action`` on capability ``name`` is currently allowed.

        Delegates the real decision to a :class:`PermissionManager` when one is
        attached; otherwise allows everything except DESTRUCTIVE actions, which
        always require explicit approval.
        """
        cap = self.get(name)
        if cap is None:
            return False
        risk = cap.risk_of(action)
        pm = getattr(self, "_permission_manager", None)
        if pm is not None:
            return pm.check_permission(
                {"action": action, "category": name, "params": params or {}}
            )
        return risk is not RiskLevel.DESTRUCTIVE

    def attach_permission_manager(self, permission_manager: Any) -> None:
        """Wire a security PermissionManager for permission decisions."""
        self._permission_manager = permission_manager


def _safe_discover(cap: Capability) -> list:
    try:
        return cap.discover()
    except Exception as e:
        logger.warning(f"discover() failed for capability '{cap.name}': {e}")
        return []


def _safe_actions(cap: Capability) -> list[str]:
    return [spec.name for spec in _safe_discover(cap)]
