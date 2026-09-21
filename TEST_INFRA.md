# ModelFusion & HugOS IDE Next-Generation Autonomous Test Infrastructure

## Overview

This document outlines the test architecture, methodology, execution procedures, and verification criteria for the next-generation autonomous developer operating system capabilities (R1–R5) implemented across ModelFusion Master CLI and HugOS IDE:

1. **R1: Real-Time Self-Healing LSP Diagnostic Auto-Patcher ("Continuous Code Repair")**
2. **R2: Speculative Ensemble Ghost Text (120+ Tok/s Local Autocomplete)**
3. **R3: Semantic Codebase Knowledge Graph (`code_graph.db`)**
4. **R4: Native Multi-Modal Visual Canvas & UI Synthesis**
5. **R5: Distributed Local AI Mesh (mDNS & mTLS Compute Offloading)**

---

## 1. Test Architecture & 4-Tier Taxonomy

The test suite employs a strict, opaque-box, category-partition methodology divided into 4 complementary tiers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        COMPREHENSIVE TEST SUITE                        │
├────────────────────────────────┬───────────────────────────────────────┤
│ Tier 1: Feature Coverage       │ Happy-path requirement verification   │
│ (45 Tests: R1-F01 to R5-F45)   │ Core functional contracts for R1–R5   │
├────────────────────────────────┼───────────────────────────────────────┤
│ Tier 2: Boundary & Corner      │ Stress testing, vacuous test defense, │
│ (45 Tests: R1-B01 to R5-B45)   │ SLAs, timeouts, preemption, invalid   │
├────────────────────────────────┼───────────────────────────────────────┤
│ Tier 3: Pairwise Interactions  │ Inter-capability cross-dependencies   │
│ (20 Tests: INT-01 to INT-20)   │ Concurrency, pipeline handoffs, state │
├────────────────────────────────┼───────────────────────────────────────┤
│ Tier 4: Real-World Scenarios   │ End-to-end user workflows, lifecycle, │
│ (10 Tests: SCENARIO-01 to 10)  │ Resilience, full-stack loop           │
└────────────────────────────────┴───────────────────────────────────────┘
```

Total: **120 Tests** (100% Deterministic, Opaque-Box, Zero-Flake).

---

## 2. Capability Matrix & Verification Contracts

### R1: Real-Time Self-Healing LSP Diagnostic Auto-Patcher
- **Ingestion & Debounce**: Ingests `vscode.languages.onDidChangeDiagnostics` via JSON-RPC `diagnostics/report`. Only errors (`DiagnosticSeverity.Error`) trigger repairs. Debounce window of 750ms ensures active typing is never interrupted.
- **Background Synthesis**: Runs at `IDLE_PRIORITY_CLASS` with compiler oracles (`py_compile`, `tsc`, `cargo check`).
- **AST Mutation Testing Certification Gate**: $K=5$ AST mutants (ROR, AOR, LOR, SDL, RVR). A patch is certified ONLY when $M_{kill} \ge 0.50 \implies R=1.00$. Vacuous test suites where $M_{kill} = 0.00$ are strictly rejected with $R=0.00$.
- **4-Tier Graduated Reward Evaluator**: Dense scoring formula:
  $$R(c) = 0.15 S_{ast} + 0.25 S_{diag} + 0.25 S_{reg} + 0.35 S_{test}$$
  Hard security gate: forbidden imports/calls (`os.system`, `subprocess.Popen`, `eval`) yield $S_{ast} = 0 \implies R=0$.
- **In-Editor CodeLens & QuickFix**: Surfaces `[🤖 Verified Fix Available (Score: 1.00) — Review Virtual Diff]` and `🤖 Apply Verified Fix (Score: 1.00)` CodeAction.
- **In-Memory Virtual Diff**: `restrl-diff://candidate/...` diff provider and atomic `vscode.workspace.applyEdit` without creating temporary files on disk.

### R2: Speculative Ensemble Ghost Text (120+ Tok/s Local Autocomplete)
- **Latency SLA Budget**: $\le 150\text{ ms}$ total from typing pause:
  - 40ms: Typing pause debounce
  - 75ms: Speculative token drafting (0.5B model >120 tok/s)
  - 20ms: AST syntax integrity verification
  - 15ms: VS Code editor rendering
- **Fill-in-the-Middle (FIM)**: Standardized `<|fim_prefix|>${prefix}<|fim_suffix|>${suffix}<|fim_middle|>` prompt formatting.
- **AST Syntax Integrity Check**: Verifies completion candidates using Tree-Sitter grammars. Syntactically invalid tokens (unclosed brackets, illegal keywords) are dropped.
- **Instant Preemption**: Cancels drafting within $<25\text{ ms}$ when user resumes typing (`token.isCancellationRequested`).

### R3: Semantic Codebase Knowledge Graph (`code_graph.db`)
- **Multi-Language Tree-Sitter Extraction**: Extracts symbol definitions, calls, implementations, and references across Rust, TypeScript, and Python.
- **SQLite Storage & Schema**: `files`, `symbols`, `calls`, `implementations`, `symbol_references`, and FTS5 virtual table `symbols_fts`. Configured with WAL mode and B-Tree indexes.
- **Sub-25ms Query Engine**:
  - Single symbol definition lookup: $<1.0\text{ ms}$
  - Recursive CTE 3-hop call hierarchy traversal: $<5.0\text{ ms}$
  - FTS5 + TermVector hybrid search: $<10.0\text{ ms}$
- **Structural Context Injection**: `injectStructuralContext(prompt, activeFile, activeSymbol)` enriches chat prompts for `@agent` and `/orchestrate`.

