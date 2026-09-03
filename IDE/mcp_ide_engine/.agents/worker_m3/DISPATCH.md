## 2026-09-02T16:34:56Z
You are Worker M3 (Dynamic Resource Telemetry & Model Selector Engineer).
Working directory: C:\Users\oyesanyf\.gemini\antigravity\scratch\mcp_ide_engine\.agents\worker_m3

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your task:
1. Read ORIGINAL_REQUEST.md, PROJECT.md, and survey analysis at C:\Users\oyesanyf\.gemini\antigravity\scratch\mcp_ide_engine\.agents\survey_explorer_3\analysis.md.
2. You have EXCLUSIVE write ownership of:
   - C:\Users\oyesanyf\.gemini\antigravity\scratch\mcp_ide_engine\crates\mcp-resource\**
3. Implement `crates/mcp-resource`:
   - `crates/mcp-resource/Cargo.toml` with dependencies: `mcp-core` (path), `sysinfo`, `tokio` (full), `serde`, `serde_json`, `async-trait`, `thiserror`, `tracing`, `parking_lot`, `futures`, `tokio-util`.
   - `crates/mcp-resource/src/lib.rs`: exports and `ResourceError`.
   - `crates/mcp-resource/src/gpu.rs`: cross-platform GPU detection chain (NVML dynamic loading / DXGI / sysinfo fallback), returning GPU name, driver version, VRAM total, VRAM used, VRAM free, and compute features.
   - `crates/mcp-resource/src/telemetry.rs`: `ResourceMonitor` with background async tick loop updating `tokio::sync::watch::Sender<SystemSnapshot>`, recording CPU core loads, system RAM, VRAM, and process stats without blocking runtime threads.
   - `crates/mcp-resource/src/sizing.rs`: exact model memory formulas:
     * Model weight memory ($M_{\text{weights}} = \text{parameters} \times \text{bytes\_per\_weight}$)
     * KV Cache memory ($M_{\text{kv}} = 2 \times N_{\text{layers}} \times N_{\text{kv\_heads}} \times D_{\text{head}} \times C_{\text{context}} \times B_{\text{elem}}$)
     * Activation memory ($M_{\text{act}} = B_{\text{batch}} \times C_{\text{context}} \times D_{\text{model}} \times \text{layers} \times \text{overhead}$)
     * Total required memory with configurable 15% safety headroom margin.
   - `crates/mcp-resource/src/selector.rs`: `ModelSelector` dynamic tier classifier (Small: 1B-3B / 2-4GB, Medium: 7B-8B / 6-12GB, Large: 14B-70B / 16-48GB, Cloud fallback), and GPU layer offloader (`calculate_layer_offload(model_spec, available_vram)`).
   - Comprehensive unit and integration tests in `crates/mcp-resource/tests/` testing live telemetry polling, mathematical model sizing, layer offloading calculations, and dynamic routing under synthetic memory pressure.
4. Run `cargo build` and `cargo test -p mcp-resource` ensuring 100% pass without warnings or errors.
5. Write your detailed handoff report to C:\Users\oyesanyf\.gemini\antigravity\scratch\mcp_ide_engine\.agents\worker_m3\handoff.md and notify the parent orchestrator via send_message when complete.
