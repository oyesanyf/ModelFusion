# E2E Test Infrastructure: ModelFusion & HugOS IDE Comprehensive 4-Tier Suite

## Test Philosophy & Methodology
- **Opaque-Box & Requirement-Driven**: Tests derive strictly from `PROJECT.md` (19 features across Rust Core, MCP Server, Model Selection Engine, Extension Host, and WiX MSI Packaging) and `ORIGINAL_REQUEST.md`.
- **4-Tier Test Architecture**:
  1. **Tier 1 (Feature Coverage)**: ≥5 test cases per feature covering the primary happy path and core functionality (19 features × 5 = 95 tests).
  2. **Tier 2 (Boundary & Corner Cases)**: ≥5 test cases per feature covering extreme inputs, empty inputs, max lengths, malformed payloads, zero/negative bounds, and edge cases (19 features × 5 = 95 tests).
  3. **Tier 3 (Cross-Feature Combinations)**: Pairwise combinatorial interactions between participant commands, slash routing, XML sanitization, MCP tools, anti-hype scoring, dynamic hardware profiling, adaptive timeouts, concurrency locks, chunked streaming, and WiX/Authenticode signing (20 tests).
  4. **Tier 4 (Real-World Application Scenarios)**: Realistic end-to-end multi-step application workflows (8 comprehensive scenarios).
- **Total Test Cases**: **218 tests** (100% deterministic, zero-flakiness, sub-second execution).

---

## 19-Feature Coverage Matrix

| # | Feature | Scope / Milestone | Tier 1 (Happy Path) | Tier 2 (Boundaries) | Tier 3 (Interactions) | Tier 4 (Workloads) | Total Tests |
|---|---------|:-----------------:|:-------------------:|:-------------------:|:---------------------:|:------------------:|:-----------:|
| F01 | Participant Commands & Directives | M1 / R1 | 5 tests (F01-01..05) | 5 tests (F01-B01..B05) | ✓ | ✓ | 12+ |
| F02 | Slash Command Router | M1 / R1 | 5 tests (F02-01..05) | 5 tests (F02-B01..B05) | ✓ | ✓ | 12+ |
| F03 | XML & User Request Sanitization | M1 / R1 | 5 tests (F03-01..05) | 5 tests (F03-B01..B05) | ✓ | ✓ | 12+ |
| F04 | OpenEvolve / AVO Integration | M1 / R1 | 5 tests (F04-01..05) | 5 tests (F04-B01..B05) | ✓ | ✓ | 12+ |
| F05 | Concurrency Locks & Permits | M1 / R1 | 5 tests (F05-01..05) | 5 tests (F05-B01..B05) | ✓ | ✓ | 12+ |
| F06 | Non-blocking Host Execution | M1 / R1 | 5 tests (F06-01..05) | 5 tests (F06-B01..B05) | ✓ | ✓ | 12+ |
| F07 | MCP 91-Tool Registration & Schemas | M2 / R2 | 5 tests (F07-01..05) | 5 tests (F07-B01..B05) | ✓ | ✓ | 12+ |
| F08 | MCP In-Process & Subcommand Handlers | M2 / R2 | 5 tests (F08-01..05) | 5 tests (F08-B01..B05) | ✓ | ✓ | 12+ |
| F09 | MCP `--ollama` Propagation | M2 / R2 | 5 tests (F09-01..05) | 5 tests (F09-B01..B05) | ✓ | ✓ | 12+ |
| F10 | MCP Automated Standalone Test Harness | M2 / R2 | 5 tests (F10-01..05) | 5 tests (F10-B01..B05) | ✓ | ✓ | 12+ |
| F11 | Dynamic Hardware Profiling | M3 / R3 | 5 tests (F11-01..05) | 5 tests (F11-B01..B05) | ✓ | ✓ | 12+ |
| F12 | Anti-Hype Model Scoring Engine | M3 / R3 | 5 tests (F12-01..05) | 5 tests (F12-B01..B05) | ✓ | ✓ | 12+ |
| F13 | Adaptive Token-Based Timeouts | M3 / R3 | 5 tests (F13-01..05) | 5 tests (F13-B01..B05) | ✓ | ✓ | 12+ |
| F14 | Non-Blocking IPC & Disconnect Detection | M3 / R3 | 5 tests (F14-01..05) | 5 tests (F14-B01..B05) | ✓ | ✓ | 12+ |
| F15 | WiX Manifest Generation | M4 / R4 | 5 tests (F15-01..05) | 5 tests (F15-B01..B05) | ✓ | ✓ | 12+ |
| F16 | Authenticode Protection & Binary Signing | M4 / R4 | 5 tests (F16-01..05) | 5 tests (F16-B01..B05) | ✓ | ✓ | 12+ |
| F17 | Dependency Bundling & MSI Generation | M4 / R4 | 5 tests (F17-01..05) | 5 tests (F17-B01..B05) | ✓ | ✓ | 12+ |
| F18 | Dual-Track E2E Test Suite (Tiers 1-4) | M-E2E | 5 tests (F18-01..05) | 5 tests (F18-B01..B05) | ✓ | ✓ | 12+ |
| F19 | Final E2E Test Pass & Adversarial Hardening | M-FINAL | 5 tests (F19-01..05) | 5 tests (F19-B01..B05) | ✓ | ✓ | 12+ |
| **Sum**| **All 19 Features** | **All Milestones** | **95 tests** | **95 tests** | **20 tests** | **8 tests** | **218 tests** |

