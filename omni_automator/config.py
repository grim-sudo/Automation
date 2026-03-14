"""
OmniAutomator configuration module.

Priority order (highest to lowest):
  1. Programmatic overrides (init_settings / CLI flag injection)
  2. Environment variables with OMNI__ prefix and nested delimiter __
  3. Backward-compat flat env vars (OPENROUTER_API_KEY, OPENAI_API_KEY, …)
  4. ~/.omniautomator/config.toml
  5. Hardcoded defaults

Usage::

    from omni_automator.config import get_settings, Settings

    settings = get_settings()
    print(settings.ai.model)
    print(settings.n8n.url)

To force a reload (e.g. in tests)::

    get_settings.cache_clear()
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Tuple, Type

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

__all__ = [
    "AISettings",
    "N8nSettings",
    "DistroBuildSettings",
    "Settings",
    "get_settings",
    "generate_example_config",
    # Legacy aliases kept for backwards compat
    "OmniConfig",
    "get_config",
]

# ---------------------------------------------------------------------------
# TOML loading helper (Python 3.11+ stdlib; falls back to tomli)
# ---------------------------------------------------------------------------

try:
    if sys.version_info >= (3, 11):
        import tomllib  # stdlib
    else:
        import tomli as tomllib  # type: ignore[no-redef]
    _TOML_AVAILABLE = True
except ImportError:
    _TOML_AVAILABLE = False


class _TomlFileSource(PydanticBaseSettingsSource):
    """Reads settings from a TOML file and merges them into the model."""

    def __init__(self, settings_cls: Type[BaseSettings], toml_path: Path) -> None:
        super().__init__(settings_cls)
        self._path = toml_path.expanduser().resolve()
        self._data: dict[str, Any] = self._load()

    # ------------------------------------------------------------------

    def _load(self) -> dict[str, Any]:
        if not _TOML_AVAILABLE or not self._path.exists():
            return {}
        try:
            with open(self._path, "rb") as fh:
                return tomllib.load(fh)
        except Exception:
            return {}

    def get_field_value(
        self, field: Any, field_name: str
    ) -> Tuple[Any, str, bool]:
        val = self._data.get(field_name)
        return val, field_name, False

    def __call__(self) -> dict[str, Any]:
        return self._data


# ---------------------------------------------------------------------------
# Backward-compat flat env-var source
# ---------------------------------------------------------------------------

# Maps bare env var names -> (nested_section, field_name_within_section)
_COMPAT_MAP: dict[str, tuple[str, str]] = {
    "OPENROUTER_API_KEY": ("ai", "openrouter_api_key"),
    "OPENROUTER_MODEL": ("ai", "model"),
    "OPENAI_API_KEY": ("ai", "openai_api_key"),
    "ANTHROPIC_API_KEY": ("ai", "anthropic_api_key"),
    "MAX_RETRIES": ("ai", "max_retries"),
}


class _CompatEnvSource(PydanticBaseSettingsSource):
    """Reads top-level backward-compat env vars and injects them as nested data."""

    def get_field_value(
        self, field: Any, field_name: str
    ) -> Tuple[Any, str, bool]:
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for env_key, (section, field) in _COMPAT_MAP.items():
            val = os.environ.get(env_key)
            if val is not None:
                result.setdefault(section, {})[field] = val
        return result


# ---------------------------------------------------------------------------
# Nested section models (plain BaseModel — not BaseSettings)
# ---------------------------------------------------------------------------

class AISettings(BaseModel):
    """AI provider and model configuration."""

    openrouter_api_key: str = Field(
        default="",
        description="OpenRouter API key",
    )
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key",
    )
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key",
    )
    model: str = Field(
        default="",
        description=(
            "Default AI model in provider/model-id format. "
            "Leave empty to resolve automatically from the OpenRouter free-model list at runtime."
        ),
    )
    fallback_chain: list[str] = Field(
        default_factory=list,
        description=(
            "Ordered list of fallback models when the primary is unavailable. "
            "Leave empty to resolve automatically from the OpenRouter free-model list at runtime."
        ),
    )
    max_tokens: int = Field(
        default=8000,
        description="Max context window tokens",
    )
    timeout: int = Field(
        default=30,
        description="API timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        description="Number of retry attempts on transient failures",
    )
    retry_delay: float = Field(
        default=2.0,
        description="Base delay in seconds between retries",
    )

    @field_validator("max_tokens")
    @classmethod
    def _validate_max_tokens(cls, v: int) -> int:
        if v < 256:
            raise ValueError("max_tokens must be at least 256")
        if v > 200_000:
            raise ValueError("max_tokens cannot exceed 200,000")
        return v

    @field_validator("timeout")
    @classmethod
    def _validate_timeout(cls, v: int) -> int:
        if v < 1:
            raise ValueError("timeout must be at least 1 second")
        return v

    @field_validator("max_retries")
    @classmethod
    def _validate_max_retries(cls, v: int) -> int:
        if v < 0:
            raise ValueError("max_retries cannot be negative")
        return v

    @field_validator("retry_delay")
    @classmethod
    def _validate_retry_delay(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError("retry_delay cannot be negative")
        return v


class N8nSettings(BaseModel):
    """n8n workflow automation integration settings."""

    url: str = Field(
        default="http://localhost:5678",
        description="Base URL of the n8n instance",
    )
    api_key: str = Field(
        default="",
        description="n8n API key for authenticated requests",
    )
    default_error_webhook: str = Field(
        default="",
        description="Webhook URL to POST error notifications to",
    )
    polling_interval_seconds: int = Field(
        default=5,
        description="Interval in seconds to poll for workflow execution status",
    )

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        v = v.strip()
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("n8n url must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("polling_interval_seconds")
    @classmethod
    def _validate_polling(cls, v: int) -> int:
        if v < 1:
            raise ValueError("polling_interval_seconds must be at least 1")
        return v


class DistroBuildSettings(BaseModel):
    """Custom Linux distribution builder settings."""

    work_dir: str = Field(
        default="/tmp/omni_distro_build",
        description="Temporary working directory for build operations",
    )
    output_dir: str = Field(
        default="./distro_output",
        description="Directory where finished ISOs and artifacts are written",
    )
    default_jobs: int = Field(
        default=0,
        description="Parallel build jobs; 0 = auto-detect from CPU count",
    )
    debian_mirror: str = Field(
        default="http://deb.debian.org/debian",
        description="Debian package mirror URL used during debootstrap",
    )
    debian_suite: str = Field(
        default="bookworm",
        description="Debian suite (release codename) for the base system",
    )
    kernel_cache_dir: str = Field(
        default="~/.omniautomator/kernel_cache",
        description="Directory for caching downloaded kernel sources",
    )
    require_root_confirmation: bool = Field(
        default=True,
        description="Prompt for explicit confirmation before root-required operations",
    )

    @field_validator("default_jobs")
    @classmethod
    def _validate_jobs(cls, v: int) -> int:
        if v < 0:
            raise ValueError("default_jobs cannot be negative")
        return v


# ---------------------------------------------------------------------------
# Root Settings class
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path.home() / ".omniautomator" / "config.toml"


class Settings(BaseSettings):
    """
    OmniAutomator root settings.

    Configuration is resolved in this priority order:

    1. Programmatic init overrides (highest priority)
    2. ``OMNI__`` prefixed env vars (e.g. ``OMNI__AI__MODEL``)
    3. Backward-compat flat env vars (``OPENROUTER_API_KEY``, etc.)
    4. ``~/.omniautomator/config.toml``
    5. Hardcoded defaults (lowest priority)
    """

    ai: AISettings = Field(
        default_factory=AISettings,
        description="AI model and provider settings",
    )
    n8n: N8nSettings = Field(
        default_factory=N8nSettings,
        description="n8n workflow automation integration settings",
    )
    distro_builder: DistroBuildSettings = Field(
        default_factory=DistroBuildSettings,
        description="Custom Linux distro builder settings",
    )
    debug: bool = Field(
        default=False,
        description="Enable verbose debug logging",
    )
    log_file: str | None = Field(
        default=None,
        description=(
            "Write structured JSON logs to this file path. "
            "None disables file logging."
        ),
    )
    safe_mode: bool = Field(
        default=False,
        description="Require explicit confirmation for destructive operations",
    )
    continue_on_error: bool = Field(
        default=False,
        description="Continue batch execution even when a command fails",
    )

    # NOTE: ``toml_settings_path`` is stored here for introspection and is also
    # consumed by the custom ``settings_customise_sources`` override below.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        toml_settings_path=_CONFIG_PATH,  # type: ignore[typeddict-unknown-key]
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """
        Custom source priority:

        init_settings > env_settings > dotenv > compat_env > toml_file
        """
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            _CompatEnvSource(settings_cls),
            _TomlFileSource(settings_cls, _CONFIG_PATH),
        )


# ---------------------------------------------------------------------------
# generate_example_config()
# ---------------------------------------------------------------------------

def generate_example_config(path: Path | None = None) -> Path:
    """
    Write a fully commented ``config.example.toml`` to *path*.

    If *path* is ``None`` the file is written to
    ``~/.omniautomator/config.example.toml``.

    Args:
        path: Destination path.  Defaults to
              ``~/.omniautomator/config.example.toml``.

    Returns:
        The ``Path`` that was written.
    """
    if path is None:
        path = Path.home() / ".omniautomator" / "config.example.toml"

    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    content = """\
