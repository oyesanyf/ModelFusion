# Project: Next-Generation Autonomous Capabilities for HugOS IDE & ModelFusion Master CLI

## Architecture & System Overview
ModelFusion and HugOS IDE form a proactive, self-healing, multi-modal developer operating system:
1. **ModelFusion Master CLI & Rust Workspace (`crates/`)**:
   - `crates/cli`: Command dispatch, HTTP API server (:5000), MCP JSON-RPC, `FusionArbiter` multi-model consensus, and mesh offloading.
   - `crates/core`: Task orchestration, multi-modal model catalog integration, and pipeline execution.
   - `crates/code_graph`: Tree-Sitter multi-language AST extraction (Rust, TypeScript, Python), SQLite database (`code_graph.db`), FTS5 virtual table, and sub-25ms structural symbol queries.
   - `crates/mesh`: P2P mDNS discovery (`_hugos-mesh._tcp.local.`) and encrypted mTLS transport for LAN compute offloading.
2. **HugOS IDE Extension & TypeScript Layer (`IDE/vscode/extensions/copilot/`, `IDE/src/`)**:
   - `ide_client_shim.ts`: Event-driven background watcher on `vscode.languages.onDidChangeDiagnostics`, Win32 Named Pipe / TCP IPC, virtual document diff provider (`restrl-diff://`), and verified fix CodeLens / QuickFix.
   - `speculativeGhostText.ts`: `vscode.InlineCompletionItemProvider` implementing 120+ tok/s speculative ghost text within a 150ms latency budget.
   - `visualCanvas.ts` & Webview: Multi-modal drag-and-drop and clipboard paste canvas routing to local VLMs for UI synthesis and visual layout diagnosis.
   - `codeGraphService.ts`: Symbol hierarchy context extraction for `@agent` and `/orchestrate`.
3. **Python ReST-RL & AI Engine (`IDE/rest_rl/`, `IDE/ov_models/`)**:
   - Sub-50ms preemption architecture: Win32 Job Objects (`_kernel32.TerminateJobObject`) for <8ms cancellation and streaming socket preemption for <25ms token abortion.
   - Adversarial AST Mutation Certification Gate ($K=5$ mutants, $M_{kill} \ge 0.50 \implies R=1.00$).
   - 4-Tier Graduated Dense Verification Signal ($R(c) = 0.15 S_{ast} + 0.25 S_{diag} + 0.25 S_{reg} + 0.35 S_{test}$).
   - Speculative draft model serving: OpenVINO INT4 `OpenVINO_Qwen2.5-Coder-0.5B-Instruct-int4-ov` (>120 tok/s).
   - Multi-modal local VLM serving: OpenVINO `OpenVINO_Qwen2-VL-7B-Instruct-int4-ov` and Ollama `qwen2-vl`.

---

## Feature Inventory

