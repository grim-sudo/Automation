"""
Files view — a read-only filesystem browser.

Spec §7/§15: Archon can see the environment. A simple, safe, read-only browser
rooted at the user's home: click folders to descend, ".." to ascend. No writes,
deletes, or moves happen here — mutation stays behind the command surface and
its permission gate.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from .. import theme as T
from ..components.panel import KeyValue, Panel, hairline


def _fmt_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.0f} PB"


class FilesView(ctk.CTkFrame):
    """Read-only home-rooted file browser with a detail inspector."""

    def __init__(
        self,
        parent: tk.Widget,
        engine: object = None,
        on_navigate: Callable[[str], None] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, fg_color=T.BG_DEEP, **kwargs)  # type: ignore[arg-type]
        self._engine = engine
        self._cwd = Path.home()
        self._selected: Path | None = None
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=3, uniform="fv")
        self.grid_columnconfigure(1, weight=2, uniform="fv")
        self._build()
        self._list_dir()

    def _build(self) -> None:
        self._panel = Panel(self, title="Files")
        self._panel.grid(row=0, column=0, sticky="nsew",
                         padx=(T.PAD_PAGE, T.SPACE_MD), pady=T.PAD_PAGE)
        self._panel.body.grid_rowconfigure(1, weight=1)
        self._panel.body.grid_columnconfigure(0, weight=1)

        self._path_label = ctk.CTkLabel(
            self._panel.body, text="", font=T.FONT_CODE_SMALL,
            text_color=T.TEXT_ACCENT, anchor="w",
        )
        self._path_label.grid(row=0, column=0, sticky="ew", pady=(0, T.SPACE_SM))
        self._panel.add_action(
            ctk.CTkButton(self._panel.action_parent, text="Home", width=64, height=26,
                          **T.btn_ghost_kwargs(), command=self._go_home))

        self._listing = ctk.CTkScrollableFrame(
            self._panel.body, fg_color="transparent",
            scrollbar_button_color=T.BG_RAISED,
            scrollbar_button_hover_color=T.PURPLE,
        )
        self._listing.grid(row=1, column=0, sticky="nsew")
        self._listing.grid_columnconfigure(0, weight=1)

        insp = Panel(self, title="Details")
        insp.grid(row=0, column=1, sticky="nsew",
                  padx=(T.SPACE_MD, T.PAD_PAGE), pady=T.PAD_PAGE)
        insp.body.grid_columnconfigure(0, weight=1)
        self._kv: dict[str, KeyValue] = {}
        for key, label in (("name", "Name"), ("type", "Type"), ("size", "Size"),
                           ("items", "Items"), ("modified", "Modified"),
                           ("perms", "Mode")):
            kv = KeyValue(insp.body, label, "—")
            kv.pack(fill="x", pady=3)
            self._kv[key] = kv
        hairline(insp.body).pack(fill="x", pady=T.SPACE_MD)
        self._hint = ctk.CTkLabel(
            insp.body, text="Select an item to inspect it.",
            font=T.FONT_SMALL, text_color=T.TEXT_MUTED, wraplength=240,
            justify="left",
        )
        self._hint.pack(fill="x", anchor="w")

    def _go_home(self) -> None:
        self._cwd = Path.home()
        self._list_dir()

    def _descend(self, path: Path) -> None:
        self._cwd = path
        self._selected = None
        self._list_dir()

    def _list_dir(self) -> None:
        for child in self._listing.winfo_children():
            child.destroy()
        self._path_label.configure(text=str(self._cwd))

        if self._cwd != self._cwd.parent:
            self._row("..", self._cwd.parent, is_dir=True, is_up=True)

        try:
            entries = sorted(
                self._cwd.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except PermissionError:
            ctk.CTkLabel(self._listing, text="Permission denied.",
                         font=T.FONT_SMALL, text_color=T.ERROR).pack(pady=T.SPACE_LG)
            return
        except Exception as exc:
            ctk.CTkLabel(self._listing, text=str(exc)[:80],
                         font=T.FONT_SMALL, text_color=T.ERROR).pack(pady=T.SPACE_LG)
            return

        for entry in entries:
            if entry.name.startswith("."):
                continue
            try:
                is_dir = entry.is_dir()
            except OSError:
                continue
            self._row(entry.name, entry, is_dir=is_dir)

    def _row(self, name: str, path: Path, is_dir: bool, is_up: bool = False) -> None:
        row = ctk.CTkFrame(self._listing, fg_color="transparent",
                           corner_radius=T.RADIUS_SM, height=30)
        row.pack(fill="x", pady=1)
        row.pack_propagate(False)
        glyph = "↰" if is_up else ("▸" if is_dir else "·")
        ctk.CTkLabel(row, text=glyph, font=(T.FONT_FAMILY_MONO, 12),
                     text_color=T.GOLD if is_dir else T.TEXT_DIM, width=18).pack(
            side="left", padx=(T.SPACE_SM, 4))
        ctk.CTkLabel(row, text=name, font=T.FONT_SMALL,
                     text_color=T.TEXT_PRIMARY if is_dir else T.TEXT_SECONDARY,
                     anchor="w").pack(side="left", fill="x", expand=True)

        def _hover(_e: tk.Event, r=row) -> None:  # type: ignore[type-arg]
            r.configure(fg_color=T.BG_RAISED)

        def _leave(_e: tk.Event, r=row) -> None:  # type: ignore[type-arg]
            r.configure(fg_color="transparent")

        def _click(_e: tk.Event, p=path, d=is_dir) -> None:  # type: ignore[type-arg]
            if d:
                self._descend(p)
            else:
                self._inspect(p)

        for w in (row, *row.winfo_children()):
            w.bind("<Enter>", _hover, add="+")
            w.bind("<Leave>", _leave, add="+")
            w.bind("<Button-1>", _click, add="+")

    def _inspect(self, path: Path) -> None:
        self._selected = path
        self._hint.configure(text="")
        try:
            st = path.stat()
            from datetime import datetime

            self._kv["name"].set(path.name[:28])
            self._kv["type"].set("Directory" if path.is_dir() else
                                 (path.suffix[1:].upper() + " file") if path.suffix
                                 else "File")
            self._kv["size"].set(_fmt_size(st.st_size) if path.is_file() else "—")
            if path.is_dir():
                try:
                    self._kv["items"].set(str(sum(1 for _ in path.iterdir())))
                except Exception:
                    self._kv["items"].set("—")
            else:
                self._kv["items"].set("—")
            self._kv["modified"].set(
                datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"))
            self._kv["perms"].set(oct(st.st_mode & 0o777)[2:])
        except Exception as exc:
            self._hint.configure(text=str(exc)[:80], text_color=T.ERROR)
