"""
Archon GUI Design System
Complete color palette, typography, and spacing constants.
"""

from __future__ import annotations

# ── Color Palette — ARCHON command center ──────────────────────────────────────
#
# A premium computing-control plane: black metal + brushed steel + warm gold.
# The material stack runs void → obsidian → charcoal → graphite → steel → iron,
# with gold reserved strictly for active / selected / executing / primary
# actions. Roughly 85% dark surfaces, 10% neutral metal, 5% accent + state.
#
# NOTE: Tk/Tcl colors have no alpha channel — only #RGB, #RRGGBB, #RRRRGGGGBBBB
# are valid. "Glow" tokens are pre-blended over the obsidian base to emulate
# translucency.

# ── Material stack (spec names) ───────────────────────────────────────────────
VOID = "#050607"  # deepest black — full-bleed backdrops
OBSIDIAN = "#090b0d"  # main window background
CHARCOAL = "#0e1114"  # panels / surfaces
GRAPHITE = "#14181c"  # elevated surfaces, hover
STEEL = "#1c2227"  # selected / raised instrument
IRON = "#252c32"  # top material — chips, strong hover

# Backgrounds — historical names mapped onto the material stack.
BG_DEEP = OBSIDIAN  # main window bg
BG_SURFACE = CHARCOAL  # panel / card background
BG_RAISED = GRAPHITE  # elevated cards, hover states
BG_HIGHLIGHT = STEEL  # selected states

# Primary accent — Archon gold (active nav, key actions, executing state).
# Historical names (PURPLE*) preserved so pages need no churn.
GOLD = "#d6a84f"
GOLD_LIGHT = "#f0c96a"
GOLD_DARK = "#806027"
PURPLE = GOLD
PURPLE_GLOW = "#2a2113"  # ~25% gold over obsidian
PURPLE_LIGHT = GOLD_LIGHT
PURPLE_DIM = "#c2953f"  # hover
PURPLE_DARK = GOLD_DARK

# Cool counterpoint — steel-blue (informational readouts, code, links).
CYAN = "#7899ba"  # INFO
CYAN_GLOW = "#141a22"  # steel-blue over obsidian
CYAN_LIGHT = "#9ab4d0"
CYAN_DIM = "#4f647d"

# Bright emphasis gold (alerts above primary).
GOLD_GLOW = "#282010"  # 15% gold over obsidian
GOLD_DIM = "#a67c1c"

# Gradient endpoints (gold → light gold — a brushed-metal sweep)
GRAD_START = GOLD
GRAD_END = GOLD_LIGHT

# Semantic state colors — restrained, sit calmly on obsidian.
SUCCESS = "#78b88a"
SUCCESS_GLOW = "#12211a"
WARNING = "#d2a85c"
WARNING_DIM = "#8a6d34"
ERROR = "#c96868"
ERROR_GLOW = "#2a1616"
ERROR_DIM = "#7f3a3a"
INFO = CYAN

# Typography — soft silver on obsidian.
TEXT_PRIMARY = "#eceae5"
TEXT_SECONDARY = "#b9bbb9"
TEXT_ACCENT = "#f0c96a"  # gold-light highlights
TEXT_CYAN = "#9ab4d0"  # steel-blue (code / readouts)
TEXT_MUTED = "#73787b"
TEXT_DIM = "#4d5255"
TEXT_WHITE = "#ffffff"

# Borders
BORDER_SUBTLE = "#20262b"  # hairline panel rule
BORDER_STRONG = "#30373d"  # spec BORDER — visible divider
BORDER_ACCENT = "#4d4020"  # thin engraved gold rule
BORDER_CYAN = "#243139"  # steel-blue rule

# ── Semantic aliases ───────────────────────────────────────────────────────────
#
# The command-center speaks in semantic tokens (bg / surface / accent / state)
# rather than raw palette names. These alias the palette above so shell code
# reads cleanly while existing pages keep their historical names.
BG = BG_DEEP
SURFACE = BG_SURFACE
SURFACE_ALT = BG_RAISED
SELECTED = BG_HIGHLIGHT
BORDER = BORDER_SUBTLE

ACCENT = GOLD  # single primary accent: active / selected / key actions
ACCENT_HOVER = PURPLE_DIM
ACCENT_MUTED = GOLD_DARK
DANGER = ERROR
DANGER_DIM = ERROR_DIM

TEXT_TERTIARY = TEXT_MUTED  # dim / disabled text

# ── Central token dict (spec §32) ──────────────────────────────────────────────
# A single lookup for tooling / introspection; the module constants above remain
# the canonical way to reference colors in widgets.
COLORS = {
    "void": VOID, "obsidian": OBSIDIAN, "charcoal": CHARCOAL,
    "graphite": GRAPHITE, "steel": STEEL, "iron": IRON, "border": BORDER_STRONG,
    "gold": GOLD, "gold_light": GOLD_LIGHT, "gold_dark": GOLD_DARK,
    "text": TEXT_PRIMARY, "text_secondary": TEXT_SECONDARY,
    "text_muted": TEXT_MUTED, "text_dim": TEXT_DIM,
    "success": SUCCESS, "warning": WARNING, "error": ERROR, "info": INFO,
}

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
# Spec §28: restrained radii (8–12px on major surfaces); avoid excessive rounding.

RADIUS_CARD = 10
RADIUS_PANEL = 10
RADIUS_BTN = 8
RADIUS_INPUT = 8
RADIUS_BADGE = 6
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


# ── Panels (spec §28: prefer panels over cards) ───────────────────────────────


def panel_kwargs(corner_radius: int = RADIUS_PANEL) -> dict:
    """Standard panel: charcoal surface with a hairline border, not a shadow."""
    return {
        "fg_color": BG_SURFACE,
        "corner_radius": corner_radius,
        "border_color": BORDER_SUBTLE,
        "border_width": 1,
    }


def panel_raised_kwargs(corner_radius: int = RADIUS_PANEL) -> dict:
    """Elevated panel — graphite surface with a stronger rule."""
    return {
        "fg_color": BG_RAISED,
        "corner_radius": corner_radius,
        "border_color": BORDER_STRONG,
        "border_width": 1,
    }


# ── Operation / connection status → color (spec §14, §17) ─────────────────────

STATUS_COLORS = {
    "online": SUCCESS, "connected": SUCCESS, "running": GOLD, "active": GOLD,
    "executing": GOLD, "queued": CYAN, "pending": TEXT_MUTED, "idle": TEXT_MUTED,
    "available": TEXT_SECONDARY, "degraded": WARNING, "warning": WARNING,
    "offline": TEXT_DIM, "failed": ERROR, "error": ERROR, "complete": SUCCESS,
    "completed": SUCCESS, "done": SUCCESS,
}


def status_color(state: str) -> str:
    """Map an operation/connection state string to a token color."""
    return STATUS_COLORS.get((state or "").strip().lower(), TEXT_SECONDARY)