| # | Feature | Scope & Description | Milestone | Source |
|---|---|---|---|---|
| F1 | Real-Time LSP Diagnostic Watcher | Event-driven background watcher on `vscode.languages.onDidChangeDiagnostics` with 750ms debounce | M1 | ORIGINAL_REQUEST §R1 |
| F2 | Autonomous Candidate Patch Synthesis | Non-blocking background repair synthesis using compiler oracles (`cargo check`, `tsc`, `py_compile`) | M1 | ORIGINAL_REQUEST §R1 |
| F3 | AST Mutation Certification & $R=1.00$ Gate | $K=5$ AST mutants; $M_{kill} \ge 0.50 \implies R=1.00$; vacuous test suites rejected | M1 | ORIGINAL_REQUEST §R1 |
| F4 | In-Editor CodeLens & QuickFix Actions | Surfaces `[🤖 Verified Fix Available (Score: 1.00) — Review Virtual Diff]` and QuickFix atomically | M1 | ORIGINAL_REQUEST §R1 |
| F5 | In-Memory Virtual Document Diffs | `restrl-diff://` virtual document diffing and atomic `vscode.workspace.applyEdit` without disk temp files | M1 | ORIGINAL_REQUEST §R1 |
| F6 | Speculative Inline Completion Provider | `vscode.languages.registerInlineCompletionItemProvider` responding within 150ms of typing pause | M2 | ORIGINAL_REQUEST §R2 |
| F7 | 0.5B Draft Model Speculative Pipeline | Speculative drafting via local 0.5B model (`qwen2.5-coder:0.5b` via OpenVINO CPU/NPU or Ollama) >120 tok/s | M2 | ORIGINAL_REQUEST §R2 |
| F8 | Background AST Integrity Verification | Fast incremental AST syntax validation via bundled Tree-Sitter WASM grammars in <20ms | M2 | ORIGINAL_REQUEST §R2 |
| F9 | Tree-Sitter Multi-Language Symbol Extractor | Rust AST parsing for Rust, TypeScript/JS, and Python extracting definitions, calls, impls, and refs | M3 | ORIGINAL_REQUEST §R3 |
| F10 | Semantic Knowledge Graph SQLite Schema | `code_graph.db` schema (`files`, `symbols`, `calls`, `implementations`, `symbol_references`, `symbols_fts`) | M3 | ORIGINAL_REQUEST §R3 |
| F11 | Sub-25ms Graph Query CLI & HTTP API | Prepared statements and recursive CTEs delivering call hierarchy and symbol lookups in <25ms | M3 | ORIGINAL_REQUEST §R3 |
| F12 | Structural Context Injection for `@agent` | Inject call hierarchy and symbol signatures into `@agent` and `/orchestrate` chat prompts | M3 | ORIGINAL_REQUEST §R3 |
| F13 | Chat Webview Visual Dropzone & Clipboard | Drag-and-drop and clipboard paste (`Win+Shift+S`) image dropzone with Base64 encoding | M4 | ORIGINAL_REQUEST §R4 |
| F14 | Local Vision Model Pipeline | Local VLM inference (`qwen2-vl` / `Florence-2`) via OpenVINO GenAI or Ollama `/api/chat` | M4 | ORIGINAL_REQUEST §R4 |
| F15 | Frontend Component & Layout Synthesis | Automatic synthesis of Tailwind/React components and diagnosis of visual CSS layout bugs | M4 | ORIGINAL_REQUEST §R4 |
| F16 | Peer-to-Peer mDNS Discovery Protocol | DNS-SD `_hugos-mesh._tcp.local.` advertising host, free RAM, GPU, free VRAM, and capabilities | M5 | ORIGINAL_REQUEST §R5 |
| F17 | Encrypted Local mTLS Transport | Mutual TLS using self-signed cluster certificates (`rcgen` / `rustls`) over LAN | M5 | ORIGINAL_REQUEST §R5 |
| F18 | Distributed Workload Offloading | Routing 32B model arbitration and ReST-RL compute sweeps from laptops to LAN GPU workstations | M5 | ORIGINAL_REQUEST §R5 |
| F19 | 4-Way Cryptographic Binary Parity | 100% SHA-256 and byte parity across all 4 `cli.exe` locations verified via `sync_cli_parity.py` | M6 | Persistent Rules |
| F20 | WiX v5 MSI Build & Authenticode Signing | Compile `HugOS.msi` with incremented build number, signed via `hugos-signing-cert.pfx` | M6 | Persistent Rules |
| F21 | Comprehensive E2E Test Suite | Automated end-to-end verification of all R1–R5 capabilities with 100% pass rate | M6 | ORIGINAL_REQUEST |

---

## Milestones

| # | Milestone Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | Real-Time Self-Healing LSP Diagnostic Auto-Patcher | F1, F2, F3, F4, F5: `onDidChangeDiagnostics`, ReST-RL daemon repair task, AST mutation gate ($M_{kill}\ge 0.5 \implies R=1.00$), CodeLens/QuickFix, `restrl-diff://` | None | **DONE** (`run_all_tests.py` 59/59, mutation gate certified) |
| M2 | Speculative Ensemble Ghost Text (120+ Tok/s) | F6, F7, F8: InlineCompletionItemProvider, 0.5B draft model FIM prompt, WASM tree-sitter AST validation, <150ms response SLA | None | **DONE** (`test_ast_validator_flaws.mjs` 3/3, 0.0127ms preemption) |
| M3 | Semantic Codebase Knowledge Graph (`code_graph.db`) | F9, F10, F11, F12: Tree-Sitter AST parser in Rust, `code_graph.db` SQLite schema & FTS5, sub-25ms CLI queries, `@agent` context injection | None | **DONE** (`cargo test --workspace` 71 passed, 0 panics) |
| M4 | Native Multi-Modal Visual Canvas & UI Synthesis | F13, F14, F15: Webview drag-and-drop & clipboard dropzone, Base64 transmission, local VLM inference (`qwen2-vl`), component/layout synthesis | None | **DONE** (`run_model_visual.py` process dispatch verified) |
| M5 | Distributed Local AI Mesh (mDNS & mTLS) | F16, F17, F18: mDNS peer discovery (`_hugos-mesh._tcp.local.`), mTLS encryption (`rustls`/`rcgen`), `FusionArbiter` 32B/ReST-RL LAN offloading | None | **DONE** (`cargo test -p mesh` 5/5 passed with client cert & pinning) |
| M6 | Packaging, 4-Way Parity & E2E Validation | F19, F20, F21: Release CLI build, 4-way parity sync, WiX v5 MSI compilation, Authenticode signing, and comprehensive E2E test pass | M1–M5 | **DONE** (`verify_msi_contents.py` 42/42, parity 100%, E2E 120/120) |


