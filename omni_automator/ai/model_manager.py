"""
AI model manager with priority-ordered fallback chain and per-provider routing.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx

from .openrouter_integration import (
    AIProviderError,
    OpenRouterClient,
    OpenRouterConfig,
    StreamChunk,
)

logger = logging.getLogger(__name__)

__all__ = [
    "ModelProvider",
    "ModelRoute",
    "AISettings",
    "ModelManager",
    # Legacy names kept for backward compatibility with code that imports
    # these symbols via omni_automator.ai.model_manager directly.
    "AIModelConfig",
    "AIModelManager",
    "get_ai_manager",
]


# ---------------------------------------------------------------------------
# Enums and primary dataclasses
# ---------------------------------------------------------------------------


class ModelProvider(Enum):
    """Supported AI model providers."""

    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL_OLLAMA = "local_ollama"


@dataclass
class ModelRoute:
    """A single entry in the model routing table."""

    model_id: str
    provider: ModelProvider
    priority: int = 0


@dataclass
class AISettings:
    """
    Settings consumed by :class:`ModelManager`.

    Can be constructed directly, from environment variables via
    :meth:`from_env`, or from an ``OmniConfig`` instance via
    :meth:`from_config`.
    """

    api_key: str = ""
    fallback_chain: list[str] = field(default_factory=list)
    timeout: float = 60.0
    max_retries: int = 3
    default_model: str = ""

    @classmethod
    def from_env(cls) -> AISettings:
        """Build :class:`AISettings` from environment variables."""
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        default_model = os.getenv("OPENROUTER_MODEL", "")
        raw_chain = os.getenv("OPENROUTER_FALLBACK_CHAIN", "").strip()

        if raw_chain:
            if raw_chain.startswith("["):
                try:
                    chain: list[str] = json.loads(raw_chain)
                except json.JSONDecodeError:
                    chain = [m.strip() for m in raw_chain.split(",") if m.strip()]
            else:
                chain = [m.strip() for m in raw_chain.split(",") if m.strip()]
        else:
            # Fall back to the single configured model as the entire chain.
            chain = [default_model] if default_model else []

        try:
            timeout = float(os.getenv("OPENROUTER_TIMEOUT", "60"))
        except ValueError:
            timeout = 60.0

        try:
            max_retries = int(os.getenv("OPENROUTER_MAX_RETRIES", "3"))
        except ValueError:
            max_retries = 3

        return cls(
            api_key=api_key,
            fallback_chain=chain,
            timeout=timeout,
            max_retries=max_retries,
            default_model=default_model,
        )

    @classmethod
    def from_config(cls, config: Any) -> AISettings:
        """
        Build :class:`AISettings` from an ``OmniConfig`` (or any object that
        exposes the same attribute names).
        """
        api_key: str = getattr(config, "openrouter_api_key", "") or ""
        max_retries: int = int(getattr(config, "max_retries", 3))
        # OmniConfig.retry_delay is the per-retry sleep, so use it as a hint.
        timeout: float = float(getattr(config, "retry_delay", 2.0)) * max_retries * 5
        return cls(
            api_key=api_key,
            max_retries=max_retries,
            timeout=max(30.0, timeout),
        )


# ---------------------------------------------------------------------------
# ModelManager
# ---------------------------------------------------------------------------


class ModelManager:
    """
    Async AI model manager with a priority-ordered fallback chain and
    per-provider request routing.

    Provider routing
    ----------------
    * ``openai/…``    — routed through OpenRouter (proxied to OpenAI).
    * ``anthropic/…`` — routed through OpenRouter (proxied to Anthropic).
    * ``google/…``    — routed through OpenRouter (proxied to Google).
    * ``local/…``     — sent directly to a running Ollama instance at
                        ``http://localhost:11434``.
    * anything else   — routed through OpenRouter.
    """

    _OLLAMA_BASE = "http://localhost:11434"

    def __init__(self, settings: AISettings | None = None) -> None:
        self._settings: AISettings = settings or AISettings.from_env()
        self._routes: list[ModelRoute] = self._build_routes()
        self._openrouter_client: OpenRouterClient | None = None
        self._local_client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    def _build_routes(self) -> list[ModelRoute]:
        """
        Construct a priority-ordered list of :class:`ModelRoute` objects from
        the ``fallback_chain`` in :attr:`_settings`.
        """
        routes: list[ModelRoute] = []
        for priority, model_id in enumerate(self._settings.fallback_chain):
            provider = self._detect_provider(model_id)
            routes.append(ModelRoute(model_id=model_id, provider=provider, priority=priority))
        return routes

    @staticmethod
    def _detect_provider(model_id: str) -> ModelProvider:
        """
        Infer the :class:`ModelProvider` from the *model_id* string prefix.

        Rules
        -----
        ``openai/``    → :attr:`ModelProvider.OPENAI`
        ``anthropic/`` → :attr:`ModelProvider.ANTHROPIC`
        ``local/``     → :attr:`ModelProvider.LOCAL_OLLAMA`
        anything else  → :attr:`ModelProvider.OPENROUTER`
        """
        lower = model_id.lower()
        if lower.startswith("openai/"):
            return ModelProvider.OPENAI
        if lower.startswith("anthropic/"):
            return ModelProvider.ANTHROPIC
        if lower.startswith("local/"):
            return ModelProvider.LOCAL_OLLAMA
        # google/ and all other vendor prefixes are served via OpenRouter.
        return ModelProvider.OPENROUTER

    # ------------------------------------------------------------------
    # Lazy client accessors
    # ------------------------------------------------------------------

    def _get_openrouter_client(self) -> OpenRouterClient:
        """Return (and lazily create) a shared :class:`OpenRouterClient`."""
        if self._openrouter_client is None:
            cfg = OpenRouterConfig(
                api_key=self._settings.api_key,
                model=self._settings.default_model,
                timeout=self._settings.timeout,
                max_retries=self._settings.max_retries,
            )
            self._openrouter_client = OpenRouterClient(cfg)
        return self._openrouter_client

    def _get_local_client(self) -> httpx.AsyncClient:
        """Return (and lazily create) a shared httpx client for Ollama."""
        if self._local_client is None:
            self._local_client = httpx.AsyncClient(
                base_url=self._OLLAMA_BASE,
                timeout=httpx.Timeout(self._settings.timeout),
            )
        return self._local_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def complete(
        self,
        messages: list[dict],
        preferred_model: str | None = None,
    ) -> tuple[str, str]:
        """
        Generate a completion for *messages*.

        If *preferred_model* is given it is tried first; then every model in
        the configured fallback chain is tried in priority order until one
        succeeds.

        Returns
        -------
        ``(content, model_used)``

        Raises
        ------
        :class:`~openrouter_integration.AIProviderError`
            When every available model in the chain fails.
        """
        # Deduplicated candidate list: preferred first, then the route chain.
        candidates: list[str] = []
        if preferred_model:
            candidates.append(preferred_model)
        for route in self._routes:
            if route.model_id not in candidates:
                candidates.append(route.model_id)

        if not candidates:
            raise AIProviderError(
                "No models configured in ModelManager and no preferred_model given.",
                model=None,
            )

        last_exc: Exception | None = None

        for model_id in candidates:
            provider = self._detect_provider(model_id)
            try:
                if provider == ModelProvider.LOCAL_OLLAMA:
                    content = await self._complete_ollama(messages, model_id)
                else:
                    # OPENROUTER, OPENAI, and ANTHROPIC are all proxied via
                    # OpenRouter.
                    client = self._get_openrouter_client()
                    content = await client.complete(messages, model=model_id)
                return content, model_id
            except Exception as exc:
                logger.warning(
                    "Model %r (provider=%s) failed: %s — trying next.",
                    model_id,
                    provider.value,
                    exc,
                )
                last_exc = exc

        raise AIProviderError(
            f"All {len(candidates)} model(s) failed. Last error: {last_exc}",
            model=candidates[-1] if candidates else None,
        )

    async def stream(
        self,
        messages: list[dict],
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream a completion for *messages* using the highest-priority route.

        Only models routed via OpenRouter support streaming.  ``LOCAL_OLLAMA``
        models raise :class:`~openrouter_integration.AIProviderError`.

        Yields
        ------
        :class:`~openrouter_integration.StreamChunk`
        """
        if not self._routes:
            raise AIProviderError(
                "No models configured in ModelManager; cannot stream.",
                model=None,
            )

        route = self._routes[0]

        if route.provider == ModelProvider.LOCAL_OLLAMA:
            raise AIProviderError(
                f"Streaming is not supported for LOCAL_OLLAMA provider "
                f"(model: {route.model_id!r}). "
                "Use ModelManager.complete() for Ollama models.",
                model=route.model_id,
            )

        client = self._get_openrouter_client()
        async for chunk in client.stream(messages, model=route.model_id):
            yield chunk

    async def close(self) -> None:
        """Close all underlying HTTP clients and release connections."""
        if self._openrouter_client is not None:
            await self._openrouter_client.close()
            self._openrouter_client = None
        if self._local_client is not None:
            await self._local_client.aclose()
            self._local_client = None

    # ------------------------------------------------------------------
    # Async context-manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> ModelManager:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Ollama helpers
    # ------------------------------------------------------------------

    async def _complete_ollama(self, messages: list[dict], model_id: str) -> str:
        """
        POST to the Ollama ``/api/chat`` endpoint (non-streaming).

        The ``local/`` prefix is stripped before forwarding to Ollama
        (e.g. ``local/llama3`` → ``llama3``).
        """
        ollama_model = model_id.removeprefix("local/")
        client = self._get_local_client()
        payload = {
            "model": ollama_model,
            "messages": messages,
            "stream": False,
        }
        response = await client.post("/api/chat", json=payload)
        if response.status_code >= 400:
            raise AIProviderError(
                f"Ollama returned HTTP {response.status_code}: {response.text}",
                status_code=response.status_code,
                model=model_id,
            )
        data: dict = response.json()
        # Ollama /api/chat response shape: {"message": {"role": "assistant", "content": "..."}}
        content = data.get("message", {}).get("content", "")
        if not content:
            # Some Ollama versions use a flat "response" key.
            content = data.get("response", "")
        return content