# OmniAutomator configuration file
# Copy this file to ~/.omniautomator/config.toml and customise as needed.
#
# Priority order for each setting:
#   CLI flag > environment variable > this file > hardcoded default
#
# Nested env var delimiter: "__"
#   e.g. export OMNI__AI__MODEL="openai/gpt-4o"
#        export OMNI__DEBUG=true
#
# Backward-compat flat env vars (no prefix required):
#   OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENAI_API_KEY,
#   ANTHROPIC_API_KEY, MAX_RETRIES

# ── Global ───────────────────────────────────────────────────────────────────

# Enable verbose debug logging (default: false)
# debug = false

# Write structured JSON logs to this file path (default: disabled)
# log_file = "/var/log/omniautomator.jsonl"

# Require explicit confirmation before destructive operations (default: false)
# safe_mode = false

# Keep going in batch mode even when a step fails (default: false)
# continue_on_error = false

# ── AI ───────────────────────────────────────────────────────────────────────

[ai]
# OpenRouter API key  (env: OPENROUTER_API_KEY)
openrouter_api_key = ""

# OpenAI direct API key  (env: OPENAI_API_KEY)
openai_api_key = ""

# Anthropic direct API key  (env: ANTHROPIC_API_KEY)
anthropic_api_key = ""

# Default model in "provider/model-id" format  (env: OPENROUTER_MODEL)
# Leave blank to resolve dynamically from the OpenRouter free-model list.
# model = ""

