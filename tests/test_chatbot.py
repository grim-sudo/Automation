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
