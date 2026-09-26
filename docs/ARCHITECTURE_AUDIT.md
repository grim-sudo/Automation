# Archon — Architecture Audit (Phase 1)

**Date:** 2026-09-26
**Baseline:** clean working tree at `3f08400`; `pytest -m "not integration and not slow"` → **153 passed**.
**Scope of this document:** describe Archon *as it actually exists* before any refactor. No code moved yet.

---

## 1. Repository shape

```
Automation/
├── main.py            legacy argparse shim → delegates to archon._cli:app
├── archon.py         real launcher: Rust-CLI feature flag, Tauri IPC, then typer app
├── launch_chatbot.py  thin launchers
├── launch_gui.py
├── archon/           the Python package (~31.5k LOC)
├── crates/            Rust workspace: archon-cli, archon-core
├── ui-tauri/          Tauri v2 + Vite + TS desktop UI
├── tests/             153 unit tests
└── docs/
```

### Python package layout (source of truth)

| Area | Files | Role |
|---|---|---|
| `core/` | `engine.py` (913), `plugin_manager.py` (210) | Orchestrator + plugin ABC/loader |
| `ai/` | `task_executor.py` (2033), `openrouter_integration.py` (912), `model_manager.py`, `model_resolver.py`, `response_parser.py`, `task_planner.py`, `context_manager.py` | Model routing, async client, planning, **and a second executor** |
| `parsers/` | `command_parser.py` (1873), `ai_parser.py` (370) | Intent + step extraction |
| `nlp/` | `semantic_engine.py`, `flexible_processor.py`, `spell_corrector.py` | 10-intent classifier, slot filling, typo correction |
| `os_adapters/` | `base_adapter.py`, `linux/arch/windows/macos_adapter.py`, `adapter_factory.py` | Per-OS filesystem/process/gui/system/network |
| `plugins/` | `universal_automation.py` (1733), `web_automation.py` (1445), `project_generator.py`, `devops_generator.py`, `folder_operations.py`, `n8n_bridge/` | Feature plugins |
| `workflow/` | `engine.py` (2180), `error_handler.py` | Multi-step workflow execution |
| `security/` | `permission_manager.py`, `path_validator.py`, `subprocess_runner.py` | Policy + safe_run |
| `distro_builder/` | pipeline + profiles + stages | Independent ISO build subsystem |
| `ui/` | `cli.py`, `chatbot.py`, `gui/` (CustomTkinter) | User interfaces |
| `config.py` (549), `utils/logger.py` | Config + logging |

---

## 2. Entry points

1. **`archon.py`** (canonical). Order of concerns in one file:
   - `ARCHON_RUST_CLI=1` → exec the compiled Rust binary and exit.
   - `--tauri-ipc` → JSON stdin/stdout dispatcher (`chat`, `run`, `n8n_*`, `distro_*`, `models`, …). Each action re-imports and re-instantiates subsystems per call.
   - otherwise → `archon._cli:app` (typer).
2. **`main.py`** — legacy argparse → translates flags → calls `archon._cli:app`.
3. **`pyproject.toml` script** `archon = archon._cli:app`.
4. **Rust** `crates/archon-cli` → `archon-bin`; **Tauri** `ui-tauri/src-tauri` shells back to `python archon.py --tauri-ipc`.

**Finding:** entry logic, transport (Tauri IPC), and subsystem wiring are interleaved in `archon.py`. The IPC dispatcher is a de-facto second API surface that duplicates CLI wiring.

---

## 3. Current application boundaries

```
CLI / IPC / GUI
      │
      ▼
core.engine.Archon ──────────────┐
   ├── parsers (command_parser, ai_parser)
   ├── nlp (semantic_engine, …)
   ├── permission_manager
   ├── os_adapters (via factory)
   ├── plugin_manager → plugins/*
   └── workflow.engine.WorkflowEngine (holds a back-reference to Archon)

ai.task_executor.AITaskExecutor  ← SECOND, parallel execution engine
```

`Archon.execute()` decides simple vs complex, checks permissions, then dispatches to either an OS adapter, a plugin (by category, alias, or advertised capability), or file handlers. `WorkflowEngine` re-implements a large per-step dispatch with its own code-generation helpers.

---

## 4. Duplicated functionality (highest-value cleanup targets)

