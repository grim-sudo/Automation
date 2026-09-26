"""
CommandPalette — the universal Ctrl+Space command surface.

Spec §22: keyboard-first, fast, minimal. A dark overlay with a single query
field, recent operations, and capability quick-links. Typing filters both
navigation destinations and free-text commands; Enter on free text hands off to
the command handler, Enter on a destination navigates.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from .. import theme as T


class CommandPalette(ctk.CTkFrame):
    """Overlay palette. Construct once over the app root; call ``open()``/``close()``."""

    def __init__(
        self,
        parent: tk.Widget,
        destinations: list[tuple[str, str]],
        on_navigate: Callable[[str], None],
        on_command: Callable[[str], None],
        recents: Callable[[], list[str]] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, fg_color=T.VOID, corner_radius=0,
                         **kwargs)  # type: ignore[arg-type]
        self._parent = parent
        self._destinations = destinations  # (key, label)
        self._on_navigate = on_navigate
        self._on_command = on_command
        self._recents = recents
        self._open = False
        self._result_rows: list[ctk.CTkFrame] = []
        self._selection = 0
        self._matches: list[tuple[str, str, str]] = []  # (kind, key/text, label)
        self._build()

    def _build(self) -> None:
        # Centered panel.
        self._panel = ctk.CTkFrame(
            self, fg_color=T.CHARCOAL, corner_radius=T.RADIUS_PANEL,
            border_color=T.BORDER_ACCENT, border_width=1, width=620,
        )
        self._panel.place(relx=0.5, rely=0.28, anchor="n")

        entry_row = ctk.CTkFrame(self._panel, fg_color="transparent")
        entry_row.pack(fill="x", padx=T.SPACE_MD, pady=(T.SPACE_MD, T.SPACE_SM))
        ctk.CTkLabel(entry_row, text="❯", font=(T.FONT_FAMILY_MONO, 18, "bold"),
                     text_color=T.GOLD).pack(side="left", padx=(4, 10))
        self._entry = ctk.CTkEntry(
            entry_row, placeholder_text="Search Archon…",
            fg_color="transparent", border_width=0,
            text_color=T.TEXT_PRIMARY, font=(T.FONT_FAMILY, 16),
            placeholder_text_color=T.TEXT_MUTED,
        )
        self._entry.pack(side="left", fill="x", expand=True)
        self._entry.bind("<KeyRelease>", self._on_type)
        self._entry.bind("<Return>", self._on_enter)
        self._entry.bind("<Escape>", lambda _e: self.close())
        self._entry.bind("<Down>", lambda _e: self._move(1))
        self._entry.bind("<Up>", lambda _e: self._move(-1))

        ctk.CTkFrame(self._panel, height=1, fg_color=T.BORDER_SUBTLE).pack(fill="x")

        self._results = ctk.CTkFrame(self._panel, fg_color="transparent")
        self._results.pack(fill="both", expand=True, padx=T.SPACE_SM,
                           pady=(T.SPACE_SM, T.SPACE_MD))

        # Dismiss when clicking the dimmed backdrop.
        self.bind("<Button-1>", self._maybe_dismiss)

    # ── Open / close ──────────────────────────────────────────────────────────

    def open(self) -> None:
        if self._open:
            return
        self._open = True
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lift()
        self._entry.delete(0, "end")
        self._entry.focus_set()
        self._refresh("")

    def close(self) -> None:
        self._open = False
        self.place_forget()

    def toggle(self) -> None:
        self.close() if self._open else self.open()

    def _maybe_dismiss(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        # Clicks that land on the backdrop (this frame) close; clicks inside the
        # panel are absorbed by child widgets.
        if event.widget is self:
            self.close()

    # ── Filtering ───────────────────────────────────────────────────────────────

    def _on_type(self, _e: tk.Event) -> None:  # type: ignore[type-arg]
        self._refresh(self._entry.get().strip())

    def _refresh(self, query: str) -> None:
        for r in self._result_rows:
            r.destroy()
        self._result_rows.clear()
        self._matches.clear()
        self._selection = 0
        q = query.lower()

        # Recents (only when query is empty).
        if not q and self._recents:
            recents = self._recents()[:4]
            if recents:
                self._section("RECENT")
                for text in recents:
                    self._matches.append(("command", text, text))
                    self._row(text, "run")

        # Destination matches.
        dests = [(k, lbl) for k, lbl in self._destinations if q in lbl.lower()]
        if dests:
            self._section("GO TO")
            for key, lbl in dests[:8]:
                self._matches.append(("nav", key, lbl))
                self._row(lbl, "view")

        # Free-text command fallback.
        if q:
            self._matches.append(("command", query, f"Run  “{query}”"))
            self._section("COMMAND")
            self._row(f"Run  “{query}”", "execute")

        self._highlight()

    def _section(self, text: str) -> None:
        lbl = ctk.CTkLabel(self._results, text=text,
                           font=(T.FONT_FAMILY, 10, "bold"),
                           text_color=T.TEXT_MUTED, anchor="w")
        lbl.pack(fill="x", padx=T.SPACE_SM, pady=(T.SPACE_SM, 2))
        self._result_rows.append(lbl)  # type: ignore[arg-type]

    def _row(self, label: str, tag: str) -> None:
        idx = len([m for m in self._result_rows if isinstance(m, ctk.CTkFrame)])
        row = ctk.CTkFrame(self._results, fg_color="transparent",
                           corner_radius=T.RADIUS_SM, height=34)
        row.pack(fill="x", padx=T.SPACE_SM, pady=1)
        row.pack_propagate(False)
        ctk.CTkLabel(row, text=label, font=T.FONT_BODY, text_color=T.TEXT_PRIMARY,
                     anchor="w").pack(side="left", padx=T.SPACE_SM)
        ctk.CTkLabel(row, text=tag.upper(), font=T.FONT_CODE_SMALL,
                     text_color=T.TEXT_DIM).pack(side="right", padx=T.SPACE_SM)
        my_index = idx
        row.bind("<Button-1>", lambda _e, i=my_index: self._activate(i))
        for child in row.winfo_children():
            child.bind("<Button-1>", lambda _e, i=my_index: self._activate(i))
        self._result_rows.append(row)

    def _frame_rows(self) -> list[ctk.CTkFrame]:
        return [r for r in self._result_rows if isinstance(r, ctk.CTkFrame)]

    def _move(self, delta: int) -> None:
        rows = self._frame_rows()
        if not rows:
            return
        self._selection = (self._selection + delta) % len(rows)
        self._highlight()

    def _highlight(self) -> None:
        for i, row in enumerate(self._frame_rows()):
            row.configure(fg_color=T.STEEL if i == self._selection else "transparent")

    def _on_enter(self, _e: tk.Event) -> None:  # type: ignore[type-arg]
        self._activate(self._selection)

    def _activate(self, index: int) -> None:
        if not (0 <= index < len(self._matches)):
            return
        kind, key, _label = self._matches[index]
        self.close()
        if kind == "nav":
            self._on_navigate(key)
        else:
            self._on_command(key)
