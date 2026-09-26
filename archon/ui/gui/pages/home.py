"""
Home page — dashboard overview with stats, quick actions, and activity feed.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from datetime import datetime

import customtkinter as ctk

from .. import theme as T
from ..components.sparkline import Sparkline
from ..components.status_badge import StatusBadge


class HomePage(ctk.CTkScrollableFrame):
    """Dashboard home page."""

    def __init__(
        self,
        parent: tk.Widget,
        on_navigate: Callable[[str], None] | None = None,
        engine: object = None,
        **kwargs: object,
    ) -> None:
        super().__init__(
            parent,
            fg_color=T.BG_DEEP,
            scrollbar_button_color=T.BG_RAISED,
            scrollbar_button_hover_color=T.PURPLE,
            **kwargs,  # type: ignore[arg-type]
        )
        self._on_navigate = on_navigate
        self._engine = engine
        self._activity: list[dict] = []
        self._sparkline: Sparkline | None = None
        self._build()
        self._start_system_updates()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self._build_hero()
        self._build_stats_row()
        self._build_activity_feed()

    def _build_hero(self) -> None:
        hero = ctk.CTkFrame(
            self,
            fg_color=T.BG_SURFACE,
            corner_radius=T.RADIUS_CARD,
            border_color=T.BORDER_ACCENT,
            border_width=1,
        )
        hero.pack(fill="x", padx=T.PAD_PAGE, pady=(T.PAD_PAGE, T.GAP_SECTION))
        hero.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(hero, fg_color="transparent")
        inner.pack(fill="x", padx=T.PAD_CARD, pady=T.PAD_CARD)
        inner.grid_columnconfigure(0, weight=1)

        # Left: greeting + date
        left = ctk.CTkFrame(inner, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        hour = datetime.now().hour
        greeting = (
            "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
        )
        ctk.CTkLabel(
            left,
            text=f"{greeting}, Commander",
            font=T.FONT_DISPLAY,
            text_color=T.TEXT_ACCENT,
        ).pack(anchor="w")

        self._date_label = ctk.CTkLabel(
            left,
            text=datetime.now().strftime("%A, %B %d, %Y  %H:%M"),
            **T.label_secondary_kwargs(),
        )
        self._date_label.pack(anchor="w", pady=(4, 0))

        ctk.CTkLabel(
            left,
            text="AI connected · Ready to automate",
            text_color=T.SUCCESS,
            font=T.FONT_SMALL,
        ).pack(anchor="w", pady=(4, 0))

        # Right: quick action 2×2 grid
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right", padx=(T.SPACE_LG, 0))

        actions = [
            ("New Chat", "chat"),
            ("Run Command", "automate"),
            ("Build OS", "distro"),
            ("New Workflow", "n8n"),
        ]
        for idx, (label, page) in enumerate(actions):
            row, col = divmod(idx, 2)
            btn = ctk.CTkButton(
                right,
                text=label,
                width=130,
                height=36,
                **T.btn_primary_kwargs() if idx == 0 else T.btn_outline_kwargs(),
                command=lambda p=page: self._navigate(p),
            )
            btn.grid(row=row, column=col, padx=4, pady=4)

        self._update_clock()

    def _build_stats_row(self) -> None:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=T.PAD_PAGE)
        row.grid_columnconfigure((0, 1, 2), weight=1)

        # Card 1 — AI Status
        ai_card = _StatCard(row, title="AI Status")
        ai_card.grid(row=0, column=0, padx=(0, T.GAP_ELEMENT), sticky="nsew")

        StatusBadge(ai_card.body, "● Connected", "active", pulse=True).pack(anchor="w")
        ctk.CTkLabel(
            ai_card.body,
            text="Free tier · unlimited",
            **T.label_secondary_kwargs(),
        ).pack(anchor="w", pady=(4, 0))

        try:
            self._model_label = ctk.CTkLabel(
                ai_card.body, text="Checking models…", **T.label_secondary_kwargs()
            )
        except Exception:
            self._model_label = ctk.CTkLabel(
                ai_card.body, text="AI layer ready", **T.label_secondary_kwargs()
            )
        self._model_label.pack(anchor="w", pady=(2, 0))

        # Card 2 — System Resources
        sys_card = _StatCard(row, title="System Resources")
        sys_card.grid(row=0, column=1, padx=T.GAP_ELEMENT // 2, sticky="nsew")

        try:
            import psutil

            self._cpu_label = ctk.CTkLabel(
                sys_card.body, text=f"CPU: {psutil.cpu_percent():.0f}%", **T.label_body_kwargs()
            )
            self._cpu_label.pack(anchor="w")
            self._sparkline = Sparkline(sys_card.body, width=160, height=32)
            self._sparkline.pack(anchor="w", pady=4)
            ram = psutil.virtual_memory()
            ctk.CTkLabel(
                sys_card.body,
                text=f"RAM: {ram.percent:.0f}%  ({ram.used // 1024 // 1024:.0f} MB / "
                f"{ram.total // 1024 // 1024:.0f} MB)",
                **T.label_secondary_kwargs(),
            ).pack(anchor="w")
        except Exception:
            ctk.CTkLabel(
                sys_card.body, text="psutil not available", **T.label_secondary_kwargs()
            ).pack(anchor="w")

        # Card 3 — n8n
        n8n_card = _StatCard(row, title="n8n Workflows")
        n8n_card.grid(row=0, column=2, padx=(T.GAP_ELEMENT, 0), sticky="nsew")

        ctk.CTkLabel(
            n8n_card.body, text="0 active", font=T.FONT_HEADING, text_color=T.TEXT_ACCENT
        ).pack(anchor="w")
        ctk.CTkLabel(
            n8n_card.body,
            text="Not connected to n8n",
            **T.label_secondary_kwargs(),
        ).pack(anchor="w", pady=(2, 4))
        ctk.CTkButton(
            n8n_card.body,
            text="Open Workflows →",
            **T.btn_outline_kwargs(),
            command=lambda: self._navigate("n8n"),
        ).pack(anchor="w")

    def _build_activity_feed(self) -> None:
        section = ctk.CTkFrame(self, fg_color="transparent")
        section.pack(fill="x", padx=T.PAD_PAGE, pady=T.GAP_SECTION)

        hdr = ctk.CTkFrame(section, fg_color="transparent")
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text="Recent Activity", **T.label_heading_kwargs()).pack(side="left")

        self._feed_frame = ctk.CTkFrame(
            section,
            fg_color=T.BG_SURFACE,
            corner_radius=T.RADIUS_CARD,
        )
        self._feed_frame.pack(fill="x", pady=(T.GAP_ELEMENT, 0))
        self._render_activity()

    def _render_activity(self) -> None:
        for child in self._feed_frame.winfo_children():
            child.destroy()

        if not self._activity:
            _empty_state(
                self._feed_frame,
                icon="▤",
                title="No activity yet",
                subtitle="Start by chatting with Archon",
                action_text="Open Chat",
                action_cmd=lambda: self._navigate("chat"),
            )
            return

        for item in self._activity[-10:]:
            _ActivityRow(self._feed_frame, **item).pack(fill="x", padx=T.SPACE_SM, pady=2)

    def add_activity(self, item: dict) -> None:
        """Add a new activity item and refresh the feed."""
        self._activity.append(item)
        self._render_activity()

    # ── Live updates ───────────────────────────────────────────────────────────

    def _update_clock(self) -> None:
        try:
            self._date_label.configure(text=datetime.now().strftime("%A, %B %d, %Y  %H:%M:%S"))
            self.after(1000, self._update_clock)
        except Exception:
            pass

    def _start_system_updates(self) -> None:
        def _update() -> None:
            try:
                import psutil

                cpu = psutil.cpu_percent(interval=None)
                if self._sparkline:
                    self._sparkline.push(cpu)
                if hasattr(self, "_cpu_label"):
                    self._cpu_label.configure(text=f"CPU: {cpu:.0f}%")
                self.after(2000, _update)
            except Exception:
                pass

        self.after(500, _update)


# ── Helper widgets ─────────────────────────────────────────────────────────────


class _StatCard(ctk.CTkFrame):
    def __init__(self, parent: tk.Widget, title: str, **kwargs: object) -> None:
        super().__init__(
            parent,
            fg_color=T.BG_SURFACE,
            corner_radius=T.RADIUS_CARD,
            **kwargs,  # type: ignore[arg-type]
        )
        ctk.CTkLabel(self, text=title, **T.label_heading_kwargs()).pack(
            anchor="w", padx=T.PAD_CARD, pady=(T.PAD_CARD, T.SPACE_SM)
        )
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="x", padx=T.PAD_CARD, pady=(0, T.PAD_CARD))


class _ActivityRow(ctk.CTkFrame):
    _TYPE_COLORS = {
        "chat": T.PURPLE,
        "automate": T.CYAN,
        "n8n": T.SUCCESS,
        "distro": T.WARNING,
    }

    def __init__(
        self,
        parent: tk.Widget,
        activity_type: str = "chat",
        description: str = "",
        timestamp: str = "",
        status: str = "success",
        **kwargs: object,
    ) -> None:
        super().__init__(
            parent,
            fg_color="transparent",
            corner_radius=T.RADIUS_SM,
            **kwargs,  # type: ignore[arg-type]
        )
        color = self._TYPE_COLORS.get(activity_type, T.TEXT_SECONDARY)

        icon_bg = ctk.CTkFrame(
            self, fg_color=color[:7] + "30", corner_radius=6, width=32, height=32
        )
        icon_bg.pack(side="left", padx=(4, 8), pady=4)
        icon_bg.pack_propagate(False)

        icons = {"chat": "❯", "automate": "▸", "n8n": "◈", "distro": "⬡"}
        ctk.CTkLabel(icon_bg, text=icons.get(activity_type, "•"), font=T.FONT_SMALL).place(
            relx=0.5, rely=0.5, anchor="center"
        )

        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.pack(side="left", fill="x", expand=True, pady=4)
        ctk.CTkLabel(mid, text=description[:80], **T.label_body_kwargs(), anchor="w").pack(
            anchor="w"
        )
        ctk.CTkLabel(mid, text=timestamp, **T.label_secondary_kwargs(), anchor="w").pack(anchor="w")

        badge_status = "active" if status == "success" else "error"
        StatusBadge(self, text=status.capitalize(), status=badge_status).pack(side="right", padx=8)


def _empty_state(
    parent: tk.Widget,
    icon: str,
    title: str,
    subtitle: str,
    action_text: str = "",
    action_cmd: Callable | None = None,
) -> None:
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True, pady=T.SPACE_2XL)
    ctk.CTkLabel(frame, text=icon, font=(T.FONT_FAMILY, 36)).pack()
    ctk.CTkLabel(frame, text=title, **T.label_heading_kwargs()).pack(pady=(T.SPACE_SM, 0))
    ctk.CTkLabel(frame, text=subtitle, **T.label_secondary_kwargs()).pack(pady=(4, T.SPACE_MD))
    if action_text and action_cmd:
        ctk.CTkButton(frame, text=action_text, **T.btn_outline_kwargs(), command=action_cmd).pack()