# ---------------------------------------------------------------------------
# Legacy compatibility shim
# ---------------------------------------------------------------------------
# The symbols below are kept so that existing code importing
# ``AIModelManager``, ``AIModelConfig``, or ``get_ai_manager`` from this
# module (or through ai/__init__.py) continues to work during the migration
# period.  New code should use ``ModelManager`` directly.
# ---------------------------------------------------------------------------

from dataclasses import dataclass as _dc  # noqa: E402


@_dc
class AIModelConfig:
    """Legacy model slot configuration.  Use AISettings + ModelManager instead."""

    name: str
    provider: str = "openrouter"
    model_id: str = ""
    api_key: str | None = None
    base_url: str | None = None
    max_tokens: int = 2048
    temperature: float = 0.7
    is_default: bool = False


class AIModelManager:
    """
    Legacy synchronous model manager shim.

    Wraps :class:`ModelManager` for callers that were written against the
    old synchronous ``AIModelManager`` API.  New code should use
    :class:`ModelManager` directly.
    """

    def __init__(self) -> None:
        self._settings = AISettings.from_env()
        self._slots: dict[str, AIModelConfig] = {}
        self._current_slot: str | None = None
        self._async_manager: ModelManager | None = None
        self._load_from_env()

    def _load_from_env(self) -> None:
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        model_id = os.getenv("OPENROUTER_MODEL", "")
        if api_key and model_id:
            cfg = AIModelConfig(
                name="default_openrouter",
                provider="openrouter",
                model_id=model_id,
                api_key=api_key,
                is_default=True,
            )
            self.register_model(cfg)

    def register_model(self, config: AIModelConfig) -> bool:
        self._slots[config.name] = config
        if config.is_default:
            self._current_slot = config.name
        return True

    def switch_model(self, model_name: str) -> bool:
        if model_name in self._slots:
            self._current_slot = model_name
            return True
        for name, cfg in self._slots.items():
            if cfg.model_id == model_name:
                self._current_slot = name
                return True
        return False

    def list_registered_models(self) -> dict[str, dict]:
        return {
            name: {
                "provider": cfg.provider,
                "model_id": cfg.model_id,
                "is_current": name == self._current_slot,
            }
            for name, cfg in self._slots.items()
        }

    def get_current_model_info(self) -> dict | None:
        if not self._current_slot or self._current_slot not in self._slots:
            return None
        cfg = self._slots[self._current_slot]
        return {
            "name": cfg.name,
            "provider": cfg.provider,
            "model_id": cfg.model_id,
            "max_tokens": cfg.max_tokens,
            "temperature": cfg.temperature,
        }

    def query(
        self,
        prompt: str,
        context: dict | None = None,
        model: str | None = None,
    ) -> dict:
        """Synchronous query — blocks the event loop; prefer async methods."""
        import asyncio

        settings = AISettings.from_env()
        if not settings.api_key:
            return {
                "content": "No OPENROUTER_API_KEY configured.",
                "model_used": "none",
                "tokens_used": 0,
                "provider": "none",
            }

        messages: list[dict] = [{"role": "user", "content": prompt}]
        if context:
            system_parts = [f"{k}: {v}" for k, v in context.items() if v]
            if system_parts:
                messages.insert(0, {"role": "system", "content": "\n".join(system_parts)})

        async def _run() -> tuple[str, str]:
            async with ModelManager(settings) as mgr:
                return await mgr.complete(messages, preferred_model=model)

        try:
            content, model_used = asyncio.run(_run())
        except Exception as exc:
            content = f"Error: {exc}"
            model_used = model or settings.default_model

        from datetime import datetime

        return {
            "content": content,
            "model_used": model_used,
            "tokens_used": len(content.split()),
            "provider": "openrouter",
            "timestamp": datetime.now().isoformat(),
        }

    def get_available_models(self) -> dict[str, list[str]]:
        return {"openrouter": list(self._slots.keys())}


# Process-level singleton for the legacy shim.
_ai_manager_instance: AIModelManager | None = None


def get_ai_manager() -> AIModelManager:
    """Return the process-wide legacy AIModelManager singleton."""
    global _ai_manager_instance
    if _ai_manager_instance is None:
        _ai_manager_instance = AIModelManager()
    return _ai_manager_instance
