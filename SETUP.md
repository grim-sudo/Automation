# OmniAutomator - Setup & Installation Guide

## System Requirements

### Minimum
- Python 3.8 or higher
- 512 MB available RAM
- 100 MB disk space
- Windows 10+, Ubuntu 18.04+, or macOS 10.14+

### Recommended
- Python 3.11 or higher
- 4 GB available RAM
- 2 GB disk space
- OpenRouter API key (free tier available at openrouter.ai)
- Administrator or root privileges for system operations

---

## Installation

### Step 1: Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd omni-automator

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# (Optional) Install GUI dependencies
pip install customtkinter pillow
```

### Step 3: Configure AI

Get your free API key from [openrouter.ai](https://openrouter.ai) and set the environment variable.

**Windows (PowerShell or Command Prompt):**

```powershell
# Option 1: PowerShell (Current session only)
$env:OPENROUTER_API_KEY="your_openrouter_api_key_here"

# Option 2: Set permanently (requires admin, new terminal window needed)
setx OPENROUTER_API_KEY "your_openrouter_api_key_here"
```

**Windows (Command Prompt):**

```cmd
setx OPENROUTER_API_KEY "your_openrouter_api_key_here"
```

⚠️ **Important:** After using `setx`, close and reopen your terminal for changes to take effect.

**Linux/macOS:**

```bash
# Current session only
export OPENROUTER_API_KEY="your_openrouter_api_key_here"

# Permanent (add to ~/.bashrc, ~/.zshrc, or ~/.bash_profile)
echo 'export OPENROUTER_API_KEY="your_openrouter_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

---

## Quick Start

### Verify Installation

```bash
# Test basic functionality
python main.py "create folder test_automation"

# If successful, you should see the folder created
```

### First Command

```bash
# Simple example - create a folder
python main.py "create folder my_project"

# Project generation - create with multiple files
python main.py "create a python project"

# DevOps example - setup infrastructure
python main.py "setup docker container"
```

---

## Running Modes

### 1. Command-Line Interface (CLI)

Execute single commands directly from the terminal.

```bash
# Simple command
python main.py "create folder backup"

# Complex command
python main.py "setup postgres database with user management"

# Use specific AI model
python main.py --model gpt-4 "your command"
```

**Best for:** Scripting, automation, single commands

### 2. Interactive Mode

Full interactive mode with AI assistance and command suggestions.

```bash
# Start interactive mode
python main.py -i
# or
python main.py --interactive

# Available commands in interactive mode:
create folder test          # Execute automation
setup database              # DevOps automation
switch gpt-4                # Switch AI model
models                      # List available models
help                        # Show help
exit                        # Quit
```

**Best for:** Exploration, learning, testing multiple commands

### 3. Graphical User Interface (GUI)

Beautiful, modern interface for visual task management.

```bash
# Launch GUI
python main.py --gui
# or
python launch_gui.py
```

**Best for:** Visual users, demonstrations, non-technical users

### 4. Batch Processing

Execute multiple commands from a configuration file.

```bash
# Create commands.txt with one command per line:
# create folder project1
# create folder project2
# setup docker container

# Execute batch
python main.py --batch commands.txt
```

**Best for:** Bulk operations, automation workflows

---

## Command Examples

### File & Folder Operations

```bash
# Create directories
python main.py "create folder my_project"

# Copy files
python main.py "copy all pdf files to archive folder"

# Delete files
python main.py "delete temporary files older than 30 days"
```

### Development Projects

```bash
# Python project
python main.py "create a python project with flask and postgresql"

# JavaScript/Node.js
python main.py "create nodejs express api server"

# React/Frontend
python main.py "setup react application with typescript"
```

### DevOps & Infrastructure

```bash
# Docker
python main.py "create docker container for nodejs"

# Kubernetes
python main.py "setup kubernetes deployment with monitoring"

# CI/CD
python main.py "setup github actions ci/cd pipeline"
```

### Database Operations

```bash
# PostgreSQL
python main.py "create postgres database with backup"

# Data Migration
python main.py "migrate mysql data to mongodb"
```

---

## AI Model Selection

### Available Models

The system supports multiple AI providers through OpenRouter:
- **OpenAI**: GPT-4, GPT-4o Mini
- **Anthropic**: Claude 3.5 Sonnet
- **Google**: Gemini 2.0 Flash
- **Mistral**: DevStral 2512
- **DeepSeek**: R1T2 Chimera
- **Local**: Ollama (llama2, and other local models)

### Switch Models

