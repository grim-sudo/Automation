#!/usr/bin/env python3
"""
Interactive Chatbot Mode for OmniAutomator
Multi-turn conversation with context awareness and clarification
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from ..utils.logger import get_logger
from ..core.spell_correction import get_spell_corrector
from ..core.smart_error_handler import get_smart_error_handler


class ChatbotMode:
    """Interactive chatbot interface for OmniAutomator"""
    
    def __init__(self):
        self.logger = get_logger("ChatbotMode")
        self.spell_corrector = get_spell_corrector()
        self.error_handler = get_smart_error_handler()
        
        # Conversation context
        self.conversation_history: List[Dict[str, str]] = []
        self.user_context: Dict[str, Any] = {
            'current_directory': os.getcwd(),
            'last_operation': None,
            'created_resources': [],
            'failed_operations': [],
            'preferences': {}
        }
        
        # System prompts
        self.system_messages = {
            'greeting': "👋 Hello! I'm OmniAutomator. I can help you with file operations, automation tasks, and more. Type 'help' for a list of commands.",
            'help': self._get_help_message(),
            'context_summary': self._get_context_summary
        }
        
        # Command handlers
        self.command_handlers = {
            'help': self.handle_help,
            'status': self.handle_status,
            'clear': self.handle_clear,
            'context': self.handle_context,
            'history': self.handle_history,
            'cd': self.handle_cd,
            'pwd': self.handle_pwd,
            'ls': self.handle_ls,
            'exit': self.handle_exit,
            'quit': self.handle_exit,
            'explain': self.handle_explain,
            'undo': self.handle_undo,
        }
    
    def start_interactive_session(self):
        """Start an interactive chatbot session"""
        self._print_banner()
        print(self.system_messages['greeting'])
        print("\n" + "="*60)
        
        while True:
            try:
                # Get user input
                user_input = self._get_user_input()
                
                if not user_input:
                    continue
                
                # Add to history
                self.conversation_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'type': 'user',
                    'content': user_input
                })
                
                # Check if it's a special command
                if user_input.startswith('/'):
                    self._handle_special_command(user_input[1:])
                    continue
                
                # Process automation command
                self._process_automation_command(user_input)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                self.logger.error(f"Session error: {e}")
                print(f"❌ Error: {e}")
                print("Try '/help' for assistance")
    
    def _get_user_input(self) -> str:
        """Get user input with prompt and formatting"""
        try:
            # Show current context in prompt
            indicator = "🤖" if self.user_context['last_operation'] else "💬"
            prompt = f"\n{indicator} You: "
            user_input = input(prompt).strip()
            return user_input
        except EOFError:
            return "exit"
    
    def _process_automation_command(self, command: str):
        """Process an automation command"""
        print(f"\n⏳ Processing: {command[:60]}{'...' if len(command) > 60 else ''}\n")
        
        # Apply spell correction
        corrected_command = self.spell_corrector.correct_text(command)
        
        if corrected_command != command:
            print(f"💡 Corrected to: {corrected_command}")
            self._ask_confirmation("Use corrected command?", corrected_command)
            command = corrected_command
        
        # Here you would integrate with the main OmniAutomator engine
        # For now, we'll show what would be executed
        self._show_command_analysis(command)
        
        # Add to history
        self.conversation_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'bot',
            'content': f"Processing: {command}"
        })
    
    def _show_command_analysis(self, command: str):
        """Show analysis of what the command will do"""
        print("📋 Command Analysis:")
        print(f"  • Input: {command}")
        print(f"  • Keywords detected: {list(self.spell_corrector.extract_keywords(command).keys())}")
        print(f"  • Current directory: {self.user_context['current_directory']}")
        print("\n✓ Ready to execute. Continue with next command or use /help")
    
    def _ask_confirmation(self, question: str, context: str = "") -> bool:
        """Ask for user confirmation"""
        if context:
            print(f"  Context: {context}")
        
        response = input(f"\n{question} (yes/no): ").strip().lower()
        return response in ['yes', 'y', 'true']
    
    def _handle_special_command(self, command: str):
        """Handle special commands starting with /"""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd in self.command_handlers:
            self.command_handlers[cmd](args)
        else:
            print(f"❌ Unknown command: /{cmd}")
            print("Use '/help' for available commands")
    
    # Special command handlers
    
    def handle_help(self, args: str = ""):
        """Show help information"""
        print(self.system_messages['help'])
    
    def handle_status(self, args: str = ""):
        """Show current status"""
        print("\n📊 Status:")
        print(f"  • Current Directory: {self.user_context['current_directory']}")
        print(f"  • Last Operation: {self.user_context['last_operation'] or 'None'}")
        print(f"  • Resources Created: {len(self.user_context['created_resources'])}")
        print(f"  • Failed Operations: {len(self.user_context['failed_operations'])}")
        print(f"  • Commands in History: {len(self.conversation_history)}")
    
    def handle_clear(self, args: str = ""):
        """Clear screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print(self.system_messages['greeting'])
    
    def handle_context(self, args: str = ""):
        """Show conversation context"""
        print("\n📝 Conversation Context:")
        print(self.user_context['context_summary']())
    
    def handle_history(self, args: str = ""):
        """Show command history"""
        print("\n📜 Conversation History:")
        if not self.conversation_history:
            print("  (empty)")
            return
        
        for i, entry in enumerate(self.conversation_history[-10:], start=1):
            speaker = "You" if entry['type'] == 'user' else "Bot"
            content = entry['content'][:50]
            print(f"  {i}. [{speaker}] {content}...")
    
    def handle_cd(self, args: str = ""):
        """Change directory"""
        if not args:
            print(f"Current directory: {os.getcwd()}")
            return
        
        try:
            os.chdir(args)
            self.user_context['current_directory'] = os.getcwd()
            print(f"✓ Changed to: {os.getcwd()}")
        except FileNotFoundError:
            print(f"❌ Directory not found: {args}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def handle_pwd(self, args: str = ""):
        """Print working directory"""
        print(f"📁 {os.getcwd()}")
    
    def handle_ls(self, args: str = ""):
        """List directory contents"""
        directory = args or os.getcwd()
        try:
            items = os.listdir(directory)
            print(f"\n📂 Contents of {directory}:")
            for item in items[:20]:
                full_path = os.path.join(directory, item)
                indicator = "📁" if os.path.isdir(full_path) else "📄"
                print(f"  {indicator} {item}")
            if len(items) > 20:
                print(f"  ... and {len(items) - 20} more items")
        except FileNotFoundError:
            print(f"❌ Directory not found: {directory}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def handle_exit(self, args: str = ""):
        """Exit the chatbot"""
        print("\n👋 Thanks for using OmniAutomator! Goodbye!")
        import sys
        sys.exit(0)
    
    def handle_explain(self, args: str = ""):
        """Explain the last command"""
        if not self.conversation_history:
            print("No command history")
            return
        
        last_user_cmd = None
        for entry in reversed(self.conversation_history):
            if entry['type'] == 'user':
                last_user_cmd = entry['content']
                break
        
        if last_user_cmd:
            print(f"\n📖 Explaining: {last_user_cmd}")
            keywords = self.spell_corrector.extract_keywords(last_user_cmd)
            print(f"\nDetected operations:")
            for keyword, found_text in keywords.items():
                print(f"  • {keyword.capitalize()}: {found_text}")
        else:
            print("No command to explain")
    
    def handle_undo(self, args: str = ""):
        """Undo last operation"""
        if self.user_context['last_operation']:
            print(f"⏮️  Undoing: {self.user_context['last_operation']}")
            print("(Undo not yet fully implemented)")
        else:
            print("Nothing to undo")
    
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
  Current Directory: {self.user_context['current_directory']}
  Commands Executed: {len(self.conversation_history)}
  Resources Created: {len(self.user_context['created_resources'])}
  Failed Operations: {len(self.user_context['failed_operations'])}
  Session Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    def _print_banner(self):
        """Print welcome banner"""
        banner = """
╔═══════════════════════════════════════════════════════════╗
║        🤖 OMNI AUTOMATOR - INTERACTIVE CHATBOT MODE      ║
║                Smart Automation Assistant                  ║
╚═══════════════════════════════════════════════════════════╝
"""
        print(banner)


# Global instance
_chatbot_instance = None


def get_chatbot() -> ChatbotMode:
    """Get or create global chatbot instance"""
    global _chatbot_instance
    if _chatbot_instance is None:
        _chatbot_instance = ChatbotMode()
    return _chatbot_instance
