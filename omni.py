#!/usr/bin/env python3
"""
OmniAutomator unified CLI entry point.

Commands: run, chatbot, gui, batch, n8n (subgroup), distro (subgroup)

Usage:
    omni run "create a folder named reports on the Desktop"
    omni chatbot
    omni gui
    omni batch commands.txt
    omni n8n list
    omni n8n run <workflow-id>
    omni distro build "minimal Debian bookworm with Python 3.12"
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import IO, Optional

# Ensure project root is on sys.path so relative imports work regardless of
# how this script is invoked (e.g. python omni.py vs as a console_script).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# ---------------------------------------------------------------------------
# Typer application objects
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="omni",
    help="OmniAutomator - Natural Language Automation Framework",
    rich_markup_mode="rich",
    no_args_is_help=False,
    add_completion=True,
)

n8n_app = typer.Typer(
    name="n8n",
    help="n8n workflow management commands",
    rich_markup_mode="rich",
)

distro_app = typer.Typer(
    name="distro",
    help="Custom distro builder commands",
    rich_markup_mode="rich",
)

app.add_typer(n8n_app, name="n8n")
app.add_typer(distro_app, name="distro")

console = Console()

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

try:
    from omni_automator import __version__ as _VERSION
except Exception:
    _VERSION = "1.0.0"


def version_callback(value: bool) -> None:
    """Print version string and exit when --version is given."""
    if value:
        console.print(f"OmniAutomator [bold cyan]v{_VERSION}[/bold cyan]")
        raise typer.Exit()


# ---------------------------------------------------------------------------
# Global state populated by the @app.callback
# ---------------------------------------------------------------------------

_global_debug: bool = False
_global_log_file: Optional[str] = None
_global_safe_mode: bool = False


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Print version and exit.",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        envvar="OMNI_DEBUG",
        help="Enable debug logging.",
    ),
    log_file: Optional[str] = typer.Option(
        None,
        "--log-file",
        envvar="OMNI_LOG_FILE",
        help="Write JSON logs to this file.",
    ),
    safe_mode: bool = typer.Option(
        False,
        "--safe-mode",
        envvar="OMNI_SAFE_MODE",
        help="Require confirmation for destructive operations.",
    ),
) -> None:
    """OmniAutomator — Natural Language Automation Framework.

    Run [bold]omni COMMAND --help[/bold] for help on individual commands.
    """
    global _global_debug, _global_log_file, _global_safe_mode
    _global_debug = debug
    _global_log_file = log_file
    _global_safe_mode = safe_mode

    # Configure logging as early as possible
    try:
        from omni_automator.utils.logger import configure_logging
        configure_logging(debug=debug, log_file=log_file)
    except Exception:
        pass

    # Ensure the config directory and example file exist
    try:
        from omni_automator.config import generate_example_config
        example = Path.home() / ".omniautomator" / "config.example.toml"
        if not example.exists():
            generate_example_config(example)
    except Exception:
        pass

    # If no sub-command given, default to interactive chatbot
    if ctx.invoked_subcommand is None:
        _launch_chatbot(debug=debug)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_engine(safe_mode: bool = False, debug: bool = False):
    """Construct and return an OmniAutomator engine instance."""
    try:
        from omni_automator.config import get_settings
        settings = get_settings()
        config = {
            "openrouter_api_key": settings.ai.openrouter_api_key,
            "safe_mode": safe_mode or settings.safe_mode,
            "continue_on_error": settings.continue_on_error,
            "debug": debug or settings.debug,
        }
    except Exception:
        config = {
            "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
            "safe_mode": safe_mode,
            "continue_on_error": False,
        }

    from omni_automator import OmniAutomator
    return OmniAutomator(config=config)


def _print_result_dict(data: dict) -> None:
    """Pretty-print a result dict as a Rich table."""
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Key")
    table.add_column("Value")
    for k, v in data.items():
        table.add_row(str(k), str(v)[:120])
    console.print(table)


def _launch_chatbot(debug: bool = False) -> None:
    """Start the chatbot interactive session."""
    # Try the modern ChatbotMode class first, then fall back to get_chatbot()
    bot = None
    try:
        from omni_automator.ui.chatbot import ChatbotMode
        bot = ChatbotMode()
    except ImportError:
        pass

    if bot is None:
        try:
            from omni_automator.ui.chatbot import get_chatbot
            bot = get_chatbot()
        except ImportError as exc:
            console.print(f"[bold red]Error:[/bold red] Could not import chatbot: {exc}")
            raise typer.Exit(1)

    console.print(
        Panel(
            "Welcome to [bold cyan]OmniAutomator[/bold cyan] interactive mode.\n"
            "Type [bold]help[/bold] for available commands or [bold]exit[/bold] to quit.",
            title="Chatbot",
            border_style="cyan",
        )
    )

    try:
        bot.start_interactive_session()
    except KeyboardInterrupt:
        console.print("\n[yellow]Session ended by user.[/yellow]")
    except Exception as exc:
        console.print(f"[bold red]Chatbot error:[/bold red] {exc}")
        if debug or _global_debug:
            import traceback
            traceback.print_exc()
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# run command
# ---------------------------------------------------------------------------

@app.command()
def run(
    command: str = typer.Argument(..., help="Natural language command to execute."),
    safe_mode: bool = typer.Option(
        False, "--safe-mode", help="Require confirmation for destructive operations."
    ),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging."),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Force a specific AI model id."
    ),
) -> None:
    """Execute a natural language automation command.

    Examples:

        omni run "create a folder named reports"

        omni run "take a screenshot and save to ~/screenshots/now.png" --safe-mode
    """
    _eff_debug = debug or _global_debug
    _eff_safe = safe_mode or _global_safe_mode

    try:
        from omni_automator.utils.logger import configure_logging
        configure_logging(debug=_eff_debug, log_file=_global_log_file)
    except Exception:
        pass

    console.print(
        Panel(
            f"[bold]Command:[/bold] {command}",
            title="[cyan]OmniAutomator[/cyan]",
            border_style="cyan",
        )
    )

    try:
        engine = _build_engine(safe_mode=_eff_safe, debug=_eff_debug)
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] Failed to initialise engine: {exc}")
        raise typer.Exit(1)

    if model:
        try:
            engine.switch_ai_model(model)
        except Exception as exc:
            console.print(f"[yellow]Warning:[/yellow] Could not switch model: {exc}")

    start = time.perf_counter()
    try:
        with console.status(f"Running: [cyan]{command}[/cyan]"):
            result = engine.execute(command)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user.[/yellow]")
        raise typer.Exit(0)
    except Exception as exc:
        console.print(f"[bold red]Execution error:[/bold red] {exc}")
        if _eff_debug:
            import traceback
            traceback.print_exc()
        raise typer.Exit(1)
    finally:
        try:
            engine.shutdown()
        except Exception:
            pass

    elapsed = time.perf_counter() - start

    if result.get("success"):
        console.print(
            Panel(
                f"[green]Success[/green] in [bold]{elapsed:.2f}s[/bold]",
                border_style="green",
            )
        )
        inner = result.get("result")
        if isinstance(inner, dict) and inner:
            _print_result_dict(inner)
        elif inner is not None and str(inner).strip():
            console.print(str(inner))
    else:
        error_msg = result.get("error", "Unknown error")
        fallback = result.get("fallback_message", "")
        console.print(f"[bold red]Failed:[/bold red] {error_msg}")
        if fallback and fallback != error_msg:
            console.print(f"[yellow]{fallback}[/yellow]")
        suggestions = result.get("ai_suggestions", [])
        if suggestions:
            console.print("\n[bold]Suggestions:[/bold]")
            for s in suggestions:
                console.print(f"  • {s}")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# chatbot command
# ---------------------------------------------------------------------------

@app.command()
def chatbot(
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging."),
) -> None:
    """Launch interactive chatbot mode.

    Start a conversational session where you can issue natural language
    commands and receive step-by-step feedback.
    """
    try:
        from omni_automator.utils.logger import configure_logging
        configure_logging(debug=debug or _global_debug, log_file=_global_log_file)
    except Exception:
        pass
    _launch_chatbot(debug=debug)


# ---------------------------------------------------------------------------
# gui command
# ---------------------------------------------------------------------------

@app.command()
def gui() -> None:
    """Launch the graphical user interface.

    Opens the OmniAutomator desktop GUI built on CustomTkinter / Tkinter.
    """
    try:
        from omni_automator.utils.logger import configure_logging
        configure_logging(debug=_global_debug, log_file=_global_log_file)
    except Exception:
        pass

    console.print(
        Panel(
            "Starting [bold cyan]OmniAutomator GUI[/bold cyan]...",
            border_style="cyan",
        )
    )

    try:
        from omni_automator.ui.gui import ModernOmniAutomatorGUI
        app_gui = ModernOmniAutomatorGUI()
        app_gui.run()
    except ImportError as exc:
        console.print(
            f"[bold red]Error:[/bold red] Could not import GUI module: {exc}\n"
            "Install the GUI dependencies: [bold]pip install customtkinter[/bold]"
        )
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"[bold red]GUI error:[/bold red] {exc}")
        if _global_debug:
            import traceback
            traceback.print_exc()
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# batch command
# ---------------------------------------------------------------------------

@app.command()
def batch(
    file: typer.FileText = typer.Argument(
        ...,
        help="File containing commands to execute (one per line).",
    ),
    stop_on_error: bool = typer.Option(
        False,
        "--stop-on-error",
        help="Halt execution after the first failure.",
    ),
    safe_mode: bool = typer.Option(
        False, "--safe-mode", help="Require confirmation for destructive operations."
    ),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging."),
) -> None:
    """Execute automation commands from a batch file (one command per line).

    Lines starting with [bold]#[/bold] are treated as comments and skipped.
    Blank lines are also skipped.

    Example file::

        # Create directory structure
        create a folder named projects/web on the Desktop
        take a screenshot and save to ~/screenshots/before.png
    """
    _eff_debug = debug or _global_debug
    _eff_safe = safe_mode or _global_safe_mode

    try:
        from omni_automator.utils.logger import configure_logging
        configure_logging(debug=_eff_debug, log_file=_global_log_file)
    except Exception:
        pass

    raw_lines = file.read().splitlines()
    commands = [
        line.strip()
        for line in raw_lines
        if line.strip() and not line.strip().startswith("#")
    ]

    if not commands:
        console.print("[yellow]No commands found in batch file.[/yellow]")
        return

    console.print(
        Panel(
            f"Executing [bold]{len(commands)}[/bold] commands from batch file.",
            title="[cyan]Batch Mode[/cyan]",
            border_style="cyan",
        )
    )

    try:
        engine = _build_engine(safe_mode=_eff_safe, debug=_eff_debug)
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] Failed to initialise engine: {exc}")
        raise typer.Exit(1)

    succeeded = 0
    failed = 0
    total = len(commands)

    try:
        for idx, cmd in enumerate(commands, start=1):
            console.print(f"\n[bold cyan][{idx}/{total}][/bold cyan] {cmd}")
            try:
                result = engine.execute(cmd)
            except KeyboardInterrupt:
                console.print("\n[yellow]Batch interrupted by user.[/yellow]")
                break
            except Exception as exc:
                console.print(f"  [bold red]Exception:[/bold red] {exc}")
                failed += 1
                if stop_on_error:
                    console.print("[yellow]Stopping on error.[/yellow]")
                    break
                continue

            if result.get("success"):
                succeeded += 1
                console.print("  [green]OK[/green]")
            else:
                failed += 1
                err = result.get("error", "Unknown error")
                console.print(f"  [bold red]FAILED:[/bold red] {err}")
                fallback = result.get("fallback_message", "")
                if fallback and fallback != err:
                    console.print(f"  [yellow]{fallback}[/yellow]")
                if stop_on_error:
                    console.print("[yellow]Stopping on error (--stop-on-error).[/yellow]")
                    break
    finally:
        try:
            engine.shutdown()
        except Exception:
            pass

    # Results table
    table = Table(title="Batch Results", header_style="bold cyan")
    table.add_column("Status")
    table.add_column("Count", justify="right")
    table.add_row("[green]Succeeded[/green]", str(succeeded))
    table.add_row("[red]Failed[/red]", str(failed))
    table.add_row("[dim]Total[/dim]", str(total))
    console.print(table)

    if failed > 0:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# n8n sub-commands
# ---------------------------------------------------------------------------

def _get_n8n_config():
    """Return (base_url, api_key) from settings or environment."""
    try:
        from omni_automator.config import get_settings
        settings = get_settings()
        return settings.n8n.url, settings.n8n.api_key
    except Exception:
        return (
            os.getenv("N8N_URL", "http://localhost:5678"),
            os.getenv("N8N_API_KEY", ""),
        )


def _n8n_headers(api_key: str) -> dict:
    """Build n8n REST API request headers."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-N8N-API-KEY"] = api_key
    return headers


