"""
Local Ollama backend for Archon.

Talks to a locally running Ollama server (default ``http://127.0.0.1:11434``)
through its native ``/api/chat`` and ``/api/tags`` endpoints. No API key is
required. This is the single Ollama HTTP implementation in the codebase; the
main AI facade (:class:`~archon.ai.automation_ai.OllamaAutomationAI`) routes all
completions through it.

Design goals (kept deliberately small):
  * one class, one responsibility — speak Ollama's HTTP API;
  * configurable base URL and model (never hardcoded at call sites);
  * uniform error surface — every failure mode raises ``AIProviderError``.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx
from loguru import logger

__all__ = ["AIProviderError", "OllamaProvider"]


def _extract_stats(data: dict[str, Any]) -> dict[str, Any]:
    """Pull real generation metrics from an Ollama done-object.

    Returns only what the server actually reported; a tokens/sec figure is
    derived from ``eval_count`` / ``eval_duration`` (nanoseconds) when both are
    present. Missing fields are simply omitted so the UI can show ``N/A``.
    """
    stats: dict[str, Any] = {}
    eval_count = data.get("eval_count")
    eval_duration = data.get("eval_duration")  # nanoseconds
    if isinstance(eval_count, int):
        stats["eval_count"] = eval_count
    if isinstance(eval_duration, int) and eval_duration > 0:
        stats["eval_duration_s"] = eval_duration / 1e9
        if isinstance(eval_count, int) and eval_count > 0:
            stats["tokens_per_sec"] = eval_count / (eval_duration / 1e9)
    prompt_eval = data.get("prompt_eval_count")
    if isinstance(prompt_eval, int):
        stats["prompt_eval_count"] = prompt_eval
    load_duration = data.get("load_duration")
    if isinstance(load_duration, int) and load_duration > 0:
        stats["load_duration_s"] = load_duration / 1e9
    return stats


class AIProviderError(Exception):
    """Raised when an AI provider returns a non-successful response.

    Shared error type across the AI layer so callers catch one exception rather
    than a parallel hierarchy per backend.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        model: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.model = model

    def __repr__(self) -> str:
        return (
            f"AIProviderError(message={str(self)!r}, "
            f"status_code={self.status_code}, model={self.model!r})"
        )

_DEFAULT_URL = "http://127.0.0.1:11434"
_DEFAULT_MODEL = "qwen3.5:9b"


