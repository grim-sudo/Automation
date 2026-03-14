"""pytest configuration and shared fixtures for OmniAutomator tests.

Fixtures here are available to every test module automatically.  They are
kept intentionally small — each test file declares its own local fixtures
where more specificity is needed.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

# ─── Event loop policy ────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


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
        "model": "openai/gpt-4o",
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 100,
            "total_tokens": 150,
        },
    }