def _n8n_get(endpoint: str) -> dict:
    """Execute a GET request to the n8n REST API."""
    import requests

    url, api_key = _get_n8n_config()
    full_url = f"{url}{endpoint}"
    try:
        resp = requests.get(full_url, headers=_n8n_headers(api_key), timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        console.print(
            f"[bold red]Error:[/bold red] Could not connect to n8n at [cyan]{url}[/cyan].\n"
            "Is n8n running? Check n8n.url in your config.toml."
        )
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"[bold red]n8n API error:[/bold red] {exc}")
        raise typer.Exit(1)


def _n8n_post(endpoint: str, body: dict) -> dict:
    """Execute a POST request to the n8n REST API."""
    import requests

    url, api_key = _get_n8n_config()
    full_url = f"{url}{endpoint}"
    try:
        resp = requests.post(
            full_url, headers=_n8n_headers(api_key), json=body, timeout=30
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        console.print(
            f"[bold red]Error:[/bold red] Could not connect to n8n at [cyan]{url}[/cyan]."
        )
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"[bold red]n8n API error:[/bold red] {exc}")
        raise typer.Exit(1)


@n8n_app.command("list")
def n8n_list() -> None:
    """List all n8n workflows registered on the configured instance."""
    # Try the dedicated bridge plugin first, then fall back to direct REST
    try:
        from omni_automator.plugins.n8n_bridge.workflow_manager import WorkflowManager
        from omni_automator.plugins.n8n_bridge.models import N8nConfig

        url, api_key = _get_n8n_config()
        n8n_cfg = N8nConfig(url=url, api_key=api_key)
        manager = WorkflowManager(n8n_cfg)
        workflows_raw = asyncio.run(manager.list_workflows())
        workflows = [
            {"id": w.id, "name": w.name, "active": w.active, "nodes": []}
            for w in workflows_raw
        ]
    except (ImportError, AttributeError):
        data = _n8n_get("/api/v1/workflows")
        workflows = data.get("data") or (data if isinstance(data, list) else [])

    if not workflows:
        console.print("[yellow]No workflows found.[/yellow]")
        return

    table = Table(title="n8n Workflows", header_style="bold cyan")
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Active")
    table.add_column("Nodes", justify="right")

    for wf in workflows:
        wf_id = str(wf.get("id", "?"))
        name = wf.get("name", "Unnamed")
        active = "[green]Yes[/green]" if wf.get("active") else "[red]No[/red]"
        nodes = str(len(wf.get("nodes", [])))
        table.add_row(wf_id, name, active, nodes)

    console.print(table)


