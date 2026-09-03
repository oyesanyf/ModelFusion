# E2E Test Infra: High-Performance MCP CLI & IDE Engine

## Test Philosophy
- **Opaque-Box & Requirement-Driven**: Tests are derived strictly from `ORIGINAL_REQUEST.md` requirements and public interface contracts, treating the engine as an opaque box.
- **Progressive Testability**: Verification mechanisms do not require features more complex than what they test. Tier 1 tests provide pass/fail signals early.
- **Robustness & Error Isolation**: Negative tests verify graceful error handling, JSON-RPC error codes, and tool isolation without host crashes.

---

## Feature Inventory & Test Mapping

| # | Feature | Requirement Source | Tier 1 (Coverage) | Tier 2 (Boundaries) | Tier 3 (Interactions) |
|---|---------|-------------------|:-----------------:|:-------------------:|:---------------------:|
| 1 | Async Multithreaded Runtime | R1.1, AC Core | 5 | 5 | ✓ |
| 2 | Rayon Work-Stealing Pool | R1.1, AC Core | 5 | 5 | ✓ |
| 3 | 5-Level Priority Queue | R1.1, AC Core | 5 | 5 | ✓ |
| 4 | Non-Blocking Task Dispatch | R1.1, AC Latency | 5 | 5 | ✓ |
| 5 | Lock-Free Registry & DashMap | R1.1, AC Core | 5 | 5 | ✓ |
| 6 | Cooperative Cancellation Token | R1.1, AC Core | 5 | 5 | ✓ |
| 7 | Task Execution Telemetry | R1.1, R5, AC Quality | 5 | 5 | ✓ |
| 8 | JSON-RPC 2.0 Framing & Codes | R2.1, AC MCP | 5 | 5 | ✓ |
| 9 | Stdio MCP Transport | R2.1, AC MCP | 5 | 5 | ✓ |
| 10 | HTTP / SSE MCP Transport | R2.1, AC MCP | 5 | 5 | ✓ |
| 11 | Protocol Handshake & Lifecycle | R2.1, AC MCP | 5 | 5 | ✓ |
| 12 | MCP Tool Registration & Call | R2.1, AC MCP | 5 | 5 | ✓ |
| 13 | MCP Resource Catalog & Read | R2.1, AC MCP | 5 | 5 | ✓ |
| 14 | MCP Prompt Management | R2.1, AC MCP | 5 | 5 | ✓ |
| 15 | MCP Client Supervision | R2.1, AC MCP | 5 | 5 | ✓ |
| 16 | MCP Server Subsystem | R2.1, AC MCP | 5 | 5 | ✓ |
| 17 | Tool Failure Isolation (isError) | R2.1, AC MCP | 5 | 5 | ✓ |
| 18 | Host CPU & RAM Telemetry | R3.1, AC Resource | 5 | 5 | ✓ |
| 19 | GPU Detection & Fallback Chain | R3.1, AC Resource | 5 | 5 | ✓ |
| 20 | Live VRAM / RAM Tracking | R3.1, AC Resource | 5 | 5 | ✓ |
| 21 | Model Memory Sizing Formulas | R3.1, AC Resource | 5 | 5 | ✓ |
| 22 | Dynamic Model Fit Classifier | R3.1, AC Resource | 5 | 5 | ✓ |
| 23 | GPU Layer Offload Calculator | R3.1, AC Resource | 5 | 5 | ✓ |
| 24 | Ratatui 5-Tab TUI Interface | R4.1, AC IDE | 5 | 5 | ✓ |
| 25 | Axum Web API & Dashboard | R4.1, AC IDE | 5 | 5 | ✓ |
| 26 | Universal Tool Parity | R4.1, AC IDE | 5 | 5 | ✓ |
| 27 | Clap CLI Subcommands | R1.1, R4.1, AC Core | 5 | 5 | ✓ |
| 28 | Interactive Reedline REPL | R4.1, AC IDE | 5 | 5 | ✓ |

---

## Test Architecture

### 1. Test Harness Runner
- Invocation: `cargo test --workspace --all-targets`
- Stress Concurrency: `cargo test -p mcp-tests --test concurrency_stress -- --nocapture`
- Benchmarks: `cargo bench -p mcp-bench`
- Pass/Fail Semantics: Strict exit code 0, 0 test failures, 0 unresolved warnings.

### 2. Test Directory Layout
- `crates/mcp-tests/tests/tier1_features.rs`: Feature Coverage tests.
- `crates/mcp-tests/tests/tier2_boundaries.rs`: Boundary, corner case, and negative tests.
- `crates/mcp-tests/tests/tier3_combinations.rs`: Pairwise combinatorial feature interactions.
- `crates/mcp-tests/tests/tier4_scenarios.rs`: Real-world end-to-end workload simulations.
- `crates/mcp-tests/tests/concurrency_stress.rs`: 50+ concurrent tasks stress harness.

---

## Real-World Application Scenarios (Tier 4)

| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | **Multi-Model Local vs Cloud Routing**: Real-time RAM/VRAM pressure triggers dynamic layer offloading and auto-routing between Small (3B), Medium (8B), Large (70B), and Cloud fallback. | F18, F19, F20, F21, F22, F23 | High |
| 2 | **Parallel MCP Tool Orchestration Pipeline**: 10 external MCP tools spawned simultaneously over stdio and SSE, streaming responses with isolated failure containment. | F8, F9, F10, F11, F12, F15, F17 | High |
| 3 | **Interactive IDE Live Workspace Session**: TUI and Web server simultaneously connected to the engine, monitoring 50 active tasks, inspecting MCP catalogs, and streaming live logs. | F1, F3, F4, F7, F24, F25, F26 | High |
| 4 | **High-Throughput Code Analysis Burst**: CLI running heavy CPU code analysis on Rayon compute pool while handling incoming MCP tool calls on Tokio async reactor without latency degradation. | F1, F2, F4, F5, F7, F27 | High |
| 5 | **Cancellation & Graceful Teardown under Load**: In-flight long-running MCP tool executions and compute jobs cancelled via cooperative `CancellationToken` without thread leak or orphaned child processes. | F1, F6, F12, F15, F17 | High |
| 6 | **Resource Exhaustion & Graceful Recovery**: Simulating near-100% memory consumption and verifying that the engine rejects/queues jobs safely and selects fallback models without crashing. | F3, F18, F20, F22, F23 | High |

---

## Coverage Thresholds

- **Tier 1 (Feature Coverage)**: $\ge 5 \times 28 = 140$ test cases
- **Tier 2 (Boundary & Corner Cases)**: $\ge 5 \times 28 = 140$ test cases
- **Tier 3 (Cross-Feature Combinations)**: $\ge 28$ pairwise interaction tests
- **Tier 4 (Real-World Application Scenarios)**: $\ge 6$ comprehensive end-to-end workload tests
- **Total Minimum Target**: $> 314$ automated test assertions
