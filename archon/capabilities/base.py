"""Capability abstraction for Archon.

A *capability* is a named unit of things Archon can do (filesystem, git,
docker, n8n, …).  It is deliberately close in shape to the existing
``AutomationPlugin`` ABC so that current plugins adapt with a thin wrapper
(:mod:`archon.capabilities.plugin_adapter`) rather than a rewrite.

This module is additive: importing it changes no existing behavior.  Nothing
in the legacy execution path depends on it yet — it is the foundation the
capability router / registry build on.

Design notes
------------
* Capabilities do **not** know about the LLM.  They receive a resolved
  ``(action, params)`` and return a structured :class:`CapabilityResult`.
* Risk metadata lets the policy layer decide when to require approval.  It
  intentionally mirrors :class:`archon.security.permission_manager.PermissionLevel`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(Enum):
    """How dangerous an action is.  Mirrors the security PermissionLevel."""

    LOW = "low"  # read-only / non-destructive
    MEDIUM = "medium"  # create files, start processes
    HIGH = "high"  # delete, terminate, system changes
    DESTRUCTIVE = "destructive"  # shutdown, format, kernel/registry changes

    @classmethod
    def from_permission_level(cls, level: Any) -> RiskLevel:
        """Map a security ``PermissionLevel`` (or its ``.value``) to a RiskLevel."""
        value = getattr(level, "value", level)
        return {
            "safe": cls.LOW,
            "moderate": cls.MEDIUM,
            "high": cls.HIGH,
            "critical": cls.DESTRUCTIVE,
        }.get(str(value).lower(), cls.MEDIUM)


@dataclass
class CapabilityResult:
    """Structured result of a capability action.

    ``raw`` preserves whatever the underlying implementation returned so the
    adapter layer never loses information during migration.
    """

    success: bool
    data: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    raw: Any = None

    @classmethod
    def ok(cls, data: Any = None, **metadata: Any) -> CapabilityResult:
        return cls(success=True, data=data, metadata=metadata, raw=data)

    @classmethod
    def fail(cls, error: str, **metadata: Any) -> CapabilityResult:
        return cls(success=False, error=error, metadata=metadata)


@dataclass
class ActionSpec:
    """Metadata describing a single action a capability exposes."""

    name: str
    risk: RiskLevel = RiskLevel.MEDIUM
    description: str = ""
    requires_approval: bool = False


class Capability(ABC):
    """Base class for everything the agent can invoke.

    Concrete capabilities may be native (Archon code), plugin-backed (an
    existing :class:`AutomationPlugin` via an adapter), or remote (an MCP tool
    via a gateway).  The agent core only ever sees this interface:
    ``capability -> action -> params -> CapabilityResult``.
    """

    #: Stable identifier used for registration/lookup, e.g. ``"filesystem"``.
    name: str = ""
    #: Human-readable summary shown to the agent/user.
    description: str = ""
    #: Baseline risk for the capability; individual actions may override.
    risk: RiskLevel = RiskLevel.MEDIUM

    @abstractmethod
    def discover(self) -> list[ActionSpec]:
        """Return the actions this capability currently supports."""

    def actions(self) -> list[str]:
        """Convenience: just the action names from :meth:`discover`."""
        return [spec.name for spec in self.discover()]

    def validate(self, action: str, params: dict[str, Any]) -> tuple[bool, str | None]:
        """Cheap pre-execution check.  Override for parameter validation.

        Default: the action must be one this capability advertises.
        """
        if action not in self.actions():
            return False, f"Unknown action '{action}' for capability '{self.name}'"
        return True, None

    @abstractmethod
    def execute(self, action: str, params: dict[str, Any]) -> CapabilityResult:
        """Run ``action`` with ``params`` and return a structured result."""

    def invoke(self, action: str, params: dict[str, Any]) -> Any:
        """Run ``action`` and return the *legacy raw result*.

        This is the shape the engine's dispatch has always returned (typically a
        ``{"success": bool, ...}`` dict).  It exists so the
        :class:`~archon.capabilities.registry.CapabilityRegistry` can act as the
        execution router without callers having to unwrap
        :class:`CapabilityResult`.  Native capabilities return their result dict;
        plugin-backed ones override this to preserve raise-on-failure semantics.
        """
        result = self.execute(action, params)
        if result.raw is not None:
            return result.raw
        if result.data is not None:
            return result.data
        return {"success": result.success, "error": result.error}

    def risk_of(self, action: str) -> RiskLevel:
        """Risk of a specific action, falling back to the capability baseline."""
        for spec in self.discover():
            if spec.name == action:
                return spec.risk
        return self.risk

    def health(self) -> dict[str, Any]:
        """Lightweight availability/status probe.  Override where meaningful."""
        return {"available": True, "name": self.name}
