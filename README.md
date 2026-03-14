# Tyranos

## Universal Automation Framework with AI Intelligence

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](https://github.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![CI](https://github.com/grim-sudo/Automation/actions/workflows/ci.yml/badge.svg)](https://github.com/grim-sudo/Automation/actions)

Tyranos is a cross-platform automation framework that executes complex workflows from plain-English commands. Describe what you want — the framework maps your intent through a multi-layer NLP and AI pipeline and runs it.

---

## What's New in v2.0

| Feature | Description |
|---------|-------------|
| **Dynamic free-model resolver** | Fetches available free models from OpenRouter at runtime — no model names are hardcoded |
| **n8n workflow bridge** | Create, run, and manage n8n workflows from natural language or CLI |
| **Linux distro builder** | Build bootable ISOs from TOML profiles or NL descriptions (Debian, Arch, Buildroot) |
| **Async AI layer** | `httpx.AsyncClient` + SSE streaming + `tenacity` fallback chain + `tiktoken` context window |
| **Unified CLI** | Single `omni` entry point — `run`, `chatbot`, `gui`, `batch`, `n8n`, `distro` |
| **pydantic-settings config** | `~/.tyranos/config.toml` + env-var overrides + `.env` file support |
| **Structured output parsing** | Pydantic v2 `TaskPlan` / `IntentResult` with JSON-repair fallbacks |
| **Subprocess security** | All shell commands use list-form `safe_run()` — zero `shell=True` |
| **Full test suite** | 153 passing pytest tests with async support |

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/grim-sudo/Automation.git
cd Automation
python -m venv .venv && source .venv/bin/activate
pip install -e .

# 2. Add your API key
echo 'OPENROUTER_API_KEY=sk-or-v1-...' > .env

# 3. Run your first command
python omni.py run "create a folder named my-project"
```

See [SETUP.md](SETUP.md) for full installation and configuration instructions.

---

## Core Capabilities

### Interfaces

| Command | Description |
|---------|-------------|
| `tyranos run "…"` | Execute one natural-language command and exit |
| `tyranos chatbot` | Multi-turn conversational REPL with streaming |
| `tyranos gui` | Graphical interface (requires `[gui]` extra) |
| `tyranos batch FILE` | Run a file of commands, one per line |
| `tyranos n8n …` | n8n workflow management sub-commands |
| `tyranos distro …` | Custom Linux ISO builder sub-commands |

### NLP Intent Types

Tyranos recognises 10 intent categories and routes each to the appropriate plugin:

| Intent | Example trigger words |
|--------|----------------------|
| `CREATE` | create, make, generate, scaffold, build, setup, new |
| `DELETE` | delete, remove, erase, purge, wipe, uninstall |
| `MODIFY` | move, copy, rename, update, convert, transform |
| `QUERY` | show, list, find, search, check, status, display |
| `EXECUTE` | run, start, deploy, release, trigger, launch, ship |
| `CONFIGURE` | configure, enable, disable, activate, tune, set |
| `ANALYZE` | analyze, audit, inspect, review, assess, measure |
| `HELP` | help, what can you do, commands |
| `N8N_WORKFLOW` | n8n, workflow, list workflows, trigger workflow |
| `BUILD_DISTRO` | build iso, create distro, compile kernel, linux image |

### Automation Capabilities

```
File & folder operations       create, delete, copy, move, rename, list, bulk-create, nested folders
Package management             install, uninstall, search, list (apt / pacman / pip / npm / brew)
Project scaffolding            Python, C, Java, React, Next.js, Express, web scraping, data science
DevOps & infrastructure        Dockerfile, docker-compose, Kubernetes, CI/CD, Terraform, monitoring
Document generation            Word (.docx), PowerPoint (.pptx), Excel (.xlsx), PDF
Web automation                 browser control, scraping, text/link/image/table extraction
Cloud deployment               AWS, GCP, Azure, Heroku via CLI wrappers
System administration          services, firewall, users, permissions, scheduled tasks
Security                       SSL setup, vulnerability scan, compliance check, hardening
n8n workflows                  create, list, run, status via REST API v1
Linux distro builder           Debian / Arch / Buildroot ISOs from TOML profiles or NL
Spell correction               typo-tolerant command parsing (Levenshtein)
```

See [usage.md](usage.md) for a complete command reference with examples for **every** capability.

---

## Installation

```bash
# Core only
pip install -e .

# With optional feature groups
pip install -e ".[dev]"                    # + tests, linting, type checking
pip install -e ".[n8n]"                    # + n8n workflow bridge
pip install -e ".[distro]"                 # + Linux distro builder
pip install -e ".[gui]"                    # + graphical interface
pip install -e ".[web]"                    # + Selenium / Playwright
pip install -e ".[data]"                   # + numpy, pandas, matplotlib
pip install -e ".[dev,n8n,distro,gui]"     # everything
```

Full instructions: [SETUP.md](SETUP.md)

---

## Configuration

Settings are read in this priority order (highest wins):

```
CLI flag  →  OMNI__SECTION__FIELD env var  →  .env file  →  ~/.tyranos/config.toml  →  default
```

**Minimal `.env`:**

```dotenv
OPENROUTER_API_KEY=sk-or-v1-...

# n8n (optional)
N8N_URL=http://localhost:5678
N8N_API_KEY=your-n8n-key
```

**Key `~/.tyranos/config.toml` settings:**

```toml
[ai]
openrouter_api_key = ""   # or use OPENROUTER_API_KEY env var
max_tokens  = 8000
timeout     = 30
max_retries = 3

[n8n]
url     = "http://localhost:5678"
api_key = ""

[distro_builder]
output_dir = "./distro_output"

debug     = false
safe_mode = false
```

---

## Command Examples

```bash
# --- Files & Folders ---
python omni.py run "create a folder named reports"
python omni.py run "create 50 folders named test1 to test50"
python omni.py run "delete all .tmp files in ~/Downloads"
python omni.py run "copy all PDFs from ~/Documents to ~/archive"
python omni.py run "rename old_config.json to config.json"
python omni.py run "list all files in ~/Projects"

# --- Projects ---
python omni.py run "create a Python project called my-api"
python omni.py run "scaffold a React app named dashboard"
python omni.py run "generate an Express backend named api-server"
python omni.py run "create a Java project named inventory-system"

# --- DevOps ---
python omni.py run "create a Dockerfile for a Node.js app"
python omni.py run "generate a docker-compose for postgres and redis"
python omni.py run "create a GitHub Actions CI pipeline"
python omni.py run "generate Terraform config for AWS EC2"

# --- Documents ---
python omni.py run "create a Word document named quarterly-report.docx"
python omni.py run "generate a PowerPoint presentation about AI trends"
python omni.py run "create an Excel spreadsheet with columns for name, date, amount"
python omni.py run "generate a PDF invoice"

# --- Packages ---
python omni.py run "install nginx"
python omni.py run "uninstall apache2"
python omni.py run "search for python packages matching http"
python omni.py run "list all installed packages"

# --- Web ---
python omni.py run "scrape https://example.com and extract all links"
python omni.py run "download https://example.com/file.zip to ~/Downloads"

# --- n8n ---
python omni.py n8n list
python omni.py n8n create "send a Slack message every morning at 9am"
python omni.py n8n run <workflow-id>
python omni.py n8n status <workflow-id>

# --- Distro ---
python omni.py distro profiles
python omni.py distro estimate --profile debian_base
sudo python omni.py distro build --profile debian_base --output ./dist

# --- Typo tolerance ---
python omni.py run "creat a fodler named test"   # auto-corrected
python omni.py run "intall packge nginx"          # auto-corrected

# --- Flags ---
python omni.py --debug run "deploy the app"
python omni.py --safe-mode run "delete old logs"
python omni.py --log-file ~/omni.jsonl batch tasks.txt
```

---

## Architecture

```
Tyranos v2.0
├── omni.py                         Unified typer CLI entry point
├── tyranos/
│   ├── ai/
│   │   ├── model_resolver.py       Dynamic free-model resolution (OpenRouter)
│   │   ├── model_manager.py        Priority-ordered fallback chain (tenacity)
│   │   ├── openrouter_integration.py   Async httpx + SSE streaming
│   │   ├── context_manager.py      Sliding-window context (tiktoken)
│   │   ├── response_parser.py      Pydantic v2 TaskPlan / IntentResult
│   │   └── task_planner.py         High-level planning orchestration
│   ├── config.py                   pydantic-settings (TOML + env vars)
│   ├── core/
│   │   ├── engine.py               Main Tyranos orchestrator
│   │   └── plugin_manager.py       Plugin discovery and dispatch
│   ├── nlp/
│   │   ├── semantic_engine.py      10-intent NLP classifier
│   │   ├── flexible_processor.py   Contextual slot-filling
│   │   └── spell_corrector.py      Levenshtein typo correction
│   ├── os_adapters/
│   │   ├── linux_adapter.py        Linux filesystem + system + GUI
│   │   ├── windows_adapter.py      Windows filesystem + system + GUI
│   │   ├── macos_adapter.py        macOS filesystem + system + GUI
│   │   └── arch_adapter.py         Arch-Linux-specific adapter
│   ├── parsers/
│   │   ├── command_parser.py       Structured step extraction
│   │   └── ai_parser.py            AI-enhanced intent parsing
│   ├── plugins/
│   │   ├── universal_automation.py   1 400-line catch-all plugin
│   │   ├── folder_operations.py      Bulk / nested folder ops
│   │   ├── project_generator.py      Project scaffolding
│   │   ├── devops_generator.py       DevOps config generation
│   │   ├── web_automation.py         Selenium / Playwright browser control
│   │   └── n8n_bridge/               n8n REST API v1 async client
│   ├── distro_builder/               10-stage async ISO build pipeline
│   ├── security/
│   │   ├── subprocess_runner.py      safe_run() — no shell=True
│   │   ├── path_validator.py         Traversal + null-byte detection
│   │   └── permission_manager.py
│   └── utils/
│       └── logger.py                 loguru structured logging
└── tests/                            153 pytest tests
```

---

## Python API

```python
# High-level engine
from tyranos.core.engine import Tyranos

engine = Tyranos()
result = engine.execute("create folder my_project")
engine.shutdown()

# Async AI direct
import asyncio
from tyranos.ai.openrouter_integration import OpenRouterAutomationAI

ai = OpenRouterAutomationAI()
plan = asyncio.run(ai.analyze_automation_request_async("setup a Python project"))
for step in plan.steps:
    print(step.action, step.params)

# n8n bridge
import asyncio
from tyranos.plugins.n8n_bridge import WorkflowManager, N8nConfig

cfg = N8nConfig(url="http://localhost:5678", api_key="...")
mgr = WorkflowManager(cfg)
workflows = asyncio.run(mgr.list_workflows())
```

---

## System Requirements

| | Minimum | Recommended |
|-|---------|-------------|
| Python | 3.10 | 3.12 |
| RAM | 512 MB | 4 GB |
| Disk | 200 MB | 2 GB (more for distro builds) |
| OS | Windows 10 / Ubuntu 20.04 / macOS 12 | Latest stable |
| Internet | Required for AI calls | Broadband |

**Distro builder additional (Linux only):** `debootstrap`, `xorriso`, `syslinux`, `arch-install-scripts`; root access required.

---

## Development

```bash
pip install -e ".[dev]"

pytest tests/ -v                                         # run all 153 tests
ruff check --fix tyranos/ omni.py                 # lint + auto-fix
ruff format tyranos/ omni.py                      # format
mypy tyranos/ omni.py --ignore-missing-imports    # type check
```

---

## Security

- All subprocess calls go through `safe_run()` — no `shell=True` anywhere in the codebase
- `PathValidator` blocks `..` traversal sequences and null-byte injection
- `--safe-mode` requires explicit confirmation before any destructive operation
- API keys are never logged or included in error tracebacks
- Structured JSON logs via `loguru` keep sensitive fields out of plain-text output

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `omni: command not found` | Activate venv: `source .venv/bin/activate` |
| AI not responding | Check `echo $OPENROUTER_API_KEY`; run `tyranos --debug run "hello"` |
| 401 from n8n | Ensure `N8N_API_KEY` and `N8N_URL` are set in `.env` |
| GUI not launching | `pip install -e ".[gui]"` |
| distro: permission denied | Run distro commands with `sudo` |
| Import errors | Ensure venv is active and `pip install -e .` has been run from project root |

---

## Documentation

| File | Contents |
|------|----------|
| [SETUP.md](SETUP.md) | Full installation, configuration, development workflow |
| [usage.md](usage.md) | Every capability with example commands |
| [user_guide.md](user_guide.md) | Interface walkthrough and config reference |
| [bug_report.md](bug_report.md) | Audit report — 22 bugs found and fixed |

---

## License

MIT — see [LICENSE](LICENSE).

## Support

- **Issues:** [GitHub Issues](https://github.com/grim-sudo/Automation/issues)
- **API key:** [openrouter.ai](https://openrouter.ai) (free tier available)
