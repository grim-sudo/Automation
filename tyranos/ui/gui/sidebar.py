"""
Sidebar navigation for the Tyranos GUI.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from . import theme as T

_NAV_ITEMS = [
    ("home",        "🏠",  "Home"),
    ("chat",        "💬",  "Chat"),
    ("automate",    "⚡",  "Automate"),
    ("n8n",         "🔄",  "Workflows"),
    ("distro",      "💿",  "Build OS"),
    ("history",     "📋",  "History"),
    ("settings",    "⚙️",  "Settings"),
]


class Sidebar(ctk.CTkFrame):
    """
    Collapsible sidebar with icon + label navigation items and status footer.

    Parameters
    ----------
    parent : tk.Widget
    on_navigate : Callable[[str], None]
        Called with page key when user clicks a nav item.
    initial_page : str
        Page key that starts as active.
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_navigate: Callable[[str], None] | None = None,
        initial_page: str = "chat",
        **kwargs: object,
    ) -> None:
        super().__init__(
            parent,
            fg_color=T.BG_SURFACE,
            corner_radius=0,
            width=T.SIDEBAR_EXPANDED,
            **kwargs,  # type: ignore[arg-type]
        )
        self._on_navigate = on_navigate
        self._active_page = initial_page
        self._expanded = True
        self._buttons: dict[str, _NavButton] = {}
        self._width_var = T.SIDEBAR_EXPANDED

        self.grid_propagate(False)
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self.grid_rowconfigure(1, weight=1)  # nav area expands
        self.grid_columnconfigure(0, weight=1)

        # ── Logo section ──────────────────────────────────────────────────────
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(16, 8))
        logo_frame.grid_columnconfigure(0, weight=1)

        logo_row = ctk.CTkFrame(logo_frame, fg_color="transparent")
        logo_row.pack(fill="x")

        # Tyranos logo canvas
        self._logo_canvas = _TyranosLogoCanvas(logo_row, size=32)
        self._logo_canvas.pack(side="left", padx=(4, 8))

        self._title_label = ctk.CTkLabel(
            logo_row,
            text="TYRANOS",
            font=(T.FONT_FAMILY, 15, "bold"),
            text_color=T.TEXT_ACCENT,
        )
        self._title_label.pack(side="left")

        self._collapse_btn = ctk.CTkButton(
            logo_row,
            text="◀",
            width=28,
            height=28,
            fg_color="transparent",
            hover_color=T.BG_RAISED,
            text_color=T.TEXT_SECONDARY,
            font=T.FONT_MICRO,
            command=self._toggle_collapse,
        )
        self._collapse_btn.pack(side="right", padx=4)

        # Divider
        ctk.CTkFrame(self, fg_color=T.BORDER_SUBTLE, height=1, corner_radius=0).grid(
            row=0, column=0, sticky="sew", padx=0
        )

        # ── Navigation items ──────────────────────────────────────────────────
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

        for key, icon, label in _NAV_ITEMS:
            btn = _NavButton(
                nav_frame,
                key=key,
                icon=icon,
                label=label,
                active=(key == self._active_page),
                on_click=self._handle_nav,
            )
            btn.pack(fill="x", pady=2)
            self._buttons[key] = btn

        # ── Status footer ─────────────────────────────────────────────────────
        self._footer = ctk.CTkFrame(self, fg_color="transparent")
        self._footer.grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 12))

        self._status_dot_canvas = tk.Canvas(
            self._footer, width=10, height=10, bg=T.BG_SURFACE, highlightthickness=0
        )
        self._status_dot_canvas.pack(side="left", padx=(4, 4))
        self._dot_id = self._status_dot_canvas.create_oval(1, 1, 9, 9, fill=T.SUCCESS, outline="")

        self._status_label = ctk.CTkLabel(
            self._footer,
            text="System Online",
            font=T.FONT_MICRO,
            text_color=T.SUCCESS,
        )
        self._status_label.pack(side="left")

        ctk.CTkLabel(
            self._footer,
            text="v2.0.0",
            font=T.FONT_MICRO,
            text_color=T.TEXT_MUTED,
        ).pack(side="right", padx=4)

        self._start_status_pulse()

    # ── Public ─────────────────────────────────────────────────────────────────

    def set_active(self, page: str) -> None:
        """Highlight the active page button."""
        if self._active_page in self._buttons:
            self._buttons[self._active_page].set_active(False)
        self._active_page = page
        if page in self._buttons:
            self._buttons[page].set_active(True)

    def set_status(self, online: bool, label: str = "") -> None:
        """Update the footer status indicator."""
        color = T.SUCCESS if online else T.ERROR
        text = label or ("System Online" if online else "AI Offline")
        try:
            self._status_dot_canvas.itemconfig(self._dot_id, fill=color)
            self._status_label.configure(text=text, text_color=color)
        except Exception:
            pass

    def show_labels(self, show: bool) -> None:
        """Show/hide text labels (for collapse animation)."""
        if show:
            self._title_label.pack(side="left")
        else:
            self._title_label.pack_forget()
        for btn in self._buttons.values():
            btn.show_label(show)

    # ── Internal ───────────────────────────────────────────────────────────────

    def _handle_nav(self, key: str) -> None:
        self.set_active(key)
        if self._on_navigate:
            self._on_navigate(key)

    def _toggle_collapse(self) -> None:
        self._expanded = not self._expanded
        target = T.SIDEBAR_EXPANDED if self._expanded else T.SIDEBAR_COLLAPSED
        self.configure(width=target)
        self.show_labels(self._expanded)
        arrow = "◀" if self._expanded else "▶"
        self._collapse_btn.configure(text=arrow)

    def _start_status_pulse(self) -> None:
        import math
        self._pulse_phase = 0.0

        def _tick() -> None:
            self._pulse_phase += 0.12
            alpha = (math.sin(self._pulse_phase) + 1) / 2
            bright = int(alpha * 255)
            dim = int(alpha * 128)
            color = f"#10{bright:02x}{dim:02x}"
            try:
                self._status_dot_canvas.itemconfig(self._dot_id, fill=color)
                self._status_dot_canvas.after(80, _tick)
            except Exception:
                pass

        _tick()


