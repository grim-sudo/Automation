"""Visual identity for Archon's terminal console.

A single source of truth for colours and glyphs so every renderer stays on the
same restrained, graphite/gold aesthetic. Colours are expressed as a
:class:`rich.theme.Theme` of named styles; glyphs degrade to plain ASCII on
terminals that cannot render the Unicode technical set.

This module is pure presentation config — it holds no state and touches no
engine internals.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

from rich.console import Console
from rich.theme import Theme

# ── Palette ───────────────────────────────────────────────────────────────────
# Warm metallic gold is the Archon identity accent; everything else is neutral
# graphite/gray so the gold and the sparse status colours carry all the signal.
_GOLD = "#d9a441"
_GOLD_DIM = "#8a6d3b"
_GRAPHITE = "#8a8f98"

ARCHON_THEME = Theme(
    {
        "archon.accent": f"bold {_GOLD}",
        "archon.accent.dim": _GOLD_DIM,
        "archon.text": "default",
        "archon.dim": _GRAPHITE,
        "archon.rule": _GOLD_DIM,
        "archon.user": "bold #b8bec9",
        # Subtle status colours — used only on state glyphs, never as decoration.
        "archon.ok": "#5fae7f",
        "archon.warn": "#d9a441",
        "archon.err": "#cc6666",
        "archon.run": _GRAPHITE,
    }
)


@dataclass(frozen=True)
class Glyphs:
    """Terminal glyph set with a Unicode and an ASCII incarnation."""

    brand: str
    running: str
    ok: str
    err: str
    online: str
    prompt: str
    rule: str

    @staticmethod
    def unicode() -> Glyphs:
        return Glyphs(
            brand="\u25c8",  # ◈
            running="\u25c7",  # ◇
            ok="\u2713",  # ✓
            err="!",
            online="\u25cf",  # ●
            prompt="\u203a",  # ›
            rule="\u2500",  # ─
        )

    @staticmethod
    def ascii() -> Glyphs:
        return Glyphs(
            brand="#",
            running="-",
            ok="+",
            err="!",
            online="*",
            prompt=">",
            rule="-",
        )


def supports_unicode(console: Console | None = None) -> bool:
    """Best-effort check that the terminal can render our technical glyphs.

    Honours an explicit ``ARCHON_ASCII=1`` override, then falls back to the
    stdout encoding and Rich's legacy-Windows flag.
    """
    if os.environ.get("ARCHON_ASCII"):
        return False
    if console is not None and getattr(console.options, "legacy_windows", False):
        return False
    encoding = (getattr(sys.stdout, "encoding", "") or "").lower()
    return "utf" in encoding


def make_console(**kwargs: object) -> Console:
    """Build a Console pre-loaded with the Archon theme."""
    return Console(theme=ARCHON_THEME, **kwargs)  # type: ignore[arg-type]


def glyphs_for(console: Console) -> Glyphs:
    """Return the appropriate glyph set for *console*."""
    return Glyphs.unicode() if supports_unicode(console) else Glyphs.ascii()
