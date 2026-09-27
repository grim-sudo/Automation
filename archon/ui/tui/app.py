"""The Archon Textual application.

Running ``archon chatbot`` launches this: a full-screen terminal application
with a live system inspector, a scrollable conversation, a collapsible
execution view, a toggleable activity log, a persistent status bar and a
docked command input.

Architecture (the seam the spec asks for)::

    Archon Engine → AgentController → worker thread
                                         │  (real events, streamed tokens)
                                         ▼
                              Textual Messages → Widgets

The app owns *no* business logic. It drives :class:`AgentController` on a worker
thread and reacts to typed :mod:`~archon.ui.tui.events` messages. Widgets render
what they are handed; they never reach into the engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual import on, work
from textual.app import App, ComposeResult, SystemCommand
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen

from ...capabilities import RiskLevel
from ...utils.logger import get_logger
from . import events as ev
from .controller import AgentController
from .screens import ConfirmScreen, StartupScreen
from .sysinfo import SystemProbe
from .widgets import (
    ActivityLog,
    ArchonHeader,
    AssistantMessage,
    CommandInput,
    ErrorView,
    ExecutionView,
    Sidebar,
    StatusBar,
    SystemMessage,
    UserMessage,
)

_CSS_PATH = Path(__file__).with_name("app.tcss")


class ArchonApp(App[None]):
    """The full-screen Archon control-plane TUI."""

    CSS_PATH = _CSS_PATH
    TITLE = "Archon"

    BINDINGS = [
        ("ctrl+k", "command_palette", "Commands"),
        ("ctrl+l", "clear_conversation", "Clear"),
        ("ctrl+c", "cancel", "Cancel"),
        ("ctrl+d", "quit", "Exit"),
        ("ctrl+b", "toggle_sidebar", "Sidebar"),
        ("ctrl+j", "toggle_activity", "Activity"),
    ]

    def __init__(self, engine: Any = None) -> None:
        super().__init__()
        self.logger = get_logger("ArchonApp")
        self.controller = AgentController(engine=engine)
        self.probe = SystemProbe()
        self._gen = 0  # run generation; late messages from older runs are dropped
        self._busy = False
        self._current_assistant: AssistantMessage | None = None
        self._current_execution: ExecutionView | None = None

    # ── layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield ArchonHeader(id="header")
        with Horizontal(id="body"):
            with VerticalScroll(id="sidebar"):
                yield Sidebar(id="sidebar-body")
            with Vertical(id="content"):
                yield VerticalScroll(id="conversation")
                yield ActivityLog()
        yield StatusBar(id="status-bar")
        yield CommandInput()

    def on_mount(self) -> None:
        # Wire the controller's hooks to post typed messages from the worker.
        self.controller.on_event = self._forward_event
        self.controller.confirmer = self._confirm_from_thread

        self.query_one("#activity", ActivityLog).display = False  # hidden by default

        # Brief startup splash, then focus the input and start polling.
        self.push_screen(StartupScreen(self._startup_facts()))
        self.set_timer(1.6, self._dismiss_startup)

        self.query_one(CommandInput).focus()
        self._refresh_static_state()
        self.refresh_sysinfo()
        self.set_interval(2.0, self.refresh_sysinfo)
        self.set_interval(0.5, self._tick_execution)

    def _dismiss_startup(self) -> None:
        if isinstance(self.screen, StartupScreen):
            self.pop_screen()
        self.query_one(CommandInput).focus()

    # ── system commands (Ctrl+K palette) ───────────────────────────────────────

    def get_system_commands(self, screen: Screen):  # noqa: ANN201 - Textual type
        yield from super().get_system_commands(screen)
        yield SystemCommand("Clear conversation", "Empty the transcript", self.action_clear_conversation)
        yield SystemCommand("Toggle sidebar", "Show/hide the system inspector", self.action_toggle_sidebar)
        yield SystemCommand("Toggle activity", "Show/hide the activity log", self.action_toggle_activity)
        yield SystemCommand("Cancel operation", "Stop the current generation", self.action_cancel)
        yield SystemCommand("Exit Archon", "Quit the application", self.action_quit)

    # ── input ───────────────────────────────────────────────────────────────────

    @on(CommandInput.Submitted)
    def _on_submit(self, message: CommandInput.Submitted) -> None:
        if self._busy:
            return
        self._start_turn(message.value)

    def _start_turn(self, text: str) -> None:
        self._busy = True
        self._gen += 1
        gen = self._gen
        conv = self.query_one("#conversation", VerticalScroll)
        conv.mount(UserMessage(text))
        assistant = AssistantMessage()
        conv.mount(assistant)
        execution = ExecutionView()
        conv.mount(execution)
        self._current_assistant = assistant
        self._current_execution = execution
        conv.scroll_end(animate=False)

        self.query_one(StatusBar).state = "THINKING"
        self.query_one("#activity", ActivityLog).run("qwen generation")
        self._run_agent(text, gen)

    # ── worker: drive the agent off the UI thread ───────────────────────────────

    @work(thread=True, exclusive=True, group="agent")
    def _run_agent(self, text: str, gen: int) -> None:
        try:
            reply = self.controller.run(
                text,
                on_token=lambda t: self.post_message(ev.TokenReceived(gen, t)),
                on_stats=lambda s: self.post_message(ev.ModelStats(gen, s)),
            )
            self.post_message(ev.ReplyComplete(gen, reply))
        except Exception as exc:  # noqa: BLE001 - surface as a readable error
            self.logger.error(f"Agent run failed: {exc}")
            self.post_message(
                ev.RunFailed(
                    gen,
                    "The request could not be completed.",
                    reason=str(exc),
                    action="Check that Ollama is running, then try again.",
                )
            )

    def _forward_event(self, event: dict[str, Any]) -> None:
        """Adapt the agent's primitive event dicts into typed UI messages.

        Called from the worker thread; ``post_message`` is thread-safe.
        """
        gen = self._gen
        kind = event.get("kind")
        if kind == "phase":
            self.post_message(ev.PhaseChanged(gen, event.get("phase", "")))
        elif kind == "tool_start":
            self.post_message(
                ev.ToolStarted(gen, event.get("name", ""), event.get("args", {}))
            )
        elif kind == "tool_ok":
            self.post_message(ev.ToolOk(gen, event.get("name", "")))
        elif kind == "tool_error":
            self.post_message(
                ev.ToolError(gen, event.get("name", ""), event.get("error", ""))
            )

    def _confirm_from_thread(
        self, name: str, args: dict[str, Any], risk: RiskLevel
    ) -> bool:
        """Block the worker thread on a modal human decision."""
        prompt = f"Approve {risk.value}-risk action '{name}'?"
        detail = ", ".join(f"{k}={v}" for k, v in list(args.items())[:6])
        return bool(
            self.call_from_thread(self.push_screen_wait, ConfirmScreen(prompt, detail))
        )

    # ── message handlers ─────────────────────────────────────────────────────────

    @on(ev.TokenReceived)
    def _on_token(self, message: ev.TokenReceived) -> None:
        if message.gen != self._gen or self._current_assistant is None:
            return
        self._current_assistant.append_token(message.text)

    @on(ev.PhaseChanged)
    def _on_phase(self, message: ev.PhaseChanged) -> None:
        if message.gen != self._gen:
            return
        if message.phase == "EXECUTING" and self._current_assistant is not None:
            # Preliminary text before a tool round is not the final answer.
            self._current_assistant.reset_stream()
        self.query_one(StatusBar).state = message.phase or "THINKING"

    @on(ev.ToolStarted)
    def _on_tool_start(self, message: ev.ToolStarted) -> None:
        if message.gen != self._gen or self._current_execution is None:
            return
        self._current_execution.start_tool(message.name, message.args)
        self.query_one("#activity", ActivityLog).run(message.name)

    @on(ev.ToolOk)
    def _on_tool_ok(self, message: ev.ToolOk) -> None:
        if message.gen != self._gen or self._current_execution is None:
            return
        self._current_execution.finish_tool(message.name, ok=True)
        self.query_one("#activity", ActivityLog).ok(message.name)

    @on(ev.ToolError)
    def _on_tool_error(self, message: ev.ToolError) -> None:
        if message.gen != self._gen or self._current_execution is None:
            return
        self._current_execution.finish_tool(message.name, ok=False, error=message.error)
        self.query_one("#activity", ActivityLog).err(f"{message.name}: {message.error}")

    @on(ev.ModelStats)
    def _on_stats(self, message: ev.ModelStats) -> None:
        if message.gen != self._gen:
            return
        tps = message.stats.get("tokens_per_sec")
        if tps is not None:
            self._update_intel(tokens_per_sec=tps)

    @on(ev.ReplyComplete)
    def _on_reply(self, message: ev.ReplyComplete) -> None:
        if message.gen != self._gen:
            return
        if self._current_assistant is not None:
            self._current_assistant.finalize(message.reply)
        if self._current_execution is not None:
            self._current_execution.complete()
        self.query_one("#activity", ActivityLog).ok("response complete")
        self._end_turn()

    @on(ev.RunFailed)
    def _on_failed(self, message: ev.RunFailed) -> None:
        if message.gen != self._gen:
            return
        conv = self.query_one("#conversation", VerticalScroll)
        if self._current_execution is not None:
            self._current_execution.complete()
        conv.mount(ErrorView(message.summary, message.reason, message.action))
        conv.scroll_end(animate=False)
        self.query_one("#activity", ActivityLog).err(message.reason or message.summary)
        self._end_turn()

    def _end_turn(self) -> None:
        self._busy = False
        self.query_one(StatusBar).state = "READY"
        self._refresh_context()
        self.query_one("#conversation", VerticalScroll).scroll_end(animate=False)

    # ── periodic state refresh ────────────────────────────────────────────────────

    @work(thread=True, exclusive=True, group="sysinfo")
    def refresh_sysinfo(self) -> None:
        snapshot = self.probe.snapshot()
        self.post_message(ev.SysInfo(snapshot))

    @on(ev.SysInfo)
    def _on_sysinfo(self, message: ev.SysInfo) -> None:
        snap = message.snapshot
        self.query_one(Sidebar).update_state(snapshot=snap)
        header = self.query_one("#header", ArchonHeader)
        header.accelerator = snap.accelerator or "—"
        self.query_one(StatusBar).accelerator = snap.accelerator or "—"
        # Intelligence facts can flip online once the model's background probe
        # finishes, so refresh them on the same interval rather than once.
        self._refresh_intel()

    def _tick_execution(self) -> None:
        if self._current_execution is not None and self._busy:
            self._current_execution.tick()

    def _refresh_intel(self) -> None:
        """Refresh model/backend/online facts (cheap; safe to call on a timer)."""
        intel = self.controller.intelligence()
        header = self.query_one("#header", ArchonHeader)
        header.model = intel.get("model") or "—"
        header.backend = intel.get("backend") or "—"
        header.online = bool(intel.get("online"))
        self.query_one(StatusBar).model = intel.get("model") or "—"
        self.query_one(Sidebar).update_state(
            intel={"model": intel.get("model"), "backend": intel.get("backend")}
        )

    def _refresh_static_state(self) -> None:
        self._refresh_intel()
        status = self.query_one(StatusBar)
        status.plugins = self.controller.plugin_count()
        status.capabilities = self.controller.capability_count()
        self.query_one(Sidebar).update_state(
            archon={
                "plugins": self.controller.plugin_count(),
                "capabilities": self.controller.capability_count(),
                "state": "READY",
            },
        )
        self._refresh_context()

    def _update_intel(self, **fields: Any) -> None:
        self.query_one(Sidebar).update_state(intel=fields)

    def _refresh_context(self) -> None:
        used, window = self.controller.context_usage()
        self._update_intel(context_used=used, context_window=window)
        self.query_one(StatusBar).context = f"{used / 1000:.1f}K / {window / 1000:.0f}K"

    def _startup_facts(self) -> dict[str, Any]:
        intel = self.controller.intelligence()
        static = self.probe.static()
        backend = intel.get("backend")
        accel = "CUDA" if self.probe._nvidia_smi else "CPU"
        return {
            "system": static.get("os_name"),
            "model": intel.get("model"),
            "backend": f"{backend} / {accel}" if backend else None,
            "plugins": self.controller.plugin_count(),
            "online": bool(intel.get("online")),
        }

    # ── actions ───────────────────────────────────────────────────────────────────

    def action_clear_conversation(self) -> None:
        conv = self.query_one("#conversation", VerticalScroll)
        conv.remove_children()
        conv.mount(SystemMessage("Conversation cleared."))
        self._current_assistant = None
        self._current_execution = None

    def action_cancel(self) -> None:
        if not self._busy:
            return
        # Drop late messages from the cancelled run; the worker thread cannot be
        # force-killed mid-inference, so we detach from it and reset the UI.
        self._gen += 1
        self.workers.cancel_group(self, "agent")
        conv = self.query_one("#conversation", VerticalScroll)
        conv.mount(SystemMessage("Cancelled."))
        self.query_one("#activity", ActivityLog).err("cancelled")
        self._end_turn()

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar", VerticalScroll)
        sidebar.display = not sidebar.display

    def action_toggle_activity(self) -> None:
        activity = self.query_one("#activity", ActivityLog)
        activity.display = not activity.display

    def on_resize(self, event: Any) -> None:
        # Collapse the sidebar on narrow terminals so nothing overflows.
        narrow = self.size.width < 90
        sidebar = self.query_one("#sidebar", VerticalScroll)
        if narrow and sidebar.display:
            sidebar.display = False
        elif not narrow and not sidebar.display:
            sidebar.display = True

    def on_unmount(self) -> None:
        self.controller.shutdown()


def run_tui(engine: Any = None) -> None:
    """Launch the Archon TUI. Blocks until the user exits."""
    ArchonApp(engine=engine).run()
