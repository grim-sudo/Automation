"""
Chat page — AI conversation interface with streaming and context panel.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable
from datetime import datetime

import customtkinter as ctk

from .. import theme as T
from ..components.chat_bubble import ChatBubble
from ..components.typing_indicator import TypingIndicator
from ..particles import draw_archon_sigil

_SUGGESTIONS = [
    ("◇", "Create a Python project", "Flask, FastAPI, or Django with your stack"),
    ("▤", "Set up Docker", "Containers, compose, or Kubernetes"),
    ("⬡", "Build a custom OS", "A Linux distro tuned for your needs"),
    ("◈", "Automate with n8n", "Wire workflows between your apps"),
]


class ChatPage(ctk.CTkFrame):
    """
    Full chat interface with message history, streaming, and context panel.
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
        self._messages: list[dict] = []
        self._streaming = False
        self._result_queue: queue.Queue = queue.Queue()

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_topbar()
        self._build_body()
        self._build_input()
        self._check_results()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_topbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color=T.BG_SURFACE, corner_radius=0, height=52)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=1)

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right", padx=T.PAD_CARD)

        ctk.CTkButton(
            right,
            text="+ New",
            width=70,
            **T.btn_outline_kwargs(),
            command=self._new_chat,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            right,
            text="✕",
            width=34,
            **T.btn_ghost_kwargs(),
            command=self._clear_history,
        ).pack(side="left")

    def _build_body(self) -> None:
        self._conv_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=T.BG_DEEP,
            scrollbar_button_color=T.BG_RAISED,
            scrollbar_button_hover_color=T.PURPLE,
        )
        self._conv_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self._conv_frame.grid_columnconfigure(0, weight=1)

        self._typing_indicator: TypingIndicator | None = None
        self._show_welcome()

    def _build_input(self) -> None:
        input_bar = ctk.CTkFrame(
            self,
            fg_color=T.BG_SURFACE,
            corner_radius=0,
            border_color=T.BORDER_SUBTLE,
            border_width=0,
        )
        input_bar.grid(row=2, column=0, columnspan=2, sticky="ew")

        inner = ctk.CTkFrame(input_bar, fg_color="transparent")
        inner.pack(fill="x", padx=T.PAD_CARD, pady=T.SPACE_SM)
        inner.grid_columnconfigure(0, weight=1)

        self._input = ctk.CTkTextbox(
            inner,
            height=72,
            fg_color=T.BG_RAISED,
            border_color=T.BORDER_SUBTLE,
            text_color=T.TEXT_PRIMARY,
            font=T.FONT_BODY,
            corner_radius=T.RADIUS_INPUT,
            wrap="word",
        )
        self._input.grid(row=0, column=0, sticky="ew", padx=(0, T.SPACE_SM))
        self._input.insert("1.0", "")

        # Placeholder simulation
        self._placeholder = "Message Archon…"
        self._show_placeholder()
        self._input.bind("<FocusIn>", self._on_focus_in)
        self._input.bind("<FocusOut>", self._on_focus_out)
        self._input.bind("<Return>", self._on_return)
        self._input.bind("<Control-Return>", lambda _e: self._send())
        self._input.bind("<KeyRelease>", self._on_key_release)

        self._send_btn = ctk.CTkButton(
            inner,
            text="➤",
            width=56,
            height=72,
            **T.btn_primary_kwargs(),
            command=self._send,
        )
        self._send_btn.grid(row=0, column=1)
        self._send_btn.configure(state="disabled", font=(T.FONT_FAMILY, 18, "bold"))

        # Bottom hint row
        hint = ctk.CTkFrame(inner, fg_color="transparent")
        hint.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ctk.CTkLabel(
            hint,
            text="Ctrl+Enter to send  ·  Enter for newline",
            **T.label_secondary_kwargs(),
        ).pack(side="left")

    # ── Interaction ───────────────────────────────────────────────────────────

    def _show_welcome(self) -> None:
        for child in self._conv_frame.winfo_children():
            child.destroy()

        welcome = ctk.CTkFrame(self._conv_frame, fg_color="transparent")
        welcome.pack(fill="both", expand=True, pady=T.SPACE_2XL)

        # Monumental emblem.
        emblem = tk.Canvas(
            welcome, width=112, height=112, bg=T.BG_DEEP, highlightthickness=0
        )
        draw_archon_sigil(emblem, size=112, phase=0.6)
        emblem.pack()

        ctk.CTkLabel(
            welcome,
            text="How can I help, Commander?",
            font=T.FONT_HEADING,
            text_color=T.TEXT_PRIMARY,
        ).pack(pady=(T.SPACE_LG, T.SPACE_XS))
        ctk.CTkLabel(
            welcome,
            text="Ask a question, or describe what you want to build or automate.",
            font=T.FONT_BODY,
            text_color=T.TEXT_SECONDARY,
        ).pack()

        # Gold hairline divider.
        rule = ctk.CTkFrame(welcome, height=1, fg_color=T.BORDER_ACCENT, width=360)
        rule.pack(pady=T.SPACE_LG)

        grid = ctk.CTkFrame(welcome, fg_color="transparent")
        grid.pack(pady=(0, T.SPACE_LG))

        for idx, (icon, title, desc) in enumerate(_SUGGESTIONS):
            row, col = divmod(idx, 2)
            card = _SuggestionCard(
                grid,
                icon=icon,
                title=title,
                desc=desc,
                on_click=lambda t=title: self._fill_and_send(t),
            )
            card.grid(row=row, column=col, padx=8, pady=8)

    def _fill_and_send(self, text: str) -> None:
        self._clear_placeholder()
        self._input.delete("1.0", "end")
        self._input.insert("1.0", text)
        self._send()

    def _send(self) -> None:
        if self._streaming:
            return
        text = self._get_input_text()
        if not text:
            return

        self._clear_input()
        self._send_btn.configure(state="disabled")

        # Clear welcome if first message
        if not self._messages:
            for child in self._conv_frame.winfo_children():
                child.destroy()

        self._add_bubble(text, "user")
        self._messages.append({"role": "user", "content": text})
        self._show_typing()
        self._streaming = True
        threading.Thread(target=self._run_query, args=(text,), daemon=True).start()

    def _run_query(self, text: str) -> None:
        try:
            if self._engine and hasattr(self._engine, "chat"):
                history = [
                    {"role": m["role"], "content": m["content"]} for m in self._messages[:-1]
                ]
                result = self._engine.chat(text, history)
                if result.get("kind") == "conversation":
                    response = result.get("reply", "No response.")
                else:
                    inner = result.get("result")
                    response = str(inner if inner is not None else result.get("error", "Done."))
            elif self._engine and hasattr(self._engine, "execute"):
                result = self._engine.execute(text)
                response = str(result.get("result", result.get("error", "No response.")))
            else:
                response = (
                    f"Archon received: '{text}'\n\n"
                    "To enable AI responses, configure your OpenRouter API key in Settings."
                )
            self._result_queue.put(("response", response))
        except Exception as exc:
            self._result_queue.put(("error", f"Could not process request: {exc}"))

    def _check_results(self) -> None:
        try:
            msg_type, content = self._result_queue.get_nowait()
            self._hide_typing()
            self._streaming = False
            if msg_type == "response":
                self._add_bubble(content, "assistant")
                self._messages.append({"role": "assistant", "content": content})
            else:
                self._add_bubble(content, "error")
            self._send_btn.configure(state="normal")
        except queue.Empty:
            pass
        self.after(100, self._check_results)

    def _add_bubble(self, text: str, role: str) -> None:
        ts = datetime.now().strftime("%H:%M")
        bubble = ChatBubble(self._conv_frame, text=text, role=role, timestamp=ts)
        bubble.pack(fill="x", padx=T.SPACE_SM, pady=2)
        self._scroll_to_bottom()

    def _show_typing(self) -> None:
        row = ctk.CTkFrame(self._conv_frame, fg_color="transparent")
        row.pack(fill="x", padx=T.SPACE_SM, pady=4)

        indicator = TypingIndicator(row)
        indicator.pack(side="left", padx=(52, 0))
        indicator.start()
        self._typing_indicator = indicator
        self._typing_row = row
        self._scroll_to_bottom()

    def _hide_typing(self) -> None:
        try:
            if hasattr(self, "_typing_row"):
                self._typing_row.destroy()
        except Exception:
            pass

    def _scroll_to_bottom(self) -> None:
        self.after(50, lambda: self._conv_frame._parent_canvas.yview_moveto(1.0))  # type: ignore[attr-defined]

    def _new_chat(self) -> None:
        self._messages = []
        self._streaming = False
        self._show_welcome()

    def _clear_history(self) -> None:
        self._new_chat()

    # ── Input helpers ──────────────────────────────────────────────────────────

    def _get_input_text(self) -> str:
        text = self._input.get("1.0", "end").strip()
        if text == self._placeholder:
            return ""
        return text

    def _clear_input(self) -> None:
        self._input.delete("1.0", "end")
        self._show_placeholder()

    def _show_placeholder(self) -> None:
        if not self._input.get("1.0", "end").strip():
            self._input.insert("1.0", self._placeholder)
            self._input.configure(text_color=T.TEXT_MUTED)

    def _clear_placeholder(self) -> None:
        if self._input.get("1.0", "end").strip() == self._placeholder:
            self._input.delete("1.0", "end")
        self._input.configure(text_color=T.TEXT_PRIMARY)

    def _on_focus_in(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        self._clear_placeholder()
        self._input.configure(border_width=1, border_color=T.PURPLE)

    def _on_focus_out(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        self._show_placeholder()
        self._input.configure(border_width=1, border_color=T.BORDER_SUBTLE)

    def _on_return(self, event: tk.Event) -> str:  # type: ignore[type-arg]
        # Enter = newline; Ctrl+Enter = send (handled via bind above)
        return ""

    def _on_key_release(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        text = self._get_input_text()
        state = "normal" if text else "disabled"
        self._send_btn.configure(state=state)


class _SuggestionCard(ctk.CTkFrame):
    """Clickable suggestion card on the welcome screen."""

    def __init__(
        self,
        parent: tk.Widget,
        icon: str,
        title: str,
        desc: str,
        on_click: Callable | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(
            parent,
            fg_color=T.BG_SURFACE,
            corner_radius=T.RADIUS_CARD,
            border_color=T.BORDER_SUBTLE,
            border_width=1,
            width=268,
            height=96,
            **kwargs,  # type: ignore[arg-type]
        )
        self.grid_propagate(False)
        self._on_click = on_click

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=T.SPACE_MD, pady=T.SPACE_MD)

        # Gold icon badge.
        badge = ctk.CTkFrame(
            inner, fg_color=T.PURPLE_GLOW, corner_radius=T.RADIUS_SM, width=34, height=34
        )
        badge.pack(side="left", anchor="n", padx=(0, T.SPACE_SM))
        badge.pack_propagate(False)
        ctk.CTkLabel(
            badge, text=icon, font=(T.FONT_FAMILY, 16), text_color=T.TEXT_ACCENT
        ).pack(expand=True)

        text_col = ctk.CTkFrame(inner, fg_color="transparent")
        text_col.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(
            text_col, text=title, font=T.FONT_BODY_BOLD, text_color=T.TEXT_PRIMARY, anchor="w"
        ).pack(anchor="w")
        ctk.CTkLabel(
            text_col,
            text=desc,
            **T.label_secondary_kwargs(),
            wraplength=190,
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        self._badge = badge
        for w in [self, inner, text_col, *text_col.winfo_children()]:
            w.bind("<Button-1>", self._clicked, add="+")
            w.bind("<Enter>", self._enter, add="+")
            w.bind("<Leave>", self._leave, add="+")

    def _clicked(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._on_click:
            self._on_click()

    def _enter(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        self.configure(border_color=T.PURPLE, fg_color=T.BG_RAISED)

    def _leave(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        self.configure(border_color=T.BORDER_SUBTLE, fg_color=T.BG_SURFACE)
