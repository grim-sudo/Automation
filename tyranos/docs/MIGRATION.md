# Tyranos — Polyglot Migration Architecture

**Status:** Planning
**Target version:** 3.0
**Profiled baseline:** Python 3.10, Tyranos 2.0, x86_64 Linux (Arch)

---

## 1. Why Migrate?

### Profiled Baselines (Tyranos 2.0)

| Metric | Measured value | Target (v3.0) |
|---|---|---|
| CLI cold-start (core imports) | **1,494 ms** | < 80 ms |
| Peak memory at startup | **33.3 MB** | < 12 MB |
| NLP parse average | **0.48 ms** | < 0.3 ms |
| NLP parse worst-case | **1.44 ms** | < 0.5 ms |
| GUI startup (CustomTkinter) | ~2,800 ms | < 400 ms |
| Packaged binary size | ~85 MB (PyInstaller) | < 8 MB |

The Python runtime alone adds > 1 second of cold-start. For a CLI tool invoked per command
this is unacceptable. A compiled CLI binary starts in **< 20 ms**.

---

## 2. Proposed Stack

```
tyranos/
├── cli/          → Rust (Clap)          cold-start ~18 ms, binary ~2.5 MB
├── core/         → Rust (library crate) shared logic, FFI bridge
├── ai/           → Python (kept)        OpenRouter async client, ML deps
├── nlp/          → Rust (port)          regex NLP + trie intent matching
├── gui/          → Tauri (Rust + TS)    native webview, ~400 ms cold-start
├── n8n_bridge/   → Go                   goroutine HTTP multiplexer
└── distro_builder/ → Rust              safe subprocess + syslinux/xorriso
```

### Language rationale

| Component | Language | Reason |
|---|---|---|
| CLI / Core | Rust | Zero-cost abstractions, compile-time safety, tiny binary |
| AI layer | Python (kept) | httpx, tenacity, tiktoken — deep Python ecosystem |
| GUI | Tauri (Rust + Web) | Native webview, ships existing TypeScript UI, ~8 MB |
| n8n bridge | Go | goroutines ideal for HTTP fan-out; simpler than Rust async |
| Distro builder | Rust | Subprocess safety, no GIL, joins naturally with CLI |

---

## 3. Migration Triggers

Migrate a component only when **all three** of its triggers fire.

### CLI / Core → Rust

| Trigger | Threshold | Current |
|---|---|---|
| Cold-start SLA breach | > 200 ms P95 | 1,494 ms ✗ |
| Binary size target | > 20 MB | ~85 MB ✗ |
| Profiling shows Python is bottleneck | > 60% CPU in cpython overhead | yes ✗ |

**Decision: migrate CLI first (Phase 1).**

### GUI → Tauri

| Trigger | Threshold | Current |
|---|---|---|
| GUI cold-start | > 1,000 ms | ~2,800 ms ✗ |
| Maintains design system | design tokens portable | yes ✓ |
| Packaging size | > 50 MB | ~85 MB ✗ |

**Decision: migrate GUI in Phase 2, after CLI is stable.**

### n8n Bridge → Go

| Trigger | Threshold | Current |
|---|---|---|
| Concurrent workflow executions | > 50/s needed | Python GIL ✗ |
| Latency P99 | > 50 ms | not yet measured |
| n8n usage active | adopted by user | conditional |

**Decision: migrate when n8n usage exceeds 20 active workflows.**

### Distro Builder → Rust

| Trigger | Threshold | Current |
|---|---|---|
| Build pipeline errors from unsafe subprocess | > 1 per week | TBD |
| ISO build time target | > 20 min | TBD |

**Decision: migrate with CLI crate (shared subprocess safety lib).**

---

## 4. Phase Plan

### Phase 1 — Rust CLI skeleton (target: 3.0-alpha)

**Goal:** `tyranos <cmd>` cold-start < 80 ms.

1. Create `crates/tyranos-cli/` with Clap 4 argument parser.
2. Implement NLP intent classifier in Rust (port regex patterns from `nlp/semantic_engine.py`).
3. For AI operations: shell out to `python -m tyranos.ai <json>` — keeps Python AI layer untouched.
4. Feature flag: `TYRANOS_RUST_CLI=1` activates Rust binary; Python CLI remains default.
5. Validation: cold-start benchmark must reach < 80 ms before flag is removed.

