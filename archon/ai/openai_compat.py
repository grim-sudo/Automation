"""OpenAI-compatible chat backend for Archon.

Speaks the OpenAI ``/v1/chat/completions`` and ``/v1/models`` wire format, which
covers FreeLLMAPI (a local OpenAI-compatible router), OpenAI itself, and
OpenRouter. One class, parameterised by ``base_url`` + ``api_key`` + ``model``,
so a new OpenAI-compatible endpoint never needs a new class.

The public surface mirrors :class:`~archon.ai.ollama_integration.OllamaProvider`
(``is_available``/``list_models``/``complete``/``chat``) and returns the same
Ollama-style ``message`` dict from :meth:`chat` (``content`` plus optional
``tool_calls``) so the MCP agent loop and the AI facade work unchanged. Every
failure mode raises :class:`AIProviderError`.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx

from .ollama_integration import AIProviderError

__all__ = ["OpenAICompatibleProvider"]


def _extract_openai_stats(usage: dict[str, Any]) -> dict[str, Any]:
    """Map an OpenAI ``usage`` block onto Archon's stats shape.

    Only fields the server actually reported are returned; a tokens/sec figure
    is not derivable from the OpenAI usage block (no timing), so it is omitted
    and the UI shows ``N/A`` rather than a fabricated number.
    """
    stats: dict[str, Any] = {}
    completion = usage.get("completion_tokens")
    prompt = usage.get("prompt_tokens")
    if isinstance(completion, int):
        stats["eval_count"] = completion
    if isinstance(prompt, int):
        stats["prompt_eval_count"] = prompt
    return stats


class OpenAICompatibleProvider:
    """Async client for any OpenAI ``/v1``-compatible chat endpoint.

    Args:
        base_url: API root ending in ``/v1`` (e.g. ``http://localhost:3001/v1``
            for FreeLLMAPI, ``https://api.openai.com/v1`` for OpenAI).
        api_key:  Bearer token sent as ``Authorization: Bearer <key>``.
        model:    Default model id (e.g. ``auto`` for FreeLLMAPI).
        timeout:  Per-request timeout in seconds.
        label:    Human name for error messages (e.g. ``freellmapi``).
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        timeout: float = 120.0,
        label: str = "openai",
    ) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""
        self.model = model or "auto"
        self.timeout = float(timeout)
        self.label = label

    # ── headers ────────────────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    # ── availability / discovery ─────────────────────────────────────────────

    async def is_available(self) -> bool:
        """Return ``True`` when ``/models`` responds successfully."""
        try:
            await self.list_models()
            return True
        except AIProviderError:
            return False

    async def list_models(self) -> list[str]:
        """Return model ids advertised by the endpoint."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url}/models", headers=self._headers()
                )
        except httpx.TimeoutException as exc:
            raise AIProviderError(
                f"{self.label} timed out listing models at {self.base_url}",
                model=self.model,
            ) from exc
        except httpx.HTTPError as exc:
            raise AIProviderError(
                f"{self.label} not reachable at {self.base_url}: {exc}",
                model=self.model,
            ) from exc

        if resp.status_code >= 400:
            raise AIProviderError(
                f"{self.label} returned HTTP {resp.status_code} for /models: "
                f"{resp.text[:200]}",
                status_code=resp.status_code,
                model=self.model,
            )
        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            raise AIProviderError(
                f"{self.label} returned malformed JSON from /models: {resp.text[:200]}",
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
        """Return a non-streaming chat completion as plain text."""
        used_model = model or self.model
        used_timeout = self.timeout if timeout is None else float(timeout)
        payload = {
            "model": used_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        data = await self._post_json("/chat/completions", payload, used_model, used_timeout)
        choices = data.get("choices") or []
        if not choices:
            return ""
        return (choices[0].get("message", {}) or {}).get("content", "") or ""

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
    ) -> dict[str, Any]:
        """Return the assistant ``message`` dict, including any ``tool_calls``.

        The returned shape matches :class:`OllamaProvider.chat`: ``content`` plus
        an optional ``tool_calls`` list of ``{"function": {"name", "arguments"}}``.
        OpenAI delivers ``arguments`` as a JSON *string*; the agent's
        ``_parse_tool_call`` already tolerates that.
        """
        if on_token is not None:
            return await self._chat_stream(
                messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
                model=model,
                on_token=on_token,
                on_stats=on_stats,
            )
        used_model = model or self.model
        payload: dict[str, Any] = {
            "model": used_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
        data = await self._post_json("/chat/completions", payload, used_model, self.timeout)
        choices = data.get("choices") or []
        message = (choices[0].get("message") if choices else None) or {}
        out: dict[str, Any] = {
            "role": "assistant",
            "content": message.get("content") or "",
        }
        if message.get("tool_calls"):
            out["tool_calls"] = message["tool_calls"]
        if on_stats is not None and isinstance(data.get("usage"), dict):
            on_stats(_extract_openai_stats(data["usage"]))
        return out

    async def _chat_stream(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None,
        temperature: float,
        max_tokens: int,
        model: str | None,
        on_token: Callable[[str], None],
        on_stats: Callable[[dict[str, Any]], None] | None,
    ) -> dict[str, Any]:
        """Streaming variant using OpenAI Server-Sent Events.

        Content deltas are forwarded to ``on_token`` as they arrive. Tool-call
        deltas arrive fragmented across chunks and are reassembled per ``index``
        (id/name once, ``arguments`` string concatenated) into the final
        Ollama-style ``tool_calls`` list.
        """
        used_model = model or self.model
        payload: dict[str, Any] = {
            "model": used_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools

        parts: list[str] = []
        # index -> {"id", "name", "arguments"}
        tool_acc: dict[int, dict[str, Any]] = {}
        usage: dict[str, Any] = {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                ) as resp:
                    if resp.status_code >= 400:
                        body = (await resp.aread()).decode("utf-8", "replace")
                        raise AIProviderError(
                            f"{self.label} returned HTTP {resp.status_code}: {body[:200]}",
                            status_code=resp.status_code,
                            model=used_model,
                        )
                    async for line in resp.aiter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data:"):
                            continue
                        data_str = line[len("data:"):].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            obj = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(obj.get("usage"), dict):
                            usage = obj["usage"]
                        choices = obj.get("choices") or []
                        if not choices:
                            continue
                        delta = choices[0].get("delta") or {}
                        chunk = delta.get("content")
                        if chunk:
                            parts.append(chunk)
                            on_token(chunk)
                        for tc in delta.get("tool_calls") or []:
                            self._accumulate_tool_call(tool_acc, tc)
        except httpx.TimeoutException as exc:
            raise AIProviderError(
                f"{self.label} stream timed out after {self.timeout}s", model=used_model
            ) from exc
        except httpx.HTTPError as exc:
            raise AIProviderError(
                f"{self.label} not reachable at {self.base_url}: {exc}", model=used_model
            ) from exc

        message: dict[str, Any] = {"role": "assistant", "content": "".join(parts)}
        if tool_acc:
            message["tool_calls"] = [
                tool_acc[i] for i in sorted(tool_acc)
            ]
        if on_stats is not None and usage:
            on_stats(_extract_openai_stats(usage))
        return message

    @staticmethod
    def _accumulate_tool_call(acc: dict[int, dict[str, Any]], delta: dict[str, Any]) -> None:
        """Merge one streamed tool-call delta into the per-index accumulator."""
        idx = delta.get("index", 0)
        slot = acc.setdefault(idx, {"function": {"name": "", "arguments": ""}})
        if delta.get("id"):
            slot["id"] = delta["id"]
        if delta.get("type"):
            slot["type"] = delta["type"]
        fn = delta.get("function") or {}
        if fn.get("name"):
            slot["function"]["name"] = fn["name"]
        if fn.get("arguments"):
            slot["function"]["arguments"] += fn["arguments"]

    # ── internal ───────────────────────────────────────────────────────────────

    async def _post_json(
        self, path: str, payload: dict[str, Any], used_model: str, timeout: float
    ) -> dict[str, Any]:
        """POST a JSON body and return the parsed object, mapping errors."""
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{self.base_url}{path}", headers=self._headers(), json=payload
                )
        except httpx.TimeoutException as exc:
            raise AIProviderError(
                f"{self.label} request timed out after {timeout}s", model=used_model
            ) from exc
        except httpx.HTTPError as exc:
            raise AIProviderError(
                f"{self.label} not reachable at {self.base_url}: {exc}", model=used_model
            ) from exc
        if resp.status_code >= 400:
            raise AIProviderError(
                f"{self.label} returned HTTP {resp.status_code}: {resp.text[:200]}",
                status_code=resp.status_code,
                model=used_model,
            )
        try:
            return resp.json()
        except json.JSONDecodeError as exc:
            raise AIProviderError(
                f"{self.label} returned malformed JSON: {resp.text[:200]}",
                model=used_model,
            ) from exc
