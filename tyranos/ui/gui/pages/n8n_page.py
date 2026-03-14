"""
n8n Workflows page — browse, create, trigger, and monitor n8n workflows.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from .. import theme as T
from ..components.workflow_card import WorkflowCard


class N8nPage(ctk.CTkFrame):
    """
    n8n integration page: workflow grid, creation drawer, execution log.
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
        self._workflows: list[dict] = []
        self._result_queue: queue.Queue = queue.Queue()
        self._loading = False

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_topbar()
        self._build_body()
        self._check_results()
        self._load_workflows()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_topbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color=T.BG_SURFACE, corner_radius=0, height=52)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(bar, fg_color="transparent")
        left.pack(side="left", padx=T.PAD_CARD)
        ctk.CTkLabel(left, text="🔄  n8n Workflows", **T.label_heading_kwargs()).pack(side="left")

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right", padx=T.PAD_CARD)

        ctk.CTkButton(
            right,
            text="↻  Refresh",
            width=90,
            **T.btn_ghost_kwargs(),
            command=self._load_workflows,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            right,
            text="+ New Workflow",
            width=120,
            **T.btn_primary_kwargs(),
            command=self._open_create_drawer,
        ).pack(side="left")

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=T.PAD_PAGE, pady=T.PAD_CARD)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=1)

        self._build_workflow_panel(body)
        self._build_exec_log_panel(body)

    def _build_workflow_panel(self, parent: ctk.CTkFrame) -> None:
        left = ctk.CTkFrame(parent, **T.card_kwargs())
        left.grid(row=0, column=0, sticky="nsew", padx=(0, T.SPACE_SM))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        # Search bar
        search_row = ctk.CTkFrame(left, fg_color="transparent")
        search_row.grid(row=0, column=0, sticky="ew", padx=T.PAD_CARD, pady=T.PAD_CARD)
        search_row.grid_columnconfigure(0, weight=1)

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search)

        ctk.CTkEntry(
            search_row,
            textvariable=self._search_var,
            placeholder_text="🔍  Search workflows…",
            **T.input_kwargs(),
        ).grid(row=0, column=0, sticky="ew")

        self._wf_scroll = ctk.CTkScrollableFrame(
            left,
            fg_color=T.BG_DEEP,
            corner_radius=T.RADIUS_SM,
            scrollbar_button_color=T.BG_RAISED,
            scrollbar_button_hover_color=T.PURPLE,
        )
        self._wf_scroll.grid(
            row=1, column=0, sticky="nsew", padx=T.PAD_CARD, pady=(0, T.PAD_CARD)
        )
        self._wf_scroll.grid_columnconfigure(0, weight=1)

        self._status_label = ctk.CTkLabel(
            self._wf_scroll,
            text="Loading workflows…",
            **T.label_secondary_kwargs(),
        )
        self._status_label.pack(pady=T.SPACE_2XL)

    def _build_exec_log_panel(self, parent: ctk.CTkFrame) -> None:
        right = ctk.CTkFrame(parent, **T.card_kwargs())
        right.grid(row=0, column=1, sticky="nsew", padx=(T.SPACE_SM, 0))
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            right,
            text="📊  Execution Log",
            font=T.FONT_SUBHEADING,
            text_color=T.TEXT_ACCENT,
        ).grid(row=0, column=0, sticky="w", padx=T.PAD_CARD, pady=(T.PAD_CARD, T.SPACE_SM))

        self._log_frame = ctk.CTkScrollableFrame(
            right,
            fg_color=T.BG_DEEP,
            corner_radius=T.RADIUS_SM,
            scrollbar_button_color=T.BG_RAISED,
            scrollbar_button_hover_color=T.PURPLE,
        )
        self._log_frame.grid(
            row=1, column=0, sticky="nsew", padx=T.PAD_CARD, pady=(0, T.PAD_CARD)
        )
        self._log_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self._log_frame,
            text="Trigger a workflow to see execution output.",
            **T.label_secondary_kwargs(),
        ).pack(pady=T.SPACE_2XL)

    # ── Workflow loading ───────────────────────────────────────────────────────

    def _load_workflows(self) -> None:
        if self._loading:
            return
        self._loading = True
        threading.Thread(target=self._fetch_workflows, daemon=True).start()

    def _fetch_workflows(self) -> None:
        try:
            if self._engine and hasattr(self._engine, "n8n"):
                import asyncio
                loop = asyncio.new_event_loop()
                wfs = loop.run_until_complete(self._engine.n8n.list_workflows())
                loop.close()
                self._result_queue.put(("workflows", wfs))
            else:
                self._result_queue.put(("workflows", []))
        except Exception as exc:
            self._result_queue.put(("error", str(exc)))

    def _check_results(self) -> None:
        try:
            kind, content = self._result_queue.get_nowait()
            self._loading = False
            if kind == "workflows":
                self._workflows = content if isinstance(content, list) else []
                self._render_workflows(self._workflows)
            elif kind == "triggered":
                self._log_execution(content)
            else:
                self._show_load_error(str(content))
        except queue.Empty:
            pass
        self.after(200, self._check_results)

    def _render_workflows(self, workflows: list[dict]) -> None:
        for child in self._wf_scroll.winfo_children():
            child.destroy()

        if not workflows:
            ctk.CTkLabel(
                self._wf_scroll,
                text="No workflows found.\nCreate one or check your n8n connection in Settings.",
                **T.label_secondary_kwargs(),
                justify="center",
            ).pack(pady=T.SPACE_2XL)
            return

        for wf in workflows:
            WorkflowCard(
                self._wf_scroll,
                name=wf.get("name", "Unnamed"),
                active=wf.get("active", False),
                trigger=wf.get("trigger", "—"),
                exec_count=wf.get("executionCount", 0),
                on_run=lambda w=wf: self._trigger_workflow(w),
                on_toggle=lambda w=wf: self._edit_workflow(w),
            ).pack(fill="x", pady=3)

    def _show_load_error(self, msg: str) -> None:
        for child in self._wf_scroll.winfo_children():
            child.destroy()
        ctk.CTkLabel(
            self._wf_scroll,
            text=f"⚠  {msg}\n\nCheck n8n URL and API key in Settings.",
            **T.label_secondary_kwargs(),
            justify="center",
        ).pack(pady=T.SPACE_2XL)

    def _on_search(self, *_args: object) -> None:
        q = self._search_var.get().lower()
        filtered = [w for w in self._workflows if q in w.get("name", "").lower()] if q else self._workflows
        self._render_workflows(filtered)

    # ── Trigger / Edit ────────────────────────────────────────────────────────

    def _trigger_workflow(self, wf: dict) -> None:
        threading.Thread(target=self._run_trigger, args=(wf,), daemon=True).start()

    def _run_trigger(self, wf: dict) -> None:
        try:
            if self._engine and hasattr(self._engine, "n8n"):
                import asyncio
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(
                    self._engine.n8n.trigger_workflow(wf.get("id", ""))
                )
                loop.close()
                self._result_queue.put(("triggered", {"wf": wf, "result": result, "ok": True}))
            else:
                self._result_queue.put(("triggered", {"wf": wf, "result": "Engine not connected", "ok": False}))
        except Exception as exc:
            self._result_queue.put(("triggered", {"wf": wf, "result": str(exc), "ok": False}))

    def _log_execution(self, data: dict) -> None:
        for child in self._log_frame.winfo_children():
            child.destroy()

        wf = data.get("wf", {})
        ok = data.get("ok", False)
        result = data.get("result", "")

        header = ctk.CTkFrame(self._log_frame, fg_color=T.BG_RAISED, corner_radius=T.RADIUS_SM)
        header.pack(fill="x", pady=(0, T.SPACE_SM), padx=T.SPACE_XS)
        ctk.CTkLabel(
            header,
            text=f"{'✓' if ok else '✗'}  {wf.get('name', 'Workflow')}",
            font=T.FONT_BODY_BOLD,
            text_color=T.SUCCESS if ok else T.ERROR,
        ).pack(anchor="w", padx=T.SPACE_SM, pady=T.SPACE_SM)

        ctk.CTkLabel(
            self._log_frame,
            text=str(result),
            font=T.FONT_SMALL,
            text_color=T.TEXT_PRIMARY,
            wraplength=260,
            justify="left",
            anchor="w",
        ).pack(anchor="w", padx=T.SPACE_SM)

    def _edit_workflow(self, wf: dict) -> None:
        pass  # open external browser to n8n editor

    # ── Create drawer ─────────────────────────────────────────────────────────

    def _open_create_drawer(self) -> None:
        _CreateDrawer(self, on_create=self._do_create_workflow)

    def _do_create_workflow(self, name: str, description: str) -> None:
        def _run() -> None:
            try:
                if self._engine and hasattr(self._engine, "n8n"):
                    import asyncio
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(
                        self._engine.n8n.create_workflow(name=name, description=description)
                    )
                    loop.close()
                self._result_queue.put(("workflows_reload", None))
            except Exception as exc:
                self._result_queue.put(("error", str(exc)))

        threading.Thread(target=_run, daemon=True).start()


