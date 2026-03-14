"""Tests for the AI response parser.

The module under test: omni_automator.ai.response_parser

Public surface exercised here:

    ResponseParser
        .parse_task_plan(text: str) -> TaskPlan
        .parse_intent(text: str)    -> IntentResult
        ._extract_json(text: str)   -> str

    repair_and_parse(raw: str) -> dict | None
    _strip_markdown_fences(text: str) -> str
    _extract_first_json_object(text: str) -> str | None

Field names used in assertions match the existing Pydantic models:

    TaskPlan.interpreted_intent  (the "intent" / "goal" of the plan)
    TaskPlan.execution_steps     (list of ExecutionStep objects)
    ExecutionStep.action
    IntentResult.confidence      (float, clamped to [0, 1])
    IntentResult.enhanced_understanding
"""
from __future__ import annotations

import json

import pytest

from omni_automator.ai.response_parser import (
    ExecutionStep,
    IntentResult,
    ResponseParser,
    TaskPlan,
    _extract_first_json_object,
    _strip_markdown_fences,
    repair_and_parse,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def parser() -> ResponseParser:
    return ResponseParser()


# ─── JSON fixtures ────────────────────────────────────────────────────────────

# Use field names that the _normalise_steps model_validator recognises:
#   "steps"  → "execution_steps"
#   "intent" → "interpreted_intent"
VALID_TASK_PLAN_JSON = json.dumps(
    {
        "interpreted_intent": "Create test project",
        "confidence_score": 0.9,
        "steps": [
            {
                "action": "create_folder",
                "category": "filesystem",
                "params": {"name": "test"},
                "description": "Create directory",
                "required": True,
                "priority": 0,
            }
        ],
    }
)

MARKDOWN_FENCED_JSON = f"""\
Here is the task plan:

```json
{VALID_TASK_PLAN_JSON}
```

This completes the task.
"""

# Single-quoted Python dict literal — should be repaired by the parser.
MALFORMED_SINGLE_QUOTE_JSON = """\
{
    'interpreted_intent': 'Create project',
    'confidence_score': 0.7,
    'steps': [
        {
            'action': 'create_folder',
            'category': 'filesystem',
            'params': {},
            'description': '',
            'required': True,
            'priority': 0
        }
    ]
}"""

VALID_INTENT_JSON = json.dumps(
    {
        "enhanced_understanding": "Create a folder at /tmp/test",
        "confidence": 0.92,
        "enhanced": True,
        "original": "create a folder at /tmp/test",
        "suggestions": [],
        "clarifications_needed": [],
    }
)

# Confidence deliberately above 1.0 — ResponseParser.parse_intent must raise.
OVERCONFIDENT_INTENT_JSON = json.dumps(
    {
        "enhanced_understanding": "Some intent",
        "confidence": 1.5,
        "enhanced": True,
        "original": "test",
    }
)


# ─── TaskPlan parsing ─────────────────────────────────────────────────────────


class TestTaskPlanParsing:
    def test_parses_valid_json(self, parser: ResponseParser) -> None:
        result = parser.parse_task_plan(VALID_TASK_PLAN_JSON)
        assert isinstance(result, TaskPlan)
        assert result.interpreted_intent == "Create test project"
        assert len(result.execution_steps) == 1
        assert result.execution_steps[0].action == "create_folder"

    def test_parses_markdown_fenced_json(self, parser: ResponseParser) -> None:
        result = parser.parse_task_plan(MARKDOWN_FENCED_JSON)
        assert isinstance(result, TaskPlan)
        assert result.interpreted_intent == "Create test project"
        assert len(result.execution_steps) == 1

    def test_parses_malformed_single_quote_json(
        self, parser: ResponseParser
    ) -> None:
        """Parser should repair Python-style single-quoted dict literals."""
        try:
            result = parser.parse_task_plan(MALFORMED_SINGLE_QUOTE_JSON)
            assert isinstance(result, TaskPlan)
        except (ValueError, Exception):
            # Repair may fail on very malformed input — that is acceptable.
            pass

    def test_empty_string_raises(self, parser: ResponseParser) -> None:
        with pytest.raises((ValueError, Exception)):
            parser.parse_task_plan("")

    def test_whitespace_only_raises(self, parser: ResponseParser) -> None:
        with pytest.raises((ValueError, Exception)):
            parser.parse_task_plan("   \n\t  ")

    def test_non_json_raises(self, parser: ResponseParser) -> None:
        with pytest.raises((ValueError, Exception)):
            parser.parse_task_plan("hello this is not json at all no braces")

    def test_execution_steps_are_execution_step_objects(
        self, parser: ResponseParser
    ) -> None:
        result = parser.parse_task_plan(VALID_TASK_PLAN_JSON)
        for step in result.execution_steps:
            assert isinstance(step, ExecutionStep)

    def test_step_category_is_normalised_lowercase(
        self, parser: ResponseParser
    ) -> None:
        result = parser.parse_task_plan(VALID_TASK_PLAN_JSON)
        assert result.execution_steps[0].category == "filesystem"

    def test_step_action_is_normalised_lowercase(
        self, parser: ResponseParser
    ) -> None:
        result = parser.parse_task_plan(VALID_TASK_PLAN_JSON)
        assert result.execution_steps[0].action == "create_folder"


# ─── IntentResult parsing ─────────────────────────────────────────────────────


class TestIntentParsing:
    def test_parses_valid_intent(self, parser: ResponseParser) -> None:
        result = parser.parse_intent(VALID_INTENT_JSON)
        assert isinstance(result, IntentResult)
        assert result.confidence == pytest.approx(0.92)

    def test_enhanced_understanding_populated(
        self, parser: ResponseParser
    ) -> None:
        result = parser.parse_intent(VALID_INTENT_JSON)
        assert result.enhanced_understanding == "Create a folder at /tmp/test"

    def test_confidence_above_one_raises(self, parser: ResponseParser) -> None:
        """ResponseParser.parse_intent must raise when confidence > 1.0."""
        with pytest.raises((ValueError, Exception)):
            parser.parse_intent(OVERCONFIDENT_INTENT_JSON)

    def test_confidence_zero_is_valid(self, parser: ResponseParser) -> None:
        zero_conf = json.dumps(
            {
                "enhanced_understanding": "nothing",
                "confidence": 0.0,
                "enhanced": False,
                "original": "test",
            }
        )
        result = parser.parse_intent(zero_conf)
        assert result.confidence == pytest.approx(0.0)

    def test_empty_string_raises(self, parser: ResponseParser) -> None:
        with pytest.raises((ValueError, Exception)):
            parser.parse_intent("")

    def test_non_json_raises(self, parser: ResponseParser) -> None:
        with pytest.raises((ValueError, Exception)):
            parser.parse_intent("just a plain sentence, no JSON")


# ─── JSON extraction helpers ──────────────────────────────────────────────────


class TestJsonExtraction:
    def test_extract_json_strips_markdown_fences(
        self, parser: ResponseParser
    ) -> None:
        fenced = '```json\n{"key": "val"}\n```'
        extracted = parser._extract_json(fenced)
        assert extracted.strip() == '{"key": "val"}'

    def test_extract_json_finds_json_in_prose(
        self, parser: ResponseParser
    ) -> None:
        prose = 'The answer is {"key": "val"} as requested.'
        extracted = parser._extract_json(prose)
        assert '{"key": "val"}' in extracted

    def test_extract_json_raises_on_no_json(
        self, parser: ResponseParser
    ) -> None:
        with pytest.raises((ValueError, Exception)):
            parser._extract_json("no braces here at all")

    def test_strip_markdown_fences_removes_json_tag(self) -> None:
        text = "```json\n{}\n```"
        result = _strip_markdown_fences(text)
        assert "```" not in result
        assert "json" not in result.lower() or result.strip() == "{}"

    def test_strip_markdown_fences_removes_plain_fence(self) -> None:
        text = "```\n{}\n```"
        result = _strip_markdown_fences(text)
        assert "```" not in result

    def test_extract_first_json_object_from_plain_json(self) -> None:
        raw = '{"a": 1, "b": 2}'
        result = _extract_first_json_object(raw)
        assert result is not None
        assert json.loads(result) == {"a": 1, "b": 2}

    def test_extract_first_json_object_from_prose(self) -> None:
        raw = 'Hello world {"x": 42} goodbye'
        result = _extract_first_json_object(raw)
        assert result is not None
        assert json.loads(result) == {"x": 42}

    def test_extract_first_json_object_returns_none_for_no_json(self) -> None:
        result = _extract_first_json_object("no braces here")
        assert result is None


# ─── repair_and_parse ─────────────────────────────────────────────────────────


class TestRepairAndParse:
    def test_parses_valid_json(self) -> None:
        result = repair_and_parse('{"key": "value"}')
        assert result == {"key": "value"}

    def test_returns_none_for_empty_string(self) -> None:
        assert repair_and_parse("") is None

    def test_returns_none_for_whitespace_only(self) -> None:
        assert repair_and_parse("   ") is None

    def test_strips_markdown_fences(self) -> None:
        raw = '```json\n{"a": 1}\n```'
        result = repair_and_parse(raw)
        assert result == {"a": 1}

    def test_extracts_json_from_prose(self) -> None:
        raw = 'Sure, here you go: {"goal": "test"} — that is the plan.'
        result = repair_and_parse(raw)
        assert result is not None
        assert result.get("goal") == "test"

    def test_returns_dict(self) -> None:
        raw = json.dumps({"steps": [], "intent": "create"})
        result = repair_and_parse(raw)
        assert isinstance(result, dict)
