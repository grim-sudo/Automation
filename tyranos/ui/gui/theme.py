"""
Tyranos GUI Design System
Complete color palette, typography, and spacing constants.
"""

from __future__ import annotations

# ── Color Palette ─────────────────────────────────────────────────────────────

# Backgrounds
BG_DEEP = "#080810"          # Deep space black — main window bg
BG_SURFACE = "#0f0f1a"       # Card background
BG_RAISED = "#1a1a2e"        # Elevated cards, hover states
BG_HIGHLIGHT = "#16213e"     # Selected states

# Accent — Tyranos purple
PURPLE = "#7c3aed"
PURPLE_GLOW = "#7c3aed40"
PURPLE_LIGHT = "#a78bfa"
PURPLE_DIM = "#4c206d"
PURPLE_DARK = "#3b1d6e"

# Accent — Futuristic cyan
CYAN = "#06b6d4"
CYAN_GLOW = "#06b6d420"
CYAN_LIGHT = "#67e8f9"
CYAN_DIM = "#0891b2"

# Gradient endpoints
GRAD_START = PURPLE
GRAD_END = CYAN

# Semantic colors
SUCCESS = "#10b981"
SUCCESS_GLOW = "#10b98130"
WARNING = "#f59e0b"
WARNING_DIM = "#92400e"
ERROR = "#ef4444"
ERROR_GLOW = "#ef444430"
ERROR_DIM = "#7f1d1d"

# Typography
TEXT_PRIMARY = "#e2e8f0"
TEXT_SECONDARY = "#64748b"
TEXT_ACCENT = "#a78bfa"      # light purple highlights
TEXT_CYAN = "#67e8f9"
TEXT_MUTED = "#475569"
TEXT_WHITE = "#ffffff"

# Borders
BORDER_SUBTLE = "#1e1e3f"
BORDER_ACCENT = "#7c3aed60"
BORDER_CYAN = "#06b6d440"

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

# ── Sidebar dimensions ────────────────────────────────────────────────────────

SIDEBAR_EXPANDED = 240
SIDEBAR_COLLAPSED = 64
SIDEBAR_ANIM_MS = 200

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
    """Primary purple gradient button styling."""
    return {
        "fg_color": PURPLE,
        "hover_color": PURPLE_DIM,
        "text_color": TEXT_WHITE,
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
    """Accent/purple label."""
    return {"text_color": TEXT_ACCENT, "font": FONT_BODY}


def label_mono_kwargs() -> dict:
    """Monospace code label."""
    return {"text_color": TEXT_CYAN, "font": FONT_CODE}