class _NavButton(ctk.CTkFrame):
    """Single item in the sidebar navigation."""

    def __init__(
        self,
        parent: tk.Widget,
        key: str,
        icon: str,
        label: str,
        active: bool = False,
        on_click: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent, fg_color="transparent", corner_radius=T.RADIUS_BTN)
        self._key = key
        self._on_click = on_click
        self._active = active

        self.grid_columnconfigure(1, weight=1)

        # Left active border (purple glow bar)
        self._accent_bar = tk.Canvas(
            self, width=3, height=36, bg=T.BG_SURFACE, highlightthickness=0
        )
        self._accent_bar.pack(side="left")
        self._bar_id = self._accent_bar.create_rectangle(0, 0, 3, 36, fill="", outline="")

        # Icon
        self._icon_label = ctk.CTkLabel(
            self,
            text=icon,
            font=(T.FONT_FAMILY, 16),
            width=36,
            anchor="center",
        )
        self._icon_label.pack(side="left")

        # Label
        self._text_label = ctk.CTkLabel(
            self,
            text=label,
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
            anchor="w",
        )
        self._text_label.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self._apply_state()

        for w in [self, self._icon_label, self._text_label]:
            w.bind("<Enter>", self._on_enter, add="+")
            w.bind("<Leave>", self._on_leave, add="+")
            w.bind("<Button-1>", self._on_press, add="+")

    def set_active(self, active: bool) -> None:
        self._active = active
        self._apply_state()

    def show_label(self, show: bool) -> None:
        if show:
            self._text_label.pack(side="left", fill="x", expand=True, padx=(0, 8))
        else:
            self._text_label.pack_forget()

    def _apply_state(self) -> None:
        if self._active:
            self.configure(fg_color=T.BG_HIGHLIGHT)
            self._text_label.configure(text_color=T.TEXT_ACCENT)
            self._icon_label.configure(text_color=T.TEXT_ACCENT)
            self._accent_bar.itemconfig(self._bar_id, fill=T.PURPLE)
        else:
            self.configure(fg_color="transparent")
            self._text_label.configure(text_color=T.TEXT_SECONDARY)
            self._icon_label.configure(text_color=T.TEXT_SECONDARY)
            self._accent_bar.itemconfig(self._bar_id, fill="")

    def _on_enter(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        if not self._active:
            self.configure(fg_color=T.BG_RAISED)
            self._text_label.configure(text_color=T.TEXT_PRIMARY)
            self._accent_bar.itemconfig(self._bar_id, fill=T.PURPLE_DIM)

    def _on_leave(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        if not self._active:
            self.configure(fg_color="transparent")
            self._text_label.configure(text_color=T.TEXT_SECONDARY)
            self._accent_bar.itemconfig(self._bar_id, fill="")

    def _on_press(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._on_click:
            self._on_click(self._key)


class _TyranosLogoCanvas(tk.Canvas):
    """Programmatic Tyranos logo — gradient ring with T mark."""

    def __init__(self, parent: tk.Widget, size: int = 32) -> None:
        super().__init__(
            parent,
            width=size,
            height=size,
            bg=T.BG_SURFACE,
            highlightthickness=0,
        )
        self._draw(size)

    def _draw(self, s: int) -> None:
        p = 2
        # Outer gradient ring — approximate with multiple arcs
        self.create_oval(p, p, s - p, s - p, fill=T.PURPLE_DARK, outline=T.PURPLE, width=2)
        # Inner T mark
        cx, cy = s // 2, s // 2
        bw = int(s * 0.5)
        bh = int(s * 0.1) + 1
        sw = int(s * 0.14) + 1
        sh = int(s * 0.3)
        # Crossbar
        self.create_rectangle(
            cx - bw // 2, cy - sh // 2 - bh // 2,
            cx + bw // 2, cy - sh // 2 + bh // 2,
            fill=T.CYAN_LIGHT, outline="",
        )
        # Stem
        self.create_rectangle(
            cx - sw // 2, cy - sh // 2 + bh // 2,
            cx + sw // 2, cy + sh // 2,
            fill=T.PURPLE_LIGHT, outline="",
        )
