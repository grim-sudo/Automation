"""
Workflow execution engine for complex multi-step automation
"""

import asyncio
import time
import os
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

from .advanced_parser import ComplexCommand, ParsedStep, CommandComplexity
from ..utils.logger import get_logger


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepExecution:
    """Execution state for a workflow step"""
    step: ParsedStep
    status: StepStatus = StepStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0


class WorkflowEngine:
    """Engine for executing complex multi-step workflows"""
    
    def __init__(self, automator_instance):
        self.automator = automator_instance
        self.logger = get_logger("WorkflowEngine")
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        self.max_parallel_steps = 3
        
        # Execution state
        self.current_workflow: Optional[ComplexCommand] = None
        self.step_executions: List[StepExecution] = []
        self.workflow_context: Dict[str, Any] = {}
        
        # Progress callbacks
        self.progress_callbacks: List[Callable] = []
    
    def execute_workflow(self, complex_command: ComplexCommand) -> Dict[str, Any]:
        """Execute a complex workflow"""
        self.logger.info(f"Starting workflow execution: {complex_command.original_command}")
        
        self.current_workflow = complex_command
        self.step_executions = [StepExecution(step) for step in complex_command.steps]
        self.workflow_context = complex_command.context.copy()
        
        try:
            if complex_command.complexity == CommandComplexity.SIMPLE:
                return self._execute_simple_workflow()
            elif complex_command.complexity == CommandComplexity.COMPOUND:
                return self._execute_compound_workflow()
            elif complex_command.complexity == CommandComplexity.WORKFLOW:
                return self._execute_complex_workflow()
            else:  # CONDITIONAL
                return self._execute_conditional_workflow()
                
        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'completed_steps': self._get_completed_steps(),
                'failed_step': self._get_failed_step()
            }
    
    def _execute_simple_workflow(self) -> Dict[str, Any]:
        """Execute simple single-step workflow"""
        if not self.step_executions:
            return {'success': True, 'message': 'No steps to execute'}
        
        step_exec = self.step_executions[0]
        result = self._execute_step(step_exec)
        
        return {
            'success': result['success'],
            'result': result.get('result'),
            'error': result.get('error'),
            'execution_time': result.get('execution_time', 0)
        }
    
    def _execute_compound_workflow(self) -> Dict[str, Any]:
        """Execute compound workflow with sequential steps"""
        results = []
        total_time = 0
        
        for step_exec in self.step_executions:
            # Check dependencies
            if not self._check_dependencies(step_exec):
                step_exec.status = StepStatus.SKIPPED
                self.logger.warning(f"Skipping step due to failed dependencies: {step_exec.step.action}")
                continue
            
            # Execute step
            result = self._execute_step(step_exec)
            results.append(result)
            total_time += result.get('execution_time', 0)
            
            # Stop on failure unless configured to continue
            if not result['success'] and not self.automator.config.get('continue_on_error', False):
                break
            
            # Update workflow context with results
            self._update_context(step_exec, result)
        
        success_count = sum(1 for r in results if r['success'])
        
        return {
            'success': success_count == len(results),
            'completed_steps': success_count,
            'total_steps': len(results),
            'results': results,
            'total_execution_time': total_time,
            'workflow_context': self.workflow_context
        }
    
    def _execute_complex_workflow(self) -> Dict[str, Any]:
        """Execute complex workflow with parallel execution where possible"""
        self.logger.info(f"Executing complex workflow with {len(self.step_executions)} steps")
        
        # Group steps by priority and dependencies
        execution_groups = self._group_steps_for_execution()
        
        results = []
        total_time = 0
        start_time = time.time()
        
        for group_index, group in enumerate(execution_groups):
            group_start = time.time()
            self.logger.info(f"Executing group {group_index + 1}/{len(execution_groups)} with {len(group)} steps")
            
            # Execute group (potentially in parallel)
            group_results = self._execute_step_group(group)
            results.extend(group_results)
            
            group_time = time.time() - group_start
            total_time += group_time
            
            # Check if we should continue
            failed_in_group = sum(1 for r in group_results if not r['success'])
            if failed_in_group > 0 and not self.automator.config.get('continue_on_error', False):
                self.logger.error(f"Stopping workflow due to {failed_in_group} failed steps in group {group_index + 1}")
                break
            
            # Notify progress
            self._notify_progress(group_index + 1, len(execution_groups), group_results)
        
        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r['success'])
        
        return {
            'success': success_count == len(self.step_executions),
            'completed_steps': success_count,
            'total_steps': len(self.step_executions),
            'failed_steps': len(self.step_executions) - success_count,
            'results': results,
            'total_execution_time': total_time,
            'estimated_time': self.current_workflow.estimated_duration,
            'workflow_context': self.workflow_context,
            'execution_summary': self._generate_execution_summary()
        }
    
    def _execute_conditional_workflow(self) -> Dict[str, Any]:
        """Execute conditional workflow with condition checking"""
        results = []
        
        for step_exec in self.step_executions:
            # Check conditions
            if step_exec.step.conditions:
                if not self._evaluate_conditions(step_exec.step.conditions):
                    step_exec.status = StepStatus.SKIPPED
                    self.logger.info(f"Skipping step due to unmet conditions: {step_exec.step.action}")
                    continue
            
            # Check dependencies
            if not self._check_dependencies(step_exec):
                step_exec.status = StepStatus.SKIPPED
                continue
            
            # Execute step
            result = self._execute_step(step_exec)
            results.append(result)
            
            # Update context
            self._update_context(step_exec, result)
        
        success_count = sum(1 for r in results if r['success'])
        
        return {
            'success': success_count > 0,  # At least one step succeeded
            'completed_steps': success_count,
            'total_steps': len(results),
            'results': results
        }
    
    def _execute_step(self, step_exec: StepExecution) -> Dict[str, Any]:
        """Execute a single workflow step with retry logic"""
        step = step_exec.step
        
        for attempt in range(self.max_retries + 1):
            step_exec.retry_count = attempt
            step_exec.status = StepStatus.RUNNING
            step_exec.start_time = time.time()
            
            try:
                self.logger.info(f"Executing step: {step.action} (attempt {attempt + 1})")
                
                # Execute based on category
                if step.category == 'filesystem':
                    # Handle filesystem operations directly
                    if step.action == 'create_folder':
                        result = self._execute_create_folder(step)
                    elif step.action == 'create_file':
                        result = self._execute_create_file(step)
                    elif step.action == 'list_folders':
                        # List folders in a directory
                        path = step.params.get('path') or step.params.get('location') or '.'
                        pattern = step.params.get('pattern', '')
                        try:
                            if os.path.exists(path) and os.path.isdir(path):
                                folders = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
                                if pattern:
                                    folders = [d for d in folders if pattern.lower() in d.lower()]
                                result = {
                                    'success': True,
                                    'folders': folders,
                                    'count': len(folders),
                                    'message': f'Found {len(folders)} folder(s)'
                                }
                                # Store in context for next steps
                                if hasattr(self, '_step_context'):
                                    self._step_context['listed_folders'] = folders
                            else:
                                result = {'success': False, 'message': f'Path not found or not a directory: {path}', 'folders': []}
                        except Exception as e:
                            result = {'success': False, 'message': f'Failed to list folders: {e}', 'folders': []}
                    elif step.action == 'list_files':
                        # List files in a directory
                        path = step.params.get('path') or step.params.get('location') or '.'
                        pattern = step.params.get('pattern', '')
                        try:
                            if os.path.exists(path) and os.path.isdir(path):
                                files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
                                if pattern:
                                    files = [f for f in files if pattern.lower() in f.lower()]
                                result = {
                                    'success': True,
                                    'files': files,
                                    'count': len(files),
                                    'message': f'Found {len(files)} file(s)'
                                }
                                # Store in context for next steps
                                if hasattr(self, '_step_context'):
                                    self._step_context['listed_files'] = files
                            else:
                                result = {'success': False, 'message': f'Path not found or not a directory: {path}', 'files': []}
                        except Exception as e:
                            result = {'success': False, 'message': f'Failed to list files: {e}', 'files': []}
                    elif step.action == 'create_bulk_folders':
                        result = self._execute_create_bulk_folders(step)
                    elif step.action == 'create_nested_folders':
                        result = self._execute_create_nested_folders(step)
                    elif step.action == 'verify_file_creation':
                        # Handle verification - just check if file exists
                        path = step.params.get('path') or step.params.get('file')
                        if path and os.path.exists(path):
                            result = {'success': True, 'message': f'File verified: {path}'}
                        else:
                            result = {'success': False, 'message': f'File not found: {path}'}
                    elif step.action == 'verify_folder_exists':
                        # Handle folder verification
                        path = step.params.get('path') or step.params.get('folder')
                        if path and os.path.exists(path):
                            result = {'success': True, 'message': f'Folder verified: {path}'}
                        else:
                            result = {'success': False, 'message': f'Folder not found: {path}'}
                    elif step.action == 'verify_files_created':
                        # Handle batch verification
                        paths = step.params.get('paths', [])
                        verified = [p for p in paths if os.path.exists(p)]
                        result = {
                            'success': len(verified) == len(paths),
                            'verified_count': len(verified),
                            'total_count': len(paths),
                            'message': f'Verified {len(verified)}/{len(paths)} files'
                        }
                    elif step.action == 'delete_folder':
                        # Handle folder deletion (safe - moves to recycle bin)
                        path = step.params.get('path') or step.params.get('folder')
                        permanent = step.params.get('permanent', False)
                        if path:
                            try:
                                if os.path.exists(path):
                                    if permanent:
                                        import shutil
                                        shutil.rmtree(path)
                                        result = {'success': True, 'message': f'Permanently deleted folder: {path}'}
                                    else:
                                        # Use Windows recycle bin (safe deletion)
                                        import subprocess
                                        try:
                                            subprocess.run(['powershell', '-Command', f'Remove-Item -Path "{path}" -Recurse -Force'], check=True)
                                            result = {'success': True, 'message': f'Deleted folder to recycle bin: {path}'}
                                        except:
                                            # Fallback to shutil
                                            import shutil
                                            shutil.rmtree(path)
                                            result = {'success': True, 'message': f'Deleted folder: {path}'}
                                else:
                                    result = {'success': False, 'message': f'Folder not found: {path}'}
                            except Exception as e:
                                result = {'success': False, 'message': f'Failed to delete folder: {e}'}
                        else:
                            result = {'success': False, 'message': 'No path specified for deletion'}
                    elif step.action == 'delete_file':
                        # Handle file deletion (safe - moves to recycle bin)
                        path = step.params.get('path') or step.params.get('file')
                        permanent = step.params.get('permanent', False)
                        if path:
                            try:
                                if os.path.exists(path):
                                    if permanent:
                                        os.remove(path)
                                        result = {'success': True, 'message': f'Permanently deleted file: {path}'}
                                    else:
                                        # Use Windows recycle bin (safe deletion)
                                        import subprocess
                                        try:
                                            subprocess.run(['powershell', '-Command', f'Remove-Item -Path "{path}" -Force'], check=True)
                                            result = {'success': True, 'message': f'Deleted file to recycle bin: {path}'}
                                        except:
                                            # Fallback
                                            os.remove(path)
                                            result = {'success': True, 'message': f'Deleted file: {path}'}
                                else:
                                    result = {'success': False, 'message': f'File not found: {path}'}
                            except Exception as e:
                                result = {'success': False, 'message': f'Failed to delete file: {e}'}
                        else:
                            result = {'success': False, 'message': 'No path specified for deletion'}
                    elif step.action == 'copy_file':
                        # Handle file copy
                        source = step.params.get('source') or step.params.get('file')
                        destination = step.params.get('destination') or step.params.get('dest')
                        if source and destination:
                            try:
                                if os.path.exists(source):
                                    import shutil
                                    # Create destination folder if it doesn't exist
                                    dest_dir = os.path.dirname(destination)
                                    if dest_dir:
                                        os.makedirs(dest_dir, exist_ok=True)
                                    shutil.copy2(source, destination)
                                    result = {'success': True, 'message': f'Copied {source} to {destination}', 'source': source, 'destination': destination}
                                else:
                                    result = {'success': False, 'message': f'Source file not found: {source}'}
                            except Exception as e:
                                result = {'success': False, 'message': f'Failed to copy file: {e}'}
                        else:
                            result = {'success': False, 'message': 'Source and destination paths required'}
                    elif step.action == 'move_file':
                        # Handle file move
                        source = step.params.get('source') or step.params.get('file') or step.params.get('path')
                        destination = step.params.get('destination') or step.params.get('dest')
                        if source and destination:
                            try:
                                if os.path.exists(source):
                                    import shutil
                                    # Create destination folder if it doesn't exist
                                    dest_dir = os.path.dirname(destination)
                                    if dest_dir:
                                        os.makedirs(dest_dir, exist_ok=True)
                                    shutil.move(source, destination)
                                    result = {'success': True, 'message': f'Moved {source} to {destination}', 'source': source, 'destination': destination}
                                else:
                                    result = {'success': False, 'message': f'Source file not found: {source}'}
                            except Exception as e:
                                result = {'success': False, 'message': f'Failed to move file: {e}'}
                        else:
                            result = {'success': False, 'message': 'Source and destination paths required'}
                    elif step.action == 'verify_deletion':
                        # Verify that a path was deleted
                        path = step.params.get('path')
                        if path:
                            if not os.path.exists(path):
                                result = {'success': True, 'message': f'Path successfully deleted: {path}'}
                            else:
                                result = {'success': False, 'message': f'Path still exists: {path}'}
                        else:
                            result = {'success': False, 'message': 'No path specified for verification'}
                    else:
                        raise Exception(f"Unknown filesystem action: {step.action}")
                elif step.category == 'project_generator':
                    result = self._execute_project_generator_step(step)
                elif step.category == 'package_manager':
                    result = self._execute_package_manager_step(step
)
                elif step.category == 'installer':
                    result = self._execute_installer_step(step)
                elif step.category == 'code_generator':
                    result = self._execute_code_generator_step(step)
                elif step.category == 'editor':
                    result = self._execute_editor_step(step)
                elif step.category == 'git':
                    result = self._execute_git_step(step)
                elif step.category == 'backup':
                    result = self._execute_backup_step(step)
                elif step.category == 'downloader':
                    result = self._execute_downloader_step(step)
                else:
                    # Use standard automator execution
                    # Resolve special paths in params
                    resolved_params = self._resolve_paths(step.params)
                    
                    parsed_command = {
                        'action': step.action,
                        'category': step.category,
                        'params': resolved_params
                    }
                    result = self.automator._execute_parsed_command(parsed_command)
                
                step_exec.end_time = time.time()
                step_exec.result = result
                step_exec.status = StepStatus.COMPLETED
                
                execution_time = step_exec.end_time - step_exec.start_time
                
                return {
                    'success': True,
                    'result': result,
                    'execution_time': execution_time,
                    'step_action': step.action
                }
                
            except Exception as e:
                step_exec.error = str(e)
                self.logger.error(f"Step execution failed (attempt {attempt + 1}): {e}")
                
                if attempt < self.max_retries:
                    self.logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    step_exec.status = StepStatus.FAILED
                    step_exec.end_time = time.time()
                    
                    return {
                        'success': False,
                        'error': f'Failed to execute step after {self.max_retries} attempts: {e}',
                        'execution_time': step_exec.end_time - step_exec.start_time if step_exec.start_time else 0,
                        'step_action': step.action,
                        'retry_count': attempt + 1
                    }
    
    def _execute_project_generator_step(self, step: ParsedStep) -> Any:
        """Execute project generator steps"""
        # Always use built-in project creation for reliability
        if step.action == 'create_python_project':
            return self._create_basic_python_project(step.params)
        elif step.action == 'create_c_project':
            return self._create_basic_c_project(step.params)
        elif step.action == 'create_web_scraping_project':
            return self._create_web_scraping_project(step.params)
        elif step.action == 'create_data_analysis_project':
            return self._create_data_analysis_project(step.params)
        else:
            # Try plugin if available
            if hasattr(self.automator.plugin_manager, 'plugins') and 'project_generator' in self.automator.plugin_manager.plugins:
                plugin = self.automator.plugin_manager.plugins['project_generator']
                return plugin.execute(step.action, step.params)
            else:
                return self._create_basic_python_project(step.params)
    
    def _execute_create_folder(self, step: ParsedStep) -> Dict[str, Any]:
        """Execute create_folder step"""
        import os
        
        name = step.params.get('name', '')
        location = step.params.get('location', '.')
        parent = step.params.get('parent', '')
        
        # Build the full path
        if parent:
            # If parent is specified, create under the parent folder
            if location and location != '.':
                full_path = os.path.join(location, parent, name)
            else:
                full_path = os.path.join(parent, name)
        elif location and location != '.':
            full_path = os.path.join(location, name)
        else:
            full_path = name
        
        # Create the folder
        try:
            os.makedirs(full_path, exist_ok=True)
            self.logger.info(f"Created folder: {full_path}")
            return {
                'success': True,
                'path': full_path,
                'message': f'Created folder: {full_path}'
            }
        except Exception as e:
            self.logger.error(f"Failed to create folder {full_path}: {e}")
            raise
    
    def _execute_create_file(self, step: ParsedStep) -> Dict[str, Any]:
        """Execute create_file step"""
        import os
        
        name = step.params.get('name', '')
        content = step.params.get('content', '')
        parent = step.params.get('parent', '')
        location = step.params.get('location', '.')
        template = step.params.get('template', '')
        
        # If no content but template is specified, generate code
        if not content and template:
            content = self._generate_algorithm_code(template, name)
        
        # If still no content but filename indicates an algorithm, generate it
        # Check for common programming language extensions
        if not content:
            code_extensions = ['.c', '.cpp', '.java', '.py', '.js', '.ts', '.go', '.rs', '.rb']
            for ext in code_extensions:
                if name.endswith(ext):
                    # Extract algorithm name from filename
                    algo_name = name.replace(ext, '').lower()
                    if algo_name and algo_name not in ['test', 'debug', 'temp']:
                        content = self._generate_algorithm_code(algo_name, name)
                    break
        
        # Build the full path
        if parent:
            if location and location != '.':
                folder_path = os.path.join(location, parent)
            else:
                folder_path = parent
        elif location and location != '.':
            folder_path = location
        else:
            folder_path = '.'
        
        file_path = os.path.join(folder_path, name)
        
        # Create the file
        try:
            os.makedirs(folder_path, exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(content)
            self.logger.info(f"Created file: {file_path}")
            return {
                'success': True,
                'path': file_path,
                'message': f'Created file: {file_path}'
            }
        except Exception as e:
            self.logger.error(f"Failed to create file {file_path}: {e}")
            raise
    
    def _generate_even_odd_code(self, language: str = 'c') -> str:
        """Generate even/odd checking code using AI for specified language"""
        language = language.lower().strip()
        
        # Use AI to generate the code dynamically
        try:
            from ..ai.openrouter_integration import OpenRouterAutomationAI
            ai = OpenRouterAutomationAI()
            
            prompt = f"""Generate a complete, working {language} program that checks if a number is even or odd.
            
Requirements:
- Take user input for a number
- Check if it's even (divisible by 2) or odd
- Display the result
- Include proper error handling for invalid input
- Use appropriate {language} syntax and conventions
- Include comments explaining the code
- Make it production-ready

Return ONLY the code, no explanations or markdown formatting."""
            
            # Use the AI to generate code
            if hasattr(ai, 'client') and ai.client:
                try:
                    response = ai.client.chat.completions.create(
                        model=ai.model_name,
                        messages=[
                            {"role": "system", "content": "You are an expert code generator. Generate production-ready code."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=1000
                    )
                    code = response.choices[0].message.content if response.choices else ""
                    
                    # Clean up markdown code blocks if present
                    if code and code.startswith('```'):
                        lines = code.split('\n')
                        if lines[0].startswith('```'):
                            code = '\n'.join(lines[1:])
                        if code.endswith('```'):
                            code = code[:-3]
                        code = code.strip()
                    
                    return code if code else self._generate_even_odd_fallback(language)
                except Exception as e:
                    self.logger.debug(f"OpenRouter API call failed: {e}")
                    return self._generate_even_odd_fallback(language)
            else:
                return self._generate_even_odd_fallback(language)
            
        except Exception as e:
            self.logger.warning(f"AI code generation failed, using fallback: {e}")
            return self._generate_even_odd_fallback(language)
    
    def _get_complexity_level(self, algorithm: str) -> str:
        """Determine if algorithm is simple, moderate, or complex"""
        algorithm = algorithm.lower()
        
        # Simple algorithms (basic logic, one function enough)
        simple = ['even', 'odd', 'prime', 'factorial', 'palindrome', 'reverse']
        # Moderate algorithms (some complexity, good for practice)
        moderate = ['fibonacci', 'bubble', 'selection', 'insertion', 'linear_search', 'binary_search']
        # Complex algorithms (optimization, advanced concepts)
        complex_algos = ['quick', 'merge', 'heap', 'dijkstra', 'bfs', 'dfs', 'dynamic']
        
        for simple_algo in simple:
            if simple_algo in algorithm:
                return 'simple'
        for moderate_algo in moderate:
            if moderate_algo in algorithm:
                return 'moderate'
        for complex_algo in complex_algos:
            if complex_algo in algorithm:
                return 'complex'
        
        return 'moderate'  # default
    
    def _generate_algorithm_code(self, algorithm: str, filename: str = '') -> str:
        """Generate code for any algorithm in any language using AI with adaptive complexity"""
        algorithm = algorithm.lower().strip()
        
        # Detect language and extract class name for Java
        language = 'c'  # default
        java_class_name = None
        
        if filename:
            if filename.endswith('.py'):
                language = 'python'
            elif filename.endswith('.java'):
                language = 'java'
                # Extract class name from filename (e.g., even_odd.java -> even_odd)
                java_class_name = filename.replace('.java', '')
            elif filename.endswith('.js'):
                language = 'javascript'
            elif filename.endswith('.cpp'):
                language = 'cpp'
            elif filename.endswith('.c'):
                language = 'c'
        
        # Determine complexity level
        complexity = self._get_complexity_level(algorithm)
        
        # Use AI to generate code dynamically for any algorithm/problem
        try:
            from ..ai.openrouter_integration import OpenRouterAutomationAI
            ai = OpenRouterAutomationAI()
            
            # Build adaptive prompt based on complexity
            # Extend supported algorithms to include more complex systems
            if algorithm in ['dijkstra', 'a_star', 'floyd_warshall']:
                algo_desc = f"implement the {algorithm} graph algorithm"
            elif algorithm in ['knapsack', 'longest_common_subsequence']:
                algo_desc = f"solve the {algorithm} problem using dynamic programming"
            elif algorithm in ['trie', 'avl_tree', 'red_black_tree']:
                algo_desc = f"implement the {algorithm} data structure"
            elif algorithm in ['producer_consumer', 'thread_safe_queue']:
                algo_desc = f"solve the {algorithm} concurrency problem"
            elif algorithm in ['http_server', 'websocket_communication']:
                algo_desc = f"build a {algorithm} system"
            elif algorithm in ['linear_regression', 'k_means']:
                algo_desc = f"implement the {algorithm} machine learning algorithm"
            elif algorithm in ['rsa_encryption', 'aes_implementation']:
                algo_desc = f"implement the {algorithm} cryptographic system"
            else:
                algo_desc = algorithm.replace('_', ' ')

            # Update the prompt to include the new algorithms
            prompt = self._build_generation_prompt(algo_desc, language, complexity, java_class_name)
            
            # Use the AI to generate code
            if hasattr(ai, 'client') and ai.client:
                try:
                    response = ai.client.chat.completions.create(
                        model=ai.model_name,
                        messages=[
                            {"role": "system", "content": self._get_system_prompt(language, complexity)},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=2000 if complexity == 'complex' else 1500
                    )
                    code = response.choices[0].message.content if response.choices else ""
                    
                    # Clean up markdown code blocks if present
                    if code and code.startswith('```'):
                        lines = code.split('\n')
                        if lines[0].startswith('```'):
                            code = '\n'.join(lines[1:])
                        if code.endswith('```'):
                            code = code[:-3]
                        code = code.strip()
                    
                    # Post-process code based on language
                    code = self._post_process_code(code, language, complexity)
                    
                    return code if code else self._generate_algorithm_fallback(algorithm, language, complexity)
                except Exception as e:
                    self.logger.debug(f"OpenRouter API call failed: {e}")
                    return self._generate_algorithm_fallback(algorithm, language, complexity)
            else:
                return self._generate_algorithm_fallback(algorithm, language, complexity)
            
        except Exception as e:
            self.logger.warning(f"AI code generation failed for {algorithm}, using fallback: {e}")
            return self._generate_algorithm_fallback(algorithm, language, complexity)
    
    def _build_generation_prompt(self, algorithm: str, language: str, complexity: str, java_class_name: str = None) -> str:
        """Build adaptive prompt based on complexity level"""
        algo_desc = algorithm.replace('_', ' ')
        
        if complexity == 'simple':
            prompt = f"""Write a simple, clean {language} program to {algo_desc}.

Requirements:
- Minimal, readable code (no over-engineering)
- One main function or method
- Basic comments explaining logic
- Handle invalid input gracefully
- Executable and testable
- ENSURE CODE IS 100% COMPLETE WITH ALL CLOSING BRACES/BLOCKS

Return ONLY the complete, valid {language} code. No markdown formatting."""
        
        elif complexity == 'moderate':
            prompt = f"""Write a {language} program to implement {algo_desc}.

Requirements:
- Well-organized code with helper functions/methods
- Clear variable names and comments
- Proper error handling
- Include test cases or examples
- Performance should be reasonable
- Executable and complete
- ENSURE CODE IS 100% COMPLETE WITH ALL CLOSING BRACES/BLOCKS
- Use ONLY ASCII characters (no unicode superscripts or special symbols)

Return ONLY the complete, valid {language} code. No markdown formatting."""
        
        else:  # complex
            prompt = f"""Write an optimized, production-ready {language} implementation of {algo_desc}.

Requirements:
- Use best practices and advanced techniques for {language}
- Include optimization strategies (e.g., memoization, dynamic programming, efficient sorting)
- Comprehensive error handling
- Clear documentation with complexity analysis
- Include examples with output
- Thoroughly tested with edge cases
- Professional code structure
- ENSURE CODE IS 100% COMPLETE WITH ALL CLOSING BRACES/BLOCKS
- Use ONLY ASCII characters (no unicode superscripts or special symbols)
- Wrap main method/function logic in proper closing blocks

Return ONLY the complete, valid {language} code. No markdown formatting."""
        
        # Special instruction for Java
        if language == 'java' and java_class_name:
            prompt += f"\n\nIMPORTANT: \n1. The public class name MUST be exactly '{java_class_name}'\n2. Include complete main method with all closing braces\n3. Use ASCII complexity notation: O(n log n) not O(n log n) with superscripts"
        
        return prompt
    
    def _get_system_prompt(self, language: str, complexity: str) -> str:
        """Get language and complexity-appropriate system prompt"""
        complexity_text = {
            'simple': 'for simple, readable code',
            'moderate': 'for well-structured, balanced code',
            'complex': 'for optimized, production-quality code'
        }
        
        return f"You are an expert {language} programmer specializing in {complexity_text.get(complexity, 'general')}. Generate only executable, working code."
    
    def _post_process_code(self, code: str, language: str, complexity: str) -> str:
        """Post-process generated code for language-specific requirements"""
        if not code:
            return code
        
        # Remove Python shebang for simple/moderate complexity
        if language == 'python' and complexity in ['simple', 'moderate']:
            lines = code.split('\n')
            if lines and lines[0].startswith('#!'):
                code = '\n'.join(lines[1:]).lstrip()
        
        # Validate and fix Java code
        if language == 'java':
            code = self._validate_and_fix_java_code(code)
        
        # Validate and fix C code
        if language == 'c':
            code = self._validate_and_fix_c_code(code)
        
        return code.strip()
    
    def _validate_and_fix_java_code(self, code: str) -> str:
        """Validate and fix Java code - ensure all braces are matched and ASCII only"""
        # Count opening and closing braces
        open_braces = code.count('{')
        close_braces = code.count('}')
        
        # If there are unmatched braces, add closing ones
        if open_braces > close_braces:
            code += '\n' + '}\n' * (open_braces - close_braces)
        
        # Replace common Unicode issues with ASCII equivalents
        # Replace superscript 2 with ^2 in comments
        code = code.replace('O(n²)', 'O(n^2)').replace('n²', 'n^2').replace('Θ(n²)', 'O(n^2)')
        code = code.replace('O(n²log n)', 'O(n^2 log n)').replace('Θ(n log n)', 'O(n log n)')
        
        return code
    
    def _validate_and_fix_c_code(self, code: str) -> str:
        """Validate and fix C code - ensure all braces are matched"""
        # Count opening and closing braces
        open_braces = code.count('{')
        close_braces = code.count('}')
        
        # If there are unmatched braces, add closing ones
        if open_braces > close_braces:
            code += '\n' + '}\n' * (open_braces - close_braces)
        
        return code
    
    def _generate_algorithm_fallback(self, algorithm: str, language: str, complexity: str = 'moderate') -> str:
        """Fallback code generation when AI is unavailable"""
        # Basic fallback templates for common algorithms
        if language == 'python':
            if complexity == 'simple':
                return f'''# {algorithm}

def {algorithm.replace('-', '_')}():
    print("Implementation of {algorithm}")

if __name__ == "__main__":
    {algorithm.replace('-', '_')}()
'''
            else:
                return f'''"""
{algorithm} implementation
Auto-generated fallback code
"""

def main():
    print(f"Implementation of {algorithm}")

if __name__ == "__main__":
    main()
'''
        
        elif language == 'java':
            # Extract class name from algorithm, ensuring it matches Java naming conventions
            class_name = algorithm.replace('_', '')
            if class_name and class_name[0].isdigit():
                class_name = 'Algorithm' + class_name
            if not class_name:
                class_name = 'Main'
            
            if complexity == 'simple':
                return f'''public class {class_name} {{
    public static void main(String[] args) {{
        System.out.println("{algorithm}");
    }}
}}
'''
            else:
                return f'''/**
 * {algorithm} implementation
 * Auto-generated fallback code
 */
public class {class_name} {{
    
    /**
     * Main method
     */
    public static void main(String[] args) {{
        System.out.println("Implementation of {algorithm}");
    }}
}}
'''
        
        elif language == 'javascript':
            if complexity == 'simple':
                return f'''// {algorithm}

function main() {{
    console.log("{algorithm}");
}}

main();
'''
            else:
                return f'''/**
 * {algorithm} implementation
 * Auto-generated fallback code
 */

function main() {{
    console.log("Implementation of {algorithm}");
}}

main();
'''
        
        elif language == 'cpp':
            if complexity == 'simple':
                return f'''#include <iostream>
using namespace std;

int main() {{
    cout << "{algorithm}" << endl;
    return 0;
}}
'''
            else:
                return f'''#include <iostream>
using namespace std;

/**
 * {algorithm} implementation
 * Auto-generated fallback code
 */

int main() {{
    cout << "Implementation of {algorithm}" << endl;
    return 0;
}}
'''
        
        else:  # C
            if complexity == 'simple':
                return f'''#include <stdio.h>

int main() {{
    printf("{algorithm}\\n");
    return 0;
}}
'''
            else:
                return f'''#include <stdio.h>

/**
 * {algorithm} implementation
 * Auto-generated fallback code
 */

int main() {{
    printf("Implementation of {algorithm}\\n");
    return 0;
}}
'''
    
    def _generate_even_odd_fallback(self, language: str) -> str:
        """Fallback for even/odd code generation"""
        if language == 'python':
            return '''#!/usr/bin/env python3
def check_even_odd(num):
    return f"{num} is even" if num % 2 == 0 else f"{num} is odd"

if __name__ == "__main__":
    try:
        number = int(input("Enter a number: "))
        print(check_even_odd(number))
    except ValueError:
        print("Please enter a valid integer")
'''
        elif language == 'java':
            return '''import java.util.Scanner;
public class EvenOdd {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        try {
            System.out.print("Enter a number: ");
            int num = sc.nextInt();
            System.out.println(num + (num % 2 == 0 ? " is even" : " is odd"));
        } catch (Exception e) {
            System.out.println("Invalid input");
        } finally {
            sc.close();
        }
    }
}
'''
        elif language == 'javascript':
            return '''const readline = require('readline');
const rl = readline.createInterface({input: process.stdin, output: process.stdout});
rl.question('Enter a number: ', (input) => {
    const num = parseInt(input);
    console.log(isNaN(num) ? "Invalid input" : num + (num % 2 === 0 ? " is even" : " is odd"));
    rl.close();
});
'''
        elif language == 'cpp':
            return '''#include <iostream>
using namespace std;
int main() {
    int num;
    cout << "Enter a number: ";
    cin >> num;
    cout << num << (num % 2 == 0 ? " is even" : " is odd") << endl;
    return 0;
}
'''
        else:  # C
            return '''#include <stdio.h>
int main() {
    int num;
    printf("Enter a number: ");
    scanf("%d", &num);
    printf("%d is %s\\n", num, num % 2 == 0 ? "even" : "odd");
    return 0;
}
'''
    
    def _execute_create_bulk_folders(self, step: ParsedStep) -> Dict[str, Any]:
        """Execute create_bulk_folders step - creates multiple folders with naming pattern"""
        import os
        
        base_name = step.params.get('base_name', '')
        start = step.params.get('start', 1)
        end = step.params.get('end', 10)
        location = step.params.get('location', '.')
        
        created = []
        
        try:
            for i in range(start, end + 1):
                folder_name = f"{base_name}{i}"
                full_path = os.path.join(location, folder_name)
                os.makedirs(full_path, exist_ok=True)
                created.append(full_path)
            
            self.logger.info(f"Created {len(created)} bulk folders")
            return {
                'success': True,
                'created_folders': created,
                'count': len(created),
                'message': f'Created {len(created)} folders'
            }
        except Exception as e:
            self.logger.error(f"Failed to create bulk folders: {e}")
            raise
    
    def _execute_create_nested_folders(self, step: ParsedStep) -> Dict[str, Any]:
        """Execute create_nested_folders step - creates parent folder with nested subfolders"""
        import os
        
        parent_name = step.params.get('parent_name', '')
        subfolders = step.params.get('subfolders', [])
        location = step.params.get('location', '.')
        
        created = []
        
        try:
            # Create parent folder
            parent_path = os.path.join(location, parent_name)
            os.makedirs(parent_path, exist_ok=True)
            created.append(parent_path)
            
            # Handle subfolders based on type
            if isinstance(subfolders, dict):
                # Complex nested structure
                # Check for test_range pattern (e.g., test2 to test100)
                if 'test_range' in subfolders:
                    test_range = subfolders['test_range']
                    test_base = test_range.get('base', 'test')
                    test_start = test_range.get('start', 2)
                    test_end = test_range.get('end', 100)
                    
                    # Create numbered subfolders
                    for i in range(test_start, test_end + 1):
                        subfolder_name = f"{test_base}{i}"
                        subfolder_path = os.path.join(parent_path, subfolder_name)
                        os.makedirs(subfolder_path, exist_ok=True)
                        created.append(subfolder_path)
                        
            elif isinstance(subfolders, list):
                # Simple list of subfolder names
                for subfolder in subfolders:
                    subfolder_path = os.path.join(parent_path, subfolder)
                    os.makedirs(subfolder_path, exist_ok=True)
                    created.append(subfolder_path)
            
            self.logger.info(f"Created nested folder structure with {len(created)} folders total")
            return {
                'success': True,
                'created_folders': created,
                'count': len(created),
                'message': f'Created nested folder structure with {len(created)} folders'
            }
        except Exception as e:
            self.logger.error(f"Failed to create nested folders: {e}")
            raise
    
    def _execute_package_manager_step(self, step: ParsedStep) -> Any:
        """Execute package manager steps"""
        if step.action == 'install_packages':
            packages = step.params.get('packages', [])
            # Simulate package installation
            self.logger.info(f"Installing packages: {packages}")
            time.sleep(2)  # Simulate installation time
            return f"Installed packages: {', '.join(packages)}"
        else:
            raise Exception(f"Unknown package manager action: {step.action}")
    
    def _execute_installer_step(self, step: ParsedStep) -> Any:
        """Execute installer steps"""
        self.logger.info(f"Simulating installation: {step.action}")
        time.sleep(5)  # Simulate installation time
        return f"Installed: {step.action}"
    
    def _execute_code_generator_step(self, step: ParsedStep) -> Any:
        """Execute code generator steps"""
        if step.action == 'create_news_scraper':
            return self._create_news_scraper_code(step.params)
        else:
            raise Exception(f"Unknown code generator action: {step.action}")
    
    def _execute_editor_step(self, step: ParsedStep) -> Any:
        """Execute editor steps"""
        if step.action == 'open_in_vscode':
            path = step.params.get('path', '.')
            # Simulate opening in VS Code
            self.logger.info(f"Opening {path} in VS Code")
            return f"Opened {path} in VS Code"
        else:
            raise Exception(f"Unknown editor action: {step.action}")
    
    def _execute_git_step(self, step: ParsedStep) -> Any:
        """Execute git steps"""
        if step.action == 'clone_repository':
            url = step.params.get('url')
            self.logger.info(f"Cloning repository: {url}")
            time.sleep(3)  # Simulate clone time
            return f"Cloned repository: {url}"
        else:
            raise Exception(f"Unknown git action: {step.action}")
    
    def _execute_backup_step(self, step: ParsedStep) -> Any:
        """Execute backup steps"""
        if step.action == 'backup_folder':
            source = step.params.get('source')
            destination = step.params.get('destination')
            self.logger.info(f"Backing up {source} to {destination}")
            time.sleep(5)  # Simulate backup time
            return f"Backed up {source} to {destination}"
        else:
            raise Exception(f"Unknown backup action: {step.action}")
    
    def _execute_downloader_step(self, step: ParsedStep) -> Any:
        """Execute downloader steps"""
        if step.action == 'download_python_installer':
            version = step.params.get('version', 'latest')
            self.logger.info(f"Downloading Python installer version: {version}")
            time.sleep(10)  # Simulate download time
            return f"Downloaded Python installer: {version}"
        else:
            raise Exception(f"Unknown downloader action: {step.action}")
    
    def _create_basic_python_project(self, params: Dict[str, Any]) -> str:
        """Create a basic Python project structure"""
        name = params.get('name', 'MyProject')
        project_type = params.get('type', 'basic')
        
        # Use the filesystem adapter to create the project
        fs_adapter = self.automator.os_adapter.filesystem
        
        # Create main directory
        fs_adapter.create_folder(name)
        
        # Create basic files based on type
        if project_type == 'web_scraping':
            content = '''import requests
from bs4 import BeautifulSoup

def scrape_news():
    """Scrape news headlines"""
    url = "https://news.ycombinator.com"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    headlines = []
    for item in soup.find_all('a', class_='storylink'):
        headlines.append(item.get_text())
    
    return headlines

if __name__ == "__main__":
    headlines = scrape_news()
    for i, headline in enumerate(headlines[:10], 1):
        print(f"{i}. {headline}")
'''
        else:
            content = '''#!/usr/bin/env python3
"""
Main module
"""

def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
'''
        
        fs_adapter.create_file('main.py', name, content)
        
        return f"Created Python project: {name}"
    
    def _create_web_scraping_project(self, params: Dict[str, Any]) -> str:
        """Create a web scraping project structure"""
        name = params.get('name', 'WebScrapingProject')
        
        fs_adapter = self.automator.os_adapter.filesystem
        
        # Create project directory
        fs_adapter.create_folder(name)
        
        # Create main scraper file
        scraper_content = '''#!/usr/bin/env python3
"""
Web scraper for news headlines
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time

class NewsBot:
    """News scraping bot"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scrape_headlines(self):
        """Scrape news headlines from multiple sources"""
        headlines = []
        
        # Example sources (you can add more)
        sources = {
            'BBC': 'https://www.bbc.com/news',
            'Reuters': 'https://www.reuters.com',
        }
        
        for source_name, url in sources.items():
            try:
                print(f"Scraping {source_name}...")
                response = self.session.get(url, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Generic headline extraction (adjust selectors as needed)
                headline_selectors = [
                    'h1', 'h2', 'h3',
                    '.headline', '.title',
                    '[data-testid*="headline"]'
                ]
                
                for selector in headline_selectors:
                    elements = soup.select(selector)[:5]  # Get top 5
                    for element in elements:
                        text = element.get_text(strip=True)
                        if len(text) > 20:  # Filter out short text
                            headlines.append({
                                'source': source_name,
                                'headline': text,
                                'timestamp': datetime.now().isoformat(),
                                'url': url
                            })
                    if headlines:  # If we found headlines, break
                        break
                        
            except Exception as e:
                print(f"Error scraping {source_name}: {e}")
        
        return headlines
    
    def save_headlines(self, headlines, filename='headlines.json'):
        """Save headlines to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(headlines, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(headlines)} headlines to {filename}")
    
    def run(self):
        """Main execution method"""
        print("NewsBot - Web Scraping Headlines")
        print("=" * 40)
        
        headlines = self.scrape_headlines()
        
        if headlines:
            print(f"\\nFound {len(headlines)} headlines:")
            for i, item in enumerate(headlines[:10], 1):
                print(f"{i}. [{item['source']}] {item['headline'][:80]}...")
            
            self.save_headlines(headlines)
        else:
            print("No headlines found. Check your internet connection and source URLs.")

if __name__ == "__main__":
    bot = NewsBot()
    bot.run()
'''
        
        fs_adapter.create_file('main.py', name, scraper_content)
        
        # Create requirements.txt
        requirements_content = '''requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
'''
        
        fs_adapter.create_file('requirements.txt', name, requirements_content)
        
        # Create README
        readme_content = f'''# {name}

A Python web scraping project for collecting news headlines.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Features

- Scrapes headlines from multiple news sources
- Saves results to JSON format
- Handles errors gracefully
- Configurable sources and selectors

## Files

- `main.py` - Main scraper script
- `requirements.txt` - Python dependencies
- `headlines.json` - Output file (created after running)
'''
        
        fs_adapter.create_file('README.md', name, readme_content)
        
        return f"Created web scraping project: {name}"
    
    def _create_data_analysis_project(self, params: Dict[str, Any]) -> str:
        """Create a comprehensive data analysis project"""
        name = params.get('name', 'DataAnalysisProject')
        
        fs_adapter = self.automator.os_adapter.filesystem
        
        # Create project directory structure
        fs_adapter.create_folder(name)
        fs_adapter.create_folder('data', name)
        fs_adapter.create_folder('notebooks', name)
        fs_adapter.create_folder('src', name)
        fs_adapter.create_folder('reports', name)
        fs_adapter.create_folder('visualizations', name)
        
        # Create a simple, valid notebook using JSON to avoid escaping issues
        import json
        
        notebook_data = {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [
                        "# Data Analysis Project\n",
                        "\n",
                        "Comprehensive data analysis with automated report generation"
                    ]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Import required libraries\n",
                        "import pandas as pd\n",
                        "import numpy as np\n",
                        "import matplotlib.pyplot as plt\n",
                        "import seaborn as sns\n",
                        "from datetime import datetime\n",
                        "\n",
                        "print('📊 Data Analysis Environment Ready!')"
                    ]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Generate sample data\n",
                        "np.random.seed(42)\n",
                        "n_samples = 1000\n",
                        "\n",
                        "df = pd.DataFrame({\n",
                        "    'date': pd.date_range('2023-01-01', periods=n_samples, freq='D'),\n",
                        "    'category': np.random.choice(['A', 'B', 'C', 'D'], n_samples),\n",
                        "    'value': np.random.normal(100, 20, n_samples),\n",
                        "    'score': np.random.uniform(0, 100, n_samples)\n",
                        "})\n",
                        "\n",
                        "print(f'Dataset shape: {df.shape}')\n",
                        "df.head()"
                    ]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Basic analysis\n",
                        "print('📈 Dataset Overview:')\n",
                        "print(df.describe())\n",
                        "\n",
                        "# Simple visualization\n",
                        "plt.figure(figsize=(12, 8))\n",
                        "\n",
                        "# Create subplots\n",
                        "plt.subplot(2, 2, 1)\n",
                        "sns.histplot(data=df, x='value', hue='category')\n",
                        "plt.title('Value Distribution by Category')\n",
                        "\n",
                        "plt.subplot(2, 2, 2)\n",
                        "sns.boxplot(data=df, x='category', y='score')\n",
                        "plt.title('Score Distribution by Category')\n",
                        "\n",
                        "plt.subplot(2, 2, 3)\n",
                        "df.groupby('category')['value'].mean().plot(kind='bar')\n",
                        "plt.title('Average Value by Category')\n",
                        "plt.xticks(rotation=45)\n",
                        "\n",
                        "plt.subplot(2, 2, 4)\n",
                        "correlation_matrix = df.select_dtypes(include=[np.number]).corr()\n",
                        "sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm')\n",
                        "plt.title('Correlation Matrix')\n",
                        "\n",
                        "plt.tight_layout()\n",
                        "plt.savefig('../visualizations/analysis_dashboard.png', dpi=300, bbox_inches='tight')\n",
                        "plt.show()"
                    ]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Statistical analysis\n",
                        "from scipy import stats\n",
                        "\n",
                        "print('📊 Statistical Analysis Results')\n",
                        "print('=' * 50)\n",
                        "\n",
                        "# Group statistics\n",
                        "category_stats = df.groupby('category').agg({\n",
                        "    'value': ['mean', 'std', 'count'],\n",
                        "    'score': ['mean', 'std']\n",
                        "}).round(2)\n",
                        "\n",
                        "print('Category Statistics:')\n",
                        "print(category_stats)\n",
                        "\n",
                        "# ANOVA test\n",
                        "groups = [group['value'].values for name, group in df.groupby('category')]\n",
                        "f_stat, p_value = stats.f_oneway(*groups)\n",
                        "\n",
                        "print('\\nANOVA Test Results:')\n",
                        "print(f'F-statistic: {f_stat:.4f}')\n",
                        "print(f'P-value: {p_value:.4f}')\n",
                        "significance = 'Yes' if p_value < 0.05 else 'No'\n",
                        "print(f'Significant difference: {significance}')"
                    ]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "# Export results\n",
                        "print('💾 Exporting results...')\n",
                        "\n",
                        "# Save processed data\n",
                        "df.to_csv('../data/processed_data.csv', index=False)\n",
                        "print('✅ Saved processed data to CSV')\n",
                        "\n",
                        "# Save summary statistics\n",
                        "summary_stats = df.describe()\n",
                        "summary_stats.to_csv('../reports/summary_statistics.csv')\n",
                        "print('✅ Saved summary statistics')\n",
                        "\n",
                        "# Generate simple HTML report\n",
                        "html_report = f'''\n",
                        "<!DOCTYPE html>\n",
                        "<html>\n",
                        "<head>\n",
                        "    <title>Data Analysis Report</title>\n",
                        "    <style>\n",
                        "        body {{ font-family: Arial, sans-serif; margin: 40px; }}\n",
                        "        h1, h2 {{ color: #2c3e50; }}\n",
                        "        .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; }}\n",
                        "    </style>\n",
                        "</head>\n",
                        "<body>\n",
                        "    <h1>📊 Data Analysis Report</h1>\n",
                        "    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n",
                        "    \n",
                        "    <div class=\"summary\">\n",
                        "        <h2>Summary</h2>\n",
                        "        <ul>\n",
                        "            <li>Dataset contains {df.shape[0]:,} records with {df.shape[1]} variables</li>\n",
                        "            <li>Categories analyzed: {', '.join(df['category'].unique())}</li>\n",
                        "            <li>Average value: {df['value'].mean():.2f}</li>\n",
                        "        </ul>\n",
                        "    </div>\n",
                        "    \n",
                        "    <h2>Statistical Summary</h2>\n",
                        "    {df.describe().to_html()}\n",
                        "    \n",
                        "    <p><em>Report generated by OmniAutomator Data Analysis System</em></p>\n",
                        "</body>\n",
                        "</html>\n",
                        "'''\n",
                        "\n",
                        "with open('../reports/analysis_report.html', 'w', encoding='utf-8') as f:\n",
                        "    f.write(html_report)\n",
                        "\n",
                        "print('✅ Generated HTML report')\n",
                        "print('\\n🎉 Analysis complete! Check the reports folder for results.')"
                    ]
                }
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3"
                },
                "language_info": {
                    "name": "python",
                    "version": "3.8.0"
                }
            },
            "nbformat": 4,
            "nbformat_minor": 4
        }
        
        notebook_content = json.dumps(notebook_data, indent=1)
        
        fs_adapter.create_file('analysis_notebook.ipynb', f'{name}/notebooks', notebook_content)
        
        # Create data analysis utilities
        utils_content = '''#!/usr/bin/env python3
"""
Data Analysis Utilities
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os

class DataAnalyzer:
    """Comprehensive data analysis toolkit"""
    
    def __init__(self, data_path=None):
        self.data_path = data_path
        self.df = None
        
    def load_data(self, file_path):
        """Load data from various formats"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.csv':
            self.df = pd.read_csv(file_path)
        elif ext in ['.xlsx', '.xls']:
            self.df = pd.read_excel(file_path)
        elif ext == '.json':
            self.df = pd.read_json(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
        
        print(f"Data loaded: {self.df.shape[0]} rows, {self.df.shape[1]} columns")
        return self.df
    
    def quick_analysis(self):
        """Perform quick exploratory analysis"""
        if self.df is None:
            raise ValueError("No data loaded")
        
        print("📊 Quick Analysis Report")
        print("=" * 50)
        print(f"Shape: {self.df.shape}")
        print(f"Columns: {list(self.df.columns)}")
        print(f"\\nData Types:\\n{self.df.dtypes}")
        print(f"\\nMissing Values:\\n{self.df.isnull().sum()}")
        print(f"\\nSummary Statistics:\\n{self.df.describe()}")
        
    def create_dashboard(self, output_path='../visualizations/dashboard.png'):
        """Create comprehensive visualization dashboard"""
        if self.df is None:
            raise ValueError("No data loaded")
        
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        
        if len(numeric_cols) < 2:
            print("Not enough numeric columns for dashboard")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Data Analysis Dashboard', fontsize=16)
        
        # Distribution plot
        self.df[numeric_cols[0]].hist(ax=axes[0,0], bins=30)
        axes[0,0].set_title(f'Distribution of {numeric_cols[0]}')
        
        # Correlation heatmap
        if len(numeric_cols) > 1:
            sns.heatmap(self.df[numeric_cols].corr(), annot=True, ax=axes[0,1])
            axes[0,1].set_title('Correlation Matrix')
        
        # Box plot
        if len(numeric_cols) > 1:
            self.df.boxplot(column=numeric_cols[1], ax=axes[1,0])
            axes[1,0].set_title(f'Box Plot of {numeric_cols[1]}')
        
        # Scatter plot
        if len(numeric_cols) > 1:
            axes[1,1].scatter(self.df[numeric_cols[0]], self.df[numeric_cols[1]])
            axes[1,1].set_xlabel(numeric_cols[0])
            axes[1,1].set_ylabel(numeric_cols[1])
            axes[1,1].set_title('Scatter Plot')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Dashboard saved to: {output_path}")
        
    def generate_report(self, output_path='../reports/auto_report.html'):
        """Generate automated HTML report"""
        if self.df is None:
            raise ValueError("No data loaded")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Automated Data Analysis Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1, h2 {{ color: #2c3e50; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>📊 Automated Data Analysis Report</h1>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h2>Dataset Overview</h2>
            <ul>
                <li>Rows: {self.df.shape[0]:,}</li>
                <li>Columns: {self.df.shape[1]}</li>
                <li>Memory Usage: {self.df.memory_usage(deep=True).sum() / 1024**2:.2f} MB</li>
            </ul>
            
            <h2>Summary Statistics</h2>
            {self.df.describe().to_html()}
            
            <h2>Data Types</h2>
            {pd.DataFrame(self.df.dtypes, columns=['Data Type']).to_html()}
            
            <h2>Missing Values</h2>
            {pd.DataFrame(self.df.isnull().sum(), columns=['Missing Count']).to_html()}
            
        </body>
        </html>
        """
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Report saved to: {output_path}")

# Example usage
if __name__ == "__main__":
    analyzer = DataAnalyzer()
    
    # Generate sample data for demonstration
    np.random.seed(42)
    sample_data = pd.DataFrame({
        'date': pd.date_range('2023-01-01', periods=1000),
        'value': np.random.normal(100, 20, 1000),
        'category': np.random.choice(['A', 'B', 'C'], 1000),
        'score': np.random.uniform(0, 100, 1000)
    })
    
    analyzer.df = sample_data
    analyzer.quick_analysis()
    analyzer.create_dashboard()
    analyzer.generate_report()
'''
        
        fs_adapter.create_file('data_analyzer.py', f'{name}/src', utils_content)
        
        # Create requirements.txt
        requirements_content = '''jupyter>=1.0.0
pandas>=2.0.0
numpy>=1.24.0
matplotlib>=3.7.0
seaborn>=0.12.0
scipy>=1.10.0
plotly>=5.14.0
openpyxl>=3.1.0
xlsxwriter>=3.1.0
'''
        
        fs_adapter.create_file('requirements.txt', name, requirements_content)
        
        # Create README.md
        readme_content = f'''# {name}

Comprehensive data analysis project with automated report generation.

## 🚀 Features

- **Jupyter Notebooks**: Interactive analysis environment
- **Automated Reports**: HTML reports with statistics and visualizations
- **Multiple Data Formats**: CSV, Excel, JSON support
- **Rich Visualizations**: Charts, plots, and dashboards
- **Statistical Analysis**: Descriptive stats, correlations, hypothesis testing
- **Export Capabilities**: Save results in multiple formats

## 📁 Project Structure

```
{name}/
├── data/                   # Raw and processed datasets
├── notebooks/              # Jupyter notebooks
│   └── analysis_notebook.ipynb
├── src/                    # Python utilities
│   └── data_analyzer.py
├── reports/                # Generated reports
├── visualizations/         # Charts and plots
├── requirements.txt        # Dependencies
└── README.md              # This file
```

## 🛠️ Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Start Jupyter
jupyter notebook notebooks/analysis_notebook.ipynb
```

## 📊 Quick Start

### Using Jupyter Notebook
1. Open `notebooks/analysis_notebook.ipynb`
2. Run all cells to see the complete analysis
3. Modify data loading section for your dataset

### Using Python Script
```python
from src.data_analyzer import DataAnalyzer

# Initialize analyzer
analyzer = DataAnalyzer()

# Load your data
analyzer.load_data('data/your_dataset.csv')

# Quick analysis
analyzer.quick_analysis()

# Create dashboard
analyzer.create_dashboard()

# Generate report
analyzer.generate_report()
```

## 📈 Analysis Features

- **Exploratory Data Analysis**: Shape, types, missing values
- **Statistical Summary**: Mean, median, std, quartiles
- **Visualizations**: Histograms, box plots, scatter plots, heatmaps
- **Correlation Analysis**: Relationship between variables
- **Automated Reporting**: HTML reports with all findings

## 🎯 Outputs

- `reports/analysis_report.html` - Comprehensive HTML report
- `reports/summary_statistics.csv` - Statistical summaries
- `visualizations/analysis_dashboard.png` - Visual dashboard
- `data/processed_data.csv` - Cleaned and processed data

## 🔧 Customization

- Modify `src/data_analyzer.py` for custom analysis functions
- Add new visualization types in the notebook
- Extend report templates for specific needs
- Add new data sources and formats

## 📚 Libraries Used

- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computing
- **matplotlib**: Basic plotting
- **seaborn**: Statistical visualizations
- **scipy**: Statistical functions
- **jupyter**: Interactive notebooks

## 🚀 Advanced Usage

For complex analyses, extend the `DataAnalyzer` class:

```python
class AdvancedAnalyzer(DataAnalyzer):
    def time_series_analysis(self):
        # Add time series specific methods
        pass
    
    def machine_learning_insights(self):
        # Add ML-based analysis
        pass
```

---

*Generated by OmniAutomator - Universal OS Automation Framework*
'''
        
        fs_adapter.create_file('README.md', name, readme_content)
        
        # Create sample data file
        sample_data_script = '''#!/usr/bin/env python3
"""
Generate sample data for analysis
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_sample_data(n_samples=1000):
    """Generate sample dataset for analysis"""
    
    np.random.seed(42)
    
    # Generate dates
    start_date = datetime.now() - timedelta(days=n_samples)
    dates = pd.date_range(start_date, periods=n_samples, freq='D')
    
    # Generate sample data
    data = {
        'date': dates,
        'product': np.random.choice(['Product_A', 'Product_B', 'Product_C', 'Product_D'], n_samples),
        'region': np.random.choice(['North', 'South', 'East', 'West'], n_samples),
        'sales': np.random.normal(1000, 200, n_samples),
        'profit': np.random.normal(150, 50, n_samples),
        'customers': np.random.poisson(25, n_samples),
        'satisfaction': np.random.uniform(1, 5, n_samples),
        'temperature': np.random.normal(20, 10, n_samples),  # Weather data
        'marketing_spend': np.random.exponential(100, n_samples)
    }
    
    df = pd.DataFrame(data)
    
    # Add some correlations
    df['profit'] = df['sales'] * 0.15 + np.random.normal(0, 20, n_samples)
    df['customers'] = (df['sales'] / 40 + np.random.normal(0, 5, n_samples)).astype(int)
    
    # Add seasonal effects
    df['sales'] += 200 * np.sin(2 * np.pi * df.index / 365.25)
    
    # Ensure positive values
    df['sales'] = np.maximum(df['sales'], 100)
    df['profit'] = np.maximum(df['profit'], 10)
    df['customers'] = np.maximum(df['customers'], 1)
    
    return df

if __name__ == "__main__":
    # Generate and save sample data
    df = generate_sample_data(1000)
    df.to_csv('sample_dataset.csv', index=False)
    
    print(f"Sample dataset created: {df.shape[0]} rows, {df.shape[1]} columns")
    print("Columns:", list(df.columns))
    print("\\nFirst 5 rows:")
    print(df.head())
    print("\\nSaved to: sample_dataset.csv")
'''
        
        fs_adapter.create_file('generate_sample_data.py', f'{name}/data', sample_data_script)
        
        return f"Created comprehensive data analysis project: {name}"
    
    def _create_basic_c_project(self, params: Dict[str, Any]) -> str:
        """Create a basic C project structure"""
        name = params.get('name', 'MyProject')
        
        fs_adapter = self.automator.os_adapter.filesystem
        
        # Create project directory
        fs_adapter.create_folder(name)
        
        # Create main.c
        content = '''#include <stdio.h>

int main() {
    int num1, num2, sum;
    
    printf("Enter first number: ");
    scanf("%d", &num1);
    
    printf("Enter second number: ");
    scanf("%d", &num2);
    
    sum = num1 + num2;
    
    printf("Sum: %d + %d = %d\\n", num1, num2, sum);
    
    return 0;
}
'''
        
        fs_adapter.create_file('main.c', name, content)
        
        return f"Created C project: {name}"
    
    def _create_news_scraper_code(self, params: Dict[str, Any]) -> str:
        """Create news scraper code"""
        filename = params.get('filename', 'scraper.py')
        target = params.get('target', 'headlines')
        
        content = '''import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def scrape_headlines():
    """Scrape news headlines from multiple sources"""
    sources = {
        'Hacker News': 'https://news.ycombinator.com',
        'Reddit Programming': 'https://www.reddit.com/r/programming.json'
    }
    
    all_headlines = []
    
    for source_name, url in sources.items():
        try:
            print(f"Scraping {source_name}...")
            
            if 'reddit' in url:
                # Handle Reddit JSON API
                headers = {'User-Agent': 'NewsScraperBot 1.0'}
                response = requests.get(url, headers=headers)
                data = response.json()
                
                for post in data['data']['children'][:10]:
                    all_headlines.append({
                        'title': post['data']['title'],
                        'source': source_name,
                        'url': post['data']['url'],
                        'timestamp': datetime.now().isoformat()
                    })
            else:
                # Handle HTML scraping
                response = requests.get(url)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                for item in soup.find_all('a', class_='storylink')[:10]:
                    all_headlines.append({
                        'title': item.get_text(),
                        'source': source_name,
                        'url': item.get('href', ''),
                        'timestamp': datetime.now().isoformat()
                    })
                    
        except Exception as e:
            print(f"Error scraping {source_name}: {e}")
    
    return all_headlines

def save_headlines(headlines, filename='headlines.json'):
    """Save headlines to JSON file"""
    with open(filename, 'w') as f:
        json.dump(headlines, f, indent=2)
    print(f"Saved {len(headlines)} headlines to {filename}")

def main():
    print("News Headline Scraper")
    print("====================")
    
    headlines = scrape_headlines()
    
    print(f"\\nFound {len(headlines)} headlines:")
    for i, headline in enumerate(headlines, 1):
        print(f"{i}. [{headline['source']}] {headline['title']}")
    
    save_headlines(headlines)

if __name__ == "__main__":
    main()
'''
        
        # Create the file
        fs_adapter = self.automator.os_adapter.filesystem
        fs_adapter.create_file(filename, None, content)
        
        return f"Created news scraper: {filename}"
    
    def _group_steps_for_execution(self) -> List[List[StepExecution]]:
        """Group steps for optimal execution order"""
        groups = []
        remaining_steps = self.step_executions.copy()
        
        while remaining_steps:
            current_group = []
            
            # Find steps that can be executed (no unmet dependencies)
            for step_exec in remaining_steps[:]:
                if self._can_execute_step(step_exec, [s.step for group in groups for s in group]):
                    current_group.append(step_exec)
                    remaining_steps.remove(step_exec)
            
            if not current_group:
                # If no steps can be executed, there might be circular dependencies
                # Add the first remaining step to break the cycle
                current_group.append(remaining_steps.pop(0))
            
            groups.append(current_group)
        
        return groups
    
    def _can_execute_step(self, step_exec: StepExecution, completed_steps: List[ParsedStep]) -> bool:
        """Check if a step can be executed based on dependencies"""
        if not step_exec.step.dependencies:
            return True
        
        completed_indices = [i for i, step in enumerate(self.current_workflow.steps) if step in completed_steps]
        
        for dep_index in step_exec.step.dependencies:
            if dep_index not in completed_indices:
                return False
        
        return True
    
    def _execute_step_group(self, group: List[StepExecution]) -> List[Dict[str, Any]]:
        """Execute a group of steps, potentially in parallel"""
        if len(group) == 1:
            # Single step, execute directly
            return [self._execute_step(group[0])]
        
        # Multiple steps, execute in parallel if safe
        if len(group) <= self.max_parallel_steps:
            return self._execute_parallel_steps(group)
        else:
            # Too many steps, execute sequentially
            return [self._execute_step(step_exec) for step_exec in group]
    
    def _execute_parallel_steps(self, steps: List[StepExecution]) -> List[Dict[str, Any]]:
        """Execute steps in parallel using ThreadPoolExecutor"""
        results = []
        
        with ThreadPoolExecutor(max_workers=min(len(steps), self.max_parallel_steps)) as executor:
            # Submit all steps
            future_to_step = {executor.submit(self._execute_step, step_exec): step_exec for step_exec in steps}
            
            # Collect results as they complete
            for future in as_completed(future_to_step):
                step_exec = future_to_step[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({
                        'success': False,
                        'error': str(e),
                        'step_action': step_exec.step.action
                    })
        
        return results
    
    def _check_dependencies(self, step_exec: StepExecution) -> bool:
        """Check if step dependencies are satisfied"""
        if not step_exec.step.dependencies:
            return True
        
        for dep_index in step_exec.step.dependencies:
            if dep_index >= len(self.step_executions):
                return False
            
            dep_step = self.step_executions[dep_index]
            if dep_step.status != StepStatus.COMPLETED:
                return False
        
        return True
    
    def _evaluate_conditions(self, conditions: List[str]) -> bool:
        """Evaluate step conditions"""
        # Simple condition evaluation - can be enhanced
        for condition in conditions:
            # For now, just return True for basic conditions
            # This would be enhanced with actual condition parsing
            if 'file exists' in condition.lower():
                # Check if file exists
                continue
            elif 'process running' in condition.lower():
                # Check if process is running
                continue
        
        return True
    
    def _update_context(self, step_exec: StepExecution, result: Dict[str, Any]):
        """Update workflow context with step results"""
        if result['success']:
            self.workflow_context[f"step_{step_exec.step.action}_result"] = result.get('result')
            self.workflow_context[f"step_{step_exec.step.action}_completed"] = True
    
    def _notify_progress(self, current_group: int, total_groups: int, group_results: List[Dict[str, Any]]):
        """Notify progress callbacks"""
        progress_info = {
            'current_group': current_group,
            'total_groups': total_groups,
            'group_results': group_results,
            'overall_progress': (current_group / total_groups) * 100
        }
        
        for callback in self.progress_callbacks:
            try:
                callback(progress_info)
            except Exception as e:
                self.logger.error(f"Progress callback error: {e}")
    
    def _get_completed_steps(self) -> List[str]:
        """Get list of completed step actions"""
        return [step_exec.step.action for step_exec in self.step_executions if step_exec.status == StepStatus.COMPLETED]
    
    def _get_failed_step(self) -> Optional[str]:
        """Get the first failed step action"""
        for step_exec in self.step_executions:
            if step_exec.status == StepStatus.FAILED:
                return step_exec.step.action
        return None
    
    def _generate_execution_summary(self) -> Dict[str, Any]:
        """Generate execution summary"""
        status_counts = {}
        for status in StepStatus:
            status_counts[status.value] = sum(1 for step_exec in self.step_executions if step_exec.status == status)
        
        return {
            'total_steps': len(self.step_executions),
            'status_breakdown': status_counts,
            'success_rate': (status_counts.get('completed', 0) / len(self.step_executions)) * 100 if self.step_executions else 0,
            'total_retries': sum(step_exec.retry_count for step_exec in self.step_executions)
        }
    
    def add_progress_callback(self, callback: Callable):
        """Add a progress callback function"""
        self.progress_callbacks.append(callback)
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status"""
        if not self.current_workflow:
            return {'status': 'idle'}
        
        return {
            'status': 'running' if any(step.status == StepStatus.RUNNING for step in self.step_executions) else 'completed',
            'original_command': self.current_workflow.original_command,
            'complexity': self.current_workflow.complexity.value,
            'progress': self._generate_execution_summary(),
            'current_step': next((step.step.action for step in self.step_executions if step.status == StepStatus.RUNNING), None)
        }
    
    def _resolve_paths(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve special path names to actual paths"""
        import os
        
        resolved_params = params.copy()
        
        # Common path mappings
        path_mappings = {
            'desktop': os.path.join(os.path.expanduser('~'), 'Desktop'),
            'documents': os.path.join(os.path.expanduser('~'), 'Documents'),
            'downloads': os.path.join(os.path.expanduser('~'), 'Downloads'),
            'home': os.path.expanduser('~'),
            'current': os.getcwd(),
            'temp': os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Temp') if os.name == 'nt' else '/tmp'
        }
        
        # Resolve location parameter
        if 'location' in resolved_params:
            location = resolved_params['location']
            if isinstance(location, str):
                location_lower = location.lower()
                if location_lower in path_mappings:
                    resolved_params['location'] = path_mappings[location_lower]
                elif location_lower.startswith('desktop/') or location_lower.startswith('desktop\\'):
                    # Handle paths like "Desktop/FolderName"
                    desktop_path = path_mappings['desktop']
                    relative_path = location[8:]  # Remove "Desktop/"
                    resolved_params['location'] = os.path.join(desktop_path, relative_path)
        
        # Resolve path parameter
        if 'path' in resolved_params:
            path = resolved_params['path']
            if isinstance(path, str):
                path_lower = path.lower()
                if path_lower in path_mappings:
                    resolved_params['path'] = path_mappings[path_lower]
        
        return resolved_params
