#!/usr/bin/env python3
"""
Interactive Chatbot Mode for Archon.

Multi-turn conversational shell that executes natural-language automation
commands through the real :class:`~archon.core.engine.Archon` engine and
renders results with Rich.  Line editing and history are provided by the
stdlib ``readline`` module when available.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..nlp.spell_corrector import get_spell_corrector
from ..utils.logger import get_logger
from ..workflow.error_handler import get_smart_error_handler

# Optional: readline gives history + arrow-key line editing for input().
# It is not available on stock Windows Python, so degrade gracefully.
try:  # pragma: no cover - platform dependent
    import readline
except ImportError:  # pragma: no cover
    readline = None  # type: ignore[assignment]

_HISTORY_PATH = Path.home() / ".archon" / "chatbot_history"


class ChatbotMode:
    """Interactive chatbot interface for Archon."""

    def __init__(self, engine: Any = None) -> None:
        self.logger = get_logger("ChatbotMode")
        self.console = Console()
        self.spell_corrector = get_spell_corrector()
        self.error_handler = get_smart_error_handler()

        # Engine is built lazily on first use so importing this module (e.g. for
        # the special-command handlers) stays cheap and offline.
        self._engine = engine

        # Conversation context
        self.conversation_history: list[dict[str, str]] = []
        self.user_context: dict[str, Any] = {
            "current_directory": os.getcwd(),
            "last_operation": None,
            "created_resources": [],
            "failed_operations": [],
            "preferences": {},
        }

        # Command handlers for slash-commands
        self.command_handlers = {
            "help": self.handle_help,
            "status": self.handle_status,
            "clear": self.handle_clear,
            "context": self.handle_context,
            "history": self.handle_history,
            "cd": self.handle_cd,
            "pwd": self.handle_pwd,
            "ls": self.handle_ls,
            "exit": self.handle_exit,
            "quit": self.handle_exit,
            "explain": self.handle_explain,
            "undo": self.handle_undo,
            "model": self.handle_model,
            "models": self.handle_model,
        }

    # ── Engine ──────────────────────────────────────────────────────────────

    @property
    def engine(self) -> Any:
        """Return the automation engine, building one on first access."""
        if self._engine is None:
            try:
                from archon._cli import _build_engine

                self._engine = _build_engine()
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.error(f"Failed to build engine: {exc}")
                from archon.core.engine import Archon

                self._engine = Archon()
        return self._engine

    # ── Session loop ──────────────────────────────────────────────────────────

    def start_interactive_session(self) -> None:
        """Start an interactive chatbot session."""
        self._print_banner()
        self._load_history()

        while True:
            try:
                user_input = self._get_user_input()

                if not user_input:
                    continue

                self.conversation_history.append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "type": "user",
                        "content": user_input,
                    }
                )

                if user_input.startswith("/"):
                    self._handle_special_command(user_input[1:])
                    continue

                self._process_automation_command(user_input)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupted. Type /exit to quit.[/yellow]")
            except EOFError:
                self._shutdown()
                break
            except Exception as exc:
                self.logger.error(f"Session error: {exc}")
                self.console.print(f"[bold red]Error:[/bold red] {exc}")
                self.console.print("[dim]Try /help for assistance.[/dim]")

    def _get_user_input(self) -> str:
        """Prompt for and return one line of user input."""
        indicator = "🤖" if self.user_context["last_operation"] else "💬"
        try:
            return self.console.input(f"\n{indicator} [bold cyan]You[/bold cyan] › ").strip()
        except EOFError:
            raise

    # ── Command execution ─────────────────────────────────────────────────────

    def _process_automation_command(self, command: str) -> None:
        """Route a natural-language message: chat answer or real execution."""
        # Spell-correct and surface the correction inline (non-blocking).
        corrected = self.spell_corrector.correct_text(command)
        if corrected != command:
            self.console.print(f"[dim]↳ interpreting as:[/dim] {corrected}")
            command = corrected

        # Build the conversational history the AI sees (user/assistant turns).
        history = [
            {"role": "user" if e["type"] == "user" else "assistant", "content": e["content"]}
            for e in self.conversation_history
            if e["type"] in ("user", "bot")
        ][:-1]  # drop the just-appended current turn

        with self.console.status(f"[cyan]Thinking:[/cyan] {command}", spinner="dots"):
            try:
                result = self.engine.chat(command, history)
            except Exception as exc:
                result = None
                self.logger.error(f"chat failed: {exc}")
                if self.error_handler:
                    self.error_handler.handle_error(str(exc), command)
                self.console.print(f"[bold red]Error:[/bold red] {exc}")

        reply_summary = command
        if result is not None:
            if result.get("kind") == "conversation":
                self.console.print(
                    Panel(result.get("reply", ""), border_style="cyan", title="[cyan]Archon[/cyan]")
                )
                reply_summary = result.get("reply", command)[:200]
            else:
                self._render_execution_result(result)
                self._update_context(command, result)
                reply_summary = f"Executed: {command}"

        self.conversation_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "type": "bot",
                "content": reply_summary,
            }
        )

    def _render_execution_result(self, result: dict) -> None:
        """Render an engine result dict with Rich."""
        if not isinstance(result, dict):
            self.console.print(str(result))
            return

        if not result.get("success", False):
            error = result.get("error", "Unknown error")
            self.console.print(
                Panel(f"[red]{error}[/red]", title="[red]Failed[/red]", border_style="red")
            )
            fallback = result.get("fallback_message", "")
            if fallback and fallback != error:
                self.console.print(f"[yellow]{fallback}[/yellow]")
            for suggestion in result.get("ai_suggestions", []):
                self.console.print(f"  [dim]•[/dim] {suggestion}")
            return

        inner = result.get("result")
        # Complex workflows carry a step breakdown; render it as a table.
        if isinstance(inner, dict) and "results" in inner:
            self._render_workflow(inner)
        elif isinstance(inner, dict) and inner:
            self._render_dict(inner)
        elif inner is not None and str(inner).strip():
            self.console.print(str(inner))
        else:
            self.console.print("[green]Done.[/green]")

    def _render_workflow(self, workflow: dict) -> None:
        """Render a multi-step workflow result as a table."""
        completed = workflow.get("completed_steps", 0)
        total = workflow.get("total_steps", 0)
        elapsed = workflow.get("total_execution_time", 0) or 0

        table = Table(
            title=f"{completed}/{total} steps completed  ·  {elapsed * 1000:.0f} ms",
            header_style="bold cyan",
        )
        table.add_column("#", justify="right", style="dim")
        table.add_column("Status")
        table.add_column("Action")
        table.add_column("Detail")

        for i, step in enumerate(workflow.get("results", []), 1):
            if not isinstance(step, dict):
                continue
            ok = step.get("success", False)
            status = "[green]OK[/green]" if ok else "[red]FAIL[/red]"
            action = str(step.get("action") or step.get("step_action") or "—")
            # The concrete plugin result is nested under "result".
            inner = step.get("result") if isinstance(step.get("result"), dict) else {}
            detail = str(
                step.get("created_item")
                or step.get("created_folder")
                or step.get("created_file")
                or inner.get("path")
                or inner.get("file_path")
                or inner.get("message")
                or step.get("details")
                or step.get("message")
                or step.get("error")
                or ""
            )[:80]
            table.add_row(str(i), status, action, detail)

        self.console.print(table)

    def _render_dict(self, data: dict) -> None:
        """Render a simple result dict as a key/value table."""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="cyan")
        table.add_column()
        for key, value in data.items():
            table.add_row(str(key), str(value)[:100])
        self.console.print(Panel(table, title="[green]Success[/green]", border_style="green"))

    def _update_context(self, command: str, result: dict) -> None:
        """Update conversation context from an execution result."""
        if not isinstance(result, dict):
            return
        if result.get("success"):
            self.user_context["last_operation"] = command
            inner = result.get("result")
            if isinstance(inner, dict):
                created = (
                    inner.get("created_item")
                    or inner.get("created_folder")
                    or inner.get("created_file")
                    or inner.get("file_path")
                    or inner.get("project_path")
                )
                if created:
                    self.user_context["created_resources"].append(str(created))
                for path in inner.get("files_created", []) or []:
                    self.user_context["created_resources"].append(str(path))
        else:
            self.user_context["failed_operations"].append(command)

    def _ask_confirmation(self, question: str, default_yes: bool = False) -> bool:
        """Ask a yes/no question; return the boolean answer."""
        suffix = "[Y/n]" if default_yes else "[y/N]"
        answer = self.console.input(f"{question} {suffix} ").strip().lower()
        if not answer:
            return default_yes
        return answer in ("yes", "y", "true")

    # ── Slash-command dispatch ──────────────────────────────────────────────────

    def _handle_special_command(self, command: str) -> None:
        """Dispatch a slash-command like ``/help`` or ``/cd path``."""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        handler = self.command_handlers.get(cmd)
        if handler:
            handler(args)
        else:
            self.console.print(f"[red]Unknown command:[/red] /{cmd}")
            self.console.print("[dim]Use /help for available commands.[/dim]")

    def handle_help(self, args: str = "") -> None:
        """Show help information."""
        self.console.print(
            Panel(self._help_body(), title="Help", border_style="cyan")
        )

    def handle_status(self, args: str = "") -> None:
        """Show current session status."""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="cyan")
        table.add_column()
        table.add_row("Current directory", self.user_context["current_directory"])
        table.add_row("Last operation", str(self.user_context["last_operation"] or "None"))
        table.add_row("Resources created", str(len(self.user_context["created_resources"])))
        table.add_row("Failed operations", str(len(self.user_context["failed_operations"])))
        table.add_row("Turns in history", str(len(self.conversation_history)))
        self.console.print(Panel(table, title="Status", border_style="cyan"))

    def handle_clear(self, args: str = "") -> None:
        """Clear the screen."""
        self.console.clear()
        self._print_banner()

    def handle_context(self, args: str = "") -> None:
        """Show the conversation context."""
        self.handle_status()

    def handle_history(self, args: str = "") -> None:
        """Show recent conversation history."""
        if not self.conversation_history:
            self.console.print("[dim](history empty)[/dim]")
            return
        table = Table(title="Recent history", header_style="bold cyan")
        table.add_column("#", justify="right", style="dim")
        table.add_column("Who")
        table.add_column("Message")
        for i, entry in enumerate(self.conversation_history[-15:], start=1):
            who = "You" if entry["type"] == "user" else "Archon"
            table.add_row(str(i), who, entry["content"][:70])
        self.console.print(table)

    def handle_cd(self, args: str = "") -> None:
        """Change the working directory."""
        if not args:
            self.console.print(os.getcwd())
            return
        target = os.path.expanduser(args)
        try:
            os.chdir(target)
            self.user_context["current_directory"] = os.getcwd()
            self.console.print(f"[green]→[/green] {os.getcwd()}")
        except FileNotFoundError:
            self.console.print(f"[red]Directory not found:[/red] {args}")
        except Exception as exc:
            self.console.print(f"[red]Error:[/red] {exc}")

    def handle_pwd(self, args: str = "") -> None:
        """Print the working directory."""
        self.console.print(os.getcwd())

    def handle_ls(self, args: str = "") -> None:
        """List directory contents."""
        directory = os.path.expanduser(args) if args else os.getcwd()
        try:
            items = sorted(os.listdir(directory))
        except FileNotFoundError:
            self.console.print(f"[red]Directory not found:[/red] {directory}")
            return
        except Exception as exc:
            self.console.print(f"[red]Error:[/red] {exc}")
            return

        for item in items[:40]:
            full = os.path.join(directory, item)
            if os.path.isdir(full):
                self.console.print(f"[blue]{item}/[/blue]")
            else:
                self.console.print(item)
        if len(items) > 40:
            self.console.print(f"[dim]… and {len(items) - 40} more[/dim]")

    def handle_exit(self, args: str = "") -> None:
        """Exit the chatbot."""
        self._shutdown()
        self.console.print("[cyan]Goodbye![/cyan]")
        import sys

        sys.exit(0)

    def handle_explain(self, args: str = "") -> None:
        """Explain the most recent command."""
        last_user_cmd = next(
            (e["content"] for e in reversed(self.conversation_history) if e["type"] == "user"),
            None,
        )
        if not last_user_cmd:
            self.console.print("[dim]No command to explain.[/dim]")
            return
        keywords = self.spell_corrector.extract_keywords(last_user_cmd)
        self.console.print(f"[bold]Explaining:[/bold] {last_user_cmd}")
        if keywords:
            for keyword, found_text in keywords.items():
                self.console.print(f"  [cyan]{keyword}[/cyan]: {found_text}")
        else:
            self.console.print("[dim]No recognised operations detected.[/dim]")

    def handle_undo(self, args: str = "") -> None:
        """Undo the last operation (not yet implemented)."""
        if self.user_context["last_operation"]:
            self.console.print(
                f"[yellow]Undo is not yet implemented "
                f"(last: {self.user_context['last_operation']}).[/yellow]"
            )
        else:
            self.console.print("[dim]Nothing to undo.[/dim]")

    # ── Model selection ─────────────────────────────────────────────────────────

    def _openrouter_ai(self) -> Any:
        """Return the live OpenRouter integration, or ``None`` when AI is off."""
        ai = getattr(getattr(self.engine, "ai_parser", None), "openrouter_ai", None)
        if ai is None or not ai.is_openrouter_available():
            return None
        return ai

    @staticmethod
    def _resolve_model_choice(arg: str, models: list[tuple[str, str]]) -> str | None:
        """Map a user argument to a model id.

        Accepts a 1-based menu number, an exact model id, or a case-insensitive
        substring of the id or display name. Returns ``None`` when nothing (or
        more than one thing, for substrings) unambiguously matches.
        """
        if arg.isdigit():
            idx = int(arg)
            return models[idx - 1][0] if 1 <= idx <= len(models) else None
        if arg in (mid for mid, _ in models):
            return arg
        needle = arg.lower()
        matches = [mid for mid, name in models if needle in mid.lower() or needle in name.lower()]
        return matches[0] if len(matches) == 1 else None

    def handle_model(self, args: str = "") -> None:
        """List the available free models and switch the active one.

        ``/model`` shows a numbered menu of the free OpenRouter models (best
        context first, current one marked) and prompts for a selection.
        ``/model <n|id|substring>`` switches directly without the menu.
        """
        ai = self._openrouter_ai()
        if ai is None:
            self.console.print(
                "[yellow]AI is not available — set OPENROUTER_API_KEY to enable "
                "model selection.[/yellow]"
            )
            return

        models = list(ai.get_available_models().items())  # (id, name), best-first
        if not models:
            self.console.print(
                "[yellow]No free models resolved. Check your API key and connection.[/yellow]"
            )
            return

        current = ai.get_current_model()

        # Direct switch when an argument is supplied.
        if args:
            chosen = self._resolve_model_choice(args.strip(), models)
            if chosen is None:
                self.console.print(f"[red]No single model matches:[/red] {args}")
                return
            ai.set_model(chosen)
            self.console.print(f"[green]✓ Model switched to[/green] {chosen}")
            return

        # Otherwise render the selection menu.
        table = Table(title="Free models (OpenRouter)", header_style="bold cyan")
        table.add_column("#", justify="right", style="dim")
        table.add_column("Model id")
        table.add_column("Name")
        table.add_column("", justify="center")
        for i, (mid, name) in enumerate(models, 1):
            marker = "[green]● current[/green]" if mid == current else ""
            table.add_row(str(i), mid, str(name)[:40], marker)
        self.console.print(table)

        try:
            answer = self.console.input(
                "\nSelect a model number (Enter to cancel) › "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            self.console.print("\n[dim]No change.[/dim]")
            return

        if not answer:
            self.console.print("[dim]No change.[/dim]")
            return
        if not answer.isdigit() or not (1 <= int(answer) <= len(models)):
            self.console.print(f"[red]Invalid selection:[/red] {answer}")
            return

        chosen_id = models[int(answer) - 1][0]
        if chosen_id == current:
            self.console.print(f"[dim]Already using[/dim] {chosen_id}")
            return
        ai.set_model(chosen_id)
        self.console.print(f"[green]✓ Model switched to[/green] {chosen_id}")

    # ── History persistence ─────────────────────────────────────────────────────

    def _load_history(self) -> None:
        """Load readline history from disk when available."""
        if readline is None:
            return
        try:
            _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            if _HISTORY_PATH.exists():
                readline.read_history_file(str(_HISTORY_PATH))
        except Exception:  # pragma: no cover - non-fatal
            pass

    def _save_history(self) -> None:
        """Persist readline history to disk when available."""
        if readline is None:
            return
        try:
            _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            readline.write_history_file(str(_HISTORY_PATH))
        except Exception:  # pragma: no cover - non-fatal
            pass

    def _shutdown(self) -> None:
        """Persist state and release engine resources."""
        self._save_history()
        if self._engine is not None:
            try:
                self._engine.shutdown()
            except Exception:  # pragma: no cover - defensive
                pass

    # ── Presentation ────────────────────────────────────────────────────────────

    def _print_banner(self) -> None:
        """Print the welcome banner."""
        self.console.print(
            Panel(
                "[bold cyan]Archon[/bold cyan] — Interactive Automation Assistant\n"
                "[dim]Type a command in plain English, or /help for slash-commands.[/dim]",
                border_style="cyan",
            )
        )

    def _help_body(self) -> str:
        """Return the help panel body text."""
        return (
            "[bold]Automation (type naturally):[/bold]\n"
            "  create a folder named reports on the Desktop\n"
            "  make a python project called scraper\n"
            "  generate a PDF titled Q3 Summary\n\n"
            "[bold]Slash-commands:[/bold]\n"
            "  [cyan]/help[/cyan]      Show this help\n"
            "  [cyan]/status[/cyan]    Session status\n"
            "  [cyan]/history[/cyan]   Recent commands\n"
            "  [cyan]/context[/cyan]   Conversation context\n"
            "  [cyan]/cd[/cyan] <path> Change directory\n"
            "  [cyan]/pwd[/cyan]       Print working directory\n"
            "  [cyan]/ls[/cyan] \\[path] List directory\n"
            "  [cyan]/explain[/cyan]   Explain the last command\n"
            "  [cyan]/undo[/cyan]      Undo last operation\n"
            "  [cyan]/model[/cyan] \\[n|id] List / switch the AI model\n"
            "  [cyan]/clear[/cyan]     Clear the screen\n"
            "  [cyan]/exit[/cyan]      Quit\n\n"
            "[dim]Spell-correction and multi-turn context are automatic.[/dim]"
        )


# Global instance
_chatbot_instance: ChatbotMode | None = None


def get_chatbot() -> ChatbotMode:
    """Get or create the global chatbot instance."""
    global _chatbot_instance
    if _chatbot_instance is None:
        _chatbot_instance = ChatbotMode()
    return _chatbot_instance
