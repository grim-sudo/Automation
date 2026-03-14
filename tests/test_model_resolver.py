"""Tests for the FreeModelResolver (model_resolver.py).

Mocks httpx.AsyncClient to avoid real HTTP calls.  Each test resets the
resolver state via invalidate() so tests are independent.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers to build fake model payloads
# ---------------------------------------------------------------------------


def _make_model(
    model_id: str,
    context_length: int = 8192,
    prompt_price: str = "0",
    completion_price: str = "0",
    name: str | None = None,
) -> dict:
    return {
        "id": model_id,
        "name": name or model_id,
        "context_length": context_length,
        "pricing": {
            "prompt": prompt_price,
            "completion": completion_price,
        },
    }


FREE_MODELS_PAYLOAD = {
    "data": [
        _make_model("free/small", context_length=4096),
        _make_model("free/large", context_length=32768),
        _make_model("free/huge", context_length=131072),
        _make_model(
            "paid/gpt4", context_length=128000, prompt_price="0.01", completion_price="0.03"
        ),
        _make_model(
            "paid/claude", context_length=200000, prompt_price="0.003", completion_price="0.015"
        ),
    ]
}

ONLY_PAID_PAYLOAD = {
    "data": [
        _make_model("paid/a", prompt_price="0.01", completion_price="0.02"),
        _make_model("paid/b", prompt_price="0.005", completion_price="0.015"),
    ]
}

EMPTY_PAYLOAD: dict = {"data": []}

_FAKE_API_KEY = "sk-or-test-key-1234"


# ---------------------------------------------------------------------------
# Import under test (guard against missing optional deps)
# ---------------------------------------------------------------------------

try:
    from omni_automator.ai.model_resolver import FreeModelResolver, ModelInfo, get_resolver

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="model_resolver not importable")


# ---------------------------------------------------------------------------
# Async httpx mock helper
# ---------------------------------------------------------------------------


def _make_async_client_mock(payload: dict):
    """
    Return a context-manager mock for httpx.AsyncClient that responds with
    the given JSON payload on GET requests.
    """
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = payload

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    mock_cls = MagicMock(return_value=mock_client)
    return mock_cls


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def resolver() -> FreeModelResolver:
    """Return a fresh, un-cached resolver with a fake API key."""
    r = FreeModelResolver(api_key=_FAKE_API_KEY)
    r.invalidate()
    return r


# ---------------------------------------------------------------------------
# Tests: basic free model filtering and sorting
# ---------------------------------------------------------------------------


class TestFreeModelFiltering:
    def test_filters_out_paid_models(self, resolver: FreeModelResolver) -> None:
        """Paid models must not appear in the free list."""
        with patch("httpx.AsyncClient", _make_async_client_mock(FREE_MODELS_PAYLOAD)):
            asyncio.run(resolver.ensure_loaded())

        ids = [m.model_id for m in resolver.fallback_chain()]
        assert "paid/gpt4" not in ids
        assert "paid/claude" not in ids

    def test_keeps_free_models(self, resolver: FreeModelResolver) -> None:
        """All free models must appear after filtering."""
        with patch("httpx.AsyncClient", _make_async_client_mock(FREE_MODELS_PAYLOAD)):
            asyncio.run(resolver.ensure_loaded())

        ids = [m.model_id for m in resolver.fallback_chain()]
        assert "free/small" in ids
        assert "free/large" in ids
        assert "free/huge" in ids

    def test_sorted_by_context_length_descending(self, resolver: FreeModelResolver) -> None:
        """Free models must be sorted with the largest context first."""
        with patch("httpx.AsyncClient", _make_async_client_mock(FREE_MODELS_PAYLOAD)):
            asyncio.run(resolver.ensure_loaded())

        chain = resolver.fallback_chain()
        lengths = [m.context_length for m in chain]
        assert lengths == sorted(lengths, reverse=True)

    def test_default_model_is_largest_context(self, resolver: FreeModelResolver) -> None:
        """default_model() must return the model with the most tokens."""
        with patch("httpx.AsyncClient", _make_async_client_mock(FREE_MODELS_PAYLOAD)):
            asyncio.run(resolver.ensure_loaded())

        default = resolver.default_model()
        assert default.model_id == "free/huge"
        assert default.context_length == 131072


# ---------------------------------------------------------------------------
# Tests: edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_response_raises(self, resolver: FreeModelResolver) -> None:
        """If no free models are found, ensure_loaded must raise RuntimeError."""
        with patch("httpx.AsyncClient", _make_async_client_mock(EMPTY_PAYLOAD)):
            with pytest.raises(RuntimeError, match="no free models"):
                asyncio.run(resolver.ensure_loaded())

    def test_only_paid_models_raises(self, resolver: FreeModelResolver) -> None:
        """If all models are paid, the resolver must signal RuntimeError."""
        with patch("httpx.AsyncClient", _make_async_client_mock(ONLY_PAID_PAYLOAD)):
            with pytest.raises(RuntimeError):
                asyncio.run(resolver.ensure_loaded())

    def test_network_error_raises(self, resolver: FreeModelResolver) -> None:
        """A network error during fetch must propagate as RuntimeError."""
        import httpx as _httpx

        failing_client = AsyncMock()
        failing_client.get = AsyncMock(side_effect=_httpx.HTTPError("connection refused"))
        failing_client.__aenter__ = AsyncMock(return_value=failing_client)
        failing_client.__aexit__ = AsyncMock(return_value=False)
        failing_cls = MagicMock(return_value=failing_client)

        with patch("httpx.AsyncClient", failing_cls), pytest.raises(RuntimeError):
            asyncio.run(resolver.ensure_loaded())

    def test_partial_pricing_keys(self, resolver: FreeModelResolver) -> None:
        """Models with missing pricing keys should be excluded (treated as paid)."""
        payload = {
            "data": [
                {"id": "mystery/model", "name": "?", "context_length": 8192, "pricing": {}},
                _make_model("free/known", context_length=4096),
            ]
        }
        with patch("httpx.AsyncClient", _make_async_client_mock(payload)):
            asyncio.run(resolver.ensure_loaded())

        ids = [m.model_id for m in resolver.fallback_chain()]
        assert "mystery/model" not in ids
        assert "free/known" in ids

    def test_empty_api_key_raises_on_init(self) -> None:
        """Constructing a resolver with an empty api_key must raise ValueError."""
        with pytest.raises(ValueError, match="API key"):
            FreeModelResolver(api_key="")

    def test_require_loaded_raises_before_ensure(self, resolver: FreeModelResolver) -> None:
        """Calling default_model() without ensure_loaded() must raise RuntimeError."""
        with pytest.raises(RuntimeError, match="not been loaded"):
            resolver.default_model()


# ---------------------------------------------------------------------------
# Tests: caching behaviour
# ---------------------------------------------------------------------------


class TestCaching:
    def test_second_ensure_loaded_does_not_re_fetch(self, resolver: FreeModelResolver) -> None:
        """After a successful load, ensure_loaded must not issue another HTTP call."""
        mock_cls = _make_async_client_mock(FREE_MODELS_PAYLOAD)
        with patch("httpx.AsyncClient", mock_cls):
            asyncio.run(resolver.ensure_loaded())
            asyncio.run(resolver.ensure_loaded())  # second call

        # AsyncClient was instantiated only once
        assert mock_cls.call_count == 1

    def test_invalidate_forces_refetch(self, resolver: FreeModelResolver) -> None:
        """After invalidate(), ensure_loaded must re-fetch from the network."""
        mock_cls = _make_async_client_mock(FREE_MODELS_PAYLOAD)
        with patch("httpx.AsyncClient", mock_cls):
            asyncio.run(resolver.ensure_loaded())
            resolver.invalidate()
            asyncio.run(resolver.ensure_loaded())

        assert mock_cls.call_count == 2

    def test_ttl_expiry_triggers_refetch(self, resolver: FreeModelResolver) -> None:
        """After the TTL expires, the next ensure_loaded call must re-fetch."""
        mock_cls = _make_async_client_mock(FREE_MODELS_PAYLOAD)
        with patch("httpx.AsyncClient", mock_cls):
            asyncio.run(resolver.ensure_loaded())
            # Wind the cached timestamp back by more than 1 hour
            resolver._fetched_at = time.monotonic() - 3700  # type: ignore[attr-defined]
            asyncio.run(resolver.ensure_loaded())

        assert mock_cls.call_count == 2


# ---------------------------------------------------------------------------
# Tests: ModelInfo data class
# ---------------------------------------------------------------------------


class TestModelInfo:
    def test_model_info_fields(self, resolver: FreeModelResolver) -> None:
        """ModelInfo objects must expose model_id, context_length, and name."""
        with patch("httpx.AsyncClient", _make_async_client_mock(FREE_MODELS_PAYLOAD)):
            asyncio.run(resolver.ensure_loaded())

        default = resolver.default_model()
        assert hasattr(default, "model_id")
        assert hasattr(default, "context_length")
        assert hasattr(default, "name")
        assert isinstance(default.model_id, str)
        assert isinstance(default.context_length, int)

    def test_model_info_repr(self) -> None:
        """ModelInfo __repr__ must include the model_id."""
        m = ModelInfo(model_id="test/model", context_length=4096, name="Test Model")
        assert "test/model" in repr(m)


# ---------------------------------------------------------------------------
# Tests: get_resolver() singleton
# ---------------------------------------------------------------------------


class TestGetResolverSingleton:
    def test_get_resolver_returns_same_instance(self) -> None:
        """Repeated calls to get_resolver() must return the same object."""
        # Patch get_config so no real config file is needed
        mock_cfg = MagicMock()
        mock_cfg.openrouter_api_key = _FAKE_API_KEY
        with patch("omni_automator.ai.model_resolver.get_config", return_value=mock_cfg):
            # Reset the module-level singleton so we can test creation
            import omni_automator.ai.model_resolver as _mr

            original = _mr._resolver
            _mr._resolver = None
            try:
                r1 = get_resolver()
                r2 = get_resolver()
                assert r1 is r2
            finally:
                _mr._resolver = original

    def test_get_resolver_returns_free_model_resolver(self) -> None:
        """The singleton must be a FreeModelResolver instance."""
        mock_cfg = MagicMock()
        mock_cfg.openrouter_api_key = _FAKE_API_KEY
        with patch("omni_automator.ai.model_resolver.get_config", return_value=mock_cfg):
            import omni_automator.ai.model_resolver as _mr

            original = _mr._resolver
            _mr._resolver = None
            try:
                assert isinstance(get_resolver(), FreeModelResolver)
            finally:
                _mr._resolver = original