class _CreateDrawer(ctk.CTkToplevel):
    """Modal dialog for creating a new n8n workflow."""

    def __init__(
        self,
        parent: tk.Widget,
        on_create: Callable[[str, str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_create = on_create
        self.title("New Workflow")
        self.geometry("440x300")
        self.resizable(False, False)
        self.configure(fg_color=T.BG_SURFACE)
        self.grab_set()

        ctk.CTkLabel(self, text="Create n8n Workflow", **T.label_heading_kwargs()).pack(
            anchor="w", padx=T.PAD_CARD, pady=(T.PAD_CARD, T.SPACE_SM)
        )

        ctk.CTkLabel(self, text="Workflow name", **T.label_secondary_kwargs()).pack(
            anchor="w", padx=T.PAD_CARD
        )
        self._name = ctk.CTkEntry(self, placeholder_text="My Workflow", **T.input_kwargs())
        self._name.pack(fill="x", padx=T.PAD_CARD, pady=(T.SPACE_XS, T.SPACE_MD))

        ctk.CTkLabel(self, text="Description (optional)", **T.label_secondary_kwargs()).pack(
            anchor="w", padx=T.PAD_CARD
        )
        self._desc = ctk.CTkTextbox(
            self,
            height=68,
            fg_color=T.BG_RAISED,
            border_color=T.BORDER_SUBTLE,
            text_color=T.TEXT_PRIMARY,
            font=T.FONT_BODY,
            corner_radius=T.RADIUS_INPUT,
        )
        self._desc.pack(fill="x", padx=T.PAD_CARD, pady=(T.SPACE_XS, T.SPACE_MD))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=T.PAD_CARD, pady=(0, T.PAD_CARD))
        ctk.CTkButton(btn_row, text="Cancel", **T.btn_ghost_kwargs(), command=self.destroy).pack(
            side="left"
        )
        ctk.CTkButton(
            btn_row, text="Create", **T.btn_primary_kwargs(), command=self._submit
        ).pack(side="right")

    def _submit(self) -> None:
        name = self._name.get().strip()
        if not name:
            return
        desc = self._desc.get("1.0", "end").strip()
        if self._on_create:
            self._on_create(name, desc)
        self.destroy()
