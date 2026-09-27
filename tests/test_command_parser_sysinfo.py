"""Tests for system-info query parsing.

Regression guard for the "Plugin 'unknown' not found" crash: system-info
queries like "show OS version" must route to system:get_info instead of
falling through to the unknown/unknown default.
"""

from __future__ import annotations

import pytest
from archon.parsers.command_parser import AdvancedCommandParser


@pytest.fixture
def parser() -> AdvancedCommandParser:
    return AdvancedCommandParser()


@pytest.mark.parametrize(
    "command",
    [
        "show OS version",
        "show system info",
        "what is my os",
        "which distro am i running",
        "kernel version",
        "system information",
    ],
)
def test_system_info_queries_route_to_get_info(
    parser: AdvancedCommandParser, command: str
) -> None:
    parsed = parser.parse(command)
    assert parsed["category"] == "system"
    assert parsed["action"] == "get_info"


def test_unrelated_command_not_misrouted_to_system(parser: AdvancedCommandParser) -> None:
    # A plain filesystem listing must NOT be swallowed by the system-info rule.
    parsed = parser.parse("list files")
    assert parsed["category"] == "filesystem"
    assert parsed["action"] == "list"
