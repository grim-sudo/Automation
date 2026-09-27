"""
Local Ollama AI facade for Archon.

The single AI facade the rest of Archon talks to. It wraps the local
:class:`~archon.ai.ollama_integration.OllamaProvider` and turns natural-language
requests into structured task plans, conversational replies, and workflow
suggestions. There is no cloud provider — everything runs against a local
Ollama server (default ``qwen3.5:9b``), so no API key is ever required.

Kept intentionally forgiving: when Ollama is unreachable or the model returns
nothing usable, methods degrade to safe fallbacks rather than raising, so the
caller (parser / engine) can still proceed with its deterministic path.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from loguru import logger

from ..config import get_config
from ..utils.logger import get_logger
from .context_manager import ContextWindow
from .ollama_integration import OllamaProvider
from .response_parser import TaskPlan, parse_task_plan

__all__ = ["AITaskPlan", "OllamaAutomationAI"]


# ---------------------------------------------------------------------------
# Legacy dataclass kept for backward compat with the parser layer
# ---------------------------------------------------------------------------


@dataclass
class AITaskPlan:
    """AI-generated task execution plan (see response_parser.TaskPlan)."""

    original_request: str
    interpreted_intent: str
    confidence_score: float
    execution_steps: list[dict[str, Any]]
    risk_assessment: dict[str, Any]
    optimization_suggestions: list[str]


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = r"""
You are Archon, an intelligent OS automation assistant.

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

# Conversational prompt — used when the user is asking/chatting rather than
# issuing a concrete automation command. Plain prose, no JSON.
_CHAT_SYSTEM_PROMPT = r"""
You are Archon, a personal computing intelligence and control system. You sit
above the user's machines and connect operating systems, AI models, automation
(n8n), MCP capabilities, cloud, containers, projects, custom OS building, and
long-running autonomous tasks.

You are not a generic chatbot. You are the control layer for the user's entire
computing environment. Answer as that system: precise, technical, grounded, and
useful. When the user seems to want an action performed (create, build, install,
deploy, run, generate, delete, …), tell them they can issue it directly and you
will execute it — you do not need to ask permission to be helpful.

Keep answers concise. Prefer concrete steps and real commands over generic
advice. Use plain text; no markdown headers or JSON.
"""


# ---------------------------------------------------------------------------
# Main facade
# ---------------------------------------------------------------------------

# Full-document generation is a single large completion (thousands of tokens) on
# a local model — far slower than a chat turn. The chat-tier timeout (~120s)
# aborts a valid, still-streaming reply, so document generation gets its own
# generous ceiling.
_DOCUMENT_TIMEOUT = 600.0


