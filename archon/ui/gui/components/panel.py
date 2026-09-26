"""
Panel — the primary content container for the Archon command center.

Spec §28: prefer panels over cards. A panel is a bordered charcoal surface with
an optional header (title + eyebrow + trailing action slot) and a body frame
that callers fill. Borders, not shadows, carry the material hierarchy.
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from .. import theme as T


class Panel(ctk.CTkFrame):
    """
    A titled content panel.

    Parameters
    ----------
    parent : tk.Widget
    title : str
        Section title (rendered small-caps style). Empty for a bare panel.
    eyebrow : str
        Optional monospace label above the title (e.g. a code / ID).
    raised : bool
        Use the elevated graphite surface instead of charcoal.
    """

    def __init__(
        self,
        parent: tk.Widget,
        title: str = "",
        eyebrow: str = "",
        raised: bool = False,
        **kwargs: object,
    ) -> None:
        base = T.panel_raised_kwargs() if raised else T.panel_kwargs()
        base.update(kwargs)  # type: ignore[arg-type]
        super().__init__(parent, **base)  # type: ignore[arg-type]

        self.grid_columnconfigure(0, weight=1)
        self._header: ctk.CTkFrame | None = None
        self.body: ctk.CTkFrame

        row = 0
        if title or eyebrow:
            self._header = self._build_header(title, eyebrow)
            self._header.grid(row=0, column=0, sticky="ew", padx=T.SPACE_MD,
                              pady=(T.SPACE_MD, T.SPACE_SM))
            row = 1

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=row, column=0, sticky="nsew",
                       padx=T.SPACE_MD, pady=(0, T.SPACE_MD))
        self.grid_rowconfigure(row, weight=1)

    def _build_header(self, title: str, eyebrow: str) -> ctk.CTkFrame:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid_columnconfigure(0, weight=1)

        text_col = ctk.CTkFrame(header, fg_color="transparent")
        text_col.grid(row=0, column=0, sticky="w")
        if eyebrow:
            ctk.CTkLabel(
                text_col, text=eyebrow, font=T.FONT_CODE_SMALL,
                text_color=T.TEXT_MUTED, anchor="w",
            ).pack(anchor="w")
        if title:
            ctk.CTkLabel(
                text_col, text=title.upper(),
                font=(T.FONT_FAMILY, 12, "bold"),
                text_color=T.TEXT_SECONDARY, anchor="w",
            ).pack(anchor="w")

        self._action_slot = ctk.CTkFrame(header, fg_color="transparent")
        self._action_slot.grid(row=0, column=1, sticky="e")
        return header

    @property
    def action_parent(self) -> ctk.CTkFrame | None:
        """Master to create header-action widgets under (or None if no header)."""
        return self._action_slot if self._header else None

    def add_action(self, widget: ctk.CTkBaseClass) -> None:
        """Pack a trailing widget into the header's action slot.

        The widget must have been created with :attr:`action_parent` as its
        master so Tk can pack it inside the slot.
        """
        if self._header is None:
            return
        widget.pack(side="right", padx=(T.SPACE_SM, 0))


def section_label(parent: tk.Widget, text: str) -> ctk.CTkLabel:
    """A small-caps section eyebrow used to group content inside a view."""
    return ctk.CTkLabel(
        parent, text=text.upper(),
        font=(T.FONT_FAMILY, 11, "bold"),
        text_color=T.TEXT_MUTED, anchor="w",
    )


def hairline(parent: tk.Widget, color: str = T.BORDER_SUBTLE) -> ctk.CTkFrame:
    """A 1px horizontal divider."""
    return ctk.CTkFrame(parent, height=1, fg_color=color, corner_radius=0)


class KeyValue(ctk.CTkFrame):
    """A single label→value instrument row (technical value in mono)."""

    def __init__(
        self,
        parent: tk.Widget,
        label: str,
        value: str = "—",
        value_color: str = T.TEXT_PRIMARY,
        mono: bool = True,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)  # type: ignore[arg-type]
        self.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            self, text=label.upper(), font=(T.FONT_FAMILY, 10, "bold"),
            text_color=T.TEXT_MUTED, anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(0, T.SPACE_MD))
        self._value = ctk.CTkLabel(
            self, text=value,
            font=T.FONT_CODE_SMALL if mono else T.FONT_SMALL,
            text_color=value_color, anchor="e", justify="right",
        )
        self._value.grid(row=0, column=1, sticky="e")

    def set(self, value: str, color: str | None = None) -> None:
        self._value.configure(text=value)
        if color:
            self._value.configure(text_color=color)
