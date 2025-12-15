#!/usr/bin/env python3
"""
AI-Powered Task Planner
Bridges AI analysis with task execution using multiple AI providers
Generates executable task plans from natural language requests
"""

import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..utils.logger import get_logger
from .ai_task_executor import get_ai_task_executor
from ..ai.openrouter_integration import OpenRouterAutomationAI, AITaskPlan


class AIPoweredTaskPlanner:
    """Generates and executes AI-powered task plans from natural language"""
    
    def __init__(self):
        self.logger = get_logger("AIPoweredTaskPlanner")
        self.executor = get_ai_task_executor()
        self.openrouter_ai = None
        self.task_history: List[Dict[str, Any]] = []
        
        # Try to initialize OpenRouter AI
        self._initialize_openrouter()
    
    def _initialize_openrouter(self):
        """Initialize OpenRouter AI if available"""
        try:
            api_key = os.getenv('OPENROUTER_API_KEY')
            if api_key:
                self.openrouter_ai = OpenRouterAutomationAI(api_key=api_key)
                if self.openrouter_ai.is_available:
                    self.logger.info("OpenRouter AI initialized successfully")
                else:
                    self.logger.warning("OpenRouter AI not available")
        except Exception as e:
            self.logger.warning(f"Failed to initialize OpenRouter: {e}")
    
    def plan_and_execute(self, request: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Plan and execute tasks from a natural language request
        
        Args:
            request: Natural language request (e.g., "create ML pipeline")
            context: Optional context information
            
        Returns:
            Execution result with created resources
        """
        self.logger.info(f"Processing request: {request}")
        
        # Step 1: Generate task plan using AI
        task_plan = self._generate_task_plan(request, context)
        
        if not task_plan:
            return {
                'success': False,
                'error': 'Failed to generate task plan',
                'request': request
            }
        
        # Step 2: Execute the task plan
        execution_result = self.executor.execute_task_plan(task_plan)
        
        # Add to history
        self.task_history.append({
            'request': request,
            'task_plan': task_plan,
            'execution_result': execution_result,
            'timestamp': datetime.now().isoformat()
        })
        
        return execution_result
    
    def _generate_task_plan(self, request: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Generate an AI task plan from natural language request"""
        
        # Try OpenRouter first if available
        if self.openrouter_ai and self.openrouter_ai.is_available:
            try:
                self.logger.info(f"Generating task plan with OpenRouter ({self.openrouter_ai.model_name})")
                task_plan = self.openrouter_ai.analyze_automation_request(request, context or {})
                
                if task_plan and hasattr(task_plan, '__dict__'):
                    # Convert dataclass to dict
                    plan_dict = {
                        'original_request': task_plan.original_request,
                        'interpreted_intent': task_plan.interpreted_intent,
                        'confidence_score': task_plan.confidence_score,
                        'execution_steps': task_plan.execution_steps,
                        'risk_assessment': task_plan.risk_assessment,
                        'optimization_suggestions': task_plan.optimization_suggestions
                    }
                    
                    self.logger.info(f"Task plan generated - Intent: {task_plan.interpreted_intent}, Steps: {len(task_plan.execution_steps)}")
                    return plan_dict
                
            except Exception as e:
                self.logger.error(f"OpenRouter task plan generation failed: {e}")
        
        # Fallback: Generate basic task plan from request
        self.logger.warning("Using fallback task plan generation")
        return self._generate_fallback_task_plan(request)
    
    def _generate_fallback_task_plan(self, request: str) -> Dict[str, Any]:
        """Generate a basic task plan using pattern matching"""
        
        request_lower = request.lower()
        
        # Machine Learning pipeline
        if any(word in request_lower for word in ['ml', 'machine learning', 'pipeline', 'deep learning']):
            return {
                'original_request': request,
                'interpreted_intent': 'Create machine learning pipeline structure',
                'confidence_score': 0.75,
                'execution_steps': [
                    {
                        'action': 'create_ml_pipeline',
                        'parameters': {
                            'pipeline_name': 'ml_project',
                            'features': ['preprocessing', 'feature_engineering', 'model_training'],
                            'location': os.path.expanduser('~')
                        },
                        'description': 'Create ML pipeline folder structure',
                        'required': True
                    }
                ],
                'risk_assessment': {'risk_level': 'low', 'concerns': [], 'mitigations': []},
                'optimization_suggestions': ['Add version control', 'Use virtual environment']
            }
        
        # Web application
        elif any(word in request_lower for word in ['web app', 'website', 'frontend', 'react', 'vue']):
            return {
                'original_request': request,
                'interpreted_intent': 'Create web application structure',
                'confidence_score': 0.75,
                'execution_steps': [
                    {
                        'action': 'create_web_app',
                        'parameters': {
                            'app_name': 'web_app',
                            'framework': 'generic',
                            'location': os.path.expanduser('~')
                        },
                        'description': 'Create web app folder structure',
                        'required': True
                    }
                ],
                'risk_assessment': {'risk_level': 'low', 'concerns': [], 'mitigations': []},
                'optimization_suggestions': ['Use npm for dependency management', 'Add build scripts']
            }
        
        # Project setup
        elif any(word in request_lower for word in ['project', 'setup', 'create folder']):
            return {
                'original_request': request,
                'interpreted_intent': 'Create project structure',
                'confidence_score': 0.70,
                'execution_steps': [
                    {
                        'action': 'setup_project',
                        'parameters': {
                            'project_name': 'my_project',
                            'project_type': 'general',
                            'location': os.path.expanduser('~')
                        },
                        'description': 'Create project folder structure',
                        'required': True
                    }
                ],
                'risk_assessment': {'risk_level': 'low', 'concerns': [], 'mitigations': []},
                'optimization_suggestions': []
            }
        
        # Default: just create a folder
        else:
            return {
                'original_request': request,
                'interpreted_intent': f'Process request: {request}',
                'confidence_score': 0.50,
                'execution_steps': [
                    {
                        'action': 'setup_project',
                        'parameters': {
                            'project_name': 'automation_task',
                            'project_type': 'general',
                            'location': os.path.expanduser('~')
                        },
                        'description': 'Create task project structure',
                        'required': True
                    }
                ],
                'risk_assessment': {'risk_level': 'low', 'concerns': [], 'mitigations': []},
                'optimization_suggestions': []
            }
    
    def get_task_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent task history"""
        return self.task_history[-limit:]
    
    def get_executor_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get executor history"""
        return self.executor.get_execution_history(limit)
    
    def switch_ai_model(self, model_name: str) -> bool:
        """Switch the AI model"""
        if not self.openrouter_ai:
            self.logger.error("OpenRouter AI not initialized")
            return False
        
        try:
            self.openrouter_ai.switch_model(model_name)
            self.logger.info(f"Switched to AI model: {model_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to switch model: {e}")
            return False


# Global planner instance
_planner_instance = None


def get_ai_task_planner() -> AIPoweredTaskPlanner:
    """Get or create the global AI task planner"""
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = AIPoweredTaskPlanner()
    return _planner_instance
