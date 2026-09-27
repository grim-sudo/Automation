"""AI integration layer for Archon."""

from .automation_ai import AITaskPlan, OllamaAutomationAI
from .context_manager import ContextManager, Message
from .ollama_integration import AIProviderError, OllamaProvider
from .response_parser import ResponseParser, TaskPlan

__all__ = [
    # Local Ollama backend
    "OllamaProvider",
    "AIProviderError",
    # AI facade
    "OllamaAutomationAI",
    "AITaskPlan",
    # Context manager
    "ContextManager",
    "Message",
    # Response parsing
    "ResponseParser",
    "TaskPlan",
]
