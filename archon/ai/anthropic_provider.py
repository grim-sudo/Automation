"""Anthropic Messages API backend for Archon.

Speaks Anthropic's native ``/v1/messages`` wire format (distinct from the
OpenAI ``/v1/chat/completions`` shape). Translates Archon's OpenAI/Ollama-style
message history and tool schema into Anthropic blocks on the way in, and maps
the ``content`` blocks back into the same Ollama-style ``message`` dict the MCP
agent expects (``content`` plus optional ``tool_calls``) on the way out.

Public surface mirrors the other providers (``is_available``/``list_models``/
``complete``/``chat``); every failure raises :class:`AIProviderError`.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx

from .ollama_integration import AIProviderError

__all__ = ["AnthropicProvider"]

_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider:
    """Async client for the Anthropic Messages API.

    Args:
        api_key:  Anthropic key, sent as the ``x-api-key`` header.
        model:    Default model id (e.g. ``claude-3-5-sonnet-latest``).
        base_url: API root (default ``https://api.anthropic.com/v1``).
        timeout:  Per-request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        base_url: str = "https://api.anthropic.com/v1",
        timeout: float = 120.0,
    ) -> None:
        self.base_url = (base_url or "https://api.anthropic.com/v1").rstrip("/")
        self.api_key = api_key or ""
        self.model = model or "claude-3-5-sonnet-latest"
        self.timeout = float(timeout)
        self.label = "anthropic"

    def _headers(self) -> dict[str, str]:
        return {
            "content-type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
        }

    # ── availability ───────────────────────────────────────────────────────────

    async def is_available(self) -> bool:
        """Return ``True`` when a key is set and a trivial request is accepted.

        Anthropic has no public unauthenticated ``/models`` list, so a missing
        key is treated as unavailable without a network round-trip.
        """
        if not self.api_key:
            return False
        try:
            await self.list_models()
            return True
        except AIProviderError:
            return False

    async def list_models(self) -> list[str]:
        """Return model ids from ``/models`` (requires a valid key)."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.base_url}/models", headers=self._headers())
        except httpx.TimeoutException as exc:
            raise AIProviderError(
                "anthropic timed out listing models", model=self.model
            ) from exc
        except httpx.HTTPError as exc:
            raise AIProviderError(
                f"anthropic not reachable at {self.base_url}: {exc}", model=self.model
            ) from exc
        if resp.status_code >= 400:
            raise AIProviderError(
                f"anthropic returned HTTP {resp.status_code} for /models: {resp.text[:200]}",
                status_code=resp.status_code,
                model=self.model,
            )
        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            raise AIProviderError(
                f"anthropic returned malformed JSON from /models: {resp.text[:200]}",
                model=self.model,
            ) from exc
        return [m.get("id", "") for m in data.get("data", []) if m.get("id")]

    # ── completion ───────────────────────────────────────────────────────────

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        model: str | None = None,
        timeout: float | None = None,
    ) -> str:
        """Return a non-streaming completion as plain text."""
        msg = await self.chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
            _timeout=timeout,
        )
        return msg.get("content", "") or ""

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        model: str | None = None,
        on_token: Callable[[str], None] | None = None,
        on_stats: Callable[[dict[str, Any]], None] | None = None,
        _timeout: float | None = None,
    ) -> dict[str, Any]:
        """Return the assistant ``message`` dict (Ollama-style).

        ponytail: non-streaming only. Anthropic's SSE event stream (message/
        content_block deltas) is materially more involved than OpenAI's; since
        Anthropic is an opt-in, un-keyed path here and the TUI already shows an
        elapsed working indicator, the whole reply is emitted to ``on_token``
        once on completion. Upgrade path: parse ``/v1/messages`` SSE
        (``content_block_delta`` → ``text_delta`` / ``input_json_delta``).
        """
        used_model = model or self.model
        used_timeout = self.timeout if _timeout is None else float(_timeout)
        system, conv = self._to_anthropic_messages(messages)
        payload: dict[str, Any] = {
            "model": used_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": conv,
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = self._to_anthropic_tools(tools)

        data = await self._post_json("/messages", payload, used_model, used_timeout)
        message = self._from_anthropic_response(data)
        if on_token is not None and message.get("content"):
            on_token(message["content"])
        if on_stats is not None and isinstance(data.get("usage"), dict):
            usage = data["usage"]
            stats: dict[str, Any] = {}
            if isinstance(usage.get("output_tokens"), int):
                stats["eval_count"] = usage["output_tokens"]
            if isinstance(usage.get("input_tokens"), int):
                stats["prompt_eval_count"] = usage["input_tokens"]
            on_stats(stats)
        return message

    # ── conversion helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _to_anthropic_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """OpenAI function-tool schema → Anthropic ``tools`` schema."""
        out: list[dict[str, Any]] = []
        for tool in tools:
            fn = tool.get("function", tool)
            out.append(
                {
                    "name": fn.get("name", ""),
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters")
                    or {"type": "object", "properties": {}},
                }
            )
        return out

    def _to_anthropic_messages(
        self, messages: list[dict[str, Any]]
    ) -> tuple[str, list[dict[str, Any]]]:
        """Translate an OpenAI/Ollama-style history into (system, messages).

        ``role: system`` messages are concatenated into the top-level system
        prompt. Assistant ``tool_calls`` become ``tool_use`` blocks (carrying the
        id we returned), and the following ``role: tool`` results become
        ``tool_result`` blocks paired to those ids in order.
        """
        system_parts: list[str] = []
        out: list[dict[str, Any]] = []
        pending_tool_ids: list[str] = []

        for msg in messages:
            role = msg.get("role")
            if role == "system":
                if msg.get("content"):
                    system_parts.append(str(msg["content"]))
                continue
            if role == "user":
                out.append({"role": "user", "content": str(msg.get("content", ""))})
                pending_tool_ids = []
                continue
            if role == "assistant":
                blocks: list[dict[str, Any]] = []
                if msg.get("content"):
                    blocks.append({"type": "text", "text": str(msg["content"])})
                pending_tool_ids = []
                for i, call in enumerate(msg.get("tool_calls") or []):
                    fn = call.get("function", {}) if isinstance(call, dict) else {}
                    tid = call.get("id") or f"call_{len(out)}_{i}"
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args) if args.strip() else {}
                        except json.JSONDecodeError:
                            args = {}
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": tid,
                            "name": fn.get("name", ""),
                            "input": args if isinstance(args, dict) else {},
                        }
                    )
                    pending_tool_ids.append(tid)
                out.append({"role": "assistant", "content": blocks or ""})
                continue
            if role == "tool":
                tid = pending_tool_ids.pop(0) if pending_tool_ids else f"call_{len(out)}"
                block = {
                    "type": "tool_result",
                    "tool_use_id": tid,
                    "content": str(msg.get("content", "")),
                }
                # Anthropic wants tool_result blocks in a user turn; merge
                # consecutive results into the same user message.
                if out and out[-1]["role"] == "user" and isinstance(
                    out[-1]["content"], list
                ):
                    out[-1]["content"].append(block)
                else:
                    out.append({"role": "user", "content": [block]})
                continue
        return "\n\n".join(system_parts), out

    @staticmethod
    def _from_anthropic_response(data: dict[str, Any]) -> dict[str, Any]:
        """Anthropic response ``content`` blocks → Ollama-style message dict."""
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        for block in data.get("content") or []:
            btype = block.get("type")
            if btype == "text":
                text_parts.append(block.get("text", ""))
            elif btype == "tool_use":
                tool_calls.append(
                    {
                        "id": block.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": block.get("name", ""),
                            "arguments": block.get("input", {}) or {},
                        },
                    }
                )
        out: dict[str, Any] = {"role": "assistant", "content": "".join(text_parts)}
        if tool_calls:
            out["tool_calls"] = tool_calls
        return out

    # ── internal ───────────────────────────────────────────────────────────────

    async def _post_json(
        self, path: str, payload: dict[str, Any], used_model: str, timeout: float
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{self.base_url}{path}", headers=self._headers(), json=payload
                )
        except httpx.TimeoutException as exc:
            raise AIProviderError(
                f"anthropic request timed out after {timeout}s", model=used_model
            ) from exc
        except httpx.HTTPError as exc:
            raise AIProviderError(
                f"anthropic not reachable at {self.base_url}: {exc}", model=used_model
            ) from exc
        if resp.status_code >= 400:
            raise AIProviderError(
                f"anthropic returned HTTP {resp.status_code}: {resp.text[:200]}",
                status_code=resp.status_code,
                model=used_model,
            )
        try:
            return resp.json()
        except json.JSONDecodeError as exc:
            raise AIProviderError(
                f"anthropic returned malformed JSON: {resp.text[:200]}", model=used_model
            ) from exc
