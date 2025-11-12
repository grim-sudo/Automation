"""
Core automation engine that orchestrates all automation operations
"""

import os
import sys
import logging
import platform
from typing import Dict, Any, List, Optional
from datetime import datetime

from .command_parser import CommandParser
from .plugin_manager import PluginManager
from .advanced_parser import AdvancedCommandParser, CommandComplexity
from .workflow_engine import WorkflowEngine
from .ai_enhanced_parser import AIEnhancedParser
from ..os_adapters.adapter_factory import OSAdapterFactory
from ..security.permission_manager import PermissionManager
from ..utils.logger import setup_logger


class OmniAutomator:
    """Main automation engine that coordinates all operations"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the automation engine"""
        try:
            self.config = config or {}
            self.logger = setup_logger("OmniAutomator")
            
            # Validate configuration
            self._validate_config()
            
            # Initialize core components with error handling
            self.os_adapter = OSAdapterFactory.create_adapter()
            self.command_parser = CommandParser()
            self.advanced_parser = AdvancedCommandParser()
            
            # Initialize AI parser with fallback
            api_key = None
            if config:
                api_key = config.get('openrouter_api_key') or os.getenv('OPENROUTER_API_KEY')
            else:
                api_key = os.getenv('OPENROUTER_API_KEY')
                
            self.ai_parser = AIEnhancedParser(api_key)
            self.plugin_manager = PluginManager()
            self.permission_manager = PermissionManager()
            self.workflow_engine = WorkflowEngine(self)
            
            # Execution state
            self.is_running = False
            self.execution_history = []
            self.sandbox_mode = self.config.get('sandbox_mode', False)
            
            # Apply sandbox mode if configured
            if self.sandbox_mode:
                self.enable_sandbox_mode()
            
            self.logger.info(f"OmniAutomator initialized on {platform.system()} {platform.release()}")
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Failed to initialize OmniAutomator: {e}")
            else:
                print(f"Critical error during initialization: {e}")
            raise
    
    def _validate_config(self):
        """Validate configuration parameters"""
        if not isinstance(self.config, dict):
            raise ValueError("Configuration must be a dictionary")
        
        # Validate sandbox mode
        if 'sandbox_mode' in self.config:
            if not isinstance(self.config['sandbox_mode'], bool):
                raise ValueError("sandbox_mode must be a boolean")
        
        # Validate continue_on_error
        if 'continue_on_error' in self.config:
            if not isinstance(self.config['continue_on_error'], bool):
                raise ValueError("continue_on_error must be a boolean")
    
    def _is_dangerous_command(self, command: str) -> bool:
        """Check if command contains potentially dangerous operations"""
        dangerous_keywords = [
            'format', 'fdisk', 'rm -rf', 'del /f /s /q', 'rmdir /s',
            'shutdown', 'reboot', 'halt', 'poweroff',
            'registry delete', 'reg delete', 'regedit',
            'net user', 'net localgroup administrators',
            'sc delete', 'taskkill /f',
            'chmod 777', 'chown root',
            'dd if=', 'mkfs', 'parted'
        ]
        
        command_lower = command.lower()
        return any(keyword in command_lower for keyword in dangerous_keywords)
    
    def execute(self, command: str, **kwargs) -> Dict[str, Any]:
        """Execute an automation command (simple or complex)"""
        try:
            # Input validation
            if not command or not isinstance(command, str):
                raise ValueError("Command must be a non-empty string")
            
            command = command.strip()
            if not command:
                raise ValueError("Command cannot be empty or whitespace only")
            
            # Security check for potentially dangerous commands
            if self._is_dangerous_command(command):
                if not self.sandbox_mode:
                    self.logger.warning(f"Potentially dangerous command detected: {command}")
            
            self.logger.info(f"Executing command: {command}")
            
            # Use AI-enhanced parsing if available, otherwise fall back to advanced parsing
            if self.ai_parser.get_ai_status()['available']:
                self.logger.info("Using AI-enhanced command parsing")
                complex_command = self.ai_parser.parse_with_ai(command, self._get_execution_context())
            else:
                self.logger.info("Using advanced command parsing (AI not available)")
                complex_command = self.advanced_parser.parse_complex_command(command)
            
            if complex_command.complexity == CommandComplexity.SIMPLE:
                # Use simple parsing for basic commands
                parsed_command = self.command_parser.parse(command)
                
                # Check permissions
                if not self.permission_manager.check_permission(parsed_command):
                    raise PermissionError(f"Permission denied for command: {command}")
                
                # Execute the command
                result = self._execute_parsed_command(parsed_command, **kwargs)
                
                # Log execution
                self._log_execution(command, parsed_command, result)
                
                return {
                    'success': True,
                    'result': result,
                    'command': command,
                    'complexity': 'simple',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                # Execute complex workflow
                self.logger.info(f"Executing complex workflow with {len(complex_command.steps)} steps")
                
                # Check permissions for all steps
                for step in complex_command.steps:
                    step_command = {
                        'action': step.action,
                        'category': step.category,
                        'params': step.params
                    }
                    if not self.permission_manager.check_permission(step_command):
                        raise PermissionError(f"Permission denied for step: {step.action}")
                
                # Execute workflow
                workflow_result = self.workflow_engine.execute_workflow(complex_command)
                
                # Log execution
                self._log_execution(command, complex_command, workflow_result)
                
                return {
                    'success': workflow_result['success'],
                    'result': workflow_result,
                    'command': command,
                    'complexity': complex_command.complexity.value,
                    'steps_completed': workflow_result.get('completed_steps', 0),
                    'total_steps': workflow_result.get('total_steps', 0),
                    'execution_time': workflow_result.get('total_execution_time', 0),
                    'timestamp': datetime.now().isoformat()
                }
            
        except Exception as e:
            self.logger.error(f"Error executing command '{command}': {str(e)}")
            
            # Get AI suggestions for error resolution if available
            error_suggestions = []
            if self.ai_parser.get_ai_status()['available']:
                try:
                    error_info = {
                        'command': command,
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'context': self._get_execution_context()
                    }
                    ai_resolution = self.ai_parser.handle_execution_error(error_info)
                    error_suggestions = ai_resolution.get('suggestions', [])
                except Exception as ai_error:
                    self.logger.warning(f"AI error resolution failed: {ai_error}")
            
            return {
                'success': False,
                'error': str(e),
                'command': command,
                'ai_suggestions': error_suggestions,
                'timestamp': datetime.now().isoformat()
            }
    
    def _execute_parsed_command(self, parsed_command: Dict[str, Any], **kwargs) -> Any:
        """Execute a parsed command using appropriate adapter/plugin"""
        action = parsed_command.get('action')
        category = parsed_command.get('category')
        
        # Route to appropriate handler
        if category == 'filesystem':
            return self.os_adapter.filesystem.execute(action, parsed_command.get('params', {}))
        elif category == 'process':
            return self.os_adapter.process.execute(action, parsed_command.get('params', {}))
        elif category == 'gui':
            return self.os_adapter.gui.execute(action, parsed_command.get('params', {}))
        elif category == 'system':
            return self.os_adapter.system.execute(action, parsed_command.get('params', {}))
        elif category == 'network':
            return self.os_adapter.network.execute(action, parsed_command.get('params', {}))
        else:
            # Try plugins
            return self.plugin_manager.execute(category, action, parsed_command.get('params', {}))
    
    def _log_execution(self, original_command: str, parsed_command: Dict[str, Any], result: Any):
        """Log command execution for audit trail"""
        execution_record = {
            'timestamp': datetime.now().isoformat(),
            'original_command': original_command,
            'parsed_command': parsed_command,
            'result_summary': str(result)[:200] if result else None,
            'user': os.getenv('USERNAME', 'unknown'),
            'platform': platform.system()
        }
        
        self.execution_history.append(execution_record)
        
        # Keep only last 1000 executions in memory
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]
    
    def batch_execute(self, commands: List[str]) -> List[Dict[str, Any]]:
        """Execute multiple commands in sequence"""
        results = []
        for command in commands:
            result = self.execute(command)
            results.append(result)
            
            # Stop on first failure unless configured otherwise
            if not result['success'] and not self.config.get('continue_on_error', False):
                break
        
        return results
    
    def get_capabilities(self) -> Dict[str, List[str]]:
        """Get list of all available capabilities"""
        capabilities = {
            'filesystem': self.os_adapter.filesystem.get_capabilities(),
            'process': self.os_adapter.process.get_capabilities(),
            'gui': self.os_adapter.gui.get_capabilities(),
            'system': self.os_adapter.system.get_capabilities(),
            'network': self.os_adapter.network.get_capabilities(),
            'plugins': self.plugin_manager.get_available_plugins()
        }
        
        return capabilities
    
    def get_execution_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent execution history"""
        return self.execution_history[-limit:]
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow execution status"""
        return self.workflow_engine.get_workflow_status()
    
    def analyze_command_complexity(self, command: str) -> Dict[str, Any]:
        """Analyze command complexity without executing"""
        complex_command = self.advanced_parser.parse_complex_command(command)
        
        return {
            'original_command': command,
            'complexity': complex_command.complexity.value,
            'estimated_steps': len(complex_command.steps),
            'estimated_duration': complex_command.estimated_duration,
            'context': complex_command.context,
            'steps_preview': [
                {
                    'action': step.action,
                    'category': step.category,
                    'priority': step.priority
                }
                for step in complex_command.steps
            ]
        }
    
    def _get_execution_context(self) -> Dict[str, Any]:
        """Get current execution context for AI analysis"""
        return {
            'platform': platform.system(),
            'sandbox_mode': self.sandbox_mode,
            'recent_commands': [record['original_command'] for record in self.execution_history[-5:]],
            'available_capabilities': list(self.get_capabilities().keys()),
            'current_directory': os.getcwd(),
            'user': os.getenv('USERNAME', 'unknown')
        }
    
    def get_ai_suggestions(self) -> List[str]:
        """Get AI-powered smart suggestions"""
        if self.ai_parser.get_ai_status()['available']:
            return self.ai_parser.get_smart_suggestions(self._get_execution_context())
        else:
            return [
                "Set OPENROUTER_API_KEY environment variable for AI-powered suggestions",
                "Try 'examples' for command ideas",
                "Use 'help' to see available commands"
            ]
    
    def analyze_command_with_ai(self, command: str) -> Dict[str, Any]:
        """Analyze command using AI without executing"""
        if self.ai_parser.get_ai_status()['available']:
            return self.ai_parser.analyze_command_intent(command)
        else:
            return {
                'intent': 'AI analysis not available',
                'confidence': 0.0,
                'suggestions': ['Enable AI by setting OPENROUTER_API_KEY environment variable'],
                'complexity': 'unknown'
            }
    
    def get_ai_status(self) -> Dict[str, Any]:
        """Get AI integration status"""
        return self.ai_parser.get_ai_status()
    
    def set_openrouter_api_key(self, api_key: str) -> bool:
        """Set OpenRouter API key for AI features"""
        success = self.ai_parser.set_api_key(api_key)
        if success:
            self.logger.info("OpenRouter AI enabled successfully")
        else:
            self.logger.error("Failed to enable OpenRouter AI")
        return success
    
    def enable_sandbox_mode(self):
        """Enable sandbox mode for safe testing"""
        self.sandbox_mode = True
        self.permission_manager.enable_sandbox_mode()
        self.logger.info("Sandbox mode enabled")
    
    def disable_sandbox_mode(self):
        """Disable sandbox mode"""
        self.sandbox_mode = False
        self.permission_manager.disable_sandbox_mode()
        self.logger.info("Sandbox mode disabled")
    
    def shutdown(self):
        """Clean shutdown of the automation engine"""
        self.logger.info("Shutting down OmniAutomator")
        self.is_running = False
        self.plugin_manager.shutdown()
        self.os_adapter.cleanup()
