#!/usr/bin/env python3
"""
Enhanced CLI with Flexible Command Support and AI Integration
Supports GUI, interactive mode, and all command variations
"""

import os
import sys
from enum import Enum

from loguru import logger

from archon.ai.task_executor import get_ai_task_executor
from archon.core.engine import Archon
from archon.nlp.flexible_processor import get_nlp_processor
from archon.nlp.semantic_engine import get_semantic_nlp
from archon.utils.logger import get_logger


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
        self.base_engine = Archon()
        self.executor = get_ai_task_executor()
        self.mode = mode
        self.nlp_processor = get_nlp_processor()
        self.semantic_nlp = get_semantic_nlp()
        self.running = True
        self.command_history = []
        self.max_history = 100

        # Import smart features
        try:
            from archon.nlp.spell_corrector import get_spell_corrector
            from archon.workflow.error_handler import get_smart_error_handler

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
        if not self.spell_corrector:
            return command

        # Skip spell correction for commands with technical patterns
        import re

        skip_patterns = [
            r"\d+-\d+",  # Number ranges like "1-100"
            r"\b\w+\d+\b",  # Words with numbers like "folder1", "test123"
            r"\breadme\b",  # Common technical terms
            r"\b(?:numbered?|naming)\b",  # Technical keywords
        ]

        for pattern in skip_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return command

        return self.spell_corrector.correct_text(command)

    def _is_complex_command(self, command: str) -> bool:
        """Check if command is complex"""
        import re

        if len(command) > 150:
            return bool(
                re.search(r"(\d+.*folders?|nested|hierarchy|structure)", command, re.IGNORECASE)
            )
        return False

    def run(self, commands: list[str] | None = None) -> None:
        """Run the CLI"""
        if self.mode == InteractionMode.INTERACTIVE:
            self._run_interactive(commands)
        elif self.mode == InteractionMode.BATCH:
            self._run_batch(commands)
        elif self.mode == InteractionMode.GUI:
            self._run_gui()
        else:
            self._run_cli(commands)

    def _run_interactive(self, initial_commands: list[str] | None = None) -> None:
        """Run interactive mode"""
        logger.info("=" * 60)
        logger.info("Archon - Interactive Mode")
        logger.info("=" * 60)
        logger.info("Available Commands:")
        logger.info("  /help     - Show help")
        logger.info("  /history  - Show command history")
        logger.info("  /status   - Show system status")
        logger.info("  /cd       - Change directory")
        logger.info("  /pwd      - Print working directory")
        logger.info("  /ls       - List files")
        logger.info("  quit      - Exit")

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

                if user_input.lower() in ["quit", "exit"]:
                    self.running = False
                    logger.info("Goodbye!")
                    break

                self._execute_interactive_command(user_input)
            except KeyboardInterrupt:
                logger.warning("Interrupted. Type 'quit' to exit.")
            except Exception as e:
                logger.error(f"Error: {e}")

    def _execute_interactive_command(self, command: str) -> None:
        """Execute command in interactive mode"""
        # Special commands
        if command.startswith("/"):
            self._handle_special_command(command)
            return

        # Regular commands with spell correction
        corrected_command = self._apply_spell_correction(command)

        if corrected_command != command:
            logger.info(f"Correction: {command} -> {corrected_command}")

        # Analyze with semantic NLP
        analysis = self.semantic_nlp.analyze(corrected_command)
        logger.info(f"Intent: {analysis.intent.value} (Confidence: {analysis.confidence:.1%})")

        # Route through the seamless chat() router so questions get an AI
        # answer and only real commands hit execution.
        try:
            result = self.base_engine.chat(corrected_command)
            if result.get("kind") == "conversation":
                logger.info(result.get("reply", ""))
            else:
                self._format_and_display_result(result)
            self.command_history.append(command)
            if len(self.command_history) > self.max_history:
                self.command_history = self.command_history[-self.max_history :]
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(str(e), command)
            else:
                logger.error(f"Error: {e}")

    def _handle_special_command(self, command: str) -> None:
        """Handle special commands like /help"""
        if command == "/help":
            logger.info("Available commands: /help, /history, /status, /cd, /pwd, /ls")
        elif command == "/history":
            for i, cmd in enumerate(self.command_history, 1):
                logger.info(f"{i:3d}. {cmd}")
        elif command == "/status":
            logger.info("Status: Running")
        else:
            logger.info(f"Unknown command: {command}")

    def _format_and_display_result(self, result: dict) -> None:
        """Format and display execution results in human-readable format"""
        if not isinstance(result, dict):
            logger.info(f"Result: {result}")
            return

        # Check if execution was successful
        success = result.get("success", False)
        completed_steps = result.get("completed_steps", 0)
        total_steps = result.get("total_steps", 0)
        results_list = result.get("results", [])
        execution_time = result.get("total_execution_time", 0)

        # Header
        status_word = "SUCCESS" if success else "FAILED"
        logger.info(f"{status_word} - {completed_steps}/{total_steps} steps completed")

        # Display results for each step
        if results_list:
            logger.info("Operation Results:")
            for i, step_result in enumerate(results_list, 1):
                if isinstance(step_result, dict):
                    step_status = "OK" if step_result.get("success", False) else "FAIL"
                    action = step_result.get("action", "Unknown")
                    details = step_result.get("details", "")
                    created_item = (
                        step_result.get("created_item")
                        or step_result.get("created_folder")
                        or step_result.get("created_file")
                    )

                    if created_item:
                        logger.info(f"  [{step_status}] {i}. {action}: {created_item}")
                    elif details:
                        logger.info(f"  [{step_status}] {i}. {action}: {details}")
                    else:
                        logger.info(f"  [{step_status}] {i}. {action}")

        # Execution time
        if execution_time:
            time_ms = execution_time * 1000
            logger.info(f"Execution Time: {time_ms:.2f} ms")

    def _run_batch(self, commands: list[str] | None = None) -> None:
        """Run batch mode"""
        if not commands:
            return

        for cmd in commands:
            logger.info(f"Executing: {cmd}")
            corrected = self._apply_spell_correction(cmd)
            try:
                self.base_engine.execute(corrected)
            except Exception as e:
                logger.error(f"Error: {e}")

    def _run_cli(self, commands: list[str] | None = None) -> None:
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
                    logger.error(f"Error: {e}")

    def _run_gui(self) -> None:
        """Run GUI mode (delegates to the Tauri desktop app)."""
        from archon._cli import gui

        gui()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Archon - Intelligent Automation System")
    parser.add_argument("commands", nargs="*", help="Commands to execute")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--batch", "-b", type=str, help="Batch file")
    parser.add_argument("--gui", "-g", action="store_true", help="GUI mode")

    args = parser.parse_args()

    # Determine mode
    if args.gui:
        mode = InteractionMode.GUI
    elif args.interactive:
        mode = InteractionMode.INTERACTIVE
    elif args.batch:
        mode = InteractionMode.BATCH
        if os.path.exists(args.batch):
            with open(args.batch) as f:
                args.commands = [line.strip() for line in f if line.strip()]
        else:
            logger.error(f"Batch file not found: {args.batch}")
            sys.exit(1)
    else:
        mode = InteractionMode.CLI

    # Create and run CLI
    cli = EnhancedCLI(mode)
    cli.run(args.commands if args.commands else None)


if __name__ == "__main__":
    main()
