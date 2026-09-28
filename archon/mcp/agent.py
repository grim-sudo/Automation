"""Local Ollama agent that drives Archon's MCP tools.

Wires a local Ollama model (default ``qwen3.5:9b``) to the Archon MCP server
(:func:`archon.mcp.server.build_mcp_server`) with a tool-calling loop:

1. Build a system prompt from the live capability catalog so the model knows
   exactly what it can do — including the custom-OS builder.
2. List the server's MCP tools and hand them to Ollama as function tools.
3. Loop: let the model call tools, execute each through an in-memory MCP client,
   feed results back, and stop when the model returns a plain answer.

Safety: low/medium-risk actions run automatically; HIGH/DESTRUCTIVE actions
(deletes, process kills, system settings, OS builds) pause for explicit human
confirmation via an injected ``confirmer``. With no confirmer, high-risk calls
are denied — the model never gets unrestricted execution, and it never reaches a
raw shell: every action goes through Archon's capability registry and permission
policy.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from loguru import logger

from ..capabilities import RiskLevel
from . import require_fastmcp
from .server import build_mcp_server

# Distro/OS build intent words for classifying free-form run_automation commands.
_DISTRO_HINTS = ("build", "distro", "iso", "operating system", "linux image", "custom os")

# Tool names whose blast radius is always high regardless of arguments.
_ALWAYS_HIGH_TOOLS = frozenset({"build_distro"})

ConfirmFn = Callable[[str, dict[str, Any], RiskLevel], bool]


def build_agent_system_prompt(engine: Any) -> str:
    """Compose the agent system prompt from the live capability catalog.

    Enumerating capabilities dynamically keeps the prompt in step with whatever
    plugins are actually loaded, rather than drifting against a hardcoded list.
    """
    catalog = engine.describe_capabilities()
    lines: list[str] = []
    for name in sorted(catalog):
        meta = catalog[name]
        actions = ", ".join(a["name"] for a in meta.get("actions", [])[:14])
        desc = (meta.get("description") or "").strip()
        lines.append(f"- {name} (risk={meta.get('risk', 'medium')}): {desc}")
        if actions:
            lines.append(f"    actions: {actions}")
    catalog_text = "\n".join(lines) if lines else "(no capabilities registered)"

    return (
        "You are Archon, an autonomous OS automation agent with full control of "
        "this machine. You act by calling tools; you never invent results.\n\n"
        "You can operate the filesystem, processes, GUI, network, system "
        "settings, generate projects and DevOps scaffolding, manage packages, "
        "scrape the web, and BUILD CUSTOM LINUX OPERATING SYSTEMS (bootable "
        "ISOs).\n\n"
        "TOOLS:\n"
        "- run_automation(command): primary tool. Give it a plain natural-"
        "language instruction; it reaches every capability, including the OS "
        "builder (e.g. \"build a minimal Arch ISO with python and git\"). Prefer "
        "this for most requests.\n"
        "- dispatch_action(capability, action, params): a precise structured "
        "call when you know the exact capability and action.\n"
        "- list_capabilities(): discover available capabilities and actions.\n\n"
        "CAPABILITIES CURRENTLY LOADED:\n"
        f"{catalog_text}\n\n"
        "RULES:\n"
        "- Choose the smallest tool call that accomplishes the task.\n"
        "- High-risk or destructive actions (deleting data, killing processes, "
        "changing system settings, building an OS which needs root) require human "
        "confirmation, handled by the harness — proceed and let it gate.\n"
        "- After tools return, summarise what actually happened in plain text. "
        "If a tool reports success=false, report the real error; do not pretend "
        "it worked.\n"
        "- When the task is done, reply with a short plain-text summary and no "
        "further tool calls."
    )


def _default_provider() -> Any:
    """Build the configured chat provider (Ollama by default) from config."""
    from ..ai.provider_factory import build_provider

    return build_provider()


class OllamaMCPAgent:
    """Tool-calling loop connecting a local Ollama model to Archon's MCP tools.

    Args:
        engine:     An Archon engine, or ``None`` to build one.
        provider:   An ``OllamaProvider``, or ``None`` to build from config.
        confirmer:  Called for HIGH/DESTRUCTIVE actions as
            ``confirmer(tool_name, args, risk) -> bool``. ``None`` denies them.
        max_rounds: Cap on tool-call rounds per :meth:`run` to bound runaway
            loops.
    """

    def __init__(
        self,
        engine: Any = None,
        provider: Any = None,
        *,
        confirmer: ConfirmFn | None = None,
        on_event: Callable[[dict[str, Any]], None] | None = None,
        max_rounds: int = 8,
    ) -> None:
        require_fastmcp()
        if engine is None:
            from ..core.engine import Archon

            engine = Archon(config={})
        self.engine = engine
        self.server = build_mcp_server(engine)
        self.provider = provider or _default_provider()
        self.confirmer = confirmer
        # Optional UI sink for *real* execution events (tool start/ok/error).
        # Kept primitive (plain dicts) so the agent never imports the UI layer;
        # the presentation layer adapts these into its own event model.
        self.on_event = on_event
        self.max_rounds = max_rounds
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": build_agent_system_prompt(engine)}
        ]

    def _emit(self, **event: Any) -> None:
        """Fire a UI event, swallowing sink errors so rendering can't break a run."""
        if self.on_event is None:
            return
        try:
            self.on_event(event)
        except Exception as exc:  # noqa: BLE001 - a broken sink must not kill the agent
            logger.debug("on_event sink raised: {}", exc)

    async def run(
        self,
        user_message: str,
        *,
        on_token: Callable[[str], None] | None = None,
        on_stats: Callable[[dict[str, Any]], None] | None = None,
    ) -> str:
        """Process one user message, running tools until the model answers.

        Args:
            user_message: The user's request.
            on_token:     Optional sink for streamed reply fragments. When set,
                          each model turn streams; intermediate turns that end
                          in tool calls emit little/no text, and the UI clears
                          any preliminary text on the ``EXECUTING`` phase event.
            on_stats:     Optional sink for real per-turn generation metrics.

        Returns:
            The model's final plain-text reply.
        """
        from fastmcp import Client

        self.messages.append({"role": "user", "content": user_message})
        async with Client(self.server) as client:
            tools = await self._ollama_tools(client)
            valid_tools = {
                t["function"]["name"] for t in tools if t.get("function", {}).get("name")
            }
            for _ in range(self.max_rounds):
                message = await self.provider.chat(
                    self.messages,
                    tools=tools,
                    max_tokens=2048,
                    on_token=on_token,
                    on_stats=on_stats,
                )
                self.messages.append(message)
                tool_calls = message.get("tool_calls") or []
                if not tool_calls:
                    return message.get("content", "") or "(no response)"
                self._emit(kind="phase", phase="EXECUTING")
                for call in tool_calls:
                    name, args = _parse_tool_call(call)
                    if name not in valid_tools:
                        # Some models (esp. via aggregating proxies) leak
                        # malformed or XML-style tool calls whose "name" is a
                        # broken fragment. Don't invoke garbage against MCP —
                        # hand the model a corrective error so it retries with a
                        # real tool instead of surfacing an opaque failure.
                        err = (
                            f"Unknown tool {name!r}. Valid tools: "
                            f"{', '.join(sorted(valid_tools))}. "
                            "Call one of these with correct JSON arguments."
                        )
                        logger.warning("MCP agent: rejected unknown tool {!r}", name)
                        self._emit(kind="tool_error", name=name or "(empty)", error=err)
                        self.messages.append(
                            {
                                "role": "tool",
                                "tool_name": name or "unknown",
                                "content": json.dumps({"success": False, "error": err}),
                            }
                        )
                        continue
                    result = await self._invoke(client, name, args)
                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_name": name,
                            "content": json.dumps(result, default=str)[:8000],
                        }
                    )
        return "Stopped after reaching the tool-call limit without a final answer."

    # ── internals ────────────────────────────────────────────────────────────

    async def _ollama_tools(self, client: Any) -> list[dict[str, Any]]:
        """Translate MCP tool definitions into Ollama's function-tool schema."""
        out: list[dict[str, Any]] = []
        for tool in await client.list_tools():
            schema = getattr(tool, "input_schema", None) or getattr(
                tool, "inputSchema", None
            )
            out.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": schema or {"type": "object", "properties": {}},
                    },
                }
            )
        return out

    async def _invoke(
        self, client: Any, name: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Confirm (if risky) then execute a single tool call via MCP."""
        risk = self._classify_risk(name, args)
        self._emit(kind="tool_start", name=name, args=args)
        if risk in (RiskLevel.HIGH, RiskLevel.DESTRUCTIVE) and not self._confirm(
            name, args, risk
        ):
            logger.info("MCP agent: {} action {} declined", risk.value, name)
            self._emit(kind="tool_error", name=name, error="declined by user")
            return {
                "success": False,
                "error": f"User declined the {risk.value}-risk action '{name}'.",
            }
        try:
            res = await client.call_tool(name, args, raise_on_error=False)
        except Exception as exc:  # noqa: BLE001 - report, keep the loop alive
            logger.warning("MCP agent: tool {} raised: {}", name, exc)
            self._emit(kind="tool_error", name=name, error=f"Tool call failed: {exc}")
            return {"success": False, "error": f"Tool call failed: {exc}"}
        if getattr(res, "is_error", False):
            err = str(getattr(res, "data", res))
            self._emit(kind="tool_error", name=name, error=err)
            return {"success": False, "error": err}
        data = getattr(res, "data", None)
        self._emit(kind="tool_ok", name=name)
        return data if data is not None else {"success": True}

    def _confirm(self, name: str, args: dict[str, Any], risk: RiskLevel) -> bool:
        """Ask the injected confirmer; deny by default when none is set."""
        if self.confirmer is None:
            return False
        return bool(self.confirmer(name, args, risk))

    def _classify_risk(self, name: str, args: dict[str, Any]) -> RiskLevel:
        """Best-effort risk for a tool call, used to decide on confirmation."""
        if name in _ALWAYS_HIGH_TOOLS:
            return RiskLevel.HIGH
        if name == "dispatch_action":
            cap = self.engine.capability_registry.get(args.get("capability", ""))
            if cap is not None:
                return cap.risk_of(args.get("action", ""))
            return RiskLevel.MEDIUM
        if name == "run_automation":
            command = str(args.get("command", ""))
            if self.engine.permission_manager.is_dangerous_command(command):
                return RiskLevel.DESTRUCTIVE
            lowered = command.lower()
            if any(hint in lowered for hint in _DISTRO_HINTS):
                return RiskLevel.HIGH
            # Everything else is gated by the engine's own permission checks.
            return RiskLevel.LOW
        # list_capabilities and other read-only tools.
        return RiskLevel.LOW


def _parse_tool_call(call: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Extract ``(name, args)`` from an Ollama tool_call, tolerating strings."""
    fn = call.get("function", {}) if isinstance(call, dict) else {}
    name = fn.get("name", "")
    args = fn.get("arguments", {})
    if isinstance(args, str):
        try:
            args = json.loads(args) if args.strip() else {}
        except json.JSONDecodeError:
            args = {}
    return name, args if isinstance(args, dict) else {}


__all__ = ["OllamaMCPAgent", "build_agent_system_prompt"]
