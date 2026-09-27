"""Tests for AI step normalization.

Regression guard for "Unknown filesystem action: create_directory": the model
emits synonymous action names (create_directory, create_plaintext_file, …) and
mixes param shapes (path vs name/location). ``_normalize_step`` must map both
onto the canonical contract the adapters and workflow engine implement, or a
task silently dies in the dispatch layer.
"""

from __future__ import annotations

import pytest
from archon.parsers.ai_parser import AIEnhancedParser


@pytest.fixture
def parser() -> AIEnhancedParser:
    # No API key needed: _normalize_step is pure and offline.
    return AIEnhancedParser(api_key=None)


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        ("create_directory", "create_folder"),
        ("make_directory", "create_folder"),
        ("mkdir", "create_folder"),
        ("create_plaintext_file", "create_file"),
        ("create_text_file", "create_file"),
        ("write_file", "create_file"),
        ("touch", "create_file"),
    ],
)
def test_filesystem_action_aliases_canonicalized(
    parser: AIEnhancedParser, action: str, expected: str
) -> None:
    got, _ = parser._normalize_step(action, "filesystem", {})
    assert got == expected


def test_path_split_into_name_and_location(parser: AIEnhancedParser) -> None:
    _, params = parser._normalize_step(
        "write_file", "filesystem", {"path": "/tmp/docs/bread.txt", "content": "hi"}
    )
    assert params["name"] == "bread.txt"
    assert params["location"] == "/tmp/docs"
    assert params["path"] == "/tmp/docs/bread.txt"  # original preserved
    assert params["content"] == "hi"


def test_name_and_location_compose_path(parser: AIEnhancedParser) -> None:
    _, params = parser._normalize_step(
        "create_file", "filesystem", {"name": "bread.txt", "location": "/tmp/docs"}
    )
    assert params["path"] == "/tmp/docs/bread.txt"


def test_non_filesystem_untouched(parser: AIEnhancedParser) -> None:
    # Other categories must pass through unchanged (no alias remap, no path split).
    action, params = parser._normalize_step(
        "create_word_document", "universal_automation", {"filename": "x.docx"}
    )
    assert action == "create_word_document"
    assert params == {"filename": "x.docx"}


def test_single_step_expands_to_one(parser: AIEnhancedParser) -> None:
    # Non-batch step: one unit in, one unit out, still normalized.
    expanded = parser._expand_step("create_directory", "filesystem", {"path": "bread"})
    assert len(expanded) == 1
    action, params = expanded[0]
    assert action == "create_folder"
    assert params["name"] == "bread"


def test_batch_directories_fan_out(parser: AIEnhancedParser) -> None:
    # "create 15 folders numbered 1-15 inside bread" arrives as one batch step.
    expanded = parser._expand_step(
        "create_directories",
        "filesystem",
        {"parent_directory": "bread", "directory_names": [str(n) for n in range(1, 16)]},
    )
    assert len(expanded) == 15
    for action, params in expanded:
        assert action == "create_folder"
        assert params["location"] == "bread"
    # First and last carry the right name + composed path.
    assert expanded[0][1]["name"] == "1"
    assert expanded[0][1]["path"] == "bread/1"
    assert expanded[-1][1]["name"] == "15"


def test_batch_files_fan_out_with_content(parser: AIEnhancedParser) -> None:
    # "a hi.txt in each with 'hello ... N'" arrives as one create_files step.
    expanded = parser._expand_step(
        "create_files",
        "filesystem",
        {
            "files": [
                {"path": "bread/1/hi.txt", "content": "hello this is the folder number 1"},
                {"path": "bread/2/hi.txt", "content": "hello this is the folder number 2"},
            ]
        },
    )
    assert len(expanded) == 2
    action, params = expanded[0]
    assert action == "create_file"
    assert params["name"] == "hi.txt"
    assert params["location"] == "bread/1"
    assert params["content"] == "hello this is the folder number 1"


def test_empty_batch_falls_through(parser: AIEnhancedParser) -> None:
    # A batch action with no items must not vanish — it stays a single step so
    # the invalid-action guard / fallback parser can decide what to do.
    expanded = parser._expand_step("create_files", "filesystem", {"files": []})
    assert len(expanded) == 1
