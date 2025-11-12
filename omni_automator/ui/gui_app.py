#!/usr/bin/env python3
"""
Modern GUI Interface for OmniAutomator
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import queue
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, List
import webbrowser

# Try to import customtkinter for modern look
try:
    import customtkinter as ctk
    HAS_CUSTOMTKINTER = True
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
except ImportError:
    HAS_CUSTOMTKINTER = False

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from omni_automator import OmniAutomator

class ModernOmniAutomatorGUI:
    """Modern GUI for OmniAutomator with advanced features"""
    
    def __init__(self):
        try:
            self.automator = None
            self.command_queue = queue.Queue()
            self.result_queue = queue.Queue()
            self.command_history = []
            self.is_running = False
            self.worker_thread = None
            
            # Initialize GUI with error handling
            try:
                if HAS_CUSTOMTKINTER:
                    self.root = ctk.CTk()
                    self.setup_modern_gui()
                else:
                    self.root = tk.Tk()
                    self.setup_classic_gui()
            except Exception as e:
                print(f"Failed to initialize GUI: {e}")
                raise
            
            # Set up window close handler
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            # Initialize automator
            self.init_automator()
            
            # Set running state
            self.is_running = True
            
            # Start background worker
            self.start_worker_thread()
            
            # Check for results periodically
            self.root.after(100, self.check_results)
            
        except Exception as e:
            print(f"Critical error during GUI initialization: {e}")
            raise
    
    def on_closing(self):
        """Handle window closing"""
        try:
            self.is_running = False
            
            # Stop worker thread
            if self.worker_thread and self.worker_thread.is_alive():
                self.command_queue.put(None)  # Signal worker to stop
                self.worker_thread.join(timeout=2.0)
            
            # Shutdown automator
            if self.automator:
                self.automator.shutdown()
            
            # Destroy window
            self.root.destroy()
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
            self.root.destroy()
    
    def setup_modern_gui(self):
        """Setup modern GUI with customtkinter"""
        self.root.title("OmniAutomator - Universal OS Automation")
        self.root.geometry("1200x800")
        
        # Configure grid
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Create sidebar
        self.sidebar = ctk.CTkFrame(self.root, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar.grid_rowconfigure(10, weight=1)
        
        # Sidebar title
        self.logo_label = ctk.CTkLabel(self.sidebar, text="OmniAutomator", 
                                      font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # AI Status
        self.ai_status_frame = ctk.CTkFrame(self.sidebar)
        self.ai_status_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        self.ai_status_label = ctk.CTkLabel(self.ai_status_frame, text="AI Status: Checking...", 
                                           font=ctk.CTkFont(size=12))
        self.ai_status_label.pack(pady=5)
        
        # Quick Actions
        self.quick_actions_label = ctk.CTkLabel(self.sidebar, text="Quick Actions", 
                                               font=ctk.CTkFont(size=16, weight="bold"))
        self.quick_actions_label.grid(row=2, column=0, padx=20, pady=(20, 10))
        
        # Quick action buttons
        actions = [
            ("File Operations", self.show_file_operations),
            ("System Settings", self.show_system_settings),
            ("Network Tools", self.show_network_tools),
            ("Performance", self.show_performance),
            ("AI Features", self.show_ai_features),
        ]
        
        for i, (text, command) in enumerate(actions):
            btn = ctk.CTkButton(self.sidebar, text=text, command=command, 
                               width=200, height=35)
            btn.grid(row=3+i, column=0, padx=20, pady=5)
        
        # Settings
        self.settings_btn = ctk.CTkButton(self.sidebar, text="Settings", 
                                         command=self.show_settings, width=200, height=35)
        self.settings_btn.grid(row=9, column=0, padx=20, pady=5)
        
        # Main content area
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Command input area
        self.input_frame = ctk.CTkFrame(self.main_frame)
        self.input_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        self.command_label = ctk.CTkLabel(self.input_frame, text="Enter Command:", 
                                         font=ctk.CTkFont(size=14, weight="bold"))
        self.command_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))
        
        self.command_entry = ctk.CTkEntry(self.input_frame, placeholder_text="Type your automation command here...", 
                                         height=40, font=ctk.CTkFont(size=12))
        self.command_entry.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.command_entry.bind("<Return>", self.execute_command)
        
        # Buttons
        self.button_frame = ctk.CTkFrame(self.input_frame)
        self.button_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        
        self.execute_btn = ctk.CTkButton(self.button_frame, text="🚀 Execute", 
                                        command=self.execute_command, height=35)
        self.execute_btn.pack(side="left", padx=5)
        
        self.ai_suggest_btn = ctk.CTkButton(self.button_frame, text="🧠 AI Suggestions", 
                                           command=self.get_ai_suggestions, height=35)
        self.ai_suggest_btn.pack(side="left", padx=5)
        
        self.clear_btn = ctk.CTkButton(self.button_frame, text="🗑️ Clear", 
                                      command=self.clear_output, height=35)
        self.clear_btn.pack(side="left", padx=5)
        
        # Output area
        self.output_frame = ctk.CTkFrame(self.main_frame)
        self.output_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.output_frame.grid_columnconfigure(0, weight=1)
        self.output_frame.grid_rowconfigure(1, weight=1)
        
        self.output_label = ctk.CTkLabel(self.output_frame, text="Output:", 
                                        font=ctk.CTkFont(size=14, weight="bold"))
        self.output_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))
        
        self.output_text = ctk.CTkTextbox(self.output_frame, font=ctk.CTkFont(family="Consolas", size=11))
        self.output_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # Status bar
        self.status_frame = ctk.CTkFrame(self.main_frame, height=30)
        self.status_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        self.status_label = ctk.CTkLabel(self.status_frame, text="Ready", 
                                        font=ctk.CTkFont(size=11))
        self.status_label.pack(side="left", padx=10, pady=5)
    
    def setup_classic_gui(self):
        """Setup classic GUI with tkinter"""
        self.root.title("OmniAutomator - Universal OS Automation")
        self.root.geometry("1200x800")
        self.root.configure(bg='#2b2b2b')
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#2b2b2b')
        style.configure('TLabel', background='#2b2b2b', foreground='white')
        style.configure('TButton', background='#404040', foreground='white')
        
        # Create main paned window
        self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel
        self.left_frame = ttk.Frame(self.paned, width=250)
        self.paned.add(self.left_frame, weight=0)
        
        # Title
        title_label = ttk.Label(self.left_frame, text="OmniAutomator", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=10)
        
        # Quick actions
        actions_label = ttk.Label(self.left_frame, text="Quick Actions", 
                                 font=('Arial', 12, 'bold'))
        actions_label.pack(pady=(20, 10))
        
        actions = [
            ("File Operations", self.show_file_operations),
            ("System Info", self.show_system_info),
            ("System Settings", self.show_system_settings),
            ("Network Tools", self.show_network_tools),
            ("Performance", self.show_performance),
            ("AI Features", self.show_ai_features),
        ]
        
        for text, command in actions:
            btn = ttk.Button(self.left_frame, text=text, command=command, width=25)
            btn.pack(pady=2, padx=10, fill=tk.X)
        
        # Right panel
        self.right_frame = ttk.Frame(self.paned)
        self.paned.add(self.right_frame, weight=1)
        
        # Command input
        input_frame = ttk.Frame(self.right_frame)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(input_frame, text="Enter Command:", font=('Arial', 12, 'bold')).pack(anchor=tk.W)
        
        self.command_entry = ttk.Entry(input_frame, font=('Arial', 11))
        self.command_entry.pack(fill=tk.X, pady=5)
        self.command_entry.bind("<Return>", self.execute_command)
        
        # Buttons
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="🚀 Execute", command=self.execute_command).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🧠 AI Suggestions", command=self.get_ai_suggestions).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ Clear", command=self.clear_output).pack(side=tk.LEFT, padx=5)
        
        # Output area
        output_frame = ttk.Frame(self.right_frame)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(output_frame, text="Output:", font=('Arial', 12, 'bold')).pack(anchor=tk.W)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, font=('Consolas', 10), 
                                                    bg='#1e1e1e', fg='white', insertbackground='white')
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.right_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def init_automator(self):
        """Initialize the OmniAutomator"""
        try:
            # Get API key from environment or config
            api_key = os.getenv('OPENROUTER_API_KEY')
            config = {'openrouter_api_key': api_key} if api_key else {}
            
            self.automator = OmniAutomator(config)
            self.log_output("✅ OmniAutomator initialized successfully")
            
            # Check AI status
            ai_status = self.automator.get_ai_status()
            if ai_status.get('available'):
                self.log_output(f"AI Available: {ai_status.get('provider')} - {ai_status.get('model')}")
                if hasattr(self, 'ai_status_label'):
                    self.ai_status_label.configure(text="AI Status: ✅ Available")
            else:
                self.log_output("⚠️ AI not available - set OPENROUTER_API_KEY for AI features")
                if hasattr(self, 'ai_status_label'):
                    self.ai_status_label.configure(text="AI Status: ❌ Not Available")
            
        except Exception as e:
            self.log_output(f"❌ Failed to initialize OmniAutomator: {e}")
    
    def start_worker_thread(self):
        """Start background worker thread"""
        self.worker_thread = threading.Thread(target=self.worker, daemon=True)
        self.worker_thread.start()
    
    def worker(self):
        """Background worker for executing commands"""
        while self.is_running:
            try:
                # Use timeout to allow periodic checking of is_running
                try:
                    command = self.command_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                if command is None:
                    break
                
                # Validate command
                if not isinstance(command, str) or not command.strip():
                    self.result_queue.put(("error", "Invalid command"))
                    continue
                
                self.result_queue.put(("status", "Executing command..."))
                
                if self.automator:
                    try:
                        result = self.automator.execute(command.strip())
                        self.result_queue.put(("result", result))
                    except Exception as exec_error:
                        self.result_queue.put(("error", f"Execution failed: {exec_error}"))
                else:
                    self.result_queue.put(("error", "Automator not initialized"))
                
            except Exception as e:
                self.result_queue.put(("error", f"Worker error: {e}"))
    
    def check_results(self):
        """Check for results from worker thread"""
        try:
            while True:
                msg_type, data = self.result_queue.get_nowait()
                
                if msg_type == "status":
                    self.update_status(data)
                elif msg_type == "result":
                    self.handle_result(data)
                elif msg_type == "error":
                    self.handle_error(data)
                    
        except queue.Empty:
            pass
        
        self.root.after(100, self.check_results)
    
    def execute_command(self, event=None):
        """Execute the entered command"""
        command = self.command_entry.get().strip()
        if not command:
            return
        
        # Add to history
        self.command_history.append(command)
        
        # Log command
        self.log_output(f"\n🚀 Executing: {command}")
        
        # Clear entry
        self.command_entry.delete(0, tk.END)
        
        # Queue command for execution
        self.command_queue.put(command)
        
        # Update status
        self.update_status("Executing...")
    
    def handle_result(self, result):
        """Handle execution result"""
        if result.get('success'):
            self.log_output("✅ Command executed successfully")
            
            if result.get('result'):
                self.log_output(f"📋 Result: {result['result']}")
            
            if result.get('complexity'):
                self.log_output(f"🔧 Complexity: {result['complexity'].upper()}")
            
            if result.get('steps_completed'):
                self.log_output(f"📊 Steps: {result['steps_completed']}/{result.get('total_steps', 0)}")
                
            # Show workflow results if available
            if result.get('results'):
                self.log_output("📋 Workflow Results:")
                for i, step_result in enumerate(result['results'], 1):
                    status = "✅" if step_result.get('success') else "❌"
                    action = step_result.get('step_action', 'Unknown')
                    self.log_output(f"   {i}. {status} {action}")
        else:
            error_msg = result.get('error', 'Unknown error')
            self.log_output(f"❌ Command failed: {error_msg}")
            
            # Show more detailed error information
            if 'Plugin' in error_msg and 'not found' in error_msg:
                self.log_output("💡 This might be a filesystem operation. Trying fallback...")
                
            # Show workflow results even on failure
            if result.get('results'):
                self.log_output("📋 Step Results:")
                for i, step_result in enumerate(result['results'], 1):
                    status = "✅" if step_result.get('success') else "❌"
                    action = step_result.get('step_action', 'Unknown')
                    error = step_result.get('error', '')
                    self.log_output(f"   {i}. {status} {action}")
                    if error and not step_result.get('success'):
                        self.log_output(f"      Error: {error}")
            
            # Show AI suggestions if available
            ai_suggestions = result.get('ai_suggestions', [])
            if ai_suggestions:
                self.log_output("AI Suggestions:")
                for i, suggestion in enumerate(ai_suggestions, 1):
                    self.log_output(f"   {i}. {suggestion}")
        
        self.update_status("Ready")
    
    def handle_error(self, error):
        """Handle execution error"""
        self.log_output(f"❌ Error: {error}")
        self.update_status("Error")
    
    def get_ai_suggestions(self):
        """Get AI suggestions"""
        if not self.automator:
            self.log_output("❌ Automator not initialized")
            return
        
        try:
            suggestions = self.automator.get_ai_suggestions()
            self.log_output("\n🧠 AI Suggestions:")
            for i, suggestion in enumerate(suggestions, 1):
                self.log_output(f"   {i}. {suggestion}")
        except Exception as e:
            self.log_output(f"❌ Failed to get AI suggestions: {e}")
    
    def log_output(self, message):
        """Log message to output area"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        if HAS_CUSTOMTKINTER:
            self.output_text.insert(tk.END, formatted_message)
            self.output_text.see(tk.END)
        else:
            self.output_text.insert(tk.END, formatted_message)
            self.output_text.see(tk.END)
    
    def update_status(self, status):
        """Update status bar"""
        if HAS_CUSTOMTKINTER:
            self.status_label.configure(text=status)
        else:
            self.status_var.set(status)
    
    def clear_output(self):
        """Clear output area"""
        if HAS_CUSTOMTKINTER:
            self.output_text.delete("1.0", tk.END)
        else:
            self.output_text.delete("1.0", tk.END)
    
    # Quick Action Methods
    def show_file_operations(self):
        """Show file operations dialog"""
        self.show_quick_commands([
            "create folder 'MyFolder'",
            "copy file 'source.txt' to 'destination.txt'",
            "delete file 'unwanted.txt'",
            "list directory contents",
            "take screenshot save as 'screenshot.png'"
        ])
    
    def show_system_info(self):
        """Show system info commands"""
        self.show_quick_commands([
            "get system info",
            "get system performance",
            "get installed software",
            "get running processes",
            "get disk usage"
        ])
    
    def show_system_settings(self):
        """Show system settings commands"""
        self.show_quick_commands([
            "manage service 'Spooler' start",
            "create system restore point",
            "manage firewall enable",
            "set environment variable 'TEST' to 'value'",
            "manage startup program add 'MyApp' 'C:\\path\\to\\app.exe'"
        ])
    
    def show_network_tools(self):
        """Show network tools commands"""
        self.show_quick_commands([
            "ping google.com",
            "get network interfaces",
            "set DNS to '8.8.8.8'",
            "enable DHCP on Ethernet",
            "download file 'https://example.com/file.zip'"
        ])
    
    def show_performance(self):
        """Show performance monitoring"""
        if self.automator:
            self.command_queue.put("get system performance")
    
    def show_ai_features(self):
        """Show AI features dialog"""
        self.show_quick_commands([
            "ai-status",
            "ai-suggestions",
            "create a machine learning project with tensorflow",
            "setup development environment with git and nodejs",
            "analyze command: 'create web scraping system'"
        ])
    
    def show_quick_commands(self, commands):
        """Show quick commands dialog"""
        dialog = QuickCommandDialog(self.root, commands, self.execute_quick_command)
    
    def execute_quick_command(self, command):
        """Execute a quick command"""
        self.command_entry.delete(0, tk.END)
        self.command_entry.insert(0, command)
        self.execute_command()
    
    def show_settings(self):
        """Show settings dialog"""
        SettingsDialog(self.root, self.automator)
    
    def run(self):
        """Run the GUI application"""
        self.root.mainloop()
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'automator') and self.automator:
            self.automator.shutdown()

