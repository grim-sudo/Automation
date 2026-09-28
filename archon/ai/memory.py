"""Persistent cross-session memory so Archon retains what it learns.

Archon forgets everything between runs. This module fixes that with a small,
dependency-free memory layer that lives *above* the provider abstraction, so it
works identically whether the active backend is local Ollama or a cloud API
(FreeLLMAPI / OpenAI / Anthropic).

Two pieces, deliberately separated:

* :class:`MemoryStore` — pure persistence (stdlib ``sqlite3`` at
  ``~/.archon/memory.db``). No AI dependency, trivially testable.
* :class:`MemoryManager` — the policy layer: builds the context block injected
  into prompts, runs best-effort LLM fact-extraction through *any* provider's
  ``complete`` coroutine, and handles explicit "remember / forget / what do you
  remember" commands.

Search is a keyword-overlap scan rather than embeddings/FTS: a personal memory
store holds hundreds of rows, not millions, so an O(n) Python scan is simpler,
has no extra dependency, and works on every SQLite build.
``ponytail: O(n) recall scan — swap for FTS5/embeddings only if a store ever
grows past a few thousand rows.``
"""

from __future__ import annotations

import json
import re
import sqlite3
import threading
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loguru import logger

__all__ = ["Memory", "MemoryStore", "MemoryManager"]

_DEFAULT_DB = Path.home() / ".archon" / "memory.db"

# Tiny stopword set so keyword overlap isn't dominated by filler words. Kept
# minimal on purpose — over-filtering hurts recall more than a few stopwords do.
_STOPWORDS = frozenset(
    ["the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at", "for", "with", "from", "by", "is", "are", "was", "were", "be", "been", "being", "do", "does", "did", "i", "you", "he", "she", "it", "we", "they", "me", "my", "your", "his", "her", "our", "their", "this", "that", "these", "those", "what", "which", "who", "whom", "how", "when", "where", "why", "can", "could", "would", "should", "will", "shall", "may", "might", "must", "have", "has", "had", "not", "no", "yes", "if", "then", "than", "so", "as", "about", "user", "users"]
)

_WORD_RE = re.compile(r"[A-Za-z0-9']+")


def _tokens(text: str) -> set[str]:
    """Return the set of meaningful lowercase word tokens in *text*."""
    return {
        w
        for w in (m.group(0).lower() for m in _WORD_RE.finditer(text))
        if len(w) >= 3 and w not in _STOPWORDS
    }


@dataclass
class Memory:
    """A single stored memory."""

    id: int
    content: str
    kind: str
    source: str
    created_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "kind": self.kind,
            "source": self.source,
            "created_at": self.created_at,
        }


