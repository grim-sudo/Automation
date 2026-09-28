"""Shared glyph set for the TUI, chosen once at import.

Reuses the console theme's Unicode/ASCII detection (honouring ``ARCHON_ASCII``)
so the whole UI degrades together on terminals that cannot render the technical
glyph set.
"""

from __future__ import annotations

from ...theme import Glyphs, supports_unicode

GLYPHS: Glyphs = Glyphs.unicode() if supports_unicode() else Glyphs.ascii()

# Extra glyphs the TUI uses beyond the console set.
PENDING = "\u25cb" if supports_unicode() else "o"  # ○ not-yet-started
BAR_FULL = "\u2588" if supports_unicode() else "#"  # █
BAR_EMPTY = "\u2591" if supports_unicode() else "."  # ░

# Animated spinner frames for the "working" indicator, so a long, quiet model
# turn (hidden reasoning before any visible token) still shows visible motion.
SPINNER: tuple[str, ...] = (
    tuple("\u2839\u2838\u283c\u2834\u2826\u2827\u2807\u280f")  # ⠹⠸⠼⠴⠦⠧⠇⠏
    if supports_unicode()
    else ("|", "/", "-", "\\")
)