class QuickCommandDialog:
    """Dialog for quick command selection"""
    
    def __init__(self, parent, commands, callback):
        self.callback = callback
        
        if HAS_CUSTOMTKINTER:
            self.dialog = ctk.CTkToplevel(parent)
            self.dialog.title("Quick Commands")
            self.dialog.geometry("500x400")
            
            # Command list
            self.listbox = tk.Listbox(self.dialog, font=('Arial', 11))
            self.listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            for command in commands:
                self.listbox.insert(tk.END, command)
            
            # Buttons
            btn_frame = ctk.CTkFrame(self.dialog)
            btn_frame.pack(fill=tk.X, padx=20, pady=10)
            
            ctk.CTkButton(btn_frame, text="Execute", command=self.execute_selected).pack(side=tk.LEFT, padx=5)
            ctk.CTkButton(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)
        else:
            self.dialog = tk.Toplevel(parent)
            self.dialog.title("Quick Commands")
            self.dialog.geometry("500x400")
            
            # Command list
            self.listbox = tk.Listbox(self.dialog, font=('Arial', 11))
            self.listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            for command in commands:
                self.listbox.insert(tk.END, command)
            
            # Buttons
            btn_frame = ttk.Frame(self.dialog)
            btn_frame.pack(fill=tk.X, padx=20, pady=10)
            
            ttk.Button(btn_frame, text="Execute", command=self.execute_selected).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        self.listbox.bind("<Double-Button-1>", lambda e: self.execute_selected())
    
    def execute_selected(self):
        """Execute selected command"""
        selection = self.listbox.curselection()
        if selection:
            command = self.listbox.get(selection[0])
            self.callback(command)
            self.dialog.destroy()