| Duplicate | Locations |
|---|---|
| `_resolve_file_with_disambiguation` | `core/engine.py` **and** `ai/task_executor.py` (near-identical) |
| `_generate_prime_number_code` / `_generate_fibonacci_code` | `core/engine.py`, `ai/task_executor.py`, and code-gen in `workflow/engine.py` |
| File read/write/modify handlers | `core/engine.py` (`_handle_*`) and `ai/task_executor.py` (`_handle_*`) |
| "Is this dangerous?" logic | `core/engine.py._is_dangerous_command` (keyword list) **parallel to** `security/permission_manager.py` (structured levels) |
| Two execution engines | `core.engine`+`workflow.engine` vs `ai.task_executor` — overlapping step handling |
| Path resolution | scattered `_resolve_path` in `universal_automation`, engine, task_executor |

This is the "accumulated over time" smell. Consolidating these is where the refactor pays off most.

---

## 5. Oversized modules (god modules)

| Lines | File | Notes |
|---|---|---|
| 2180 | `workflow/engine.py` | dispatch + code generation + folder ops + git/backup/download steps |
| 2033 | `ai/task_executor.py` | ~40 `_handle_*` methods; a parallel engine |
| 1873 | `parsers/command_parser.py` | |
| 1733 | `plugins/universal_automation.py` | packages + docs(.docx/.pptx/.xlsx/.pdf) + website + cloud + monitoring |
| 1445 | `plugins/web_automation.py` | |
| 913 | `core/engine.py` | includes embedded code-gen literals |

`universal_automation.py` is the explicit catch-all called out in the brief: package mgmt, document generation, website scaffolding, cloud deploy, and monitoring all in one plugin.

---

## 6. Existing abstractions we can build ON (do not reinvent)

- **`AutomationPlugin` ABC** (`core/plugin_manager.py`): `name`, `description`, `version`, `get_capabilities() -> list[str]`, `execute(action, params)`, `initialize()`, `cleanup()`. This is already ~90% of the requested Capability interface. The requested capability layer should **wrap/extend this**, not replace it.
- **`PluginManager`**: register/unregister/execute/`get_plugin_by_capability`/shutdown — already a proto-registry (with prefix matching).
- **OS adapters**: clean `Base*Adapter` hierarchy + `OSAdapterFactory` with distro detection. Already isolated behind interfaces — **matches the target `os/` design; leave in place.**
- **Security**: `PermissionLevel {SAFE, MODERATE, HIGH, CRITICAL}`, `ActionCategory`, `PermissionRule` with `requires_confirmation` and blocked paths. This maps directly onto the requested `risk: low/medium/high/destructive` + approval model.
- **AI layer**: `ModelManager`/`ModelRoute` fallback chain, `FreeModelResolver` (no hardcoded model), async `OpenRouterClient`. Already independent of tools. **Matches target; preserve.**

---

## 7. Security-sensitive code

- `security/subprocess_runner.py` — `safe_run()` list-form, no `shell=True`. All subprocess should go through it.
- `security/path_validator.py` — traversal + null-byte checks (22 tests).
- `security/permission_manager.py` — the real policy engine.
- **Risk:** `core/engine.py._is_dangerous_command` is a *second, weaker* gate (substring keyword match) that runs independently and only warns. Any refactor must route dangerous ops through `permission_manager`, not this list.
- Distro builder invokes `debootstrap`/`xorriso`/`pacstrap` — must stay on `safe_run`.

---

## 8. Tests (baseline behavior)

`tests/`: `test_model_fallback`, `test_model_resolver`, `test_nlp`, `test_path_validator`, `test_response_parser`, `test_spell_corrector` → **153 passed**, all pure unit tests.

**Coverage gaps (no tests today):** `core.engine` dispatch, `plugin_manager`, `workflow.engine`, OS adapters, `permission_manager` enforcement, n8n bridge, distro pipeline. These gaps are exactly the areas the refactor will touch, so characterization tests are needed before moving that code.

---

## 9. Config & environment

- `config.py` (pydantic-settings): priority `CLI flag → SECTION__FIELD env → .env → ~/.archon/config.toml → default`. Sections: `ai`, `n8n`, `distro_builder`, plus `debug`/`safe_mode`.
- Separately, `permission_manager` persists `~/.archon/permissions.json`.
- Rust has its own `crates/archon-core/src/config.rs`.
- **Finding:** config is fairly centralized in Python already; secrets come from env/.env (not committed). Runtime state (execution_history, permissions.json) is not clearly separated from config.

