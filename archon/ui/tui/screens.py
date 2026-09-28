"""Modal/overlay screens: a brief startup splash and a risk confirmation modal.

Both are pure presentation. The confirmation modal returns a boolean via
``push_screen_wait`` so a worker thread driving the agent can block on a real
human decision for HIGH/DESTRUCTIVE actions.
"""

from __future__ import annotations

from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Center, Middle, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from .widgets.glyphs import GLYPHS


class StartupScreen(ModalScreen[None]):
    """A short identity splash shown before the main UI takes over."""

    def __init__(self, facts: dict[str, Any]) -> None:
        super().__init__()
        self._facts = facts

    def compose(self) -> ComposeResult:
        g = GLYPHS
        body = Text(justify="center")
        body.append(f"\n{g.brand}\n\n", style="#d9a441 bold")
        body.append("ARCHON\n", style="#d9a441 bold")
        body.append("ONE TO RULE THEM ALL\n\n", style="#8a6d3b")
        body.append("LOCAL COMPUTING INTELLIGENCE\n\n", style="#8a8f98")

        def row(label: str, value: Any) -> None:
            body.append(f"{label:<10}", style="#8a8f98")
            body.append(f"{'—' if value is None else value}\n", style="#d7dae0")

        row("SYSTEM", self._facts.get("system"))
        row("MODEL", self._facts.get("model"))
        row("BACKEND", self._facts.get("backend"))
        row("PLUGINS", self._facts.get("plugins"))
        body.append("\n")
        online = self._facts.get("online")
        body.append(
            f"{g.online} {'ONLINE' if online else 'OFFLINE'}\n",
            style="#5fae7f bold" if online else "#d9a441 bold",
        )
        yield Center(Middle(Static(body, classes="startup-body")))


class ConfirmScreen(ModalScreen[bool]):
    """Yes/No modal for a risky action; returns the decision."""

    BINDINGS = [
        ("y", "confirm", "Yes"),
        ("n", "deny", "No"),
        ("escape", "deny", "No"),
    ]

    def __init__(self, prompt: str, detail: str = "") -> None:
        super().__init__()
        self._prompt = prompt
        self._detail = detail

    def compose(self) -> ComposeResult:
        text = Text()
        text.append(f"{GLYPHS.err} CONFIRM\n\n", style="#d9a441 bold")
        text.append(self._prompt, style="#d7dae0")
        if self._detail:
            text.append(f"\n\n{self._detail}", style="#8a8f98")
        with Center(Middle(Vertical(classes="confirm-box"))):
            yield Static(text, classes="confirm-text")
            with Center():
                yield Button("Approve", id="confirm-yes", variant="warning")
                yield Button("Deny", id="confirm-no", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-yes")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_deny(self) -> None:
        self.dismiss(False)


class PhraseConfirmScreen(ModalScreen[bool]):
    """Typed-confirmation modal for risky actions.

    Unlike a one-keystroke y/n, the user must type an exact phrase (default
    ``yes``) to proceed. Archon does the phrase match; anything else — including
    an empty submission or Escape — cancels. Used for HIGH/DESTRUCTIVE actions
    such as deletion, where a deliberate keystroke sequence is the safeguard.
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, prompt: str, detail: str = "", phrase: str = "yes") -> None:
        super().__init__()
        self._prompt = prompt
        self._detail = detail
        self._phrase = phrase

    def compose(self) -> ComposeResult:
        text = Text()
        text.append(f"{GLYPHS.err} CONFIRM\n\n", style="#d9a441 bold")
        text.append(self._prompt, style="#d7dae0")
        if self._detail:
            text.append(f"\n\n{self._detail}", style="#8a8f98")
        text.append(
            f"\n\nType '{self._phrase}' to proceed, anything else cancels.",
            style="#cc6666",
        )
        with Center(Middle(Vertical(classes="confirm-box"))):
            yield Static(text, classes="confirm-text")
            yield Input(placeholder=f"type '{self._phrase}'", id="phrase-input")

    def on_mount(self) -> None:
        self.query_one("#phrase-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip().lower() == self._phrase.lower())

    def action_cancel(self) -> None:
        self.dismiss(False)


class SudoPromptScreen(ModalScreen[str | None]):
    """Masked password prompt for privilege escalation.

    Returns the entered password, or ``None`` if the user cancels (Escape or an
    empty submission). The password is handed straight to the escalator and
    never stored by the UI.
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, reason: str) -> None:
        super().__init__()
        self._reason = reason

    def compose(self) -> ComposeResult:
        text = Text()
        text.append(f"{GLYPHS.err} SUDO REQUIRED\n\n", style="#d9a441 bold")
        text.append(f"{self._reason} needs root privileges.\n", style="#d7dae0")
        text.append("Enter your sudo password to continue.", style="#8a8f98")
        with Center(Middle(Vertical(classes="confirm-box"))):
            yield Static(text, classes="confirm-text")
            yield Input(password=True, placeholder="sudo password", id="sudo-input")

    def on_mount(self) -> None:
        self.query_one("#sudo-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value or None)

    def action_cancel(self) -> None:
        self.dismiss(None)