class SettingsDialog:
    """Settings dialog"""
    
    def __init__(self, parent, automator):
        self.automator = automator
        
        if HAS_CUSTOMTKINTER:
            self.dialog = ctk.CTkToplevel(parent)
            self.dialog.title("Settings")
            self.dialog.geometry("600x500")
            
            # API Key setting
            api_frame = ctk.CTkFrame(self.dialog)
            api_frame.pack(fill=tk.X, padx=20, pady=20)
            
            ctk.CTkLabel(api_frame, text="OpenRouter API Key:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor=tk.W, padx=10, pady=5)
            
            self.api_entry = ctk.CTkEntry(api_frame, placeholder_text="Enter your OpenRouter API key...", width=400)
            self.api_entry.pack(fill=tk.X, padx=10, pady=5)
            
            current_key = os.getenv('OPENROUTER_API_KEY', '')
            if current_key:
                self.api_entry.insert(0, current_key[:20] + "..." if len(current_key) > 20 else current_key)
            
            ctk.CTkButton(api_frame, text="Save API Key", command=self.save_api_key).pack(pady=10)
            
            # Other settings
            settings_frame = ctk.CTkFrame(self.dialog)
            settings_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            ctk.CTkLabel(settings_frame, text="Application Settings", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor=tk.W, padx=10, pady=5)
            
            self.sandbox_var = ctk.BooleanVar()
            ctk.CTkCheckBox(settings_frame, text="Enable Sandbox Mode", variable=self.sandbox_var).pack(anchor=tk.W, padx=10, pady=5)
            
            self.auto_suggestions_var = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(settings_frame, text="Auto AI Suggestions", variable=self.auto_suggestions_var).pack(anchor=tk.W, padx=10, pady=5)
        else:
            self.dialog = tk.Toplevel(parent)
            self.dialog.title("Settings")
            self.dialog.geometry("600x500")
            
            # API Key setting
            api_frame = ttk.LabelFrame(self.dialog, text="API Configuration")
            api_frame.pack(fill=tk.X, padx=20, pady=20)
            
            ttk.Label(api_frame, text="OpenRouter API Key:").pack(anchor=tk.W, padx=10, pady=5)
            
            self.api_entry = ttk.Entry(api_frame, width=50)
            self.api_entry.pack(fill=tk.X, padx=10, pady=5)
            
            current_key = os.getenv('OPENROUTER_API_KEY', '')
            if current_key:
                self.api_entry.insert(0, current_key[:20] + "..." if len(current_key) > 20 else current_key)
            
            ttk.Button(api_frame, text="Save API Key", command=self.save_api_key).pack(pady=10)
    
    def save_api_key(self):
        """Save API key"""
        api_key = self.api_entry.get().strip()
        if api_key:
            os.environ['OPENROUTER_API_KEY'] = api_key
            messagebox.showinfo("Success", "API key saved! Restart the application to apply changes.")
        else:
            messagebox.showwarning("Warning", "Please enter a valid API key.")

def main():
    """Main function"""
    try:
        app = ModernOmniAutomatorGUI()
        app.run()
    except Exception as e:
        print(f"Failed to start GUI: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
