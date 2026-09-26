"""
Archon GUI Design System
Complete color palette, typography, and spacing constants.
"""

from __future__ import annotations

# ── Color Palette — ARCHON "monument" command center ───────────────────────────
#
# A monumental JARVIS-style command deck: an obsidian-black void, gold as the
# hero accent (active nav, key actions, emphasis), a restrained steel/champagne
# highlight for live instrument readouts, and warm parchment text. Gold on black
# reads as engraved metal rather than neon — deliberate, weighty, monumental.
#
# NOTE: Tk/Tcl colors do not support an alpha channel — only #RGB, #RRGGBB, or
# #RRRRGGGGBBBB are valid. The "glow"/translucent accents below are therefore
# pre-blended over BG_DEEP (#0a0a0d) to emulate the intended transparency.

# Backgrounds — obsidian void, neutral-cool black (no navy tint)
BG_DEEP = "#0a0a0d"  # Obsidian void — main window bg
BG_SURFACE = "#131217"  # Panel / card background
BG_RAISED = "#1c1b22"  # Elevated cards, hover states
BG_HIGHLIGHT = "#272430"  # Selected states (faint warm tint)

# Primary accent — monumental gold (buttons, active nav, key actions).
# The historical names (PURPLE*) are kept so pages need no churn; the values
# now carry the gold "monument" identity.
PURPLE = "#d4af37"
PURPLE_GLOW = "#3c3317"  # 25% gold over BG_DEEP
PURPLE_LIGHT = "#e6c65c"
PURPLE_DIM = "#b8942a"  # hover
PURPLE_DARK = "#8a6d1f"

# Highlight accent — steel/champagne (glows, rings, code, live readouts).
# A cool counterpoint so instrument data reads apart from the gold.
CYAN = "#7fb8c6"
CYAN_GLOW = "#172025"  # 13% steel over BG_DEEP
CYAN_LIGHT = "#b6e0ea"
CYAN_DIM = "#4d8895"

# Status accent — bright emphasis gold (alerts / highlights above primary)
GOLD = "#ffc843"
GOLD_GLOW = "#282313"  # 15% gold over BG_DEEP
GOLD_DIM = "#a67c1c"

# Gradient endpoints (gold → champagne — a brushed-metal sweep)
GRAD_START = PURPLE
GRAD_END = PURPLE_LIGHT

# Semantic colors — retuned to sit on obsidian
SUCCESS = "#3fd99b"
SUCCESS_GLOW = "#103129"  # 18% success over BG_DEEP
WARNING = GOLD
WARNING_DIM = GOLD_DIM
ERROR = "#ff5c6e"
ERROR_GLOW = "#36171e"  # 18% error over BG_DEEP
ERROR_DIM = "#7f1d2e"

# Typography — warm parchment on obsidian
TEXT_PRIMARY = "#ece7db"
TEXT_SECONDARY = "#8a8574"
TEXT_ACCENT = "#e6c65c"  # gold-light highlights
TEXT_CYAN = "#b6e0ea"  # steel-light (code / readouts)
TEXT_MUTED = "#5c5850"
TEXT_WHITE = "#ffffff"

# Borders
BORDER_SUBTLE = "#201f26"
BORDER_ACCENT = "#5a4c1d"  # 40% gold over BG_DEEP (thin engraved rule)
BORDER_CYAN = "#27353b"  # 25% steel over BG_DEEP

# ── Semantic aliases ───────────────────────────────────────────────────────────
#
# The command-center redesign speaks in semantic tokens (bg / surface / accent /
# state colors) rather than raw palette names. These alias the palette above so
# new shell code reads cleanly while existing pages keep their historical names.
BG = BG_DEEP
SURFACE = BG_SURFACE
SURFACE_ALT = BG_RAISED
SELECTED = BG_HIGHLIGHT
BORDER = BORDER_SUBTLE

ACCENT = PURPLE  # single primary accent: active / selected / key actions
ACCENT_HOVER = PURPLE_DIM
INFO = CYAN  # informational readouts
# SUCCESS / WARNING / ERROR already defined above; DANGER is a spec-name alias.
DANGER = ERROR
DANGER_DIM = ERROR_DIM

TEXT_TERTIARY = TEXT_MUTED  # dim / disabled text

# ── Typography ─────────────────────────────────────────────────────────────────

FONT_FAMILY = "Inter"
FONT_FAMILY_MONO = "JetBrains Mono"

