# OmniAutomator — Setup & Installation Guide

## System Requirements

### Minimum
- Python 3.10 or higher
- 512 MB available RAM
- 200 MB disk space
- Windows 10+, Ubuntu 20.04+, or macOS 12+

### Recommended
- Python 3.12
- 4 GB available RAM
- 2 GB disk space (much more for distro builds)
- OpenRouter API key — free tier at [openrouter.ai](https://openrouter.ai)
- Administrator or root privileges for system operations

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/grim-sudo/Automation.git
cd Automation
```

---

## Step 2 — Create a Virtual Environment

Using a virtual environment is strongly recommended to keep dependencies isolated.

```bash
# Create the venv
python -m venv .venv

# Activate it
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows (PowerShell)
.venv\Scripts\activate.bat       # Windows (CMD)
```

You should see `(.venv)` at the start of your prompt once activated.

---

## Step 3 — Install Dependencies

```bash
# Core package only
pip install -e .

# Core + development tools (tests, linting, type checking)
pip install -e ".[dev]"

# Add optional feature groups as needed:
pip install -e ".[dev,n8n]"             # + n8n workflow bridge
pip install -e ".[dev,distro]"          # + Linux distro builder
pip install -e ".[dev,gui]"             # + graphical interface
pip install -e ".[dev,n8n,distro,gui]"  # everything
```

### What each group adds

| Group | Extra packages |
|---|---|
| `dev` | pytest, ruff, mypy, pytest-asyncio, respx |
| `n8n` | aiohttp (webhook listener) |
| `distro` | kconfiglib (kernel config) |
| `gui` | customtkinter, pyautogui, pynput, pillow |
| `web` | selenium, playwright, webdriver-manager |
| `data` | numpy, pandas, matplotlib, seaborn |

---

## Step 4 — Configure Your API Key

OmniAutomator uses [OpenRouter](https://openrouter.ai) to resolve and call free AI models at runtime. An API key is required.

### Option A — Environment Variable (Recommended)

```bash
# Linux / macOS — current session only
export OPENROUTER_API_KEY="sk-or-v1-..."

# Linux / macOS — permanent (pick whichever shell you use)
echo 'export OPENROUTER_API_KEY="sk-or-v1-..."' >> ~/.bashrc
echo 'export OPENROUTER_API_KEY="sk-or-v1-..."' >> ~/.zshrc
source ~/.bashrc   # reload

# Windows — PowerShell (current session)
$env:OPENROUTER_API_KEY="sk-or-v1-..."

# Windows — permanent
setx OPENROUTER_API_KEY "sk-or-v1-..."
# ⚠ Close and reopen your terminal after setx for the change to take effect.
```

### Option B — `.env` File

Create a `.env` file in the project root:

```
OPENROUTER_API_KEY=sk-or-v1-...
```

The framework reads `.env` automatically on startup.

### Option C — Config File

```bash
# Generate an example config file
python -c "from omni_automator.config import generate_example_config; generate_example_config()"
```

This writes `~/.omniautomator/config.example.toml`. Copy it to `~/.omniautomator/config.toml` and add your key:

```toml
[ai]
openrouter_api_key = "sk-or-v1-..."
```

---

## Step 5 — Verify the Installation

```bash
# Show CLI help
omni --help

# Run a simple test command
omni run "create folder omni_test"

# Check that the folder was created
ls omni_test    # Linux/macOS
dir omni_test   # Windows
```

If you see the folder, the installation is working correctly.

---

## Running Modes

### `omni run` — Single Command

Execute one natural-language command and exit.

```bash
omni run "create a python project with tests"
omni run "copy all pdf files to archive"
omni run "setup docker container for nodejs"
```

Flags:
```bash
omni --debug run "your command"           # verbose logging
omni --safe-mode run "delete files"       # confirm before destructive ops
omni --log-file /tmp/omni.jsonl run "…"   # write structured JSON log
```

### `omni chatbot` — Interactive Conversation

Multi-turn conversational interface with streaming responses and command history.

```bash
omni chatbot

# Special commands inside chatbot:
/help       — show available commands
/status     — show current model and connection status
/history    — show command history
/context    — show active conversation context
/cd <path>  — change working directory
/pwd        — print working directory
/ls         — list files
/clear      — clear conversation context
exit        — quit
```

### `omni gui` — Graphical Interface

```bash
# Requires [gui] extras
pip install -e ".[gui]"
omni gui
```

### `omni batch` — Bulk Execution

Create a plain-text file with one command per line:

```
create folder project1
create folder project2
setup docker container
install package nginx
```

Then execute:

```bash
omni batch commands.txt
omni --continue-on-error batch commands.txt   # don't stop on failures
```

---

## n8n Workflow Integration

Requires a running [n8n](https://n8n.io) instance and the `[n8n]` extra.

```bash
pip install -e ".[n8n]"
```

Set connection details in your config or via env vars:

```bash
export OMNI__N8N__URL="http://localhost:5678"
export OMNI__N8N__API_KEY="your_n8n_api_key"
```

### CLI Commands

```bash
# List all workflows
omni n8n list

# Run a workflow by ID
omni n8n run <workflow-id>

# Create a workflow from a natural-language description
omni n8n create "when a file appears in S3, post a message to Slack"

# Check execution status
omni n8n status <workflow-id> <execution-id>
```

---

## Custom Linux Distro Builder

Requires Linux, root access, and the `[distro]` extra plus host tools.

```bash
# Install Python extra
pip install -e ".[distro]"

# Install host tools (Debian/Ubuntu)
sudo apt-get install debootstrap xorriso syslinux-common

# Install host tools (Arch)
sudo pacman -S arch-install-scripts xorriso syslinux
```

### Using Built-in Profiles

```bash
# List available profiles
omni distro profiles

# Build from a profile
sudo omni distro build --profile debian_base --output ./dist

# Estimate build time before committing
omni distro estimate debian_base
```

### Build from Natural Language

```bash
sudo omni distro build --nl "minimal debian iso with nginx, headless, no GUI"
sudo omni distro build --nl "arch linux with KDE desktop and gaming packages"
sudo omni distro build --nl "tiny buildroot image for embedded systems"
```

### Custom Profiles

Create a TOML profile in `~/.omniautomator/profiles/` or copy from `omni_automator/distro_builder/profiles/`:

```toml
[meta]
name = "my-server"
base = "debian"  # debian | arch | unix (buildroot)

[kernel]
version = "latest-stable"
patches = []

[kernel.kconfig]
CONFIG_KVM = "y"
CONFIG_MODULES = "y"

[packages]
base     = ["base-files", "systemd", "openssh-server", "nginx"]
optional = ["curl", "git", "htop"]

[build]
hostname = "my-server"
locale   = "en_US.UTF-8"
timezone = "UTC"
desktop  = ""
```

---

## Configuration Reference

Priority order (highest wins):

1. CLI flags
2. `OMNI__SECTION__FIELD` env vars (e.g. `OMNI__AI__TIMEOUT=60`)
3. Legacy flat env vars (`OPENROUTER_API_KEY`, `MAX_RETRIES`)
4. `~/.omniautomator/config.toml`
5. Built-in defaults

### Full Config Reference

```toml
# ── Global ───────────────────────────────────────────────────────────────────
debug              = false   # verbose debug logging
safe_mode          = false   # confirm before destructive operations
continue_on_error  = false   # don't abort batch on first failure
log_file           = ""      # write JSON logs here (e.g. /var/log/omni.jsonl)

# ── AI ───────────────────────────────────────────────────────────────────────
[ai]
openrouter_api_key = ""   # required — or set OPENROUTER_API_KEY
openai_api_key     = ""   # optional direct OpenAI access
anthropic_api_key  = ""   # optional direct Anthropic access

# Model selection: leave blank to resolve automatically from free-model list
model          = ""
fallback_chain = []

max_tokens  = 8000    # sliding-window context token budget
timeout     = 30      # per-request timeout (seconds)
max_retries = 3       # retries per model before advancing the fallback chain
retry_delay = 2.0     # base delay between retries (seconds, exponential backoff)

# ── n8n ──────────────────────────────────────────────────────────────────────
[n8n]
url                      = "http://localhost:5678"
api_key                  = ""
default_error_webhook    = ""
polling_interval_seconds = 5

# ── Distro Builder ───────────────────────────────────────────────────────────
[distro_builder]
work_dir                  = "/tmp/omni_distro_build"
output_dir                = "./distro_output"
default_jobs              = 0        # 0 = auto-detect from cpu_count
debian_mirror             = "http://deb.debian.org/debian"
debian_suite              = "bookworm"
kernel_cache_dir          = "~/.omniautomator/kernel_cache"
require_root_confirmation = true
```

### Environment Variable Examples

```bash
# Nested setting (use __ as delimiter)
export OMNI__AI__MAX_TOKENS=16000
export OMNI__AI__TIMEOUT=60
export OMNI__N8N__URL="http://n8n.example.com"
export OMNI__DEBUG=true

# Legacy flat vars (no prefix needed)
export OPENROUTER_API_KEY="sk-or-v1-..."
export MAX_RETRIES=5
```

---

## Running the Test Suite

```bash
# All tests
pytest tests/ -v

# Fast (unit tests only, skip slow/integration)
pytest tests/ -m "not slow and not integration"

# With coverage report
pytest tests/ --cov=omni_automator --cov-report=term-missing

# Specific test file
pytest tests/test_response_parser.py -v
```

---

## Development Workflow

```bash
# Lint
ruff check omni_automator/ omni.py tests/

# Auto-fix lint issues
ruff check --fix omni_automator/ omni.py tests/

# Format
ruff format omni_automator/ omni.py tests/

# Type check
mypy omni_automator/ omni.py --ignore-missing-imports

# Run CI checks locally (lint + typecheck + tests)
ruff check omni_automator/ omni.py tests/ && \
mypy omni_automator/ omni.py --ignore-missing-imports && \
pytest tests/ -v
```

---

## Troubleshooting

### `omni: command not found`

The `omni` command is installed when you run `pip install -e .`. Make sure your virtual environment is activated:

```bash
source .venv/bin/activate   # Linux/macOS
which omni                  # should print a path inside .venv/
```

If using the system Python on Arch Linux (PEP 668 restriction):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

### AI not responding

```bash
# Verify the key is set
echo $OPENROUTER_API_KEY

# Run with debug logging to see the HTTP traffic
omni --debug run "hello"
```

### Dependencies missing after install

```bash
pip install -e . --force-reinstall --no-cache-dir
```

### GUI not launching

```bash
pip install -e ".[gui]"
omni gui
```

If `pyautogui` throws errors on headless Linux, set `DISPLAY` or use a virtual framebuffer.

### Permission denied (distro builder)

`debootstrap` and `pacstrap` require root. Run the distro commands with `sudo`:

```bash
sudo omni distro build --profile debian_base --output ./dist
```

### Module import errors

```bash
# Ensure you are in the project root with the venv active
cd /path/to/Automation
source .venv/bin/activate
pip install -e .
```

### Enabling Debug Logging

```bash
# Print debug logs to terminal
omni --debug run "your command"

# Write structured JSON logs to a file
omni --log-file /tmp/omni.jsonl run "your command"
cat /tmp/omni.jsonl | python -m json.tool   # pretty-print
```

---

## Security Notes

- **Never commit your API key** to version control; use env vars or `~/.omniautomator/config.toml`
- Use `--safe-mode` to require confirmation before destructive operations
- The distro builder requires root — review profiles before running
- All subprocess calls use `safe_run()` (no `shell=True`); path inputs are validated for traversal attempts

---

## Next Steps

1. Run `omni chatbot` to explore capabilities interactively
2. Check `omni --help` and `omni run --help` for all available flags
3. Copy `~/.omniautomator/config.example.toml` to `config.toml` and customise it
4. Read the [README](README.md) for architecture details and Python API examples
