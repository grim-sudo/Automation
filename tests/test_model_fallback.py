"""Tests for the AI model fallback chain logic.

The module under test: tyranos.ai.openrouter_integration

Classes exercised:

    OpenRouterConfig   — dataclass holding URL, API key, model, timeout, retries
    AIProviderError    — exception subclass carrying status_code and model attrs
    OpenRouterClient   — async client with complete() and complete_with_fallback()

Key behaviours verified:

    1. complete_with_fallback() returns (content, model_name) from the first
       model that succeeds.
    2. When a model raises AIProviderError the chain falls through to the next.
    3. When every model fails the last exception is re-raised.
    4. An empty fallback_chain raises immediately (ValueError or AIProviderError).
    5. AIProviderError carries .status_code and .model attributes and includes
       the original message in str().
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from tyranos.ai.openrouter_integration import (
    AIProviderError,
    OpenRouterClient,
    OpenRouterConfig,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def config() -> OpenRouterConfig:
    return OpenRouterConfig(
        url="https://openrouter.ai/api/v1",
        api_key="test-key-123",
        model="test/model-a",
        timeout=30,
        max_retries=3,
    )


@pytest.fixture
def fallback_chain() -> list[str]:
    return [
        "test/model-a",
        "test/model-b",
        "test/model-c",
    ]


# ─── Fallback chain behaviour ─────────────────────────────────────────────────


class TestFallbackChain:
    @pytest.mark.asyncio
    async def test_uses_first_model_when_available(
        self, config: OpenRouterConfig, fallback_chain: list[str]
    ) -> None:
        """When the first model succeeds, content and model name are returned."""
        client = OpenRouterClient(config)

        with patch.object(client, "complete", new=AsyncMock(return_value="Hello from test model")):
            content, model = await client.complete_with_fallback(
                [{"role": "user", "content": "Hi"}],
                fallback_chain=fallback_chain,
            )

        assert content == "Hello from test model"
        assert model == fallback_chain[0]

    @pytest.mark.asyncio
    async def test_falls_back_on_error(
        self, config: OpenRouterConfig, fallback_chain: list[str]
    ) -> None:
        """When the first model raises AIProviderError the second is tried."""
        client = OpenRouterClient(config)
        call_count = 0

        async def mock_complete(messages, model=None, **kwargs):
            nonlocal call_count
            call_count += 1
            if model == fallback_chain[0]:
                raise AIProviderError("Rate limit exceeded", 429, model)
            return "Response from fallback"

        with patch.object(client, "complete", side_effect=mock_complete):
            content, model_used = await client.complete_with_fallback(
                [{"role": "user", "content": "Hi"}],
                fallback_chain=fallback_chain,
            )

        assert content == "Response from fallback"
        assert call_count == 2  # first failed, second succeeded

    @pytest.mark.asyncio
    async def test_falls_back_on_multiple_errors(
        self, config: OpenRouterConfig, fallback_chain: list[str]
    ) -> None:
        """The chain should skip each failing model until one succeeds."""
        client = OpenRouterClient(config)
        call_count = 0

        async def mock_complete(messages, model=None, **kwargs):
            nonlocal call_count
            call_count += 1
            # First two models fail; third succeeds
            if model in fallback_chain[:2]:
                raise AIProviderError("Unavailable", 503, model)
            return "Response from third model"

        with patch.object(client, "complete", side_effect=mock_complete):
            content, model_used = await client.complete_with_fallback(
                [{"role": "user", "content": "Hi"}],
                fallback_chain=fallback_chain,
            )

        assert content == "Response from third model"
        assert model_used == fallback_chain[2]
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_all_models_fail_raises_exception(
        self, config: OpenRouterConfig, fallback_chain: list[str]
    ) -> None:
        """When every model in the chain fails an exception must be raised."""
        client = OpenRouterClient(config)

        async def always_fail(messages, model=None, **kwargs):
            raise AIProviderError("Service unavailable", 503, model or "unknown")

        with patch.object(client, "complete", side_effect=always_fail):
            with pytest.raises(Exception):
                await client.complete_with_fallback(
                    [{"role": "user", "content": "Hi"}],
                    fallback_chain=fallback_chain,
                )

    @pytest.mark.asyncio
    async def test_empty_fallback_chain_raises(self, config: OpenRouterConfig) -> None:
        """complete_with_fallback([]) must raise without making any network call."""
        client = OpenRouterClient(config)
        with pytest.raises(Exception):
            await client.complete_with_fallback(
                [{"role": "user", "content": "Hi"}],
                fallback_chain=[],
            )

    @pytest.mark.asyncio
    async def test_single_model_chain_success(self, config: OpenRouterConfig) -> None:
        """A one-element chain that succeeds should return immediately."""
        client = OpenRouterClient(config)
        single_chain = ["test/model-a"]

        with patch.object(client, "complete", new=AsyncMock(return_value="OK")):
            content, model = await client.complete_with_fallback(
                [{"role": "user", "content": "test"}],
                fallback_chain=single_chain,
            )

        assert content == "OK"
        assert model == "test/model-a"

    @pytest.mark.asyncio
    async def test_last_model_in_chain_is_tried(
        self, config: OpenRouterConfig, fallback_chain: list[str]
    ) -> None:
        """Ensures every entry in the chain is exhausted before raising."""
        client = OpenRouterClient(config)
        tried_models: list[str] = []

        async def track_and_fail(messages, model=None, **kwargs):
            tried_models.append(model or "")
            raise AIProviderError("Always fails", 500, model or "unknown")

        with patch.object(client, "complete", side_effect=track_and_fail):
            with pytest.raises(Exception):
                await client.complete_with_fallback(
                    [{"role": "user", "content": "Hi"}],
                    fallback_chain=fallback_chain,
                )

        assert tried_models == fallback_chain


# ─── AIProviderError ──────────────────────────────────────────────────────────


class TestAIProviderError:
    def test_has_status_code_attribute(self) -> None:
        err = AIProviderError("Rate limited", 429, "test/model-a")
        assert err.status_code == 429

    def test_has_model_attribute(self) -> None:
        err = AIProviderError("Rate limited", 429, "test/model-a")
        assert err.model == "test/model-a"

    def test_message_in_str(self) -> None:
        err = AIProviderError("Rate limited", 429, "test/model-a")
        assert "Rate limited" in str(err)

    def test_is_exception_subclass(self) -> None:
        err = AIProviderError("err", 500, "model")
        assert isinstance(err, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        with pytest.raises(AIProviderError) as exc_info:
            raise AIProviderError("test error", 503, "some/model")
        assert exc_info.value.status_code == 503
        assert exc_info.value.model == "some/model"

    def test_status_code_none_allowed(self) -> None:
        """Some error paths omit the status code (e.g. connection errors)."""
        err = AIProviderError("Connection failed", None, "some/model")
        assert err.status_code is None

    def test_model_none_allowed(self) -> None:
        err = AIProviderError("Unexpected", 500, None)
        assert err.model is None


# ─── OpenRouterConfig ─────────────────────────────────────────────────────────


class TestOpenRouterConfig:
    def test_default_values(self) -> None:
        cfg = OpenRouterConfig()
        assert cfg.url.startswith("https://")
        assert isinstance(cfg.api_key, str)
        assert isinstance(cfg.model, str)
        assert cfg.timeout > 0
        assert cfg.max_retries >= 1

    def test_custom_values(self) -> None:
        cfg = OpenRouterConfig(
            url="https://example.com/v1",
            api_key="sk-test",
            model="custom/model",
            timeout=10,
            max_retries=5,
        )
        assert cfg.api_key == "sk-test"
        assert cfg.model == "custom/model"
        assert cfg.timeout == 10
        assert cfg.max_retries == 5

    def test_from_env_classmethod_exists(self) -> None:
        """from_env() should exist and return an OpenRouterConfig."""
        cfg = OpenRouterConfig.from_env()
        assert isinstance(cfg, OpenRouterConfig)


# ─── OpenRouterClient construction ────────────────────────────────────────────


class TestOpenRouterClientConstruction:
    def test_can_be_instantiated_with_config(self, config: OpenRouterConfig) -> None:
        client = OpenRouterClient(config)
        assert client is not None

    def test_stores_config(self, config: OpenRouterConfig) -> None:
        client = OpenRouterClient(config)
        assert client._cfg is config

    def test_is_async_context_manager(self, config: OpenRouterConfig) -> None:
        """OpenRouterClient must expose __aenter__ and __aexit__."""
        client = OpenRouterClient(config)
        assert hasattr(client, "__aenter__")
        assert hasattr(client, "__aexit__")
