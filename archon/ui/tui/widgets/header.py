"""Application header: identity on the left, model/backend state on the right.

A single reactive :class:`Static` that renders both halves as a two-column
grid, so it never needs child widgets. Setting any reactive re-renders it, so
the header always reflects the live backend state.
"""

from __future__ import annotations

from rich.table import Table
from rich.text import Text
from textual.reactive import reactive
from textual.widgets import Static

from .glyphs import GLYPHS


class ArchonHeader(Static):
    """A one-line identity + connection banner."""

    model: reactive[str] = reactive("—")
    backend: reactive[str] = reactive("—")
    accelerator: reactive[str] = reactive("—")
    online: reactive[bool] = reactive(False)

    def render(self) -> Table:
        g = GLYPHS
        brand = Text()
        brand.append(f"{g.brand} ", style="#d9a441 bold")
        brand.append("ARCHON", style="#d9a441 bold")
        brand.append("    ")
        brand.append("ONE TO RULE THEM ALL", style="#8a6d3b")

        state = Text(justify="right")
        chips = [c for c in (self.model, self.backend, self.accelerator) if c and c != "—"]
        if chips:
            state.append("  •  ".join(chips), style="#8a8f98")
            state.append("    ")
        if self.online:
            state.append(f"{g.online} ONLINE", style="#5fae7f bold")
        else:
            state.append(f"{g.online} OFFLINE", style="#d9a441 bold")

        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="right", ratio=1)
        grid.add_row(brand, state)
        return grid