@n8n_app.command("run")
def n8n_run(
    workflow_id: str = typer.Argument(..., help="Workflow ID to trigger."),
    payload: Optional[str] = typer.Option(
        None, "--payload", "-p", help="JSON string to send as execution body."
    ),
) -> None:
    """Trigger an n8n workflow execution.

    The workflow must have an active webhook or the n8n REST API must be enabled.
    """
    body: dict = {}
    if payload:
        try:
            body = json.loads(payload)
        except json.JSONDecodeError as exc:
            console.print(f"[bold red]Invalid JSON payload:[/bold red] {exc}")
            raise typer.Exit(1)

    # Try bridge plugin first
    try:
        from omni_automator.plugins.n8n_bridge.workflow_manager import WorkflowManager
        from omni_automator.plugins.n8n_bridge.models import N8nConfig

        url, api_key = _get_n8n_config()
        n8n_cfg = N8nConfig(url=url, api_key=api_key)
        manager = WorkflowManager(n8n_cfg)
        exec_result = asyncio.run(manager.execute_workflow(workflow_id, body))
        exec_id = getattr(exec_result, "id", "?")
        status = getattr(exec_result, "status", "triggered")
        console.print(
            Panel(
                f"Workflow [bold]{workflow_id}[/bold] triggered.\n"
                f"Execution ID: [bold cyan]{exec_id}[/bold cyan]  "
                f"Status: [green]{status}[/green]",
                title="[green]Triggered[/green]",
                border_style="green",
            )
        )
        return
    except (ImportError, AttributeError):
        pass

    # Fall back to direct REST
    result = _n8n_post(f"/api/v1/workflows/{workflow_id}/execute", body)
    exec_id = result.get("executionId") or result.get("id") or "?"
    console.print(
        Panel(
            f"Workflow [bold]{workflow_id}[/bold] triggered.\n"
            f"Execution ID: [bold cyan]{exec_id}[/bold cyan]",
            title="[green]Triggered[/green]",
            border_style="green",
        )
    )