class OllamaProvider:
    """Async client for a local Ollama server.

    Args:
        base_url: Ollama server root, e.g. ``http://127.0.0.1:11434``.
        model:    Default model name, e.g. ``qwen3.5:9b``.
        timeout:  Per-request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_URL,
        model: str = _DEFAULT_MODEL,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = (base_url or _DEFAULT_URL).rstrip("/")
        self.model = model or _DEFAULT_MODEL
        self.timeout = float(timeout)

    # ── Availability / discovery ─────────────────────────────────────────────

    async def is_available(self) -> bool:
        """Return ``True`` when the Ollama server responds to ``/api/tags``."""
        try:
            await self.list_models()
            return True
        except AIProviderError:
            return False

    async def list_models(self) -> list[str]:
        """Return the model names installed on the server.

        Raises:
            AIProviderError: When the server is unreachable or replies with an
                error / malformed body.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
        except httpx.TimeoutException as exc:
            raise AIProviderError(
                f"Ollama timed out listing models at {self.base_url}", model=self.model
            ) from exc
        except httpx.HTTPError as exc:
            raise AIProviderError(
                f"Ollama not reachable at {self.base_url}: {exc}", model=self.model
            ) from exc

        if resp.status_code >= 400:
            raise AIProviderError(
                f"Ollama returned HTTP {resp.status_code} for /api/tags: {resp.text[:200]}",
                status_code=resp.status_code,
                model=self.model,
            )
        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            raise AIProviderError(
                f"Ollama returned malformed JSON from /api/tags: {resp.text[:200]}",
                model=self.model,
            ) from exc
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]

    # ── Completion ───────────────────────────────────────────────────────────

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        model: str | None = None,
        timeout: float | None = None,
    ) -> str:
        """Return a non-streaming chat completion.

        Args:
            messages:    OpenAI-style ``{"role", "content"}`` list.
            temperature: Sampling temperature.
            max_tokens:  Upper bound on generated tokens (Ollama ``num_predict``).
            model:       Override the default model for this call.
            timeout:     Per-call timeout override in seconds. Long generations
                         (e.g. full documents) need more than the chat default,
                         which otherwise aborts a valid, still-streaming reply.

        Returns:
            The assistant text (empty string if the model produced none).

        Raises:
            AIProviderError: On unavailability, unknown model, timeout,
                malformed response, or inference error.
        """
        used_model = model or self.model
        used_timeout = self.timeout if timeout is None else float(timeout)
        payload: dict[str, Any] = {
            "model": used_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            async with httpx.AsyncClient(timeout=used_timeout) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.TimeoutException as exc:
            raise AIProviderError(
                f"Ollama request timed out after {used_timeout}s", model=used_model
            ) from exc
        except httpx.HTTPError as exc:
            raise AIProviderError(
                f"Ollama not reachable at {self.base_url}: {exc}", model=used_model
            ) from exc

        return self._parse_chat_response(resp, used_model)[0]

    async def complete_ex(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        model: str | None = None,
        timeout: float | None = None,
    ) -> tuple[str, str]:
        """Like :meth:`complete`, but also return Ollama's ``done_reason``.

        ``done_reason`` is ``"stop"`` when the model ended on its own and
        ``"length"`` when it hit ``num_predict`` and the text is truncated. The
        document generator uses this to continue a long reply instead of writing
        out a document that just stops mid-section.
        """
        used_model = model or self.model
        used_timeout = self.timeout if timeout is None else float(timeout)
        payload: dict[str, Any] = {
            "model": used_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            async with httpx.AsyncClient(timeout=used_timeout) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.TimeoutException as exc:
            raise AIProviderError(
                f"Ollama request timed out after {used_timeout}s", model=used_model
            ) from exc
        except httpx.HTTPError as exc:
            raise AIProviderError(
                f"Ollama not reachable at {self.base_url}: {exc}", model=used_model
            ) from exc

        return self._parse_chat_response(resp, used_model)

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
        """Return the raw assistant message, including any ``tool_calls``.

        Unlike :meth:`complete` (which returns just the text), this surfaces the
        full ``message`` object so a tool-calling agent loop can read
        ``message["tool_calls"]``. Ollama's native ``/api/chat`` accepts an
        OpenAI-style ``tools`` list and returns
        ``{"role": "assistant", "content": "...", "tool_calls": [...]}``.

        Args:
            messages:    Chat history; tool results use ``role: "tool"``.
            tools:       OpenAI-style function/tool definitions, or ``None``.
            temperature: Sampling temperature.
            max_tokens:  Upper bound on generated tokens (Ollama ``num_predict``).
            model:       Override the default model for this call.
            on_token:    When given, stream the reply and invoke this with each
                         text fragment as it arrives. Tool calls are still
                         accumulated and returned in the final message.
            on_stats:    Optional sink for the final generation stats
                         (``eval_count``/``eval_duration`` etc.) so the UI can
                         show a real tokens/sec figure.

        Returns:
            The assistant ``message`` dict (``content`` may be empty when the
            model chose to call tools instead of replying).

        Raises:
            AIProviderError: On unavailability, unknown model, timeout,
                malformed response, or inference error.
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
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if tools:
            payload["tools"] = tools
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.TimeoutException as exc:
            raise AIProviderError(
                f"Ollama request timed out after {self.timeout}s", model=used_model
            ) from exc
        except httpx.HTTPError as exc:
            raise AIProviderError(
                f"Ollama not reachable at {self.base_url}: {exc}", model=used_model
            ) from exc

        # Reuse the shared validation, then hand back the whole message object.
        self._parse_chat_response(resp, used_model)
        data = resp.json()
        message = data.get("message") if isinstance(data, dict) else None
        if not isinstance(message, dict):
            raise AIProviderError(
                f"Ollama returned no message object: {str(data)[:200]}", model=used_model
            )
        if on_stats is not None and isinstance(data, dict):
            on_stats(_extract_stats(data))
        return message

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
        """Streaming variant of :meth:`chat`.

        Ollama streams newline-delimited JSON message deltas. Content fragments
        are handed to ``on_token`` as they arrive; ``tool_calls`` are collected
        and returned in the assembled message so the agent loop keeps working.
        """
        used_model = model or self.model
        payload: dict[str, Any] = {
            "model": used_model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if tools:
            payload["tools"] = tools

        parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST", f"{self.base_url}/api/chat", json=payload
                ) as resp:
                    if resp.status_code == 404:
                        raise AIProviderError(
                            f"Ollama model {used_model!r} not found. Pull it with "
                            f"'ollama pull {used_model}'.",
                            status_code=404,
                            model=used_model,
                        )
                    if resp.status_code >= 400:
                        body = (await resp.aread()).decode("utf-8", "replace")
                        raise AIProviderError(
                            f"Ollama returned HTTP {resp.status_code}: {body[:200]}",
                            status_code=resp.status_code,
                            model=used_model,
                        )
                    async for line in resp.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if obj.get("error"):
                            raise AIProviderError(
                                f"Ollama inference error: {obj['error']}", model=used_model
                            )
                        msg = obj.get("message") or {}
                        chunk = msg.get("content", "")
                        if chunk:
                            parts.append(chunk)
                            on_token(chunk)
                        calls = msg.get("tool_calls")
                        if calls:
                            tool_calls.extend(calls)
                        if obj.get("done"):
                            if on_stats is not None:
                                on_stats(_extract_stats(obj))
                            break
        except httpx.TimeoutException as exc:
            raise AIProviderError(
                f"Ollama stream timed out after {self.timeout}s", model=used_model
            ) from exc
        except httpx.HTTPError as exc:
            raise AIProviderError(
                f"Ollama not reachable at {self.base_url}: {exc}", model=used_model
            ) from exc

        message: dict[str, Any] = {"role": "assistant", "content": "".join(parts)}
        if tool_calls:
            message["tool_calls"] = tool_calls
        return message

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """Yield incremental text chunks from a streaming chat completion.

        Ollama streams newline-delimited JSON objects (not SSE); each carries a
        ``message.content`` fragment until an object with ``done: true``.

        Args:
            messages:    OpenAI-style message list.
            temperature: Sampling temperature.
            max_tokens:  Upper bound on generated tokens.
            model:       Override the default model.

        Yields:
            Text fragments as they arrive.

        Raises:
            AIProviderError: On unavailability, unknown model, or timeout before
                the first chunk.
        """
        used_model = model or self.model
        payload: dict[str, Any] = {
            "model": used_model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST", f"{self.base_url}/api/chat", json=payload
                ) as resp:
                    if resp.status_code >= 400:
                        body = (await resp.aread()).decode("utf-8", "replace")
                        raise AIProviderError(
                            f"Ollama returned HTTP {resp.status_code}: {body[:200]}",
                            status_code=resp.status_code,
                            model=used_model,
                        )
                    async for line in resp.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if obj.get("error"):
                            raise AIProviderError(
                                f"Ollama inference error: {obj['error']}", model=used_model
                            )
                        chunk = obj.get("message", {}).get("content", "")
                        if chunk:
                            yield chunk
                        if obj.get("done"):
                            break
        except httpx.TimeoutException as exc:
            raise AIProviderError(
                f"Ollama stream timed out after {self.timeout}s", model=used_model
            ) from exc
        except httpx.HTTPError as exc:
            raise AIProviderError(
                f"Ollama not reachable at {self.base_url}: {exc}", model=used_model
            ) from exc

    # ── Internal ───────────────────────────────────────────────────────────

    def _parse_chat_response(
        self, resp: httpx.Response, used_model: str
    ) -> tuple[str, str]:
        """Validate a non-streaming ``/api/chat`` reply.

        Returns ``(content, done_reason)`` — ``done_reason`` is ``"length"`` when
        the reply was truncated at ``num_predict``, ``"stop"`` on a clean finish.
        """
        if resp.status_code == 404:
            raise AIProviderError(
                f"Ollama model {used_model!r} not found. Pull it with "
                f"'ollama pull {used_model}'.",
                status_code=404,
                model=used_model,
            )
        if resp.status_code >= 400:
            raise AIProviderError(
                f"Ollama returned HTTP {resp.status_code}: {resp.text[:200]}",
                status_code=resp.status_code,
                model=used_model,
            )
        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            raise AIProviderError(
                f"Ollama returned malformed JSON: {resp.text[:200]}", model=used_model
            ) from exc
        if isinstance(data, dict) and data.get("error"):
            raise AIProviderError(
                f"Ollama inference error: {data['error']}", model=used_model
            )
        # /api/chat → {"message": {"content": "..."}}; some builds use "response".
        content = ""
        done_reason = "stop"
        if isinstance(data, dict):
            content = data.get("message", {}).get("content", "") or data.get("response", "")
            done_reason = data.get("done_reason") or "stop"
        if not content:
            logger.debug("Ollama returned empty content for model {}", used_model)
        return content or "", done_reason
