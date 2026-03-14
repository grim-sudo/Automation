"""Schema-validated AI response parser with JSON repair and markdown fence stripping."""

from __future__ import annotations

import ast
import json
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

__all__ = [
    # Pydantic models
    "ExecutionStep",
    "TaskPlan",
    "IntentResult",
    "AIResponse",
    "RiskAssessment",
    # Parser class
    "ResponseParser",
    # Module-level convenience functions (backward compat)
    "repair_and_parse",
    "parse_task_plan",
    "parse_intent_result",
]

# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json)?\s*", re.IGNORECASE)
_FENCE_END_RE = re.compile(r"```\s*$", re.MULTILINE)


# ---------------------------------------------------------------------------
# Pydantic v2 models
# ---------------------------------------------------------------------------


class ExecutionStep(BaseModel):
    """A single executable step within a task plan.

    Attributes:
        action:      Action identifier, e.g. ``"create_folder"``.
        category:    Routing category, e.g. ``"filesystem"``.
        params:      Free-form parameters passed to the plugin/adapter.
        description: Human-readable description for UI display.
        required:    If ``True`` and this step fails, the whole plan aborts.
        priority:    Lower number = executed first.
    """

    action: str
    category: str = Field(default="filesystem")
    params: dict[str, Any] = Field(default_factory=dict)
    description: str = Field(default="")
    required: bool = Field(default=True)
    priority: int = Field(default=0)

    @field_validator("action", "category")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("action and category must be non-empty strings")
        return v.strip().lower()


class RiskAssessment(BaseModel):
    """Risk assessment attached to a :class:`TaskPlan`.

    Attributes:
        level:       One of ``low | medium | high | critical``.
        concerns:    List of potential problem descriptions.
        mitigations: Suggested safety measures.
    """

    level: str = Field(default="medium")
    concerns: list[str] = Field(default_factory=list)
    mitigations: list[str] = Field(default_factory=list)

    @field_validator("level")
    @classmethod
    def _valid_level(cls, v: str) -> str:
        allowed = {"low", "medium", "high", "critical"}
        v = v.lower().strip()
        return v if v in allowed else "medium"


class TaskPlan(BaseModel):
    """A complete AI-generated task execution plan.

    All fields have safe defaults so ``model_validate()`` never raises when
    optional keys are absent from the AI response.

    Attributes:
        goal:               High-level description of what the plan achieves.
        steps:              Ordered list of :class:`ExecutionStep` objects.
        context:            Arbitrary key/value context captured by the AI.
        estimated_duration: Human-readable time estimate, e.g. ``"30 seconds"``.
    """

    goal: str = Field(default="")
    steps: list[ExecutionStep] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    estimated_duration: str = Field(default="unknown")

    # ── Backward-compat fields from the previous schema ──────────────────────
    original_request: str = Field(default="")
    interpreted_intent: str = Field(default="")
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    corrected_input: str = Field(default="")
    execution_steps: list[ExecutionStep] = Field(default_factory=list)
    risk_assessment: RiskAssessment = Field(default_factory=RiskAssessment)
    optimization_suggestions: list[str] = Field(default_factory=list)
    user_confirmations_needed: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalise_input(cls, data: Any) -> Any:
        """Accept alternative key names produced by different AI prompts."""
        if not isinstance(data, dict):
            return data
        # Merge "execution_steps" into "steps"
        if "execution_steps" in data and "steps" not in data:
            data["steps"] = data["execution_steps"]
        # Keep execution_steps in sync
        if "steps" in data and "execution_steps" not in data:
            data["execution_steps"] = data["steps"]
        # Legacy key aliases
        if "risks" in data and "risk_assessment" not in data:
            data["risk_assessment"] = data.pop("risks")
        if "optimizations" in data and "optimization_suggestions" not in data:
            data["optimization_suggestions"] = data.pop("optimizations")
        if "confidence" in data and "confidence_score" not in data:
            data["confidence_score"] = data.pop("confidence")
        if "intent" in data and "interpreted_intent" not in data:
            data["interpreted_intent"] = data.pop("intent")
        return data

    @model_validator(mode="after")
    def _sync_step_lists(self) -> TaskPlan:
        """Keep steps and execution_steps in sync after construction."""
        if self.steps and not self.execution_steps:
            object.__setattr__(self, "execution_steps", list(self.steps))
        elif self.execution_steps and not self.steps:
            object.__setattr__(self, "steps", list(self.execution_steps))
        return self

    @field_validator("confidence_score", mode="before")
    @classmethod
    def _clamp_confidence(cls, v: Any) -> float:
        try:
            return min(1.0, max(0.0, float(v)))
        except (TypeError, ValueError):
            return 0.5

    @classmethod
    def empty(cls, original_request: str = "") -> TaskPlan:
        """Return a minimal TaskPlan with no steps (safe fallback)."""
        return cls(
            original_request=original_request,
            goal=original_request,
            interpreted_intent="Could not parse AI response",
            confidence_score=0.1,
        )


