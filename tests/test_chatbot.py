"""Tests for the interactive chatbot (``archon.ui.chatbot``).

Locks in the chatbot interaction contract: ``_process_automation_command``
drives the Ollama+MCP agent (:class:`~archon.mcp.agent.OllamaMCPAgent`) and
renders its reply, and the ``/model`` switcher lists/switches the local model.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from archon.ui.chatbot import ChatbotMode


class _FakeAgent:
    """Minimal stand-in for OllamaMCPAgent.run()."""

    def __init__(self, reply: str = "done", error: Exception | None = None) -> None:
        self._reply = reply
        self._error = error
        self.calls: list[str] = []

    async def run(self, message: str) -> str:
        self.calls.append(message)
        if self._error is not None:
            raise self._error
        return self._reply


def _bot_with_agent(agent: _FakeAgent) -> tuple[ChatbotMode, MagicMock]:
    engine = MagicMock()
    bot = ChatbotMode(engine=engine)
    bot._agent = agent  # inject so the lazy property returns it
    return bot, engine


def test_process_command_drives_agent():
    agent = _FakeAgent(reply="Created the folder.")
    bot, _ = _bot_with_agent(agent)

    bot._process_automation_command("create a folder named reports")

    assert agent.calls == ["create a folder named reports"]
    assert bot.user_context["last_operation"] == "create a folder named reports"


def test_agent_reply_recorded_in_history():
    agent = _FakeAgent(reply="All set.")
    bot, _ = _bot_with_agent(agent)

    bot._process_automation_command("do something")

    last = bot.conversation_history[-1]
    assert last["type"] == "bot"
    assert last["content"] == "All set."


def test_agent_exception_is_caught_not_raised():
    agent = _FakeAgent(error=RuntimeError("kaboom"))
    bot, _ = _bot_with_agent(agent)

    # Must not propagate — the session loop stays alive.
    bot._process_automation_command("create an error")

    # No successful operation recorded on failure.
    assert bot.user_context["last_operation"] is None


def test_lazy_engine_not_built_when_injected():
    engine = MagicMock()
    bot = ChatbotMode(engine=engine)
    # Accessing the property returns the injected engine, no rebuild.
    assert bot.engine is engine


def test_confirm_action_pauses_spinner_while_prompting():
    """The live 'Working' spinner must be stopped before prompting.

    A running rich Status owns the terminal and swallows input(), which left
    the session stuck with an unanswerable confirmation prompt.
    """
    from unittest.mock import call

    engine = MagicMock()
    bot = ChatbotMode(engine=engine)

    status = MagicMock()
    bot._status = status
    # Record ordering: stop must happen before the input prompt, start after.
    events: list[str] = []
    status.stop.side_effect = lambda: events.append("stop")
    status.start.side_effect = lambda: events.append("start")
    bot.console.input = MagicMock(
        side_effect=lambda *_a, **_k: events.append("input") or "yes"
    )

    approved = bot._confirm_action("run_automation", {"command": "rm -rf x"}, "DESTRUCTIVE")

    assert approved is True
    assert events == ["stop", "input", "start"]
    status.stop.assert_has_calls([call()])
    status.start.assert_has_calls([call()])


def test_confirm_action_without_spinner_still_prompts():
    """When no spinner is active the confirmer still prompts (no crash)."""
    engine = MagicMock()
    bot = ChatbotMode(engine=engine)
    bot._status = None
    bot.console.input = MagicMock(return_value="n")

    assert bot._confirm_action("dispatch_action", {}, "HIGH") is False


def test_confirm_requires_exact_yes_not_single_letter():
    """Phrase-match: a bare 'y' must NOT approve a risky action — only 'yes'.

    The typed confirmation is the safeguard for deletion/termination, so muscle
    memory 'y' should fall through to a cancel.
    """
    bot = ChatbotMode(engine=MagicMock())
    bot._status = None
    bot.console.input = MagicMock(return_value="y")
    assert bot._confirm_action("run_automation", {"command": "delete /x"}, "HIGH") is False

    bot.console.input = MagicMock(return_value="YES")  # case-insensitive
    assert bot._confirm_action("run_automation", {"command": "delete /x"}, "HIGH") is True


def test_short_collapses_whitespace_and_caps_length():
    assert ChatbotMode._short("a\n  b   c", 40) == "a b c"
    long = ChatbotMode._short("x" * 100, 20)
    assert len(long) == 20 and long.endswith("…")


def test_confirm_panel_titles_risk_and_lists_args():
    from rich.console import Console

    panel = ChatbotMode._confirm_panel(
        "run_automation", {"command": "rm -rf /tmp/x"}, "DESTRUCTIVE"
    )
    # Render to text so we assert on what the user actually sees.
    console = Console(width=80)
    with console.capture() as cap:
        console.print(panel)
    text = cap.get()
    assert "DESTRUCTIVE action — approve?" in text
    assert "run_automation" in text
    assert "rm -rf /tmp/x" in text


# ─── Model switcher (/model) ─────────────────────────────────────────────────


class _FakeAI:
    """Minimal stand-in for the local Ollama AI facade the switcher drives."""

    def __init__(self, models: dict[str, str], current: str, available: bool = True) -> None:
        self._models = models
        self._current = current
        self.is_available = available

    def get_available_models(self) -> dict[str, str]:
        return dict(self._models)

    def get_current_model(self) -> str:
        return self._current

    def set_model(self, model_id: str) -> bool:
        self._current = model_id
        return True


def _bot_with_ai(ai: _FakeAI) -> ChatbotMode:
    engine = MagicMock()
    engine.ai_parser.ai = ai
    # switch_ai_model is what the chatbot calls; route it to the facade.
    engine.switch_ai_model.side_effect = ai.set_model
    return ChatbotMode(engine=engine)


_MODELS = {"qwen3.5:9b": "qwen3.5:9b", "llama3:8b": "llama3:8b", "mistral:7b": "mistral:7b"}


def test_model_switch_by_number():
    ai = _FakeAI(_MODELS, current="qwen3.5:9b")
    bot = _bot_with_ai(ai)

    bot.handle_model("2")

    assert ai.get_current_model() == "llama3:8b"


def test_model_switch_by_id_substring():
    ai = _FakeAI(_MODELS, current="qwen3.5:9b")
    bot = _bot_with_ai(ai)

    bot.handle_model("mistral")  # unique substring

    assert ai.get_current_model() == "mistral:7b"


def test_model_switch_rejects_ambiguous_or_missing():
    ai = _FakeAI(_MODELS, current="qwen3.5:9b")
    bot = _bot_with_ai(ai)

    bot.handle_model(":")  # matches multiple → ambiguous, no change
    assert ai.get_current_model() == "qwen3.5:9b"

    bot.handle_model("nope")  # matches nothing → no change
    assert ai.get_current_model() == "qwen3.5:9b"


def test_model_switch_out_of_range_number_no_change():
    ai = _FakeAI(_MODELS, current="qwen3.5:9b")
    bot = _bot_with_ai(ai)

    bot.handle_model("99")

    assert ai.get_current_model() == "qwen3.5:9b"


def test_model_command_noop_when_ai_unavailable():
    ai = _FakeAI(_MODELS, current="qwen3.5:9b", available=False)
    bot = _bot_with_ai(ai)

    # Must not raise and must not switch.
    bot.handle_model("2")

    assert ai.get_current_model() == "qwen3.5:9b"


def test_resolve_model_choice_exact_id():
    models = list(_MODELS.items())
    assert ChatbotMode._resolve_model_choice("mistral:7b", models) == "mistral:7b"
    assert ChatbotMode._resolve_model_choice("1", models) == "qwen3.5:9b"
    assert ChatbotMode._resolve_model_choice("0", models) is None
