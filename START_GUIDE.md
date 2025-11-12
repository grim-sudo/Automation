# 🚀 OmniAutomator Start Guide

Welcome to OmniAutomator! This comprehensive guide will help you get started with both CLI and GUI execution modes, from basic setup to advanced automation workflows.

---

## 📋 **Table of Contents**

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Initial Setup](#initial-setup)
4. [CLI Usage](#cli-usage)
5. [GUI Usage](#gui-usage)
6. [First Commands](#first-commands)
7. [Advanced Features](#advanced-features)
8. [Troubleshooting](#troubleshooting)
9. [Next Steps](#next-steps)

---

## 🔧 **Prerequisites**

### **System Requirements**
- **Operating System**: Windows 10+, Ubuntu 18.04+, or macOS 10.14+
- **Python**: Version 3.8 or higher
- **Memory**: At least 512 MB RAM available
- **Storage**: 100 MB free disk space
- **Network**: Internet connection (for AI features)

### **Check Your Python Version**
```bash
python --version
# Should show Python 3.8.0 or higher
```

If you don't have Python installed:
- **Windows**: Download from [python.org](https://python.org)
- **macOS**: Use Homebrew: `brew install python`
- **Linux**: Use package manager: `sudo apt install python3 python3-pip`

---

## 📦 **Installation**

### **Step 1: Download OmniAutomator**
```bash
# If you have the source code, navigate to the directory
cd path/to/OmniAutomator

# Or clone from repository (if available)
git clone https://github.com/your-repo/omni-automator.git
cd omni-automator
```

### **Step 2: Install Dependencies**
```bash
# Install all required packages
pip install -r requirements.txt

# On some systems, you might need to use pip3
pip3 install -r requirements.txt
```

### **Step 3: Verify Installation**
```bash
# Test basic functionality
python main.py --help

# Should show the help menu with available commands
```

---

## ⚙️ **Initial Setup**

### **1. AI Integration Setup (Recommended)**

To enable AI-enhanced features, you'll need an OpenRouter API key:

1. **Get an API Key**:
   - Visit [OpenRouter.ai](https://openrouter.ai)
   - Sign up for an account
   - Generate an API key

2. **Set Environment Variable**:
   ```bash
   # Windows (Command Prompt)
   set OPENROUTER_API_KEY=your_api_key_here
   
   # Windows (PowerShell)
   $env:OPENROUTER_API_KEY="your_api_key_here"
   
   # macOS/Linux
   export OPENROUTER_API_KEY=your_api_key_here
   ```

3. **Test AI Integration**:
   ```bash
   python -c "from omni_automator.ai.openrouter_integration import OpenRouterAutomationAI; print('AI Available:', OpenRouterAutomationAI().is_openrouter_available())"
   ```

### **2. Security Configuration**

For safe testing, enable sandbox mode:
```bash
# Enable sandbox mode for safe testing
set OMNI_SANDBOX_MODE=true
```

---

## 💻 **CLI Usage**

### **Basic CLI Commands**

#### **1. Execute Single Commands**
```bash
# Basic syntax
python main.py execute "your command here"

# Examples
python main.py execute "create folder 'TestFolder' on desktop"
python main.py execute "create file 'hello.txt' with content 'Hello World'"
python main.py execute "list files in current directory"
```

#### **2. Interactive Mode**
```bash
# Start interactive mode
python main.py interactive

# You'll see a prompt like this:
OmniAutomator> 

# Type commands directly:
OmniAutomator> create folder MyProject
OmniAutomator> create file README.md in MyProject
OmniAutomator> exit
```

#### **3. Batch Processing**
```bash
# Create a commands file
echo "create folder BatchTest" > commands.txt
echo "create file test1.txt in BatchTest" >> commands.txt
echo "create file test2.txt in BatchTest" >> commands.txt

# Execute batch file
python main.py batch commands.txt
```

#### **4. System Capabilities**
```bash
# Show all available capabilities
python main.py capabilities

# Shows categories like:
# - filesystem: create_folder, create_file, delete, copy, move, list
# - process: start, stop, list, get_info
# - gui: click, type, screenshot, wait
# - system: get_info, power_management
# - network: download, http_request
# - plugins: project_generator, web_automation
```

### **CLI Command Examples**

#### **File System Operations**
```bash
# Create directories
python main.py execute "create folder 'Projects/WebApp/src'"
python main.py execute "create folder 'Documents/Backup'"

# Create files with content
python main.py execute "create file 'app.py' with content 'print(\"Hello World\")'"
python main.py execute "create file 'README.md' with content '# My Project'"

# File management
python main.py execute "copy file 'source.txt' to 'backup.txt'"
python main.py execute "move file 'old.txt' to 'archive/old.txt'"
python main.py execute "delete file 'temp.txt'"
```

#### **Project Generation**
```bash
# Create programming projects
python main.py execute "create a C project named 'Calculator'"
python main.py execute "create a Python project named 'WebScraper'"
python main.py execute "create hello world program in C"
python main.py execute "create hello world program in Python"
```

#### **Process Management**
```bash
# Start applications
python main.py execute "start notepad"
python main.py execute "start calculator"

# Process information
python main.py execute "list running processes"
python main.py execute "get process info for notepad"
```

---

## 🖥️ **GUI Usage**

### **Starting the GUI**

#### **Method 1: Direct Launch**
```bash
# Launch GUI with AI support
python launch_gui.py
```

#### **Method 2: With Environment Setup**
```bash
# Set API key and launch
set OPENROUTER_API_KEY=your_key_here
python launch_gui.py
```

### **GUI Interface Overview**

When the GUI launches, you'll see:

1. **Left Sidebar**:
   - AI Status indicator
   - Quick Action buttons
   - Settings panel

2. **Main Area**:
   - Command input field
   - Output display area
   - Status bar

3. **Quick Actions**:
   - File Operations
   - System Info
   - Network Tools
   - Performance Monitor

### **Using the GUI**

#### **1. Basic Command Execution**
1. Type your command in the input field
2. Press Enter or click "Execute"
3. Watch the output in the display area
4. Check the status bar for progress

#### **2. Quick Actions**
- Click any quick action button
- Follow the prompts or dialogs
- Results appear in the output area

#### **3. AI Features**
- AI status shows in the sidebar
- AI suggestions appear automatically
- Enhanced command understanding

#### **4. Settings**
- Click the Settings button
- Configure API keys
- Adjust preferences
- Enable/disable features

### **GUI Command Examples**

Try these commands in the GUI:

```
create folder "GUITest" on desktop
create file "test.py" in GUITest with content "print('GUI Test')"
create a Python hello world program
get system information
list files in current directory
```

---

## 🎯 **First Commands**

### **Beginner Commands**

Start with these safe, simple commands:

```bash
# File operations
python main.py execute "create folder 'Learning' on desktop"
python main.py execute "create file 'notes.txt' in Learning"
python main.py execute "list files in Learning folder"

# System information
python main.py execute "get current directory"
python main.py execute "get system time"

# Simple projects
python main.py execute "create hello world program in Python"
python main.py execute "create hello world program in C"
```

### **Intermediate Commands**

Once comfortable, try these:

```bash
# Project creation
python main.py execute "create a Python project named 'MyFirstProject'"
python main.py execute "create a C project for simple calculator"

# File management
python main.py execute "copy all .txt files to backup folder"
python main.py execute "create folder structure: src, tests, docs"

# Process management
python main.py execute "start text editor"
python main.py execute "list all running applications"
```

### **Advanced Commands**

For experienced users:

```bash
# Complex workflows
python main.py execute "create a web scraping project with data analysis"
python main.py execute "setup development environment with git and python"
python main.py execute "create REST API project with database integration"

# System administration
python main.py execute "backup Documents folder to external drive"
python main.py execute "monitor system performance and generate report"
python main.py execute "cleanup temporary files and optimize system"
```

---

## 🚀 **Advanced Features**

### **1. AI-Enhanced Commands**

With AI enabled, you can use natural language:

```bash
# Natural language requests
python main.py execute "I need a complete web application for a blog"
python main.py execute "Help me set up a machine learning project"
python main.py execute "Create a system to monitor my computer's health"
```

### **2. Workflow Optimization**

AI automatically optimizes complex tasks:
- Parallel execution of independent operations
- Dependency resolution
- Error recovery and retry logic
- Resource optimization

### **3. Plugin System**

Extend functionality with plugins:

```bash
# Use project generator plugin
python main.py execute "generate React application with TypeScript"

# Use web automation plugin
python main.py execute "scrape news articles from website"
```

### **4. System Integration**

Install system-wide integration:

```bash
# Run as Administrator (Windows)
python install_system_integration.py

# Adds:
# - omni command globally
# - Right-click context menu
# - File associations
# - Start menu shortcuts
```

---

## 🔒 **Security Features**

### **Sandbox Mode**

For safe testing:

```bash
# Enable sandbox mode
set OMNI_SANDBOX_MODE=true
python main.py execute "delete important file"  # Will be blocked
```

### **Permission Levels**

Commands are classified by risk:
- **Safe**: File reading, system info
- **Moderate**: File creation, process start
- **High**: File deletion, system changes
- **Critical**: System shutdown, registry edits

### **Audit Logging**

All operations are logged:
- Command executed
- User and timestamp
- Results and errors
- Security checks

---

## 🚨 **Troubleshooting**

### **Common Issues**

#### **1. "Command not found" Error**
```bash
# Make sure you're in the right directory
cd path/to/OmniAutomator

# Check Python installation
python --version

# Try with python3
python3 main.py execute "test command"
```

#### **2. "Permission denied" Error**
```bash
# Run as Administrator (Windows)
# Right-click Command Prompt -> "Run as Administrator"

# Or enable sandbox mode
set OMNI_SANDBOX_MODE=true
```

#### **3. AI Features Not Working**
```bash
# Check API key
echo $OPENROUTER_API_KEY

# Test connection
python -c "from omni_automator.ai.openrouter_integration import OpenRouterAutomationAI; print(OpenRouterAutomationAI().is_openrouter_available())"

# Set API key if missing
set OPENROUTER_API_KEY=your_key_here
```

#### **4. GUI Won't Start**
```bash
# Install GUI dependencies
pip install customtkinter pillow

# Check for errors
python launch_gui.py

# Try without AI
unset OPENROUTER_API_KEY
python launch_gui.py
```

#### **5. Import Errors**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python path
python -c "import sys; print(sys.path)"
```

### **Debug Mode**

Enable detailed logging:

```bash
# Set debug level
set OMNI_LOG_LEVEL=DEBUG

# Run command with verbose output
python main.py execute "your command" --verbose
```

### **Getting Help**

```bash
# Show help
python main.py --help

# Show command help
python main.py execute --help

# Show capabilities
python main.py capabilities

# Interactive help
python main.py interactive
OmniAutomator> help
```

---

## 📈 **Next Steps**

### **1. Explore More Features**

- Try different command types
- Experiment with AI-enhanced commands
- Test the GUI interface
- Create custom workflows

### **2. System Integration**

```bash
# Install system integration (Windows)
python install_system_integration.py

# Use global commands
omni "create project"
omni-gui  # Launch GUI
```

### **3. Advanced Usage**

- Create custom plugins
- Set up automated workflows
- Integrate with other tools
- Use the Python API

### **4. Learn More**

- Read [ENHANCED_FEATURES.md](ENHANCED_FEATURES.md) for detailed features
- Check [SYSTEM_AUDIT_REPORT.md](SYSTEM_AUDIT_REPORT.md) for security info
- Explore the plugin system
- Join the community discussions

---

## 🎉 **Congratulations!**

You're now ready to use OmniAutomator! Start with simple commands and gradually explore more advanced features. The system is designed to be intuitive and powerful, whether you prefer CLI or GUI interaction.

### **Quick Reference**

```bash
# CLI Commands
python main.py execute "command"     # Single command
python main.py interactive          # Interactive mode
python main.py batch file.txt       # Batch processing
python main.py capabilities         # Show capabilities

# GUI
python launch_gui.py                 # Launch GUI

# System Integration
python install_system_integration.py # Install globally
```

### **Support**

If you need help:
1. Check this guide and documentation
2. Enable debug mode for detailed logs
3. Test with sandbox mode for safety
4. Report issues with detailed error messages

**Happy Automating! 🚀**