class IntentResult(BaseModel):
    """The result of an intent-detection or command-enhancement call.

    Attributes:
        intent:           Short label for the detected intent.
        confidence:       0–1 confidence score.
        entities:         Named entities extracted from the command.
        parameters:       Resolved parameters for the intent.
        original_command: The raw user command string.
    """

    intent: str = Field(default="")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    entities: dict[str, Any] = Field(default_factory=dict)
    parameters: dict[str, Any] = Field(default_factory=dict)
    original_command: str = Field(default="")

    # ── Backward-compat extras used by openrouter_integration.py ─────────────
    enhanced_understanding: str = Field(default="")
    suggestions: list[str] = Field(default_factory=list)
    clarifications_needed: list[str] = Field(default_factory=list)
    enhanced: bool = Field(default=False)
    original: str = Field(default="")

    @field_validator("confidence", mode="before")
    @classmethod
    def _clamp(cls, v: Any) -> float:
        try:
            return min(1.0, max(0.0, float(v)))
        except (TypeError, ValueError):
            return 0.5


class AIResponse(BaseModel):
    """Wrapper around a complete AI provider response.

    Attributes:
        task_plan:   Parsed :class:`TaskPlan`, if the response contained one.
        intent:      Parsed :class:`IntentResult`, if applicable.
        raw_content: The raw text returned by the model.
        model_used:  The model identifier that produced the response.
        usage:       Token usage dict (prompt_tokens, completion_tokens, …).
    """

    task_plan: TaskPlan | None = Field(default=None)
    intent: IntentResult | None = Field(default=None)
    raw_content: str = Field(default="")
    model_used: str = Field(default="")
    usage: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# ResponseParser class
# ---------------------------------------------------------------------------


class ResponseParser:
    """Parse raw AI response strings into typed Pydantic models.

    Handles:
    - Markdown code-fence stripping (`` ```json … ``` ``)
    - First ``{…}`` block extraction
    - Single-quote → double-quote repair
    - Missing / trailing comma repair
    - Python literal (``None``, ``True``, ``False``) substitution
    - ``ast.literal_eval`` fallback

    Example::

        parser = ResponseParser()
        plan   = parser.parse_task_plan(raw_text)
        intent = parser.parse_intent(raw_text)
    """

    # ── Public methods ────────────────────────────────────────────────────────

    def parse_task_plan(self, raw: str, original_request: str = "") -> TaskPlan:
        """Parse *raw* AI text into a :class:`TaskPlan`.

        Args:
            raw:              Raw text from the AI response.
            original_request: Original user command (used in fallback objects).

        Returns:
            Validated :class:`TaskPlan` (never raises).
        """
        json_str = self._extract_json(raw)
        if not json_str:
            return TaskPlan.empty(original_request)

        try:
            data = json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            repaired = self._repair_json(json_str)
            try:
                data = json.loads(repaired)
            except (json.JSONDecodeError, ValueError):
                return TaskPlan.empty(original_request)

        if not isinstance(data, dict):
            return TaskPlan.empty(original_request)

        if original_request and not data.get("original_request"):
            data["original_request"] = original_request
        if original_request and not data.get("goal"):
            data["goal"] = original_request

        try:
            return TaskPlan.model_validate(data)
        except Exception:
            plan = TaskPlan.empty(original_request)
            # Salvage any steps that were present in the raw data
            raw_steps = data.get("steps") or data.get("execution_steps") or []
            if isinstance(raw_steps, list):
                salvaged: list[ExecutionStep] = []
                for s in raw_steps:
                    try:
                        salvaged.append(ExecutionStep.model_validate(s))
                    except Exception:
                        pass
                plan.steps = salvaged
                plan.execution_steps = salvaged
            return plan

    def parse_intent(self, raw: str, original_command: str = "") -> IntentResult:
        """Parse *raw* AI text into an :class:`IntentResult`.

        Args:
            raw:              Raw text from the AI response.
            original_command: Original user command.

        Returns:
            Validated :class:`IntentResult` (never raises).
        """
        json_str = self._extract_json(raw)
        if not json_str:
            return IntentResult(
                original_command=original_command, original=original_command
            )

        try:
            data = json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            repaired = self._repair_json(json_str)
            try:
                data = json.loads(repaired)
            except (json.JSONDecodeError, ValueError):
                return IntentResult(
                    original_command=original_command, original=original_command
                )

        if not isinstance(data, dict):
            return IntentResult(
                original_command=original_command, original=original_command
            )

        data.setdefault("original_command", original_command)
        data.setdefault("original", original_command)

        try:
            result = IntentResult.model_validate(data)
            result.enhanced = True
            return result
        except Exception:
            return IntentResult(
                original_command=original_command, original=original_command
            )

    # ── JSON extraction ───────────────────────────────────────────────────────

    def _extract_json(self, raw: str) -> str:
        """Extract a JSON string from *raw*, trying several strategies.

        Strategy order:

        1. Strip markdown fences (`` ```json … ``` ``).
        2. Try ``json.loads()`` on the stripped text directly.
        3. Find the first ``{…}`` block using brace-depth tracking.
        4. Fall back to the entire stripped text.

        Args:
            raw: String that should contain JSON somewhere.

        Returns:
            Best-candidate JSON string, or ``""`` if nothing found.
        """
        if not raw or not raw.strip():
            return ""

        # 1. Strip markdown fences
        stripped = _FENCE_RE.sub("", raw)
        stripped = _FENCE_END_RE.sub("", stripped).strip()

        # 2. Direct parse — return as-is if it already works
        try:
            json.loads(stripped)
            return stripped
        except (json.JSONDecodeError, ValueError):
            pass

        # 3. Find the first { … } block
        extracted = self._find_first_json_object(stripped)
        if extracted:
            return extracted

        # 4. Return the stripped text and let the caller try repairs
        return stripped

    def _find_first_json_object(self, text: str) -> str:
        """Return the substring spanning the first top-level ``{…}`` block.

        Correctly handles nested braces and string literals (including escaped
        characters).

        Args:
            text: Source text.

        Returns:
            The first complete JSON object, or ``""`` if not found.
        """
        start = text.find("{")
        if start == -1:
            return ""
        depth = 0
        in_str = False
        escape_next = False
        for i in range(start, len(text)):
            ch = text[i]
            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_str:
                escape_next = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start: i + 1]
        # Truncated object — return from start to end so the repair step
        # can attempt to close it.
        return text[start:] if depth > 0 else ""

    # ── JSON repair ───────────────────────────────────────────────────────────

    def _repair_json(self, raw: str) -> str:
        """Apply lightweight heuristic repairs to *raw* and return the result.

        Repairs attempted (in order):

        1. Replace Python ``None`` / ``True`` / ``False`` with JSON equivalents.
        2. Replace single-quoted string delimiters with double-quote ones.
        3. Insert missing commas between adjacent value tokens.
        4. Remove trailing commas before ``}`` or ``]``.
        5. Try ``ast.literal_eval`` as a bridge (handles more Python syntax).
        6. Close any unclosed braces/brackets.

        Args:
            raw: Potentially broken JSON-like string.

        Returns:
            Best-effort repaired JSON string.
        """
        if not raw:
            return raw

        text = raw.strip()

        # 1. Python literals → JSON literals
        text = re.sub(r'\bNone\b', 'null', text)
        text = re.sub(r'\bTrue\b', 'true', text)
        text = re.sub(r'\bFalse\b', 'false', text)

        # 2. Single-quoted strings → double-quoted
        text = re.sub(r"(?<![\\])'((?:[^'\\]|\\.)*)'", r'"\1"', text)

        # 3. Add missing commas between adjacent value-like tokens
        text = re.sub(
            r'([}\]"])\s*(\n\s*)([{\["a-zA-Z0-9_\-])', r'\1,\2\3', text
        )

        # 4. Remove trailing commas before closing delimiters
        text = re.sub(r',\s*([}\]])', r'\1', text)

        # 5. Try ast.literal_eval as a bridge
        try:
            evaluated = ast.literal_eval(text)
            return json.dumps(evaluated)
        except (ValueError, SyntaxError):
            pass

        # 6. Close unclosed structures
        open_braces = text.count('{') - text.count('}')
        open_brackets = text.count('[') - text.count(']')
        text = text.rstrip().rstrip(',')
        text += ']' * max(0, open_brackets)
        text += '}' * max(0, open_braces)

        return text


