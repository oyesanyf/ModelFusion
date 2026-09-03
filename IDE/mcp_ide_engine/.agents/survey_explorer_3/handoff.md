# Handoff Report: Resource Telemetry, Model Selector, Unified IDE & Benchmark Harness (R3, R4, R5)

**Agent:** Survey Explorer 3 (Resource & IDE Engine Architect)  
**Date:** 2026-09-02T16:16:30Z  
**Type:** Hard Handoff (Task Complete)

---

## 1. Observation

1. **Original Request Scope (`ORIGINAL_REQUEST.md`):**
   - Lines 18-20 (R3): *"Implement a real-time system resource monitor that probes available CPU threads, system RAM, and GPU/VRAM capacity. The engine must dynamically assess hardware limits and recommend or route inference and agent tasks to the optimal local model (or cloud fallback) based on real-time resource availability."*
   - Lines 21-23 (R4): *"Provide an interactive IDE interface (TUI and embedded web/API frontend) that exposes 100% of the CLI tools, command registry, MCP tool execution views, thread status monitors, and resource utilization metrics."*
   - Lines 24-26 (R5): *"Provide a complete automated test suite and benchmark suite validating end-to-end command execution, concurrent MCP tool invocation under load, resource metric accuracy, and error handling."*
   - Acceptance Criteria (Lines 32, 40-41, 44-45, 49): Concurrency stress test of 50+ simultaneous tasks with zero deadlocks; live CPU/RAM/GPU telemetry; model fit classification tiers; IDE parity with streaming output; < 5ms dispatch latency benchmarks.

2. **Completed Analysis Output (`analysis.md`):**
   - Created comprehensive 435-line architectural specification in `C:\Users\oyesanyf\.gemini\antigravity\scratch\mcp_ide_engine\.agents\survey_explorer_3\analysis.md`.
   - **R3 Architecture**: 5-tier cross-platform GPU detection chain (NVIDIA NVML $\rightarrow$ Windows DXGI $\rightarrow$ Apple Metal $\rightarrow$ Vulkan $\rightarrow$ sysinfo Host RAM), non-blocking background telemetry worker publishing via `tokio::sync::watch`, exact mathematical formulas for model weights, KV cache ($M_{\text{kv}}$), activation memory ($M_{\text{act}}$), 15% safety headroom margin, and dynamic layer offloading calculator.
   - **R4 Architecture**: Unified Command Bus (`CommandRegistry`, `TaskDispatcher`, `EventBus`) guaranteeing 100% tool parity; 5-tab Ratatui TUI with live sparklines, gauges, ANSI terminal log stream, and headless test mode; embedded Axum Web server providing REST endpoints, SSE telemetry feeds, and full-duplex WebSockets.
   - **R5 Architecture**: Criterion microbenchmark suite measuring task dispatch latency (< 5ms ceiling, < 50µs target) and JSON-RPC serialization; high-concurrency stress harness executing 50+ tasks simultaneously using `tokio::sync::Barrier` and timeout guards; 4-tier automated test framework (Unit, Subsystem, Concurrency/Stress, End-to-End Opaque-Box).
   - **Workspace Layout**: 8-crate modular workspace structure (`mcp-core`, `mcp-protocol`, `mcp-resource`, `mcp-tui`, `mcp-web`, `mcp-cli`, `mcp-bench`, `mcp-tests`).

---

## 2. Logic Chain

1. **Telemetry Non-Blocking Invariant (Obs 1, R3):** Telemetry queries must never block worker threads executing developer commands or MCP tool calls. Therefore, telemetry collection is isolated into an asynchronous background tick loop that updates an atomic `watch` channel snapshot in $O(1)$ read time without lock contention.
2. **Resilient Hardware Fallback (Obs 1, R3):** GPUs vary across user environments (NVIDIA CUDA, AMD ROCm/DirectX, Apple Silicon Unified Memory, or CPU-only VMs). A dynamic symbol loading approach for NVML ensures that non-NVIDIA systems smoothly cascade to DirectX DXGI, Metal, Vulkan, or host RAM without panics.
3. **Memory Sizing Accuracy (Obs 1, R3):** Large Language Models run out of memory not just from model weights, but from KV cache and activation buffers at large context sizes. Formulating explicit KV cache calculation ($M_{\text{kv}} = 2 \times N_{\text{layers}} \times N_{\text{kv\_heads}} \times D_{\text{head}} \times C_{\text{context}} \times B_{\text{elem}}$) with a 15% safety margin prevents Out-Of-Memory crashes and intelligently offloads layers or routes to cloud endpoints when local memory is saturated.
4. **100% Tool Parity Guarantee (Obs 1, R4):** To ensure identical behavior between CLI, TUI, and Web interfaces, all execution is routed through a centralized `CommandRegistry` and `TaskDispatcher`. CLI commands, TUI interactive panels, and Web REST/WebSocket endpoints share identical descriptors, JSON parameter schemas, and asynchronous event streams.
5. **Deadlock-Free Concurrency & Latency Ceiling (Obs 1, R5):** The 50+ concurrent task stress test validates thread pool safety by synchronizing task dispatch via `tokio::sync::Barrier` and asserting completion within bounded timeouts. Criterion benchmarks guarantee dispatch overhead remains well beneath the 5ms threshold.

---

## 3. Caveats

- **DirectX DXGI Compilation**: On Linux/macOS build hosts, the `windows` crate dependency for DXGI must be target-gated (`#[cfg(target_os = "windows")]`) to ensure clean cross-platform compilation.
- **TUI Headless Terminal Emulation**: In automated CI/headless environments without an interactive TTY, Ratatui tests should use `ratatui::backend::TestBackend` to verify widget rendering without opening raw terminal mode.
- **Embedded Web Asset Packaging**: In development mode, web assets can be served dynamically or embedded via `rust-embed`; in release mode, assets are compiled directly into the executable for single-binary portability.

---

## 4. Conclusion

The architectural investigation and specification for Requirements R3, R4, and R5 are complete, rigorous, and fully documented in `analysis.md`. The blueprints for the telemetry engine, dynamic model selector, unified TUI/Web IDE, Criterion benchmarks, and concurrency stress harness are ready for immediate synthesis by the orchestrator and implementation by the engineering teams.

---

## 5. Verification Method

1. **Inspect Analysis Specification:**
   ```powershell
   Get-Content "C:\Users\oyesanyf\.gemini\antigravity\scratch\mcp_ide_engine\.agents\survey_explorer_3\analysis.md"
   ```
2. **Verify Requirement Coverage:**
   - **R3**: Check Section 2 (Telemetry fallback chain, Rust data structures) and Section 3 (Model sizing formulas, fit tiers, layer offload calculator).
   - **R4**: Check Section 4 (Universal Command Bus, Ratatui TUI architecture, Axum REST/SSE/WebSocket routes).
   - **R5**: Check Section 5 (Criterion benchmarks, 50+ task concurrency stress test harness, 4-tier test framework).
   - **Workspace**: Check Section 6 for Cargo workspace crate breakdown and dependency matrix.
3. **Invalidation Conditions:**
   - If telemetry polling blocks worker threads on the async runtime.
   - If model selector omits KV cache or activation overhead in memory sizing.
   - If CLI commands and IDE tools diverge in schema or execution pathway.