# Font tuples for CTk (family, size, weight)
FONT_DISPLAY = (FONT_FAMILY, 28, "bold")
FONT_HEADING = (FONT_FAMILY, 20, "bold")
FONT_SUBHEADING = (FONT_FAMILY, 16, "normal")
FONT_BODY = (FONT_FAMILY, 14, "normal")
FONT_BODY_BOLD = (FONT_FAMILY, 14, "bold")
FONT_SMALL = (FONT_FAMILY, 12, "normal")
FONT_MICRO = (FONT_FAMILY, 11, "normal")
FONT_CODE = (FONT_FAMILY_MONO, 13, "normal")
FONT_CODE_SMALL = (FONT_FAMILY_MONO, 11, "normal")

# ── Spacing (8px base unit) ───────────────────────────────────────────────────

SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 16
SPACE_LG = 24
SPACE_XL = 32
SPACE_2XL = 48

PAD_CARD = 20
PAD_PAGE = 28
GAP_SECTION = 24
GAP_ELEMENT = 12

# ── Border Radius ─────────────────────────────────────────────────────────────

RADIUS_CARD = 16
RADIUS_BTN = 10
RADIUS_INPUT = 8
RADIUS_BADGE = 20
RADIUS_SM = 6

# ── Shell dimensions ──────────────────────────────────────────────────────────

SIDEBAR_EXPANDED = 232
SIDEBAR_COLLAPSED = 60
SIDEBAR_ANIM_MS = 200

TOPBAR_HEIGHT = 52
STATUSBAR_HEIGHT = 28

# ── Animation durations (ms) ─────────────────────────────────────────────────

ANIM_FAST = 100
ANIM_NORMAL = 200
ANIM_SLOW = 300
ANIM_SPLASH = 1500

# ── Reusable CTk widget kwargs ────────────────────────────────────────────────


def card_kwargs(corner_radius: int = RADIUS_CARD) -> dict:
    """Standard card frame styling."""
    return {"fg_color": BG_SURFACE, "corner_radius": corner_radius}


def raised_card_kwargs(corner_radius: int = RADIUS_CARD) -> dict:
    """Elevated/hover card frame styling."""
    return {"fg_color": BG_RAISED, "corner_radius": corner_radius}


def btn_primary_kwargs() -> dict:
    """Primary gold button styling — dark engraved text on gold."""
    return {
        "fg_color": PURPLE,
        "hover_color": PURPLE_DIM,
        "text_color": BG_DEEP,
        "corner_radius": RADIUS_BTN,
        "font": FONT_BODY_BOLD,
    }


def btn_outline_kwargs() -> dict:
    """Outline/secondary button styling."""
    return {
        "fg_color": "transparent",
        "hover_color": BG_RAISED,
        "text_color": TEXT_ACCENT,
        "border_color": BORDER_ACCENT,
        "border_width": 1,
        "corner_radius": RADIUS_BTN,
        "font": FONT_BODY,
    }


def btn_ghost_kwargs() -> dict:
    """Ghost/tertiary button styling."""
    return {
        "fg_color": "transparent",
        "hover_color": BG_RAISED,
        "text_color": TEXT_SECONDARY,
        "corner_radius": RADIUS_BTN,
        "font": FONT_SMALL,
    }


def input_kwargs() -> dict:
    """Standard text input styling."""
    return {
        "fg_color": BG_RAISED,
        "border_color": BORDER_SUBTLE,
        "text_color": TEXT_PRIMARY,
        "placeholder_text_color": TEXT_MUTED,
        "corner_radius": RADIUS_INPUT,
        "font": FONT_BODY,
    }


def label_heading_kwargs() -> dict:
    """Section heading label."""
    return {"text_color": TEXT_PRIMARY, "font": FONT_HEADING}


def label_body_kwargs() -> dict:
    """Standard body label."""
    return {"text_color": TEXT_PRIMARY, "font": FONT_BODY}


def label_secondary_kwargs() -> dict:
    """Secondary/muted label."""
    return {"text_color": TEXT_SECONDARY, "font": FONT_SMALL}


def label_accent_kwargs() -> dict:
    """Accent/gold label."""
    return {"text_color": TEXT_ACCENT, "font": FONT_BODY}


def label_mono_kwargs() -> dict:
    """Monospace code label."""
    return {"text_color": TEXT_CYAN, "font": FONT_CODE}
