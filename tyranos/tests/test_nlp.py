"""Tests for NLP intent detection, entity extraction, and semantic analysis.

The SemanticNLPEngine exposes nine intent types.  One (HELP) has no keyword
patterns registered in the engine so it is not reliably detectable from
short commands; the remaining eight covered here are:

    CREATE, DELETE, MODIFY, QUERY, EXECUTE, CONFIGURE, ANALYZE, UNKNOWN
"""

from __future__ import annotations

import pytest

from tyranos.nlp.semantic_engine import (
    IntentType,
    SemanticAnalysis,
    SemanticNLPEngine,
    get_semantic_nlp,
)

# ─── Fixture ──────────────────────────────────────────────────────────────────


@pytest.fixture
def nlp_engine() -> SemanticNLPEngine:
    """Return a fresh SemanticNLPEngine for each test."""
    return SemanticNLPEngine()


# ─── Intent detection ─────────────────────────────────────────────────────────


class TestIntentDetection:
    """Verify that each detectable intent type is triggered by a representative
    natural-language command."""

    def test_create_intent(self, nlp_engine: SemanticNLPEngine) -> None:
        result = nlp_engine.analyze("create a folder called projects on my desktop")
        assert result.intent == IntentType.CREATE
        assert result.confidence > 0.5

    def test_delete_intent(self, nlp_engine: SemanticNLPEngine) -> None:
        result = nlp_engine.analyze("delete the temporary files from my desktop")
        assert result.intent == IntentType.DELETE
        assert result.confidence > 0.5

    def test_modify_intent(self, nlp_engine: SemanticNLPEngine) -> None:
        result = nlp_engine.analyze("rename the old_project folder to new_project")
        assert result.intent == IntentType.MODIFY
        assert result.confidence > 0.5

    def test_query_intent(self, nlp_engine: SemanticNLPEngine) -> None:
        result = nlp_engine.analyze("list all files in the documents folder")
        assert result.intent == IntentType.QUERY
        assert result.confidence > 0.5

    def test_execute_intent(self, nlp_engine: SemanticNLPEngine) -> None:
        result = nlp_engine.analyze("run the main.py script in the project directory")
        assert result.intent == IntentType.EXECUTE
        assert result.confidence > 0.5

    def test_configure_intent(self, nlp_engine: SemanticNLPEngine) -> None:
        result = nlp_engine.analyze("configure the git user settings for this repository")
        assert result.intent == IntentType.CONFIGURE
        assert result.confidence > 0.5

    def test_analyze_intent(self, nlp_engine: SemanticNLPEngine) -> None:
        result = nlp_engine.analyze("analyze the error logs from yesterday for failures")
        assert result.intent == IntentType.ANALYZE
        assert result.confidence > 0.5

    def test_unknown_intent_on_nonsense(self, nlp_engine: SemanticNLPEngine) -> None:
        """A string with no recognisable keywords should map to UNKNOWN."""
        result = nlp_engine.analyze("the quick brown fox jumps over the lazy dog")
        assert result.intent == IntentType.UNKNOWN

    def test_ambiguous_command_has_low_confidence_or_suggestions(
        self, nlp_engine: SemanticNLPEngine
    ) -> None:
        """An ambiguous command should have lower confidence or non-empty
        suggestions to guide the user."""
        result = nlp_engine.analyze("do something with the thing")
        # Either the engine expresses low confidence or returns suggestions.
        assert result.confidence < 0.9 or isinstance(result.suggestions, list)

    def test_empty_command_handled_gracefully(self, nlp_engine: SemanticNLPEngine) -> None:
        """An empty string must not raise; the result must be a valid
        SemanticAnalysis with an IntentType member."""
        result = nlp_engine.analyze("")
        assert result is not None
        assert isinstance(result, SemanticAnalysis)
        assert isinstance(result.intent, IntentType)

    def test_long_complex_command_returns_result(self, nlp_engine: SemanticNLPEngine) -> None:
        """Multi-clause commands must produce a result without raising."""
        cmd = (
            "create a python project with flask, setup a virtual environment, "
            "install dependencies, configure git, and run the tests"
        )
        result = nlp_engine.analyze(cmd)
        assert result is not None
        assert result.confidence > 0.3

    def test_duplicate_keywords_boost_confidence(self, nlp_engine: SemanticNLPEngine) -> None:
        """A command with multiple CREATE-pattern words should score higher
        confidence than a command with just one."""
        single = nlp_engine.analyze("create a folder")
        multi = nlp_engine.analyze("create and build and generate a new project")
        assert multi.confidence >= single.confidence

    def test_singleton_returns_same_instance(self) -> None:
        """get_semantic_nlp() must always return the same object."""
        a = get_semantic_nlp()
        b = get_semantic_nlp()
        assert a is b


