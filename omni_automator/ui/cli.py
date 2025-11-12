"""
Command Line Interface for OmniAutomator
"""

import sys
import json
import click
from typing import Optional
from colorama import init, Fore, Style

from ..core.engine import OmniAutomator
from ..utils.logger import setup_logger

# Initialize colorama for Windows
init()

class CLIInterface:
    """Command Line Interface for OmniAutomator"""
    
    def __init__(self):
        self.automator = None
        self.logger = setup_logger("CLI")
    
    def start_interactive_mode(self):
        """Start interactive command mode"""
        print(f"{Fore.CYAN}🤖 OmniAutomator - Universal OS Automation{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Type 'help' for commands, 'quit' to exit{Style.RESET_ALL}")
        print()
        
        # Initialize automator
        self.automator = OmniAutomator()
        
        while True:
            try:
                # Get user input
                command = input(f"{Fore.YELLOW}omni> {Style.RESET_ALL}").strip()
                
                if not command:
                    continue
                
                # Handle special commands
                if command.lower() in ['quit', 'exit', 'q']:
                    break
                elif command.lower() == 'help':
                    self._show_help()
                elif command.lower() == 'capabilities':
                    self._show_capabilities()
                elif command.lower() == 'history':
                    self._show_history()
                elif command.lower() == 'permissions':
                    self._show_permissions()
                elif command.lower().startswith('sandbox'):
                    self._handle_sandbox_command(command)
                elif command.lower() == 'examples':
                    self._show_complex_examples()
                elif command.lower().startswith('analyze'):
                    self._analyze_command(command)
                elif command.lower() == 'ai-status':
                    self._show_ai_status()
                elif command.lower() == 'ai-suggestions':
                    self._show_ai_suggestions()
                elif command.lower().startswith('set-api-key'):
                    self._set_api_key(command)
                else:
                    # Execute automation command
                    self._execute_command(command)
                    
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Use 'quit' to exit{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        
        # Cleanup
        if self.automator:
            self.automator.shutdown()
        print(f"{Fore.GREEN}Goodbye!{Style.RESET_ALL}")
    
    def _execute_command(self, command: str):
        """Execute an automation command"""
        try:
            result = self.automator.execute(command)
            
            if result['success']:
                complexity = result.get('complexity', 'simple')
                
                if complexity == 'simple':
                    print(f"{Fore.GREEN}✓ Command executed successfully{Style.RESET_ALL}")
                    if result.get('result'):
                        self._print_result(result['result'])
                else:
                    # Complex workflow result
                    steps_completed = result.get('steps_completed', 0)
                    total_steps = result.get('total_steps', 0)
                    execution_time = result.get('execution_time', 0)
                    
                    print(f"{Fore.GREEN}✓ Complex workflow completed successfully{Style.RESET_ALL}")
                    print(f"  Complexity: {complexity.upper()}")
                    print(f"  Steps completed: {steps_completed}/{total_steps}")
                    print(f"  Execution time: {execution_time:.2f} seconds")
                    
                    # Show workflow summary if available
                    workflow_result = result.get('result', {})
                    if isinstance(workflow_result, dict) and 'execution_summary' in workflow_result:
                        summary = workflow_result['execution_summary']
                        success_rate = summary.get('success_rate', 0)
                        print(f"  Success rate: {success_rate:.1f}%")
            else:
                print(f"{Fore.RED}✗ Command failed: {result.get('error', 'Unknown error')}{Style.RESET_ALL}")
                
                # Show AI suggestions if available
                ai_suggestions = result.get('ai_suggestions', [])
                if ai_suggestions:
                    print(f"\n{Fore.CYAN}🤖 AI Suggestions:{Style.RESET_ALL}")
                    for i, suggestion in enumerate(ai_suggestions, 1):
                        print(f"  {i}. {suggestion}")
                
        except Exception as e:
            print(f"{Fore.RED}✗ Execution error: {e}{Style.RESET_ALL}")
    
    def _print_result(self, result):
        """Print command result in a formatted way"""
        if isinstance(result, (dict, list)):
            print(json.dumps(result, indent=2, default=str))
        else:
            print(str(result))
    
    def _show_help(self):
        """Show help information"""
        help_text = f"""
{Fore.CYAN}OmniAutomator Commands:{Style.RESET_ALL}

{Fore.YELLOW}File Operations:{Style.RESET_ALL}
  create folder 'name' [in 'location']  - Create a new folder
  create file 'name' [in 'location']    - Create a new file
  delete file/folder 'path'             - Delete file or folder
  copy 'source' to 'destination'        - Copy file or folder
  move 'source' to 'destination'        - Move file or folder

{Fore.YELLOW}Process Operations:{Style.RESET_ALL}
  open/start 'program' [with args]      - Start a program
  close/kill 'program'                  - Terminate a program
  list processes                        - List running processes

{Fore.YELLOW}GUI Operations:{Style.RESET_ALL}
  click on 'target' [at x,y]            - Click on element
  type 'text'                           - Type text
  press key 'key'                       - Press a key
  take screenshot [save as 'filename']  - Take screenshot
  wait X seconds                        - Wait for X seconds

{Fore.YELLOW}System Operations:{Style.RESET_ALL}
  get system info                       - Get system information
  set volume to X                       - Set system volume (0-100)
  shutdown/restart                      - Power operations

{Fore.YELLOW}Network Operations:{Style.RESET_ALL}
  download 'url' [as 'filename']        - Download file
  get 'url'                            - Make HTTP GET request

{Fore.YELLOW}Special Commands:{Style.RESET_ALL}
  help                                 - Show this help
  capabilities                         - Show available capabilities
  history                             - Show execution history
  permissions                         - Show permission status
  sandbox on/off                      - Enable/disable sandbox mode
  examples                            - Show complex command examples
  analyze <command>                   - Analyze command complexity
  ai-status                           - Show AI integration status
  ai-suggestions                      - Get AI-powered smart suggestions
  set-api-key <key>                   - Set Gemini API key for AI features
  quit/exit                           - Exit the program

{Fore.GREEN}Examples:{Style.RESET_ALL}
  create folder 'MyProject' on desktop
  open notepad
  type 'Hello, World!'
  take screenshot save as 'screen.png'
  download 'https://example.com/file.zip'
"""
        print(help_text)
    
    def _show_capabilities(self):
        """Show available capabilities"""
        if not self.automator:
            return
        
        capabilities = self.automator.get_capabilities()
        
        print(f"{Fore.CYAN}Available Capabilities:{Style.RESET_ALL}")
        for category, actions in capabilities.items():
            print(f"\n{Fore.YELLOW}{category.title()}:{Style.RESET_ALL}")
            for action in actions:
                print(f"  • {action}")
    
    def _show_history(self):
        """Show execution history"""
        if not self.automator:
            return
        
        history = self.automator.get_execution_history(10)
        
        if not history:
            print(f"{Fore.YELLOW}No execution history{Style.RESET_ALL}")
            return
        
        print(f"{Fore.CYAN}Recent Commands:{Style.RESET_ALL}")
        for i, record in enumerate(reversed(history), 1):
            status = "✓" if record.get('success', True) else "✗"
            color = Fore.GREEN if record.get('success', True) else Fore.RED
            print(f"{color}{i}. {status} {record['original_command']}{Style.RESET_ALL}")
    
    def _show_permissions(self):
        """Show permission status"""
        if not self.automator:
            return
        
        permissions = self.automator.permission_manager.get_permission_summary()
        
        print(f"{Fore.CYAN}Permission Status:{Style.RESET_ALL}")
        print(f"Sandbox Mode: {'ON' if permissions['sandbox_mode'] else 'OFF'}")
        print(f"\n{Fore.YELLOW}User Permissions:{Style.RESET_ALL}")
        
        for perm, allowed in permissions['user_permissions'].items():
            status = "✓" if allowed else "✗"
            color = Fore.GREEN if allowed else Fore.RED
            print(f"  {color}{status} {perm.replace('_', ' ').title()}{Style.RESET_ALL}")
        
        if permissions['blocked_operations']:
            print(f"\n{Fore.YELLOW}Blocked Operations:{Style.RESET_ALL}")
            for op in permissions['blocked_operations']:
                print(f"  {Fore.RED}✗ {op}{Style.RESET_ALL}")
    
    def _handle_sandbox_command(self, command: str):
        """Handle sandbox mode commands"""
        if not self.automator:
            return
        
        parts = command.lower().split()
        if len(parts) < 2:
            print(f"{Fore.YELLOW}Usage: sandbox on/off{Style.RESET_ALL}")
            return
        
        if parts[1] == 'on':
            self.automator.enable_sandbox_mode()
            print(f"{Fore.GREEN}Sandbox mode enabled{Style.RESET_ALL}")
        elif parts[1] == 'off':
            self.automator.disable_sandbox_mode()
            print(f"{Fore.YELLOW}Sandbox mode disabled{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}Usage: sandbox on/off{Style.RESET_ALL}")
    
    def _show_complex_examples(self):
        """Show examples of complex commands"""
        examples = f"""
{Fore.CYAN}🚀 Complex Command Examples:{Style.RESET_ALL}

{Fore.YELLOW}Development Workflows:{Style.RESET_ALL}
  create a python web scraping project called NewsBot and install requests and beautifulsoup
  setup development environment with git nodejs and vscode then clone my repo
  create a folder MyApp and in that folder create a c program file for addition of two numbers

{Fore.YELLOW}System Administration:{Style.RESET_ALL}
  backup my documents folder and download the latest python installer then take a screenshot
  create a project folder then copy all my python files to it and open in vscode
  install git and nodejs then create a new react project and start the dev server

{Fore.YELLOW}Data Processing:{Style.RESET_ALL}
  create a data analysis project with pandas and matplotlib then generate sample data
  download csv file from url then create python script to analyze it and save results
  backup database then create new analysis folder and copy relevant files

{Fore.YELLOW}Web Development:{Style.RESET_ALL}
  create html css and javascript files for a landing page then open in browser
  setup react project with typescript and tailwind then create component files
  clone repository then install dependencies and start development server

{Fore.GREEN}💡 Tips:{Style.RESET_ALL}
- Use natural language - the system understands context
- Chain multiple actions with "and", "then", "after"
- The system will break down complex commands into steps
- Use 'analyze <command>' to see how a command will be executed
- Complex workflows show progress and can run steps in parallel

{Fore.BLUE}Try typing:{Style.RESET_ALL} analyze create a python project and install requests
"""
        print(examples)
    
    def _analyze_command(self, command: str):
        """Analyze a command without executing it"""
        if not self.automator:
            return
        
        # Extract the actual command (remove 'analyze' prefix)
        parts = command.split(' ', 1)
        if len(parts) < 2:
            print(f"{Fore.YELLOW}Usage: analyze <command>{Style.RESET_ALL}")
            return
        
        target_command = parts[1]
        
        try:
            analysis = self.automator.analyze_command_complexity(target_command)
            
            print(f"{Fore.CYAN}📊 Command Analysis:{Style.RESET_ALL}")
            print(f"Command: {analysis['original_command']}")
            print(f"Complexity: {analysis['complexity'].upper()}")
            print(f"Estimated Steps: {analysis['estimated_steps']}")
            print(f"Estimated Duration: {analysis['estimated_duration']} seconds")
            
            if analysis['context']:
                print(f"\n{Fore.YELLOW}Detected Context:{Style.RESET_ALL}")
                for key, values in analysis['context'].items():
                    if values:
                        print(f"  {key.replace('_', ' ').title()}: {', '.join(values)}")
            
            if analysis['steps_preview']:
                print(f"\n{Fore.YELLOW}Execution Steps:{Style.RESET_ALL}")
                for i, step in enumerate(analysis['steps_preview'], 1):
                    print(f"  {i}. {step['action']} ({step['category']}) - Priority: {step['priority']}")
            
        except Exception as e:
            print(f"{Fore.RED}Analysis error: {e}{Style.RESET_ALL}")
    
    def _show_ai_status(self):
        """Show AI integration status"""
        if not self.automator:
            return
        
        status = self.automator.get_ai_status()
        
        print(f"{Fore.CYAN}🤖 AI Integration Status:{Style.RESET_ALL}")
        print(f"Available: {'✅ YES' if status['available'] else '❌ NO'}")
        print(f"Has API Key: {'✅ YES' if status['has_api_key'] else '❌ NO'}")
        print(f"Has Library: {'✅ YES' if status['has_library'] else '❌ NO'}")
        print(f"Model: {status.get('model', 'None')}")
        
        if not status['available']:
            print(f"\n{Fore.YELLOW}💡 To enable AI features:{Style.RESET_ALL}")
            if not status['has_library']:
                print("1. Install OpenAI: pip install openai")
            if not status['has_api_key']:
                print("2. Get API key from: https://openrouter.ai/keys")
                print("3. Set key: set-api-key YOUR_API_KEY")
                print("   Or set environment variable: OPENROUTER_API_KEY=your_key")
    
    def _show_ai_suggestions(self):
        """Show AI-powered smart suggestions"""
        if not self.automator:
            return
        
        print(f"{Fore.CYAN}🧠 AI Smart Suggestions:{Style.RESET_ALL}")
        
        try:
            suggestions = self.automator.get_ai_suggestions()
            
            if suggestions:
                for i, suggestion in enumerate(suggestions, 1):
                    print(f"{i}. {suggestion}")
            else:
                print("No suggestions available")
                
        except Exception as e:
            print(f"{Fore.RED}Error getting suggestions: {e}{Style.RESET_ALL}")
    
    def _set_api_key(self, command: str):
        """Set Gemini API key"""
        if not self.automator:
            return
        
        parts = command.split(' ', 1)
        if len(parts) < 2:
            print(f"{Fore.YELLOW}Usage: set-api-key YOUR_API_KEY{Style.RESET_ALL}")
            print(f"Get your API key from: https://makersuite.google.com/app/apikey")
            return
        
        api_key = parts[1].strip()
        
        try:
            success = self.automator.set_gemini_api_key(api_key)
            
            if success:
                print(f"{Fore.GREEN}✅ Gemini AI enabled successfully!{Style.RESET_ALL}")
                print(f"You can now use AI-enhanced features:")
                print(f"- Smarter command understanding")
                print(f"- AI-powered suggestions")
                print(f"- Intelligent error resolution")
            else:
                print(f"{Fore.RED}❌ Failed to enable Gemini AI{Style.RESET_ALL}")
                print(f"Please check your API key and internet connection")
                
        except Exception as e:
            print(f"{Fore.RED}Error setting API key: {e}{Style.RESET_ALL}")


@click.group()
def cli():
    """OmniAutomator - Universal OS Automation Framework"""
    pass


@cli.command()
def interactive():
    """Start interactive command mode"""
    interface = CLIInterface()
    interface.start_interactive_mode()


@cli.command()
@click.argument('command', required=True)
@click.option('--sandbox', is_flag=True, help='Run in sandbox mode')
@click.option('--output', type=click.Choice(['json', 'text']), default='text', help='Output format')
def execute(command: str, sandbox: bool, output: str):
    """Execute a single automation command"""
    try:
        # Initialize automator
        automator = OmniAutomator()
        
        if sandbox:
            automator.enable_sandbox_mode()
        
        # Check if it's a CLI command first
        if command.lower() == 'ai-status':
            # Handle ai-status command
            status = automator.get_ai_status()
            click.echo(f"🤖 AI Integration Status:")
            click.echo(f"Available: {'✅ YES' if status['available'] else '❌ NO'}")
            click.echo(f"Has API Key: {'✅ YES' if status['has_api_key'] else '❌ NO'}")
            click.echo(f"Has Library: {'✅ YES' if status['has_library'] else '❌ NO'}")
            click.echo(f"Model: {status.get('model', 'None')}")
            click.echo(f"Provider: {status.get('provider', 'Unknown')}")
            
            if not status['available']:
                click.echo(f"\n💡 To enable AI features:")
                if not status['has_library']:
                    click.echo("1. Install OpenAI: pip install openai")
                if not status['has_api_key']:
                    click.echo("2. Get API key from: https://openrouter.ai/keys")
                    click.echo("3. Set key: set-api-key YOUR_API_KEY")
                    click.echo("   Or set environment variable: OPENROUTER_API_KEY=your_key")
            
            result = {'success': True}
        elif command.lower() == 'ai-suggestions':
            # Handle ai-suggestions command
            suggestions = automator.get_ai_suggestions()
            click.echo(f"🧠 AI Smart Suggestions:")
            for i, suggestion in enumerate(suggestions, 1):
                click.echo(f"  {i}. {suggestion}")
            result = {'success': True}
        else:
            # Execute regular automation command
            result = automator.execute(command)
        
        # Output result
        if output == 'json':
            click.echo(json.dumps(result, indent=2, default=str))
        else:
            if result['success']:
                click.echo(f"✓ Command executed successfully")
                if result.get('result'):
                    click.echo(str(result['result']))
            else:
                click.echo(f"✗ Command failed: {result.get('error', 'Unknown error')}")
        
        # Cleanup
        automator.shutdown()
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def capabilities():
    """Show available automation capabilities"""
    try:
        automator = OmniAutomator()
        caps = automator.get_capabilities()
        
        click.echo("Available Capabilities:")
        for category, actions in caps.items():
            click.echo(f"\n{category.title()}:")
            for action in actions:
                click.echo(f"  • {action}")
        
        automator.shutdown()
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument('commands_file', type=click.File('r'))
@click.option('--sandbox', is_flag=True, help='Run in sandbox mode')
def batch(commands_file, sandbox: bool):
    """Execute commands from a file"""
    try:
        # Read commands
        commands = [line.strip() for line in commands_file if line.strip() and not line.startswith('#')]
        
        if not commands:
            click.echo("No commands found in file")
            return
        
        # Initialize automator
        automator = OmniAutomator()
        
        if sandbox:
            automator.enable_sandbox_mode()
        
        # Execute commands
        results = automator.batch_execute(commands)
        
        # Show results
        for i, result in enumerate(results):
            status = "✓" if result['success'] else "✗"
            click.echo(f"{status} Command {i+1}: {result['command']}")
            if not result['success']:
                click.echo(f"   Error: {result.get('error', 'Unknown error')}")
        
        # Cleanup
        automator.shutdown()
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


if __name__ == '__main__':
    cli()
