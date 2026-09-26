"""Adapt existing ``AutomationPlugin`` instances to the Capability interface.

This is the bridge that lets every current plugin appear in the
:class:`CapabilityRegistry` without modifying the plugin.  New functionality
should prefer native :class:`Capability` subclasses; legacy plugins ride in
through this adapter during the migration.
"""

from __future__ import annotations

from typing import Any

from ..core.plugin_manager import AutomationPlugin, PluginManager
from ..security.permission_manager import PermissionManager
from .base import ActionSpec, Capability, CapabilityResult, RiskLevel
from .registry import CapabilityRegistry


class PluginCapability(Capability):
    """Wrap one :class:`AutomationPlugin` as a :class:`Capability`."""

    def __init__(
        self,
        plugin: AutomationPlugin,
        *,
        permission_manager: PermissionManager | None = None,
    ) -> None:
        self._plugin = plugin
        self._pm = permission_manager
        self.name = plugin.name
        self.description = plugin.description
        self.risk = RiskLevel.MEDIUM  # baseline; per-action risk resolved below

    def discover(self) -> list[ActionSpec]:
        specs: list[ActionSpec] = []
        try:
            actions = self._plugin.get_capabilities() or []
        except Exception:
            actions = []
        for action in actions:
            risk = self._risk_for(action)
            specs.append(
                ActionSpec(
                    name=action,
                    risk=risk,
                    requires_approval=risk in (RiskLevel.HIGH, RiskLevel.DESTRUCTIVE),
                )
            )
        return specs

    def _risk_for(self, action: str) -> RiskLevel:
        """Derive per-action risk from the security policy when available."""
        if self._pm is not None:
            category = self._pm._map_to_action_category(self.name, action)
            if category is not None:
                rule = self._pm.permission_rules.get(category)
                if rule is not None:
                    return RiskLevel.from_permission_level(rule.permission_level)
        return RiskLevel.MEDIUM

    def _supports(self, action: str) -> bool:
        """Whether the plugin handles ``action`` — exact or prefix match.

        Mirrors :meth:`archon.core.plugin_manager.PluginManager.execute` /
        ``get_plugin_by_capability`` so routing through the registry keeps the
        legacy prefix-matching behavior (e.g. ``navigate_to_x`` -> ``navigate_to``).
        """
        try:
            caps = self._plugin.get_capabilities() or []
        except Exception:
            caps = []
        if action in caps:
            return True
        return any(isinstance(cap, str) and action.startswith(cap) for cap in caps)

    def validate(self, action: str, params: dict[str, Any]) -> tuple[bool, str | None]:
        if self._supports(action):
            return True, None
        return False, f"Unknown action '{action}' for capability '{self.name}'"

    def execute(self, action: str, params: dict[str, Any]) -> CapabilityResult:
        ok, err = self.validate(action, params)
        if not ok:
            return CapabilityResult.fail(err or "validation failed")
        try:
            raw = self._plugin.execute(action, params or {})
        except Exception as e:  # preserve legacy result shape on the error path
            return CapabilityResult.fail(str(e), action=action, capability=self.name)
        # Plugins already tend to return {"success": bool, ...}; respect that.
        if isinstance(raw, dict) and "success" in raw:
            return CapabilityResult(
                success=bool(raw.get("success")),
                data=raw,
                error=raw.get("error"),
                metadata={"action": action, "capability": self.name},
                raw=raw,
            )
        return CapabilityResult.ok(raw, action=action, capability=self.name)

    def invoke(self, action: str, params: dict[str, Any]) -> Any:
        """Run the plugin and return its raw result, raising on failure.

        Faithful to :meth:`PluginManager.execute`: the plugin's own exceptions
        propagate (so the engine's existing fall-through / error handling is
        unchanged) rather than being swallowed into a result dict.
        """
        return self._plugin.execute(action, params or {})


def build_registry_from_plugin_manager(
    plugin_manager: PluginManager,
    *,
    permission_manager: PermissionManager | None = None,
    registry: CapabilityRegistry | None = None,
) -> CapabilityRegistry:
    """Populate (or create) a registry with capabilities for every loaded plugin.

    Additive: existing dispatch through ``PluginManager`` is untouched.  This
    simply exposes the same plugins through the capability surface.
    """
    registry = registry or CapabilityRegistry()
    if permission_manager is not None:
        registry.attach_permission_manager(permission_manager)
    for plugin in plugin_manager.plugins.values():
        registry.register(
            PluginCapability(plugin, permission_manager=permission_manager),
            replace=True,
        )
    return registry
