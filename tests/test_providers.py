"""Tests for the multi-provider AI layer and the empty-file write guard.

Covers:
  * OpenAICompatibleProvider: chat content + tool-call assembly, complete,
    list_models, error surface (all mocked; no network).
  * AnthropicProvider: message conversion (system/tool pairing), response
    parsing back into Ollama-style dicts.
  * provider_factory.build_provider: selection + fallback to Ollama when a
    cloud provider is unreachable.
  * engine._handle_write_file: refuses to write empty/placeholder content and
    reports an honest failure instead of a 0-byte success.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from archon.ai.anthropic_provider import AnthropicProvider
from archon.ai.ollama_integration import AIProviderError
from archon.ai.openai_compat import OpenAICompatibleProvider

# ─── httpx mock helpers ──────────────────────────────────────────────────────


def _response(status_code=200, json_body=None, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    if json_body is None:
        resp.json.side_effect = json.JSONDecodeError("no json", text or "", 0)
    else:
        resp.json.return_value = json_body
    resp.text = text
    return resp


def _client_mock(*, post=None, get=None):
    client = AsyncMock()
    if post is not None:
        client.post = AsyncMock(return_value=post)
    if get is not None:
        client.get = AsyncMock(return_value=get)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=client)


# ─── OpenAI-compatible provider ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_openai_list_models():
    payload = {"data": [{"id": "auto"}, {"id": "fusion"}]}
    with patch("httpx.AsyncClient", _client_mock(get=_response(json_body=payload))):
        p = OpenAICompatibleProvider("http://x/v1", "k", "auto")
        assert await p.list_models() == ["auto", "fusion"]


@pytest.mark.asyncio
async def test_openai_chat_returns_content_and_tool_calls():
    body = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "hi",
                    "tool_calls": [
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {"name": "run", "arguments": '{"x":1}'},
                        }
                    ],
                }
            }
        ],
        "usage": {"completion_tokens": 5, "prompt_tokens": 10},
    }
    with patch("httpx.AsyncClient", _client_mock(post=_response(json_body=body))):
        p = OpenAICompatibleProvider("http://x/v1", "k", "auto")
        stats: dict = {}
        msg = await p.chat(
            [{"role": "user", "content": "hey"}],
            tools=[{"type": "function", "function": {"name": "run"}}],
            on_stats=stats.update,
        )
    assert msg["content"] == "hi"
    assert msg["tool_calls"][0]["function"]["name"] == "run"
    assert stats == {"eval_count": 5, "prompt_eval_count": 10}


@pytest.mark.asyncio
async def test_openai_complete_returns_text():
    body = {"choices": [{"message": {"content": "answer"}}]}
    with patch("httpx.AsyncClient", _client_mock(post=_response(json_body=body))):
        p = OpenAICompatibleProvider("http://x/v1", "k", "auto")
        assert await p.complete([{"role": "user", "content": "q"}]) == "answer"


@pytest.mark.asyncio
async def test_openai_http_error_raises():
    with patch(
        "httpx.AsyncClient", _client_mock(post=_response(status_code=401, text="nope"))
    ):
        p = OpenAICompatibleProvider("http://x/v1", "", "auto")
        with pytest.raises(AIProviderError):
            await p.complete([{"role": "user", "content": "q"}])


def test_openai_accumulate_tool_call_fragments():
    acc: dict = {}
    OpenAICompatibleProvider._accumulate_tool_call(
        acc, {"index": 0, "id": "c1", "function": {"name": "run"}}
    )
    OpenAICompatibleProvider._accumulate_tool_call(
        acc, {"index": 0, "function": {"arguments": '{"a":'}}
    )
    OpenAICompatibleProvider._accumulate_tool_call(
        acc, {"index": 0, "function": {"arguments": "1}"}}
    )
    assert acc[0]["id"] == "c1"
    assert acc[0]["function"]["name"] == "run"
    assert acc[0]["function"]["arguments"] == '{"a":1}'


# ─── Anthropic provider ──────────────────────────────────────────────────────


def test_anthropic_message_conversion_pairs_tool_results():
    p = AnthropicProvider("k", "claude-3-5-sonnet-latest")
    system, conv = p._to_anthropic_messages(
        [
            {"role": "system", "content": "be brief"},
            {"role": "user", "content": "run it"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"id": "t1", "function": {"name": "run", "arguments": '{"x":1}'}}
                ],
            },
            {"role": "tool", "content": "done"},
        ]
    )
    assert system == "be brief"
    # user, assistant(tool_use), user(tool_result)
    assert conv[0]["role"] == "user"
    use_block = conv[1]["content"][0]
    assert use_block["type"] == "tool_use"
    assert use_block["id"] == "t1"
    assert use_block["input"] == {"x": 1}
    result_block = conv[2]["content"][0]
    assert result_block["type"] == "tool_result"
    assert result_block["tool_use_id"] == "t1"


def test_anthropic_response_parsing():
    data = {
        "content": [
            {"type": "text", "text": "hello"},
            {"type": "tool_use", "id": "t9", "name": "run", "input": {"a": 2}},
        ]
    }
    msg = AnthropicProvider._from_anthropic_response(data)
    assert msg["content"] == "hello"
    assert msg["tool_calls"][0]["id"] == "t9"
    assert msg["tool_calls"][0]["function"]["arguments"] == {"a": 2}


@pytest.mark.asyncio
async def test_anthropic_chat_emits_content(monkeypatch):
    body = {
        "content": [{"type": "text", "text": "reply"}],
        "usage": {"input_tokens": 3, "output_tokens": 4},
    }
    with patch("httpx.AsyncClient", _client_mock(post=_response(json_body=body))):
        p = AnthropicProvider("k", "claude-3-5-sonnet-latest")
        tokens: list = []
        stats: dict = {}
        msg = await p.chat(
            [{"role": "user", "content": "hi"}],
            on_token=tokens.append,
            on_stats=stats.update,
        )
    assert msg["content"] == "reply"
    assert tokens == ["reply"]
    assert stats == {"eval_count": 4, "prompt_eval_count": 3}


# ─── provider factory ────────────────────────────────────────────────────────


class _AI:
    provider = "ollama"
    model = ""
    ollama_url = "http://127.0.0.1:11434"
    ollama_model = "qwen3.5:4b"
    timeout = 30
    freellmapi_url = "http://localhost:3001/v1"
    freellmapi_api_key = "key"
    freellmapi_model = "auto"
    openai_url = "https://api.openai.com/v1"
    openai_api_key = ""
    openai_model = "gpt-4o-mini"
    anthropic_url = "https://api.anthropic.com/v1"
    anthropic_api_key = ""
    anthropic_model = "claude-3-5-sonnet-latest"


class _Cfg:
    def __init__(self, provider="ollama"):
        self.ai = _AI()
        self.ai.provider = provider


def test_factory_default_builds_ollama():
    from archon.ai.ollama_integration import OllamaProvider
    from archon.ai.provider_factory import build_provider

    prov = build_provider(_Cfg("ollama"))
    assert isinstance(prov, OllamaProvider)
    assert prov.model == "qwen3.5:4b"


def test_factory_freellmapi_when_reachable():
    from archon.ai.provider_factory import build_provider

    with patch("archon.ai.provider_factory._probe_reachable", return_value=True):
        prov = build_provider(_Cfg("freellmapi"))
    assert isinstance(prov, OpenAICompatibleProvider)
    assert prov.model == "auto"
    assert prov.label == "freellmapi"


def test_factory_falls_back_to_ollama_when_unreachable():
    from archon.ai.ollama_integration import OllamaProvider
    from archon.ai.provider_factory import build_provider

    with patch("archon.ai.provider_factory._probe_reachable", return_value=False):
        prov = build_provider(_Cfg("freellmapi"))
    assert isinstance(prov, OllamaProvider)


def test_factory_anthropic_without_key_falls_back():
    from archon.ai.ollama_integration import OllamaProvider
    from archon.ai.provider_factory import build_provider

    prov = build_provider(_Cfg("anthropic"))
    assert isinstance(prov, OllamaProvider)


# ─── empty-file write guard ──────────────────────────────────────────────────


def _engine():
    from archon.core.engine import Archon

    return Archon(config={})


def test_write_file_refuses_empty_content(tmp_path):
    eng = _engine()
    res = eng._handle_write_file(
        {"file_path": str(tmp_path / "out.txt"), "content": "   "}
    )
    assert res["success"] is False
    assert "content" in res["error"].lower()
    assert not (tmp_path / "out.txt").exists()


def test_write_file_refuses_unresolved_placeholder(tmp_path):
    eng = _engine()
    res = eng._handle_write_file(
        {"file_path": str(tmp_path / "out.txt"), "content": "{{extracted_content}}"}
    )
    assert res["success"] is False
    assert not (tmp_path / "out.txt").exists()


def test_write_file_writes_real_content(tmp_path):
    eng = _engine()
    target = tmp_path / "out.txt"
    res = eng._handle_write_file({"file_path": str(target), "content": "real data"})
    assert res["success"] is True
    assert target.read_text() == "real data"


# ─── adapter content forwarding (empty-file root cause) ──────────────────────


def test_linux_adapter_forwards_content(tmp_path):
    from archon.os_adapters.linux_adapter import LinuxFilesystemAdapter

    adapter = LinuxFilesystemAdapter()
    ok = adapter.execute(
        "create_file",
        {"name": "f.txt", "location": str(tmp_path), "content": "hello"},
    )
    assert ok is True
    assert (tmp_path / "f.txt").read_text() == "hello"


def test_macos_adapter_forwards_content(tmp_path):
    from archon.os_adapters.macos_adapter import MacOSFilesystemAdapter

    adapter = MacOSFilesystemAdapter()
    ok = adapter.execute(
        "create_file",
        {"name": "f.txt", "location": str(tmp_path), "content": "hello"},
    )
    assert ok is True
    assert (tmp_path / "f.txt").read_text() == "hello"
