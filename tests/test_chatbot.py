"""Tests for the interactive chatbot (``archon.ui.chatbot``).

Locks in the chatbot interaction contract: ``_process_automation_command``
must dispatch through the engine's seamless ``chat()`` router (which decides
between a conversational answer and real execution) and render the result.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from archon.ui.chatbot import ChatbotMode


def _bot_with_engine(result: dict) -> tuple[ChatbotMode, MagicMock]:
    engine = MagicMock()
    # chat() is the seamless router; automation results carry kind="automation"
    # plus the full execute() payload.
    result = {"kind": "automation", **result}
    engine.chat.return_value = result
    bot = ChatbotMode(engine=engine)
    return bot, engine


def test_process_command_executes_through_engine():
    result = {"success": True, "result": {"message": "created"}, "command": "create a folder"}
    bot, engine = _bot_with_engine(result)

    bot._process_automation_command("create a folder named reports")

    engine.chat.assert_called_once()
    # Context is updated on success.
    assert bot.user_context["last_operation"] == "create a folder named reports"


def test_success_records_created_resource():
    result = {"success": True, "result": {"file_path": "/tmp/report.pdf"}}
    bot, _ = _bot_with_engine(result)

    bot._process_automation_command("create a pdf named report")

    assert "/tmp/report.pdf" in bot.user_context["created_resources"]


def test_failure_records_failed_operation():
    result = {"success": False, "error": "boom", "fallback_message": "try again"}
    bot, _ = _bot_with_engine(result)

    bot._process_automation_command("create a widget")

    assert "create a widget" in bot.user_context["failed_operations"]
    assert bot.user_context["last_operation"] is None


def test_conversational_message_renders_reply():
    engine = MagicMock()
    engine.chat.return_value = {
        "kind": "conversation",
        "success": True,
        "reply": "I can build operating systems, projects, and automations.",
    }
    bot = ChatbotMode(engine=engine)

    bot._process_automation_command("what can you build?")

    engine.chat.assert_called_once()
    # A conversational turn is not recorded as an executed operation.
    assert bot.user_context["last_operation"] is None
    assert bot.user_context["failed_operations"] == []


def test_engine_exception_is_caught_not_raised():
    engine = MagicMock()
    engine.chat.side_effect = RuntimeError("kaboom")
    bot = ChatbotMode(engine=engine)

    # Must not propagate — the session loop stays alive.
    bot._process_automation_command("create an error")

    assert bot.user_context["created_resources"] == []


def test_workflow_result_renders_without_error():
    result = {
        "success": True,
        "result": {
            "completed_steps": 2,
            "total_steps": 2,
            "total_execution_time": 0.01,
            "results": [
                {"success": True, "action": "create_folder", "created_folder": "/tmp/a"},
                {"success": True, "action": "create_folder", "created_folder": "/tmp/b"},
            ],
        },
    }
    bot, _ = _bot_with_engine(result)

    # Should render the step table without raising.
    bot._render_execution_result(result)


def test_lazy_engine_not_built_when_injected():
    engine = MagicMock()
    bot = ChatbotMode(engine=engine)
    # Accessing the property returns the injected engine, no rebuild.
    assert bot.engine is engine


# ─── Model switcher (/model) ─────────────────────────────────────────────────


class _FakeAI:
    """Minimal stand-in for the OpenRouter integration the switcher drives."""

    def __init__(self, models: dict[str, str], current: str, available: bool = True) -> None:
        self._models = models
        self._current = current
        self._available = available

    def is_openrouter_available(self) -> bool:
        return self._available

    def get_available_models(self) -> dict[str, str]:
        return dict(self._models)

    def get_current_model(self) -> str:
        return self._current

    def set_model(self, model_id: str) -> bool:
        self._current = model_id
        return True


def _bot_with_ai(ai: _FakeAI) -> ChatbotMode:
    engine = MagicMock()
    engine.ai_parser.openrouter_ai = ai
    return ChatbotMode(engine=engine)


_MODELS = {"prov/big:free": "Big", "prov/small:free": "Small", "prov/mid:free": "Mid"}


def test_model_switch_by_number():
    ai = _FakeAI(_MODELS, current="prov/big:free")
    bot = _bot_with_ai(ai)

    bot.handle_model("2")  # second entry, best-first order

    assert ai.get_current_model() == "prov/small:free"


def test_model_switch_by_id_substring():
    ai = _FakeAI(_MODELS, current="prov/big:free")
    bot = _bot_with_ai(ai)

    bot.handle_model("mid")  # unique substring

    assert ai.get_current_model() == "prov/mid:free"


def test_model_switch_rejects_ambiguous_or_missing():
    ai = _FakeAI(_MODELS, current="prov/big:free")
    bot = _bot_with_ai(ai)

    bot.handle_model("free")  # matches all three → ambiguous, no change
    assert ai.get_current_model() == "prov/big:free"

    bot.handle_model("nope")  # matches nothing → no change
    assert ai.get_current_model() == "prov/big:free"


def test_model_switch_out_of_range_number_no_change():
    ai = _FakeAI(_MODELS, current="prov/big:free")
    bot = _bot_with_ai(ai)

    bot.handle_model("99")

    assert ai.get_current_model() == "prov/big:free"


def test_model_command_noop_when_ai_unavailable():
    ai = _FakeAI(_MODELS, current="prov/big:free", available=False)
    bot = _bot_with_ai(ai)

    # Must not raise and must not switch.
    bot.handle_model("2")

    assert ai.get_current_model() == "prov/big:free"


def test_resolve_model_choice_exact_id():
    models = list(_MODELS.items())
    assert ChatbotMode._resolve_model_choice("prov/mid:free", models) == "prov/mid:free"
    assert ChatbotMode._resolve_model_choice("1", models) == "prov/big:free"
    assert ChatbotMode._resolve_model_choice("0", models) is None
