"""Model Context Protocol (MCP) integration for Archon.

Exposes Archon's capability surface as MCP tools (:mod:`.server`) and drives a
local Ollama model against those tools with a confirmation gate for high-risk
actions (:mod:`.agent`).

FastMCP is an optional dependency (the ``mcp`` extra). Both submodules import
it at module load, so import them lazily and surface a clear install hint if it
is missing — see :func:`require_fastmcp`.
"""

from __future__ import annotations


def require_fastmcp() -> None:
    """Raise a friendly error when the optional ``fastmcp`` dep is absent."""
    try:
        import fastmcp  # noqa: F401
    except ImportError as exc:  # pragma: no cover - trivial guard
        raise ImportError(
            "MCP support needs FastMCP. Install it with:\n"
            "    pip install fastmcp\n"
            "or install Archon's MCP extra:\n"
            "    pip install 'archon[mcp]'"
        ) from exc


__all__ = ["require_fastmcp"]