@n8n_app.command("create")
def n8n_create(
    description: str = typer.Argument(
        ..., help="Natural language workflow description."
    ),
) -> None:
    """Create an n8n workflow from natural language.

    Uses the configured AI model to generate a workflow JSON definition and
    uploads it to the n8n instance via the REST API.
    """
    console.print(
        Panel(
            f"[bold]Description:[/bold] {description}",
            title="[cyan]Generating n8n Workflow[/cyan]",
            border_style="cyan",
        )
    )

    # Try the dedicated bridge plugin first
    try:
        from omni_automator.plugins.n8n_bridge.node_builder import (
            parse_nl_to_steps,
            build_linear_workflow,
        )
        from omni_automator.plugins.n8n_bridge.workflow_manager import WorkflowManager
        from omni_automator.plugins.n8n_bridge.models import N8nConfig

        url, api_key = _get_n8n_config()
        n8n_cfg = N8nConfig(url=url, api_key=api_key)
        manager = WorkflowManager(n8n_cfg)
        steps = parse_nl_to_steps(description)
        if not steps:
            console.print("[bold red]Could not extract workflow steps from description.[/bold red]")
            raise typer.Exit(1)
        workflow = build_linear_workflow(name=description[:50], steps=steps)
        created = asyncio.run(manager.create_workflow(workflow))
        wf_id = getattr(created, "id", "?")
        wf_name = getattr(created, "name", description[:40])
        console.print(
            Panel(
                f"Workflow [bold]{wf_name}[/bold] created.\n"
                f"ID: [bold cyan]{wf_id}[/bold cyan]",
                title="[green]Created[/green]",
                border_style="green",
            )
        )
        return
    except (ImportError, AttributeError):
        pass

    # Fall back: use the AI engine to generate workflow JSON then POST it
    engine = None
    try:
        engine = _build_engine(debug=_global_debug)
        ai_result = engine.execute(
            f"generate n8n workflow JSON for: {description}"
        )
    except Exception as exc:
        console.print(f"[bold red]AI generation error:[/bold red] {exc}")
        raise typer.Exit(1)
    finally:
        if engine:
            try:
                engine.shutdown()
            except Exception:
                pass

    raw_content = ""
    if isinstance(ai_result.get("result"), dict):
        raw_content = str(ai_result["result"].get("content", ""))
    elif isinstance(ai_result.get("result"), str):
        raw_content = ai_result["result"]

    if not raw_content:
        console.print("[bold red]Error:[/bold red] AI did not produce workflow JSON.")
        raise typer.Exit(1)

    try:
        from omni_automator.ai.response_parser import repair_and_parse
        workflow_data = repair_and_parse(raw_content)
        if workflow_data is None:
            raise ValueError("Could not parse AI output as JSON")
    except Exception as exc:
        console.print(f"[bold red]JSON parse error:[/bold red] {exc}")
        raise typer.Exit(1)

    created = _n8n_post("/api/v1/workflows", workflow_data)
    wf_id = created.get("id", "?")
    wf_name = created.get("name", description[:40])
    console.print(
        Panel(
            f"Workflow [bold]{wf_name}[/bold] created.\n"
            f"ID: [bold cyan]{wf_id}[/bold cyan]",
            title="[green]Created[/green]",
            border_style="green",
        )
    )


