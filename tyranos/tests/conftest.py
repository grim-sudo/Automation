"""pytest configuration and shared fixtures for Tyranos tests.

Fixtures here are available to every test module automatically.  They are
kept intentionally small — each test file declares its own local fixtures
where more specificity is needed.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

# ─── Event loop policy ────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


# ─── Network guard — intercepts all real OpenRouter calls in every test ───────


@pytest.fixture(autouse=True)
def mock_openrouter_models(respx_mock: respx.MockRouter) -> None:
    """Block every test from hitting the real OpenRouter models endpoint.

    autouse=True means this fixture applies automatically to every test
    without the test having to request it explicitly.  Any test that
    constructs a FreeModelResolver (or any code path that calls
    GET https://openrouter.ai/api/v1/models) receives this canned response
    instead of making a live network request.
    """
    respx_mock.get("https://openrouter.ai/api/v1/models").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "test/free-model-large",
                        "context_length": 128000,
                        "pricing": {"prompt": "0", "completion": "0"},
                    },
                    {
                        "id": "test/free-model-medium",
                        "context_length": 32000,
                        "pricing": {"prompt": "0", "completion": "0"},
                    },
                    {
                        "id": "test/free-model-small",
                        "context_length": 8000,
                        "pricing": {"prompt": "0", "completion": "0"},
                    },
                ]
            },
        )
    )


# ─── Test configuration ───────────────────────────────────────────────────────


@pytest.fixture
def test_config() -> dict[str, str]:
    """Return a dict of dummy environment/config values safe for use in tests."""
    return {
        "OPENROUTER_API_KEY": "test-key-for-ci",
        "N8N_URL": "http://localhost:5678",
        "N8N_API_KEY": "test-n8n-key",
        "ANTHROPIC_API_KEY": "test-key-for-ci",
        "OPENAI_API_KEY": "test-key-for-ci",
    }


# ─── Shared AI response data ──────────────────────────────────────────────────

# A minimal task plan using the field names understood by the existing
# TaskPlan Pydantic model.  The "steps" key is normalised to
# "execution_steps" by the _normalise_steps model_validator.
SAMPLE_TASK_PLAN: dict[str, Any] = {
    "interpreted_intent": "Create a Python project",
    "confidence_score": 0.9,
    "steps": [
        {
            "action": "create_folder",
            "category": "filesystem",
            "params": {"name": "my_project"},
            "description": "Create project directory",
            "required": True,
            "priority": 0,
        }
    ],
}

# A minimal intent result compatible with the existing IntentResult model.
SAMPLE_INTENT: dict[str, Any] = {
    "enhanced_understanding": "Create a folder at /tmp/test",
    "confidence": 0.95,
    "enhanced": True,
    "original": "create a folder at /tmp/test",
    "suggestions": ["Consider adding sub-directories"],
    "clarifications_needed": [],
}


@pytest.fixture
def sample_task_plan_json() -> str:
    return json.dumps(SAMPLE_TASK_PLAN)


@pytest.fixture
def sample_intent_json() -> str:
    return json.dumps(SAMPLE_INTENT)


# ─── HTTP / AI client mocks ───────────────────────────────────────────────────


@pytest.fixture
def mock_httpx_client():
    """Fixture providing a mock httpx.AsyncClient."""
    with patch("httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        yield mock_instance


@pytest.fixture
def mock_openrouter_response() -> dict[str, Any]:
    """Return a mock OpenRouter API success response payload."""
    return {
        "id": "chatcmpl-test-123",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(SAMPLE_TASK_PLAN),
                },
                "finish_reason": "stop",
            }
        ],
        "model": "test/free-model-large",
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 100,
            "total_tokens": 150,
        },
    }