```bash
# List all available models
python main.py --list-models

# Use specific model for single command
python main.py --model gpt-4 "your command"

# In interactive mode, switch at runtime:
python main.py -i
> switch gpt-4           # Switch to GPT-4
> models                 # List all models
> your command           # Execute with active model
```

---

## Configuration

### Environment Variables

Essential configuration variables:

```bash
# AI Provider
OPENROUTER_API_KEY         # Required for OpenRouter models

# Optional customization
OMNI_LOG_LEVEL            # DEBUG, INFO, WARNING, ERROR
OMNI_WORK_DIR             # Working directory for operations
```

### Configuration File (Optional)

Create `~/.omnimator/config.json` for persistent configuration:

```json
{
  "ai_model": "mistralai/devstral-2512:free",
  "log_level": "INFO",
  "auto_switch_on_error": true,
  "timeout": 30,
  "max_retries": 3
}
```

---

## Troubleshooting

### Issue: Python not found

```bash
# Verify Python installation
python --version

# On Linux/macOS, try:
python3 --version

# Add to PATH if necessary
```

### Issue: Dependencies missing

```bash
# Reinstall with cleanup
pip install -r requirements.txt --force-reinstall --no-cache-dir
```

### Issue: GUI not launching

```bash
# Install GUI dependencies explicitly
pip install customtkinter pillow --force-reinstall

# Try launching again
python main.py --gui
```

### Issue: AI not responding

```bash
# Verify API key is configured
# Windows:
echo %OPENROUTER_API_KEY%
# Linux/macOS:
echo $OPENROUTER_API_KEY

# Set if missing
setx OPENROUTER_API_KEY "your_key_here"

# Verify connection with simple command
python main.py "hello"
```

### Issue: Permission denied (macOS/Linux)

```bash
# Give execute permissions
chmod +x main.py
chmod +x launch_gui.py

# Try again with python prefix
python main.py "your command"
```

### Issue: Module not found

```bash
# Ensure you're in correct directory
cd /path/to/omni-automator

# Check venv is activated
# Windows: Look for (venv) in prompt
# Linux/macOS: Look for (venv) in prompt

# Reinstall dependencies
pip install -r requirements.txt
```

### Debugging

Enable debug output:

```bash
# Windows
set OMNI_LOG_LEVEL=DEBUG
python main.py "your command"

# Linux/macOS
export OMNI_LOG_LEVEL=DEBUG
python main.py "your command"
```

---

## Usage Patterns

### Simple Automation

```bash
# One-time task
python main.py "create folder backup && copy important files"
```

### Scheduled Automation

```bash
# Windows Task Scheduler
# Create task to run: python main.py "backup database"

# Linux/macOS Cron
# Add to crontab:
# 0 2 * * * cd /path/to/omni-automator && python main.py "backup database"
```

### Scripting with Python

```python
from omni_automator.ui.enhanced_cli import EnhancedCLI
from omni_automator.ui.enhanced_cli import InteractionMode

# Initialize CLI
cli = EnhancedCLI(InteractionMode.CLI)

# Execute commands
result = cli.engine.execute_command("create folder test")
print(f"Status: {result['step'].status}")
print(f"Action: {result['parsed'].action}")
```

---

## Performance Tips

1. **Reuse CLI Instance**: In scripts, create CLI once and reuse
2. **Batch Operations**: Group related commands together
3. **Model Selection**: Use faster models for simple tasks
4. **Caching**: Results are cached locally when possible

---

## Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **Permissions**: Run with minimal required privileges
3. **Audit Logging**: All operations are logged
4. **Sandboxing**: Use interactive mode to review before execution

---

## Support & Help

### Getting Help

```bash
# Show help
python main.py --help

# In interactive mode:
python main.py -i
> help
```

### Common Questions

**Q: Can I use without API key?**
A: Yes, with limited functionality using local Ollama model

**Q: Can I use in Docker?**
A: Yes, install Docker image (in development)

**Q: Can I integrate with CI/CD?**
A: Yes, use batch mode or programmatic API

**Q: What about data privacy?**
A: Commands are processed, results may go to AI model

---

## Next Steps

1. **Start with Interactive Mode**: `python main.py -i`
2. **Try GUI**: `python main.py --gui`
3. **Read Examples**: Check command examples above
4. **Explore Models**: Try different AI models
5. **Create Workflows**: Build automation workflows

---

## Resources

- **GitHub**: <repository-url>
- **Documentation**: See README.md
- **API Key**: openrouter.ai (free tier)
- **Issues**: Report on GitHub

---

**Ready to automate? Start with:** `python main.py -i`
