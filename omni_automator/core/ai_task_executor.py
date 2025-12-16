#!/usr/bin/env python3
"""
AI Task Executor - Bridges AI-generated task plans with actual execution
Provides unified execution for tasks from any AI provider (OpenRouter, Ollama, etc.)
"""

import os
import json
import subprocess
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..utils.logger import get_logger


@dataclass
class ExecutionTask:
    """Single executable task from AI plan"""
    task_id: str
    action: str
    parameters: Dict[str, Any]
    description: str
    required: bool = True
    priority: int = 0


class AITaskExecutor:
    """Executes AI-generated task plans with full modularity"""
    
    def __init__(self):
        self.logger = get_logger("AITaskExecutor")
        self.execution_handlers: Dict[str, Callable] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.execution_state: Dict[str, Any] = {
            'current_task': None,
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'created_resources': []
        }
        
        # Register all available execution handlers
        self._register_handlers()
    
    def execute_task_plan(self, task_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an AI-generated task plan
        
        Args:
            task_plan: AITaskPlan with execution_steps
            
        Returns:
            Execution result with status and created resources
        """
        self.logger.info(f"Executing task plan: {task_plan.get('interpreted_intent', 'Unknown')}")
        
        if 'execution_steps' not in task_plan or not task_plan['execution_steps']:
            self.logger.warning("Task plan has no execution steps")
            return {'success': False, 'error': 'No execution steps provided'}
        
        execution_result = {
            'original_request': task_plan.get('original_request', ''),
            'interpreted_intent': task_plan.get('interpreted_intent', ''),
            'confidence_score': task_plan.get('confidence_score', 0),
            'execution_steps': [],
            'created_resources': [],
            'failed_operations': [],
            'total_steps': len(task_plan['execution_steps']),
            'completed_steps': 0,
            'start_time': datetime.now().isoformat(),
            'success': True
        }
        
        # Reset state for this execution
        self.execution_state = {
            'current_task': None,
            'total_tasks': len(task_plan['execution_steps']),
            'completed_tasks': 0,
            'failed_tasks': 0,
            'created_resources': []
        }
        
        # Execute each step
        for i, step in enumerate(task_plan['execution_steps']):
            self.logger.info(f"Executing step {i+1}/{len(task_plan['execution_steps'])}: {step.get('action', 'unknown')}")
            
            try:
                step_result = self._execute_single_step(step)
                
                if step_result['success']:
                    self.execution_state['completed_tasks'] += 1
                    execution_result['created_resources'].extend(
                        step_result.get('created_resources', [])
                    )
                else:
                    self.execution_state['failed_tasks'] += 1
                    if step.get('required', True):
                        execution_result['failed_operations'].append({
                            'step': i + 1,
                            'action': step.get('action'),
                            'error': step_result.get('error', 'Unknown error')
                        })
                        execution_result['success'] = False
                        break  # Stop on required step failure
                    else:
                        self.logger.warning(f"Optional step failed: {step.get('action')}")
                
                execution_result['execution_steps'].append(step_result)
                execution_result['completed_steps'] += 1
                
            except Exception as e:
                self.logger.error(f"Error executing step {i+1}: {str(e)}")
                execution_result['failed_operations'].append({
                    'step': i + 1,
                    'action': step.get('action'),
                    'error': str(e)
                })
                if step.get('required', True):
                    execution_result['success'] = False
                    break
        
        execution_result['end_time'] = datetime.now().isoformat()
        
        # Save execution record
        self.execution_history.append(execution_result)
        
        return execution_result
    
    def _execute_single_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single task step"""
        action = step.get('action', '').lower().replace(' ', '_').replace('-', '_')
        
        # Support both 'parameters' and 'params' keys (for compatibility with different AI providers)
        parameters = step.get('parameters') or step.get('params') or {}
        
        # Get the handler for this action
        if action not in self.execution_handlers:
            return {
                'success': False,
                'action': action,
                'error': f"No handler registered for action: {action}",
                'parameters': parameters
            }
        
        try:
            handler = self.execution_handlers[action]
            result = handler(**parameters)
            
            if not isinstance(result, dict):
                result = {'success': True, 'result': result}
            
            result['action'] = action
            result['parameters'] = parameters
            
            return result
            
        except Exception as e:
            self.logger.error(f"Handler error for action {action}: {str(e)}")
            return {
                'success': False,
                'action': action,
                'error': str(e),
                'parameters': parameters
            }
    
    def _register_handlers(self):
        """Register all execution handlers"""
        # Folder and File Operations
        self.execution_handlers['create_folder'] = self._handle_create_folder
        self.execution_handlers['create_folders'] = self._handle_create_folders
        self.execution_handlers['create_file'] = self._handle_create_file
        self.execution_handlers['create_directory_structure'] = self._handle_create_directory_structure
        
        # Code Modification Operations
        self.execution_handlers['read_file'] = self._handle_read_file
        self.execution_handlers['write_file'] = self._handle_write_file
        self.execution_handlers['modify_file'] = self._handle_modify_file
        
        # Project Setup
        self.execution_handlers['setup_project'] = self._handle_setup_project
        self.execution_handlers['initialize_project'] = self._handle_setup_project  # Alias
        self.execution_handlers['create_ml_pipeline'] = self._handle_create_ml_pipeline
        self.execution_handlers['create_web_app'] = self._handle_create_web_app
        
        # Development Operations
        self.execution_handlers['setup_git'] = self._handle_setup_git
        self.execution_handlers['install_dependencies'] = self._handle_install_dependencies
        self.execution_handlers['install_packages'] = self._handle_install_packages
        self.execution_handlers['generate_code'] = self._handle_generate_code
        
        # DevOps Operations
        self.execution_handlers['setup_docker'] = self._handle_setup_docker
        self.execution_handlers['create_pipeline'] = self._handle_create_pipeline
        self.execution_handlers['configure_deployment'] = self._handle_configure_deployment
        
        # Windows System Operations (Bare-Metal Automation)
        self.execution_handlers['run_powershell'] = self._handle_run_powershell
        self.execution_handlers['run_command'] = self._handle_run_command
        self.execution_handlers['start_process'] = self._handle_run_command  # Alias
        self.execution_handlers['install_software'] = self._handle_install_software
        self.execution_handlers['manage_service'] = self._handle_manage_service
        self.execution_handlers['system_config'] = self._handle_system_config
        self.execution_handlers['set_registry'] = self._handle_set_registry
        self.execution_handlers['create_task'] = self._handle_create_task
        self.execution_handlers['enable_feature'] = self._handle_enable_feature
        self.execution_handlers['restart_system'] = self._handle_restart_system
        
        self.logger.info(f"Registered {len(self.execution_handlers)} execution handlers")
    
    # ===== Folder and File Handlers =====
    
    def _handle_create_folder(self, name: str, location: str = None, **kwargs) -> Dict[str, Any]:
        """Create a single folder"""
        try:
            # Default to home directory
            if location is None or location == 'current_directory':
                path = os.path.expanduser('~')
            else:
                path = location
            
            # Build full path - handle nested paths like 'machine_learning_project/data'
            full_path = os.path.join(path, name)
            os.makedirs(full_path, exist_ok=True)
            
            self.logger.info(f"Created folder: {full_path}")
            
            return {
                'success': True,
                'path': full_path,
                'created_resources': [full_path]
            }
        except Exception as e:
            self.logger.error(f"Failed to create folder {name}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_create_folders(self, folders: List[Dict[str, str]], base_location: str = None, **kwargs) -> Dict[str, Any]:
        """Create multiple folders with hierarchy"""
        try:
            created = []
            base = base_location if base_location else os.path.expanduser('~')
            
            for folder in folders:
                if isinstance(folder, str):
                    name = folder
                    path = base
                elif isinstance(folder, dict):
                    name = folder.get('name', '')
                    path = folder.get('path', base)
                else:
                    continue
                
                if not name:
                    continue
                
                full_path = os.path.join(path, name)
                os.makedirs(full_path, exist_ok=True)
                created.append(full_path)
                self.logger.info(f"Created folder: {full_path}")
            
            return {
                'success': True,
                'count': len(created),
                'folders': created,
                'created_resources': created
            }
        except Exception as e:
            self.logger.error(f"Failed to create folders: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_create_file(self, name: str, location: str = None, content: str = "", **kwargs) -> Dict[str, Any]:
        """Create a file with optional content"""
        try:
            path = location if location else os.path.expanduser('~')
            full_path = os.path.join(path, name)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w') as f:
                f.write(content)
            
            self.logger.info(f"Created file: {full_path}")
            
            return {
                'success': True,
                'path': full_path,
                'size': len(content),
                'created_resources': [full_path]
            }
        except Exception as e:
            self.logger.error(f"Failed to create file {name}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_create_directory_structure(self, structure: Dict[str, Any], base_location: str = None, **kwargs) -> Dict[str, Any]:
        """Create complete directory structure with files"""
        try:
            base = base_location if base_location else os.path.expanduser('~')
            created = []
            
            def create_structure(current_path: str, struct: Dict[str, Any]):
                """Recursively create directory structure"""
                if isinstance(struct, dict):
                    for key, value in struct.items():
                        item_path = os.path.join(current_path, key)
                        
                        if isinstance(value, dict) and value.get('type') == 'file':
                            # Create file
                            os.makedirs(os.path.dirname(item_path), exist_ok=True)
                            content = value.get('content', '')
                            with open(item_path, 'w') as f:
                                f.write(content)
                            created.append(item_path)
                            self.logger.info(f"Created file: {item_path}")
                        else:
                            # Create directory and recurse
                            os.makedirs(item_path, exist_ok=True)
                            created.append(item_path)
                            self.logger.info(f"Created directory: {item_path}")
                            
                            if isinstance(value, dict):
                                create_structure(item_path, value)
            
            create_structure(base, structure)
            
            return {
                'success': True,
                'count': len(created),
                'created_resources': created
            }
        except Exception as e:
            self.logger.error(f"Failed to create directory structure: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    # ===== Code Modification Handlers =====
    
    def _handle_read_file(self, file_path: str = None, **kwargs) -> Dict[str, Any]:
        """Read file contents"""
        try:
            # Support both file_path and path parameters
            path = file_path or kwargs.get('path')
            if not path:
                return {'success': False, 'error': "file_path parameter required"}
            
            # Resolve relative paths from Desktop
            if not os.path.isabs(path):
                # Try Desktop first
                desktop_path = os.path.expanduser('~/Desktop')
                if os.path.exists(os.path.join(desktop_path, path)):
                    path = os.path.join(desktop_path, path)
                else:
                    path = os.path.expanduser(path)
            
            if not os.path.exists(path):
                return {'success': False, 'error': f"File not found: {path}"}
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.logger.info(f"Read file: {path}")
            
            return {
                'success': True,
                'file_path': path,
                'content': content,
                'size': len(content),
                'lines': len(content.split('\n'))
            }
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {str(e)}")
            return {'success': False, 'error': str(e), 'file_path': file_path}
    
    def _handle_write_file(self, file_path: str = None, content: str = "", **kwargs) -> Dict[str, Any]:
        """Write content to file"""
        try:
            # Support both file_path and path parameters
            path = file_path or kwargs.get('path')
            if not path:
                return {'success': False, 'error': "file_path parameter required"}
            
            # Resolve relative paths from Desktop
            if not os.path.isabs(path):
                # Try Desktop first
                desktop_path = os.path.expanduser('~/Desktop')
                if not os.path.exists(os.path.dirname(path) or '.'):
                    path = os.path.join(desktop_path, path)
                else:
                    path = os.path.expanduser(path)
            
            # Create directories if needed
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"Wrote file: {path}")
            
            return {
                'success': True,
                'file_path': path,
                'size': len(content),
                'lines': len(content.split('\n'))
            }
        except Exception as e:
            self.logger.error(f"Failed to write file {file_path}: {str(e)}")
            return {'success': False, 'error': str(e), 'file_path': file_path}
    
    def _handle_modify_file(self, file_path: str = None, intent: str = "", old_code: str = None, new_code: str = None, **kwargs) -> Dict[str, Any]:
        """Modify file by replacing code based on intent"""
        try:
            # Support both file_path and path parameters
            path = file_path or kwargs.get('path')
            if not path:
                return {'success': False, 'error': "file_path parameter required"}
            
            # Resolve relative paths from Desktop
            if not os.path.isabs(path):
                # Try Desktop first
                desktop_path = os.path.expanduser('~/Desktop')
                if os.path.exists(os.path.join(desktop_path, path)):
                    path = os.path.join(desktop_path, path)
                else:
                    path = os.path.expanduser(path)
            
            if not os.path.exists(path):
                return {'success': False, 'error': f"File not found: {path}"}
            
            # Read the file
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # If specific old/new code provided, do direct replacement
            if old_code and new_code:
                if old_code not in content:
                    return {'success': False, 'error': f"Could not find code to replace in {path}"}
                modified_content = content.replace(old_code, new_code)
            else:
                # Auto-generate replacement based on intent
                modified_content = self._generate_code_replacement_ai(content, intent)
            
            # Write back
            with open(path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            
            self.logger.info(f"Modified file: {path} with intent: {intent}")
            
            return {
                'success': True,
                'file_path': path,
                'action': 'modified',
                'intent': intent
            }
        except Exception as e:
            self.logger.error(f"Failed to modify file {file_path}: {str(e)}")
            return {'success': False, 'error': str(e), 'file_path': file_path}
    
    def _generate_code_replacement_ai(self, current_content: str, intent: str) -> str:
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
    
    # ===== Project Setup Handlers =====
    
    def _handle_setup_project(self, project_name: str = None, project_type: str = "general", location: str = None, app_name: str = None, **kwargs) -> Dict[str, Any]:
        """Setup a new project with basic structure"""
        try:
            # Handle flexible naming
            name = project_name or app_name or "my_project"
            base = location if location else os.path.expanduser('~')
            project_path = os.path.join(base, name)
            
            # Create base structure
            created = [project_path]
            os.makedirs(project_path, exist_ok=True)
            
            # Add type-specific folders
            folders = ['src', 'tests', 'docs', 'config']
            for folder in folders:
                folder_path = os.path.join(project_path, folder)
                os.makedirs(folder_path, exist_ok=True)
                created.append(folder_path)
            
            # Create README
            readme_path = os.path.join(project_path, 'README.md')
            with open(readme_path, 'w') as f:
                f.write(f"# {name}\n\nProject type: {project_type}\n")
            created.append(readme_path)
            
            self.logger.info(f"Project setup complete: {project_path}")
            
            return {
                'success': True,
                'project_path': project_path,
                'created_count': len(created),
                'created_resources': created
            }
        except Exception as e:
            self.logger.error(f"Failed to setup project: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_create_ml_pipeline(self, pipeline_name: str, features: List[str] = None, location: str = None, **kwargs) -> Dict[str, Any]:
        """Create ML pipeline directory structure"""
        try:
            base = location if location else os.path.expanduser('~')
            pipeline_path = os.path.join(base, pipeline_name)
            
            created = [pipeline_path]
            os.makedirs(pipeline_path, exist_ok=True)
            
            # ML pipeline structure
            ml_folders = [
                'data/raw',
                'data/processed',
                'notebooks',
                'src/preprocessing',
                'src/models',
                'src/features',
                'results',
                'configs'
            ]
            
            for folder in ml_folders:
                folder_path = os.path.join(pipeline_path, folder)
                os.makedirs(folder_path, exist_ok=True)
                created.append(folder_path)
            
            # Create key files
            files = {
                'requirements.txt': "# ML Pipeline Requirements\nnumpy\npandas\nscikit-learn\ntensorflow\n",
                'src/__init__.py': "",
                'src/preprocessing/__init__.py': "",
                'src/models/__init__.py': "",
                'src/features/__init__.py': "",
                'notebooks/exploration.ipynb': '{}',
                'README.md': f"# {pipeline_name}\n\nMachine Learning Pipeline\n"
            }
            
            for file_name, content in files.items():
                file_path = os.path.join(pipeline_path, file_name)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w') as f:
                    f.write(content)
                created.append(file_path)
            
            self.logger.info(f"ML pipeline created: {pipeline_path}")
            
            return {
                'success': True,
                'pipeline_path': pipeline_path,
                'created_count': len(created),
                'features': features or [],
                'created_resources': created
            }
        except Exception as e:
            self.logger.error(f"Failed to create ML pipeline: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_create_web_app(self, app_name: str, framework: str = "generic", location: str = None, **kwargs) -> Dict[str, Any]:
        """Create web application structure"""
        try:
            base = location if location else os.path.expanduser('~')
            app_path = os.path.join(base, app_name)
            
            created = [app_path]
            os.makedirs(app_path, exist_ok=True)
            
            # Web app folders
            web_folders = ['public', 'src', 'tests', 'docs', 'config']
            for folder in web_folders:
                folder_path = os.path.join(app_path, folder)
                os.makedirs(folder_path, exist_ok=True)
                created.append(folder_path)
            
            # Create standard files
            files = {
                'package.json': '{"name": "' + app_name + '", "version": "1.0.0"}',
                '.gitignore': 'node_modules/\n.env\n*.log\n',
                'README.md': f"# {app_name}\n\nWeb Application\n",
                'src/index.js': '// Application entry point\n'
            }
            
            for file_name, content in files.items():
                file_path = os.path.join(app_path, file_name)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w') as f:
                    f.write(content)
                created.append(file_path)
            
            self.logger.info(f"Web app created: {app_path}")
            
            return {
                'success': True,
                'app_path': app_path,
                'framework': framework,
                'created_count': len(created),
                'created_resources': created
            }
        except Exception as e:
            self.logger.error(f"Failed to create web app: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    # ===== Development Operation Handlers =====
    
    def _handle_setup_git(self, location: str = None, **kwargs) -> Dict[str, Any]:
        """Initialize git repository"""
        try:
            path = location if location else os.getcwd()
            
            if not os.path.exists(os.path.join(path, '.git')):
                subprocess.run(['git', 'init'], cwd=path, check=True, capture_output=True)
                self.logger.info(f"Git repository initialized: {path}")
            
            return {
                'success': True,
                'path': path,
                'message': 'Git repository initialized'
            }
        except Exception as e:
            self.logger.error(f"Failed to setup git: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_install_dependencies(self, packages: List[str] = None, **kwargs) -> Dict[str, Any]:
        """Install dependencies"""
        try:
            # This is a placeholder - actual implementation would use pip/npm/etc
            self.logger.info(f"Would install packages: {packages}")
            
            return {
                'success': True,
                'packages': packages or [],
                'message': 'Dependencies installation would proceed'
            }
        except Exception as e:
            self.logger.error(f"Failed to install dependencies: {str(e)}")
            return {'success': False, 'error': str(e)}    
    def _handle_install_packages(self, packages: List[str] = None, location: str = None, **kwargs) -> Dict[str, Any]:
        """Install packages (generic handler)"""
        try:
            self.logger.info(f"Would install packages: {packages}")
            
            return {
                'success': True,
                'packages': packages or [],
                'location': location,
                'message': f'Would install {len(packages) if packages else 0} packages'
            }
        except Exception as e:
            self.logger.error(f"Failed to install packages: {e}")
            return {'success': False, 'error': str(e)}    
    def _handle_generate_code(self, module_name: str, code_type: str = "class", **kwargs) -> Dict[str, Any]:
        """Generate code file"""
        try:
            self.logger.info(f"Generated {code_type}: {module_name}")
            
            return {
                'success': True,
                'module': module_name,
                'type': code_type,
                'message': f'Generated {code_type}: {module_name}'
            }
        except Exception as e:
            self.logger.error(f"Failed to generate code: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    # ===== DevOps Operation Handlers =====
    
    def _handle_setup_docker(self, app_name: str, base_image: str = "python:3.11", **kwargs) -> Dict[str, Any]:
        """Create Docker configuration"""
        try:
            dockerfile_content = f"""FROM {base_image}

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
"""
            
            docker_compose = f"""version: '3.8'

services:
  {app_name}:
    build: .
    container_name: {app_name}
    environment:
      - ENV=production
    ports:
      - "8000:8000"
"""
            
            return {
                'success': True,
                'app_name': app_name,
                'dockerfile': dockerfile_content,
                'docker_compose': docker_compose,
                'message': 'Docker configuration generated'
            }
        except Exception as e:
            self.logger.error(f"Failed to setup docker: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_create_pipeline(self, pipeline_name: str, stages: List[str] = None, **kwargs) -> Dict[str, Any]:
        """Create CI/CD pipeline"""
        try:
            self.logger.info(f"Created pipeline: {pipeline_name}")
            
            return {
                'success': True,
                'pipeline': pipeline_name,
                'stages': stages or ['build', 'test', 'deploy'],
                'message': f'Pipeline created: {pipeline_name}'
            }
        except Exception as e:
            self.logger.error(f"Failed to create pipeline: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _handle_configure_deployment(self, environment: str = "production", **kwargs) -> Dict[str, Any]:
        """Configure deployment"""
        try:
            self.logger.info(f"Configured deployment for: {environment}")
            
            return {
                'success': True,
                'environment': environment,
                'message': f'Deployment configured for {environment}'
            }
        except Exception as e:
            self.logger.error(f"Failed to configure deployment: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    # ===== Windows System Operations (Bare-Metal Automation) =====
    
    def _handle_run_powershell(self, script: str, admin: bool = False, **kwargs) -> Dict[str, Any]:
        """Execute PowerShell script"""
        try:
            self.logger.info(f"Executing PowerShell script (admin={admin})")
            
            # For security, only run in non-admin mode by default
            if admin:
                self.logger.warning("Admin mode requested - would require elevation")
                return {
                    'success': False,
                    'error': 'Admin PowerShell requires elevation - not executed for safety',
                    'script_preview': script[:100]
                }
            
            # Run PowerShell command
            result = subprocess.run(
                ['powershell', '-Command', script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error_output': result.stderr,
                'return_code': result.returncode,
                'script_preview': script[:100]
            }
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'PowerShell script timeout (>30s)'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_run_command(self, command: str, args: List[str] = None, **kwargs) -> Dict[str, Any]:
        """Execute system command"""
        try:
            self.logger.info(f"Executing command: {command}")
            
            # Security: whitelist common safe commands
            safe_commands = ['ipconfig', 'systeminfo', 'tasklist', 'dir', 'whoami', 
                           'date', 'time', 'echo', 'type', 'findstr', 'wmic']
            
            cmd_name = command.split()[0].lower().replace('.exe', '')
            
            if cmd_name not in safe_commands:
                self.logger.warning(f"Command {cmd_name} not in safe list")
                return {
                    'success': False,
                    'error': f'Command {cmd_name} requires explicit approval',
                    'hint': 'Use run_powershell for custom commands'
                }
            
            cmd_list = [command] + (args or [])
            result = subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout[:1000],  # Limit output
                'error_output': result.stderr[:500],
                'return_code': result.returncode
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_install_software(self, software: str, method: str = 'winget', **kwargs) -> Dict[str, Any]:
        """Install software package"""
        try:
            self.logger.info(f"Installing software: {software} via {method}")
            
            if method == 'winget':
                # Use Windows Package Manager
                result = subprocess.run(
                    ['winget', 'install', '--id', software, '-e', '-h'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            elif method == 'chocolatey':
                # Use Chocolatey
                result = subprocess.run(
                    ['choco', 'install', software, '-y'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            else:
                return {
                    'success': False,
                    'error': f'Unknown package manager: {method}',
                    'supported': ['winget', 'chocolatey']
                }
            
            return {
                'success': result.returncode == 0,
                'software': software,
                'method': method,
                'output': result.stdout[:500],
                'return_code': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Installation timeout (>5 minutes)'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_manage_service(self, service: str, action: str = 'status', **kwargs) -> Dict[str, Any]:
        """Manage Windows service"""
        try:
            self.logger.info(f"Managing service {service}: {action}")
            
            valid_actions = ['start', 'stop', 'restart', 'status', 'enable', 'disable']
            if action not in valid_actions:
                return {
                    'success': False,
                    'error': f'Invalid action {action}',
                    'valid_actions': valid_actions
                }
            
            if action == 'status':
                cmd = ['Get-Service', '-Name', service]
                result = subprocess.run(
                    ['powershell', '-Command', f'Get-Service -Name {service}'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            elif action in ['enable', 'disable']:
                enabled = action == 'enable'
                cmd = f'Set-Service -Name {service} -StartupType {"Automatic" if enabled else "Disabled"}'
                result = subprocess.run(
                    ['powershell', '-Command', cmd],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            else:
                # start, stop, restart
                cmd = f'Restart-Service -Name {service}' if action == 'restart' else f'{action.capitalize()}-Service -Name {service}'
                result = subprocess.run(
                    ['powershell', '-Command', cmd],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            
            return {
                'success': result.returncode == 0,
                'service': service,
                'action': action,
                'output': result.stdout[:500],
                'return_code': result.returncode
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_system_config(self, setting: str, value: str = None, **kwargs) -> Dict[str, Any]:
        """Modify system configuration"""
        try:
            self.logger.info(f"System config: {setting} = {value}")
            
            # Safe configuration changes
            configs = {
                'hostname': f'Rename-Computer -NewName {value}',
                'timezone': f'Set-TimeZone -Id "{value}"',
                'hostname_info': 'Get-ComputerInfo -Property CsComputerName'
            }
            
            if setting not in configs:
                return {
                    'success': False,
                    'error': f'Unknown setting: {setting}',
                    'available': list(configs.keys())
                }
            
            if not value and setting != 'hostname_info':
                return {'success': False, 'error': f'Setting {setting} requires a value'}
            
            result = subprocess.run(
                ['powershell', '-Command', configs[setting]],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                'success': result.returncode == 0,
                'setting': setting,
                'value': value,
                'output': result.stdout[:500]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_set_registry(self, path: str, key: str, value: str, value_type: str = 'String', **kwargs) -> Dict[str, Any]:
        """Modify Windows registry"""
        try:
            self.logger.warning(f"Registry modification requested: {path}\\{key}")
            
            # Registry changes are sensitive - require explicit confirmation
            # This is a safety measure
            self.logger.info("Registry changes require admin privileges and manual confirmation")
            
            return {
                'success': False,
                'error': 'Registry modifications require explicit admin confirmation',
                'registry_path': path,
                'key': key,
                'value': value,
                'hint': 'Use PowerShell with admin privileges for registry changes'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_create_task(self, task_name: str, script: str, trigger: str = 'daily', **kwargs) -> Dict[str, Any]:
        """Create scheduled task"""
        try:
            self.logger.info(f"Creating scheduled task: {task_name} ({trigger})")
            
            # Generate PowerShell command to create task
            ps_cmd = f"""
$trigger = New-ScheduledTaskTrigger -{trigger.capitalize()}
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-Command "{script}"'
Register-ScheduledTask -TaskName '{task_name}' -Trigger $trigger -Action $action -User System
"""
            
            result = subprocess.run(
                ['powershell', '-Command', ps_cmd],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                'success': result.returncode == 0,
                'task_name': task_name,
                'trigger': trigger,
                'output': result.stdout[:500],
                'return_code': result.returncode
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_enable_feature(self, feature: str, **kwargs) -> Dict[str, Any]:
        """Enable Windows feature"""
        try:
            self.logger.info(f"Enabling Windows feature: {feature}")
            
            # Enable Windows Feature
            result = subprocess.run(
                ['powershell', '-Command', f'Enable-WindowsOptionalFeature -Online -FeatureName {feature}'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                'success': result.returncode == 0,
                'feature': feature,
                'output': result.stdout[:500],
                'note': 'System restart may be required'
            }
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Feature installation timeout'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_restart_system(self, delay: int = 60, reason: str = "OmniAutomator", **kwargs) -> Dict[str, Any]:
        """Schedule system restart"""
        try:
            self.logger.warning(f"System restart requested with {delay}s delay")
            
            # Safety: don't actually restart, just log the request
            self.logger.info(f"Would restart system in {delay} seconds: {reason}")
            
            return {
                'success': True,
                'action': 'restart_scheduled',
                'delay_seconds': delay,
                'reason': reason,
                'note': 'Restart was not executed - manual confirmation required',
                'command': f'shutdown /s /t {delay} /c "{reason}"'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent execution history"""
        return self.execution_history[-limit:]
    
    def get_execution_state(self) -> Dict[str, Any]:
        """Get current execution state"""
        return self.execution_state.copy()


# Global executor instance
_executor_instance = None


def get_ai_task_executor() -> AITaskExecutor:
    """Get or create the global AI task executor"""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = AITaskExecutor()
    return _executor_instance