# Ordered fallback chain when the primary model is unavailable.
# Leave blank to resolve dynamically from the OpenRouter free-model list.
# fallback_chain = []

# Maximum number of tokens to include in a single request
max_tokens = 8000

# Per-request HTTP timeout in seconds
timeout = 30

# Retry attempts on transient failures  (env: MAX_RETRIES)
max_retries = 3

# Base delay (seconds) between retries — uses exponential back-off
retry_delay = 2.0

# ── n8n ──────────────────────────────────────────────────────────────────────

[n8n]
# Base URL of your n8n instance
url = "http://localhost:5678"

# n8n API key (leave blank to skip authenticated requests)
api_key = ""

# Webhook URL to notify on automation errors (leave blank to disable)
default_error_webhook = ""

# How often (seconds) to poll for workflow execution status
polling_interval_seconds = 5

# ── Distro Builder ───────────────────────────────────────────────────────────

[distro_builder]
# Temporary scratch directory used during build operations
work_dir = "/tmp/omni_distro_build"

# Directory where finished ISOs and release artifacts are written
output_dir = "./distro_output"

# Parallel make jobs (0 = auto-detect via nproc / os.cpu_count())
default_jobs = 0

# Debian mirror used by debootstrap
debian_mirror = "http://deb.debian.org/debian"

# Debian suite (release codename) for the base system
debian_suite = "bookworm"

# Directory for caching downloaded kernel source archives
kernel_cache_dir = "~/.omniautomator/kernel_cache"

# Prompt for confirmation before root-required build operations
require_root_confirmation = true
"""

    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# get_settings() singleton
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the global :class:`Settings` singleton.

    The first call reads all sources (env vars, TOML file, defaults) and
    caches the result.  Subsequent calls return the same object.

    To force a fresh load (useful in tests)::

        get_settings.cache_clear()

    Returns:
        Validated :class:`Settings` instance.
    """
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _CONFIG_PATH.exists():
        # Seed the directory with an example config on first run
        try:
            generate_example_config(_CONFIG_PATH.parent / "config.example.toml")
        except OSError:
            pass  # Non-fatal; config still loads from env/defaults
    return Settings()


# ---------------------------------------------------------------------------
# Legacy aliases (kept for backward compatibility with older call sites)
# ---------------------------------------------------------------------------

def get_config(**overrides: Any) -> Settings:
    """Backward-compat alias for :func:`get_settings`.

    If *overrides* are provided a fresh (non-cached) instance is returned.
    """
    if overrides:
        return Settings(**overrides)
    return get_settings()


# Legacy name alias
OmniConfig = Settings
