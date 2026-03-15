"""
Distro Builder page — 5-step wizard to configure and build a custom Linux ISO.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from .. import theme as T
from ..components.progress_card import ProgressCard

_DISTRO_TYPES = [
    ("🖥", "Desktop", "Full GUI environment with apps"),
    ("⚙", "Server", "Minimal headless server image"),
    ("🔒", "Security", "Pentest and hardening tools"),
    ("🛠", "Dev", "Developer toolchain pre-installed"),
    ("🪶", "Minimal", "Bare-bones base system only"),
]

_BASE_SYSTEMS = ["Arch Linux", "Debian", "Ubuntu", "Alpine", "Fedora"]

_APP_BUNDLES = [
    ("🌐 Browser", "firefox"),
    ("💻 Terminal", "alacritty"),
    ("📝 Editor", "neovim"),
    ("🐳 Docker", "docker"),
    ("🐍 Python", "python"),
    ("🦀 Rust", "rust"),
    ("📦 Node.js", "nodejs"),
    ("🔒 Security", "wireshark nmap"),
]


class DistroPage(ctk.CTkFrame):
    """
    5-step distro wizard: type → apps → base → security → build.
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
        self._result_queue: queue.Queue = queue.Queue()
        self._building = False

        # Wizard state
        self._step = 0
        self._config: dict = {
            "distro_type": "Desktop",
            "base": "Arch Linux",
            "apps": [],
            "hardening": False,
            "hostname": "tyranos",
            "username": "user",
        }

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_topbar()
        self._build_body()
        self._check_results()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_topbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color=T.BG_SURFACE, corner_radius=0, height=52)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(bar, fg_color="transparent")
        left.pack(side="left", padx=T.PAD_CARD)
        ctk.CTkLabel(left, text="💿  Distro Builder", **T.label_heading_kwargs()).pack(side="left")

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right", padx=T.PAD_CARD)
        ctk.CTkButton(
            right,
            text="↩ Reset",
            width=80,
            **T.btn_ghost_kwargs(),
            command=self._reset_wizard,
        ).pack(side="left")

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=T.PAD_PAGE, pady=T.PAD_CARD)
        body.grid_rowconfigure(1, weight=1)
        body.grid_columnconfigure(0, weight=1)

        self._build_stepper(body)

        self._content = ctk.CTkFrame(body, **T.card_kwargs())
        self._content.grid(row=1, column=0, sticky="nsew", pady=(T.SPACE_MD, 0))
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        self._render_step()

    def _build_stepper(self, parent: ctk.CTkFrame) -> None:
        steps = ["Type", "Apps", "Base", "Security", "Build"]
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=0, column=0, sticky="ew")

        for i, label in enumerate(steps):
            is_active = i == self._step
            is_done = i < self._step
            col = ctk.CTkFrame(row, fg_color="transparent")
            col.pack(side="left", expand=True)

            dot_color = T.PURPLE if is_active else (T.SUCCESS if is_done else T.BG_RAISED)
            dot_border = T.PURPLE if is_active else (T.SUCCESS if is_done else T.BORDER_SUBTLE)
            txt_color = T.TEXT_ACCENT if is_active else (T.SUCCESS if is_done else T.TEXT_MUTED)

            dot = ctk.CTkFrame(
                col,
                width=28,
                height=28,
                fg_color=dot_color,
                border_color=dot_border,
                border_width=2,
                corner_radius=14,
            )
            dot.pack(anchor="center")
            dot.pack_propagate(False)
            ctk.CTkLabel(
                dot,
                text="✓" if is_done else str(i + 1),
                font=T.FONT_SMALL,
                text_color=T.TEXT_WHITE,
            ).place(relx=0.5, rely=0.5, anchor="center")

            ctk.CTkLabel(col, text=label, font=T.FONT_MICRO, text_color=txt_color).pack(
                anchor="center", pady=(2, 0)
            )

            if i < len(steps) - 1:
                line_color = T.SUCCESS if is_done else T.BORDER_SUBTLE
                ctk.CTkFrame(row, fg_color=line_color, height=2, width=40).pack(
                    side="left", pady=(0, 14)
                )

        self._stepper_row = row

    def _refresh_stepper(self) -> None:
        self._stepper_row.destroy()
        self._build_stepper(self._stepper_row.master)  # type: ignore[arg-type]

    # ── Step rendering ────────────────────────────────────────────────────────

    def _render_step(self) -> None:
        for w in self._content.winfo_children():
            w.destroy()

        steps = [
            self._render_step_type,
            self._render_step_apps,
            self._render_step_base,
            self._render_step_security,
            self._render_step_build,
        ]
        if self._step < len(steps):
            steps[self._step]()

    def _render_step_type(self) -> None:
        frame = self._scroll_frame()
        ctk.CTkLabel(
            frame, text="Select Distro Type", font=T.FONT_HEADING, text_color=T.TEXT_PRIMARY
        ).pack(anchor="w", padx=T.PAD_CARD, pady=(T.PAD_CARD, T.SPACE_LG))

        grid = ctk.CTkFrame(frame, fg_color="transparent")
        grid.pack(padx=T.PAD_CARD)

        self._type_var = tk.StringVar(value=self._config["distro_type"])
        for idx, (icon, name, desc) in enumerate(_DISTRO_TYPES):
            row, col = divmod(idx, 3)
            card = _SelectCard(
                grid,
                icon=icon,
                title=name,
                desc=desc,
                selected_var=self._type_var,
                value=name,
            )
            card.grid(row=row, column=col, padx=6, pady=6)

        self._nav_buttons(frame, back=False, on_next=self._step1_next)

    def _step1_next(self) -> None:
        self._config["distro_type"] = self._type_var.get()
        self._advance()

    def _render_step_apps(self) -> None:
        frame = self._scroll_frame()
        ctk.CTkLabel(
            frame, text="Select App Bundles", font=T.FONT_HEADING, text_color=T.TEXT_PRIMARY
        ).pack(anchor="w", padx=T.PAD_CARD, pady=(T.PAD_CARD, T.SPACE_LG))

        self._app_vars: dict[str, tk.BooleanVar] = {}
        grid = ctk.CTkFrame(frame, fg_color="transparent")
        grid.pack(padx=T.PAD_CARD)
        for idx, (label, pkg) in enumerate(_APP_BUNDLES):
            row, col = divmod(idx, 2)
            var = tk.BooleanVar(value=pkg in self._config["apps"])
            self._app_vars[pkg] = var
            cb = ctk.CTkCheckBox(
                grid,
                text=label,
                variable=var,
                font=T.FONT_BODY,
                text_color=T.TEXT_PRIMARY,
                fg_color=T.PURPLE,
                hover_color=T.PURPLE_DIM,
                border_color=T.BORDER_ACCENT,
                checkmark_color=T.TEXT_WHITE,
            )
            cb.grid(row=row, column=col, sticky="w", padx=T.PAD_CARD, pady=T.SPACE_XS)

        self._nav_buttons(frame, on_next=self._step2_next)

    def _step2_next(self) -> None:
        self._config["apps"] = [pkg for pkg, var in self._app_vars.items() if var.get()]
        self._advance()

    def _render_step_base(self) -> None:
        frame = self._scroll_frame()
        ctk.CTkLabel(
            frame, text="Select Base System", font=T.FONT_HEADING, text_color=T.TEXT_PRIMARY
        ).pack(anchor="w", padx=T.PAD_CARD, pady=(T.PAD_CARD, T.SPACE_LG))

        self._base_var = tk.StringVar(value=self._config["base"])
        for base in _BASE_SYSTEMS:
            ctk.CTkRadioButton(
                frame,
                text=base,
                variable=self._base_var,
                value=base,
                font=T.FONT_BODY,
                text_color=T.TEXT_PRIMARY,
                fg_color=T.PURPLE,
                hover_color=T.PURPLE_DIM,
                border_color_checked=T.PURPLE,
            ).pack(anchor="w", padx=T.PAD_CARD * 2, pady=T.SPACE_SM)

        ctk.CTkLabel(frame, text="Hostname", **T.label_secondary_kwargs()).pack(
            anchor="w", padx=T.PAD_CARD, pady=(T.SPACE_LG, T.SPACE_XS)
        )
        self._hostname_var = tk.StringVar(value=self._config["hostname"])
        ctk.CTkEntry(frame, textvariable=self._hostname_var, **T.input_kwargs()).pack(
            fill="x", padx=T.PAD_CARD
        )

        ctk.CTkLabel(frame, text="Default Username", **T.label_secondary_kwargs()).pack(
            anchor="w", padx=T.PAD_CARD, pady=(T.SPACE_MD, T.SPACE_XS)
        )
        self._user_var = tk.StringVar(value=self._config["username"])
        ctk.CTkEntry(frame, textvariable=self._user_var, **T.input_kwargs()).pack(
            fill="x", padx=T.PAD_CARD
        )

        self._nav_buttons(frame, on_next=self._step3_next)

    def _step3_next(self) -> None:
        self._config["base"] = self._base_var.get()
        self._config["hostname"] = self._hostname_var.get().strip() or "tyranos"
        self._config["username"] = self._user_var.get().strip() or "user"
        self._advance()

    def _render_step_security(self) -> None:
        frame = self._scroll_frame()
        ctk.CTkLabel(
            frame, text="Security Options", font=T.FONT_HEADING, text_color=T.TEXT_PRIMARY
        ).pack(anchor="w", padx=T.PAD_CARD, pady=(T.PAD_CARD, T.SPACE_LG))

        self._harden_var = tk.BooleanVar(value=self._config["hardening"])
        ctk.CTkCheckBox(
            frame,
            text="Apply CIS benchmarks & hardening",
            variable=self._harden_var,
            font=T.FONT_BODY,
            text_color=T.TEXT_PRIMARY,
            fg_color=T.SUCCESS,
            hover_color=T.SUCCESS,
            border_color=T.BORDER_ACCENT,
            checkmark_color=T.TEXT_WHITE,
        ).pack(anchor="w", padx=T.PAD_CARD * 2, pady=T.SPACE_SM)

        self._fw_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            frame,
            text="Enable nftables firewall",
            variable=self._fw_var,
            font=T.FONT_BODY,
            text_color=T.TEXT_PRIMARY,
            fg_color=T.SUCCESS,
            hover_color=T.SUCCESS,
            border_color=T.BORDER_ACCENT,
            checkmark_color=T.TEXT_WHITE,
        ).pack(anchor="w", padx=T.PAD_CARD * 2, pady=T.SPACE_SM)

        self._ssh_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            frame,
            text="Disable root SSH login",
            variable=self._ssh_var,
            font=T.FONT_BODY,
            text_color=T.TEXT_PRIMARY,
            fg_color=T.SUCCESS,
            hover_color=T.SUCCESS,
            border_color=T.BORDER_ACCENT,
            checkmark_color=T.TEXT_WHITE,
        ).pack(anchor="w", padx=T.PAD_CARD * 2, pady=T.SPACE_SM)

        self._nav_buttons(frame, on_next=self._step4_next)

    def _step4_next(self) -> None:
        self._config["hardening"] = self._harden_var.get()
        self._advance()

    def _render_step_build(self) -> None:
        frame = self._scroll_frame()
        ctk.CTkLabel(
            frame, text="Build Summary", font=T.FONT_HEADING, text_color=T.TEXT_PRIMARY
        ).pack(anchor="w", padx=T.PAD_CARD, pady=(T.PAD_CARD, T.SPACE_MD))

        summary = ctk.CTkFrame(frame, fg_color=T.BG_RAISED, corner_radius=T.RADIUS_SM)
        summary.pack(fill="x", padx=T.PAD_CARD, pady=(0, T.SPACE_LG))

        lines = [
            ("Type", self._config["distro_type"]),
            ("Base", self._config["base"]),
            ("Hostname", self._config["hostname"]),
            ("User", self._config["username"]),
            ("Apps", ", ".join(self._config["apps"]) or "None"),
            ("Hardening", "Yes" if self._config["hardening"] else "No"),
        ]
        for label, value in lines:
            row = ctk.CTkFrame(summary, fg_color="transparent")
            row.pack(fill="x", padx=T.PAD_CARD, pady=T.SPACE_XS)
            ctk.CTkLabel(
                row,
                text=f"{label}:",
                font=T.FONT_SMALL,
                text_color=T.TEXT_MUTED,
                width=100,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=value, font=T.FONT_SMALL, text_color=T.TEXT_PRIMARY, anchor="w"
            ).pack(side="left")

        self._progress_card = ProgressCard(frame, title="Build Progress", percentage=0)
        self._progress_card.pack(fill="x", padx=T.PAD_CARD, pady=(0, T.SPACE_MD))

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(padx=T.PAD_CARD, pady=(0, T.PAD_CARD))

        ctk.CTkButton(
            btn_row,
            text="← Back",
            **T.btn_outline_kwargs(),
            command=self._go_back,
        ).pack(side="left", padx=(0, T.SPACE_SM))

        self._build_btn = ctk.CTkButton(
            btn_row,
            text="🔨  Build ISO",
            **T.btn_primary_kwargs(),
            command=self._start_build,
        )
        self._build_btn.pack(side="left")

        self._build_label = ctk.CTkLabel(frame, text="", **T.label_secondary_kwargs())
        self._build_label.pack(pady=(T.SPACE_SM, 0))

    def _start_build(self) -> None:
        if self._building:
            return
        self._building = True
        self._build_btn.configure(state="disabled")
        self._build_label.configure(text="⟳  Building…", text_color=T.CYAN)
        threading.Thread(target=self._run_build, daemon=True).start()

    def _run_build(self) -> None:
        try:
            if self._engine and hasattr(self._engine, "build_distro"):
                import asyncio

                loop = asyncio.new_event_loop()
                for pct, msg in loop.run_until_complete(self._engine.build_distro(self._config)):
                    self._result_queue.put(("progress", (pct, msg)))
                loop.close()
                self._result_queue.put(("done", "ISO build complete!"))
            else:
                # Simulate progress for demo
                import time

                stages = [
                    (10, "Validating config…"),
                    (25, "Bootstrapping base…"),
                    (45, "Installing packages…"),
                    (65, "Applying config…"),
                    (80, "Applying security…"),
                    (95, "Creating ISO image…"),
                    (100, "Done!"),
                ]
                for pct, msg in stages:
                    time.sleep(0.6)
                    self._result_queue.put(("progress", (pct, msg)))
                self._result_queue.put(("done", "Build complete (simulated)."))
        except Exception as exc:
            self._result_queue.put(("build_error", str(exc)))

    def _check_results(self) -> None:
        try:
            kind, content = self._result_queue.get_nowait()
            if kind == "progress":
                pct, msg = content
                if hasattr(self, "_progress_card"):
                    self._progress_card.set_value(pct)
                if hasattr(self, "_build_label"):
                    self._build_label.configure(text=msg, text_color=T.CYAN)
            elif kind == "done":
                self._building = False
                if hasattr(self, "_build_label"):
                    self._build_label.configure(text=f"✓  {content}", text_color=T.SUCCESS)
                if hasattr(self, "_build_btn"):
                    self._build_btn.configure(state="normal")
            elif kind == "build_error":
                self._building = False
                if hasattr(self, "_build_label"):
                    self._build_label.configure(text=f"✗  {content}", text_color=T.ERROR)
                if hasattr(self, "_build_btn"):
                    self._build_btn.configure(state="normal")
        except queue.Empty:
            pass
        self.after(100, self._check_results)

    # ── Navigation helpers ────────────────────────────────────────────────────

    def _advance(self) -> None:
        self._step = min(self._step + 1, 4)
        self._render_step()

    def _go_back(self) -> None:
        self._step = max(self._step - 1, 0)
        self._render_step()

    def _reset_wizard(self) -> None:
        self._step = 0
        self._building = False
        self._config = {
            "distro_type": "Desktop",
            "base": "Arch Linux",
            "apps": [],
            "hardening": False,
            "hostname": "tyranos",
            "username": "user",
        }
        self._render_step()

    def _nav_buttons(
        self,
        frame: ctk.CTkFrame,
        back: bool = True,
        on_next: Callable | None = None,
    ) -> None:
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(padx=T.PAD_CARD, pady=T.PAD_CARD)
        if back:
            ctk.CTkButton(
                row,
                text="← Back",
                **T.btn_outline_kwargs(),
                command=self._go_back,
            ).pack(side="left", padx=(0, T.SPACE_SM))
        label = "Build →" if self._step == 3 else "Next →"
        ctk.CTkButton(
            row,
            text=label,
            **T.btn_primary_kwargs(),
            command=on_next or self._advance,
        ).pack(side="left")

    def _scroll_frame(self) -> ctk.CTkScrollableFrame:
        f = ctk.CTkScrollableFrame(
            self._content,
            fg_color="transparent",
            scrollbar_button_color=T.BG_RAISED,
            scrollbar_button_hover_color=T.PURPLE,
        )
        f.grid(row=0, column=0, sticky="nsew")
        f.grid_columnconfigure(0, weight=1)
        return f


