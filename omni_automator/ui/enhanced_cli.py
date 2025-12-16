#!/usr/bin/env python3
"""
Enhanced CLI with Flexible Command Support and AI Integration
Supports GUI, interactive mode, and all command variations
"""

import sys
import os
from typing import Optional, List
from enum import Enum

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omni_automator.core.engine import OmniAutomator
from omni_automator.core.enhanced_workflow_engine import EnhancedWorkflowEngine
from omni_automator.core.ai_model_manager import get_ai_manager, AIModelConfig
from omni_automator.core.ai_task_executor import get_ai_task_executor
from omni_automator.core.flexible_nlp import get_nlp_processor


class InteractionMode(Enum):
    """Interaction mode"""
    CLI = "cli"
    INTERACTIVE = "interactive"
    GUI = "gui"
    BATCH = "batch"


class EnhancedCLI:
    """Enhanced CLI with flexible command processing"""
    
    def __init__(self, mode: InteractionMode = InteractionMode.CLI):
        # Use the full OmniAutomator engine for complex commands
        self.base_engine = OmniAutomator()
        # Keep the workflow engine for simple commands
        self.workflow_engine = EnhancedWorkflowEngine()
        self.executor = get_ai_task_executor()
        self.mode = mode
        self.ai_manager = get_ai_manager()
        self.nlp_processor = get_nlp_processor()
        self.running = True
        self.command_history = []
        self.max_history = 100
    
    # Alias for backward compatibility
    @property
    def engine(self):
        return self.base_engine
    
    def _is_complex_command(self, command: str) -> bool:
        """Check if command has nested/loop structures"""
        import re
        
        if len(command) > 150:
            patterns = [
                r'in\s+(?:that|those|each|every)',
                r'and\s+in\s+',
                r'inside\s+(?:each|every)',
                r'\d+\s+folders?.*\d+\s+folders?',
            ]
            
            for pattern in patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    return True
            
            if command.lower().count(' and ') >= 3:
                return True
        
        return False
    
    def run(self, commands: Optional[List[str]] = None) -> None:
        """Run the CLI"""
        if self.mode == InteractionMode.INTERACTIVE:
            self._run_interactive(commands)
        elif self.mode == InteractionMode.BATCH:
            self._run_batch(commands)
        elif self.mode == InteractionMode.GUI:
            self._run_gui()
        else:
            self._run_cli(commands)
    
    def _run_interactive(self, initial_commands: Optional[List[str]] = None) -> None:
        """Run interactive mode"""
        print("=" * 60)
        print("OmniAutomator - Interactive Mode")
        print("=" * 60)
        self._show_interactive_help()
        
        # Execute initial commands if provided
        if initial_commands:
            for cmd in initial_commands:
                self._execute_interactive_command(cmd)
        
        # Interactive loop
        while self.running:
            try:
                user_input = input("\n📟 Enter command (or 'help' for commands, 'quit' to exit): ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() == 'quit':
                    self.running = False
                    print("Goodbye!")
                    break
                
                self._execute_interactive_command(user_input)
            
            except KeyboardInterrupt:
                print("\nInterrupted. Type 'quit' to exit.")
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def _run_batch(self, commands: List[str]) -> None:
        """Run batch mode"""
        print("=" * 60)
        print("OmniAutomator - Batch Mode")
        print(f"Executing {len(commands)} commands...")
        print("=" * 60)
        
        execution = self.engine.execute_workflow(commands, "batch_job")
        
        print(f"\n✅ Batch execution completed:")
        print(f"  - Steps executed: {execution.steps_executed}/{execution.total_steps}")
        print(f"  - Steps failed: {execution.steps_failed}")
        print(f"  - AI queries: {execution.ai_queries}")
        print(f"  - Started: {execution.started_at}")
        print(f"  - Completed: {execution.completed_at}")
    
    def _run_cli(self, commands: Optional[List[str]] = None) -> None:
        """Run CLI mode"""
        if not commands:
            self._show_cli_help()
            return
        
        for command in commands:
            self._execute_cli_command(command)
    
    def _run_gui(self) -> None:
        """Run GUI mode"""
        try:
            from ui.gui_app import GUIApplication
            
            app = GUIApplication(self.engine)
            app.run()
        
        except ImportError:
            print("GUI module not available. Run in interactive mode instead.")
            self.mode = InteractionMode.INTERACTIVE
            self._run_interactive()
    
    def _execute_interactive_command(self, user_input: str) -> None:
        """Execute command in interactive mode"""
        # Handle special commands
        if user_input.lower().startswith('help'):
            self._show_interactive_help()
            return
        
        if user_input.lower().startswith('history'):
            self._show_command_history()
            return
        
        if user_input.lower().startswith('models'):
            self._show_ai_models()
            return
        
        if user_input.lower().startswith('switch'):
            self._handle_model_switch(user_input)
            return
        
        if user_input.lower().startswith('variations'):
            self._show_command_variations(user_input)
            return
        
        # Execute as command
        self._execute_command(user_input)
    
    def _execute_cli_command(self, command: str) -> None:
        """Execute single command in CLI mode"""
        print(f"Executing: {command}")
        self._execute_command(command)
        print()
    
    def _execute_command(self, command: str) -> None:
        """Execute a command - with AI analysis and task execution bridge"""
        # Add to history
        self.command_history.append(command)
        if len(self.command_history) > self.max_history:
            self.command_history.pop(0)
        
        try:
            print(f"🔄 Processing: {command}")
        except:
            print(f"Processing: {command}")
        
        # For complex commands with loops/nesting, use the full OmniAutomator engine
        # which handles the advanced parser with loop support properly
        if self._is_complex_command(command):
            result = self.base_engine.execute(command)
            try:
                print(f"✅ Status: {'SUCCESS' if result.get('success') else 'FAILED'}")
            except:
                print(f"Status: {'SUCCESS' if result.get('success') else 'FAILED'}")
            if result.get('success'):
                print(f"   - Total steps: {result.get('steps_completed', result.get('total_steps', 'multiple'))}")
            else:
                print(f"   - Error: {result.get('error')}")
        else:
            # For simple commands, use the workflow engine
            result = self.workflow_engine.execute_command(command)
            step = result['step']
            parsed = result['parsed']
            ai_response = result.get('ai_response')
            
            # Display results
            try:
                print(f"✅ Status: {step.status.value.upper()}")
            except:
                print(f"Status: {step.status.value.upper()}")
            try:
                print(f"📌 Action: {parsed.action}")
            except:
                print(f"Action: {parsed.action}")
            try:
                print(f"📂 Category: {parsed.category}")
            except:
                print(f"Category: {parsed.category}")
            print(f"Confidence: {parsed.confidence:.1%}")
            try:
                print(f"🔄 Flexibility Score: {parsed.flexibility_score:.2f}")
            except:
                print(f"Flexibility Score: {parsed.flexibility_score:.2f}")
            
            if parsed.params:
                print(f"Parameters:")
                for key, value in parsed.params.items():
                    print(f"   - {key}: {value}")
            
            # For code modification, execute directly without AI plan
            if parsed.category == 'modify_file':
                try:
                    print(f"\n🔧 Executing file modification...")
                except:
                    print(f"\nExecuting file modification...")
                parsed_command = {
                    'action': 'modify_file',
                    'category': 'code_modification',
                    'params': parsed.params
                }
                mod_result = self.base_engine._execute_parsed_command(parsed_command)
                if mod_result.get('success'):
                    print(f"✅ File successfully modified!")
                    print(f"   - Intent: {parsed.params.get('intent')}")
                else:
                    print(f"❌ Modification failed: {mod_result.get('error')}")
            # Check if AI generated a task plan and execute it
            elif ai_response and hasattr(ai_response, 'task_plan') and ai_response.task_plan:
                print(f"\n🤖 AI Analysis Generated Task Plan:")
                print(f"   - Intent: {ai_response.task_plan.get('interpreted_intent', 'Unknown')}")
                print(f"   - Confidence: {ai_response.task_plan.get('confidence_score', 0):.2%}")
                print(f"   - Steps: {len(ai_response.task_plan.get('execution_steps', []))}")
                
                # Execute the AI-generated task plan
                print(f"\n⚡ Executing AI-generated tasks...")
                execution_result = self.executor.execute_task_plan(ai_response.task_plan)
                
                if execution_result['success']:
                    print(f"✅ Task execution successful!")
                    print(f"   - Created resources: {len(execution_result.get('created_resources', []))}")
                    if execution_result.get('created_resources'):
                        for resource in execution_result['created_resources'][:5]:
                            print(f"      ✓ {resource}")
                        if len(execution_result['created_resources']) > 5:
                            print(f"      ... and {len(execution_result['created_resources']) - 5} more")
                else:
                    print(f"❌ Task execution failed:")
                    for failure in execution_result.get('failed_operations', []):
                        print(f"   - Step {failure.get('step')}: {failure.get('error')}")
            elif ai_response:
                ai_resp = ai_response
                print(f"\n🤖 AI Enhancement:")
                print(f"   - Model: {ai_resp.model_used}")
                print(f"   - Provider: {ai_resp.provider}")
                print(f"   - Response: {ai_resp.content[:200]}...")
            
            if step.result:
                print(f"📤 Result: {step.result}")
            
            if step.error:
                print(f"❌ Error: {step.error}")
    
    def _show_interactive_help(self) -> None:
        """Show help for interactive mode"""
        print("""
Available Commands:
  - File operations: create folder, delete file, copy files, move files
  - Deployments: deploy app with Docker, setup Kubernetes, deploy to cloud
  - Databases: setup database, create schema, backup database
  - Pipelines: create CI/CD pipeline, setup monitoring, optimize workflow
  - Data: backup data, migrate data, sync data
  - ML/AI: setup ML pipeline, train model, deploy model
  - Security: setup security, audit permissions, encrypt data

Examples (natural language variations supported):
  ✓ "create a folder called myproject"
  ✓ "make folder myproject"
  ✓ "setup myproject folder on desktop"
  ✓ "deploy app using docker"
  ✓ "migrate database from mysql to postgresql"
  ✓ "setup kubernetes cluster for production"

Special Commands:
  - help              Show this help
  - history           Show command history
  - models            List AI models
  - switch <model>    Switch AI model
  - variations <cmd>  Show command variations
  - quit              Exit
        """)
    
    def _show_cli_help(self) -> None:
        """Show help for CLI mode"""
        print("""
OmniAutomator - Enhanced CLI

Usage:
  python omnimator --interactive    Run in interactive mode
  python omnimator --batch <file>   Run batch commands from file
  python omnimator --gui            Run GUI mode
  python omnimator "<command>"      Execute single command
  python omnimator "<cmd1>" "<cmd2>" Execute multiple commands

Examples:
  python omnimator "create folder myproject"
  python omnimator "deploy app using docker"
  python omnimator "setup database with postgresql"

For more help, run in interactive mode with --interactive flag.
        """)
    
    def _show_command_history(self) -> None:
        """Show command history"""
        if not self.command_history:
            print("No command history.")
            return
        
        print(f"\n📜 Command History ({len(self.command_history)} commands):")
        for i, cmd in enumerate(self.command_history, 1):
            print(f"  {i:3d}. {cmd}")
    
    def _show_ai_models(self) -> None:
        """Show available AI models"""
        current = self.ai_manager.get_current_model_info()
        models = self.ai_manager.list_registered_models()
        
        print(f"\n🤖 AI Models:")
        
        if current:
            print(f"  Current: {current['name']} ({current['provider']})")
        
        if models:
            print(f"  Registered:")
            for name, info in models.items():
                marker = "✓" if info['is_current'] else " "
                print(f"    [{marker}] {name} ({info['provider']})")
        else:
            print("  No models registered.")
    
    def _handle_model_switch(self, user_input: str) -> None:
        """Handle model switching"""
        parts = user_input.split(None, 1)
        if len(parts) < 2:
            self._show_ai_models()
            return
        
        model_name = parts[1].strip()
        if self.engine.switch_ai_model(model_name):
            print(f"✅ Switched to model: {model_name}")
        else:
            print(f"❌ Model '{model_name}' not found")
            self._show_ai_models()
    
    def _show_command_variations(self, user_input: str) -> None:
        """Show command variations"""
        # Extract command from "variations <command>"
        parts = user_input.split(None, 1)
        if len(parts) < 2:
            print("Usage: variations <command>")
            return
        
        command = parts[1]
        variations = self.engine.get_command_alternatives(command)
        
        print(f"\n📌 Command Variations:")
        print(f"  Original: {variations['original']}")
        print(f"  Alternatives ({variations['count'] - 1}):")
        for alt in variations['alternatives'][1:]:
            print(f"    • {alt}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="OmniAutomator - Intelligent Automation System"
    )
    parser.add_argument(
        'commands',
        nargs='*',
        help='Commands to execute'
    )
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Run in interactive mode'
    )
    parser.add_argument(
        '--batch', '-b',
        type=str,
        help='Run batch commands from file'
    )
    parser.add_argument(
        '--gui', '-g',
        action='store_true',
        help='Run in GUI mode'
    )
    parser.add_argument(
        '--model', '-m',
        type=str,
        help='Specify AI model to use'
    )
    
    args = parser.parse_args()
    
    # Determine mode
    if args.gui:
        mode = InteractionMode.GUI
    elif args.interactive:
        mode = InteractionMode.INTERACTIVE
    elif args.batch:
        mode = InteractionMode.BATCH
        # Load batch file
        if os.path.exists(args.batch):
            with open(args.batch, 'r') as f:
                args.commands = [line.strip() for line in f if line.strip()]
        else:
            print(f"Error: Batch file not found: {args.batch}")
            sys.exit(1)
    else:
        mode = InteractionMode.CLI
    
    # Create CLI
    cli = EnhancedCLI(mode)
    
    # Switch model if specified
    if args.model:
        cli.engine.switch_ai_model(args.model)
    
    # Run
    if args.commands or mode != InteractionMode.CLI:
        cli.run(args.commands if args.commands else None)
    else:
        # Show help if no commands
        cli._show_cli_help()


if __name__ == '__main__':
    main()
