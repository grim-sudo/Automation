"""
AI integration modules for OmniAutomator
"""

from .openrouter_integration import OpenRouterAutomationAI
from .model_manager import get_ai_manager, AIModelManager, AIModelConfig
from .task_planner import get_ai_task_planner, AIPoweredTaskPlanner
from .task_executor import get_ai_task_executor, AITaskExecutor

__all__ = [
    "OpenRouterAutomationAI",
    "get_ai_manager",
    "AIModelManager",
    "AIModelConfig",
    "get_ai_task_planner",
    "AIPoweredTaskPlanner",
    "get_ai_task_executor",
    "AITaskExecutor",
]