@n8n_app.command("status")
def n8n_status(
    workflow_id: str = typer.Argument(..., help="Workflow ID to inspect."),
) -> None:
    """Get the current status of an n8n workflow."""
    # Try bridge plugin first
    try:
        from omni_automator.plugins.n8n_bridge.workflow_manager import WorkflowManager
        from omni_automator.plugins.n8n_bridge.models import N8nConfig

        url, api_key = _get_n8n_config()
        n8n_cfg = N8nConfig(url=url, api_key=api_key)
        manager = WorkflowManager(n8n_cfg)
        executions = asyncio.run(manager.get_executions(workflow_id, limit=10))

        if not executions:
            console.print("[yellow]No executions found.[/yellow]")
            return

        table = Table(title=f"Recent executions — {workflow_id}", header_style="bold cyan")
        table.add_column("ID", style="dim")
        table.add_column("Status")
        table.add_column("Started")
        for ex in executions:
            table.add_row(
                str(ex.get("id", "")),
                str(ex.get("status", "")),
                str(ex.get("startedAt", "")),
            )
        console.print(table)
        return
    except (ImportError, AttributeError):
        pass

    # Fall back to direct REST
    data = _n8n_get(f"/api/v1/workflows/{workflow_id}")
    wf = data.get("data", data)

    table = Table(title=f"Workflow: {workflow_id}", header_style="bold cyan")
    table.add_column("Field", style="dim")
    table.add_column("Value")
    table.add_row("Name", str(wf.get("name", "Unknown")))
    table.add_row(
        "Active",
        "[green]Yes[/green]" if wf.get("active") else "[red]No[/red]",
    )
    table.add_row("Nodes", str(len(wf.get("nodes", []))))
    table.add_row("Created", str(wf.get("createdAt", "?")))
    table.add_row("Updated", str(wf.get("updatedAt", "?")))
    console.print(table)


