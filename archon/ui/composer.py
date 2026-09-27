"""Interactive input composer for the Archon console.

A thin wrapper over ``prompt_toolkit`` providing history, arrow-key recall,
multiline composition, slash-command and path completion, and clean paste
handling. When ``prompt_toolkit`` is unavailable or the session is not attached
to a TTY (piped/non-interactive), it degrades to the stdlib :func:`input`
(readline-backed when present) so scripts and pipes keep working.

Presentation/input only — it returns the typed string and lets the caller do
everything else.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path

_HISTORY_PATH = Path.home() / ".archon" / "chatbot_history"

try:  # prompt_toolkit is preferred but optional.
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion, PathCompleter
    from prompt_toolkit.formatted_text import ANSI
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.key_binding import KeyBindings

    _HAVE_PTK = True
except ImportError:  # pragma: no cover - exercised only without the dep
    _HAVE_PTK = False


# Slash-commands surfaced by completion. Kept in sync with the chatbot's real
# handlers by the chatbot passing its command names in.
def _slash_completer(commands: Iterable[str]) -> Completer:
    path_completer = PathCompleter(expanduser=True)
    cmds = sorted(set(commands))

    class _SlashCompleter(Completer):
        def get_completions(self, document, complete_event):  # noqa: ANN001
            text = document.text_before_cursor
            if not text.startswith("/"):
                return
            head, _, tail = text.partition(" ")
            # Complete the command name itself.
            if not _:
                word = head[1:]
                for cmd in cmds:
                    if cmd.startswith(word):
                        yield Completion(cmd, start_position=-len(word))
                return
            # Path completion for commands that take a filesystem path.
            if head[1:] in ("cd", "ls"):
                sub = document.__class__(tail, cursor_position=len(tail))
                yield from path_completer.get_completions(sub, complete_event)

    return _SlashCompleter()


class Composer:
    """Reads one line (or block) of user input per :meth:`prompt` call."""

    def __init__(self, commands: Iterable[str] | None = None) -> None:
        self._commands = list(commands or [])
        self._interactive = _HAVE_PTK and sys.stdin.isatty() and sys.stdout.isatty()
        self._session = self._build_session() if self._interactive else None

    def _build_session(self) -> object | None:
        try:
            _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            bindings = KeyBindings()

            @bindings.add("enter")
            def _(event) -> None:  # noqa: ANN001 - submit on Enter
                event.current_buffer.validate_and_handle()

            @bindings.add("escape", "enter")
            def _(event) -> None:  # noqa: ANN001 - Alt/Esc+Enter → newline
                event.current_buffer.insert_text("\n")

            return PromptSession(
                history=FileHistory(str(_HISTORY_PATH)),
                completer=_slash_completer(self._commands),
                complete_while_typing=True,
                multiline=True,
                key_bindings=bindings,
            )
        except Exception:  # pragma: no cover - defensive; fall back to input()
            self._interactive = False
            return None

    def prompt(self, message_ansi: str, plain_prompt: str = "> ") -> str:
        """Return one submission.

        Raises ``EOFError`` on Ctrl+D / end of pipe and ``KeyboardInterrupt``
        on Ctrl+C so the session loop can handle them uniformly.

        Args:
            message_ansi: ANSI-coloured prompt for the interactive path.
            plain_prompt: Plain prompt used on the fallback path.
        """
        if self._session is not None:
            return self._session.prompt(ANSI(message_ansi)).strip()
        # Fallback: stdlib input (readline gives history when importable).
        return input(plain_prompt).strip()

    @property
    def interactive(self) -> bool:
        return self._interactive
