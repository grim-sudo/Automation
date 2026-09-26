# Archon — Bug Report

**Audit date:** 2026-03-14
**Python version tested:** 3.14.3
**Test result:** 153 / 153 PASSED

---

## Summary

A comprehensive 12-phase audit was performed covering imports, CLI, NLP, AI layer, security, structured output parsing, n8n bridge, configuration and test suite. Twenty-two bugs were found and fixed. The repository now passes all tests, has zero `shell=True` calls, and zero hardcoded model names.

---

## Bug Table

| # | Severity | File(s) | Description | Fix |
|---|----------|---------|-------------|-----|
| 1 | Medium | `os_adapters/linux_adapter.py` | `pyautogui` import raises `SystemExit` on headless systems, crashing the adapter factory | Broadened the `except` clause to `except (ImportError, SystemExit, Exception)` |
| 2 | High | `os_adapters/linux_adapter.py`<br>`os_adapters/macos_adapter.py`<br>`os_adapters/windows_adapter.py`<br>`os_adapters/arch_adapter.py`<br>`omni.py`<br>`plugins/universal_automation.py` | `import requests` throughout — `requests` was removed from dependencies; any code path that reached these imports raised `ImportError` at runtime | Migrated all usages to `httpx` (already a declared dependency). Streaming downloads use `httpx.Client.stream()` + `iter_bytes()` |
| 3 | Low | `os_adapters/arch_adapter.py` | 13 bare `except:` blocks silently swallow all exceptions including `KeyboardInterrupt` and `SystemExit` | Changed all to `except Exception:` |
| 4 | Low | `os_adapters/adapter_factory.py` | Bare `except:` on platform import guard | Changed to `except Exception:` |
| 5 | Low | `nlp/flexible_processor.py` | Duplicate keys in the intent pattern dict caused silent loss of entries | Removed duplicate keys |
| 6 | Low | `tests/test_path_validator.py` | Test used wrong keyword argument (`sanitize=` → positional), raising `TypeError` on every run | Fixed to pass the argument positionally |
| 7 | High | `tests/test_response_parser.py` | Seven tests wrapped calls to `ResponseParser.parse_task_plan()` / `parse_intent()` in `pytest.raises()`. These methods are documented as **never-raising** — they always return a fallback object. The tests always passed vacuously (no exception = caught by outer `except`) and never actually validated anything | Rewrote all seven to assert on the returned fallback value (empty `TaskPlan`, `IntentResult` with clamped confidence, etc.) |
| 8 | High | `tests/test_response_parser.py` | Five tests imported `_extract_first_json_object` and `_strip_markdown_fences` as module-level functions. Neither symbol exists at module level; both are private instance methods (`parser._find_first_json_object()`, accessible via `parser._extract_json()`) | Removed non-existent imports; rewrote tests to call the correct instance methods |
| 9 | High | `security/path_validator.py` | `validate()` raised bare `ValueError` for path-traversal sequences (`..`) and null-byte injections, but the entire test suite and all callers expected `PathValidationError` (the module's own exception class, a subclass of `PermissionError`) | Changed both `raise ValueError(...)` to `raise PathValidationError(...)` |
| 10 | Medium | `ai/openrouter_integration.py` | `asyncio.get_event_loop()` is deprecated since Python 3.10 and raises `DeprecationWarning` (will be removed in 3.16). Called in two places: during `__init__` task scheduling and the sync wrapper | Replaced with `asyncio.get_running_loop()` + `try/except RuntimeError` pattern in both locations |
| 11 | High | `ai/openrouter_integration.py` | `__init__` loaded the API key via bare `os.getenv("OPENROUTER_API_KEY")` **before** pydantic-settings had processed the `.env` file. pydantic-settings does not inject dotenv values into `os.environ`, so the key was always empty when loaded this way | Changed to read `get_config().ai.openrouter_api_key` first, falling back to `os.getenv` |
| 12 | High | `config.py` — `_CompatEnvSource` | `_CompatEnvSource.__call__()` only read `os.environ`. Because pydantic-settings' own `DotEnvSettingsSource` does **not** inject values into `os.environ`, all legacy flat env vars defined in `.env` (e.g. `OPENROUTER_API_KEY`) were invisible to the compat source | Added `dotenv_values(".env")` read inside `__call__()` as a fallback; `os.environ` still takes priority |
| 13 | High | `config.py` — `_COMPAT_MAP` | `N8N_API_KEY` and `N8N_URL` were absent from `_COMPAT_MAP`, so `.env` entries for n8n were never mapped to the nested `settings.n8n.*` fields. Every n8n API call failed with HTTP 401 | Added `"N8N_API_KEY": ("n8n", "api_key")` and `"N8N_URL": ("n8n", "url")` to `_COMPAT_MAP` |
| 14 | Medium | `nlp/semantic_engine.py` | `deploy`, `release`, `publish`, `ship` lacked any intent pattern match, so commands like "deploy my app" resolved to `IntentType.UNKNOWN` | Added `r'\b(deploy|release|publish|ship)\b'` to the `EXECUTE` pattern list |
| 15 | Medium | `nlp/semantic_engine.py` | `"Build a custom linux iso"` resolved to `IntentType.CREATE` instead of `BUILD_DISTRO` because the only pattern required `build` to appear **immediately** before `custom/linux/iso`; the intervening article `a` broke the match. With only one BUILD_DISTRO match vs one CREATE match, Python dict ordering returned CREATE first | Added a flexible `r'\b(build|create|compile|make)\b.*\b(iso|distro|distribution|linux\s+image)\b'` pattern and a standalone `r'\b(?:linux\s+iso|linux\s+distro|linux\s+distribution|custom\s+iso)\b'` pattern, giving BUILD_DISTRO a higher score |
| 16 | High | `plugins/n8n_bridge/models.py` | `N8nWorkflow.id` was declared as `str = ""`. An empty string is **not** `None`, so `model_dump(exclude_none=True)` kept the empty `id` field in the POST payload. n8n API rejected unknown/empty `id` on workflow creation with HTTP 400 | Changed declaration to `id: str \| None = None` |
| 17 | High | `plugins/n8n_bridge/workflow_manager.py` — `create_workflow` | The `active` field was included in the POST payload for workflow creation. n8n REST API v1 treats `active` as read-only at creation time and returns `400 {"message":"request/body/active is read-only"}` | Added `exclude={"active"}` to the `model_dump()` call |
| 18 | High | `plugins/n8n_bridge/workflow_manager.py` — `create_workflow` | The `tags` field was included in the POST payload. n8n also treats `tags` as read-only at create time, returning the same 400 error after Bug #17 was fixed | Extended exclude to `exclude={"active", "tags"}` |
| 19 | Low | `parsers/command_parser.py` | `ParsedStep.dependencies: List[int] = None` and `.conditions: List[str] = None` — bare `List` default `None` is not valid without `Optional`; mypy flags this as an error and it can cause runtime `TypeError` when type-checked code tries to iterate the field | Changed both to `Optional[List[...]] = None` |
| 20 | Low | `omni.py` | `_n8n_get()` and `_n8n_post()` used `import requests` locally, which was no longer installed | Migrated to `import httpx`; mapped `requests.exceptions.ConnectionError` → `httpx.ConnectError` |
| 21 | Low | `omni.py:754` | Variable `created` was typed as `N8nWorkflow` from its first assignment (line 703) and then reused as `dict` on line 754, causing a mypy type collision | Renamed the second binding to `created_raw` |
| 22 | Low | `.env` | `OPENROUTER_MODEL=stepfun/step-3.5-flash:free` hardcoded a specific model, overriding the `FreeModelResolver` auto-selection that the project requires | Commented the line out; `FreeModelResolver` now selects at runtime |

---

## Issues Not Fixed (Pre-existing / Out of Scope)

| Category | Count | Notes |
|----------|-------|-------|
| `B904` raise-without-from | 110 | `raise X` inside `except` blocks without `from err`. Style-only; not blocking |
| Missing return-type annotations (`ANN*`) | ~100 | Legacy code without type annotations. Not blocking tests |
| `UP045` Optional → `X \| None` | Widespread | Auto-fixable style; ruff applied 2536 auto-fixes |
| `E722` bare `except` | 16 remaining | In platform-specific OS adapter code not touching the main path |
| Platform unused imports (`F401`) | 16 | `winreg`, `win32*`, `AppKit`, `Quartz`, `Xlib` — expected unused on Linux |
| `asyncio.DefaultEventLoopPolicy` DeprecationWarning | 1 | In `tests/conftest.py`; Python 3.16 will remove it; not blocking on 3.14 |
| mypy errors (pre-existing) | ~530 | Distributed across legacy files not touched in this audit |

---

## Ruff Auto-Fix Summary

```
Before:  2959 violations
Fixed:   2536 (auto-fix --fix)
Remaining: 423 (all non-blocking style/annotation issues)
```

---

## Security Audit Results

| Check | Result |
|-------|--------|
| `shell=True` in source files | **CLEAN** — 0 occurrences |
| Hardcoded model names (`gpt-4`, `claude-*`, etc.) | **CLEAN** — 0 occurrences |
| Path traversal protection | **VERIFIED** — `PathValidator` raises `PathValidationError` |
| Subprocess calls | **VERIFIED** — all use list form via `safe_run()`; no shell injection possible |