# ---------------------------------------------------------------------------
# distro sub-commands
# ---------------------------------------------------------------------------

@distro_app.command("build")
def distro_build(
    description: Optional[str] = typer.Argument(
        None,
        help="Natural language description of the distro to build.",
    ),
    profile: Optional[str] = typer.Option(
        None, "--profile", help="Path to a .toml build profile."
    ),
    output: str = typer.Option(
        "./distro_output", "--output", "-o", help="Output directory for ISO artifacts."
    ),
    jobs: int = typer.Option(
        0, "--jobs", "-j", help="Parallel build jobs (0 = auto-detect)."
    ),
) -> None:
    """Build a custom Linux distribution ISO.

    Supply either a [bold]description[/bold] (natural language) or a
    [bold]--profile[/bold] (path to a .toml build profile file).

    [bold yellow]WARNING:[/bold yellow] This operation requires root privileges
    and substantial disk space (>=10 GB recommended).

    Examples:

        omni distro build "minimal Debian bookworm with i3 and Python 3.12"

        omni distro build --profile ~/profiles/developer.toml -o /mnt/iso
    """
    if not description and not profile:
        console.print(
            "[bold red]Error:[/bold red] Provide a description or --profile."
        )
        raise typer.Exit(1)

    # Check root privilege
    try:
        from omni_automator.security.path_validator import PathValidator
        PathValidator.check_root_required("distro build")
    except PermissionError as exc:
        console.print(f"[bold red]Permission error:[/bold red] {exc}")
        raise typer.Exit(1)
    except Exception:
        pass  # Non-fatal; skip root check on unsupported platforms

    # Load settings
    try:
        from omni_automator.config import get_settings
        settings = get_settings()
        work_dir = settings.distro_builder.work_dir
        build_jobs = jobs if jobs > 0 else (
            settings.distro_builder.default_jobs or os.cpu_count() or 4
        )
        debian_mirror = settings.distro_builder.debian_mirror
        debian_suite = settings.distro_builder.debian_suite
        require_confirm = settings.distro_builder.require_root_confirmation
    except Exception:
        work_dir = "/tmp/omni_distro_build"
        build_jobs = jobs if jobs > 0 else (os.cpu_count() or 4)
        debian_mirror = "http://deb.debian.org/debian"
        debian_suite = "bookworm"
        require_confirm = True

    # Safe-mode confirmation
    if require_confirm or _global_safe_mode:
        try:
            from omni_automator.security.path_validator import get_path_validator
            validator = get_path_validator()
            validator.safe_mode = True
            confirmed = validator.require_confirmation("distro build", output)
        except Exception:
            answer = console.input(
                "[yellow]Building a distro requires root and ~10 GB disk space. "
                "Continue? (yes/N): [/yellow]"
            ).strip().lower()
            confirmed = answer == "yes"

        if not confirmed:
            console.print("[yellow]Build cancelled by user.[/yellow]")
            raise typer.Exit(0)

    # Assemble build configuration dict
    build_config: dict = {
        "work_dir": work_dir,
        "output_dir": output,
        "jobs": build_jobs,
        "debian_mirror": debian_mirror,
        "debian_suite": debian_suite,
    }

    # Parse profile TOML if provided
    if profile:
        profile_path = Path(profile).expanduser().resolve()
        if not profile_path.exists():
            console.print(f"[bold red]Error:[/bold red] Profile not found: {profile_path}")
            raise typer.Exit(1)
        try:
            if sys.version_info >= (3, 11):
                import tomllib
            else:
                import tomli as tomllib  # type: ignore[no-redef]
            with open(profile_path, "rb") as fh:
                profile_data = tomllib.load(fh)
            build_config.update(profile_data)
            console.print(f"[dim]Loaded profile: {profile_path}[/dim]")
        except ImportError:
            console.print("[yellow]Warning: TOML library not available; profile not loaded.[/yellow]")
        except Exception as exc:
            console.print(f"[bold red]Profile parse error:[/bold red] {exc}")
            raise typer.Exit(1)

    if description:
        build_config["description"] = description

    console.print(
        Panel(
            f"[bold]Output:[/bold] {output}\n"
            f"[bold]Suite:[/bold] {build_config['debian_suite']}\n"
            f"[bold]Mirror:[/bold] {build_config['debian_mirror']}\n"
            f"[bold]Jobs:[/bold] {build_jobs}",
            title="[cyan]Distro Build Configuration[/cyan]",
            border_style="cyan",
        )
    )

    output_path = Path(output).expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    work_path = Path(work_dir).expanduser().resolve()
    work_path.mkdir(parents=True, exist_ok=True)

    # Try the dedicated distro_builder plugin
    try:
        from omni_automator.distro_builder.build_pipeline import (
            build_distro,
            build_from_nl,
        )
        from omni_automator.distro_builder.models import DistroProfile

        console.print("[bold yellow]Starting build — this will take a long time...[/bold yellow]")
        if profile and "description" not in build_config:
            dp = DistroProfile.model_validate(build_config)
            result = asyncio.run(build_distro(dp, output_path, jobs=build_jobs))
        else:
            result = asyncio.run(
                build_from_nl(build_config.get("description", ""), output_path)
            )

        if result.success:
            iso_path = getattr(result, "iso_path", str(output_path))
            console.print(
                Panel(
                    f"ISO written to [bold]{iso_path}[/bold]\n"
                    f"Build time: {getattr(result, 'build_time_seconds', '?')}s",
                    title="[green]Build Complete[/green]",
                    border_style="green",
                )
            )
        else:
            log_path = getattr(result, "log_path", "?")
            console.print(
                f"[bold red]Build failed.[/bold red] See log: {log_path}"
            )
            raise typer.Exit(1)

    except ImportError:
        # No dedicated distro_builder module — emit manual instructions
        _emit_debootstrap_instructions(build_config, output_path, work_path)