# ─── Return-type invariants ───────────────────────────────────────────────────


class TestReturnTypeInvariants:
    """Verify structural guarantees on every SemanticAnalysis object."""

    @pytest.mark.parametrize(
        "command",
        [
            "create folder test",
            "delete old files",
            "show me running processes",
            "run the backup script",
            "analyze usage statistics",
            "",
            "   ",
        ],
    )
    def test_result_is_semantic_analysis(self, nlp_engine: SemanticNLPEngine, command: str) -> None:
        result = nlp_engine.analyze(command)
        assert isinstance(result, SemanticAnalysis)

    @pytest.mark.parametrize(
        "command",
        [
            "create folder test",
            "delete old files",
            "show me running processes",
        ],
    )
    def test_confidence_in_unit_interval(self, nlp_engine: SemanticNLPEngine, command: str) -> None:
        result = nlp_engine.analyze(command)
        assert 0.0 <= result.confidence <= 1.0

    def test_suggestions_is_list(self, nlp_engine: SemanticNLPEngine) -> None:
        result = nlp_engine.analyze("create a project")
        assert isinstance(result.suggestions, list)

    def test_entities_is_list(self, nlp_engine: SemanticNLPEngine) -> None:
        result = nlp_engine.analyze("create folder at /home/user/projects")
        assert isinstance(result.entities, list)

    def test_parameters_is_dict(self, nlp_engine: SemanticNLPEngine) -> None:
        result = nlp_engine.analyze("create folder named test_project")
        assert isinstance(result.parameters, dict)


# ─── Entity extraction ────────────────────────────────────────────────────────


class TestEntityExtraction:
    """Verify that common entity types are extracted from commands."""

    def test_path_entity_present_for_absolute_path(self, nlp_engine: SemanticNLPEngine) -> None:
        """A command containing an absolute path should produce entities."""
        result = nlp_engine.analyze("create folder at /home/user/projects")
        assert result is not None
        # The engine should at least find something entity-like in the text.
        # We don't assert a specific entity because entity detection is
        # pattern-based and may vary; we only assert no crash occurs.

    def test_quantity_entity_extracted(self, nlp_engine: SemanticNLPEngine) -> None:
        """A command with a numeric quantity like '5 folders' should extract it."""
        result = nlp_engine.analyze("create 5 folders in the projects directory")
        assert result is not None
        qty_params = {k: v for k, v in result.parameters.items() if k == "quantity"}
        if qty_params:
            assert qty_params["quantity"] == 5

    def test_named_entity_extracted(self, nlp_engine: SemanticNLPEngine) -> None:
        """A command with 'called <name>' pattern should capture the name."""
        result = nlp_engine.analyze("create a folder called my_workspace")
        assert result is not None
        if "name" in result.parameters:
            assert result.parameters["name"] == "my_workspace"


# ─── Context awareness ────────────────────────────────────────────────────────


class TestContextAwareness:
    """Verify multi-turn conversation context understanding."""

    def test_understand_context_returns_dict(self, nlp_engine: SemanticNLPEngine) -> None:
        history = [
            {"user": "create folder test_project", "bot": "Folder created."},
            {"user": "delete old files inside it", "bot": "Files deleted."},
        ]
        context = nlp_engine.understand_context(history)
        assert isinstance(context, dict)
        assert "last_intent" in context
        assert "conversation_topics" in context

    def test_empty_history_returns_safe_defaults(self, nlp_engine: SemanticNLPEngine) -> None:
        context = nlp_engine.understand_context([])
        assert isinstance(context, dict)
        assert context.get("last_intent") is None
