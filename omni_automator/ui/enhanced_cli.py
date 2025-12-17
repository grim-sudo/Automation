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
from omni_automator.core.semantic_nlp_engine import get_semantic_nlp
from omni_automator.utils.logger import get_logger


class InteractionMode(Enum):
    """Interaction mode"""
    CLI = "cli"
    INTERACTIVE = "interactive"
    GUI = "gui"
    BATCH = "batch"


class EnhancedCLI:
    """Enhanced CLI with flexible command processing"""
    
    def __init__(self, mode: InteractionMode = InteractionMode.CLI):
        self.logger = get_logger("EnhancedCLI")
        self.base_engine = OmniAutomator()
        self.workflow_engine = EnhancedWorkflowEngine()
        self.executor = get_ai_task_executor()
        self.mode = mode
        self.ai_manager = get_ai_manager()
        self.nlp_processor = get_nlp_processor()
        self.semantic_nlp = get_semantic_nlp()
        self.running = True
        self.command_history = []
        self.max_history = 100
        
        # Import smart features
        try:
            from omni_automator.core.spell_correction import get_spell_corrector
            from omni_automator.core.smart_error_handler import get_smart_error_handler
            self.spell_corrector = get_spell_corrector()
            self.error_handler = get_smart_error_handler()
        except ImportError:
            self.spell_corrector = None
            self.error_handler = None
    
    @property
    def engine(self):
        """Backward compatibility"""
        return self.base_engine
    
    def _apply_spell_correction(self, command: str) -> str:
        """Apply spell correction if available"""
        if self.spell_corrector:
            return self.spell_corrector.correct_text(command)
        return command
    
    def _is_complex_command(self, command: str) -> bool:
        """Check if command is complex"""
        import re
        if len(command) > 150:
            return bool(re.search(r'(\d+.*folders?|nested|hierarchy|structure)', command, re.IGNORECASE))
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
        print("\nAvailable Commands:")
        print("  /help     - Show help")
        print("  /history  - Show command history")
        print("  /status   - Show system status")
        print("  /cd       - Change directory")
        print("  /pwd      - Print working directory")
        print("  /ls       - List files")
        print("  quit      - Exit\n")
        
        # Execute initial commands if provided
        if initial_commands:
            for cmd in initial_commands:
                self._execute_interactive_command(cmd)
        
        # Interactive loop
        while self.running:
            try:
                user_input = input("\n> ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit']:
                    self.running = False
                    print("Goodbye!")
                    break
                
                self._execute_interactive_command(user_input)
            except KeyboardInterrupt:
                print("\n\nInterrupted. Type 'quit' to exit.")
            except Exception as e:
                print(f"Error: {e}")
    
    def _execute_interactive_command(self, command: str) -> None:
        """Execute command in interactive mode"""
        # Special commands
        if command.startswith('/'):
            self._handle_special_command(command)
            return
        
        # Regular commands with spell correction
        corrected_command = self._apply_spell_correction(command)
        
        if corrected_command != command:
            print(f"Correction: {command} -> {corrected_command}")
        
        # Analyze with semantic NLP
        analysis = self.semantic_nlp.analyze(corrected_command)
        print(f"Intent: {analysis.intent.value} (Confidence: {analysis.confidence:.1%})")
        
        # Execute
        try:
            result = self.base_engine.execute(corrected_command)
            self._format_and_display_result(result)
            self.command_history.append(command)
            if len(self.command_history) > self.max_history:
                self.command_history = self.command_history[-self.max_history:]
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(str(e), command)
            else:
                print(f"Error: {e}")
    
    def _handle_special_command(self, command: str) -> None:
        """Handle special commands like /help"""
        if command == '/help':
            print("Available commands: /help, /history, /status, /cd, /pwd, /ls")
        elif command == '/history':
            for i, cmd in enumerate(self.command_history, 1):
                print(f"{i:3d}. {cmd}")
        elif command == '/status':
            print("Status: Running")
        else:
            print(f"Unknown command: {command}")
    
    def _format_and_display_result(self, result: dict) -> None:
        """Format and display execution results in human-readable format"""
        if not isinstance(result, dict):
            print(f"Result: {result}")
            return
        
        # Check if execution was successful
        success = result.get('success', False)
        completed_steps = result.get('completed_steps', 0)
        total_steps = result.get('total_steps', 0)
        results_list = result.get('results', [])
        execution_time = result.get('total_execution_time', 0)
        
        # Header
        status_symbol = "✅" if success else "❌"
        print(f"\n{status_symbol} {'SUCCESS' if success else 'FAILED'} - {completed_steps}/{total_steps} steps completed")
        
        # Display results for each step
        if results_list:
            print("\n📋 Operation Results:")
            for i, step_result in enumerate(results_list, 1):
                if isinstance(step_result, dict):
                    step_status = "✓" if step_result.get('success', False) else "✗"
                    action = step_result.get('action', 'Unknown')
                    details = step_result.get('details', '')
                    created_item = step_result.get('created_item') or step_result.get('created_folder') or step_result.get('created_file')
                    
                    if created_item:
                        print(f"   {step_status} {i}. {action}: {created_item}")
                    elif details:
                        print(f"   {step_status} {i}. {action}: {details}")
                    else:
                        print(f"   {step_status} {i}. {action}")
        
        # Execution time
        if execution_time:
            time_ms = execution_time * 1000
            print(f"\n⏱️  Execution Time: {time_ms:.2f} ms")
        
        print()  # Blank line for readability
    
    def _run_batch(self, commands: Optional[List[str]] = None) -> None:
        """Run batch mode"""
        if not commands:
            return
        
        for cmd in commands:
            print(f"\nExecuting: {cmd}")
            corrected = self._apply_spell_correction(cmd)
            try:
                self.base_engine.execute(corrected)
            except Exception as e:
                print(f"Error: {e}")
    
    def _run_cli(self, commands: Optional[List[str]] = None) -> None:
        """Run CLI mode"""
        if not commands:
            return
        
        for cmd in commands:
            corrected = self._apply_spell_correction(cmd)
            try:
                self.base_engine.execute(corrected)
            except Exception as e:
                if self.error_handler:
                    self.error_handler.handle_error(str(e), cmd)
                else:
                    print(f"Error: {e}")
    
    def _run_gui(self) -> None:
        """Run GUI mode"""
        try:
            from omni_automator.ui.gui_app import OmniAutomatorGUI
            gui = OmniAutomatorGUI()
            gui.run()
        except ImportError:
            print("GUI mode requires PyQt/Tkinter. Please install required dependencies.")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="OmniAutomator - Intelligent Automation System"
    )
    parser.add_argument('commands', nargs='*', help='Commands to execute')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    parser.add_argument('--batch', '-b', type=str, help='Batch file')
    parser.add_argument('--gui', '-g', action='store_true', help='GUI mode')
    
    args = parser.parse_args()
    
    # Determine mode
    if args.gui:
        mode = InteractionMode.GUI
    elif args.interactive:
        mode = InteractionMode.INTERACTIVE
    elif args.batch:
        mode = InteractionMode.BATCH
        if os.path.exists(args.batch):
            with open(args.batch, 'r') as f:
                args.commands = [line.strip() for line in f if line.strip()]
        else:
            print(f"Batch file not found: {args.batch}")
            sys.exit(1)
    else:
        mode = InteractionMode.CLI
    
    # Create and run CLI
    cli = EnhancedCLI(mode)
    cli.run(args.commands if args.commands else None)


if __name__ == '__main__':
    main()
