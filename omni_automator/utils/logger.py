"""Structured logging utilities for OmniAutomator using loguru."""

from __future__ import annotations

import functools
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, TypeVar, Union

from loguru import logger

__all__ = [
    "configure_logging",
    "get_logger",
    "setup_logger",
    "log_execution",
    "logger",
]

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

_LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | "
    "{name}:{function}:{line} | {message}"
)

_CONSOLE_FORMAT = (
    "<green>{time:HH:mm:ss}</green> | "
    "<level>{level:<8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

# Track whether configure_logging has been called so we only auto-init once.
_configured: bool = False

# ---------------------------------------------------------------------------
# Core configuration
# ---------------------------------------------------------------------------


def configure_logging(
    debug: bool = False,
    log_file: str | None = None,
) -> None:
    """Configure the global loguru logger.

    Removes **all** existing loguru sinks and installs fresh ones:

    - A ``stderr`` sink at level ``DEBUG`` when *debug* is ``True``, otherwise
      at ``INFO``.
    - An optional JSON-formatted file sink when *log_file* is given.

    This function is idempotent: calling it multiple times replaces the sinks
    rather than stacking duplicates.

    Args:
        debug:    ``True`` → set console level to ``DEBUG`` and enable
                  exception diagnostics.
        log_file: Path to a file that receives newline-delimited JSON log
                  records.  ``None`` disables file logging.
    """
    global _configured

    # Reset every existing sink so re-calls are idempotent.
    logger.remove()

    level = "DEBUG" if debug else "INFO"

    # ── Stderr sink (human-readable with colour) ─────────────────────────────
    logger.add(
        sys.stderr,
        format=_CONSOLE_FORMAT,
        level=level,
        colorize=True,
        backtrace=True,
        diagnose=debug,
    )

    # ── File sink (JSON, optional) ────────────────────────────────────────────
    if log_file:
        log_path = Path(log_file).expanduser().resolve()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(log_path),
            level="DEBUG",
            format="{message}",     # loguru serialize=True handles the JSON
            serialize=True,
            rotation="50 MB",
            retention="30 days",
            compression="gz",
            enqueue=True,           # thread-safe async writes
            backtrace=True,
            diagnose=False,         # avoid leaking locals to the log file
            encoding="utf-8",
        )

    _configured = True


# ---------------------------------------------------------------------------
# Auto-initialise with sensible defaults at import time
# ---------------------------------------------------------------------------

def _default_init() -> None:
    """Configure logging on first import so the module is always usable."""
    log_dir = Path.home() / ".omni_automator" / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime

        log_path = log_dir / f"omni_{datetime.now().strftime('%Y%m%d')}.log"
        _env_level = os.getenv("OMNI_LOG_LEVEL", "INFO").upper()
        configure_logging(
            debug=(_env_level == "DEBUG"),
            log_file=str(log_path),
        )
    except Exception:
        # Never let logging setup crash the application
        try:
            configure_logging(debug=False)
        except Exception:
            pass


_default_init()


# ---------------------------------------------------------------------------
# Public accessors
# ---------------------------------------------------------------------------


def get_logger(name: str) -> "logger.__class__":
    """Return a loguru logger bound with the context key ``name``.

    The returned object is a fully-featured loguru ``Logger`` instance — it
    supports ``.debug()``, ``.info()``, ``.warning()``, ``.error()``,
    ``.exception()``, ``.bind()``, etc.

    Existing call sites that previously used a ``logging.Logger`` continue to
    work because loguru's interface is a strict superset.

    Args:
        name: Component or module name embedded in every log record.

    Returns:
        A loguru ``Logger`` with ``name`` bound in its extra context.
    """
    if not _configured:
        configure_logging()
    return logger.bind(name=name)


def setup_logger(
    name: str,
    log_file: str | None = None,
    level: Union[str, int] = "INFO",
) -> "logger.__class__":
    """Backward-compatible logger factory.

    Ensures :func:`configure_logging` has been called (optionally with the
    given *log_file*) and returns a bound logger for *name*.

    Args:
        name:     Component name bound into every log record's extra context.
        log_file: Optional path for a JSON file sink.  If ``None`` and the
                  module was already configured with a file sink, that sink
                  remains active.
        level:    Minimum log level as a string (``"DEBUG"``, ``"INFO"``, …)
                  or an ``int`` (stdlib ``logging`` constants are accepted for
                  backward compatibility).

    Returns:
        A loguru ``Logger`` instance bound with *name*.
    """
    # Normalise level
    if isinstance(level, int):
        # Map stdlib logging int levels: DEBUG=10, INFO=20, WARNING=30, ERROR=40
        _int_map = {10: "DEBUG", 20: "INFO", 30: "WARNING", 40: "ERROR", 50: "CRITICAL"}
        level_str = _int_map.get(level, "INFO")
    else:
        level_str = str(level).upper()

    debug = level_str == "DEBUG"

    if not _configured or log_file:
        configure_logging(debug=debug, log_file=log_file)

    return get_logger(name)


# ---------------------------------------------------------------------------
# log_execution decorator
# ---------------------------------------------------------------------------

_F = TypeVar("_F", bound=Callable[..., Any])


def log_execution(func: _F) -> _F:
    """Decorator that logs function entry and exit at ``DEBUG`` level with timing.

    - On **entry**: logs ``>> qualified_name(preview_of_args)``
    - On **exit**: logs ``<< qualified_name  [elapsed ms]``
    - On **error**: logs ``!! qualified_name raised ExcType: msg  [elapsed ms]``

    The decorator is transparent — it preserves ``__name__``, ``__doc__``,
    ``__module__``, and ``__wrapped__`` via :func:`functools.wraps`.

    Args:
        func: The callable to wrap.

    Returns:
        The wrapped callable.

    Example::

        from omni_automator.utils.logger import log_execution

        @log_execution
        def run_task(command: str) -> dict:
            ...
    """
    _bound = logger.bind(name=func.__module__)

    @functools.wraps(func)
    def _wrapper(*args: Any, **kwargs: Any) -> Any:
        preview = _format_args(args, kwargs)
        _bound.opt(depth=1).debug(">> {}({})", func.__qualname__, preview)
        t0 = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            elapsed = (time.perf_counter() - t0) * 1000
            _bound.opt(depth=1).debug(
                "<< {}  [{:.1f} ms]", func.__qualname__, elapsed
            )
            return result
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            _bound.opt(depth=1).debug(
                "!! {} raised {} after {:.1f} ms: {}",
                func.__qualname__,
                type(exc).__name__,
                elapsed,
                exc,
            )
            raise

    return _wrapper  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _format_args(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    """Produce a compact, truncated representation of call arguments."""
    parts: list[str] = []
    for a in args:
        parts.append(_trunc(repr(a)))
    for k, v in kwargs.items():
        parts.append(f"{k}={_trunc(repr(v))}")
    return ", ".join(parts)


def _trunc(s: str, max_len: int = 80) -> str:
    """Truncate *s* to *max_len* characters with a ``…`` suffix."""
    return s if len(s) <= max_len else s[: max_len - 3] + "..."
