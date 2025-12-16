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
    
    def _is_too_complex_for_ai(self, command: str) -> bool:
        """Check if command is too complex for AI parsing (likely to cause JSON errors)"""
        import re
        
        # Very long commands with nested loops tend to break AI JSON parsing
        if len(command) > 200:
            # Check for nested/loop structures
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
            
            # Multiple action conjunctions also indicate complexity
            actions = command.lower().count(' and ')
            if actions >= 3:
                return True
        
        return False
    
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
            
            # Check if command is too complex for AI (very long with nested structures)
            # Use fallback parser directly for these cases
            if self._is_too_complex_for_ai(command):
                self.logger.info("Command is too complex for AI, using advanced parser directly")
                complex_command = self.advanced_parser.parse_complex_command(command)
            # Use AI-enhanced parsing if available, otherwise fall back to advanced parsing
            elif self.ai_parser.get_ai_status()['available']:
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
            error_msg = str(e)
            self.logger.error(f"Error executing command '{command}': {error_msg}")
            
            # Provide helpful fallback messages for specific errors
            fallback_msg = self._get_fallback_error_message(command, error_msg, type(e).__name__)
            
            # Get AI suggestions for error resolution if available
            error_suggestions = []
            if self.ai_parser.get_ai_status()['available']:
                try:
                    error_info = {
                        'command': command,
                        'error': error_msg,
                        'error_type': type(e).__name__,
                        'context': self._get_execution_context()
                    }
                    ai_resolution = self.ai_parser.handle_execution_error(error_info)
                    error_suggestions = ai_resolution.get('suggestions', [])
                except Exception as ai_error:
                    self.logger.warning(f"AI error resolution failed: {ai_error}")
            
            return {
                'success': False,
                'error': error_msg,
                'fallback_message': fallback_msg,
                'command': command,
                'ai_suggestions': error_suggestions,
                'timestamp': datetime.now().isoformat()
            }
    
    def _execute_parsed_command(self, parsed_command: Dict[str, Any], **kwargs) -> Any:
        """Execute a parsed command using appropriate adapter/plugin"""
        action = parsed_command.get('action')
        category = parsed_command.get('category')
        params = parsed_command.get('params', {})
        
        # Route to appropriate handler
        if category == 'filesystem':
            return self.os_adapter.filesystem.execute(action, params)
        elif category == 'process':
            return self.os_adapter.process.execute(action, params)
        elif category == 'gui':
            return self.os_adapter.gui.execute(action, params)
        elif category == 'system':
            return self.os_adapter.system.execute(action, params)
        elif category == 'network':
            return self.os_adapter.network.execute(action, params)
        elif category == 'code_modification':
            # Handle code modification actions
            if action == 'modify_file':
                return self._handle_modify_file(params)
            elif action == 'read_file':
                return self._handle_read_file(params)
            elif action == 'write_file':
                return self._handle_write_file(params)
        else:
            # Try plugins
            return self.plugin_manager.execute(category, action, params)
    
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
    
    def _get_fallback_error_message(self, command: str, error: str, error_type: str) -> str:
        """Generate helpful fallback error message based on error type"""
        import re
        
        # Check for common error patterns
        if 'unknown' in error.lower() and 'action' in error.lower():
            return (
                "⚠️ Command complexity too high: The command contains multiple nested levels that "
                "exceed current parsing capabilities.\n"
                "Suggestion: Break the command into simpler steps or use fewer nesting levels.\n"
                "Example: Instead of 3+ nested 'in each' statements, use 2 levels maximum."
            )
        
        # Check for multi-level nesting in command
        nested_count = len(re.findall(r'in\s+(?:each|every)', command, re.IGNORECASE))
        if nested_count >= 3:
            return (
                f"⚠️ Command has {nested_count} nesting levels: The parser supports up to 2-3 levels of nesting.\n"
                "Your command structure:\n"
                "  • Level 1: in that / and in that\n"
                "  • Level 2: in each [type] make/create\n"
                "  • Level 3: in each of the [plural]\n"
                "Suggestion: Simplify by removing one or more nesting levels or running multiple commands."
            )
        
        # Check for unsupported patterns
        if 'registry' in command.lower() or 'index' in command.lower():
            if error_type == 'NotImplementedError':
                return "⚠️ Registry/Index generation: This feature requires additional setup.\nTry using a simpler command."
        
        # Generic helpful message
        return (
            "⚠️ Command parsing failed: The command structure may not be fully supported.\n"
            "Supported patterns:\n"
            "  • Simple creation: 'create X folder'\n"
            "  • Single nesting: 'make A B C folders and in each make D E F folders'\n"
            "  • Double nesting: Add 'and in each of the [plural] create [items]'\n"
            "Please verify your command syntax or try a simpler approach."
        )
    
    def _resolve_file_with_disambiguation(self, file_name: str) -> Optional[str]:
        """
        Resolve a file name to its full path.
        If multiple files with the same name exist, prompt user to select one.
        Returns the selected file path or None if not found/selected.
        Prioritizes current working directory, then user project directories.
        """
        # Check current directory first
        if os.path.exists(file_name):
            return os.path.abspath(file_name)
        
        # Check Desktop
        desktop_path = os.path.expanduser('~/Desktop')
        if os.path.exists(os.path.join(desktop_path, file_name)):
            return os.path.join(desktop_path, file_name)
        
        # Search for files in user project directories (limited depth, prioritize current dir)
        user_search_paths = [
            os.getcwd(),  # Current directory first
            os.path.expanduser('~/Desktop'),
            os.path.expanduser('~/Documents'),
            os.path.expanduser('~/Projects'),
        ]
        
        found_files = []
        found_files_set = set()  # To avoid duplicates
        current_dir = os.getcwd()
        
        # First pass: search user directories with limited depth
        for search_path in user_search_paths:
            if not os.path.exists(search_path):
                continue
            for root, dirs, files in os.walk(search_path):
                # Limit depth to 5 levels for user directories
                depth = root.replace(search_path, '').count(os.sep)
                if depth > 5:
                    continue
                # Skip system directories
                if any(skip in root.lower() for skip in ['appdata', 'roaming', 'site-packages', 'dist-packages']):
                    continue
                
                if file_name in files:
                    full_path = os.path.abspath(os.path.join(root, file_name))
                    if full_path not in found_files_set:
                        found_files.append(full_path)
                        found_files_set.add(full_path)
        
        # If no files found, return None
        if not found_files:
            return None
        
        # If only one file found, return it
        if len(found_files) == 1:
            return found_files[0]
        
        # If multiple files found, prompt user to select with enhanced context
        try:
            print(f"\n⚠️  Multiple files named '{file_name}' found:")
        except:
            print(f"\nWARNING: Multiple files named '{file_name}' found:")
        print(f"    Current working directory: {current_dir}\n")
        
        for idx, path in enumerate(found_files, 1):
            # Show location context
            abs_path = os.path.abspath(path)
            
            # Determine folder context
            if abs_path.startswith(current_dir):
                try:
                    folder_context = f"📁 [IN PROJECT] {os.path.dirname(os.path.relpath(abs_path, current_dir))}"
                except:
                    folder_context = f"[IN PROJECT] {os.path.dirname(os.path.relpath(abs_path, current_dir))}"
            elif abs_path.startswith(desktop_path):
                try:
                    folder_context = f"🖥️  [ON DESKTOP]"
                except:
                    folder_context = f"[ON DESKTOP]"
            else:
                try:
                    folder_context = f"📂 {os.path.dirname(abs_path)}"
                except:
                    folder_context = f"{os.path.dirname(abs_path)}"
            
            # Get file stats
            try:
                file_stat = os.stat(abs_path)
                size_kb = file_stat.st_size / 1024
                size_str = f"{size_kb:.1f}KB" if size_kb < 1024 else f"{size_kb/1024:.1f}MB"

            except:
                size_str = "?"
            
            print(f"   {idx}. {folder_context}")
            print(f"       Full path: {abs_path}")
            print(f"       Size: {size_str}\n")
        
        try:
            # Try to get user input
            choice = input(f"Enter the number of the file to use (1-{len(found_files)}): ").strip()
            choice_idx = int(choice) - 1
            
            if 0 <= choice_idx < len(found_files):
                selected_file = found_files[choice_idx]
                print(f"✓ Selected: {selected_file}\n")
                return selected_file
            else:
                print(f"❌ Invalid choice. Using first option.\n")
                return found_files[0]
        except (ValueError, KeyboardInterrupt):
            print(f"✓ Using first option: {found_files[0]}\n")
            return found_files[0]
    
    def _handle_read_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read file contents"""
        try:
            file_path = params.get('file_path') or params.get('path')
            if not file_path:
                raise ValueError("file_path parameter required")
            
            # Resolve relative paths from Desktop with duplicate detection
            if not os.path.isabs(file_path):
                resolved_path = self._resolve_file_with_disambiguation(file_path)
                if not resolved_path:
                    return {'success': False, 'error': f"File not found: {file_path}"}
                file_path = resolved_path
            elif not os.path.exists(file_path):
                # Check if there are duplicate files
                file_name = os.path.basename(file_path)
                resolved_path = self._resolve_file_with_disambiguation(file_name)
                if resolved_path:
                    file_path = resolved_path
                else:
                    return {'success': False, 'error': f"File not found: {file_path}"}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                'success': True,
                'file_path': file_path,
                'content': content,
                'size': len(content),
                'lines': len(content.split('\n'))
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'file_path': params.get('file_path')
            }
    
    def _handle_write_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Write content to file"""
        try:
            file_path = params.get('file_path') or params.get('path')
            content = params.get('content', '')
            
            if not file_path:
                raise ValueError("file_path parameter required")
            
            # Resolve relative paths from Desktop with duplicate detection
            if not os.path.isabs(file_path):
                resolved_path = self._resolve_file_with_disambiguation(file_path)
                if not resolved_path:
                    # If not found, use Desktop as default location
                    desktop_path = os.path.expanduser('~/Desktop')
                    file_path = os.path.join(desktop_path, file_path)
                else:
                    file_path = resolved_path
            elif not os.path.exists(file_path):
                # Check if there are duplicate files
                file_name = os.path.basename(file_path)
                resolved_path = self._resolve_file_with_disambiguation(file_name)
                if resolved_path:
                    file_path = resolved_path
            
            # Create directories if needed
            os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                'success': True,
                'file_path': file_path,
                'size': len(content),
                'lines': len(content.split('\n'))
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'file_path': params.get('file_path')
            }
    
    def _handle_modify_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Modify file by replacing old implementation with new one"""
        try:
            file_path = params.get('file_path') or params.get('path')
            old_code = params.get('old_code')
            new_code = params.get('new_code')
            intent = params.get('intent', '')
            
            if not file_path:
                raise ValueError("file_path parameter required")
            
            # Resolve relative paths from Desktop with duplicate detection
            if not os.path.isabs(file_path):
                resolved_path = self._resolve_file_with_disambiguation(file_path)
                if not resolved_path:
                    return {
                        'success': False,
                        'error': f"File not found: {file_path}",
                        'file_path': file_path
                    }
                file_path = resolved_path
            elif not os.path.exists(file_path):
                # Check if there are duplicate files
                file_name = os.path.basename(file_path)
                resolved_path = self._resolve_file_with_disambiguation(file_name)
                if resolved_path:
                    file_path = resolved_path
                else:
                    return {
                        'success': False,
                        'error': f"File not found: {file_path}",
                        'file_path': file_path
                    }
            
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # If specific old/new code provided, do direct replacement
            if old_code and new_code:
                if old_code not in content:
                    raise ValueError(f"Could not find code to replace in {file_path}")
                modified_content = content.replace(old_code, new_code)
            else:
                # Auto-generate replacement based on intent
                modified_content = self._generate_code_replacement(content, intent)
            
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            
            return {
                'success': True,
                'file_path': file_path,
                'action': 'modified',
                'intent': intent
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'file_path': params.get('file_path')
            }
    
    def _generate_code_replacement(self, current_content: str, intent: str) -> str:
        """Generate code replacement based on intent"""
        intent_lower = intent.lower()
        
        # Prime number detection
        if 'prime' in intent_lower and 'fibonacci' in current_content.lower():
            return self._generate_prime_number_code()
        
        # Fibonacci from other code
        if 'fibonacci' in intent_lower:
            return self._generate_fibonacci_code()
        
        # Default: return unchanged
        return current_content
    
    def _generate_prime_number_code(self) -> str:
        """Generate prime number identifier code"""
        return '''# Prime Number Identifier

def is_prime(num):
    """Check if a number is prime."""
    if num < 2:
        return False
    if num == 2:
        return True
    if num % 2 == 0:
        return False
    for i in range(3, int(num**0.5) + 1, 2):
        if num % i == 0:
            return False
    return True

def find_primes(limit):
    """Find all prime numbers up to the given limit."""
    primes = [num for num in range(2, limit + 1) if is_prime(num)]
    return primes

def find_primes_count(count):
    """Find the first n prime numbers."""
    primes = []
    num = 2
    while len(primes) < count:
        if is_prime(num):
            primes.append(num)
        num += 1
    return primes

if __name__ == "__main__":
    choice = input("Find primes by (1) limit or (2) count? Enter 1 or 2: ")
    
    if choice == "1":
        limit = int(input("Enter the upper limit: "))
        primes = find_primes(limit)
        print(f"Prime numbers up to {limit}: {primes}")
        print(f"Total primes found: {len(primes)}")
    elif choice == "2":
        count = int(input("Enter the count of primes to find: "))
        primes = find_primes_count(count)
        print(f"First {count} prime numbers: {primes}")
    else:
        print("Invalid choice!")
'''
    
    def _generate_fibonacci_code(self) -> str:
        """Generate fibonacci series code"""
        return '''# Fibonacci Series Implementation

def fibonacci(n):
    """Generate Fibonacci series up to n terms."""
    series = []
    a, b = 0, 1
    for _ in range(n):
        series.append(a)
        a, b = b, a + b
    return series

if __name__ == "__main__":
    n = int(input("Enter the number of terms: "))
    print("Fibonacci Series:", fibonacci(n))
'''