---

## Interface Contracts

### 1. LSP Auto-Patcher: Extension ↔ ReST-RL Daemon
- Protocol: Windows Named Pipe `\\.\pipe\hugos_rest_rl_ipc` / TCP `127.0.0.1:45454`
- Ingestion RPC: `diagnostics/report`
  ```json
  { "jsonrpc": "2.0", "method": "diagnostics/report", "params": { "file_path": "...", "code": "...", "diagnostics": [...] }, "id": 1 }
  ```
- Resolution RPC: `agent/poll_resolutions`
  ```json
  { "file_path": "...", "passed": true, "reward": 1.0, "candidate_code": "...", "diff": "...", "mutation_certified": true }
  ```
- CodeLens: `[🤖 Verified Fix Available (Score: 1.00) — Review Virtual Diff]` -> opens `restrl-diff://candidate/<file>?taskId=<id>`.
- QuickFix: `🤖 Apply Verified Fix (Score: 1.00)` -> executes `vscode.workspace.applyEdit`.

### 2. Speculative Ghost Text: Extension ↔ Draft Pipeline
- Latency SLA: $\le 150\text{ ms}$ from typing pause.
- Debounce: 40ms; Drafting: 75ms; AST verification: 20ms; Rendering: 15ms.
- FIM Format: `<|fim_prefix|>${prefix}<|fim_suffix|>${suffix}<|fim_middle|>`
- Validation: Tree-Sitter WASM syntax check. If parse errors are introduced, drop candidate.

### 3. Knowledge Graph: Master CLI ↔ Extension
- Database: `IDE/db/code_graph.db`
- Index Command: `cli.exe --graph-index [--workspace <DIR>]`
- Query Command: `cli.exe --graph-query "<SYMBOL>" [--workspace <DIR>] [--type <all|calls|callees|impls|refs>]`
- Latency SLA: $\le 25\text{ ms}$ response time via prepared SQLite queries.

### 4. Visual Canvas: Webview ↔ ModelFusion VLM
- Webview Event: `dragover`/`drop` and `paste` -> `FileReader.readAsDataURL` -> `{ type: 'attachVisualAsset', asset: { id, filename, mimeType, base64Data } }`.
- Inference: Ollama `/api/chat` (`images: [base64]`) or Master CLI `--task visual-question-answering`.

### 5. Distributed Mesh: Local Node ↔ Remote GPU Node
- Discovery: mDNS service `_hugos-mesh._tcp.local.` / `_modelfusion._tcp.local.`.
- Transport: TLS 1.3 mutual authentication (mTLS) on port `5055`.
- Arbitration RPC: `POST /mesh/tasks/arbitrate` passing `CandidateSolution` array; returns consensus synthesized code from 32B model.

---

## Code Layout & Boundaries

- **Rust Workspace**: `crates/cli/`, `crates/core/`, `crates/code_graph/`, `crates/mesh/`, `crates/db/`
- **TypeScript IDE Extension**: `IDE/rest_rl/ide_client_shim.ts`, `IDE/src/autocomplete/`, `IDE/src/visual/`, `IDE/src/graph/`, `IDE/vscode/extensions/copilot/`
- **Python ReST-RL & AI Engine**: `IDE/rest_rl/`, `IDE/ov_models/`
- **Packaging Scripts**: `IDE/build_msi.ps1`, `IDE/sync_cli_parity.py`, `IDE/generate_wix.js`, `IDE/verify_msi_contents.py`
- **Metadata Workspace**: `.agents/orchestrator_3/`
