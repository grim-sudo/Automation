# OmniAutomator

## Universal Automation Framework with AI Intelligence

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](https://github.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![CI](https://github.com/grim-sudo/Automation/actions/workflows/ci.yml/badge.svg)](https://github.com/grim-sudo/Automation/actions)

OmniAutomator is a cross-platform automation framework that combines advanced natural language processing with an async AI layer to execute complex workflows through plain-English commands. Version 2.0 introduces a fully dynamic free-model resolver, n8n workflow integration, and a custom Linux distro builder.

---

## What's New in v2.0

- **Dynamic free-model resolution** — fetches available free models from OpenRouter at runtime; no model names are hardcoded anywhere in the codebase
- **n8n workflow bridge** — create, run, and manage n8n workflows from natural language or CLI commands
- **Custom Linux distro builder** — build bootable ISOs from TOML profiles or NL descriptions (Debian, Arch, Buildroot)
- **Async AI layer** — `httpx.AsyncClient`, SSE streaming, `tenacity` fallback chain, `tiktoken` sliding-window context
- **Unified CLI** — single `omni` entry point replacing separate launcher scripts
- **pydantic-settings config** — `~/.omniautomator/config.toml` with env-var override support
- **Structured output parsing** — Pydantic v2 `TaskPlan` / `IntentResult` models with JSON-repair fallbacks
- **Subprocess security** — all shell commands use list-form `safe_run()`; no `shell=True` anywhere
- **Full test suite** — pytest with async support and mocked AI calls

---

## Core Features

### AI-Powered Execution
- **10 NLP intent types**: FILE_OPERATION, SYSTEM_OPERATION, WEB_OPERATION, CODE_OPERATION, DATA_OPERATION, SECURITY_OPERATION, DEVELOPMENT_OPERATION, COMMUNICATION_OPERATION, N8N_WORKFLOW, BUILD_DISTRO
- **Dynamic model selection**: best available free model is selected at runtime from OpenRouter
- **Automatic fallback chain**: if the primary model fails, the next free model is tried automatically
- **Sliding-window context**: conversation history trimmed by token count (default 8 000 tokens)
- **Spell correction**: typo handling with >95% accuracy on common mistakes
- **JSON repair**: malformed AI responses are repaired before parsing

### Automation Capabilities
- **File & folder operations**: create, copy, move, delete, organise
- **System management**: process control, service management, package installation
- **Project generation**: scaffolding for Python, Node.js, React, and more
- **DevOps**: Docker, Kubernetes, CI/CD pipeline automation
- **Web automation**: form submission, scraping, API testing
- **n8n workflows**: create trigger-action pipelines, poll execution status, schedule runs
- **Linux distro builder**: compile custom kernels, build rootfs, assemble bootable ISOs

### Interfaces
- **`omni run`** — single-command CLI execution
- **`omni chatbot`** — multi-turn conversational mode with SSE streaming
- **`omni gui`** — graphical interface
- **`omni batch`** — bulk execution from a file
- **`omni n8n`** — n8n workflow sub-commands
- **`omni distro`** — distro builder sub-commands
- **Python API** — programmatic access via `OmniAutomator`

---

## Installation

### Prerequisites
- Python 3.10 or higher
- An [OpenRouter](https://openrouter.ai) API key (free tier available)

### From Source

```bash
git clone https://github.com/grim-sudo/Automation.git
cd Automation

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# Install core package
pip install -e .

# Install with all optional extras
pip install -e ".[dev,n8n,distro,gui]"
```

### Set Your API Key

```bash
# Linux/macOS — current session
export OPENROUTER_API_KEY="sk-or-v1-..."

# Linux/macOS — permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export OPENROUTER_API_KEY="sk-or-v1-..."' >> ~/.bashrc

# Windows PowerShell
$env:OPENROUTER_API_KEY="sk-or-v1-..."
setx OPENROUTER_API_KEY "sk-or-v1-..."
```

Or create a `.env` file in the project root:

```
OPENROUTER_API_KEY=sk-or-v1-...
```

---

## Quick Start

```bash
# Run a single command
omni run "create a python project with tests"

# Interactive chatbot
omni chatbot

# Batch execution
omni batch commands.txt

# Show all commands and options
omni --help
```

---

## Command Examples

### File & System Operations

```bash
omni run "create folder backup"
omni run "copy all pdf files to archive"
omni run "delete temporary files older than 30 days"
omni run "create 100 folders from test1 to test100 with 15 nested folders each"
```

### With Typos (Auto-Corrected)

```bash
omni run "creat a fodler named test"    # → create a folder named test
omni run "delet all files in downloads" # → delete all files in downloads
omni run "intall packages"              # → install packages
```

### Project Generation

```bash
omni run "generate a python project with flask and postgresql"
omni run "create react application with typescript and testing"
omni run "setup nodejs express api server"
```

### DevOps & Infrastructure

```bash
omni run "create docker container for nodejs application"
omni run "setup kubernetes deployment with monitoring"
omni run "configure ci/cd pipeline with github actions"
```

### n8n Workflow Integration

```bash
# List workflows
omni n8n list

# Run a workflow
omni n8n run <workflow-id>

# Create a workflow from natural language
omni n8n create "when a file appears in S3, send a Slack notification"

# Check execution status
omni n8n status <workflow-id> <execution-id>
```

### Custom Linux Distro Builder

```bash
# Build from a TOML profile
omni distro build --profile debian_base --output ./dist

# Build from natural language
omni distro build --nl "minimal debian iso with nginx, no GUI, headless server"

# List available profiles
omni distro profiles

# Estimate build time
omni distro estimate debian_base
```

---

## Configuration

OmniAutomator reads configuration from (highest to lowest priority):

1. CLI flags (`--debug`, `--safe-mode`, `--log-file`)
2. Environment variables with `OMNI__` prefix (e.g. `OMNI__AI__MAX_TOKENS=16000`)
3. Backward-compat flat env vars (`OPENROUTER_API_KEY`, `MAX_RETRIES`, …)
4. `~/.omniautomator/config.toml`
5. Hardcoded defaults

### Generating the Example Config

```bash
python -c "from omni_automator.config import generate_example_config; generate_example_config()"
# Writes ~/.omniautomator/config.example.toml
```

### Key Settings

```toml
# ~/.omniautomator/config.toml

[ai]
openrouter_api_key = ""   # or set OPENROUTER_API_KEY env var
max_tokens     = 8000      # sliding-window context size
timeout        = 30        # per-request timeout (seconds)
max_retries    = 3         # retry attempts per model before fallback

[n8n]
url     = "http://localhost:5678"
api_key = ""

[distro_builder]
work_dir    = "/tmp/omni_distro_build"
output_dir  = "./distro_output"
debian_mirror = "http://deb.debian.org/debian"
debian_suite  = "bookworm"

# Global
debug      = false
safe_mode  = false         # require confirmation for destructive ops
log_file   = ""            # write JSON logs to this path
```

### CLI Flags

```bash
omni --debug run "your command"           # verbose logging
omni --safe-mode run "delete everything"  # prompt before destructive ops
omni --log-file /tmp/omni.jsonl run "…"   # structured JSON log output
```

---

## Architecture

```
OmniAutomator v2.0
├── omni.py                  Unified typer CLI entry point
├── omni_automator/
│   ├── ai/
│   │   ├── model_resolver.py     Dynamic free-model resolution (OpenRouter)
│   │   ├── model_manager.py      Priority-ordered fallback chain (tenacity)
│   │   ├── openrouter_integration.py  Async httpx client + SSE streaming
│   │   ├── context_manager.py    Sliding-window context (tiktoken)
│   │   ├── response_parser.py    Pydantic v2 TaskPlan / IntentResult
│   │   └── task_planner.py       High-level planning orchestration
│   ├── config.py                 pydantic-settings (TOML + env vars)
│   ├── core/
│   │   ├── engine.py             Main OmniAutomator orchestrator
│   │   └── plugin_manager.py     Plugin discovery and dispatch
│   ├── nlp/
│   │   └── semantic_engine.py    10-intent NLP (+ N8N_WORKFLOW, BUILD_DISTRO)
│   ├── os_adapters/
│   │   ├── linux_adapter.py
│   │   ├── windows_adapter.py
│   │   └── macos_adapter.py
│   ├── plugins/
│   │   ├── n8n_bridge/           n8n REST API client + workflow builder
│   │   ├── universal_automation.py
│   │   ├── project_generator.py
│   │   └── devops_generator.py
│   ├── distro_builder/           Custom Linux ISO pipeline
│   │   ├── kernel_fetcher.py
│   │   ├── kernel_configurator.py
│   │   ├── rootfs_builder.py
│   │   ├── package_selector.py
│   │   ├── iso_assembler.py
│   │   ├── build_pipeline.py
│   │   └── profiles/             TOML build profiles
│   ├── security/
│   │   ├── subprocess_runner.py  safe_run() — no shell=True
│   │   ├── path_validator.py     Traversal detection + safe-mode confirm
│   │   └── permission_manager.py
│   └── utils/
│       └── logger.py             loguru-based logging
└── tests/                        pytest test suite
```

---

## System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| Python | 3.10 | 3.12 |
| RAM | 512 MB | 4 GB |
| Disk | 200 MB | 2 GB (more for distro builds) |
| OS | Windows 10 / Ubuntu 20.04 / macOS 12 | Latest stable |
| Internet | Required for AI features | High-speed |

### Distro Builder Additional Requirements (Linux only)

- `debootstrap` (Debian rootfs)
- `arch-install-scripts` / `pacstrap` (Arch rootfs)
- `xorriso` (ISO assembly)
- `syslinux` (bootloader)
- Root access for rootfs operations

---

## Python API

```python
from omni_automator.core.engine import OmniAutomator

engine = OmniAutomator()
result = engine.execute_command("create folder my_project")
print(result)
```

```python
# Async usage
import asyncio
from omni_automator.ai.openrouter_integration import OpenRouterAutomationAI

ai = OpenRouterAutomationAI()
plan = asyncio.run(ai.analyze_automation_request_async("create a python project"))
for step in plan.steps:
    print(step.action, step.params)
```

```python
# n8n bridge
import asyncio
from omni_automator.plugins.n8n_bridge import WorkflowManager, N8nConfig

cfg = N8nConfig(url="http://localhost:5678", api_key="...")
mgr = WorkflowManager(cfg)
workflows = asyncio.run(mgr.list_workflows())
```

---

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v --asyncio-mode=auto

# Lint
ruff check omni_automator/ omni.py tests/

# Type check
mypy omni_automator/ omni.py --ignore-missing-imports
```

---

## Troubleshooting

**AI not responding**
```bash
echo $OPENROUTER_API_KEY   # verify the key is set
omni --debug run "hello"   # show verbose output
```

**Dependencies missing**
```bash
pip install -e . --force-reinstall
```

**GUI not launching**
```bash
pip install -e ".[gui]"
omni gui
```

**Permission denied (distro builder)**
The distro builder requires root for `debootstrap`/`pacstrap`. Run with `sudo` or as root.

**Debug logging**
```bash
omni --debug --log-file /tmp/omni.jsonl run "your command"
```

---

## Security

- All subprocess calls use `safe_run()` (list-form args — no `shell=True`)
- `PathValidator` blocks directory traversal and writes to system paths
- `--safe-mode` requires explicit confirmation before destructive operations
- API keys are never logged or included in error messages
- All operations are logged via `loguru` (structured JSON when `--log-file` is set)

---

## Support

- **Setup Guide**: [SETUP.md](SETUP.md)
- **Issues**: [GitHub Issues](https://github.com/grim-sudo/Automation/issues)
- **API key**: [openrouter.ai](https://openrouter.ai) (free tier available)
