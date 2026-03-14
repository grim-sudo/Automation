"""AI integration layer for OmniAutomator."""

from .openrouter_integration import (
    OpenRouterClient,
    OpenRouterConfig,
    StreamChunk,
    AIProviderError,
    # Legacy
    OpenRouterAutomationAI,
    AITaskPlan,
)
from .model_manager import ModelManager, ModelProvider, ModelRoute
from .context_manager import ContextManager, Message
from .task_planner import TaskPlanner
from .response_parser import TaskPlan, ResponseParser

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
