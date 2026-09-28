"""Tests for the MCP integration (server + local Ollama agent).

These are hermetic: no real Ollama server and no real network. The MCP server is
driven through an in-memory ``fastmcp.Client``, and the agent uses a fake
provider so the tool-calling loop is exercised without a model.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("fastmcp")

from archon.capabilities import RiskLevel  # noqa: E402
from archon.mcp.agent import (  # noqa: E402
    OllamaMCPAgent,
    _parse_tool_call,
    build_agent_system_prompt,
)
from archon.mcp.server import build_mcp_server  # noqa: E402

# ─── fakes ──────────────────────────────────────────────────────────────────


class _FakeCap:
    def __init__(self, risk: RiskLevel) -> None:
        self._risk = risk

    def risk_of(self, action: str) -> RiskLevel:
        return self._risk


class _FakeRegistry:
    def __init__(self) -> None:
        self._caps = {"filesystem": _FakeCap(RiskLevel.LOW)}
        self.dispatched: list[tuple[str, str, dict]] = []
        self.permit = True

    def __contains__(self, name: str) -> bool:
        return name in self._caps

    def get(self, name: str) -> Any:
        return self._caps.get(name)

    def check_permission(self, name, action, params):
        return self.permit

    def dispatch(self, name, action, params):
        self.dispatched.append((name, action, params))
        return {"success": True, "action": action}


class _FakePermMgr:
    @staticmethod
    def is_dangerous_command(cmd: str) -> bool:
        return "rm -rf" in cmd.lower()


class _FakeEngine:
    """Minimal engine surface used by the MCP server and agent."""

    def __init__(self) -> None:
        self.capability_registry = _FakeRegistry()
        self.permission_manager = _FakePermMgr()
        self.executed: list[str] = []

    def describe_capabilities(self) -> dict:
        return {
            "filesystem": {
                "description": "Files and folders",
                "risk": "medium",
                "actions": [{"name": "create_folder", "risk": "medium", "description": ""}],
            }
        }

    def execute(self, command: str) -> dict:
        self.executed.append(command)
        return {"success": True, "command": command, "complexity": "simple"}


class _FakeProvider:
    """Returns a scripted sequence of assistant messages for chat()."""

    def __init__(self, scripted: list[dict]) -> None:
        self._scripted = list(scripted)
        self.model = "fake"
        self.calls: list[dict] = []

    async def chat(
        self,
        messages,
        *,
        tools=None,
        temperature=0.3,
        max_tokens=2048,
        model=None,
        on_token=None,
        on_stats=None,
    ):
        self.calls.append({"messages": list(messages), "tools": tools})
        return self._scripted.pop(0)


def _tool_call(name: str, args: dict) -> dict:
    return {"function": {"name": name, "arguments": args}}


# ─── server ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_server_lists_three_tools():
    from fastmcp import Client

    server = build_mcp_server(_FakeEngine())
    async with Client(server) as c:
        names = {t.name for t in await c.list_tools()}
    assert names == {"list_capabilities", "run_automation", "dispatch_action"}


@pytest.mark.asyncio
async def test_run_automation_calls_engine_execute():
    from fastmcp import Client

    engine = _FakeEngine()
    server = build_mcp_server(engine)
    async with Client(server) as c:
        res = await c.call_tool("run_automation", {"command": "make a folder"})
    assert res.is_error is False
    assert engine.executed == ["make a folder"]
    assert res.data["success"] is True


@pytest.mark.asyncio
async def test_run_automation_rejects_empty_command():
    from fastmcp import Client

    server = build_mcp_server(_FakeEngine())
    async with Client(server) as c:
        res = await c.call_tool("run_automation", {"command": "   "})
    assert res.data["success"] is False


@pytest.mark.asyncio
async def test_dispatch_action_routes_through_registry():
    from fastmcp import Client

    engine = _FakeEngine()
    server = build_mcp_server(engine)
    async with Client(server) as c:
        res = await c.call_tool(
            "dispatch_action",
            {"capability": "filesystem", "action": "create_folder", "params": {"name": "x"}},
        )
    assert res.data["success"] is True
    assert engine.capability_registry.dispatched == [
        ("filesystem", "create_folder", {"name": "x"})
    ]


@pytest.mark.asyncio
async def test_dispatch_action_unknown_capability():
    from fastmcp import Client

    server = build_mcp_server(_FakeEngine())
    async with Client(server) as c:
        res = await c.call_tool(
            "dispatch_action", {"capability": "nope", "action": "x", "params": {}}
        )
    assert res.data["success"] is False
    assert "Unknown capability" in res.data["error"]


@pytest.mark.asyncio
async def test_dispatch_action_permission_denied():
    from fastmcp import Client

    engine = _FakeEngine()
    engine.capability_registry.permit = False
    server = build_mcp_server(engine)
    async with Client(server) as c:
        res = await c.call_tool(
            "dispatch_action",
            {"capability": "filesystem", "action": "create_folder", "params": {}},
        )
    assert res.data["success"] is False
    assert "Permission denied" in res.data["error"]


# ─── agent risk classification ──────────────────────────────────────────────


def _agent() -> OllamaMCPAgent:
    return OllamaMCPAgent(engine=_FakeEngine(), provider=_FakeProvider([]))


def test_classify_run_automation_safe_is_low():
    assert _agent()._classify_risk("run_automation", {"command": "list files"}) is RiskLevel.LOW


def test_classify_run_automation_dangerous_is_destructive():
    a = _agent()
    assert a._classify_risk("run_automation", {"command": "rm -rf /"}) is RiskLevel.DESTRUCTIVE


def test_classify_run_automation_distro_is_high():
    a = _agent()
    assert a._classify_risk("run_automation", {"command": "build an arch iso"}) is RiskLevel.HIGH


def test_classify_dispatch_uses_registry_risk():
    a = _agent()
    risk = a._classify_risk("dispatch_action", {"capability": "filesystem", "action": "x"})
    assert risk is RiskLevel.LOW


def test_classify_list_capabilities_is_low():
    assert _agent()._classify_risk("list_capabilities", {}) is RiskLevel.LOW


def test_build_agent_system_prompt_lists_capabilities():
    prompt = build_agent_system_prompt(_FakeEngine())
    assert "filesystem" in prompt
    assert "run_automation" in prompt
    assert "CUSTOM LINUX" in prompt.upper()


def test_parse_tool_call_handles_json_string_args():
    name, args = _parse_tool_call({"function": {"name": "t", "arguments": '{"a": 1}'}})
    assert name == "t"
    assert args == {"a": 1}


def test_parse_tool_call_handles_bad_string_args():
    _, args = _parse_tool_call({"function": {"name": "t", "arguments": "not json"}})
    assert args == {}


# ─── agent loop ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_agent_runs_tool_then_answers():
    engine = _FakeEngine()
    provider = _FakeProvider(
        [
            {"role": "assistant", "content": "", "tool_calls": [
                _tool_call("run_automation", {"command": "make a folder"})
            ]},
            {"role": "assistant", "content": "Done — folder created."},
        ]
    )
    agent = OllamaMCPAgent(engine=engine, provider=provider, confirmer=lambda *a: True)
    reply = await agent.run("make a folder")
    assert reply == "Done — folder created."
    assert engine.executed == ["make a folder"]
    # A tool-role message with the result was fed back to the model.
    assert any(m.get("role") == "tool" for m in provider.calls[-1]["messages"])


@pytest.mark.asyncio
async def test_agent_rejects_malformed_tool_name():
    """A leaked/XML-mangled tool name must not be invoked; the model gets a
    corrective error and can recover on the next turn."""
    engine = _FakeEngine()
    provider = _FakeProvider(
        [
            {"role": "assistant", "content": "", "tool_calls": [
                _tool_call('run_="parameter name="command', {"command": "x"})
            ]},
            {"role": "assistant", "content": "Recovered."},
        ]
    )
    agent = OllamaMCPAgent(engine=engine, provider=provider, confirmer=lambda *a: True)
    reply = await agent.run("do the thing")
    assert reply == "Recovered."
    # The garbage tool name never reached the engine.
    assert engine.executed == []
    # The model was handed a corrective tool message naming the valid tools.
    tool_msgs = [m for m in provider.calls[-1]["messages"] if m.get("role") == "tool"]
    assert tool_msgs and "Unknown tool" in tool_msgs[-1]["content"]
    assert "run_automation" in tool_msgs[-1]["content"]


@pytest.mark.asyncio
async def test_agent_denies_high_risk_without_confirmer():
    engine = _FakeEngine()
    provider = _FakeProvider(
        [
            {"role": "assistant", "content": "", "tool_calls": [
                _tool_call("run_automation", {"command": "rm -rf /tmp/x"})
            ]},
            {"role": "assistant", "content": "I could not proceed."},
        ]
    )
    # No confirmer => high-risk denied; engine.execute must NOT run.
    agent = OllamaMCPAgent(engine=engine, provider=provider, confirmer=None)
    await agent.run("delete everything")
    assert engine.executed == []
    tool_msgs = [m for m in provider.calls[-1]["messages"] if m.get("role") == "tool"]
    assert tool_msgs and "declined" in json.loads(tool_msgs[-1]["content"])["error"]


@pytest.mark.asyncio
async def test_agent_respects_confirmer_approval():
    engine = _FakeEngine()
    provider = _FakeProvider(
        [
            {"role": "assistant", "content": "", "tool_calls": [
                _tool_call("run_automation", {"command": "build an arch iso"})
            ]},
            {"role": "assistant", "content": "Build started."},
        ]
    )
    seen: list = []
    def confirm(name, args, risk):
        seen.append((name, risk))
        return True
    agent = OllamaMCPAgent(engine=engine, provider=provider, confirmer=confirm)
    await agent.run("build an OS")
    assert engine.executed == ["build an arch iso"]
    assert seen == [("run_automation", RiskLevel.HIGH)]


@pytest.mark.asyncio
async def test_agent_stops_at_round_limit():
    engine = _FakeEngine()
    # Always returns a tool call → never terminates on its own.
    loop_msg = {"role": "assistant", "content": "", "tool_calls": [
        _tool_call("list_capabilities", {})
    ]}
    provider = _FakeProvider([dict(loop_msg) for _ in range(10)])
    agent = OllamaMCPAgent(engine=engine, provider=provider, max_rounds=3)
    reply = await agent.run("loop forever")
    assert "tool-call limit" in reply


# ─── OllamaProvider.chat (mocked httpx) ─────────────────────────────────────


@pytest.mark.asyncio
async def test_ollama_chat_returns_message_with_tool_calls():
    from archon.ai.ollama_integration import OllamaProvider

    body = {"message": {"role": "assistant", "content": "", "tool_calls": [
        {"function": {"name": "run_automation", "arguments": {"command": "x"}}}
    ]}}
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = body
    resp.text = ""

    client = MagicMock()
    client.post = MagicMock()

    async def _post(*a, **k):
        return resp

    client.post = _post
    ctx = MagicMock()

    async def _aenter(*a):
        return client

    async def _aexit(*a):
        return False

    ctx.__aenter__ = _aenter
    ctx.__aexit__ = _aexit
    with patch("httpx.AsyncClient", MagicMock(return_value=ctx)):
        provider = OllamaProvider(model="qwen3.5:9b")
        msg = await provider.chat([{"role": "user", "content": "hi"}], tools=[{"x": 1}])
    assert msg["tool_calls"][0]["function"]["name"] == "run_automation"
