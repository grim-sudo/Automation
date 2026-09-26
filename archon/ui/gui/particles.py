"""
Ambient particle field and the Archon sigil for the GUI.

A quiet holographic backdrop: drifting glowing nodes linked by faint proximity
lines, plus the Archon "sigil" — a three-blade trident emblem wrapped in a HUD
reticle, used for the splash and logo. Everything runs on tkinter's ``after()``
loop — no external deps.
"""

from __future__ import annotations

import math
import random
import tkinter as tk

from . import theme as T
from .animations import hex_to_rgb, rgb_to_hex

# Precomputed link-fade ramp: line color at N steps between BG and accent.
# Tk has no per-item alpha, so proximity lines are drawn as pre-blended hexes.
_LINK_STEPS = 6

# Hard cap on the node pool — keeps the O(n²) link pass affordable in pure
# Python; the field looks full well before this on any real window.
_MAX_NODES = 70


def _blend(fg: str, bg: str, t: float) -> str:
    """Blend fg over bg by factor t (0..1) and return a hex string."""
    fr, fg_, fb = hex_to_rgb(fg)
    br, bg_, bb = hex_to_rgb(bg)
    return rgb_to_hex(
        round(fr * t + br * (1 - t)),
        round(fg_ * t + bg_ * (1 - t)),
        round(fb * t + bb * (1 - t)),
    )


class _Node:
    __slots__ = ("x", "y", "vx", "vy", "r", "color")

    def __init__(self, w: int, h: int) -> None:
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        speed = random.uniform(6.0, 22.0)  # px/sec
        ang = random.uniform(0, math.tau)
        self.vx = math.cos(ang) * speed
        self.vy = math.sin(ang) * speed
        self.r = random.uniform(1.0, 2.6)
        # Most nodes are steel; a few gold for warmth against the obsidian field.
        self.color = T.CYAN if random.random() < 0.62 else T.PURPLE_LIGHT


