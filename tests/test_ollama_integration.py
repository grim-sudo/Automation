"""Tests for the local Ollama backend (ollama_integration.py).

Mocks httpx to avoid a real Ollama server. Covers the required error modes:
server unavailable, model unavailable, timeout, malformed response, and
inference errors — plus successful completion, streaming, and model listing.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from archon.ai.ollama_integration import AIProviderError, OllamaProvider

# ─── httpx mock helpers ────────────────────────────────────────────────────


def _response(status_code: int = 200, json_body=None, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    if json_body is None:
        resp.json.side_effect = json.JSONDecodeError("no json", text or "", 0)
    else:
        resp.json.return_value = json_body
    resp.text = text
    return resp


def _client_mock(*, post=None, get=None) -> MagicMock:
    client = AsyncMock()
    if post is not None:
        client.post = AsyncMock(**post) if isinstance(post, dict) else AsyncMock(return_value=post)
    if get is not None:
        client.get = AsyncMock(return_value=get)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=client)


# ─── list_models / availability ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_models_returns_names():
    payload = {"models": [{"name": "qwen3.5:9b"}, {"name": "llama3"}]}
    with patch("httpx.AsyncClient", _client_mock(get=_response(json_body=payload))):
        provider = OllamaProvider(model="qwen3.5:9b")
        assert await provider.list_models() == ["qwen3.5:9b", "llama3"]


@pytest.mark.asyncio
async def test_is_available_true_when_server_responds():
    with patch("httpx.AsyncClient", _client_mock(get=_response(json_body={"models": []}))):
        assert await OllamaProvider().is_available() is True


@pytest.mark.asyncio
async def test_is_available_false_when_unreachable():
    client = AsyncMock()
    client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    with patch("httpx.AsyncClient", MagicMock(return_value=client)):
        assert await OllamaProvider().is_available() is False


# ─── complete ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_complete_extracts_message_content():
    body = {"message": {"role": "assistant", "content": "hello world"}, "done": True}
    with patch("httpx.AsyncClient", _client_mock(post=_response(json_body=body))):
        provider = OllamaProvider(model="qwen3.5:9b")
        out = await provider.complete([{"role": "user", "content": "hi"}])
        assert out == "hello world"


@pytest.mark.asyncio
async def test_complete_model_unavailable_raises_404():
    resp = _response(status_code=404, text="model not found")
    with patch("httpx.AsyncClient", _client_mock(post=resp)):
        provider = OllamaProvider(model="missing:1b")
        with pytest.raises(AIProviderError) as exc:
            await provider.complete([{"role": "user", "content": "hi"}])
        assert exc.value.status_code == 404
        assert "ollama pull" in str(exc.value)


@pytest.mark.asyncio
async def test_complete_timeout_raises():
    client = AsyncMock()
    client.post = AsyncMock(side_effect=httpx.TimeoutException("slow"))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    with patch("httpx.AsyncClient", MagicMock(return_value=client)):
        with pytest.raises(AIProviderError, match="timed out"):
            await OllamaProvider().complete([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_complete_unreachable_raises():
    client = AsyncMock()
    client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    with patch("httpx.AsyncClient", MagicMock(return_value=client)):
        with pytest.raises(AIProviderError, match="not reachable"):
            await OllamaProvider().complete([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_complete_malformed_json_raises():
    with patch("httpx.AsyncClient", _client_mock(post=_response(text="<html>oops"))):
        with pytest.raises(AIProviderError, match="malformed JSON"):
            await OllamaProvider().complete([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_complete_inference_error_raises():
    body = {"error": "out of memory"}
    with patch("httpx.AsyncClient", _client_mock(post=_response(json_body=body))):
        with pytest.raises(AIProviderError, match="inference error"):
            await OllamaProvider().complete([{"role": "user", "content": "hi"}])


# ─── stream ──────────────────────────────────────────────────────────────


class _StreamResponse:
    def __init__(self, lines, status_code=200):
        self._lines = lines
        self.status_code = status_code

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    async def aread(self):
        return b""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _stream_client(stream_resp) -> MagicMock:
    client = AsyncMock()
    client.stream = MagicMock(return_value=stream_resp)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=client)


@pytest.mark.asyncio
async def test_stream_yields_content_chunks():
    lines = [
        json.dumps({"message": {"content": "he"}, "done": False}),
        json.dumps({"message": {"content": "llo"}, "done": False}),
        json.dumps({"message": {"content": ""}, "done": True}),
    ]
    with patch("httpx.AsyncClient", _stream_client(_StreamResponse(lines))):
        provider = OllamaProvider(model="qwen3.5:9b")
        chunks = [c async for c in provider.stream([{"role": "user", "content": "hi"}])]
        assert "".join(chunks) == "hello"


# ─── facade wiring (OllamaAutomationAI) ──────────────────────────────────────


def test_facade_defaults_to_ollama_provider():
    """The main AI facade uses the local Ollama backend when provider=ollama.

    Forces the ollama provider so the test is deterministic regardless of the
    ambient ``.env`` (which may select a cloud provider like freellmapi).
    """
    from archon.ai.automation_ai import OllamaAutomationAI
    from archon.config import get_config

    cfg = get_config()
    with patch.object(cfg.ai, "provider", "ollama"), patch.object(
        OllamaProvider, "is_available", AsyncMock(return_value=True)
    ), patch.object(
        OllamaProvider, "list_models", AsyncMock(return_value=["qwen3.5:9b"])
    ):
        ai = OllamaAutomationAI()
    assert ai._ollama is not None
    # Model name comes from config (env: OLLAMA_MODEL), not a hardcoded literal,
    # so this stays correct whatever local model the environment selects.
    cfg = get_config()
    assert ai._model_name == (cfg.ai.model or cfg.ai.ollama_model)
    status = ai.get_ai_status()
    assert status["provider"] == "Ollama"


def test_facade_call_routes_through_ollama():
    """analyze/_call must reach the Ollama provider."""
    from archon.ai.automation_ai import OllamaAutomationAI
    from archon.config import get_config

    cfg = get_config()
    with patch.object(cfg.ai, "provider", "ollama"), patch.object(
        OllamaProvider, "is_available", AsyncMock(return_value=True)
    ), patch.object(
        OllamaProvider, "list_models", AsyncMock(return_value=["qwen3.5:9b"])
    ):
        ai = OllamaAutomationAI()

    captured = {}

    async def fake_complete(messages, **kwargs):
        captured["messages"] = messages
        captured["kwargs"] = kwargs
        return '{"intent": "test", "confidence": 0.9, "steps": []}'

    with patch.object(ai._ollama, "complete", side_effect=fake_complete):
        reply = ai.converse("hello there")
    assert reply
    assert captured["messages"][-1]["content"] == "hello there"

