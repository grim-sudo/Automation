"""FastMCP server exposing Archon's capabilities as MCP tools.

The server wraps a single :class:`~archon.core.engine.Archon` instance and
publishes three tools:

* ``list_capabilities`` — the live capability catalog (name → actions → risk),
  so any MCP client (or a local model) can discover what Archon can do.
* ``run_automation`` — the primary entry point. Runs a natural-language command
  through :meth:`Archon.execute`, which reaches *every* capability including the
  custom-OS / distro builder. All of the engine's permission checks apply.
* ``dispatch_action`` — a precise, structured call routed through the capability
  registry for when the exact ``capability``/``action``/``params`` are known.

Security note: the tools inherit the engine's ``PermissionManager`` gating, but
the server itself does not add per-call human confirmation — that lives in the
local agent loop (:mod:`archon.mcp.agent`). Only expose ``archon mcp serve`` to
trusted MCP clients; an untrusted client could invoke high-risk actions subject
only to the engine's own permission rules.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from . import require_fastmcp


def build_mcp_server(engine: Any = None, *, safe_mode: bool = False) -> Any:
    """Build a :class:`fastmcp.FastMCP` server bound to an Archon engine.

    Args:
        engine:    An existing Archon engine, or ``None`` to construct one.
        safe_mode: Passed through when constructing a new engine.

    Returns:
        A configured ``FastMCP`` instance ready to ``run()`` or connect to
        in-memory via a ``fastmcp.Client``.
    """
    require_fastmcp()
    from fastmcp import FastMCP

    if engine is None:
        from ..core.engine import Archon

        engine = Archon(config={"safe_mode": safe_mode})

    mcp = FastMCP(
        name="archon",
        instructions=(
            "Archon controls this machine: filesystem, processes, GUI, network, "
            "system settings, project/devops generation, package management, web "
            "scraping, and building custom Linux operating systems (ISOs). Use "
            "run_automation for most tasks; it accepts plain natural language and "
            "reaches every capability, including the OS builder. Use "
            "dispatch_action when you know the exact capability and action. Call "
            "list_capabilities to discover what is available."
        ),
    )

    @mcp.tool(
        description=(
            "List every Archon capability with its actions and risk level. "
            "Returns a mapping of capability name -> {description, risk, actions}."
        )
    )
    def list_capabilities() -> dict[str, Any]:
        return engine.describe_capabilities()

    @mcp.tool(
        description=(
            "Run a natural-language automation command through Archon. This is "
            "the primary tool and reaches every capability, including creating "
            "files/folders, running projects, package installs, web scraping, and "
            "building a custom Linux OS ISO (e.g. 'build a minimal Arch ISO with "
            "python and git'). Returns the structured execution result."
        )
    )
    def run_automation(command: str) -> dict[str, Any]:
        """Execute ``command`` and return Archon's result dict."""
        if not command or not command.strip():
            return {"success": False, "error": "command must be a non-empty string"}
        logger.info("MCP run_automation: {}", command)
        return engine.execute(command)

    @mcp.tool(
        description=(
            "Invoke a specific capability action directly. Prefer this when the "
            "exact capability, action, and params are known (discover them with "
            "list_capabilities). params is a JSON object of action arguments."
        )
    )
    def dispatch_action(
        capability: str,
        action: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Route ``action`` on ``capability`` through the registry."""
        registry = engine.capability_registry
        if capability not in registry:
            return {
                "success": False,
                "error": f"Unknown capability '{capability}'. Call list_capabilities.",
            }
        if not registry.check_permission(capability, action, params or {}):
            return {
                "success": False,
                "error": (
                    f"Permission denied for {capability}.{action} by the "
                    "engine's permission policy."
                ),
            }
        try:
            result = registry.dispatch(capability, action, params or {})
        except ValueError as exc:
            return {"success": False, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001 - surface, never crash the server
            logger.warning("MCP dispatch_action failed: {}", exc)
            return {"success": False, "error": f"Execution error: {exc}"}
        if isinstance(result, dict):
            return result
        return {"success": True, "result": result}

    return mcp
