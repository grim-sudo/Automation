"""
Dynamic free-model resolver for OpenRouter.

On startup (or when the cache is stale), fetches all models from the
OpenRouter catalogue, filters for those with pricing.prompt == "0" AND
pricing.completion == "0", sorts by context_length descending, and
exposes:

  * ``default_model()``  — the single best free model (largest context)
  * ``fallback_chain()`` — the full ordered list used for retry logic

The result is cached in-process for 1 hour; a call to ``invalidate()``
forces a fresh fetch on the next access.

No model name is ever hardcoded here or anywhere else in the codebase.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from loguru import logger

from ..config import get_config

__all__ = [
    "ModelInfo",
    "FreeModelResolver",
    "get_resolver",
    "default_model",
    "fallback_chain",
]

_OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
_CACHE_TTL_SECONDS = 3600  # 1 hour


class ModelInfo:
    """
    Lightweight representation of a single OpenRouter model.

    Attributes:
        model_id:       Full model identifier as returned by the OpenRouter API.
        context_length: Maximum context window in tokens.
        name:           Human-readable display name.
    """

    __slots__ = ("model_id", "context_length", "name")

    def __init__(self, model_id: str, context_length: int, name: str) -> None:
        self.model_id = model_id
        self.context_length = context_length
        self.name = name

    def __repr__(self) -> str:
        return f"ModelInfo(id={self.model_id!r}, ctx={self.context_length})"


class FreeModelResolver:
    """
    Fetches, filters, and caches the OpenRouter free-model list.

    Usage::

        resolver = FreeModelResolver(api_key="sk-or-v1-...")
        await resolver.ensure_loaded()
        model = resolver.default_model()
        chain = resolver.fallback_chain()

    All model names used elsewhere in the codebase come from this class.
    """

    def __init__(self, api_key: str) -> None:
        """
        Args:
            api_key: OpenRouter API key (``sk-or-v1-...``).

        Raises:
            ValueError: If *api_key* is empty or ``None``.
        """
        if not api_key:
            raise ValueError(
                "OpenRouter API key is required for model resolution. "
                "Set OPENROUTER_API_KEY in environment or config."
            )
        self._api_key = api_key
        self._models: list[ModelInfo] = []
        self._fetched_at: float = 0.0
        self._lock = asyncio.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    async def ensure_loaded(self) -> None:
        """
        Guarantee the model list is fresh (cache TTL = 1 hour).

        This method is safe to call concurrently; only one fetch runs at a time.

        Raises:
            RuntimeError: If the OpenRouter API call fails and the cache is empty.
        """
        if self._is_fresh():
            return
        async with self._lock:
            if self._is_fresh():
                return
            await self._fetch_and_cache()

    def default_model(self) -> ModelInfo:
        """
        Return the highest-context-length free model.

        Returns:
            ModelInfo for the best available free model.

        Raises:
            RuntimeError: If ``ensure_loaded()`` has not been awaited yet.
        """
        self._require_loaded()
        return self._models[0]

    def fallback_chain(self) -> list[ModelInfo]:
        """
        Return the complete ordered list of free models, best-first.

        Returns:
            List of ModelInfo, sorted by context_length descending.

        Raises:
            RuntimeError: If ``ensure_loaded()`` has not been awaited yet.
        """
        self._require_loaded()
        return list(self._models)

    def invalidate(self) -> None:
        """Force a fresh fetch on the next ``ensure_loaded()`` call."""
        self._models = []
        self._fetched_at = 0.0

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _is_fresh(self) -> bool:
        return bool(self._models) and (time.monotonic() - self._fetched_at) < _CACHE_TTL_SECONDS

    def _require_loaded(self) -> None:
        if not self._models:
            raise RuntimeError(
                "Free model list has not been loaded yet. "
                "Await resolver.ensure_loaded() before accessing models."
            )

    async def _fetch_and_cache(self) -> None:
        """
        Fetch models from OpenRouter and populate self._models.

        Raises:
            RuntimeError: On any HTTP or parsing failure.
        """
        logger.debug("Fetching free models from OpenRouter…")
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "HTTP-Referer": "https://tyranos.local",
            "X-Title": "Tyranos",
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(_OPENROUTER_MODELS_URL, headers=headers)
                resp.raise_for_status()
                data: dict[str, Any] = resp.json()
        except httpx.HTTPError as exc:
            self._raise_resolution_error(str(exc))
            return  # unreachable; satisfies type-checkers
        except Exception as exc:
            self._raise_resolution_error(str(exc))
            return

        raw_models: list[dict[str, Any]] = data.get("data", [])
        free: list[ModelInfo] = []
        for m in raw_models:
            pricing = m.get("pricing", {})
            if (
                str(pricing.get("prompt", "1")) == "0"
                and str(pricing.get("completion", "1")) == "0"
            ):
                free.append(
                    ModelInfo(
                        model_id=m["id"],
                        context_length=int(m.get("context_length", 0)),
                        name=m.get("name", m["id"]),
                    )
                )

        if not free:
            self._raise_resolution_error("API returned no free models")
            return

        free.sort(key=lambda m: m.context_length, reverse=True)
        self._models = free
        self._fetched_at = time.monotonic()
        logger.info(
            "Resolved {} free models; default={}",
            len(free),
            free[0].model_id,
        )

    @staticmethod
    def _raise_resolution_error(detail: str) -> None:
        raise RuntimeError(
            f"Could not resolve free models from OpenRouter. "
            f"Check your API key and internet connection. Detail: {detail}"
        )


# ---------------------------------------------------------------------------
# Process-level singleton
# ---------------------------------------------------------------------------

_resolver: FreeModelResolver | None = None


def get_resolver() -> FreeModelResolver:
    """
    Return the process-wide FreeModelResolver, creating it on first call.

    Returns:
        FreeModelResolver instance.

    Raises:
        ValueError: If OPENROUTER_API_KEY is not configured.
    """
    global _resolver
    if _resolver is None:
        cfg = get_config()
        _resolver = FreeModelResolver(cfg.ai.openrouter_api_key)
    return _resolver


# ---------------------------------------------------------------------------
# Convenience sync helpers (for non-async callers)
# ---------------------------------------------------------------------------


def default_model() -> ModelInfo:
    """
    Synchronous shortcut: return the default free model.

    Internally runs ``ensure_loaded()`` in a new event loop if needed.

    Returns:
        Best-context-length free ModelInfo.

    Raises:
        RuntimeError: If model resolution fails.
    """
    resolver = get_resolver()
    if not resolver._is_fresh():
        asyncio.run(resolver.ensure_loaded())
    return resolver.default_model()


def fallback_chain() -> list[ModelInfo]:
    """
    Synchronous shortcut: return the full ordered fallback chain.

    Returns:
        List of ModelInfo sorted by context_length descending.

    Raises:
        RuntimeError: If model resolution fails.
    """
    resolver = get_resolver()
    if not resolver._is_fresh():
        asyncio.run(resolver.ensure_loaded())
    return resolver.fallback_chain()