class OllamaAutomationAI:
    """Local-Ollama AI facade.

    Args:
        model: Optional model override. Defaults to the configured Ollama model.
    """

    def __init__(self, model: str | None = None) -> None:
        self.logger = get_logger("OllamaAI")
        _config = get_config()
        self._model_name: str = ""
        self._is_available: bool = False
        self.last_error: str | None = None
        self._context_window = ContextWindow(
            max_tokens=_config.ai.max_tokens,
            system_prompt=_SYSTEM_PROMPT.strip(),
        )
        resolved_model = (
            model
            or _config.ai.model
            or getattr(_config.ai, "ollama_model", "")
            or "qwen3.5:9b"
        )
        # Local reasoning models are far slower than a cloud API; floor the
        # timeout so first-token latency + reasoning fits.
        local_timeout = max(float(_config.ai.timeout), 120.0)
        self._ollama = OllamaProvider(
            base_url=getattr(_config.ai, "ollama_url", "") or "http://127.0.0.1:11434",
            model=resolved_model,
            timeout=local_timeout,
        )
        self._model_name = self._ollama.model

        # Kick off availability probe: background task if a loop is running,
        # otherwise synchronously.
        self._init_task: asyncio.Task[None] | None = None
        try:
            loop = asyncio.get_running_loop()
            self._init_task = loop.create_task(self._async_init())
        except RuntimeError:
            with contextlib.suppress(RuntimeError):
                asyncio.run(self._async_init())

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_available(self) -> bool:
        """``True`` when the Ollama server is reachable and a model is selected."""
        return self._is_available

    @property
    def model_name(self) -> str:
        """Current model id (empty string if not yet initialised)."""
        return self._model_name

    # ── Async initialisation ────────────────────────────────────────────────

    async def _async_init(self) -> None:
        """Probe the local Ollama server and lock onto the configured model."""
        try:
            if not await self._ollama.is_available():
                self._is_available = False
                self.last_error = (
                    f"Ollama not reachable at {self._ollama.base_url}. "
                    "Start it with 'ollama serve'."
                )
                logger.warning("OllamaAI: {}", self.last_error)
                return
            installed = await self._ollama.list_models()
            if installed and self._ollama.model not in installed:
                # Model not pulled yet — surface a clear hint but stay available
                # so the first real call returns the actionable 404 message.
                logger.warning(
                    "OllamaAI: model {} not installed (have: {}); "
                    "pull it with 'ollama pull {}'",
                    self._ollama.model,
                    ", ".join(installed[:5]),
                    self._ollama.model,
                )
            self._model_name = self._ollama.model
            self._is_available = True
            logger.info(
                "OllamaAI ready — model={} url={}", self._model_name, self._ollama.base_url
            )
        except Exception as exc:
            self.last_error = str(exc)
            self._is_available = False
            logger.warning("OllamaAI init failed: {}", exc)

    async def _ensure_init(self) -> None:
        """Await the background init task if still running."""
        if self._init_task is not None and not self._init_task.done():
            await self._init_task
        elif not self._is_available and not self.last_error:
            await self._async_init()

    # ── Task-plan analysis ────────────────────────────────────────────────────

    async def analyze_automation_request_async(
        self,
        user_request: str,
        context: dict[str, Any] | None = None,
    ) -> AITaskPlan:
        """Analyse a natural-language request into a structured plan."""
        await self._ensure_init()
        if not self._is_available:
            return self._fallback_plan(user_request)

        prompt = self._build_prompt(user_request, context or {})
        try:
            # Plans can enumerate many steps (e.g. "15 folders, a file in each");
            # the default budget truncates those mid-JSON. Give the plan call
            # more room — the salvage path in parse_task_plan is the backstop.
            raw = await self._call(prompt, max_tokens=4096)
            task_plan = parse_task_plan(raw, user_request)
            return self._task_plan_to_legacy(task_plan)
        except Exception as exc:
            logger.error("analyze_automation_request_async failed: {}", exc)
            return self._fallback_plan(user_request)

    def analyze_automation_request(
        self,
        user_request: str,
        context: dict[str, Any] | None = None,
    ) -> AITaskPlan:
        """Blocking wrapper around :meth:`analyze_automation_request_async`."""
        try:
            return self._run_sync(
                self.analyze_automation_request_async(user_request, context)
            )
        except Exception as exc:
            logger.warning("analyze_automation_request sync wrapper failed: {}", exc)
            return self._fallback_plan(user_request)

    # ── Conversation ──────────────────────────────────────────────────────────

    async def converse_async(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        """Return a conversational (non-automation) reply to ``message``."""
        await self._ensure_init()
        if not self._is_available:
            return (
                f"AI is not available. Is Ollama running at {self._ollama.base_url}? "
                "You can still issue automation commands directly."
            )
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _CHAT_SYSTEM_PROMPT.strip()}
        ]
        if history:
            # Keep the tail so we stay well under the context budget.
            messages.extend(history[-10:])
        messages.append({"role": "user", "content": message})
        try:
            reply = await self._ollama.complete(messages, temperature=0.6, max_tokens=1024)
        except Exception as exc:
            logger.warning("converse_async failed: {}", exc)
            return f"[AI error: {exc}]"
        return reply or (
            "The model returned an empty response. Try rephrasing, or check "
            "that the Ollama model is loaded."
        )

    def converse(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        """Blocking wrapper around :meth:`converse_async`."""
        try:
            return self._run_sync(self.converse_async(message, history))
        except Exception as exc:
            logger.warning("converse sync wrapper failed: {}", exc)
            return f"[AI error: {exc}]"

    async def stream_response(self, prompt: str) -> AsyncIterator[str]:
        """Yield incremental text tokens from a streaming conversational reply."""
        await self._ensure_init()
        if not self._is_available:
            yield (
                f"AI is not available. Is Ollama running at {self._ollama.base_url}?"
            )
            return
        self._context_window.add_user(prompt)
        accumulated: list[str] = []
        try:
            async for chunk in self._ollama.stream(
                self._context_window.get_messages(), temperature=0.7, max_tokens=1024
            ):
                accumulated.append(chunk)
                yield chunk
        except Exception as exc:
            logger.error("stream_response error: {}", exc)
            yield f"\n[Stream error: {exc}]"
        finally:
            self._context_window.add_assistant("".join(accumulated))

    # ── Suggestions / enhancement helpers ─────────────────────────────────────

    def generate_smart_suggestions(self, context: dict[str, Any]) -> list[str]:
        """Return AI-powered automation suggestions."""
        if not self._is_available:
            return ["Start Ollama for AI-powered suggestions", "create folder myproject"]
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
        """Enhance a command with AI insights."""
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
        """Return AI suggestions for a failed command."""
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
        """Ask AI to suggest workflow optimisations."""
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

    def generate_code(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate raw code/text for ``prompt`` (empty string when unavailable).

        Strips a leading/trailing markdown code fence if the model wraps its
        output. Returns ``""`` on any failure so callers fall back cleanly.
        """
        if not self._is_available:
            return ""
        try:
            messages = [
                {
                    "role": "system",
                    "content": (system_prompt or "You are an expert code generator. "
                                "Return only code, no explanations or markdown."),
                },
                {"role": "user", "content": prompt},
            ]
            raw = self._run_sync(
                self._ollama.complete(messages, temperature=0.7, max_tokens=2000)
            )
            code = (raw or "").strip()
            if code.startswith("```"):
                lines = code.split("\n")
                if lines[0].startswith("```"):
                    code = "\n".join(lines[1:])
                if code.endswith("```"):
                    code = code[:-3]
                code = code.strip()
            return code
        except Exception as exc:
            logger.warning("generate_code failed: {}", exc)
            return ""

    def generate_document(self, request: str, filename: str = "") -> str:
        """Generate prose/markdown document body for a natural-language request.

        Unlike :meth:`generate_code`, this keeps markdown formatting (headings,
        lists, tables) intact — only an outer ```` ``` ```` fence wrapping the
        whole reply is stripped. Returns ``""`` on any failure so callers can
        fall back to writing an empty file rather than crashing.
        """
        if not self._is_available:
            return ""
        try:
            target = f" The file is named '{filename}'." if filename else ""
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a technical writer. Produce a complete, well-structured "
                        "document in GitHub-flavored Markdown for the user's request. "
                        "Use headings, lists, and tables where helpful. Write the full "
                        "content — do not summarize, describe, or leave placeholders. "
                        "Output only the document body, with no preamble or commentary."
                    ),
                },
                {"role": "user", "content": f"{request}{target}"},
            ]
            raw = self._run_sync(
                self._ollama.complete(
                    messages,
                    temperature=0.7,
                    max_tokens=4000,
                    timeout=_DOCUMENT_TIMEOUT,
                ),
                timeout=_DOCUMENT_TIMEOUT + 30,
            )
            text = (raw or "").strip()
            # Strip a single outer fence if the model wrapped the whole document.
            if text.startswith("```"):
                lines = text.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                text = "\n".join(lines).strip()
            return text
        except Exception as exc:
            logger.warning("generate_document failed: {}", exc)
            return ""

    # ── Model management / status ──────────────────────────────────────────────

    def set_model(self, model_name: str) -> bool:
        """Override the active model (validation deferred to next call)."""
        self._model_name = model_name
        self._ollama.model = model_name
        logger.info("OllamaAI: model set to {}", model_name)
        return True

    def get_available_models(self) -> dict[str, str]:
        """Return an ``model_id -> name`` map of installed Ollama models."""
        try:
            names = asyncio.run(self._ollama.list_models())
            return {name: name for name in names}
        except Exception:
            return {}

    def is_ready(self) -> bool:
        """Return ``True`` when the AI integration is operational."""
        return self._is_available

    def get_ai_status(self) -> dict[str, Any]:
        """Return a status summary dict."""
        return {
            "available": self._is_available,
            "model": self._model_name if self._is_available else None,
            "provider": "Ollama",
            "url": self._ollama.base_url,
            "last_error": self.last_error,
            "available_models": list(self.get_available_models().keys()),
        }

    def get_current_model(self) -> str:
        """Return the active model id, or ``"None"`` when not initialised."""
        return self._model_name if self._is_available else "None"

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _call(self, prompt: str, *, temperature: float = 0.3, max_tokens: int = 2048) -> str:
        """Make a single async completion call through the Ollama backend."""
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT.strip()},
            {"role": "user", "content": prompt},
        ]
        return await self._ollama.complete(
            messages, temperature=temperature, max_tokens=max_tokens
        )

    @staticmethod
    def _run_sync(coro: Any, timeout: float | None = 180) -> Any:
        """Run ``coro`` to completion whether or not a loop is already running.

        ``timeout`` caps the wait only when a loop is already running (the
        worker-thread path). Long generations such as full documents pass a
        larger value; ``None`` waits indefinitely.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        # A loop is already running in this thread — offload to a worker thread
        # so we don't try to nest event loops.
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result(timeout=timeout)

    @staticmethod
    def _fallback_plan(user_request: str) -> AITaskPlan:
        return AITaskPlan(
            original_request=user_request,
            interpreted_intent=f"Basic interpretation: {user_request}",
            confidence_score=0.2,
            execution_steps=[],
            risk_assessment={"level": "unknown", "concerns": ["AI unavailable"], "mitigations": []},
            optimization_suggestions=["Start Ollama to enable AI planning"],
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
