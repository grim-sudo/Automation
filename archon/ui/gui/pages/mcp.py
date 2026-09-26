"""
MCP / Capabilities view — how Archon gains and exercises external reach.

Spec §17: a capability network around the Archon core, plus an inspector that
lists a capability's actions and permissions. Backed by
``engine.describe_capabilities()`` (the CapabilityRegistry). When no external MCP
servers are connected, the local capability registry still populates the graph;
a designed note explains how to extend Archon's reach.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from .. import theme as T
from ..components.capability_graph import CapabilityGraph
from ..components.empty_state import EmptyState
from ..components.panel import KeyValue, Panel, hairline, section_label

# risk value → display color
_RISK_COLOR = {
    "low": T.SUCCESS,
    "medium": T.WARNING,
    "high": T.ERROR,
    "critical": T.ERROR,
}


class McpView(ctk.CTkFrame):
    """Capability network + action inspector."""

    def __init__(
        self,
        parent: tk.Widget,
        engine: object = None,
        on_navigate: Callable[[str], None] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, fg_color=T.BG_DEEP, **kwargs)  # type: ignore[arg-type]
        self._engine = engine
        self._caps = self._load_caps()
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=3, uniform="mc")
        self.grid_columnconfigure(1, weight=2, uniform="mc")
        self._build()

    def _load_caps(self) -> dict:
        try:
            if self._engine and hasattr(self._engine, "describe_capabilities"):
                return self._engine.describe_capabilities() or {}
        except Exception:
            pass
        return {}

    def _build(self) -> None:
        if not self._caps:
            EmptyState(
                self,
                title="No Capabilities Connected",
                message="Connect an MCP server to extend Archon's reach.",
                note="engine.describe_capabilities() returned nothing",
            ).grid(row=0, column=0, columnspan=2, sticky="nsew")
            return

        left = Panel(self, title="Capability Network")
        left.grid(row=0, column=0, sticky="nsew", padx=(T.PAD_PAGE, T.SPACE_MD),
                  pady=T.PAD_PAGE)
        self._graph = CapabilityGraph(
            left.body, bg=T.BG_SURFACE, on_select=self._select,
        )
        self._graph.pack(fill="both", expand=True)
        self._graph.set_capabilities([
            {"name": name, "status": "connected"} for name in self._caps
        ])

        self._insp = Panel(self, title="Inspector")
        self._insp.grid(row=0, column=1, sticky="nsew",
                        padx=(T.SPACE_MD, T.PAD_PAGE), pady=T.PAD_PAGE)
        self._insp.body.grid_rowconfigure(0, weight=1)
        self._insp.body.grid_columnconfigure(0, weight=1)
        self._insp_host = ctk.CTkScrollableFrame(
            self._insp.body, fg_color="transparent",
            scrollbar_button_color=T.BG_RAISED,
            scrollbar_button_hover_color=T.PURPLE,
        )
        self._insp_host.grid(row=0, column=0, sticky="nsew")
        self._insp_host.grid_columnconfigure(0, weight=1)
        # Open the first capability by default.
        self._select(next(iter(self._caps)))

    def _select(self, name: str) -> None:
        meta = self._caps.get(name)
        if meta is None:
            return
        for child in self._insp_host.winfo_children():
            child.destroy()

        ctk.CTkLabel(self._insp_host, text=name.replace("_", " ").upper(),
                     font=T.FONT_HEADING, text_color=T.TEXT_PRIMARY,
                     anchor="w").pack(fill="x")
        ctk.CTkLabel(self._insp_host, text="● Connected", font=T.FONT_SMALL,
                     text_color=T.SUCCESS, anchor="w").pack(fill="x", pady=(0, T.SPACE_SM))
        desc = meta.get("description") or ""
        if desc:
            ctk.CTkLabel(self._insp_host, text=desc, font=T.FONT_SMALL,
                         text_color=T.TEXT_SECONDARY, anchor="w",
                         wraplength=240, justify="left").pack(fill="x")

        risk = (meta.get("risk") or "low").lower()
        KeyValue(self._insp_host, "Risk", risk.upper(),
                 value_color=_RISK_COLOR.get(risk, T.TEXT_SECONDARY)).pack(
            fill="x", pady=(T.SPACE_SM, 0))

        actions = meta.get("actions") or []
        hairline(self._insp_host).pack(fill="x", pady=T.SPACE_MD)
        section_label(self._insp_host, f"Actions · {len(actions)}").pack(
            fill="x", pady=(0, T.SPACE_SM))
        if not actions:
            ctk.CTkLabel(self._insp_host, text="No actions advertised.",
                         font=T.FONT_SMALL, text_color=T.TEXT_MUTED).pack(anchor="w")
        for act in actions:
            self._action_row(act)

    def _action_row(self, act: dict) -> None:
        row = ctk.CTkFrame(self._insp_host, fg_color="transparent")
        row.pack(fill="x", pady=1)
        arisk = (act.get("risk") or "low").lower()
        ctk.CTkLabel(row, text="●", font=(T.FONT_FAMILY, 9),
                     text_color=_RISK_COLOR.get(arisk, T.TEXT_DIM)).pack(
            side="left", padx=(0, T.SPACE_SM))
        ctk.CTkLabel(row, text=act.get("name", ""), font=T.FONT_CODE_SMALL,
                     text_color=T.TEXT_CYAN, anchor="w").pack(
            side="left", fill="x", expand=True)