def _emit_debootstrap_instructions(
    cfg: dict, output_path: Path, work_path: Path
) -> None:
    """Print manual debootstrap steps when no distro-build plugin is available."""
    suite = cfg.get("debian_suite", "bookworm")
    mirror = cfg.get("debian_mirror", "http://deb.debian.org/debian")
    description = cfg.get("description", "custom Debian distro")

    console.print(
        Panel(
            f"[bold yellow]No built-in distro builder found.[/bold yellow]\n\n"
            f"To build [cyan]'{description}'[/cyan] manually, run:\n\n"
            f"  [bold]sudo debootstrap {suite} {work_path} {mirror}[/bold]\n\n"
            f"Then chroot, customise, and remaster into an ISO under:\n"
            f"  [bold]{output_path}[/bold]",
            title="Manual Build Instructions",
            border_style="yellow",
        )
    )


@distro_app.command("profiles")
def distro_profiles() -> None:
    """List available distro build profiles.

    Searches for [bold]*.toml[/bold] files in the default profile directories.
    """
    # Look in the dedicated distro_builder profiles directory first
    search_dirs = [
        Path(__file__).parent / "omni_automator" / "distro_builder" / "profiles",
        Path.home() / ".omniautomator" / "profiles",
        Path("/etc/omniautomator/profiles"),
        Path("./profiles"),
    ]

    found: list[Path] = []
    for directory in search_dirs:
        if directory.exists():
            found.extend(sorted(directory.glob("*.toml")))

    if not found:
        console.print(
            "[yellow]No profiles found.[/yellow]\n"
            "Place .toml profile files in one of these directories:"
        )
        for d in search_dirs:
            console.print(f"  • {d}")
        return

    table = Table(title="Available Distro Profiles", header_style="bold cyan")
    table.add_column("Name")
    table.add_column("Path", style="dim")
    table.add_column("Description")

    for path in found:
        description = "—"
        try:
            if sys.version_info >= (3, 11):
                import tomllib
            else:
                import tomli as tomllib  # type: ignore[no-redef]
            with open(path, "rb") as fh:
                data = tomllib.load(fh)
            description = data.get("description", "—")
        except Exception:
            pass
        table.add_row(path.stem, str(path), description)

    console.print(table)


