#!/usr/bin/env python3
"""Interactive console for Archon.

A polished, keyboard-first command console that drives a local Ollama model
against Archon's MCP tools (:class:`~archon.mcp.agent.OllamaMCPAgent`). The model
plans and calls tools autonomously; high-risk/destructive actions pause for
explicit confirmation. Real execution events stream into a live operational
view, replies render as Markdown, and errors read like sentences rather than
tracebacks.

Layering: this class is the presentation/input layer only. It composes three
collaborators — :class:`~archon.ui.renderer.Renderer` (draws),
:class:`~archon.ui.composer.Composer` (reads), and the agent (executes) — and
never reaches into engine business logic beyond the documented facade methods.
"""

from __future__ import annotations

import asyncio
import os
import platform
from datetime import datetime
from typing import Any

from rich.panel import Panel
from rich.table import Table

from ..nlp.spell_corrector import get_spell_corrector
from ..utils.logger import get_logger
from ..workflow.error_handler import get_smart_error_handler
from .composer import Composer
from .events import Channel, UIEvent, error, ok, phase, start
from .renderer import Renderer


class ChatbotMode:
    """Interactive console interface for Archon."""

    def __init__(self, engine: Any = None) -> None:
        self.logger = get_logger("ChatbotMode")
        self.renderer = Renderer()
        self.console = self.renderer.console  # kept for back-compat call sites
        self.spell_corrector = get_spell_corrector()
        self.error_handler = get_smart_error_handler()

        # Engine + agent are built lazily so importing this module stays cheap.
        self._engine = engine
        self._agent: Any = None

        # The live view (or a paused-capable stand-in) currently owning the
        # terminal; the confirmer pauses it before prompting. ``stop``/``start``
        # compatible so a rich Status, our OpsView, or a mock all work here.
        self._status: Any = None

        self.conversation_history: list[dict[str, str]] = []
        self.user_context: dict[str, Any] = {
            "current_directory": os.getcwd(),
            "last_operation": None,
            "created_resources": [],
            "failed_operations": [],
            "preferences": {},
        }

        self.command_handlers = {
            "help": self.handle_help,
            "status": self.handle_status,
            "clear": self.handle_clear,
            "context": self.handle_context,
            "history": self.handle_history,
            "plugins": self.handle_plugins,
            "config": self.handle_config,
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
        self._composer = Composer(commands=self.command_handlers.keys())

    # ── Engine / agent ──────────────────────────────────────────────────────

    @property
    def engine(self) -> Any:
        if self._engine is None:
            try:
                from archon._cli import _build_engine

                self._engine = _build_engine()
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.error(f"Failed to build engine: {exc}")
                from archon.core.engine import Archon

                self._engine = Archon()
        return self._engine

    @property
    def agent(self) -> Any:
        """Return the Ollama+MCP agent, building one on first access.

        Raises ``ImportError`` (surfaced to the caller) when the optional
        ``fastmcp`` dependency is missing.
        """
        if self._agent is None:
            from archon.mcp.agent import OllamaMCPAgent

            self._agent = OllamaMCPAgent(
                engine=self.engine,
                confirmer=self._confirm_action,
                on_event=self._on_agent_event,
            )
        return self._agent

    # ── Confirmation ──────────────────────────────────────────────────────────

    def _confirm_action(self, name: str, args: dict[str, Any], risk: Any) -> bool:
        """Confirmer for the agent: prompt before HIGH/DESTRUCTIVE actions.

        Pauses the live view while prompting; a running live display owns the
        terminal and would otherwise swallow the input prompt.
        """
        status = self._status
        if status is not None:
            status.stop()
        try:
            self.console.print(self._confirm_panel(name, args, risk))
            return self._ask_confirmation("Approve this action?", default_yes=False)
        finally:
            if status is not None:
                status.start()

    @staticmethod
    def _confirm_panel(name: str, args: dict[str, Any], risk: Any) -> Panel:
        """Build a readable approval panel: tool name plus a key/value table."""
        level = str(getattr(risk, "value", risk)).upper()
        # Standard colours (not the named archon.* theme) so the panel renders
        # on any Console, including callers that don't load the Archon theme.
        body = Table(show_header=False, box=None, padding=(0, 1))
        body.add_column(style="yellow", justify="right", no_wrap=True)
        body.add_column(overflow="fold")
        body.add_row("action", name)
        for key, value in (args or {}).items():
            body.add_row(key, str(value))
        return Panel(
            body,
            title=f"[bold red]{level} action — approve?[/bold red]",
            border_style="red",
        )

    def _ask_confirmation(self, question: str, default_yes: bool = False) -> bool:
        """Ask a yes/no question; return the boolean answer."""
        suffix = "[Y/n]" if default_yes else "[y/N]"
        answer = self.console.input(f"{question} {suffix} ").strip().lower()
        if not answer:
            return default_yes
        return answer in ("yes", "y", "true")

    # ── Live execution events ───────────────────────────────────────────────

    def _on_agent_event(self, event: dict[str, Any]) -> None:
        """Adapt the agent's primitive event dicts into the UI event model.

        Only *real* execution transitions arrive here; nothing is fabricated.
        """
        view = self._status
        if view is None or not hasattr(view, "handle"):
            return
        kind = event.get("kind")
        name = event.get("name", "")
        ui_event: UIEvent
        if kind == "phase":
            ui_event = phase(event.get("phase", "WORKING"), Channel.ARCHON)
        elif kind == "tool_start":
            ui_event = start(name, channel=Channel.ARCHON)
        elif kind == "tool_ok":
            ui_event = ok(name, channel=Channel.ARCHON)
        elif kind == "tool_error":
            ui_event = error(name, event.get("error", ""), channel=Channel.ARCHON)
        else:
            return
        view.handle(ui_event)

    # ── Session loop ──────────────────────────────────────────────────────────

    def start_interactive_session(self) -> None:
        """Start an interactive console session."""
        self._print_banner()

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
                self.renderer.note("Interrupted. Ctrl+D or /exit to quit.")
            except EOFError:
                self._shutdown()
                break
            except Exception as exc:
                self.logger.error(f"Session error: {exc}")
                self.renderer.error_block("Something went wrong.", reason=str(exc))

    def _get_user_input(self) -> str:
        """Prompt for and return one submission."""
        cwd = os.path.basename(os.getcwd()) or "/"
        # Truecolour gold arrow, dim cwd — matches the Rich theme accent.
        ansi = (
            f"\n\x1b[38;2;138;143;152m{cwd}\x1b[0m "
            f"\x1b[38;2;217;164;65m\u203a\x1b[0m "
        )
        return self._composer.prompt(ansi, plain_prompt=f"\n{cwd} > ")

    @staticmethod
    def _short(text: str, limit: int) -> str:
        """One-line, length-capped version of *text* for status labels."""
        flat = " ".join(text.split())
        return flat if len(flat) <= limit else flat[: limit - 1] + "…"

    # ── Command execution ─────────────────────────────────────────────────────

    def _process_automation_command(self, command: str) -> None:
        """Drive the Ollama+MCP agent for one message and render the reply."""
        corrected = self.spell_corrector.correct_text(command)
        if corrected != command:
            self.renderer.note(f"interpreting as: {corrected}")
            command = corrected

        self.renderer.user_turn(command)

        try:
            agent = self.agent
        except ImportError as exc:
            self.renderer.error_block(
                "MCP support is unavailable.",
                reason=str(exc),
                action="Install the MCP extra:  pip install 'archon[mcp]'",
            )
            return

        reply: str | None = None
        view = self.renderer.ops_view()
        with view:
            self._status = view
            try:
                reply = asyncio.run(agent.run(command))
            except Exception as exc:
                self.logger.error(f"agent run failed: {exc}")
                if self.error_handler:
                    self.error_handler.handle_error(str(exc), command)
                view.stop()
                self._render_run_error(exc)
            finally:
                self._status = None

        if reply is not None:
            self.renderer.assistant_turn(reply)
            self.user_context["last_operation"] = command

        self.conversation_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "type": "bot",
                "content": (reply or command)[:200],
            }
        )

    def _render_run_error(self, exc: Exception) -> None:
        """Turn an exception into a human-readable error block.

        The full traceback is preserved in the logging system (logged above);
        here the user sees a sentence and a next step.
        """
        message = str(exc)
        lowered = message.lower()
        action = ""
        if "ollama" in lowered or "connection" in lowered or "reach" in lowered:
            action = "Start the local model server:  ollama serve"
        elif "timwidth" in lowered or "timed out" in lowered:
            action = "The local model may be cold — try again in a moment."
        self.renderer.error_block(
            "Unable to complete that request.", reason=message, action=action
        )

    # ── Slash-command dispatch ──────────────────────────────────────────────────

    def _handle_special_command(self, command: str) -> None:
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        handler = self.command_handlers.get(cmd)
        if handler:
            handler(args)
        else:
            self.renderer.note(f"Unknown command: /{cmd}  —  /help for the list.")

    def handle_help(self, args: str = "") -> None:
        self.console.print(Panel(self._help_body(), title="Help", border_style="archon.rule"))

    def handle_status(self, args: str = "") -> None:
        ai = self._ollama_ai()
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="archon.dim")
        table.add_column()
        table.add_row("Model", ai.get_current_model() if ai else "offline")
        table.add_row("Backend", "Ollama" if ai else "—")
        table.add_row("Directory", self.user_context["current_directory"])
        table.add_row("Last operation", str(self.user_context["last_operation"] or "None"))
        table.add_row("Turns in history", str(len(self.conversation_history)))
        self.console.print(Panel(table, title="Status", border_style="archon.rule"))

    def handle_clear(self, args: str = "") -> None:
        self.console.clear()
        self._print_banner()

    def handle_context(self, args: str = "") -> None:
        self.handle_status()

    def handle_history(self, args: str = "") -> None:
        if not self.conversation_history:
            self.renderer.note("(history empty)")
            return
        table = Table(title="Recent history", header_style="archon.accent.dim")
        table.add_column("#", justify="right", style="archon.dim")
        table.add_column("Who")
        table.add_column("Message")
        for i, entry in enumerate(self.conversation_history[-15:], start=1):
            who = "You" if entry["type"] == "user" else "Archon"
            table.add_row(str(i), who, entry["content"][:70])
        self.console.print(table)

    def handle_plugins(self, args: str = "") -> None:
        """List the loaded automation plugins (real, from the plugin manager)."""
        try:
            plugins = self.engine.plugin_manager.get_available_plugins()
        except Exception as exc:
            self.renderer.note(f"Could not read plugins: {exc}")
            return
        if not plugins:
            self.renderer.note("(no plugins loaded)")
            return
        table = Table(title="Loaded plugins", header_style="archon.accent.dim")
        table.add_column("Plugin")
        table.add_column("Version", style="archon.dim")
        table.add_column("Capabilities", justify="right", style="archon.dim")
        for name, meta in plugins.items():
            table.add_row(
                name,
                str(meta.get("version", "?")),
                str(len(meta.get("capabilities", []))),
            )
        self.console.print(table)

    def handle_config(self, args: str = "") -> None:
        """Show the effective config source and key AI settings (real values)."""
        from pathlib import Path

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="archon.dim")
        table.add_column()
        table.add_row("Config dir", str(Path.home() / ".archon"))
        ai = self._ollama_ai()
        if ai is not None:
            status = ai.get_ai_status()
            table.add_row("Model", str(status.get("model")))
            table.add_row("Backend", str(status.get("provider")))
            table.add_row("URL", str(status.get("url")))
        else:
            table.add_row("AI", "offline")
        self.console.print(Panel(table, title="Config", border_style="archon.rule"))

    def handle_cd(self, args: str = "") -> None:
        if not args:
            self.console.print(os.getcwd())
            return
        target = os.path.expanduser(args)
        try:
            os.chdir(target)
            self.user_context["current_directory"] = os.getcwd()
            self.renderer.note(f"→ {os.getcwd()}")
        except FileNotFoundError:
            self.renderer.note(f"Directory not found: {args}")
        except Exception as exc:
            self.renderer.note(f"Error: {exc}")

    def handle_pwd(self, args: str = "") -> None:
        self.console.print(os.getcwd())

    def handle_ls(self, args: str = "") -> None:
        directory = os.path.expanduser(args) if args else os.getcwd()
        try:
            items = sorted(os.listdir(directory))
        except FileNotFoundError:
            self.renderer.note(f"Directory not found: {directory}")
            return
        except Exception as exc:
            self.renderer.note(f"Error: {exc}")
            return
        for item in items[:40]:
            full = os.path.join(directory, item)
            suffix = "/" if os.path.isdir(full) else ""
            self.console.print(f"{item}{suffix}")
        if len(items) > 40:
            self.renderer.note(f"… and {len(items) - 40} more")

    def handle_exit(self, args: str = "") -> None:
        self._shutdown()
        self.renderer.note("Goodbye.")
        import sys

        sys.exit(0)

    def handle_explain(self, args: str = "") -> None:
        last_user_cmd = next(
            (e["content"] for e in reversed(self.conversation_history) if e["type"] == "user"),
            None,
        )
        if not last_user_cmd:
            self.renderer.note("No command to explain.")
            return
        keywords = self.spell_corrector.extract_keywords(last_user_cmd)
        self.console.print(f"[archon.dim]Explaining:[/archon.dim] {last_user_cmd}")
        if keywords:
            for keyword, found_text in keywords.items():
                self.console.print(f"  [archon.accent.dim]{keyword}[/archon.accent.dim]: {found_text}")
        else:
            self.renderer.note("No recognised operations detected.")

    def handle_undo(self, args: str = "") -> None:
        if self.user_context["last_operation"]:
            self.renderer.note(
                f"Undo is not yet implemented (last: {self.user_context['last_operation']})."
            )
        else:
            self.renderer.note("Nothing to undo.")

    # ── Model selection ─────────────────────────────────────────────────────────

    def _ollama_ai(self) -> Any:
        """Return the live Ollama AI facade, or ``None`` when AI is off."""
        ai = getattr(getattr(self.engine, "ai_parser", None), "ai", None)
        if ai is None or not ai.is_available:
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
        """List the installed Ollama models and switch the active one."""
        ai = self._ollama_ai()
        if ai is None:
            self.renderer.note(
                "AI is not available — start the local Ollama server "
                "('ollama serve') to enable model selection."
            )
            return

        models = list(ai.get_available_models().items())  # (id, name)
        if not models:
            self.renderer.note("No models installed. Pull one with 'ollama pull qwen3.5:9b'.")
            return

        current = ai.get_current_model()

        if args:
            chosen = self._resolve_model_choice(args.strip(), models)
            if chosen is None:
                self.renderer.note(f"No single model matches: {args}")
                return
            self._switch_model(chosen)
            return

        table = Table(title="Installed Ollama models", header_style="archon.accent.dim")
        table.add_column("#", justify="right", style="archon.dim")
        table.add_column("Model id")
        table.add_column("", justify="center")
        for i, (mid, _name) in enumerate(models, 1):
            marker = "[archon.ok]● current[/archon.ok]" if mid == current else ""
            table.add_row(str(i), mid, marker)
        self.console.print(table)

        try:
            answer = self.console.input("\nSelect a model number (Enter to cancel) › ").strip()
        except (EOFError, KeyboardInterrupt):
            self.renderer.note("No change.")
            return

        if not answer:
            self.renderer.note("No change.")
            return
        if not answer.isdigit() or not (1 <= int(answer) <= len(models)):
            self.renderer.note(f"Invalid selection: {answer}")
            return

        chosen_id = models[int(answer) - 1][0]
        if chosen_id == current:
            self.renderer.note(f"Already using {chosen_id}")
            return
        self._switch_model(chosen_id)

    def _switch_model(self, model_id: str) -> None:
        """Switch the active model on both the engine facade and the agent."""
        self.engine.switch_ai_model(model_id)
        self._agent = None  # rebuild so the provider picks up the new model
        self.renderer.note(f"✓ Model switched to {model_id}")

    # ── Shutdown ─────────────────────────────────────────────────────────────

    def _shutdown(self) -> None:
        """Release engine resources (history persists via the composer)."""
        if self._engine is not None:
            try:
                self._engine.shutdown()
            except Exception:  # pragma: no cover - defensive
                pass

    # ── Presentation ────────────────────────────────────────────────────────────

    def _system_info(self) -> dict[str, str]:
        """Gather real startup facts for the banner (no fabrication)."""
        ai = self._ollama_ai()
        model = ai.get_current_model() if ai is not None else "offline"
        try:
            plugins = len(self.engine.plugin_manager.get_available_plugins())
        except Exception:
            plugins = 0
        return {
            "system": _distro_name(),
            "model": model,
            "backend": "Ollama" if ai is not None else "—",
            "plugins": f"{plugins} active" if plugins else "0",
            "status": "ONLINE" if ai is not None else "OFFLINE",
        }

    def _print_banner(self) -> None:
        self.renderer.startup(self._system_info())

    def _help_body(self) -> str:
        return (
            "[archon.accent.dim]Type naturally[/archon.accent.dim] — a local model plans and runs the tools:\n"
            "  create a folder named reports on the Desktop\n"
            "  build a minimal Arch ISO with python and git\n\n"
            "[archon.accent.dim]Commands[/archon.accent.dim]\n"
            "  /help      Show this help\n"
            "  /status    Model + session status\n"
            "  /model     List / switch the Ollama model\n"
            "  /plugins   List loaded plugins\n"
            "  /config    Show config + AI settings\n"
            "  /history   Recent messages\n"
            "  /cd <path> Change directory\n"
            "  /pwd       Print working directory\n"
            "  /ls [path] List a directory\n"
            "  /explain   Explain the last command\n"
            "  /clear     Redraw the console\n"
            "  /exit      Quit (or Ctrl+D)\n\n"
            "[archon.dim]Enter sends • Alt+Enter for a new line • ↑/↓ history • Ctrl+C interrupts[/archon.dim]"
        )


def _distro_name() -> str:
    """Return a friendly OS name (PRETTY_NAME on Linux, else platform.system)."""
    if platform.system() == "Linux":
        try:
            with open("/etc/os-release", encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip().strip('"')
        except OSError:
            pass
    return platform.system() or "Unknown"


# Global instance
_chatbot_instance: ChatbotMode | None = None


def get_chatbot() -> ChatbotMode:
    """Get or create the global chatbot instance."""
    global _chatbot_instance
    if _chatbot_instance is None:
        _chatbot_instance = ChatbotMode()
    return _chatbot_instance
