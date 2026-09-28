# Archon — User Guide

Archon turns plain-English instructions into real actions on your machine. You
describe an outcome; Archon classifies the intent, plans the steps with an AI
model, and executes them through a hardened, cross-platform automation layer.

This guide walks through every way to drive Archon and every option you can
set. For a conceptual overview and architecture, see
**[README.md](README.md)**. For a capability-by-capability command catalog, see
**[docs/usage.md](docs/usage.md)**.

---

## Table of contents

1. [Installation](#installation)
2. [First run](#first-run)
3. [Configuration](#configuration)
4. [The `run` command](#the-run-command)
5. [Interactive chatbot](#interactive-chatbot)
6. [Batch execution](#batch-execution)
7. [Desktop command center](#desktop-command-center)
8. [n8n workflows](#n8n-workflows)
9. [Linux distro builder](#linux-distro-builder)
10. [MCP server & autonomous agent](#mcp-server--autonomous-agent)
11. [Global flags](#global-flags)
12. [Environment variables](#environment-variables)
13. [Configuration file reference](#configuration-file-reference)
14. [Troubleshooting](#troubleshooting)

---

## Installation

**Requirements:** Python 3.10+ (3.12+ recommended) and a virtual environment.

```bash
# Clone the repository
git clone https://github.com/grim-sudo/Automation.git
cd Automation

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate           # Windows

# Install the core package
pip install -e .
```

**Optional feature groups:**

```bash
pip install -e ".[dev]"                    # tests, linting, type checking
pip install -e ".[n8n]"                    # n8n workflow bridge
pip install -e ".[distro]"                 # Linux ISO builder (Linux only)
pip install -e ".[web]"                    # Selenium / Playwright browser automation
pip install -e ".[gui]"                    # desktop automation (screen / input control)
pip install -e ".[data]"                   # numpy, pandas, matplotlib, seaborn
pip install -e ".[mcp]"                    # FastMCP server + local agent
pip install -e ".[dev,n8n,distro,web]"     # a full working set
```

| Group | Adds |
|-------|------|
| `dev` | pytest, pytest-asyncio, respx, ruff, mypy |
| `n8n` | aiohttp (webhook listener) |
| `distro` | kconfiglib (kernel config helpers) |
| `web` | selenium, playwright, webdriver-manager |
| `gui` | pyautogui, pynput, pillow, psutil (screen / input automation) |
| `data` | numpy, pandas, matplotlib, seaborn |
| `mcp` | fastmcp (MCP server + local Ollama agent) |

**Verify:**

```bash
archon --version
# Archon v2.0.0
```

> If your virtual environment's `bin/` is on `PATH`, use `archon` directly.
> Otherwise call `python archon.py` from the project root — the two are
> equivalent.

---

## First run

By default Archon runs its AI planning core on a **local LLM through
[Ollama](https://ollama.com)** — no API key, no cloud dependency. The default
model is `qwen3.5:9b`.

```bash
# One-time: install Ollama, then pull the default model
ollama pull qwen3.5:9b

# Make sure the Ollama server is running (usually automatic)
ollama serve   # if not already running

# Run your first command
archon run "create a folder named my-project"
```

Archon talks to Ollama at `http://127.0.0.1:11434` by default. Override the
URL or model with the `OLLAMA_URL` / `OLLAMA_MODEL` env vars or the `[ai]`
config section.

Archon can also target a cloud backend by setting `AI_PROVIDER` to `freellmapi`,
`openai`, or `anthropic` (with the matching `*_API_KEY`). Any cloud provider
falls back to local Ollama automatically if it's unreachable, so Archon keeps
working either way. See [SETUP.md](SETUP.md#step-4--set-up-the-ai-backend) for
the full provider matrix. Chain-of-thought / "thinking" tokens are never shown.

### Memory

Archon remembers what it learns across sessions, regardless of which provider
is active. Durable facts (preferences, environment, ongoing projects) are
extracted automatically after each exchange and stored in a local SQLite file
at `~/.archon/memory.db`; relevant ones are injected into later prompts. You can
also manage memory explicitly in chat:

- `remember that I use PostgreSQL` — store a fact directly.
- `what do you remember about me` — list stored memories.
- `forget about zsh` — drop memories matching a phrase.
- `forget everything` — clear the store.

Turn it off with `MEMORY_ENABLED=false`, or keep the store but disable automatic
extraction (explicit `remember` only) with `MEMORY_AUTO_EXTRACT=false`.

Running `archon` with no sub-command drops you straight into the interactive
chatbot.

---

## Configuration

Settings resolve in priority order (highest wins):

```
CLI flag  →  SECTION__FIELD env var  →  flat env var  →  .env file  →  ~/.archon/config.toml  →  default
```

The two nested-section env forms are, for example, `AI__MODEL` (double
underscore, section-scoped) and the flat convenience aliases like
`OLLAMA_MODEL` and `N8N_URL`. Use the flat names in `.env`; the
double-underscore names are for section-scoped overrides.

Generate a commented example config with:

```bash
python -c "from archon.config import generate_example_config; generate_example_config()"
# writes ~/.archon/config.example.toml
```

See [Configuration file reference](#configuration-file-reference) for every
setting.

---

## The `run` command

Execute a single natural-language command and exit.

```bash
archon run "create a folder named reports"
archon run "create 50 folders named test1 to test50"
archon run "delete all .tmp files in ~/Downloads"
archon run "scaffold a React app named dashboard"
archon run "create a Dockerfile for a Node.js app"
archon run "take a screenshot and save to ~/screenshots/now.png"
```

**Options:**

| Flag | Effect |
|------|--------|
| `--safe-mode` | Require confirmation before any destructive operation |
| `--debug` | Verbose logging |
| `-m`, `--model <id>` | Force a specific AI model for this run |

Typos are tolerated automatically (`creat a fodler named test` still works).
On failure, Archon prints the error plus any AI-suggested fixes and exits with
a non-zero status.

---

## Interactive chatbot

A multi-turn conversational shell that keeps context across turns and executes
real commands.

```bash
archon chatbot
# or just: archon
```

Type commands in plain English. Spell-correction and multi-turn context are
automatic. The session also supports slash-commands:

| Command | Description |
|---------|-------------|
| `/help` | Show the help panel |
| `/status` | Session status (directory, last operation, counts) |
| `/history` | Recent commands this session |
| `/context` | Conversation context (same as `/status`) |
| `/cd <path>` | Change the working directory |
| `/pwd` | Print the working directory |
| `/ls [path]` | List directory contents |
| `/explain` | Explain the most recent command |
| `/undo` | Undo the last operation (not yet implemented) |
| `/model [n\|id]` | List installed Ollama models and switch the active one |
| `/clear` | Clear the screen |
| `/exit`, `/quit` | Quit the session |

### Switching the AI model

The `/model` command lets you see and change the active Ollama model:

- **`/model`** — prints a numbered menu of the models installed on your local
  Ollama server, with the current one marked `● current`.
- **`/model <n>`** — switch directly by menu number.
- **`/model <id-or-substring>`** — switch by exact model id or a unique
  substring of the id or display name. Ambiguous or missing matches are
  rejected with no change.

The switch takes effect immediately for the rest of the session. It is not
persisted to disk — the next launch reverts to the configured default. To pin
a model across launches, set `OLLAMA_MODEL` or `[ai] model` in `config.toml`.

> Only models you have pulled (`ollama pull <name>`) appear in the menu.

---

## Batch execution

Run a file of commands, one per line. Lines starting with `#` are comments;
blank lines are skipped.

```bash
archon batch tasks.txt
archon batch tasks.txt --stop-on-error
```

Example `tasks.txt`:

```
# Create directory structure
create a folder named projects/web on the Desktop
take a screenshot and save to ~/screenshots/before.png
install nginx
```

**Options:**

| Flag | Effect |
|------|--------|
| `--stop-on-error` | Halt after the first failure instead of continuing |
| `--safe-mode` | Confirm before destructive operations |
| `--debug` | Verbose logging |

A results table (succeeded / failed / total) prints at the end. The command
exits non-zero if any command failed.

---

## Desktop command center

Archon's graphical interface is a native desktop app built with **Tauri v2**
(Rust backend) and **Vite + TypeScript** (frontend), living in `ui-tauri/`. It
reads live system telemetry natively in Rust and drives the same Python engine
over a JSON IPC bridge.

```bash
archon gui
```

`archon gui` launches a built binary if one exists under
`ui-tauri/src-tauri/target/{release,debug}/`. If none is found, it prints the
commands to run or build it:

```bash
cd ui-tauri
npm install
npm run tauri dev       # run in development mode
# or
npm run tauri build     # produce a release binary; then `archon gui` finds it
```

**Prerequisites:** Node.js, a Rust toolchain, and the Tauri platform
dependencies (on Linux: `webkit2gtk-4.1` and `gtk3`). See the
[Tauri prerequisites guide](https://tauri.app/start/prerequisites/).

---

## n8n workflows

Manage n8n workflows on a configured instance. Requires `N8N_URL` and
`N8N_API_KEY` (set the flat names in `.env`).

```bash
archon n8n list                          # list all workflows
archon n8n run <workflow-id>             # trigger a workflow
archon n8n run <workflow-id> -p '{"key":"value"}'   # trigger with a JSON payload
archon n8n create "send a Slack message every morning at 9am"  # generate from NL
archon n8n status                        # check instance connectivity
```

---

## Linux distro builder

Build custom Linux ISOs from a natural-language description or a TOML profile.
**Linux only. Requires root and substantial disk space (>= 10 GB recommended).**

```bash
archon distro profiles                   # list available .toml profiles
archon distro estimate "minimal Debian with Python 3.12"   # estimate time/disk
sudo archon distro build "minimal Debian bookworm with i3 and Python 3.12"
sudo archon distro build --profile ~/profiles/developer.toml -o /mnt/iso
```

**`build` options:**

| Flag | Effect |
|------|--------|
| `--profile <path>` | Path to a `.toml` build profile |
| `-o`, `--output <dir>` | Output directory for ISO artifacts (default `./distro_output`) |
| `-j`, `--jobs <n>` | Parallel build jobs (0 = auto-detect) |

The builder requires root and confirms before running unless confirmation is
disabled in config. Review your TOML profile before running with `sudo`.

> `archon` is installed inside the virtual environment, so it is not on the
> root `PATH` by default. Run the builder as `sudo .venv/bin/archon distro
> build …` (or `sudo python archon.py distro build …`).

Profiles are searched in, in order:
`archon/distro_builder/profiles/`, `~/.archon/profiles/`,
`/etc/archon/profiles/`, and `./profiles/`.

---

## MCP server & autonomous agent

Archon can expose its capabilities over the
[Model Context Protocol](https://modelcontextprotocol.io) and let a local Ollama
model call those tools autonomously. Install the optional extra first:

```bash
pip install -e ".[mcp]"                  # pulls in FastMCP
```

### Serve Archon as MCP tools

```bash
archon mcp serve                         # stdio transport (default)
archon mcp serve --transport http --port 8000
```

Any MCP client (Claude Desktop, another agent, etc.) can then call three tools:

| Tool | Purpose |
|------|---------|
| `list_capabilities` | Discover every capability, its actions, and risk level |
| `run_automation` | Run a plain natural-language command; reaches every capability, including the OS builder |
| `dispatch_action` | Invoke a specific `capability` / `action` / `params` directly |

> **Security:** the server enforces Archon's permission policy but adds no
> per-call confirmation prompt. Only expose it to trusted clients. For a
> confirmation-gated local model, use `archon mcp agent` instead.

### Drive the local model against the tools

```bash
archon mcp agent "create a folder named reports on the desktop"
archon mcp agent                         # interactive session
```

The model (default `qwen3.5:9b`) plans and calls tools on its own. Low and
medium-risk actions run automatically; high-risk or destructive ones (deleting
data, killing processes, changing system settings, building an OS) pause for a
`y/n` confirmation.

| Flag | Effect |
|------|--------|
| `-y`, `--yes` | Auto-approve high-risk actions without prompting (use with care) |
| `--debug` | Verbose logging |

The model never reaches a raw shell — every action is routed through Archon's
capability registry and permission manager.

---

## Global flags

These apply to any command and can be placed before the sub-command:

| Flag | Env var | Effect |
|------|---------|--------|
| `-V`, `--version` | — | Print the version and exit |
| `--debug` | `ARCHON_DEBUG` | Enable verbose debug logging |
| `--log-file <path>` | `ARCHON_LOG_FILE` | Write structured JSON logs to a file |
| `--safe-mode` | `ARCHON_SAFE_MODE` | Require confirmation for destructive operations |

```bash
archon --debug run "deploy the app"
archon --safe-mode run "delete old logs"
archon --log-file ~/archon.jsonl batch tasks.txt
```

---

## Environment variables

| Variable | Purpose |
|----------|---------|
| `AI_PROVIDER` | AI backend: `ollama` (default), `freellmapi`, `openai`, or `anthropic` |
| `OLLAMA_URL` | Local Ollama server URL (default `http://127.0.0.1:11434`) |
| `OLLAMA_MODEL` | Local model name (default `qwen3.5:9b`) |
| `FREELLMAPI_URL` / `FREELLMAPI_API_KEY` / `FREELLMAPI_MODEL` | FreeLLMAPI endpoint, key, and model (default model `auto`) |
| `OPENAI_URL` / `OPENAI_API_KEY` / `OPENAI_MODEL` | OpenAI endpoint, key, and model |
| `ANTHROPIC_URL` / `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | Anthropic endpoint, key, and model |
| `MEMORY_ENABLED` / `MEMORY_AUTO_EXTRACT` | Persistent cross-session memory and auto-fact-extraction (both default on) |
| `MEMORY_MAX_INJECT` / `MEMORY_DB_PATH` | Max facts injected per prompt (default 8) and DB path override (default `~/.archon/memory.db`) |
| `N8N_URL` | n8n instance base URL (e.g. `http://localhost:5678`) |
| `N8N_API_KEY` | n8n REST API key |
| `ARCHON_DEBUG` | Enable debug logging (`1`/`true`) |
| `ARCHON_LOG_FILE` | Path for structured JSON logs |
| `ARCHON_SAFE_MODE` | Require confirmation for destructive operations |

Flat names shown above are the convenience aliases used in `.env`. Nested
section overrides use the double-underscore form (e.g. `AI__MAX_TOKENS`,
`DISTRO_BUILDER__OUTPUT_DIR`).

---

## Configuration file reference

Archon reads `~/.archon/config.toml`. Key settings:

```toml
[ai]
provider     = "ollama"                    # ollama | freellmapi | openai | anthropic
ollama_url   = "http://127.0.0.1:11434"    # local Ollama server
ollama_model = "qwen3.5:9b"                # default local model
model        = ""         # pin a model; blank uses ollama_model
max_tokens   = 8000
timeout      = 30
max_retries  = 3

# Cloud backends (used when 'provider' selects them; fall back to Ollama when down)
# freellmapi_api_key = ""
# freellmapi_model   = "auto"
# openai_api_key     = ""
# anthropic_api_key  = ""

[n8n]
url     = "http://localhost:5678"
api_key = ""

[distro_builder]
output_dir = "./distro_output"

# Top-level flags
debug     = false
safe_mode = false
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `archon: command not found` | Activate the venv (`source .venv/bin/activate`) or call `python archon.py` |
| AI not responding | Default local backend: check Ollama is running (`curl http://127.0.0.1:11434/api/tags`) and the model is pulled (`ollama pull qwen3.5:9b`). Cloud `AI_PROVIDER`: the sidebar **Backend** field shows the active provider — if it fell back to Ollama the provider was unreachable; verify its endpoint/key. Run `archon --debug run "hello"` |
| First AI request is slow / times out | Local models are slow to load on first use; Archon uses a 120s floor for the local timeout. Larger models need more RAM/VRAM |
| A large nested command only ran partially | The chosen model may be flaky. Try `/model` to switch to a more reliable one |
| n8n returns 401 | Ensure `N8N_URL` and `N8N_API_KEY` are set in `.env` (flat names, not `N8N__URL`) |
| GUI won't launch | Build it once: `cd ui-tauri && npm install && npm run tauri build`, or `npm run tauri dev` |
| Distro: permission denied | Run the build as `sudo .venv/bin/archon distro build …` |
| Import errors | Ensure the venv is active and `pip install -e .` ran from the project root |

More detailed setup and development notes are in **[SETUP.md](SETUP.md)**.