---

## Test Directory Structure & Runners

```
ModelFusion/
├── tests/
│   └── e2e/
│       ├── __init__.py
│       ├── test_e2e_harness.py        # Python test harness & mock adapters
│       ├── test_tier1_features.py     # Tier 1 Python tests (95 tests)
│       ├── test_tier2_boundaries.py   # Tier 2 Python tests (95 tests)
│       ├── test_tier3_interactions.py # Tier 3 Python tests (20 tests)
│       ├── test_tier4_scenarios.py    # Tier 4 Python tests (8 scenarios)
│       ├── run_all_e2e.py             # Python master test runner
│       ├── test_e2e_harness.mjs       # Node.js ESM test harness
│       ├── tier1_features.test.mjs    # Tier 1 Node tests
│       ├── tier2_boundaries.test.mjs  # Tier 2 Node tests
│       ├── tier3_interactions.test.mjs# Tier 3 Node tests
│       ├── tier4_scenarios.test.mjs   # Tier 4 Node tests
│       ├── test_suite_all.mjs         # 218 test case declarations
│       ├── run_standalone_e2e.mjs     # Standalone in-process test runner
│       └── run_all_e2e.mjs            # Master Node ESM test runner
├── IDE/
│   ├── test_e2e_suite.py              # IDE proxy runner (Python)
│   ├── test_e2e_suite.mjs             # IDE proxy runner (Node.js)
│   └── vscode/extensions/copilot/test/e2e_all/
│       ├── testHarness.mjs            # Extension host test harness
│       ├── tier1_features.test.mjs    # Extension host Tier 1 tests
│       ├── tier2_boundaries.test.mjs  # Extension host Tier 2 tests
│       ├── tier3_interactions.test.mjs# Extension host Tier 3 tests
│       ├── tier4_scenarios.test.mjs   # Extension host Tier 4 tests
│       └── run_all_tests.mjs          # Native node --test master runner
```

---

## Execution Commands

### 1. Primary Node.js ESM Test Runner (Recommended)
```powershell
node D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\test\e2e_all\run_all_tests.mjs
```

### 2. Standalone In-Process Runner
```powershell
node D:\harfile\ModelFusion\tests\e2e\run_standalone_e2e.mjs
```

### 3. Python Test Runner
```powershell
python D:\harfile\ModelFusion\tests\e2e\run_all_e2e.py
```

### 4. Single-Tier Filtering
```powershell
node D:\harfile\ModelFusion\tests\e2e\run_standalone_e2e.mjs --tier 1
node D:\harfile\ModelFusion\tests\e2e\run_standalone_e2e.mjs --tier 2
node D:\harfile\ModelFusion\tests\e2e\run_standalone_e2e.mjs --tier 3
node D:\harfile\ModelFusion\tests\e2e\run_standalone_e2e.mjs --tier 4
```

---

## Real-World Workload Scenarios (Tier 4)

1. **SCENARIO-01: Complete Code Evolution Workflow**: User prompt `@agent /evolve`, hardware check (70% memory margin), multi-objective model selection, generation steps with monotonic fitness gain, candidate diff inspection, and atomic workspace patch application.
2. **SCENARIO-02: High-Concurrency Multi-Task Storm**: Simultaneous requests across fast-path `/stats`, MCP telemetry tools, and heavy inference requests. Verifies permit acquisition, fast-path lock bypass, and queue drainage.
3. **SCENARIO-03: Full MCP 91-Tool Automated Standalone Audit & Benchmarking**: Handshake initialization, schema compliance of all 91 tools, execution of categorized tools, and latency SLA compliance (<500ms).
4. **SCENARIO-04: Robust Network Interruption & Disconnect Auto-Abort**: HTTP chunked transfer with 5s keepalive heartbeats, abrupt client TCP RST disconnection, and automatic worker cancellation and permit release within 100ms.
5. **SCENARIO-05: End-to-End WiX MSI Installer Build, Signing & Verification**: Packaged directory scanning, XML manifest generation, Authenticode SHA256 code signing of `cli.exe` and `HugOS.msi`, and digital signature validation.
6. **SCENARIO-06: Complex Context Sanitization & Participant Delegation**: Deeply nested XML user request, fake command examples inside code blocks, `@agent @workspace` chained directives, and clean extraction and routing.
7. **SCENARIO-07: Dynamic Hardware-Constrained Model Selection & Adaptive Timeout Scaling**: Low-VRAM system probe, anti-hype scoring selecting quantized Ollama Q4 model, and exact formula-based token timeout calculation ($120 + \text{prompt}/40 + \text{tokens}/10$).
8. **SCENARIO-08: Extension Host Non-blocking Maintenance & Workspace Recovery**: Background cache clearing and file snapshotting while typing and thought streaming remain smooth at 60fps, with clean atomic rollback.
