"""
OpenRouter AI integration for Tyranos.

Async rewrite using httpx.AsyncClient.  All model names are resolved
dynamically via FreeModelResolver — none are hardcoded.

Streaming (SSE) is supported and used by chatbot mode.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx
from loguru import logger

from ..config import get_config
from ..utils.logger import get_logger
from .context_manager import ContextWindow
from .model_resolver import FreeModelResolver, get_resolver
from .response_parser import TaskPlan, parse_task_plan

__all__ = [
    # New async client (spec-required)
    "OpenRouterConfig",
    "StreamChunk",
    "AIProviderError",
    "OpenRouterClient",
    # Legacy names (backward compat)
    "AITaskPlan",
    "OpenRouterAutomationAI",
]

_BASE_URL = "https://openrouter.ai/api/v1"
_CHAT_URL = f"{_BASE_URL}/chat/completions"


# ---------------------------------------------------------------------------
# Legacy dataclass kept for backward compat
# ---------------------------------------------------------------------------


@dataclass
class AITaskPlan:
    """AI-generated task execution plan (legacy dataclass; see response_parser.TaskPlan)."""

    original_request: str
    interpreted_intent: str
    confidence_score: float
    execution_steps: list[dict[str, Any]]
    risk_assessment: dict[str, Any]
    optimization_suggestions: list[str]


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = r"""
You are Tyranos, an intelligent OS automation assistant.

RESPONSE FORMAT — always valid JSON, never wrapped in markdown code fences:
{
    "intent": "what the user wants",
    "confidence": 0.85,
    "corrected_input": "spell-corrected version if relevant",
    "clarification_questions": [],
    "assumptions": [],
    "steps": [
        {
            "action": "specific_action_name",
            "category": "filesystem|process|gui|network|system|project_generator|package_manager|devops",
            "params": {},
            "description": "human readable description",
            "required": true
        }
    ],
    "risks": {
        "level": "low|medium|high|critical",
        "concerns": [],
        "mitigations": []
    },
    "optimizations": [],
    "user_confirmations_needed": []
}