class ParticleField(tk.Canvas):
    """
    A drifting constellation of glowing nodes linked by proximity lines.

    Reusable as a full-bleed background. Call :meth:`start` to animate and
    :meth:`stop` to halt (also happens automatically when the widget is
    destroyed). ``density`` is nodes per 100k px²; ``link_dist`` is the max
    pixel distance for a connecting line.
    """

    def __init__(
        self,
        parent: tk.Widget,
        bg: str = T.BG_DEEP,
        density: float = 0.9,
        link_dist: float = 130.0,
        fps: int = 30,
        **kwargs: object,
    ) -> None:
        super().__init__(
            parent,
            bg=bg,
            highlightthickness=0,
            bd=0,
            **kwargs,  # type: ignore[arg-type]
        )
        self._bg = bg
        self._density = density
        self._link_dist = link_dist
        self._interval = max(16, int(1000 / fps))
        self._dt = self._interval / 1000.0
        self._nodes: list[_Node] = []
        self._running = False
        self._cw = 0
        self._ch = 0
        # Pre-blend the link color ramp against the background once — a warm,
        # dim gold rule so proximity lines recede into the obsidian field.
        self._link_ramp = [
            _blend(T.PURPLE_DARK, bg, (i + 1) / _LINK_STEPS) for i in range(_LINK_STEPS)
        ]
        self.bind("<Configure>", self._on_resize)

    # ── Lifecycle ───────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._tick()

    def stop(self) -> None:
        self._running = False

    def destroy(self) -> None:  # noqa: D102 - tk override
        self._running = False
        super().destroy()

    # ── Sizing ──────────────────────────────────────────────────────────────

    def _on_resize(self, event: tk.Event) -> None:
        self._cw, self._ch = event.width, event.height
        # ponytail: O(n²) proximity check each frame — cap the pool so the
        # pure-Python Tk render loop stays smooth. Upgrade path: spatial grid.
        target = int(self._cw * self._ch / 100_000 * self._density * 100)
        target = max(8, min(target, _MAX_NODES))
        # Grow or shrink the node pool to match the new area.
        while len(self._nodes) < target:
            self._nodes.append(_Node(self._cw, self._ch))
        if len(self._nodes) > target:
            self._nodes = self._nodes[:target]

    # ── Animation ─────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        if not self._running or not self.winfo_exists():
            return
        if self._cw <= 1 or self._ch <= 1:
            self.after(self._interval, self._tick)
            return

        self._advance()
        self._render()
        self.after(self._interval, self._tick)

    def _advance(self) -> None:
        w, h = self._cw, self._ch
        for n in self._nodes:
            n.x += n.vx * self._dt
            n.y += n.vy * self._dt
            # Wrap around the edges for a seamless field.
            if n.x < -5:
                n.x = w + 5
            elif n.x > w + 5:
                n.x = -5
            if n.y < -5:
                n.y = h + 5
            elif n.y > h + 5:
                n.y = -5

    def _render(self) -> None:
        self.delete("all")
        nodes = self._nodes
        max_d = self._link_dist
        max_d2 = max_d * max_d
        ramp = self._link_ramp
        last = _LINK_STEPS - 1

        # Proximity links — nearer pairs get a brighter pre-blended color.
        for i, a in enumerate(nodes):
            for b in nodes[i + 1 :]:
                dx = a.x - b.x
                dy = a.y - b.y
                d2 = dx * dx + dy * dy
                if d2 >= max_d2:
                    continue
                closeness = 1 - math.sqrt(d2) / max_d
                self.create_line(
                    a.x, a.y, b.x, b.y,
                    fill=ramp[min(last, int(closeness * _LINK_STEPS))],
                    width=1,
                )

        # Glowing nodes: a soft halo under a bright core.
        for n in nodes:
            self.create_oval(
                n.x - n.r * 2.4, n.y - n.r * 2.4,
                n.x + n.r * 2.4, n.y + n.r * 2.4,
                fill=_blend(n.color, self._bg, 0.28), outline="",
            )
            self.create_oval(
                n.x - n.r, n.y - n.r, n.x + n.r, n.y + n.r,
                fill=n.color, outline="",
            )


def _rot(cx: float, cy: float, along: float, perp: float, a: float) -> tuple[float, float]:
    """Point at (along, perp) in a frame whose forward axis is angle ``a``."""
    dx, dy = math.cos(a), math.sin(a)
    return (cx + along * dx - perp * math.sin(a), cy + along * dy + perp * math.cos(a))


def _blade(
    canvas: tk.Canvas,
    c: float,
    s: float,
    a: float,
    dark: str,
    lit: str,
    edge: str,
    ridge: str,
) -> None:
    """Draw one beveled blade of the tri-sigil, forward axis at angle ``a``."""
    tip = _rot(c, c, 0.42 * s, 0, a)
    inner = _rot(c, c, 0.03 * s, 0, a)
    eo_r = _rot(c, c, 0.27 * s, 0.052 * s, a)
    el_r = _rot(c, c, 0.15 * s, 0.026 * s, a)
    eo_l = _rot(c, c, 0.27 * s, -0.052 * s, a)
    el_l = _rot(c, c, 0.15 * s, -0.026 * s, a)
    # Shadowed (left) face, then gold-lit (right) face.
    canvas.create_polygon(*tip, *eo_l, *el_l, *inner, fill=dark, outline="")
    canvas.create_polygon(*tip, *eo_r, *el_r, *inner, fill=lit, outline="")
    # Outer edge highlight and central ridge.
    canvas.create_line(
        *tip, *eo_r, *el_r, fill=edge,
        width=max(1, int(s * 0.012)), capstyle="round", joinstyle="round",
    )
    canvas.create_line(*tip, *inner, fill=ridge, width=max(1, int(s * 0.006)))