### R4: Native Multi-Modal Visual Canvas & UI Synthesis
- **Webview Dropzone & Clipboard**: Accepts `.png`, `.jpg`, `.jpeg`, `.webp`, `.svg`, and clipboard paste (`Win+Shift+S`). Rejects non-image files.
- **Base64 Encoding**: `FileReader.readAsDataURL` $\rightarrow$ `{ type: 'attachVisualAsset', asset: { id, filename, mimeType, base64Data, width, height } }`.
- **Local VLM Routing**: Routes image attachments to local OpenVINO Qwen2-VL or Ollama `qwen2-vl` via `/api/chat` with `images: [base64]`. Zero external cloud leakage.
- **Visual Workflows**:
  - Component Synthesis: Mockup/wireframe screenshot $\rightarrow$ React JSX + Tailwind CSS code.
  - Layout Bug Diagnosis: Layout screenshot $\rightarrow$ CSS box model & flexbox/grid misalignment diagnosis + patch.

### R5: Distributed Local AI Mesh (mDNS & mTLS)
- **mDNS Discovery**: P2P advertisement on `_hugos-mesh._tcp.local.` with TXT records (`node_id`, `hostname`, `free_ram_gb`, `gpu_name`, `free_vram_mb`, `capabilities`).
- **Encrypted mTLS**: Mutual TLS 1.3 authentication using self-signed cluster certificates (`CN=<node_id>.hugos.local`). SHA-256 fingerprint verified against mDNS advertisement.
- **Hardware Sizing & Offloading**:
  - Available RAM $\ge 24\text{ GB}$ or Free VRAM $\ge 14\text{ GB} \implies$ local execution of 32B model / ReST-RL sweep.
  - Lightweight nodes (e.g. laptops with 8 GB RAM) offload heavy 32B model arbitration and ReST-RL sweeps to LAN workstation peers.
  - Resilient fallback: If no LAN peer satisfies capacity requirements, falls back to local degraded model (1.5B) without error.

---

## 3. How to Run the Tests

### Command Line Execution
```powershell
# Run the complete test suite (All 120 tests across 4 tiers)
& "D:\tools\nodejs\node.exe" tests/e2e/test_nextgen_autonomous.mjs

# Run with quiet mode (summary only)
& "D:\tools\nodejs\node.exe" tests/e2e/test_nextgen_autonomous.mjs --quiet

# Run in JSON machine-readable mode
& "D:\tools\nodejs\node.exe" tests/e2e/test_nextgen_autonomous.mjs --json

# Run specific tier only
& "D:\tools\nodejs\node.exe" tests/e2e/test_nextgen_autonomous.mjs --tier 1
& "D:\tools\nodejs\node.exe" tests/e2e/test_nextgen_autonomous.mjs --tier 2
& "D:\tools\nodejs\node.exe" tests/e2e/test_nextgen_autonomous.mjs --tier 3
& "D:\tools\nodejs\node.exe" tests/e2e/test_nextgen_autonomous.mjs --tier 4
```

---

## 4. Expected Output Derivation & Verification Oracles

| Capability | Test Input | Authoritative Oracle | Verification Method |
|---|---|---|---|
| R1 Auto-Patcher | Rust/TS/Python compiler error diagnostics | Compiler oracles (`cargo check`, `tsc`, `py_compile`), `GraduatedRewardEvaluator`, `AdversarialCertificationGate` | Reward must equal 1.00, $M_{kill} \ge 0.50$, CodeLens title matches pattern, `restrl-diff://` content matches candidate, no temp disk files. |
| R2 Ghost Text | Document prefix/suffix and cursor position | FIM grammar specification, INT4 0.5B token generation, Tree-Sitter syntax parser | Latency $\le 150\text{ ms}$, syntax errors dropped, cancellation $<25\text{ ms}$, indentation preserved. |
| R3 Knowledge Graph | Multi-language source code | Tree-Sitter AST grammars, SQLite B-Tree index & FTS5 virtual table | Response time $<25\text{ ms}$, single-symbol $<1\text{ ms}$, call hierarchy $<5\text{ ms}$, schema integrity verified. |
| R4 Visual Canvas | PNG/JPEG/WEBP/SVG image buffers | Base64 MIME spec, local VLM chat API contract (`openvino_genai` / Ollama) | Valid Base64 data URL, thumbnail chip emitted, React/Tailwind code or CSS patch synthesized. |
| R5 Local AI Mesh | Node telemetry and arbitration request | RFC 6762 (mDNS), TLS 1.3 mTLS handshake, `FusionArbiter` dynamic sizing matrix | Valid TXT records, cert fingerprint match, 32B offloaded to workstation with fallback. |

---

## 5. Adversarial Verification Gates

1. **Vacuous Test Suite Defense**: A candidate patch tested against unit tests with zero assertion sensitivity (e.g. `assert True`) will have all mutants survive ($M_{kill} = 0.00$). The certification gate detects this and rejects the patch with $R=0.00$.
2. **Security Sandbox Escape Barrier**: Any candidate attempting code injection, command execution (`os.system`, `eval`, `subprocess.Popen`), or memory tampering triggers an immediate AST security block ($S_{ast} = 0 \implies R=0$).
3. **Sub-25ms Preemption Under Stress**: Typing interrupts streaming token drafting in $<25\text{ ms}$, with zero orphaned child processes or leaked socket descriptors.
4. **Resilient LAN Partition Handling**: When a remote mesh node disconnects or drops packets mid-arbitration, `FusionArbiter` catches socket errors within timeout and transparently falls back to local degraded models.
