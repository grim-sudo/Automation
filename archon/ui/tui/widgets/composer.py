"""Persistent command input.

A bottom-docked multiline input built on Textual's :class:`TextArea`. Enter
submits the current buffer (posting a :class:`CommandInput.Submitted` message);
Shift+Enter inserts a newline for multiline composition. Command history is
recalled with Up/Down when the caret is on the first/last line, so ordinary
text editing still works.

Presentation/input only: it emits the typed string and lets the app decide
what to do with it.
"""

from __future__ import annotations

from pathlib import Path

from textual import events
from textual.message import Message
from textual.widgets import TextArea

_HISTORY_PATH = Path.home() / ".archon" / "chatbot_history"
_HISTORY_MAX = 500


class CommandInput(TextArea):
    """Multiline prompt with history recall and Enter-to-submit."""

    class Submitted(Message):
        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    def __init__(self) -> None:
        super().__init__(
            id="command-input",
            classes="command-input",
            soft_wrap=True,
            show_line_numbers=False,
            tab_behavior="focus",
        )
        self._history: list[str] = _load_history()
        self._hist_index: int | None = None
        self._draft = ""

    def on_mount(self) -> None:
        self.border_title = "COMMAND"

    def _submit(self) -> None:
        value = self.text.strip()
        if not value:
            return
        self._remember(value)
        self.post_message(self.Submitted(value))
        self.clear()
        self._hist_index = None
        self._draft = ""

    def _remember(self, value: str) -> None:
        if self._history and self._history[-1] == value:
            pass
        else:
            self._history.append(value)
        _append_history(value)

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            self._submit()
            return
        if event.key in ("up", "down") and self._history:
            # Only hijack Up/Down when there's a single line to edit, so
            # multiline editing keeps normal caret movement.
            if self.document.line_count <= 1:
                event.prevent_default()
                event.stop()
                self._recall(-1 if event.key == "up" else 1)
                return

    def _recall(self, direction: int) -> None:
        if self._hist_index is None:
            if direction < 0:
                self._draft = self.text
                self._hist_index = len(self._history) - 1
            else:
                return
        else:
            self._hist_index += direction
        if self._hist_index >= len(self._history):
            self._hist_index = None
            self.load_text(self._draft)
            self.move_cursor(self.document.end)
            return
        if self._hist_index < 0:
            self._hist_index = 0
        self.load_text(self._history[self._hist_index])
        self.move_cursor(self.document.end)


def _load_history() -> list[str]:
    try:
        lines = _HISTORY_PATH.read_text(encoding="utf-8").splitlines()
        return [ln for ln in lines if ln.strip()][-_HISTORY_MAX:]
    except OSError:
        return []


def _append_history(value: str) -> None:
    try:
        _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _HISTORY_PATH.open("a", encoding="utf-8") as fh:
            fh.write(value.replace("\n", " ") + "\n")
    except OSError:
        pass