class _SelectCard(ctk.CTkFrame):
    """Radio-style selection card for distro type picker."""

    def __init__(
        self,
        parent: tk.Widget,
        icon: str,
        title: str,
        desc: str,
        selected_var: tk.StringVar,
        value: str,
        **kwargs: object,
    ) -> None:
        super().__init__(
            parent,
            fg_color=T.BG_RAISED,
            corner_radius=T.RADIUS_CARD,
            border_color=T.BORDER_SUBTLE,
            border_width=1,
            width=180,
            height=100,
            **kwargs,  # type: ignore[arg-type]
        )
        self.grid_propagate(False)
        self._var = selected_var
        self._value = value

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            inner, text=f"{icon}  {title}", font=T.FONT_BODY_BOLD, text_color=T.TEXT_PRIMARY
        ).pack()
        ctk.CTkLabel(inner, text=desc, **T.label_secondary_kwargs(), wraplength=160).pack(
            pady=(T.SPACE_XS, 0)
        )

        self._var.trace_add("write", self._refresh)
        self._refresh()

        for w in [self, inner, *inner.winfo_children()]:
            w.bind("<Button-1>", self._select, add="+")
            w.bind("<Enter>", self._enter, add="+")
            w.bind("<Leave>", self._leave, add="+")

    def _select(self, _e: tk.Event) -> None:  # type: ignore[type-arg]
        self._var.set(self._value)

    def _refresh(self, *_args: object) -> None:
        selected = self._var.get() == self._value
        self.configure(border_color=T.PURPLE if selected else T.BORDER_SUBTLE)

    def _enter(self, _e: tk.Event) -> None:  # type: ignore[type-arg]
        if self._var.get() != self._value:
            self.configure(border_color=T.BORDER_ACCENT)

    def _leave(self, _e: tk.Event) -> None:  # type: ignore[type-arg]
        self._refresh()
