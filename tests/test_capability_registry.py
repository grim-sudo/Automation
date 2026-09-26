"""Tests for the additive capability layer: registry + plugin adapter.

The capability system must expose existing plugins without altering their
behavior, prevent duplicate registration, resolve by name/action, and derive
risk metadata from the security policy.
"""

from __future__ import annotations

from typing import Any

import pytest
from archon.capabilities import (
    ActionSpec,
    Capability,
    CapabilityRegistry,
    CapabilityResult,
    PluginCapability,
    RiskLevel,
    build_registry_from_plugin_manager,
)
from archon.core.plugin_manager import AutomationPlugin
from archon.security.permission_manager import PermissionManager

# ─── Test doubles ──────────────────────────────────────────────────────────────


class FakePlugin(AutomationPlugin):
    @property
    def name(self) -> str:
        return "filesystem"

    @property
    def description(self) -> str:
        return "fake filesystem plugin"

    @property
    def version(self) -> str:
        return "0.1"

    def get_capabilities(self) -> list[str]:
        return ["create_folder", "delete"]

    def execute(self, action: str, params: dict[str, Any]) -> Any:
        if action == "boom":
            raise RuntimeError("kaboom")
        return {"success": True, "action": action, "params": params}


class RawReturnPlugin(FakePlugin):
    def execute(self, action: str, params: dict[str, Any]) -> Any:
        return "plain string result"  # no success key


class NativeCap(Capability):
    name = "native"
    description = "a native capability"
    risk = RiskLevel.LOW

    def discover(self) -> list[ActionSpec]:
        return [ActionSpec(name="ping", risk=RiskLevel.LOW)]

    def execute(self, action: str, params: dict[str, Any]) -> CapabilityResult:
        return CapabilityResult.ok("pong")


# ─── Registry ────────────────────────────────────────────────────────────────


def test_register_and_get():
    reg = CapabilityRegistry()
    cap = NativeCap()
    reg.register(cap)
    assert reg.get("native") is cap
    assert "native" in reg
    assert reg.list() == ["native"]


def test_duplicate_registration_raises():
    reg = CapabilityRegistry()
    reg.register(NativeCap())
    with pytest.raises(ValueError):
        reg.register(NativeCap())
    # replace=True is allowed
    reg.register(NativeCap(), replace=True)


def test_unregister():
    reg = CapabilityRegistry()
    reg.register(NativeCap())
    assert reg.unregister("native") is True
    assert reg.unregister("native") is False
    assert reg.get("native") is None


def test_empty_name_rejected():
    reg = CapabilityRegistry()
    cap = NativeCap()
    cap.name = ""
    with pytest.raises(ValueError):
        reg.register(cap)


def test_find_by_action_and_available():
    reg = CapabilityRegistry()
    reg.register(PluginCapability(FakePlugin()))
    assert reg.find_by_action("create_folder") == ["filesystem"]
    assert reg.find_by_action("nonexistent") == []
    assert "filesystem" in reg.available()


def test_route_matches_exact_and_prefix():
    reg = CapabilityRegistry()
    reg.register(PluginCapability(FakePlugin()))  # advertises create_folder, delete
    assert reg.route("create_folder") == ["filesystem"]  # exact
    assert reg.route("create_folder_deep") == ["filesystem"]  # prefix
    assert reg.route("nonexistent") == []


def test_dispatch_returns_raw_result():
    reg = CapabilityRegistry()
    reg.register(PluginCapability(FakePlugin()))
    raw = reg.dispatch("filesystem", "create_folder", {"name": "x"})
    assert raw == {"success": True, "action": "create_folder", "params": {"name": "x"}}


def test_dispatch_unknown_capability_raises():
    reg = CapabilityRegistry()
    with pytest.raises(ValueError, match="not found"):
        reg.dispatch("nope", "create_folder", {})


def test_dispatch_unsupported_action_raises():
    reg = CapabilityRegistry()
    reg.register(PluginCapability(FakePlugin()))
    with pytest.raises(ValueError, match="not supported"):
        reg.dispatch("filesystem", "totally_unknown", {})


def test_dispatch_propagates_plugin_exception():
    plugin = FakePlugin()
    plugin.get_capabilities = lambda: ["boom"]  # type: ignore[method-assign]
    reg = CapabilityRegistry()
    reg.register(PluginCapability(plugin))
    with pytest.raises(RuntimeError, match="kaboom"):
        reg.dispatch("filesystem", "boom", {})


def test_native_invoke_returns_legacy_payload():
    reg = CapabilityRegistry()
    reg.register(NativeCap())
    assert reg.dispatch("native", "ping", {}) == "pong"


def test_describe_includes_actions_and_risk():
    reg = CapabilityRegistry()
    reg.register(NativeCap())
    described = reg.describe()
    assert described["native"]["risk"] == "low"
    assert described["native"]["actions"][0]["name"] == "ping"


# ─── PluginCapability adapter ──────────────────────────────────────────────────


def test_plugin_capability_exposes_actions():
    cap = PluginCapability(FakePlugin())
    assert cap.name == "filesystem"
    assert set(cap.actions()) == {"create_folder", "delete"}


def test_plugin_capability_execute_preserves_success_dict():
    cap = PluginCapability(FakePlugin())
    result = cap.execute("create_folder", {"name": "x"})
    assert result.success is True
    assert result.raw == {"success": True, "action": "create_folder", "params": {"name": "x"}}


def test_plugin_capability_execute_wraps_plain_result():
    cap = PluginCapability(RawReturnPlugin())
    result = cap.execute("create_folder", {})
    assert result.success is True
    assert result.data == "plain string result"


def test_plugin_capability_validate_rejects_unknown_action():
    cap = PluginCapability(FakePlugin())
    result = cap.execute("no_such_action", {})
    assert result.success is False
    assert "Unknown action" in (result.error or "")


def test_plugin_capability_execute_catches_exceptions():
    plugin = FakePlugin()
    plugin.get_capabilities = lambda: ["boom"]  # type: ignore[method-assign]
    cap = PluginCapability(plugin)
    result = cap.execute("boom", {})
    assert result.success is False
    assert "kaboom" in (result.error or "")


def test_risk_derived_from_permission_manager(tmp_path):
    pm = PermissionManager(config_file=str(tmp_path / "perm.json"))
    cap = PluginCapability(FakePlugin(), permission_manager=pm)
    # filesystem/delete maps to FILESYSTEM_DELETE → HIGH
    assert cap.risk_of("delete") is RiskLevel.HIGH
    # filesystem/create_folder maps to FILESYSTEM_WRITE → MODERATE → MEDIUM
    assert cap.risk_of("create_folder") is RiskLevel.MEDIUM


def test_risk_level_maps_from_permission_level():
    assert RiskLevel.from_permission_level("safe") is RiskLevel.LOW
    assert RiskLevel.from_permission_level("critical") is RiskLevel.DESTRUCTIVE
    assert RiskLevel.from_permission_level("unknown") is RiskLevel.MEDIUM


# ─── build_registry_from_plugin_manager ────────────────────────────────────────


class FakePluginManager:
    def __init__(self, plugins):
        self.plugins = {p.name: p for p in plugins}


def test_build_registry_from_plugin_manager(tmp_path):
    pm = PermissionManager(config_file=str(tmp_path / "perm.json"))
    mgr = FakePluginManager([FakePlugin()])
    reg = build_registry_from_plugin_manager(mgr, permission_manager=pm)
    assert reg.get("filesystem") is not None
    # destructive gate: delete is HIGH (allowed), power-style destructive denied by default
    assert reg.check_permission("filesystem", "create_folder", {"name": "x"}) is True
