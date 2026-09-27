"""Tests for OpenRouter chat-completion response parsing.

Covers the root cause behind the ``'NoneType' object has no attribute 'strip'``
crash: some models return ``content: null`` (reasoning models) or ``content`` as
a list of parts. ``_extract_message_text`` must tolerate all of these.
"""

from __future__ import annotations

from archon.ai.openrouter_integration import _extract_message_text


def test_null_content_returns_empty_string():
    # Reasoning models can return content: null — must not raise.
    assert _extract_message_text({"choices": [{"message": {"content": None}}]}) == ""


def test_plain_string_content_is_stripped():
    data = {"choices": [{"message": {"content": "  hello  "}}]}
    assert _extract_message_text(data) == "hello"


def test_list_content_parts_are_joined():
    data = {"choices": [{"message": {"content": [{"text": "a"}, {"text": "b"}]}}]}
    assert _extract_message_text(data) == "ab"


def test_missing_keys_return_empty_string():
    assert _extract_message_text({}) == ""
    assert _extract_message_text({"choices": []}) == ""
    assert _extract_message_text({"choices": [{}]}) == ""
