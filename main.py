#!/usr/bin/env python3
"""
OmniAutomator - Universal OS Automation Framework
Main entry point for the application
Supports flexible NLP, AI integration, and multiple interaction modes
"""

import sys
import os
import argparse
import io

# Fix encoding issues on Windows
if sys.platform == 'win32':
    # Use UTF-8 encoding for stdout/stderr
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from omni_automator.ui.enhanced_cli import EnhancedCLI, InteractionMode
from omni_automator.core.ai_model_manager import get_ai_manager, AIModelConfig
from omni_automator.core.ai_task_executor import get_ai_task_executor


def setup_default_ai_models():
    """Setup default AI models if not already configured"""
    ai_manager = get_ai_manager()
    models = ai_manager.list_registered_models()
    
    if not models:
        # Register default local model (no API key required)
        try:
            local_config = AIModelConfig(
                name="local_default",
                provider="local",
                model_id="ollama/llama2",
                is_default=True
            )
            ai_manager.register_model(local_config)
        except Exception as e:
            print(f"Note: Local AI model not available: {e}")


def main():
    """Main entry point with enhanced CLI"""
    parser = argparse.ArgumentParser(
        description="OmniAutomator - Intelligent Automation with Flexible NLP",
        epilog="""
Examples:
  python main.py --interactive              # Interactive mode
  python main.py --gui                      # GUI mode
  python main.py "create folder myapp"      # Single command
  python main.py "create folder" "deploy app"  # Multiple commands
  python main.py --batch commands.txt       # Batch mode
        """
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Run in interactive mode'
    )
    mode_group.add_argument(
        '-g', '--gui',
        action='store_true',
        help='Run in GUI mode'
    )
    mode_group.add_argument(
        '-b', '--batch',
        type=str,
        metavar='FILE',
        help='Run batch commands from file'
    )
    mode_group.add_argument(
        '--legacy',
        action='store_true',
        help='Use legacy CLI (backward compatibility)'
    )
    
    # AI options
    parser.add_argument(
        '-m', '--model',
        type=str,
        help='Specify AI model to use'
    )
    parser.add_argument(
        '--list-models',
        action='store_true',
        help='List available AI models'
    )
    
    # Commands
    parser.add_argument(
        'commands',
        nargs='*',
        help='Commands to execute'
    )
    
    args = parser.parse_args()
    
    # Setup default models
    setup_default_ai_models()
    
    # List models if requested
    if args.list_models:
        ai_manager = get_ai_manager()
        models = ai_manager.list_registered_models()
        
        print("Available AI Models:")
        for name, info in models.items():
            marker = "✓" if info['is_current'] else " "
            print(f"  [{marker}] {name} ({info['provider']})")
        
        if not models:
            print("  No models registered")
        
        return
    
    # Use legacy CLI if requested (now just uses enhanced CLI)
    if args.legacy:
        cli = EnhancedCLI(InteractionMode.INTERACTIVE)
        cli.run()
        return
    
    # Determine interaction mode
    if args.gui:
        mode = InteractionMode.GUI
    elif args.interactive:
        mode = InteractionMode.INTERACTIVE
    elif args.batch:
        mode = InteractionMode.BATCH
        # Load batch file
        if os.path.exists(args.batch):
            with open(args.batch, 'r') as f:
                args.commands = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        else:
            print(f"Error: Batch file not found: {args.batch}")
            sys.exit(1)
    else:
        mode = InteractionMode.CLI
    
    # Create enhanced CLI
    cli = EnhancedCLI(mode)
    
    # Switch AI model if specified
    if args.model:
        if not cli.engine.switch_ai_model(args.model):
            print(f"Warning: AI model '{args.model}' not found")
    
    # Run CLI
    if args.commands or mode != InteractionMode.CLI:
        cli.run(args.commands if args.commands else None)
    else:
        # Show help if no commands
        parser.print_help()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
