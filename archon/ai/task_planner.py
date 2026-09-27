"""
Legacy synchronous AI task planner.

Converts a natural-language request into a task plan via the local-Ollama AI
facade (:class:`~archon.ai.automation_ai.OllamaAutomationAI`) and executes it
through the AI task executor. Kept so existing entry points and tests that call
``get_ai_task_planner()`` continue to work.
"""

from __future__ import annotations

import os
from datetime import datetime

from ..utils.logger import get_logger
from .automation_ai import AITaskPlan, OllamaAutomationAI


class AIPoweredTaskPlanner:
    """Synchronous task planner backed by the local Ollama AI facade."""

    def __init__(self) -> None:
        self.logger = get_logger("AIPoweredTaskPlanner")
        self.ai: OllamaAutomationAI | None = None
        self.task_history: list[dict] = []
        self._initialize_ai()

    def _initialize_ai(self) -> None:
        try:
            self.ai = OllamaAutomationAI()
            if self.ai.is_available:
                self.logger.info("Ollama AI initialised")
            else:
                self.logger.warning("Ollama AI not available")
        except Exception as exc:
            self.logger.warning("Failed to initialise Ollama AI: %s", exc)

    def plan_and_execute(self, request: str, context: dict | None = None) -> dict:
        """Generate a task plan and execute it (legacy sync API)."""
        from .task_executor import get_ai_task_executor

        self.logger.info("Processing request: %s", request)
        task_plan = self._generate_task_plan(request, context)
        if not task_plan:
            return {"success": False, "error": "Failed to generate task plan", "request": request}

        executor = get_ai_task_executor()
        unknown_actions: list[str] = []
        try:
            known = set(executor.execution_handlers.keys())
            for step in task_plan.get("execution_steps", []):
                action = (step.get("action") or "").lower()
                if action and action not in known:
                    unknown_actions.append(action)
        except Exception:
            unknown_actions = []

        if unknown_actions:
            self.logger.warning("Unknown actions in plan: %s — using NL fallback.", unknown_actions)
            try:
                result = executor.parse_and_execute_nl(request, confirm=False)
                result["note"] = (
                    "NL fallback executed in dry-run mode. "
                    "Re-run in interactive mode to confirm execution."
                )
            except Exception as exc:
                result = {"success": False, "error": f"NL fallback failed: {exc}"}
        else:
            result = executor.execute_task_plan(task_plan)

        self.task_history.append(
            {
                "request": request,
                "task_plan": task_plan,
                "execution_result": result,
                "timestamp": datetime.now().isoformat(),
            }
        )
        return result

    def _generate_task_plan(self, request: str, context: dict | None = None) -> dict | None:
        if self.ai and self.ai.is_available:
            try:
                ai_plan: AITaskPlan = self.ai.analyze_automation_request(request, context or {})
                if ai_plan and hasattr(ai_plan, "__dict__"):
                    return {
                        "original_request": ai_plan.original_request,
                        "interpreted_intent": ai_plan.interpreted_intent,
                        "confidence_score": ai_plan.confidence_score,
                        "execution_steps": ai_plan.execution_steps,
                        "risk_assessment": ai_plan.risk_assessment,
                        "optimization_suggestions": ai_plan.optimization_suggestions,
                    }
            except Exception as exc:
                self.logger.error("Ollama plan generation failed: %s", exc)
        self.logger.warning("Using fallback task plan generation")
        return self._fallback_plan(request)

    @staticmethod
    def _fallback_plan(request: str) -> dict:
        request_lower = request.lower()
        if any(w in request_lower for w in ["ml", "machine learning", "pipeline", "deep learning"]):
            action, description = "create_ml_pipeline", "Create ML pipeline folder structure"
        elif any(w in request_lower for w in ["web app", "website", "frontend", "react", "vue"]):
            action, description = "create_web_app", "Create web app folder structure"
        else:
            action, description = "setup_project", "Create project folder structure"
        return {
            "original_request": request,
            "interpreted_intent": f"Process request: {request}",
            "confidence_score": 0.50,
            "execution_steps": [
                {
                    "action": action,
                    "parameters": {
                        "project_name": "automation_task",
                        "location": os.path.expanduser("~"),
                    },
                    "description": description,
                    "required": True,
                }
            ],
            "risk_assessment": {"risk_level": "low", "concerns": [], "mitigations": []},
            "optimization_suggestions": [],
        }

    def get_task_history(self, limit: int = 10) -> list[dict]:
        return self.task_history[-limit:]

    def switch_ai_model(self, model_name: str) -> bool:
        if not self.ai:
            return False
        try:
            self.ai.set_model(model_name)
            return True
        except Exception:
            return False


# Process-level singleton for the legacy shim.
_planner_instance: AIPoweredTaskPlanner | None = None


def get_ai_task_planner() -> AIPoweredTaskPlanner:
    """Return the process-wide AIPoweredTaskPlanner singleton."""
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = AIPoweredTaskPlanner()
    return _planner_instance