def draw_archon_sigil(
    canvas: tk.Canvas,
    size: int,
    phase: float = 0.0,
    glyph: bool = True,
) -> None:
    """
    Draw the Archon emblem into ``canvas`` (cleared first).

    The command sigil: a three-blade trident (one apex up, two swept down) with
    beveled gold-lit faces, wrapped in a HUD reticle — concentric gold rings, a
    crosshair with cardinal beads, and a pulsing reactor core. ``phase`` (radians,
    ever-increasing) drives a spark traveling the outer ring and the core pulse;
    pass a constant for a static mark. Scales to ``size`` px in gold-on-obsidian.
    """
    canvas.delete("all")
    c = size / 2
    bg = T.BG_DEEP

    ring = _blend(T.PURPLE, bg, 0.5)
    ring_mid = _blend(T.PURPLE, bg, 0.85)
    ring_in = _blend(T.PURPLE, bg, 0.32)
    cross = _blend(T.PURPLE, bg, 0.28)

    # Reactor glow — warm center wash (pre-blended, no alpha in Tk).
    for frac, t in ((0.30, 0.10), (0.20, 0.16), (0.12, 0.26)):
        gr = size * frac
        canvas.create_oval(
            c - gr, c - gr, c + gr, c + gr, fill=_blend(T.GOLD, bg, t), outline=""
        )

    # HUD reticle rings.
    r_out = size * 0.46
    canvas.create_oval(c - r_out, c - r_out, c + r_out, c + r_out, outline=ring, width=1)
    r_mid = size * 0.42
    canvas.create_oval(
        c - r_mid, c - r_mid, c + r_mid, c + r_mid,
        outline=ring_mid, width=max(1, int(size * 0.012)), dash=(2, 6),
    )
    r_inr = size * 0.32
    canvas.create_oval(c - r_inr, c - r_inr, c + r_inr, c + r_inr, outline=ring_in, width=1)

    # Crosshair.
    m = size * 0.03
    canvas.create_line(m, c, size - m, c, fill=cross, width=1)
    canvas.create_line(c, m, c, size - m, fill=cross, width=1)

    # Cardinal beads.
    br = max(1.5, size * 0.018)
    for bx, by in ((c, m + br), (c, size - m - br), (m + br, c), (size - m - br, c)):
        canvas.create_oval(bx - br, by - br, bx + br, by + br, fill=T.PURPLE_LIGHT, outline="")

    # Tri-blade sigil — apex up (-90°), swept down at ±120°.
    dark, lit, edge, ridge = T.BG_RAISED, T.PURPLE_DARK, T.PURPLE_LIGHT, T.GOLD
    for k in range(3):
        _blade(canvas, c, size, -math.pi / 2 + k * (math.tau / 3), dark, lit, edge, ridge)

    # Traveling spark on the outer ring.
    sx = c + r_out * math.cos(phase)
    sy = c + r_out * math.sin(phase)
    sr = max(1.5, size * 0.025)
    canvas.create_oval(
        sx - sr * 2, sy - sr * 2, sx + sr * 2, sy + sr * 2,
        fill=_blend(T.GOLD, bg, 0.35), outline="",
    )
    canvas.create_oval(sx - sr, sy - sr, sx + sr, sy + sr, fill=T.PURPLE_LIGHT, outline="")

    # Reactor core — crescent, spark line, pulsing center.
    if glyph:
        aw = size * 0.05
        canvas.create_arc(
            c - aw, c - aw * 0.6, c + aw, c + aw * 1.2,
            start=200, extent=140, style="arc", outline=T.PURPLE, width=max(1, int(size * 0.01)),
        )
        canvas.create_line(c, c - size * 0.07, c, c + size * 0.07, fill=T.PURPLE_LIGHT, width=1)
        pulse = (math.sin(phase * 2) + 1) / 2  # 0..1
        kr = max(1.5, size * 0.03)
        canvas.create_oval(
            c - kr, c - kr, c + kr, c + kr,
            fill=_blend(T.GOLD, bg, 0.45 + 0.55 * pulse), outline="",
        )