**Rollback:** `TYRANOS_RUST_CLI=0` or delete binary — Python `_cli.py` is unchanged.

**Files touched:**
- `crates/` (new — Rust workspace)
- `Cargo.toml` (new)
- `pyproject.toml` — add `[tool.maturin]` for Python ↔ Rust FFI if needed

### Phase 2 — Tauri GUI (target: 3.0-beta)

**Goal:** GUI cold-start < 400 ms; design parity with CustomTkinter v2 GUI.

1. Port `tyranos/ui/gui/theme.py` color tokens to CSS custom properties.
2. Scaffold Tauri app in `ui-tauri/` — reuse existing TypeScript/React component library or write minimal vanilla TS.
3. Tauri commands (Rust) bridge to Python AI layer via stdio JSON-RPC.
4. Feature flag: `TYRANOS_GUI=tauri|ctk` — default remains `ctk` until parity achieved.
5. CustomTkinter GUI (`tyranos/ui/gui/`) remains fully functional as fallback.

**Rollback:** `TYRANOS_GUI=ctk` restores v2 GUI immediately.

### Phase 3 — Go n8n bridge (target: 3.1)

**Goal:** Handle > 50 concurrent workflow triggers with < 20 ms P99.

1. Implement Go module `n8n-bridge/` with goroutine HTTP multiplexer.
2. Expose gRPC or HTTP/2 API; Python `n8n_bridge/` becomes thin client.
3. Feature flag: `TYRANOS_N8N_BACKEND=go|python`.

**Rollback:** `TYRANOS_N8N_BACKEND=python` — Go service stops, aiohttp client resumes.

### Phase 4 — Rust distro builder (target: 3.1)

**Goal:** Eliminate unsafe shell string interpolation in ISO pipeline.

1. Port `distro_builder/build_pipeline.py` stages to Rust.
2. Use `std::process::Command` builder pattern (no `shell=true`).
3. Share subprocess safety logic with CLI crate.

---

## 5. Interop Strategy

### Python ↔ Rust

```
Python caller  →  maturin PyO3 bindings  →  Rust lib crate
             OR
Python caller  →  subprocess JSON-RPC    →  Rust binary
```

Use **PyO3 / maturin** for hot-path NLP (< 1 ms target). Use **subprocess JSON-RPC** for cold-path AI operations (already slow due to HTTP).

### Python ↔ Go (n8n bridge)

```
Python aiohttp  →  HTTP/2 localhost  →  Go net/http server
```

The Python client calls `http://localhost:5679/api/v1/...` — identical URL shape to current n8n REST API calls; only the backend changes.

### Tauri ↔ Python (AI layer)

```
Tauri frontend  →  Tauri command (Rust)  →  spawn python -m tyranos.ai
                                         ←  stdout JSON stream
```

SSE streaming preserved: Python writes `data: {...}\n\n` to stdout; Rust relays to Tauri event bus.

---

## 6. Rollback Flags Summary

| Component | Env var | Safe value | Risky value |
|---|---|---|---|
| CLI | `TYRANOS_RUST_CLI` | `0` (Python) | `1` (Rust) |
| GUI | `TYRANOS_GUI` | `ctk` (CustomTkinter) | `tauri` |
| n8n bridge | `TYRANOS_N8N_BACKEND` | `python` | `go` |
| Distro builder | `TYRANOS_DISTRO_BACKEND` | `python` | `rust` |

All flags default to `python`/`ctk` so `git bisect` always works without recompiling.

---

## 7. Testing Strategy

- **Parity tests:** each new component must pass the existing `tests/` suite via JSON-RPC adapter.
- **Benchmark CI step:** `benches/` crate measures cold-start and NLP latency on each PR; fails if targets regress.
- **Integration tests tagged `polyglot`:** run only in CI Phase > 1 environments.

---

## 8. What Does NOT Change

- `tyranos/config.py` — config schema, env vars, `~/.tyranos/config.toml` path
- `tyranos/ai/` — entire AI layer stays Python until Phase 4+
- `tyranos/_cli.py` — the Python CLI entry point remains for `pip install` users
- `tests/` — all 153 existing tests must continue to pass throughout migration
- `pyproject.toml` extras (`[gui]`, `[n8n]`, etc.) — install surface unchanged

---

*Generated: 2026-03-15. Update measurements before each phase gate.*
