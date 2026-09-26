"""
Archon GUI — main application window.
Splash screen → sidebar + page router → persistent window state.
"""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from typing import Any

import customtkinter as ctk

from . import theme as T
from .components.status_bar import StatusBar
from .components.topbar import TopBar
from .pages.automate import AutomatePage
from .pages.chat import ChatPage
from .pages.distro_page import DistroPage
from .pages.history import HistoryPage
from .pages.home import HomePage
from .pages.n8n_page import N8nPage
from .pages.settings import SettingsPage
from .particles import ParticleField, draw_archon_sigil
from .sidebar import Sidebar

_STATE_PATH = Path.home() / ".archon" / "gui_state.json"

_PAGE_ORDER = ["home", "chat", "automate", "n8n", "distro", "history", "settings"]

_PAGE_CLASSES: dict[str, type] = {
    "home": HomePage,
    "chat": ChatPage,
    "automate": AutomatePage,
    "n8n": N8nPage,
    "distro": DistroPage,
    "history": HistoryPage,
    "settings": SettingsPage,
}


class ArchonApp(ctk.CTk):
    """
    Main application window with splash, sidebar navigation, and page routing.
    """

    def __init__(self, engine: object = None) -> None:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        super().__init__(fg_color=T.BG_DEEP)
        self._engine = engine
        self._pages: dict[str, ctk.CTkFrame] = {}
        self._active_page = "home"

        self.title("Archon")
        self.minsize(900, 600)
        self._restore_geometry()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._show_splash()

    # ── Splash ────────────────────────────────────────────────────────────────

    def _show_splash(self) -> None:
        self._splash = ctk.CTkFrame(self, fg_color=T.BG_DEEP, corner_radius=0)
        self._splash.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Full-bleed ambient particle constellation behind the reactor.
        self._splash_field = ParticleField(self._splash, bg=T.BG_DEEP)
        self._splash_field.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._splash_field.start()

        # Arc-reactor logo canvas (drawn atop the field).
        canvas = tk.Canvas(
            self._splash,
            width=170,
            height=170,
            bg=T.BG_DEEP,
            highlightthickness=0,
        )
        canvas.place(relx=0.5, rely=0.37, anchor="center")
        self._splash_canvas = canvas
        self._splash_ring_step = 0.0
        self._draw_splash_logo(canvas)

        ctk.CTkLabel(
            self._splash,
            text="ARCHON",
            font=(T.FONT_FAMILY, 40, "bold"),
            text_color=T.TEXT_PRIMARY,
        ).place(relx=0.5, rely=0.56, anchor="center")

        ctk.CTkLabel(
            self._splash,
            text="Systems online · Awaiting directive",
            font=T.FONT_SUBHEADING,
            text_color=T.TEXT_CYAN,
        ).place(relx=0.5, rely=0.62, anchor="center")

        self._splash_bar_canvas = tk.Canvas(
            self._splash,
            width=300,
            height=4,
            bg=T.BG_RAISED,
            highlightthickness=0,
        )
        self._splash_bar_canvas.place(relx=0.5, rely=0.69, anchor="center")
        self._splash_bar_canvas.create_rectangle(0, 0, 0, 4, fill=T.PURPLE, tags="bar")
        self._splash_progress = 0.0

        self._animate_splash()

    def _draw_splash_logo(self, canvas: tk.Canvas) -> None:
        draw_archon_sigil(canvas, size=170, phase=self._splash_ring_step)

    def _animate_splash(self) -> None:
        # The window may be closed (or the splash replaced) mid-animation; a
        # pending `after` callback would then draw on a destroyed canvas.
        if not self._splash.winfo_exists() or not self._splash_canvas.winfo_exists():
            return

        self._splash_ring_step += 0.12
        self._draw_splash_logo(self._splash_canvas)

        self._splash_progress = min(self._splash_progress + 0.014, 1.0)
        bar_w = int(300 * self._splash_progress)
        self._splash_bar_canvas.coords("bar", 0, 0, bar_w, 4)

        if self._splash_progress < 1.0:
            self.after(40, self._animate_splash)
        else:
            self.after(300, self._launch_main)

    def _launch_main(self) -> None:
        self._splash_field.stop()
        self._splash.destroy()
        self._build_main()

    # ── Main layout ───────────────────────────────────────────────────────────

    def _build_main(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._sidebar = Sidebar(self, on_navigate=self._navigate, initial_page="home")
        self._sidebar.grid(row=0, column=0, rowspan=3, sticky="ns")

        self._topbar = TopBar(
            self,
            on_command=self._handle_command,
            on_settings=lambda: self._navigate("settings"),
        )
        self._topbar.grid(row=0, column=1, sticky="ew")

        self._page_container = ctk.CTkFrame(self, fg_color=T.BG_DEEP, corner_radius=0)
        self._page_container.grid(row=1, column=1, sticky="nsew")
        self._page_container.grid_rowconfigure(0, weight=1)
        self._page_container.grid_columnconfigure(0, weight=1)

        self._statusbar = StatusBar(self)
        self._statusbar.grid(row=2, column=1, sticky="ew")

        # Pre-build home page; others built on demand
        self._show_page("home")
        self._topbar.set_page("home")

        # Keyboard shortcuts
        self.bind("<Control-comma>", lambda _e: self._navigate("settings"))
        self.bind("<Control-h>", lambda _e: self._navigate("home"))
        self.bind("<Control-t>", lambda _e: self._navigate("chat"))

    # ── Navigation ────────────────────────────────────────────────────────────

    def _navigate(self, page_name: str) -> None:
        if page_name not in _PAGE_CLASSES:
            return
        self._active_page = page_name
        self._show_page(page_name)
        self._sidebar.set_active(page_name)
        self._topbar.set_page(page_name)

    def _handle_command(self, text: str) -> None:
        """Route a global command-bar entry to the Command view and run it."""
        self._navigate("automate")
        page = self._pages.get("automate")
        submit = getattr(page, "submit_command", None)
        if callable(submit):
            submit(text)

    def _show_page(self, page_name: str) -> None:
        # Hide all existing pages
        for frame in self._pages.values():
            frame.grid_remove()

        # Build page lazily
        if page_name not in self._pages:
            cls = _PAGE_CLASSES[page_name]
            page = cls(
                self._page_container,
                engine=self._engine,
                on_navigate=self._navigate,
            )
            page.grid(row=0, column=0, sticky="nsew")
            self._pages[page_name] = page
        else:
            self._pages[page_name].grid()
            refresh = getattr(self._pages[page_name], "refresh", None)
            if callable(refresh):
                refresh()

    # ── Window state ──────────────────────────────────────────────────────────

    def _restore_geometry(self) -> None:
        try:
            if _STATE_PATH.exists():
                data: dict[str, Any] = json.loads(_STATE_PATH.read_text())
                geo = data.get("geometry", "1200x750")
                self.geometry(geo)
                return
        except Exception:
            pass
        self.geometry("1200x750")

    def _save_geometry(self) -> None:
        try:
            _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            _STATE_PATH.write_text(json.dumps({"geometry": self.geometry()}))
        except Exception:
            pass

    def _on_close(self) -> None:
        self._save_geometry()
        self.destroy()

    def run(self) -> None:
        """Start the GUI event loop."""
        self.mainloop()


# ── Public facade ─────────────────────────────────────────────────────────────


class ModernArchonGUI:
    """
    Public entry point for `archon.ui.gui`.
    Wraps ArchonApp so callers only need `ModernArchonGUI(engine).run()`.
    """

    def __init__(self, engine: object = None) -> None:
        self._engine = engine
        self._app: ArchonApp | None = None

    def run(self) -> None:
        """Launch the GUI (blocking)."""
        self._app = ArchonApp(engine=self._engine)
        self._app.run()