TYPO TOLERANCE: silently correct grammar/spelling and reflect fixes in "corrected_input".
NEVER include verify_* actions — the workflow engine handles verification automatically.
NEVER generate actions not listed in the category reference above.
"""


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class OpenRouterAutomationAI:
    """
    Async OpenRouter AI client.

    Uses FreeModelResolver to pick the default model without hardcoding any
    model name.  Falls back gracefully when the API is unavailable.

    Args:
        api_key: OpenRouter API key. Reads ``OPENROUTER_API_KEY`` env var if omitted.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self.logger = get_logger("OpenRouterAI")
        _config = get_config()
        self._api_key = (
            api_key or _config.ai.openrouter_api_key or os.getenv("OPENROUTER_API_KEY", "")
        )
        self._resolver: FreeModelResolver | None = None
        self._model_name: str = ""  # set after ensure_loaded()
        self._is_available: bool = False
        self.last_error: str | None = None
        self._context_window = ContextWindow(
            max_tokens=_config.ai.max_tokens,
            system_prompt=_SYSTEM_PROMPT.strip(),
        )
        # Attempt async initialisation in the background
        self._init_task: asyncio.Task[None] | None = None
        try:
            loop = asyncio.get_running_loop()
            self._init_task = loop.create_task(self._async_init())
        except RuntimeError:
            # No running loop — initialise synchronously
            with contextlib.suppress(RuntimeError):
                asyncio.run(self._async_init())

    # ── Properties (backward compat) ─────────────────────────────────────────

    @property
    def is_available(self) -> bool:
        """``True`` when the API is reachable and a model is selected."""
        return self._is_available

    @property
    def model_name(self) -> str:
        """Current model id (empty string if not yet initialised)."""
        return self._model_name

    # ── Async initialisation ──────────────────────────────────────────────────

    async def _async_init(self) -> None:
        """Resolve the best free model and warm-test connectivity."""
        if not self._api_key:
            self.last_error = "OPENROUTER_API_KEY not set"
            logger.warning("OpenRouterAI: API key not set — AI features disabled")
            return
        try:
            resolver = self._get_resolver()
            await resolver.ensure_loaded()
            self._model_name = resolver.default_model().model_id
            await self._probe_connectivity()
            self._is_available = True
            logger.info("OpenRouterAI ready — model={}", self._model_name)
        except Exception as exc:
            self.last_error = str(exc)
            self._is_available = False
            logger.warning("OpenRouterAI init failed: {}", exc)

    async def _probe_connectivity(self) -> None:
        """Send a minimal request to verify the API key works."""
        headers = self._headers()
        payload = {
            "model": self._model_name,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 3,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(_CHAT_URL, headers=headers, json=payload)
            resp.raise_for_status()

    # ── Public async API ──────────────────────────────────────────────────────

    async def analyze_automation_request_async(
        self,
        user_request: str,
        context: dict[str, Any] | None = None,
    ) -> AITaskPlan:
        """
        Async version of analyze_automation_request.

        Args:
            user_request: Natural language command from the user.
            context:      Optional execution context dict.

        Returns:
            AITaskPlan (legacy dataclass).
        """
        await self._ensure_init()
        if not self._is_available:
            return self._fallback_plan(user_request)

        prompt = self._build_prompt(user_request, context or {})
        try:
            raw = await self._call(prompt)
            task_plan = parse_task_plan(raw, user_request)
            return self._task_plan_to_legacy(task_plan)
        except Exception as exc:
            logger.error("analyze_automation_request_async failed: {}", exc)
            return self._fallback_plan(user_request)

    async def stream_response(self, prompt: str) -> AsyncIterator[str]:
        """
        Yield incremental text tokens from a streaming response.

        Suitable for chatbot mode where results should appear progressively.

        Args:
            prompt: User message.

        Yields:
            String chunks as they arrive.
        """
        await self._ensure_init()
        if not self._is_available:
            yield "AI is not available. Check OPENROUTER_API_KEY."
            return

        headers = self._headers()
        self._context_window.add_user(prompt)
        payload = {
            "model": self._model_name,
            "messages": self._context_window.get_messages(),
            "stream": True,
            "temperature": 0.7,
            "max_tokens": 1024,
        }
        accumulated: list[str] = []
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", _CHAT_URL, headers=headers, json=payload) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            chunk = data["choices"][0].get("delta", {}).get("content") or ""
                            if chunk:
                                accumulated.append(chunk)
                                yield chunk
                        except (KeyError, json.JSONDecodeError):
                            continue
        except Exception as exc:
            logger.error("stream_response error: {}", exc)
            yield f"\n[Stream error: {exc}]"
        finally:
            self._context_window.add_assistant("".join(accumulated))

    # ── Synchronous wrappers (backward compat) ────────────────────────────────

    def analyze_automation_request(
        self,
        user_request: str,
        context: dict[str, Any] | None = None,
    ) -> AITaskPlan:
        """
        Synchronous wrapper (blocking) around analyze_automation_request_async.

        Args:
            user_request: Natural language command.
            context:      Optional context dict.

        Returns:
            AITaskPlan.
        """
        try:
            try:
                asyncio.get_running_loop()
                loop_running = True
            except RuntimeError:
                loop_running = False

            if loop_running:
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(
                        asyncio.run,
                        self.analyze_automation_request_async(user_request, context),
                    )
                    return future.result(timeout=60)
            else:
                return asyncio.run(self.analyze_automation_request_async(user_request, context))
        except Exception as exc:
            logger.warning("analyze_automation_request sync wrapper failed: {}", exc)
            return self._fallback_plan(user_request)

    def generate_smart_suggestions(self, context: dict[str, Any]) -> list[str]:
        """Return AI-powered automation suggestions.

        Args:
            context: Dict with keys like os_type, recent_commands, current_directory.

        Returns:
            List of suggestion strings.
        """
        if not self._is_available:
            return ["Set OPENROUTER_API_KEY for AI-powered suggestions"]
        try:
            prompt = (
                f"Suggest 5 useful automation commands for:\n"
                f"OS: {context.get('os_type', 'unknown')}\n"
                f"CWD: {context.get('current_directory', 'unknown')}\n"
                f"Recent: {context.get('recent_commands', [])}\n"
                "Output as a plain numbered list."
            )
            raw = asyncio.run(self._call(prompt))
            lines = [
                line.strip()
                for line in raw.splitlines()
                if line.strip() and not line.startswith("#")
            ]
            return lines[:8] if lines else ["create folder myproject", "take screenshot"]
        except Exception as exc:
            logger.warning("smart suggestions failed: {}", exc)
            return ["create folder myproject", "take screenshot", "list files"]

    def enhance_command_understanding(
        self, command: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Enhance a command with AI insights.

        Args:
            command: Raw user command.
            context: Optional context.

        Returns:
            Dict with ``enhanced``, ``original``, ``suggestions`` etc.
        """
        from .response_parser import parse_intent_result

        if not self._is_available:
            return {"enhanced": False, "original": command}
        try:
            prompt = (
                f"Analyse this command and return JSON with keys: "
                f"enhanced_understanding, suggestions, clarifications_needed, confidence.\n"
                f"Command: {command}\nContext: {context or {}}"
            )
            raw = asyncio.run(self._call(prompt))
            result = parse_intent_result(raw, command)
            return {
                "enhanced": result.enhanced,
                "original": result.original,
                "enhanced_understanding": result.enhanced_understanding,
                "suggestions": result.suggestions,
                "confidence": result.confidence,
            }
        except Exception as exc:
            logger.warning("enhance_command_understanding failed: {}", exc)
            return {"enhanced": False, "original": command}

    def suggest_error_resolution(self, error_info: dict[str, Any]) -> dict[str, Any]:
        """Return AI suggestions for a failed command.

        Args:
            error_info: Dict with keys ``error_message``, ``command``, ``error_type``.

        Returns:
            Dict with ``suggestions`` list and ``confidence`` float.
        """
        if not self._is_available:
            return {"suggestions": ["Check logs and retry"], "confidence": 0.1}
        try:
            prompt = (
                f"Automation command failed:\n"
                f"Command: {error_info.get('command')}\n"
                f"Error: {error_info.get('error_message')}\n"
                "Provide 3-5 actionable fix suggestions as a JSON array under key 'suggestions'."
            )
            raw = asyncio.run(self._call(prompt))
            from .response_parser import repair_and_parse

            data = repair_and_parse(raw) or {}
            suggestions = data.get("suggestions", [])
            return {"suggestions": suggestions[:5], "confidence": 0.8}
        except Exception as exc:
            logger.warning("suggest_error_resolution failed: {}", exc)
            return {"suggestions": ["Check command syntax and retry"], "confidence": 0.3}

    def optimize_workflow(self, steps: list[dict[str, Any]]) -> dict[str, Any]:
        """Ask AI to suggest workflow optimisations.

        Args:
            steps: List of workflow step dicts.

        Returns:
            Dict with ``optimized_steps``, ``improvements``, ``parallel_groups``.
        """
        if not self._is_available:
            return {"optimized_steps": steps, "improvements": [], "parallel_groups": []}
        try:
            import json as _json

            prompt = (
                f"Optimise this workflow:\n{_json.dumps(steps, indent=2)}\n"
                "Return JSON with keys: optimized_steps, improvements, parallel_groups."
            )
            raw = asyncio.run(self._call(prompt))
            from .response_parser import repair_and_parse

            data = repair_and_parse(raw) or {}
            return {
                "optimized_steps": data.get("optimized_steps", steps),
                "improvements": data.get("improvements", []),
                "parallel_groups": data.get("parallel_groups", []),
            }
        except Exception:
            return {"optimized_steps": steps, "improvements": [], "parallel_groups": []}

    def set_model(self, model_name: str) -> bool:
        """Override the active model.

        Args:
            model_name: OpenRouter model id.

        Returns:
            ``True`` (always accepted; validation deferred to next call).
        """
        self._model_name = model_name
        logger.info("OpenRouterAI: model set to {}", model_name)
        return True

    def get_available_models(self) -> dict[str, str]:
        """Return a model_id → description map for all free models.

        Returns:
            Dict of model id → display name.
        """
        try:
            resolver = self._get_resolver()
            if not resolver._is_fresh():
                asyncio.run(resolver.ensure_loaded())
            return {m.model_id: m.name for m in resolver.fallback_chain()}
        except Exception:
            return {}

    def is_openrouter_available(self) -> bool:
        """Check if the AI integration is ready.

        Returns:
            ``True`` when operational.
        """
        return self._is_available

    def get_ai_status(self) -> dict[str, Any]:
        """Return a status summary dict.

        Returns:
            Dict with ``available``, ``model``, ``provider`` etc.
        """
        return {
            "available": self._is_available,
            "has_api_key": bool(self._api_key),
            "model": self._model_name if self._is_available else None,
            "provider": "OpenRouter",
            "last_error": self.last_error,
            "available_models": list(self.get_available_models().keys()),
        }

    def get_current_model(self) -> str:
        """Return the active model id.

        Returns:
            Model id string, or ``"None"`` if not initialised.
        """
        return self._model_name if self._is_available else "None"

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _call(self, prompt: str, *, temperature: float = 0.3, max_tokens: int = 2048) -> str:
        """Make a single async completion call.

        Args:
            prompt:      User text.
            temperature: Sampling temperature.
            max_tokens:  Max completion tokens.

        Returns:
            Raw response string.

        Raises:
            httpx.HTTPError: On network failure.
        """
        payload = {
            "model": self._model_name,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT.strip()},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(_CHAT_URL, headers=self._headers(), json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "HTTP-Referer": "https://tyranos.local",
            "X-Title": "Tyranos",
            "Content-Type": "application/json",
        }

    def _get_resolver(self) -> FreeModelResolver:
        if self._resolver is None:
            self._resolver = get_resolver()
        return self._resolver

    async def _ensure_init(self) -> None:
        """Await the background init task if still running."""
        if self._init_task is not None and not self._init_task.done():
            await self._init_task
        elif not self._is_available and not self.last_error:
            await self._async_init()

    @staticmethod
    def _fallback_plan(user_request: str) -> AITaskPlan:
        return AITaskPlan(
            original_request=user_request,
            interpreted_intent=f"Basic interpretation: {user_request}",
            confidence_score=0.2,
            execution_steps=[],
            risk_assessment={"level": "unknown", "concerns": ["AI unavailable"], "mitigations": []},
            optimization_suggestions=["Enable AI by setting OPENROUTER_API_KEY"],
        )

    @staticmethod
    def _task_plan_to_legacy(plan: TaskPlan) -> AITaskPlan:
        return AITaskPlan(
            original_request=plan.original_request,
            interpreted_intent=plan.interpreted_intent,
            confidence_score=plan.confidence_score,
            execution_steps=[
                {
                    "action": s.action,
                    "category": s.category,
                    "params": s.params,
                    "description": s.description,
                    "required": s.required,
                }
                for s in plan.execution_steps
            ],
            risk_assessment={
                "level": plan.risk_assessment.level,
                "concerns": plan.risk_assessment.concerns,
                "mitigations": plan.risk_assessment.mitigations,
            },
            optimization_suggestions=plan.optimization_suggestions,
        )

    # ── Compat aliases ────────────────────────────────────────────────────────

    def _parse_ai_response(self, response_text: str) -> dict[str, Any]:
        """Legacy parse helper delegating to repair_and_parse."""
        from .response_parser import repair_and_parse

        return repair_and_parse(response_text) or {}

    def _get_fallback_response(self) -> dict[str, Any]:
        return {
            "intent": "Basic command execution",
            "confidence": 0.3,
            "steps": [],
            "risks": {"level": "medium", "concerns": [], "mitigations": []},
            "optimizations": [],
        }

    @staticmethod
    def _build_prompt(request: str, context: dict[str, Any]) -> str:
        """Build the user-facing analysis prompt, optionally enriched with context."""
        ctx_lines = [f"{k}: {v}" for k, v in context.items() if v]
        ctx_str = "\n".join(ctx_lines) if ctx_lines else "No additional context"
        return (
            f"AUTOMATION REQUEST: {request}\n\n"
            f"CONTEXT:\n{ctx_str}\n\n"
            "Analyse the request and respond with valid JSON."
        )


# =============================================================================
# New async client (spec-required additions)
# =============================================================================


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AIProviderError(Exception):
    """Raised when the AI provider returns a non-successful response."""

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


# ---------------------------------------------------------------------------
# Configuration and streaming dataclasses
# ---------------------------------------------------------------------------


@dataclass
class OpenRouterConfig:
    """Configuration for the async :class:`OpenRouterClient`."""

    url: str = "https://openrouter.ai/api/v1"
    api_key: str = ""
    model: str = ""
    timeout: float = 60.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> OpenRouterConfig:
        """Construct a config instance from environment variables."""
        return cls(
            api_key=os.getenv("OPENROUTER_API_KEY", ""),
            model=os.getenv("OPENROUTER_MODEL", ""),
        )


@dataclass
class StreamChunk:
    """A single SSE token/delta emitted by the streaming endpoint."""

    content: str
    finish_reason: str | None
    model: str


# ---------------------------------------------------------------------------
# Async client
# ---------------------------------------------------------------------------

_SITE_HEADERS: dict[str, str] = {
    "HTTP-Referer": "https://tyranos.local",
    "X-Title": "Tyranos",
}


class OpenRouterClient:
    """
    Async HTTP client for the OpenRouter chat-completions API.

    Features
    --------
    * Non-streaming completion with tenacity exponential-backoff retry.
    * SSE streaming via an async generator.
    * Model fallback chain (tries each model in order, logs warnings on failure).
    * Async context-manager support.

    Example::

        async with OpenRouterClient(OpenRouterConfig(api_key="...")) as client:
            text = await client.complete(messages)
    """

    def __init__(self, config: OpenRouterConfig) -> None:
        self._cfg = config
        self._client = httpx.AsyncClient(
            base_url=config.url.rstrip("/"),
            headers={
                **_SITE_HEADERS,
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(config.timeout),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Send a non-streaming chat completion request.

        Retries up to ``config.max_retries`` times with exponential back-off
        (wait_exponential min=1s, max=10s) before raising the last exception.

        Parameters
        ----------
        messages:
            OpenAI-compatible message list.
        model:
            Override the configured model for this call.
        **kwargs:
            Extra fields forwarded verbatim in the request body
            (e.g. ``temperature``, ``max_tokens``).

        Returns
        -------
        str
            The assistant content string.
        """
        from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential

        async for attempt in AsyncRetrying(
            wait=wait_exponential(min=1, max=10),
            stop=stop_after_attempt(self._cfg.max_retries),
            reraise=True,
        ):
            with attempt:
                payload = self._build_payload(messages, model=model, stream=False, **kwargs)
                response = await self._client.post("/chat/completions", json=payload)
                self._raise_for_status(response, model or self._cfg.model)
                data = response.json()
                return self._extract_completion_content(data)

        # Unreachable — AsyncRetrying with reraise=True always raises.
        raise AIProviderError("Retry loop exited unexpectedly.", model=model or self._cfg.model)

    async def stream(
        self,
        messages: list[dict],
        model: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """
        Send a streaming chat completion request and yield :class:`StreamChunk` objects.

        SSE lines are parsed one at a time; the ``[DONE]`` sentinel terminates
        iteration cleanly.  Heartbeat and event-type lines are silently skipped.

        Parameters
        ----------
        messages:
            OpenAI-compatible message list.
        model:
            Override the configured model for this call.

        Yields
        ------
        :class:`StreamChunk`
        """
        payload = self._build_payload(messages, model=model, stream=True)
        used_model = model or self._cfg.model
        async with self._client.stream("POST", "/chat/completions", json=payload) as response:
            self._raise_for_status(response, used_model)
            async for line in response.aiter_lines():
                chunk = self._parse_sse_line(line, used_model)
                if chunk is not None:
                    yield chunk

    async def complete_with_fallback(
        self,
        messages: list[dict],
        fallback_chain: list[str],
    ) -> tuple[str, str]:
        """
        Try each model in *fallback_chain* in order until one succeeds.

        On any exception (timeout, rate limit, 4xx/5xx) the failure is logged
        as a warning and the next model is tried.

        Parameters
        ----------
        messages:
            OpenAI-compatible message list.
        fallback_chain:
            Ordered list of model ids to try.

        Returns
        -------
        ``(content, model_used)``

        Raises
        ------
        :class:`AIProviderError`
            When every model in the chain fails.
        """
        if not fallback_chain:
            raise AIProviderError("fallback_chain is empty — no models to try.", model=None)

        last_exc: Exception | None = None
        for model_id in fallback_chain:
            try:
                content = await self.complete(messages, model=model_id)
                return content, model_id
            except Exception as exc:
                logger.warning(
                    "Model {} failed during fallback chain: {} — trying next.",
                    model_id,
                    exc,
                )
                last_exc = exc

        raise AIProviderError(
            f"All {len(fallback_chain)} model(s) in fallback chain failed. Last error: {last_exc}",
            model=fallback_chain[-1],
        )

    async def close(self) -> None:
        """Close the underlying httpx.AsyncClient."""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Async context-manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> OpenRouterClient:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        messages: list[dict],
        model: str | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict:
        payload: dict = {
            "model": model or self._cfg.model,
            "messages": messages,
            "stream": stream,
        }
        payload.update(kwargs)
        return payload

    def _raise_for_status(self, response: httpx.Response, model: str) -> None:
        """Raise :class:`AIProviderError` for HTTP 4xx / 5xx."""
        if response.status_code >= 400:
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            raise AIProviderError(
                f"Provider returned HTTP {response.status_code}: {detail}",
                status_code=response.status_code,
                model=model,
            )

    @staticmethod
    def _extract_completion_content(data: dict) -> str:
        """Pull the content string out of a non-streaming response."""
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError) as exc:
            raise AIProviderError(f"Unexpected response shape: {data}") from exc

    @staticmethod
    def _parse_sse_line(line: str, model: str) -> StreamChunk | None:
        """
        Parse one raw SSE text line.

        Returns a :class:`StreamChunk` when the line carries delta content,
        ``None`` for all non-content lines (blank lines, heartbeats, event
        declarations, and the ``[DONE]`` terminator).
        """
        line = line.strip()
        if not line:
            return None
        # Skip event-type lines ("event: …") and heartbeat comments (":").
        if line.startswith("event:") or line.startswith(":"):
            return None
        if not line.startswith("data: "):
            return None
        payload = line[len("data: ") :]
        if payload.strip() == "[DONE]":
            return None
        try:
            obj = json.loads(payload)
        except json.JSONDecodeError:
            logger.debug("Could not parse SSE payload as JSON: {!r}", payload)
            return None
        choices = obj.get("choices", [])
        choice = choices[0] if choices else {}
        delta = choice.get("delta", {})
        content = delta.get("content") or ""
        finish_reason = choice.get("finish_reason")
        used_model = obj.get("model", model)
        return StreamChunk(content=content, finish_reason=finish_reason, model=used_model)
