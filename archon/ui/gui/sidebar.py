"""
Sidebar navigation for the Archon GUI.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from . import theme as T
from .components.icon import Icon
from .particles import draw_archon_sigil

# Grouped navigation. Only backend-backed destinations are listed; each entry is
# (page_key, icon_name, label). Empty group title renders with no header.
_NAV_GROUPS: list[tuple[str, list[tuple[str, str, str]]]] = [
    ("", [
        ("home", "overview", "Overview"),
        ("automate", "command", "Command"),
        ("chat", "chat", "Chat"),
    ]),
    ("AUTOMATION", [
        ("n8n", "workflows", "Workflows"),
        ("distro", "osbuilder", "OS Builder"),
    ]),
    ("ACTIVITY", [
        ("history", "history", "History"),
    ]),
    ("SYSTEM", [
        ("settings", "settings", "Settings"),
    ]),
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

        # Archon logo canvas
        self._logo_canvas = _ArchonLogoCanvas(logo_row, size=32)
        self._logo_canvas.pack(side="left", padx=(4, 8))

        self._title_label = ctk.CTkLabel(
            logo_row,
            text="ARCHON",
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
        nav_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=T.BG_SURFACE,
            scrollbar_button_hover_color=T.BG_RAISED,
        )
        nav_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=6)
        self._section_labels: list[ctk.CTkLabel] = []

        for title, items in _NAV_GROUPS:
            if title:
                lbl = ctk.CTkLabel(
                    nav_frame,
                    text=title,
                    font=(T.FONT_FAMILY, 10, "bold"),
                    text_color=T.TEXT_MUTED,
                    anchor="w",
                )
                lbl.pack(fill="x", padx=(14, 8), pady=(14, 4))
                self._section_labels.append(lbl)
            for key, icon_name, label in items:
                btn = _NavButton(
                    nav_frame,
                    key=key,
                    icon_name=icon_name,
                    label=label,
                    active=(key == self._active_page),
                    on_click=self._handle_nav,
                )
                btn.pack(fill="x", pady=1)
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
        for lbl in getattr(self, "_section_labels", []):
            if show:
                lbl.pack(fill="x", padx=(14, 8), pady=(14, 4))
            else:
                lbl.pack_forget()
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
        icon_name: str,
        label: str,
        active: bool = False,
        on_click: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent, fg_color="transparent", corner_radius=T.RADIUS_BTN)
        self._key = key
        self._on_click = on_click
        self._active = active

        self.grid_columnconfigure(1, weight=1)

        # Left active indicator bar.
        self._accent_bar = tk.Canvas(
            self, width=3, height=34, bg=T.BG_SURFACE, highlightthickness=0
        )
        self._accent_bar.pack(side="left")
        self._bar_id = self._accent_bar.create_rectangle(0, 0, 3, 34, fill="", outline="")

        # Monochrome line icon.
        self._icon = Icon(self, icon_name, size=18, color=T.TEXT_SECONDARY, bg=T.BG_SURFACE)
        self._icon.pack(side="left", padx=(10, 10), pady=8)

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

        for w in [self, self._icon, self._text_label]:
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
            self._icon.set_bg(T.BG_HIGHLIGHT)
            self._icon.set_color(T.TEXT_ACCENT)
            self._accent_bar.configure(bg=T.BG_HIGHLIGHT)
            self._accent_bar.itemconfig(self._bar_id, fill=T.ACCENT)
        else:
            self.configure(fg_color="transparent")
            self._text_label.configure(text_color=T.TEXT_SECONDARY)
            self._icon.set_bg(T.BG_SURFACE)
            self._icon.set_color(T.TEXT_SECONDARY)
            self._accent_bar.configure(bg=T.BG_SURFACE)
            self._accent_bar.itemconfig(self._bar_id, fill="")

    def _on_enter(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        if not self._active:
            self.configure(fg_color=T.BG_RAISED)
            self._text_label.configure(text_color=T.TEXT_PRIMARY)
            self._icon.set_bg(T.BG_RAISED)
            self._icon.set_color(T.TEXT_PRIMARY)
            self._accent_bar.configure(bg=T.BG_RAISED)
            self._accent_bar.itemconfig(self._bar_id, fill=T.PURPLE_DIM)

    def _on_leave(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        if not self._active:
            self.configure(fg_color="transparent")
            self._text_label.configure(text_color=T.TEXT_SECONDARY)
            self._icon.set_bg(T.BG_SURFACE)
            self._icon.set_color(T.TEXT_SECONDARY)
            self._accent_bar.configure(bg=T.BG_SURFACE)
            self._accent_bar.itemconfig(self._bar_id, fill="")

    def _on_press(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._on_click:
            self._on_click(self._key)


class _ArchonLogoCanvas(tk.Canvas):
    """Programmatic Archon logo — the static sigil emblem."""

    def __init__(self, parent: tk.Widget, size: int = 32) -> None:
        super().__init__(
            parent,
            width=size,
            height=size,
            bg=T.BG_SURFACE,
            highlightthickness=0,
        )
        # A fixed phase places the traveling spark at a pleasing rest position.
        draw_archon_sigil(self, size=size, phase=0.6)