# ---------------------------------------------------------------------------
# Module-level convenience functions (backward compat with existing callers)
# ---------------------------------------------------------------------------

_default_parser = ResponseParser()


def repair_and_parse(raw: str) -> dict[str, Any] | None:
    """Extract and parse a JSON object from *raw* with repair fallbacks.

    Convenience wrapper around :class:`ResponseParser` for callers that just
    need a ``dict`` back without constructing the full Pydantic models.

    Args:
        raw: String that should contain JSON somewhere.

    Returns:
        Parsed dict, or ``None`` if all strategies failed.
    """
    if not raw or not raw.strip():
        return None

    json_str = _default_parser._extract_json(raw)
    if not json_str:
        return None

    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass

    repaired = _default_parser._repair_json(json_str)
    try:
        return json.loads(repaired)
    except (json.JSONDecodeError, ValueError):
        pass

    return None


def parse_task_plan(raw: str, original_request: str = "") -> TaskPlan:
    """Parse a raw AI response string into a :class:`TaskPlan`.

    Module-level convenience wrapper for :meth:`ResponseParser.parse_task_plan`.

    Args:
        raw:              Raw text from the AI response.
        original_request: Original user command.

    Returns:
        Validated :class:`TaskPlan` (never raises).
    """
    return _default_parser.parse_task_plan(raw, original_request=original_request)


def parse_intent_result(raw: str, original: str = "") -> IntentResult:
    """Parse a raw AI response string into an :class:`IntentResult`.

    Module-level convenience wrapper for :meth:`ResponseParser.parse_intent`.

    Args:
        raw:      Raw text from the AI response.
        original: Original user command.

    Returns:
        Validated :class:`IntentResult` (never raises).
    """
    return _default_parser.parse_intent(raw, original_command=original)