@distro_app.command("estimate")
def distro_estimate(
    description: str = typer.Argument(
        ..., help="Natural language description of the distro to estimate."
    ),
) -> None:
    """Estimate build time and disk usage without actually building.

    Uses the AI model to analyse the description and produce rough estimates.
    Falls back to a heuristic estimate when AI is unavailable.
    """
    console.print(
        Panel(
            f"[bold]Description:[/bold] {description}",
            title="[cyan]Build Estimate[/cyan]",
            border_style="cyan",
        )
    )

    # Try the dedicated distro builder estimator first
    try:
        from omni_automator.distro_builder.build_pipeline import estimate_build_time
        from omni_automator.distro_builder.package_selector import nl_to_profile

        profile = nl_to_profile(description)
        estimate = estimate_build_time(profile)
        console.print(
            Panel(
                f"Estimated build time: [bold]{estimate}[/bold]",
                border_style="cyan",
            )
        )
        return
    except (ImportError, AttributeError):
        pass

    # AI-assisted estimate
    ai_text = ""
    engine = None
    try:
        from omni_automator.config import get_settings
        settings = get_settings()
        jobs_count = settings.distro_builder.default_jobs or os.cpu_count() or 4
    except Exception:
        jobs_count = os.cpu_count() or 4

    try:
        engine = _build_engine(debug=_global_debug)
        ai_result = engine.execute(
            f"estimate build time and disk usage for a custom Linux distro: {description}"
        )
        if isinstance(ai_result.get("result"), dict):
            ai_text = str(ai_result["result"].get("content", ""))
        elif isinstance(ai_result.get("result"), str):
            ai_text = ai_result["result"]
    except Exception:
        ai_text = ""
    finally:
        if engine:
            try:
                engine.shutdown()
            except Exception:
                pass

    if ai_text and ai_text.strip():
        console.print(Panel(ai_text.strip(), title="AI Estimate", border_style="cyan"))
        return

    # Heuristic fallback
    base_time = 20
    base_disk = 5
    for keyword in ["desktop", "gnome", "kde", "development", "server", "kernel", "xfce", "cuda"]:
        if keyword in description.lower():
            base_time += 10
            base_disk += 2

    adj_time = max(5, base_time // max(1, jobs_count // 2))

    table = Table(title="Heuristic Build Estimate", header_style="bold cyan")
    table.add_column("Parameter")
    table.add_column("Estimate")
    table.add_row(
        "Build time",
        f"~{adj_time}–{adj_time * 2} minutes ({jobs_count} jobs)",
    )
    table.add_row("Disk space", f"~{base_disk}–{base_disk + 3} GB")
    table.add_row("RAM required", "~2 GB minimum")
    table.add_row(
        "Note",
        "Rough estimate only; actual time depends on mirror speed and hardware.",
    )
    console.print(table)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(0)
