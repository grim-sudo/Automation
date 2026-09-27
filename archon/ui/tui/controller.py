"""Controller between Archon's engine/agent and the Textual UI.

This is the seam the spec asks for: the UI is a *client* of Archon's systems,
never their owner. The controller builds and holds the engine and the
Ollama+MCP agent, exposes read-only facts (model, plugins, capabilities,
context usage) for the sidebar, and runs one agent turn synchronously so a
Textual worker thread can drive it.

No Textual imports live here — the app injects its confirmer and event sink,
and this module stays a plain, testable controller.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from ...utils.logger import get_logger

ConfirmFn = Callable[[str, dict[str, Any], Any], bool]
EventFn = Callable[[dict[str, Any]], None]


class AgentController:
    """Owns the engine + agent and answers the sidebar's questions."""

    def __init__(self, engine: Any = None) -> None:
        self.logger = get_logger("TUIController")
        self._engine = engine
        self._agent: Any = None
        # Injected by the app before the first run.
        self.confirmer: ConfirmFn | None = None
        self.on_event: EventFn | None = None

    # ── engine / agent ────────────────────────────────────────────────────────

    @property
    def engine(self) -> Any:
        if self._engine is None:
            try:
                from archon._cli import _build_engine

                self._engine = _build_engine()
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.error(f"Failed to build engine: {exc}")
                from archon.core.engine import Archon

                self._engine = Archon()
        return self._engine

    @property
    def agent(self) -> Any:
        """Build the Ollama+MCP agent on first use, wiring the app's hooks."""
        if self._agent is None:
            from archon.mcp.agent import OllamaMCPAgent

            self._agent = OllamaMCPAgent(
                engine=self.engine,
                confirmer=self.confirmer,
                on_event=self.on_event,
            )
        return self._agent

    def run(
        self,
        message: str,
        *,
        on_token: Callable[[str], None] | None = None,
        on_stats: Callable[[dict[str, Any]], None] | None = None,
    ) -> str:
        """Run one agent turn to completion. Blocking — call from a worker."""
        return asyncio.run(self.agent.run(message, on_token=on_token, on_stats=on_stats))

    # ── facts for the sidebar / header ─────────────────────────────────────────

    def _ollama_ai(self) -> Any:
        ai = getattr(getattr(self.engine, "ai_parser", None), "ai", None)
        if ai is None or not getattr(ai, "is_available", False):
            return None
        return ai

    def intelligence(self) -> dict[str, Any]:
        """Model/backend facts. Values are ``None`` when AI is offline."""
        ai = self._ollama_ai()
        if ai is None:
            return {"model": None, "backend": None, "online": False}
        return {
            "model": ai.get_current_model(),
            "backend": "Ollama",
            "online": True,
        }

    def context_usage(self) -> tuple[int, int]:
        """Approximate (used_tokens, window_tokens) for the live conversation.

        Ollama does not expose a running context-fill figure, so this estimates
        from the message payload (≈4 chars/token). The window is the configured
        context size. Returned as a rough gauge, never presented as exact.
        """
        window = 8000
        try:
            from archon.config import get_config

            window = int(get_config().ai.max_tokens)
        except Exception:
            pass
        used = 0
        if self._agent is not None:
            for msg in self._agent.messages:
                used += len(str(msg.get("content", "")))
        return used // 4, window

    def plugin_count(self) -> int | None:
        try:
            return len(self.engine.plugin_manager.get_available_plugins())
        except Exception:
            return None

    def capability_count(self) -> int | None:
        try:
            return len(self.engine.describe_capabilities())
        except Exception:
            return None

    # ── model selection ─────────────────────────────────────────────────────────

    def model_ids(self) -> list[str]:
        ai = self._ollama_ai()
        if ai is None:
            return []
        return list(ai.get_available_models().keys())

    def current_model(self) -> str | None:
        ai = self._ollama_ai()
        return ai.get_current_model() if ai is not None else None

    def switch_model(self, model_id: str) -> bool:
        try:
            self.engine.switch_ai_model(model_id)
            self._agent = None  # rebuild so the provider picks up the new model
            return True
        except Exception as exc:
            self.logger.error(f"Failed to switch model: {exc}")
            return False

    def shutdown(self) -> None:
        if self._engine is not None:
            try:
                self._engine.shutdown()
            except Exception:  # pragma: no cover - defensive
                pass
