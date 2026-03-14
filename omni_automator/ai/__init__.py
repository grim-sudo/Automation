"""AI integration layer for OmniAutomator."""

from .context_manager import ContextManager, Message
from .model_manager import ModelManager, ModelProvider, ModelRoute
from .openrouter_integration import (
    AIProviderError,
    AITaskPlan,
    # Legacy
    OpenRouterAutomationAI,
    OpenRouterClient,
    OpenRouterConfig,
    StreamChunk,
)
from .response_parser import ResponseParser, TaskPlan
from .task_planner import TaskPlanner

__all__ = [
    # New async client (spec-required)
    "OpenRouterClient",
    "OpenRouterConfig",
    "StreamChunk",
    "AIProviderError",
    # Model manager (spec-required)
    "ModelManager",
    "ModelProvider",
    "ModelRoute",
    # Context manager (spec-required)
    "ContextManager",
    "Message",
    # Task planner (spec-required)
    "TaskPlanner",
    "TaskPlan",
    "ResponseParser",
    # Legacy compatibility — used by parsers/ai_parser.py and task_executor.py
    "OpenRouterAutomationAI",
    "AITaskPlan",
]
