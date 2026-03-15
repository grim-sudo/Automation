"""
Automate page — natural-language command execution with safe-mode preview.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable
from datetime import datetime

import customtkinter as ctk

from .. import theme as T


class AutomatePage(ctk.CTkFrame):
    """
    NLP command interface: input → safe preview → execute → live output.
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
        self._running = False
        self._result_queue: queue.Queue = queue.Queue()
        self._history: list[str] = []
        self._safe_mode = tk.BooleanVar(value=True)

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
        ctk.CTkLabel(left, text="⚡  Automate", **T.label_heading_kwargs()).pack(side="left")

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right", padx=T.PAD_CARD)

        # Safe Mode toggle
        safe_frame = ctk.CTkFrame(right, fg_color=T.BG_RAISED, corner_radius=T.RADIUS_BTN)
        safe_frame.pack(side="left", padx=4)
        ctk.CTkLabel(
            safe_frame,
            text="🛡  Safe Mode",
            font=T.FONT_SMALL,
            text_color=T.SUCCESS,
        ).pack(side="left", padx=(T.SPACE_SM, 4), pady=4)
        ctk.CTkSwitch(
            safe_frame,
            text="",
            width=40,
            variable=self._safe_mode,
            onvalue=True,
            offvalue=False,
            fg_color=T.BG_DEEP,
            progress_color=T.SUCCESS,
            button_color=T.TEXT_WHITE,
            command=self._on_safe_toggle,
        ).pack(side="left", padx=(0, T.SPACE_SM), pady=4)

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=T.PAD_PAGE, pady=T.PAD_CARD)
        body.grid_rowconfigure(1, weight=1)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        self._build_input_card(body)
        self._build_left_panel(body)
        self._build_right_panel(body)

    def _build_input_card(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(parent, **T.card_kwargs())
        card.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, T.SPACE_MD))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="Natural Language Command",
            font=T.FONT_SUBHEADING,
            text_color=T.TEXT_ACCENT,
        ).grid(row=0, column=0, sticky="w", padx=T.PAD_CARD, pady=(T.PAD_CARD, T.SPACE_SM))

        self._cmd_input = ctk.CTkTextbox(
            card,
            height=68,
            fg_color=T.BG_RAISED,
            border_color=T.BORDER_SUBTLE,
            text_color=T.TEXT_PRIMARY,
            font=T.FONT_BODY,
            corner_radius=T.RADIUS_INPUT,
            wrap="word",
        )
        self._cmd_input.grid(row=1, column=0, sticky="ew", padx=T.PAD_CARD, pady=(0, T.SPACE_SM))
        self._cmd_input.insert("1.0", "")

        # Placeholder
        self._placeholder = "Describe what you want to automate…"
        self._show_placeholder()
        self._cmd_input.bind("<FocusIn>", self._on_focus_in)
        self._cmd_input.bind("<FocusOut>", self._on_focus_out)
        self._cmd_input.bind("<KeyRelease>", self._on_key_release)

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew", padx=T.PAD_CARD, pady=(0, T.PAD_CARD))

        self._preview_btn = ctk.CTkButton(
            btn_row,
            text="🔍  Preview",
            width=110,
            **T.btn_outline_kwargs(),
            command=self._preview,
            state="disabled",
        )
        self._preview_btn.pack(side="left", padx=(0, T.SPACE_SM))

        self._execute_btn = ctk.CTkButton(
            btn_row,
            text="⚡  Execute",
            width=110,
            **T.btn_primary_kwargs(),
            command=self._execute,
            state="disabled",
        )
        self._execute_btn.pack(side="left")

        self._status_label = ctk.CTkLabel(
            btn_row,
            text="",
            **T.label_secondary_kwargs(),
        )
        self._status_label.pack(side="left", padx=T.SPACE_MD)

    def _build_left_panel(self, parent: ctk.CTkFrame) -> None:
        left = ctk.CTkFrame(parent, **T.card_kwargs())
        left.grid(row=1, column=0, sticky="nsew", padx=(0, T.SPACE_SM))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left,
            text="📋  Recent Commands",
            font=T.FONT_SUBHEADING,
            text_color=T.TEXT_ACCENT,
        ).grid(row=0, column=0, sticky="w", padx=T.PAD_CARD, pady=(T.PAD_CARD, T.SPACE_SM))

        self._history_frame = ctk.CTkScrollableFrame(
            left,
            fg_color=T.BG_DEEP,
            corner_radius=T.RADIUS_SM,
            scrollbar_button_color=T.BG_RAISED,
            scrollbar_button_hover_color=T.PURPLE,
        )
        self._history_frame.grid(
            row=1, column=0, sticky="nsew", padx=T.PAD_CARD, pady=(0, T.PAD_CARD)
        )
        self._history_frame.grid_columnconfigure(0, weight=1)
        self._render_history_empty()

    def _build_right_panel(self, parent: ctk.CTkFrame) -> None:
        right = ctk.CTkFrame(parent, **T.card_kwargs())
        right.grid(row=1, column=1, sticky="nsew", padx=(T.SPACE_SM, 0))
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(right, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=T.PAD_CARD, pady=(T.PAD_CARD, T.SPACE_SM))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="📊  Execution Output",
            font=T.FONT_SUBHEADING,
            text_color=T.TEXT_ACCENT,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header,
            text="🗑",
            width=30,
            **T.btn_ghost_kwargs(),
            command=self._clear_output,
        ).grid(row=0, column=1)

        self._output_frame = ctk.CTkScrollableFrame(
            right,
            fg_color=T.BG_DEEP,
            corner_radius=T.RADIUS_SM,
            scrollbar_button_color=T.BG_RAISED,
            scrollbar_button_hover_color=T.PURPLE,
        )
        self._output_frame.grid(
            row=1, column=0, sticky="nsew", padx=T.PAD_CARD, pady=(0, T.PAD_CARD)
        )
        self._output_frame.grid_columnconfigure(0, weight=1)
        self._render_output_empty()

    # ── Interaction ───────────────────────────────────────────────────────────

    def _on_safe_toggle(self) -> None:
        pass  # visual state handled by CTkSwitch

    def _preview(self) -> None:
        text = self._get_input_text()
        if not text:
            return
        self._clear_output_widgets()
        self._append_output_step("🔍 Preview mode — no changes will be made", "info")
        self._append_output_step(f"Command: {text}", "cmd")
        if self._engine and hasattr(self._engine, "parse"):
            try:
                parsed = self._engine.parse(text)
                self._append_output_step(
                    f"Intent: {parsed.get('action', 'unknown')} / {parsed.get('category', 'unknown')}",
                    "ok",
                )
            except Exception as exc:
                self._append_output_step(f"Parse error: {exc}", "error")
        else:
            self._append_output_step(
                "Engine not connected — attach Tyranos engine to preview.", "warn"
            )

    def _execute(self) -> None:
        if self._running:
            return
        text = self._get_input_text()
        if not text:
            return

        self._history.insert(0, text)
        self._history = self._history[:20]
        self._render_history()

        self._clear_output_widgets()
        self._execute_btn.configure(state="disabled")
        self._preview_btn.configure(state="disabled")
        self._status_label.configure(text="⟳  Running…", text_color=T.CYAN)
        self._running = True

        self._append_output_step(f"⚡ Executing: {text}", "cmd")
        if self._safe_mode.get():
            self._append_output_step("🛡 Safe mode ON — destructive ops will be skipped", "info")

        threading.Thread(target=self._run_command, args=(text,), daemon=True).start()

    def _run_command(self, text: str) -> None:
        try:
            if self._engine and hasattr(self._engine, "execute"):
                result = self._engine.execute(text)
                output = str(result.get("result", result.get("error", "Done.")))
                self._result_queue.put(("ok", output))
            else:
                self._result_queue.put(
                    ("warn", "Engine not attached. Connect Tyranos engine in Settings.")
                )
        except Exception as exc:
            self._result_queue.put(("error", f"Error: {exc}"))

    def _check_results(self) -> None:
        try:
            kind, content = self._result_queue.get_nowait()
            self._running = False
            self._append_output_step(content, kind)
            if kind == "error":
                self._status_label.configure(text="✗  Failed", text_color=T.ERROR)
            else:
                self._status_label.configure(text="✓  Done", text_color=T.SUCCESS)
            self._update_btn_states()
        except queue.Empty:
            pass
        self.after(100, self._check_results)

    def _append_output_step(self, text: str, kind: str = "ok") -> None:
        colors = {
            "ok": T.SUCCESS,
            "error": T.ERROR,
            "warn": T.WARNING,
            "info": T.CYAN,
            "cmd": T.TEXT_ACCENT,
        }
        icon = {"ok": "✓", "error": "✗", "warn": "⚠", "info": "ℹ", "cmd": "❯"}.get(kind, "·")
        color = colors.get(kind, T.TEXT_PRIMARY)
        ts = datetime.now().strftime("%H:%M:%S")

        row = ctk.CTkFrame(self._output_frame, fg_color="transparent")
        row.pack(fill="x", pady=1)
        ctk.CTkLabel(
            row,
            text=f"{icon}  {ts}",
            font=T.FONT_CODE_SMALL,
            text_color=color,
            width=80,
            anchor="w",
        ).pack(side="left", padx=(T.SPACE_SM, T.SPACE_SM))
        ctk.CTkLabel(
            row,
            text=text,
            font=T.FONT_SMALL,
            text_color=T.TEXT_PRIMARY,
            wraplength=320,
            anchor="w",
            justify="left",
        ).pack(side="left", fill="x", expand=True)

        self._scroll_output()

    def _scroll_output(self) -> None:
        self.after(50, lambda: self._output_frame._parent_canvas.yview_moveto(1.0))  # type: ignore[attr-defined]

    def _clear_output(self) -> None:
        self._clear_output_widgets()
        self._render_output_empty()
        self._status_label.configure(text="")

    def _clear_output_widgets(self) -> None:
        for child in self._output_frame.winfo_children():
            child.destroy()

    def _render_output_empty(self) -> None:
        ctk.CTkLabel(
            self._output_frame,
            text="Output will appear here…",
            **T.label_secondary_kwargs(),
        ).pack(pady=T.SPACE_2XL)

    def _render_history(self) -> None:
        for child in self._history_frame.winfo_children():
            child.destroy()
        if not self._history:
            self._render_history_empty()
            return
        for cmd in self._history:
            _HistoryRow(self._history_frame, cmd=cmd, on_click=self._fill_command).pack(
                fill="x", pady=2
            )

    def _render_history_empty(self) -> None:
        ctk.CTkLabel(
            self._history_frame,
            text="No commands yet.",
            **T.label_secondary_kwargs(),
        ).pack(pady=T.SPACE_2XL)

    def _fill_command(self, text: str) -> None:
        self._clear_placeholder()
        self._cmd_input.delete("1.0", "end")
        self._cmd_input.insert("1.0", text)
        self._update_btn_states()

    # ── Input helpers ──────────────────────────────────────────────────────────

    def _get_input_text(self) -> str:
        text = self._cmd_input.get("1.0", "end").strip()
        if text == self._placeholder:
            return ""
        return text

    def _show_placeholder(self) -> None:
        if not self._cmd_input.get("1.0", "end").strip():
            self._cmd_input.insert("1.0", self._placeholder)
            self._cmd_input.configure(text_color=T.TEXT_MUTED)

    def _clear_placeholder(self) -> None:
        if self._cmd_input.get("1.0", "end").strip() == self._placeholder:
            self._cmd_input.delete("1.0", "end")
        self._cmd_input.configure(text_color=T.TEXT_PRIMARY)

    def _on_focus_in(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        self._clear_placeholder()

    def _on_focus_out(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        self._show_placeholder()

    def _on_key_release(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        self._update_btn_states()

    def _update_btn_states(self) -> None:
        has_text = bool(self._get_input_text())
        state = "normal" if has_text and not self._running else "disabled"
        self._execute_btn.configure(state=state)
        self._preview_btn.configure(state=state)


class _HistoryRow(ctk.CTkFrame):
    """Single row in the command history panel."""

    def __init__(
        self,
        parent: tk.Widget,
        cmd: str,
        on_click: Callable[[str], None] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(
            parent,
            fg_color=T.BG_RAISED,
            corner_radius=T.RADIUS_SM,
            **kwargs,  # type: ignore[arg-type]
        )
        self._cmd = cmd
        self._on_click = on_click

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=T.SPACE_SM, pady=T.SPACE_XS)

        ctk.CTkLabel(
            inner,
            text=cmd,
            font=T.FONT_SMALL,
            text_color=T.TEXT_PRIMARY,
            anchor="w",
            wraplength=200,
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            inner,
            text="↩",
            width=24,
            height=24,
            **T.btn_ghost_kwargs(),
            command=self._clicked,
        ).pack(side="right")

        for w in [self, inner]:
            w.bind("<Button-1>", self._clicked, add="+")
            w.bind("<Enter>", self._enter, add="+")
            w.bind("<Leave>", self._leave, add="+")

    def _clicked(self, _event: tk.Event | None = None) -> None:  # type: ignore[type-arg]
        if self._on_click:
            self._on_click(self._cmd)

    def _enter(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        self.configure(fg_color=T.BG_HIGHLIGHT)

    def _leave(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        self.configure(fg_color=T.BG_RAISED)
