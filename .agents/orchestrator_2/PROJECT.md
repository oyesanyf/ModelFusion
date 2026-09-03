# Project: ModelFusion Comprehensive Code Review, Safety Audit & Architectural Verification

## Architecture & System Overview
ModelFusion is a hybrid multi-language system combining:
1. **Rust Core Engine (`crates/`)**: High-performance local LLM orchestrator, task detection, model selection, AST/PE analysis, fusion engine, and CLI runtime (`crates/cli`, `crates/core`, `crates/analysis`, `crates/monitoring`, `crates/task_detection`, `crates/model_selection`, `crates/security`, `crates/db`, `crates/utils`).
2. **TypeScript / IDE Subsystem (`IDE/vscode/extensions/copilot/`)**: HugOS IDE extension integrating multi-agent team presets, real-time 60fps asynchronous ring-buffered IPC event streaming, Webview activity bar dashboards, native candidate diff viewer (`hugos-candidate://`), and VS Code LM API provider.
3. **Python & AVO/Evolutionary Subsystems (`src/openevolve/`, `src/scripts/`, `canned_benchmark/`, `scratch/`)**: Multi-provider inference backends (Transformers, ONNX, OpenVINO, GGUF), MCP servers, evolutionary optimization engines (OpenEvolve, MAP-Elites, AVO), and automated test harnesses.

---

## Feature Inventory

| # | Feature / Module | Scope & Description | Milestone | Source |
|---|---|---|---|---|
| F1 | Rust Memory Safety & Unsafe Audit | Audit 9 core crates for `unsafe` blocks, raw pointers, FFI, drop semantics, byte slicing boundaries | M1 | `survey_rust.md` / `audit_rust.md` |
| F2 | Rust Concurrency & Deadlock Audit | Audit Mutex, RwLock, Tokio async runtimes, `INFERENCE_SEM`/`FAST_SEM` hardware throttling | M1 | `survey_rust.md` / `audit_rust.md` |
| F3 | Rust Subprocess & Network Security | Audit TLS certificate verification (`danger_accept_invalid_certs`), PowerShell silent downloads, `std::env::set_var` in async | M1 | `survey_rust.md` / `audit_rust.md` |
| F4 | TypeScript Disposable Lifecycle & Leaks | Audit `vscode.Disposable`, `lm.registerMcpServerDefinitionProvider`, `onDidChangeTextDocument`, and decoration lifecycles | M2 | `survey_ts.md` / `review_ts.md` |
| F5 | TypeScript Concurrency & UI Responsiveness | Audit 60fps `AsyncRingBuffer`, eliminate synchronous `child_process.execSync`, verify HTTP polling non-blocking timeouts | M2 | `survey_ts.md` / `review_ts.md` |
| F6 | TypeScript Runtime Exception Boundaries | Audit `ModelFusionLMProvider` process exit respawn (`startServer`), undeclared `ollamaModel` variable, Webview CSP & XSS | M2 | `survey_ts.md` / `review_ts.md` |
| F7 | Python Subprocess & Process Pool Safety | Audit subprocess timeout zombie leaks (`draco_evaluator.py`, `test_all_cli_flags.py`), `ProcessPoolExecutor` worker pool starvation | M3 | `survey_python.md` / `challenge_python.md` |
| F8 | Python Inference Output & Stdout Cleanliness | Audit stdout vs stderr stream segregation in `run_model_onnx.py`, CUDA OOM fallback handling in `run_model_transformers.py` | M3 | `survey_python.md` / `challenge_python.md` |
| F9 | Python Resource Leaks & Atomic Persistence | Audit Windows file lock collisions on temporary files, non-atomic JSON checkpoint writing in `database.py` and benchmark caches | M3 | `survey_python.md` / `challenge_python.md` |
| F10 | Comprehensive Safety Audit Synthesis & Report | Synthesize cross-domain findings, severity matrices, proof-of-concept tests, and actionable refactoring roadmap into structured report | M4 | `VERIFICATION_REPORT.md` |

---

## Milestones

| # | Milestone Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | Rust Core & Crates Safety Audit | Audit and verify memory safety, concurrency, TLS validation, and byte slicing across 9 Rust crates | None | **DONE** |
| M2 | TypeScript & IDE Extension Audit | Audit and verify Disposable lifecycle, non-blocking UI IPC streaming, and runtime exception safety | None | **DONE** |
| M3 | Python & AVO/Evolutionary Audit | Audit and verify subprocess lifecycle, worker pool starvation, stdout cleanliness, and atomic persistence | None | **DONE** |
| M4 | Comprehensive Verification Report | Synthesize verified findings across all domains into formal `VERIFICATION_REPORT.md` and report to parent | M1, M2, M3 | **DONE** |

---

## Code Layout & Boundaries

- **Rust Workspace**: `crates/utils/`, `crates/db/`, `crates/security/`, `crates/monitoring/`, `crates/task_detection/`, `crates/model_selection/`, `crates/analysis/`, `crates/core/`, `crates/cli/`
- **TypeScript IDE Extension**: `IDE/vscode/extensions/copilot/src/extension/dashboard/`, `IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/`
- **Python Systems**: `src/openevolve/`, `src/scripts/`, `canned_benchmark/`, `scratch/`, `tests/`
- **Metadata Workspace**: `.agents/orchestrator_2/`
- **Master Artifact**: `d:/harfile/ModelFusion/VERIFICATION_REPORT.md`
