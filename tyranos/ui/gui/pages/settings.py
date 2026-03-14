"""
Settings page — 6-category configuration UI with live save.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from .. import theme as T

_CATEGORIES = [
    ("🤖", "AI"),
    ("🔄", "n8n"),
    ("💿", "Distro"),
    ("🎨", "Appearance"),
    ("🛡", "Safety"),
    ("ℹ", "About"),
]


class SettingsPage(ctk.CTkFrame):
    """
    Settings with left category tabs and right content panel.
    """

    def __init__(
        self,
        parent: tk.Widget,
        engine: object = None,
        on_navigate: Callable[[str], None] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, fg_color=T.BG_DEEP, **kwargs)  # type: ignore[arg-type]
        self._engine = engine
        self._on_navigate = on_navigate
        self._active_cat = "AI"
        self._saved_label_id: str | None = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_topbar()
        self._build_body()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_topbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color=T.BG_SURFACE, corner_radius=0, height=52)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(bar, fg_color="transparent")
        left.pack(side="left", padx=T.PAD_CARD)
        ctk.CTkLabel(left, text="⚙  Settings", **T.label_heading_kwargs()).pack(side="left")

        self._save_feedback = ctk.CTkLabel(bar, text="", **T.label_secondary_kwargs())
        self._save_feedback.pack(side="right", padx=T.PAD_CARD)

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=T.PAD_PAGE, pady=T.PAD_CARD)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        # Left category nav
        nav = ctk.CTkFrame(body, fg_color=T.BG_SURFACE, corner_radius=T.RADIUS_CARD, width=160)
        nav.grid(row=0, column=0, sticky="ns", padx=(0, T.SPACE_MD))
        nav.grid_propagate(False)
        self._cat_buttons: dict[str, ctk.CTkButton] = {}

        for icon, name in _CATEGORIES:
            btn = ctk.CTkButton(
                nav,
                text=f"{icon}  {name}",
                anchor="w",
                fg_color=T.PURPLE if name == self._active_cat else "transparent",
                hover_color=T.BG_RAISED,
                text_color=T.TEXT_WHITE if name == self._active_cat else T.TEXT_SECONDARY,
                font=T.FONT_BODY,
                corner_radius=T.RADIUS_BTN,
                command=lambda n=name: self._select_cat(n),
            )
            btn.pack(fill="x", padx=T.SPACE_SM, pady=2, ipady=4)
            self._cat_buttons[name] = btn

        # Right content
        self._content = ctk.CTkFrame(body, **T.card_kwargs())
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        self._render_category(self._active_cat)

    # ── Category switching ────────────────────────────────────────────────────

    def _select_cat(self, name: str) -> None:
        if name == self._active_cat:
            return
        # Update nav buttons
        old_btn = self._cat_buttons.get(self._active_cat)
        if old_btn:
            old_btn.configure(fg_color="transparent", text_color=T.TEXT_SECONDARY)
        new_btn = self._cat_buttons.get(name)
        if new_btn:
            new_btn.configure(fg_color=T.PURPLE, text_color=T.TEXT_WHITE)
        self._active_cat = name
        self._render_category(name)

    def _render_category(self, name: str) -> None:
        for w in self._content.winfo_children():
            w.destroy()

        renderers = {
            "AI": self._render_ai,
            "n8n": self._render_n8n,
            "Distro": self._render_distro,
            "Appearance": self._render_appearance,
            "Safety": self._render_safety,
            "About": self._render_about,
        }
        renderer = renderers.get(name)
        if renderer:
            renderer()

    # ── Category: AI ─────────────────────────────────────────────────────────

    def _render_ai(self) -> None:
        scroll = self._make_scroll()

        ctk.CTkLabel(scroll, text="AI Configuration", font=T.FONT_HEADING, text_color=T.TEXT_PRIMARY).pack(
            anchor="w", padx=T.PAD_CARD, pady=(T.PAD_CARD, T.SPACE_LG)
        )

        cfg = self._load_config()

        self._ai_key = self._field(
            scroll,
            "OpenRouter API Key",
            cfg.get("openrouter_api_key", ""),
            placeholder="sk-or-…",
            secret=True,
        )
        self._ai_base = self._field(
            scroll,
            "API Base URL",
            cfg.get("openrouter_base_url", "https://openrouter.ai/api/v1"),
            placeholder="https://openrouter.ai/api/v1",
        )
        self._ai_tokens = self._field(
            scroll,
            "Max Tokens",
            str(cfg.get("max_tokens", 4096)),
            placeholder="4096",
        )
        self._ai_timeout = self._field(
            scroll,
            "Request Timeout (s)",
            str(cfg.get("timeout", 60)),
            placeholder="60",
        )

        self._save_btn(scroll, self._save_ai)

    def _save_ai(self) -> None:
        try:
            from tyranos.config import get_config
            cfg = get_config()
            cfg.ai.openrouter_api_key = self._ai_key.get().strip()  # type: ignore[union-attr]
            cfg.ai.openrouter_base_url = self._ai_base.get().strip()  # type: ignore[union-attr]
            try:
                cfg.ai.max_tokens = int(self._ai_tokens.get().strip())  # type: ignore[union-attr]
            except ValueError:
                pass
            self._show_saved()
        except Exception:
            self._show_saved("⚠ Saved locally only")

    # ── Category: n8n ────────────────────────────────────────────────────────

    def _render_n8n(self) -> None:
        scroll = self._make_scroll()

        ctk.CTkLabel(scroll, text="n8n Connection", font=T.FONT_HEADING, text_color=T.TEXT_PRIMARY).pack(
            anchor="w", padx=T.PAD_CARD, pady=(T.PAD_CARD, T.SPACE_LG)
        )

        import os
        self._n8n_url = self._field(
            scroll,
            "n8n URL",
            os.environ.get("N8N_URL", "http://localhost:5678"),
            placeholder="http://localhost:5678",
        )
        self._n8n_key = self._field(
            scroll,
            "n8n API Key",
            os.environ.get("N8N_API_KEY", ""),
            placeholder="Your n8n API key…",
            secret=True,
        )

        # Test connection button
        test_row = ctk.CTkFrame(scroll, fg_color="transparent")
        test_row.pack(anchor="w", padx=T.PAD_CARD, pady=(T.SPACE_MD, 0))
        ctk.CTkButton(
            test_row,
            text="⟳  Test Connection",
            width=150,
            **T.btn_outline_kwargs(),
            command=self._test_n8n,
        ).pack(side="left")
        self._n8n_test_label = ctk.CTkLabel(
            test_row, text="", **T.label_secondary_kwargs()
        )
        self._n8n_test_label.pack(side="left", padx=T.SPACE_SM)

        self._save_btn(scroll, self._save_n8n)

    def _test_n8n(self) -> None:
        self._n8n_test_label.configure(text="Testing…", text_color=T.CYAN)

        def _do() -> None:
            result_q: queue.Queue = queue.Queue()
            try:
                import httpx
                url = self._n8n_url.get().strip().rstrip("/")
                key = self._n8n_key.get().strip()
                with httpx.Client(timeout=5) as c:
                    r = c.get(f"{url}/api/v1/workflows", headers={"X-N8N-API-KEY": key})
                result_q.put(("ok", f"✓  Connected ({r.status_code})"))
            except Exception as exc:
                result_q.put(("err", f"✗  {exc}"))
            kind, msg = result_q.get()
            if kind == "ok":
                self._n8n_test_label.configure(text=msg, text_color=T.SUCCESS)
            else:
                self._n8n_test_label.configure(text=msg, text_color=T.ERROR)

        threading.Thread(target=_do, daemon=True).start()

    def _save_n8n(self) -> None:
        import os
        os.environ["N8N_URL"] = self._n8n_url.get().strip()
        os.environ["N8N_API_KEY"] = self._n8n_key.get().strip()
        self._show_saved()

    # ── Category: Distro ──────────────────────────────────────────────────────

    def _render_distro(self) -> None:
        scroll = self._make_scroll()

        ctk.CTkLabel(scroll, text="Distro Builder", font=T.FONT_HEADING, text_color=T.TEXT_PRIMARY).pack(
            anchor="w", padx=T.PAD_CARD, pady=(T.PAD_CARD, T.SPACE_LG)
        )

        self._iso_out = self._field(
            scroll,
            "ISO Output Directory",
            "/tmp/tyranos_builds",
            placeholder="/tmp/tyranos_builds",
        )
        self._build_threads = self._field(
            scroll,
            "Build Threads",
            "4",
            placeholder="4",
        )

        ctk.CTkLabel(
            scroll,
            text="⚠  Distro builds require root / sudo and Linux build tools (xorriso, debootstrap/pacstrap).",
            font=T.FONT_SMALL,
            text_color=T.WARNING,
            wraplength=380,
            justify="left",
        ).pack(anchor="w", padx=T.PAD_CARD, pady=(T.SPACE_MD, 0))

        self._save_btn(scroll, self._show_saved)

    # ── Category: Appearance ──────────────────────────────────────────────────

    def _render_appearance(self) -> None:
        scroll = self._make_scroll()

        ctk.CTkLabel(scroll, text="Appearance", font=T.FONT_HEADING, text_color=T.TEXT_PRIMARY).pack(
            anchor="w", padx=T.PAD_CARD, pady=(T.PAD_CARD, T.SPACE_LG)
        )

        ctk.CTkLabel(scroll, text="Color Mode", **T.label_secondary_kwargs()).pack(
            anchor="w", padx=T.PAD_CARD
        )
        self._color_mode = ctk.CTkSegmentedButton(
            scroll,
            values=["Dark", "Light", "System"],
            command=self._on_color_mode,
            font=T.FONT_SMALL,
            fg_color=T.BG_RAISED,
            selected_color=T.PURPLE,
            selected_hover_color=T.PURPLE_DIM,
            unselected_color=T.BG_RAISED,
            unselected_hover_color=T.BG_HIGHLIGHT,
            text_color=T.TEXT_PRIMARY,
        )
        self._color_mode.set("Dark")
        self._color_mode.pack(anchor="w", padx=T.PAD_CARD, pady=(T.SPACE_XS, T.SPACE_MD))

        ctk.CTkLabel(scroll, text="Scaling", **T.label_secondary_kwargs()).pack(
            anchor="w", padx=T.PAD_CARD
        )
        self._scale_slider = ctk.CTkSlider(
            scroll,
            from_=0.8,
            to=1.4,
            number_of_steps=6,
            fg_color=T.BG_RAISED,
            progress_color=T.PURPLE,
            button_color=T.PURPLE,
            button_hover_color=T.PURPLE_DIM,
            command=self._on_scale,
        )
        self._scale_slider.set(1.0)
        self._scale_slider.pack(fill="x", padx=T.PAD_CARD, pady=(T.SPACE_XS, T.SPACE_SM))

        self._scale_label = ctk.CTkLabel(scroll, text="Scale: 1.0×", **T.label_secondary_kwargs())
        self._scale_label.pack(anchor="w", padx=T.PAD_CARD)

    def _on_color_mode(self, value: str) -> None:
        import customtkinter as ctk2
        mode_map = {"Dark": "dark", "Light": "light", "System": "system"}
        try:
            ctk2.set_appearance_mode(mode_map.get(value, "dark"))
        except Exception:
            pass

    def _on_scale(self, value: float) -> None:
        self._scale_label.configure(text=f"Scale: {value:.1f}×")
        try:
            import customtkinter as ctk2
            ctk2.set_widget_scaling(value)
        except Exception:
            pass

    # ── Category: Safety ─────────────────────────────────────────────────────

    def _render_safety(self) -> None:
        scroll = self._make_scroll()

        ctk.CTkLabel(scroll, text="Safety & Permissions", font=T.FONT_HEADING, text_color=T.TEXT_PRIMARY).pack(
            anchor="w", padx=T.PAD_CARD, pady=(T.PAD_CARD, T.SPACE_LG)
        )

        toggles = [
            ("Safe Mode Default", "Enable safe mode for all new commands", True),
            ("Confirm Destructive Ops", "Prompt before delete/overwrite", True),
            ("Audit Logging", "Log all executed commands to disk", True),
            ("Network Access", "Allow commands to make network calls", False),
            ("Shell Execution", "Allow raw shell commands", False),
        ]
        self._safety_vars: dict[str, tk.BooleanVar] = {}
        for key, desc, default in toggles:
            var = tk.BooleanVar(value=default)
            self._safety_vars[key] = var
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.pack(fill="x", padx=T.PAD_CARD, pady=T.SPACE_XS)
            ctk.CTkLabel(
                row, text=key, font=T.FONT_BODY, text_color=T.TEXT_PRIMARY, anchor="w"
            ).pack(side="left", fill="x", expand=True)
            ctk.CTkSwitch(
                row,
                text="",
                width=40,
                variable=var,
                onvalue=True,
                offvalue=False,
                fg_color=T.BG_DEEP,
                progress_color=T.SUCCESS,
                button_color=T.TEXT_WHITE,
            ).pack(side="right")
            ctk.CTkLabel(
                scroll,
                text=desc,
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                anchor="w",
            ).pack(anchor="w", padx=T.PAD_CARD * 2, pady=(0, T.SPACE_SM))

        self._save_btn(scroll, self._show_saved)

    # ── Category: About ───────────────────────────────────────────────────────

    def _render_about(self) -> None:
        frame = self._make_scroll()

        logo_canvas = tk.Canvas(
            frame,
            width=64,
            height=64,
            bg=T.BG_DEEP,
            highlightthickness=0,
        )
        logo_canvas.pack(pady=(T.PAD_CARD, T.SPACE_MD))
        logo_canvas.create_oval(4, 4, 60, 60, fill=T.PURPLE, outline=T.PURPLE_LIGHT, width=2)
        logo_canvas.create_text(32, 32, text="T", font=("Inter", 28, "bold"), fill=T.TEXT_WHITE)

        ctk.CTkLabel(frame, text="Tyranos", font=T.FONT_DISPLAY, text_color=T.TEXT_PRIMARY).pack()
        ctk.CTkLabel(frame, text="v2.0.0  ·  Universal OS Automation Framework", **T.label_secondary_kwargs()).pack(
            pady=(T.SPACE_XS, T.SPACE_LG)
        )

        info_card = ctk.CTkFrame(frame, fg_color=T.BG_RAISED, corner_radius=T.RADIUS_SM)
        info_card.pack(fill="x", padx=T.PAD_CARD)

        rows = [
            ("Python", "≥3.10"),
            ("License", "MIT"),
            ("Stack", "CustomTkinter · httpx · Pydantic · Loguru"),
            ("AI", "OpenRouter API (free model pool)"),
        ]
        for label, value in rows:
            r = ctk.CTkFrame(info_card, fg_color="transparent")
            r.pack(fill="x", padx=T.PAD_CARD, pady=T.SPACE_XS)
            ctk.CTkLabel(r, text=label, font=T.FONT_SMALL, text_color=T.TEXT_MUTED, width=100, anchor="w").pack(side="left")
            ctk.CTkLabel(r, text=value, font=T.FONT_SMALL, text_color=T.TEXT_PRIMARY, anchor="w").pack(side="left")

        ctk.CTkLabel(
            frame,
            text="Built with  ❤  by the Tyranos Team",
            font=T.FONT_SMALL,
            text_color=T.TEXT_MUTED,
        ).pack(pady=T.SPACE_LG)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _make_scroll(self) -> ctk.CTkScrollableFrame:
        scroll = ctk.CTkScrollableFrame(
            self._content,
            fg_color="transparent",
            scrollbar_button_color=T.BG_RAISED,
            scrollbar_button_hover_color=T.PURPLE,
        )
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        return scroll

    def _field(
        self,
        parent: ctk.CTkScrollableFrame,
        label: str,
        value: str,
        placeholder: str = "",
        secret: bool = False,
    ) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, **T.label_secondary_kwargs()).pack(
            anchor="w", padx=T.PAD_CARD, pady=(T.SPACE_MD, T.SPACE_XS)
        )
        entry = ctk.CTkEntry(
            parent,
            placeholder_text=placeholder,
            show="•" if secret else "",
            **T.input_kwargs(),
        )
        entry.insert(0, value)
        entry.pack(fill="x", padx=T.PAD_CARD)
        return entry

    def _save_btn(self, parent: ctk.CTkFrame, command: Callable) -> None:
        ctk.CTkButton(
            parent,
            text="💾  Save",
            width=100,
            **T.btn_primary_kwargs(),
            command=command,
        ).pack(anchor="w", padx=T.PAD_CARD, pady=T.SPACE_LG)

    def _show_saved(self, text: str = "✓  Saved") -> None:
        self._save_feedback.configure(text=text, text_color=T.SUCCESS)
        if self._saved_label_id:
            try:
                self.after_cancel(self._saved_label_id)
            except Exception:
                pass
        self._saved_label_id = self.after(  # type: ignore[assignment]
            3000,
            lambda: self._save_feedback.configure(text=""),
        )

    def _load_config(self) -> dict:
        try:
            from tyranos.config import get_config
            cfg = get_config()
            return {
                "openrouter_api_key": cfg.ai.openrouter_api_key or "",
                "openrouter_base_url": cfg.ai.openrouter_base_url or "",
                "max_tokens": cfg.ai.max_tokens,
                "timeout": getattr(cfg.ai, "timeout", 60),
            }
        except Exception:
            return {}
