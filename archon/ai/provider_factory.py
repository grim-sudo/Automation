"""Provider factory for Archon's AI backends.

Chooses the active chat provider from config (``ai.provider``) and constructs
it, so the AI facade and the MCP agent share one selection path instead of both
hardcoding :class:`OllamaProvider`.

Supported providers:
  * ``ollama``     — local Ollama server (no key).
  * ``freellmapi`` — local OpenAI-compatible router (:class:`OpenAICompatibleProvider`).
  * ``openai``     — OpenAI (:class:`OpenAICompatibleProvider`).
  * ``anthropic``  — Anthropic Messages API (:class:`AnthropicProvider`).

A chosen cloud provider is probed once synchronously with a short timeout; if it
is unreachable (or unconfigured), the factory falls back to local Ollama so the
app still works. All providers expose the same
``is_available``/``list_models``/``complete``/``chat`` surface, returning the
Ollama-style ``message`` dict from ``chat``.
"""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

__all__ = ["build_provider"]

# ponytail: fixed short probe budget for the synchronous reachability check.
# A cloud endpoint that can't answer /models in this window is treated as down
# and we fall back to Ollama. Upgrade path: make it configurable if a slow but
# valid remote endpoint ever needs a longer floor.
_PROBE_TIMEOUT = 4.0


def _ollama_provider(cfg: Any) -> Any:
    """Build an :class:`OllamaProvider` from config (the fallback backend)."""
    from .ollama_integration import OllamaProvider

    model = cfg.ai.model or getattr(cfg.ai, "ollama_model", "") or "qwen3.5:9b"
    return OllamaProvider(
        base_url=getattr(cfg.ai, "ollama_url", "") or "http://127.0.0.1:11434",
        model=model,
        # Local reasoning models need a generous floor; the cloud-tuned default
        # (30s) starves them mid-thought on a cold model load.
        timeout=max(float(cfg.ai.timeout), 120.0),
    )


def _probe_reachable(url: str, headers: dict[str, str]) -> bool:
    """Synchronously GET ``url``; ``True`` on a non-5xx/non-error response.

    Runs before the event loop is up (factory is called from ``__init__`` and
    worker threads), so it uses a blocking client with a short timeout rather
    than the async client the providers use at call time.
    """
    try:
        resp = httpx.get(url, headers=headers, timeout=_PROBE_TIMEOUT)
    except httpx.HTTPError as exc:
        logger.warning("Provider probe failed for {}: {}", url, exc)
        return False
    # 4xx (e.g. auth) still proves the endpoint is up; 5xx means it's broken.
    return resp.status_code < 500


def build_provider(cfg: Any | None = None, *, model: str | None = None) -> Any:
    """Return the configured chat provider, falling back to Ollama when down.

    Args:
        cfg:   A loaded config; ``get_config()`` is used when ``None``.
        model: Optional model override applied to the chosen provider.
    """
    if cfg is None:
        from ..config import get_config

        cfg = get_config()

    provider = (getattr(cfg.ai, "provider", "") or "ollama").strip().lower()
    timeout = max(float(cfg.ai.timeout), 120.0)

    if provider in ("ollama", ""):
        prov = _ollama_provider(cfg)
        if model:
            prov.model = model
        return prov

    if provider in ("freellmapi", "openai"):
        from .openai_compat import OpenAICompatibleProvider

        if provider == "freellmapi":
            base_url = getattr(cfg.ai, "freellmapi_url", "") or "http://localhost:3001/v1"
            api_key = getattr(cfg.ai, "freellmapi_api_key", "") or ""
            used_model = model or getattr(cfg.ai, "freellmapi_model", "") or "auto"
        else:
            base_url = getattr(cfg.ai, "openai_url", "") or "https://api.openai.com/v1"
            api_key = getattr(cfg.ai, "openai_api_key", "") or ""
            used_model = model or getattr(cfg.ai, "openai_model", "") or "gpt-4o-mini"

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        if _probe_reachable(f"{base_url.rstrip('/')}/models", headers):
            logger.info("AI provider: {} model={} url={}", provider, used_model, base_url)
            return OpenAICompatibleProvider(
                base_url=base_url,
                api_key=api_key,
                model=used_model,
                timeout=timeout,
                label=provider,
            )
        logger.warning(
            "AI provider {} unreachable at {}; falling back to Ollama",
            provider,
            base_url,
        )
        return _ollama_provider(cfg)

    if provider == "anthropic":
        from .anthropic_provider import AnthropicProvider

        base_url = getattr(cfg.ai, "anthropic_url", "") or "https://api.anthropic.com/v1"
        api_key = getattr(cfg.ai, "anthropic_api_key", "") or ""
        used_model = model or getattr(cfg.ai, "anthropic_model", "") or "claude-3-5-sonnet-latest"
        if not api_key:
            logger.warning("AI provider anthropic has no API key; falling back to Ollama")
            return _ollama_provider(cfg)
        headers = {
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
        if _probe_reachable(f"{base_url.rstrip('/')}/models", headers):
            logger.info("AI provider: anthropic model={} url={}", used_model, base_url)
            return AnthropicProvider(
                api_key=api_key, model=used_model, base_url=base_url, timeout=timeout
            )
        logger.warning(
            "AI provider anthropic unreachable at {}; falling back to Ollama", base_url
        )
        return _ollama_provider(cfg)

    logger.warning("Unknown AI provider {!r}; using Ollama", provider)
    prov = _ollama_provider(cfg)
    if model:
        prov.model = model
    return prov
