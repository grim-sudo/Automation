# Archon — User Guide

Archon is a natural-language automation framework. You describe what you want in plain English; the framework maps your intent to the right action and runs it.

---

## Table of Contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Running a single command](#running-a-single-command)
4. [Interactive chatbot mode](#interactive-chatbot-mode)
5. [Batch execution](#batch-execution)
6. [n8n workflow management](#n8n-workflow-management)
7. [Custom Linux distro builder](#custom-linux-distro-builder)
8. [Global flags](#global-flags)
9. [Logging](#logging)
10. [Environment variables reference](#environment-variables-reference)
11. [Configuration file reference](#configuration-file-reference)
12. [Tips and examples](#tips-and-examples)

---

## Installation

**Requirements:** Python 3.10+ and a virtual environment.

```bash
# Clone the repository
git clone <repo-url> && cd Automation

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # Linux / macOS
# venv\Scripts\activate           # Windows

# Install with all development dependencies
pip install -e ".[dev]"

# Or install only what you need:
pip install -e ".[n8n]"           # includes n8n bridge
pip install -e ".[distro]"        # includes distro builder (Linux only)
pip install -e ".[gui]"           # desktop automation deps (screen/input control)
```

**Verify:**

```bash
archon --version
# 1.0.0
```

---

## Configuration

Archon reads settings from multiple sources in this priority order (highest wins):

```
CLI flag → environment variable → .env file → ~/.archon/config.toml → built-in default
```

### Quick start: `.env` file

Create `.env` in the project root:

```dotenv
# AI provider (at least one key required for AI-enhanced features)
OPENROUTER_API_KEY=sk-or-...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Leave OPENROUTER_MODEL blank — Archon auto-selects the best free model
# OPENROUTER_MODEL=

# n8n integration (optional)
N8N_URL=http://localhost:5678
N8N_API_KEY=your-n8n-api-key
```

### Config file

On first run, an example config is written to `~/.archon/config.example.toml`. Copy it:

```bash
cp ~/.archon/config.example.toml ~/.archon/config.toml
```

Then edit `~/.archon/config.toml` to set your keys and preferences.

### Nested environment variables

Any config field can be overridden with an environment variable using `__` as a delimiter:

```bash
export OMNI__AI__MAX_TOKENS=16000
export OMNI__AI__TIMEOUT=60
export OMNI__N8N__URL=http://my-n8n:5678
export OMNI__DEBUG=true
```

---

## Running a single command

```bash
archon run "COMMAND"
```

**Examples:**

```bash
# File system
archon run "create a folder named reports in ~/Documents"
archon run "create 5 folders named test1 through test5 on the Desktop"
archon run "delete all .tmp files in /home/user/Downloads"

# Screenshots / UI
archon run "take a screenshot and save to ~/screenshots/now.png"

# System info
archon run "show running processes sorted by CPU"
archon run "check disk usage on /"

# Web / network
archon run "download https://example.com/file.zip to ~/Downloads"

# Development
archon run "create a Python project called my-api in ~/Projects"
archon run "deploy the app"
archon run "run the test suite"
```

**Flags:**

```bash
archon run "delete all logs" --safe-mode   # asks for confirmation first
archon run "build project" --debug          # verbose output
archon run "summarise this" -m openai/gpt-4o  # force a specific model
```

---

## Interactive chatbot mode

Starts a REPL where you type commands one at a time:

```bash
archon chatbot
```

- Type any natural language command and press Enter.
- Type `exit` or `quit` to leave.
- The chatbot maintains context across turns in the same session.

---

## Batch execution

Run multiple commands from a text file — one command per line.

**Create a batch file** (`tasks.txt`):

```
# Comments start with #
# Blank lines are ignored

create a folder named reports in ~/Documents
create a folder named archive in ~/Documents
take a screenshot and save it to ~/screenshots/start.png
show disk usage on /home
```

**Run it:**

```bash
archon batch tasks.txt
```

**Options:**

```bash
archon batch tasks.txt --stop-on-error     # halt on first failure
archon batch tasks.txt --safe-mode         # confirm destructive steps
archon batch tasks.txt --debug             # verbose output per step
```

---

## n8n workflow management

The n8n bridge talks to a running [n8n](https://n8n.io) instance via its REST API v1.

**Prerequisites:**

1. n8n running (e.g. `docker run -p 5678:5678 n8nio/n8n`)
2. An n8n API key created at `http://localhost:5678/settings/api`
3. Set in `.env`:
   ```dotenv
   N8N_URL=http://localhost:5678
   N8N_API_KEY=your-key-here
   ```

### List workflows

```bash
archon n8n list
```

### Create a workflow from natural language

```bash
archon n8n create "send a Slack message every morning at 9am"
archon n8n create "watch a folder for new CSV files and email them to me"
```

Archon uses the AI layer to generate the workflow JSON, then posts it to n8n. You can activate it manually from the n8n UI or via the API.

### Trigger (run) a workflow

```bash
archon n8n run <WORKFLOW_ID>
```

### Check workflow status

```bash
archon n8n status <WORKFLOW_ID>
```

---

## Custom Linux distro builder

Builds a bootable Linux ISO from scratch. Requires root and Linux build tools (`debootstrap` or `pacstrap`, `xorriso`, `syslinux`).

**List available profiles:**

```bash
archon distro profiles
```

**Estimate build time and disk usage (dry run):**

```bash
archon distro estimate --profile minimal
archon distro estimate --profile desktop
```

**Build an ISO:**

```bash
sudo archon distro build --profile minimal --output ~/isos/
sudo archon distro build --profile desktop --name "MyDistro" --output ~/isos/
```

Build stages (all async, progress reported to the console):
1. Validate environment
2. Fetch kernel sources
3. Configure kernel
4. Compile kernel
5. Build root filesystem (debootstrap / pacstrap)
6. Install packages
7. Configure system
8. Set up bootloader
9. Assemble ISO with xorriso
10. Verify and checksum

The finished ISO is written to the configured `output_dir` (default `./distro_output`).

> **Note:** Builds require several GB of free disk space and can take 20–60 minutes depending on hardware and package selection.

---

## Global flags

These flags apply to all commands:

| Flag | Env var | Description |
|------|---------|-------------|
| `--debug` | `OMNI_DEBUG=true` | Enable verbose debug logging to the console |
| `--log-file PATH` | `OMNI_LOG_FILE=/path/to/file.jsonl` | Write structured JSON logs to a file |
| `--safe-mode` | `OMNI_SAFE_MODE=true` | Require explicit confirmation before any destructive operation |
| `--version` / `-V` | — | Print version and exit |

**Examples:**

```bash
# Debug a failing command
archon --debug run "my command"

# Always log to a file
archon --log-file ~/archon.jsonl run "my command"

# Set via environment so you don't have to type it every time
export OMNI_SAFE_MODE=true
archon run "delete old logs"   # will ask for confirmation
```

---

## Logging

Archon uses [loguru](https://github.com/Delgan/loguru) for structured logging.

| Mode | Output |
|------|--------|
| Default | INFO-level to the console |
| `--debug` | DEBUG-level to the console (very verbose) |
| `--log-file path` | Structured JSON to the specified file (`INFO` and above) |
| Both `--debug` and `--log-file` | DEBUG to console **and** JSON to file |

**Reading JSON logs:**

```bash
# Tail-follow a running session
tail -f ~/archon.jsonl | python -m json.tool

# Filter only errors
grep '"level":"ERROR"' ~/archon.jsonl | python -m json.tool
```

---

## Environment variables reference

| Variable | Section | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | `ai` | OpenRouter API key |
| `OPENROUTER_MODEL` | `ai` | Force a model (leave blank for auto-selection) |
| `OPENAI_API_KEY` | `ai` | OpenAI direct API key |
| `ANTHROPIC_API_KEY` | `ai` | Anthropic direct API key |
| `MAX_RETRIES` | `ai` | Retry attempts on transient AI failures |
| `N8N_API_KEY` | `n8n` | n8n REST API key |
| `N8N_URL` | `n8n` | Base URL of the n8n instance |
| `OMNI_DEBUG` | global | `true` to enable debug logging |
| `OMNI_SAFE_MODE` | global | `true` to enable safe mode |
| `OMNI_LOG_FILE` | global | Path to write JSON logs |

Nested config can be overridden with double-underscore notation:

```bash
export OMNI__AI__MAX_TOKENS=32000
export OMNI__AI__TIMEOUT=120
export OMNI__N8N__POLLING_INTERVAL_SECONDS=10
export OMNI__DISTRO_BUILDER__OUTPUT_DIR=/mnt/builds
```

---

## Configuration file reference

`~/.archon/config.toml`:

```toml
# Global
debug = false
# log_file = "/var/log/archon.jsonl"
safe_mode = false
continue_on_error = false   # keep going in batch mode even when a step fails

[ai]
openrouter_api_key = ""
openai_api_key = ""
anthropic_api_key = ""
# model = ""              # leave blank → auto-select best free model
# fallback_chain = []     # leave blank → auto-select
max_tokens = 8000
timeout = 30              # seconds per AI request
max_retries = 3
retry_delay = 2.0         # base delay for exponential back-off

[n8n]
url = "http://localhost:5678"
api_key = ""
default_error_webhook = ""        # POST errors here (leave blank to disable)
polling_interval_seconds = 5

[distro_builder]
work_dir = "/tmp/omni_distro_build"
output_dir = "./distro_output"
default_jobs = 0                  # 0 = auto-detect from nproc
debian_mirror = "http://deb.debian.org/debian"
debian_suite = "bookworm"
kernel_cache_dir = "~/.archon/kernel_cache"
require_root_confirmation = true
```

---

## Tips and examples

### Model selection

Archon automatically selects the best free model from OpenRouter at startup. You do **not** need to set a model name. If you want to pin a model:

```bash
archon run "my command" -m openai/gpt-4o
```

Or in `.env` (not recommended — overrides auto-selection):

```dotenv
# OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
```

### Safe mode for destructive workflows

```bash
# Confirm every destructive step interactively
archon --safe-mode batch cleanup_tasks.txt
```

### Running without an AI key (offline / local mode)

Some simple intents (file operations, folder creation) are handled directly by the NLP engine without calling any AI API. Only complex or ambiguous commands require an API key.

### Shell completion

```bash
archon --install-completion    # installs completion for your shell
# restart your shell, then:
archon r<TAB>    # completes to 'run'
```

### Programmatic Python API

```python
from archon.config import get_settings
from archon.core.engine import Archon

settings = get_settings()
engine = Archon(settings)

result = engine.execute("create a folder named reports in /tmp")
print(result)

engine.shutdown()
```

### n8n workflow lifecycle example

```bash
# 1. List existing workflows
archon n8n list

# 2. Create a new one from natural language
archon n8n create "every hour, check if /var/log/app.log is over 100MB and email me"

# 3. Activate it in the n8n UI (or via the n8n REST API directly)

# 4. Check its last execution status
archon n8n status <id>

# 5. Trigger it manually
archon n8n run <id>
```

### Batch file for a morning routine

```
# morning_routine.txt
take a screenshot and save to ~/screenshots/morning.png
show disk usage on /
show running processes sorted by memory
list all files modified in the last 24 hours in ~/Projects
```

```bash
archon batch morning_routine.txt --log-file ~/morning.jsonl
```
