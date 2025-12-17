#!/usr/bin/env python3
"""
Interactive Chatbot Launcher for OmniAutomator
Starts the smart interactive session with spell correction and error recovery
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from omni_automator.ui.chatbot_mode import get_chatbot


def main():
    """Start interactive chatbot mode"""
    try:
        chatbot = get_chatbot()
        chatbot.start_interactive_session()
    except KeyboardInterrupt:
        print("\n\n👋 Session ended by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
