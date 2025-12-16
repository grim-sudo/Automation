#!/usr/bin/env python3
"""
Enhanced Workflow Engine with AI Integration and Flexible NLP
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json
import os
from datetime import datetime

from .enhanced_command_parser import EnhancedCommandParser
from .ai_model_manager import get_ai_manager, AIResponse
from .flexible_nlp import get_nlp_processor
from .ai_task_planner import get_ai_task_planner


class CommandExecutionStatus(Enum):
    """Status of command execution"""
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_FOR_AI = "waiting_for_ai"


@dataclass
class WorkflowStep:
    """Single step in a workflow"""
    id: str
    command: str
    action: str
    category: str
    params: Dict[str, Any]
    status: CommandExecutionStatus = CommandExecutionStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    ai_enhanced: bool = False
    ai_model_used: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class WorkflowExecution:
    """Execution record for a workflow"""
    workflow_id: str
    started_at: str
    completed_at: Optional[str] = None
    status: str = "running"
    steps_executed: int = 0
    steps_failed: int = 0
    total_steps: int = 0
    ai_queries: int = 0
    total_execution_time: float = 0.0


class EnhancedWorkflowEngine:
    """Workflow engine with AI integration and flexible parsing"""
    
    def __init__(self, base_engine=None):
        self.base_engine = base_engine
        self.command_parser = EnhancedCommandParser()
        self.ai_manager = get_ai_manager()
        self.nlp_processor = get_nlp_processor()
        self.task_planner = get_ai_task_planner()
        
        # Callback handlers for different actions
        self.action_handlers: Dict[str, Callable] = {}
        self.current_workflow = None
        self.execution_history: List[WorkflowExecution] = []
        
        self._load_handlers()
    
    def execute_command(self, command: str, use_ai_enhancement: bool = True) -> Dict[str, Any]:
        """Execute a single command with flexible parsing and optional AI"""
        # Parse command with flexible NLP
        parsed = self.command_parser.parse_flexible(command)
        
        # Check if AI enhancement is needed
        ai_response = None
        if use_ai_enhancement and parsed.confidence < 0.7:
            ai_response = self._get_ai_enhancement(command, parsed)
        
        # Create workflow step
        step = WorkflowStep(
            id=self._generate_step_id(),
            command=command,
            action=parsed.action,
            category=parsed.category,
            params=parsed.params,
            ai_enhanced=ai_response is not None,
            ai_model_used=ai_response.model_used if ai_response else None
        )
        
        # Execute the action
        step.status = CommandExecutionStatus.EXECUTING
        
        try:
            result = self._execute_action(step)
            step.result = result
            step.status = CommandExecutionStatus.SUCCESS
        except Exception as e:
            step.error = str(e)
            step.status = CommandExecutionStatus.FAILED
        
        return {
            'step': step,
            'parsed': parsed,
            'ai_response': ai_response,
            'success': step.status == CommandExecutionStatus.SUCCESS
        }
    
    def execute_workflow(self, commands: List[str], workflow_name: str = None) -> WorkflowExecution:
        """Execute a sequence of commands"""
        workflow_id = workflow_name or self._generate_workflow_id()
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            started_at=datetime.now().isoformat(),
            total_steps=len(commands)
        )
        
        steps = []
        
        for i, command in enumerate(commands):
            result = self.execute_command(command)
            steps.append(result)
            
            execution.steps_executed += 1
            if result['step'].status == CommandExecutionStatus.FAILED:
                execution.steps_failed += 1
                # Optionally stop on first failure
                # break
            
            if result['ai_response']:
                execution.ai_queries += 1
        
        execution.completed_at = datetime.now().isoformat()
        execution.status = "completed"
        
        self.execution_history.append(execution)
        self._save_execution_history()
        
        return execution
    
    def get_command_alternatives(self, command: str) -> Dict[str, List[str]]:
        """Get alternative ways to express the same command"""
        variations = self.command_parser.get_command_variations(command)
        
        return {
            'original': command,
            'alternatives': variations,
            'count': len(variations)
        }
    
    def switch_ai_model(self, model_name: str) -> bool:
        """Switch the AI model used for enhancement"""
        return self.ai_manager.switch_model(model_name)
    
    def get_available_ai_models(self) -> Dict[str, List[str]]:
        """Get available AI models"""
        return self.ai_manager.get_available_models()
    
    def get_current_ai_model(self) -> Optional[Dict[str, Any]]:
        """Get current AI model info"""
        return self.ai_manager.get_current_model_info()
    
    def register_action_handler(self, action: str, handler: Callable) -> None:
        """Register a handler for a specific action"""
        self.action_handlers[action.lower()] = handler
    
    def _get_ai_enhancement(self, command: str, parsed) -> Optional[AIResponse]:
        """Get AI enhancement for low-confidence commands - generates executable task plan"""
        try:
            # Skip AI for very long complex commands that break AI JSON parsing
            if self._is_too_complex_for_ai(command):
                return None  # Return None to fall back to simple parsing
            
            context = {
                'task': 'generate_execution_plan',
                'command': command,
                'parsed_action': parsed.action,
                'parsed_category': parsed.category,
                'confidence': parsed.confidence,
                'capabilities': list(self.action_handlers.keys()),
                'constraints': ['ensure safety', 'verify parameters']
            }
            
            # Use AI task planner to generate executable task plan
            task_plan = self.task_planner._generate_task_plan(command, context)
            
            # Create AI response with task plan
            response = AIResponse(
                content=f"Generated task plan for: {command}",
                model_used=self.task_planner.openrouter_ai.model_name if self.task_planner.openrouter_ai else "local",
                tokens_used=0,
                provider="openrouter" if self.task_planner.openrouter_ai and self.task_planner.openrouter_ai.is_available else "local",
                timestamp=str(__import__('datetime').datetime.now()),
                task_plan=task_plan
            )
            
            return response
        except Exception as e:
            print(f"AI enhancement failed: {e}")
            return None
    
    def _is_too_complex_for_ai(self, command: str) -> bool:
        """Check if command is too complex for AI parsing"""
        import re
        
        if len(command) > 200:
            nested_patterns = [
                r'in\s+(?:that|those|each|every)',
                r'and\s+in\s+',
                r'inside\s+(?:each|every)',
                r'\d+\s+folders?.*\d+\s+folders?',
                r'table \d+ to table \d+',
            ]
            
            for pattern in nested_patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    return True
            
            actions = command.lower().count(' and ')
            if actions >= 3:
                return True
        
        return False
    
    def _execute_action(self, step: WorkflowStep) -> Dict[str, Any]:
        """Execute an action based on the step"""
        action_key = step.action.lower().replace(' ', '_')
        
        # Check if handler is registered
        if action_key in self.action_handlers:
            handler = self.action_handlers[action_key]
            return handler(**step.params)
        
        # Try to use base engine if available
        if self.base_engine:
            return self.base_engine.execute(step.action, step.params)
        
        # Default: return success with action name
        return {
            'action': step.action,
            'status': 'executed',
            'params': step.params
        }
    
    def _load_handlers(self) -> None:
        """Load action handlers"""
        # Register default handlers
        self.register_action_handler('create_folder', self._handle_create_folder)
        self.register_action_handler('deploy_container', self._handle_deploy_container)
        self.register_action_handler('setup_database', self._handle_setup_database)
        self.register_action_handler('create_pipeline', self._handle_create_pipeline)
        self.register_action_handler('monitor_service', self._handle_monitor_service)
        self.register_action_handler('backup_data', self._handle_backup_data)
        self.register_action_handler('migrate_data', self._handle_migrate_data)
    
    # Default handlers
    def _handle_create_folder(self, name: str, location: str = None, **kwargs) -> Dict[str, Any]:
        """Handle folder creation"""
        try:
            path = location if location else '.'
            full_path = os.path.join(path, name)
            os.makedirs(full_path, exist_ok=True)
            return {'success': True, 'path': full_path}
        except Exception as e:
            raise Exception(f"Failed to create folder: {e}")
    
    def _handle_deploy_container(self, app_name: str, target: str = 'docker', **kwargs) -> Dict[str, Any]:
        """Handle container deployment"""
        return {
            'success': True,
            'app_name': app_name,
            'target': target,
            'message': f"Container '{app_name}' deployment initiated on {target}"
        }
    
    def _handle_setup_database(self, db_name: str, db_type: str = 'postgresql', **kwargs) -> Dict[str, Any]:
        """Handle database setup"""
        return {
            'success': True,
            'database': db_name,
            'type': db_type,
            'message': f"Database '{db_name}' ({db_type}) setup initiated"
        }
    
    def _handle_create_pipeline(self, pipeline_name: str, features: List[str] = None, **kwargs) -> Dict[str, Any]:
        """Handle pipeline creation"""
        return {
            'success': True,
            'pipeline': pipeline_name,
            'features': features or [],
            'message': f"Pipeline '{pipeline_name}' created with {len(features or [])} features"
        }
    
    def _handle_monitor_service(self, service_name: str, **kwargs) -> Dict[str, Any]:
        """Handle service monitoring"""
        return {
            'success': True,
            'service': service_name,
            'message': f"Monitoring setup for '{service_name}'"
        }
    
    def _handle_backup_data(self, source: str, destination: str, **kwargs) -> Dict[str, Any]:
        """Handle data backup"""
        return {
            'success': True,
            'source': source,
            'destination': destination,
            'message': f"Backup from '{source}' to '{destination}' initiated"
        }
    
    def _handle_migrate_data(self, source_name: str, target_name: str, **kwargs) -> Dict[str, Any]:
        """Handle data migration"""
        return {
            'success': True,
            'source': source_name,
            'target': target_name,
            'message': f"Migration from '{source_name}' to '{target_name}' initiated"
        }
    
    def _generate_step_id(self) -> str:
        """Generate unique step ID"""
        import uuid
        return f"step_{uuid.uuid4().hex[:8]}"
    
    def _generate_workflow_id(self) -> str:
        """Generate unique workflow ID"""
        import uuid
        return f"workflow_{uuid.uuid4().hex[:8]}"
    
    def _save_execution_history(self) -> None:
        """Save execution history"""
        try:
            history_dir = os.path.expanduser("~/.omnimator/execution_history")
            os.makedirs(history_dir, exist_ok=True)
            
            history_file = os.path.join(
                history_dir,
                f"history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            with open(history_file, 'w') as f:
                json.dump([
                    {
                        'workflow_id': exec.workflow_id,
                        'started_at': exec.started_at,
                        'completed_at': exec.completed_at,
                        'status': exec.status,
                        'steps_executed': exec.steps_executed,
                        'steps_failed': exec.steps_failed,
                        'total_steps': exec.total_steps,
                        'ai_queries': exec.ai_queries
                    }
                    for exec in self.execution_history
                ], f, indent=2)
        except Exception as e:
            print(f"Failed to save execution history: {e}")


# Export enhanced workflow engine
__all__ = ['EnhancedWorkflowEngine', 'WorkflowStep', 'WorkflowExecution', 'CommandExecutionStatus']
