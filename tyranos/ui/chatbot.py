#!/usr/bin/env python3
"""
Interactive Chatbot Mode for Tyranos
Multi-turn conversation with context awareness and clarification
"""

import os
from datetime import datetime
from typing import Any

from loguru import logger

from ..nlp.spell_corrector import get_spell_corrector
from ..utils.logger import get_logger
from ..workflow.error_handler import get_smart_error_handler


class ChatbotMode:
    """Interactive chatbot interface for Tyranos"""

    def __init__(self):
        self.logger = get_logger("ChatbotMode")
        self.spell_corrector = get_spell_corrector()
        self.error_handler = get_smart_error_handler()

        # Conversation context
        self.conversation_history: list[dict[str, str]] = []
        self.user_context: dict[str, Any] = {
            "current_directory": os.getcwd(),
            "last_operation": None,
            "created_resources": [],
            "failed_operations": [],
            "preferences": {},
        }

        # System prompts
        self.system_messages = {
            "greeting": "👋 Hello! I'm Tyranos. I can help you with file operations, automation tasks, and more. Type 'help' for a list of commands.",
            "help": self._get_help_message(),
            "context_summary": self._get_context_summary,
        }

        # Command handlers
        self.command_handlers = {
            "help": self.handle_help,
            "status": self.handle_status,
            "clear": self.handle_clear,
            "context": self.handle_context,
            "history": self.handle_history,
            "cd": self.handle_cd,
            "pwd": self.handle_pwd,
            "ls": self.handle_ls,
            "exit": self.handle_exit,
            "quit": self.handle_exit,
            "explain": self.handle_explain,
            "undo": self.handle_undo,
        }

    def start_interactive_session(self):
        """Start an interactive chatbot session"""
        self._print_banner()
        logger.info(self.system_messages["greeting"])
        logger.info("=" * 60)

        while True:
            try:
                # Get user input
                user_input = self._get_user_input()

                if not user_input:
                    continue

                # Add to history
                self.conversation_history.append(
                    {"timestamp": datetime.now().isoformat(), "type": "user", "content": user_input}
                )

                # Check if it's a special command
                if user_input.startswith("/"):
                    self._handle_special_command(user_input[1:])
                    continue

                # Process automation command
                self._process_automation_command(user_input)

            except KeyboardInterrupt:
                logger.info("Goodbye!")
                break
            except Exception as e:
                self.logger.error(f"Session error: {e}")
                logger.error(f"Error: {e}")
                logger.info("Try '/help' for assistance")

    def _get_user_input(self) -> str:
        """Get user input with prompt and formatting"""
        try:
            # Show current context in prompt
            indicator = "🤖" if self.user_context["last_operation"] else "💬"
            prompt = f"\n{indicator} You: "
            user_input = input(prompt).strip()
            return user_input
        except EOFError:
            return "exit"

    def _process_automation_command(self, command: str):
        """Process an automation command"""
        logger.info(f"Processing: {command[:60]}{'...' if len(command) > 60 else ''}")

        # Apply spell correction
        corrected_command = self.spell_corrector.correct_text(command)

        if corrected_command != command:
            logger.info(f"Corrected to: {corrected_command}")
            self._ask_confirmation("Use corrected command?", corrected_command)
            command = corrected_command

        # Here you would integrate with the main Tyranos engine
        # For now, we'll show what would be executed
        self._show_command_analysis(command)

        # Add to history
        self.conversation_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "type": "bot",
                "content": f"Processing: {command}",
            }
        )

    def _show_command_analysis(self, command: str):
        """Show analysis of what the command will do"""
        logger.info("Command Analysis:")
        logger.info(f"Input: {command}")
        logger.info(
            f"Keywords detected: {list(self.spell_corrector.extract_keywords(command).keys())}"
        )
        logger.info(f"Current directory: {self.user_context['current_directory']}")
        logger.info("Ready to execute. Continue with next command or use /help")

    def _ask_confirmation(self, question: str, context: str = "") -> bool:
        """Ask for user confirmation"""
        if context:
            logger.info(f"Context: {context}")

        response = input(f"\n{question} (yes/no): ").strip().lower()
        return response in ["yes", "y", "true"]

    def _handle_special_command(self, command: str):
        """Handle special commands starting with /"""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd in self.command_handlers:
            self.command_handlers[cmd](args)
        else:
            logger.error(f"Unknown command: /{cmd}")
            logger.info("Use '/help' for available commands")

    # Special command handlers

    def handle_help(self, args: str = ""):
        """Show help information"""
        logger.info(self.system_messages["help"])

    def handle_status(self, args: str = ""):
        """Show current status"""
        logger.info("Status:")
        logger.info(f"Current Directory: {self.user_context['current_directory']}")
        logger.info(f"Last Operation: {self.user_context['last_operation'] or 'None'}")
        logger.info(f"Resources Created: {len(self.user_context['created_resources'])}")
        logger.info(f"Failed Operations: {len(self.user_context['failed_operations'])}")
        logger.info(f"Commands in History: {len(self.conversation_history)}")

    def handle_clear(self, args: str = ""):
        """Clear screen"""
        os.system("cls" if os.name == "nt" else "clear")
        logger.info(self.system_messages["greeting"])

    def handle_context(self, args: str = ""):
        """Show conversation context"""
        logger.info("Conversation Context:")
        logger.info(self.user_context["context_summary"]())

    def handle_history(self, args: str = ""):
        """Show command history"""
        logger.info("Conversation History:")
        if not self.conversation_history:
            logger.info("(empty)")
            return

        for i, entry in enumerate(self.conversation_history[-10:], start=1):
            speaker = "You" if entry["type"] == "user" else "Bot"
            content = entry["content"][:50]
            logger.info(f"{i}. [{speaker}] {content}...")

    def handle_cd(self, args: str = ""):
        """Change directory"""
        if not args:
            logger.info(f"Current directory: {os.getcwd()}")
            return

        try:
            os.chdir(args)
            self.user_context["current_directory"] = os.getcwd()
            logger.info(f"Changed to: {os.getcwd()}")
        except FileNotFoundError:
            logger.error(f"Directory not found: {args}")
        except Exception as e:
            logger.error(f"Error: {e}")

    def handle_pwd(self, args: str = ""):
        """Print working directory"""
        logger.info(f"{os.getcwd()}")

    def handle_ls(self, args: str = ""):
        """List directory contents"""
        directory = args or os.getcwd()
        try:
            items = os.listdir(directory)
            logger.info(f"Contents of {directory}:")
            for item in items[:20]:
                full_path = os.path.join(directory, item)
                item_type = "DIR" if os.path.isdir(full_path) else "FILE"
                logger.info(f"  [{item_type}] {item}")
            if len(items) > 20:
                logger.info(f"  ... and {len(items) - 20} more items")
        except FileNotFoundError:
            logger.error(f"Directory not found: {directory}")
        except Exception as e:
            logger.error(f"Error: {e}")

    def handle_exit(self, args: str = ""):
        """Exit the chatbot"""
        logger.info("Thanks for using Tyranos! Goodbye!")
        import sys

        sys.exit(0)

    def handle_explain(self, args: str = ""):
        """Explain the last command"""
        if not self.conversation_history:
            logger.info("No command history")
            return

        last_user_cmd = None
        for entry in reversed(self.conversation_history):
            if entry["type"] == "user":
                last_user_cmd = entry["content"]
                break

        if last_user_cmd:
            logger.info(f"Explaining: {last_user_cmd}")
            keywords = self.spell_corrector.extract_keywords(last_user_cmd)
            logger.info("Detected operations:")
            for keyword, found_text in keywords.items():
                logger.info(f"  {keyword.capitalize()}: {found_text}")
        else:
            logger.info("No command to explain")

    def handle_undo(self, args: str = ""):
        """Undo last operation"""
        if self.user_context["last_operation"]:
            logger.info(f"Undoing: {self.user_context['last_operation']}")
            logger.info("(Undo not yet fully implemented)")
        else:
            logger.info("Nothing to undo")

    def _get_help_message(self) -> str:
        """Get help message"""
        return """
🆘 HELP - Available Commands

AUTOMATION COMMANDS (type naturally):
  "create a folder named test"
  "delete the test folder"
  "copy file1.txt to backup/"

SPECIAL COMMANDS (start with /):
  /help          - Show this help message
  /status        - Show current status
  /history       - Show recent commands
  /context       - Show conversation context
  /cd <path>     - Change directory
  /pwd           - Print working directory
  /ls [path]     - List directory contents
  /explain       - Explain last command
  /undo          - Undo last operation
  /exit, /quit   - Exit the program

FEATURES:
  ✓ Grammar-tolerant (typos like "fodler" → "folder")
  ✓ Smart error recovery with suggestions
  ✓ Path validation with auto-creation
  ✓ Multi-turn conversation with context
  ✓ Command clarification and confirmation

TIPS:
  • Use natural language (e.g., "make a new project")
  • Spell-check is automatic
  • Ask for clarification if unsure
  • Type 'help' anytime for assistance
"""

    def _get_context_summary(self) -> str:
        """Get context summary"""
        return f"""
  Current Directory: {self.user_context["current_directory"]}
  Commands Executed: {len(self.conversation_history)}
  Resources Created: {len(self.user_context["created_resources"])}
  Failed Operations: {len(self.user_context["failed_operations"])}
  Session Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

    def _print_banner(self):
        """Print welcome banner"""
        banner = """
╔═══════════════════════════════════════════════════════════╗
║            TYRANOS - INTERACTIVE CHATBOT MODE            ║
║                Smart Automation Assistant                  ║
╚═══════════════════════════════════════════════════════════╝
"""
        logger.info(banner)


# Global instance
_chatbot_instance = None


def get_chatbot() -> ChatbotMode:
    """Get or create global chatbot instance"""
    global _chatbot_instance
    if _chatbot_instance is None:
        _chatbot_instance = ChatbotMode()
    return _chatbot_instance