class MemoryStore:
    """SQLite-backed persistent store of learned facts.

    Args:
        db_path: Database file path. Defaults to ``~/.archon/memory.db``. Pass
            ``":memory:"`` for an ephemeral in-process store (tests).
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._path = Path(db_path) if db_path is not None else _DEFAULT_DB
        if str(self._path) != ":memory:":
            self._path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: the facade is called from AnyIO worker
        # threads; a single connection guarded by a lock is simplest and the
        # write volume is negligible.
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    content    TEXT NOT NULL,
                    kind       TEXT NOT NULL DEFAULT 'fact',
                    source     TEXT NOT NULL DEFAULT 'auto',
                    created_at REAL NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at)"
            )
            self._conn.commit()

    # ── writes ────────────────────────────────────────────────────────────────

    def remember(
        self, content: str, *, kind: str = "fact", source: str = "auto"
    ) -> Memory | None:
        """Store *content* as a memory, skipping exact duplicates.

        Returns the stored :class:`Memory`, or ``None`` when the content is
        blank or already present verbatim.
        """
        text = (content or "").strip()
        if not text:
            return None
        with self._lock:
            row = self._conn.execute(
                "SELECT id FROM memories WHERE content = ?", (text,)
            ).fetchone()
            if row is not None:
                return None  # already known — don't duplicate
            created = time.time()
            cur = self._conn.execute(
                "INSERT INTO memories (content, kind, source, created_at) "
                "VALUES (?, ?, ?, ?)",
                (text, kind, source, created),
            )
            self._conn.commit()
            return Memory(cur.lastrowid, text, kind, source, created)

    def forget(self, query: str) -> int:
        """Delete memories whose content contains *query* (case-insensitive).

        Returns the number of rows deleted.
        """
        q = (query or "").strip()
        if not q:
            return 0
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM memories WHERE lower(content) LIKE ?",
                (f"%{q.lower()}%",),
            )
            self._conn.commit()
            return cur.rowcount

    def clear(self) -> int:
        """Delete all memories. Returns the number removed."""
        with self._lock:
            count = self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            self._conn.execute("DELETE FROM memories")
            self._conn.commit()
            return int(count)

    # ── reads ───────────────────────────────────────────────────────────────

    def count(self) -> int:
        with self._lock:
            return int(self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0])

    def recent(self, limit: int = 10) -> list[Memory]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, content, kind, source, created_at FROM memories "
                "ORDER BY created_at DESC LIMIT ?",
                (max(0, limit),),
            ).fetchall()
        return [Memory(*r) for r in rows]

    def recall(self, query: str, limit: int = 8) -> list[Memory]:
        """Return memories most relevant to *query* by keyword overlap.

        Ranked by number of distinct query tokens present, then recency. Returns
        only rows with at least one token match (empty list when the query has
        no usable tokens).
        """
        wanted = _tokens(query)
        if not wanted:
            return []
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, content, kind, source, created_at FROM memories"
            ).fetchall()
        scored: list[tuple[int, float, Memory]] = []
        for r in rows:
            mem = Memory(*r)
            overlap = len(wanted & _tokens(mem.content))
            if overlap:
                scored.append((overlap, mem.created_at, mem))
        scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
        return [m for _, _, m in scored[: max(0, limit)]]

    def all(self) -> list[Memory]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, content, kind, source, created_at FROM memories "
                "ORDER BY created_at DESC"
            ).fetchall()
        return [Memory(*r) for r in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()


# ---------------------------------------------------------------------------
# Policy layer
# ---------------------------------------------------------------------------

# An async callable matching every provider's ``complete`` coroutine:
# ``complete(messages, *, temperature, max_tokens, timeout) -> str``.
CompleteFn = Callable[..., Awaitable[str]]

_EXTRACT_SYSTEM = (
    "You extract durable, reusable facts worth remembering long-term about the "
    "user, their preferences, environment, tools, or ongoing projects. Ignore "
    "one-off task details, pleasantries, and anything transient. Output ONLY a "
    "JSON array of short factual strings (max 5). Each string must stand on its "
    "own without the conversation. If nothing is worth remembering, output []."
)

# Explicit user commands. Kept deterministic so "remember X" always works even
# when auto-extraction is off or the model is unavailable.
_REMEMBER_RE = re.compile(
    r"^\s*(?:please\s+)?(?:remember|note|keep in mind|don'?t forget)"
    r"(?:\s+that|\s+this)?\s*[:,]?\s+(.+)$",
    re.IGNORECASE | re.DOTALL,
)
_FORGET_ALL_RE = re.compile(
    r"^\s*forget\s+(?:everything|all|it all|all of it|all memories)\s*[.!]?\s*$",
    re.IGNORECASE,
)
_FORGET_RE = re.compile(
    r"^\s*forget\s+(?:that\s+|about\s+|the\s+)?(.+?)\s*[.!]?\s*$",
    re.IGNORECASE | re.DOTALL,
)
_RECALL_RE = re.compile(
    r"^\s*(?:what do you (?:remember|know)(?:\s+about me)?"
    r"|list (?:your )?memories|show (?:your )?memories)\s*[?.!]?\s*$",
    re.IGNORECASE,
)


class MemoryManager:
    """Injection + extraction policy on top of a :class:`MemoryStore`.

    Args:
        store:        The backing :class:`MemoryStore`.
        auto_extract: When ``True``, :meth:`learn` runs a best-effort LLM
            extraction call after each exchange. When ``False``, only explicit
            "remember" commands store anything.
        max_inject:   Maximum memories injected into a prompt.
    """

    def __init__(
        self,
        store: MemoryStore,
        *,
        auto_extract: bool = True,
        max_inject: int = 8,
    ) -> None:
        self.store = store
        self.auto_extract = auto_extract
        self.max_inject = max_inject

    # ── injection ─────────────────────────────────────────────────────────────

    def context_block(self, query: str) -> str:
        """Return a system-prompt block of relevant memories, or ``""``.

        Combines the memories most relevant to *query* with a few most-recent
        ones (so a stable profile is always present even when the query matches
        nothing), deduplicated and capped at ``max_inject``.
        """
        try:
            relevant = self.store.recall(query, limit=self.max_inject)
            seen = {m.id for m in relevant}
            if len(relevant) < self.max_inject:
                for m in self.store.recent(limit=self.max_inject):
                    if m.id not in seen:
                        relevant.append(m)
                        seen.add(m.id)
                    if len(relevant) >= self.max_inject:
                        break
        except Exception as exc:  # noqa: BLE001 - memory must never break a turn
            logger.debug("memory context_block failed: {}", exc)
            return ""
        if not relevant:
            return ""
        lines = "\n".join(f"- {m.content}" for m in relevant)
        return (
            "Known context about this user and their environment, remembered "
            "from earlier conversations. Use it when relevant; do not repeat it "
            "back verbatim unless asked:\n" + lines
        )

    # ── explicit commands ─────────────────────────────────────────────────────

    def handle_command(self, message: str) -> str | None:
        """Handle an explicit memory command, or return ``None`` if not one.

        Recognises "remember (that) X", "forget X" / "forget everything", and
        "what do you remember". Returns the reply text when handled.
        """
        text = (message or "").strip()
        if not text:
            return None

        if _RECALL_RE.match(text):
            mems = self.store.recent(limit=max(self.max_inject, 20))
            if not mems:
                return "I haven't remembered anything yet."
            body = "\n".join(f"- {m.content}" for m in mems)
            return f"Here's what I remember:\n{body}"

        if _FORGET_ALL_RE.match(text):
            n = self.store.clear()
            return f"Forgotten everything ({n} memor{'y' if n == 1 else 'ies'} cleared)."

        m = _REMEMBER_RE.match(text)
        if m:
            fact = m.group(1).strip().rstrip(".")
            stored = self.store.remember(fact, kind="explicit", source="user")
            if stored is None:
                return "I already had that noted."
            return "Got it — I'll remember that."

        m = _FORGET_RE.match(text)
        if m:
            target = m.group(1).strip()
            n = self.store.forget(target)
            if n == 0:
                return f"I had nothing matching \u201c{target}\u201d to forget."
            return f"Forgotten {n} memor{'y' if n == 1 else 'ies'} matching \u201c{target}\u201d."

        return None

    # ── extraction ─────────────────────────────────────────────────────────────

    async def learn(
        self,
        complete: CompleteFn,
        user_message: str,
        assistant_reply: str,
    ) -> list[Memory]:
        """Extract and store durable facts from one exchange (best-effort).

        Uses *complete* (any provider's coroutine) to pull salient facts. Never
        raises: extraction failures degrade to storing nothing, since memory is
        an enhancement, not a critical path.
        """
        if not self.auto_extract:
            return []
        exchange = (
            f"User: {user_message.strip()}\n\n"
            f"Assistant: {assistant_reply.strip()}"
        )
        messages = [
            {"role": "system", "content": _EXTRACT_SYSTEM},
            {"role": "user", "content": exchange},
        ]
        try:
            raw = await complete(
                messages, temperature=0.0, max_tokens=256, timeout=60.0
            )
        except TypeError:
            # Provider without a timeout kwarg — retry without it.
            try:
                raw = await complete(messages, temperature=0.0, max_tokens=256)
            except Exception as exc:  # noqa: BLE001
                logger.debug("memory extraction call failed: {}", exc)
                return []
        except Exception as exc:  # noqa: BLE001
            logger.debug("memory extraction call failed: {}", exc)
            return []

        facts = _parse_facts(raw)
        stored: list[Memory] = []
        for fact in facts[:5]:
            mem = self.store.remember(fact, kind="fact", source="auto")
            if mem is not None:
                stored.append(mem)
        if stored:
            logger.debug("memory: learned {} new fact(s)", len(stored))
        return stored


def _parse_facts(raw: str) -> list[str]:
    """Parse a model reply into a list of short fact strings.

    Accepts a JSON array (preferred) or a newline/bullet list as a fallback.
    Filters blanks, over-long entries, and obvious "nothing" sentinels.
    """
    text = (raw or "").strip()
    if not text:
        return []

    candidates: list[str] = []
    # Preferred: a JSON array somewhere in the reply.
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            if isinstance(data, list):
                candidates = [str(x) for x in data]
        except (json.JSONDecodeError, ValueError):
            candidates = []
    # Fallback: line/bullet parsing.
    if not candidates:
        for line in text.splitlines():
            cleaned = line.strip().lstrip("-*0123456789.) ").strip()
            if cleaned:
                candidates.append(cleaned)

    out: list[str] = []
    for c in candidates:
        fact = c.strip().strip('"').strip()
        if not fact or len(fact) > 400:
            continue
        if fact.lower() in {"[]", "none", "n/a", "nothing"}:
            continue
        out.append(fact)
    return out