---

## 10. Rust / Python / Tauri ownership (as-is)

| Component | Language | Status |
|---|---|---|
| CLI | Python (`_cli.py`) canonical; Rust (`archon-cli`) behind `ARCHON_RUST_CLI=1` | Rust delegates AI back to Python |
| Core intent/security/config | duplicated: Python `archon/*` and Rust `archon-core/*` | Parallel implementations |
| GUI | CustomTkinter (`archon/ui/gui`) default; Tauri (`ui-tauri`) behind `ARCHON_GUI=tauri` | Two GUIs |
| AI, distro, n8n, plugins | Python only | — |

`docs/MIGRATION.md` describes a **different** v3 vision (polyglot: Rust CLI, Go n8n, Rust distro). That plan is orthogonal to — and partly in tension with — the capability-platform vision in the new brief. **This needs an explicit decision** (see open questions).

---

## 11. Gap vs. target architecture

| Target (brief) | Today | Gap |
|---|---|---|
| Agent Core | `core.engine.Archon` (mixes parse+dispatch+file ops) | needs a thin, traceable observe→plan→execute→verify loop |
| Capability Router | `PluginManager.get_plugin_by_capability` + engine if/elif | proto-router; no unified capability object |
| Capability abstraction | per-plugin string lists | no `Capability` with discover/validate/execute/risk/health |
| Capability Registry | `PluginManager` (plugins only) | needs to also hold native + MCP capabilities |
| MCP Gateway | **absent** | new, additive |
| Native tools / OS / Build / Data / Git / Cloud | in plugins + adapters + universal_automation | present but not behind capability boundary; **data** boundary absent |
| n8n | `plugins/n8n_bridge` (works) | move behind capability boundary |
| Policy layer | `permission_manager` (+ weak engine gate) | unify; make model requests pass through it |

---

## 12. Recommended migration order (minimizes risk, each step independently shippable)

Status legend: ✅ done · 🔵 partial · ⬜ not started

1. ✅ **Characterization tests** for engine dispatch + permission enforcement (lock current behavior before touching it). — `tests/test_engine_dispatch.py`, `tests/test_permission_manager.py`.
2. ✅ **Capability core (additive):** small `Capability` protocol + `CapabilityRegistry` that **wraps the existing `PluginManager`** so every current plugin appears as a capability with risk metadata.
3. ✅ **Unify the danger gate:** `engine._is_dangerous_command` now delegates to `permission_manager.is_dangerous_command` (duplicate removed).
4. ✅ **De-duplicate** file/code-gen helpers shared by `core.engine` and `ai.task_executor` → `utils/file_resolver.py`, `utils/codegen.py`.
5. 🔵 **Split `universal_automation.py`** by responsibility behind capabilities. Done: `documents` (`capabilities/native/documents.py`), `filesystem` (`capabilities/native/filesystem.py`). Remaining: packages/software (HIGH risk — needs review), website, cloud, monitoring.
   - ✅ **Registry is the execution router:** `engine._execute_parsed_command` resolves + dispatches through `CapabilityRegistry.route()`/`dispatch()`; the duplicated `get_plugin_by_capability` + `plugin_manager.execute` logic in the engine is gone. `PluginManager` stays as loader/lifecycle owner. (`workflow/engine.py` still has its own copy — see step 7.)
6. ⬜ **n8n behind a capability**; then **MCP gateway** as a third capability source.
7. ⬜ **Agent execution loop** extracted with limits/timeout/cancel/trace. Also fold `workflow/engine.py`'s duplicate per-step dispatch onto the registry.
8. ⬜ **Data capability boundary** (interface only, no engines).
9. ⬜ Docs per section 21.

Each step is a logical commit. OS adapters, distro builder, AI model routing, and the Tauri boundary are already close to target and should be **left largely in place**.

---

## 13. Explicitly "do not move" (already correct)

- `os_adapters/` hierarchy + factory.
- `ai/model_manager.py`, `model_resolver.py`, `openrouter_integration.py` (model routing/fallback).
- `distro_builder/` subsystem internals.
- `security/subprocess_runner.py`, `path_validator.py`.
- `plugins/n8n_bridge/` REST client internals (only wrap, don't rewrite).
