# Handoff Report: Integration Test Suite & Harness Investigation

**Agent**: survey_explorer_gen3_3  
**Role**: Teamwork Explorer (Read-Only Investigation)  
**Date**: 2026-09-03  
**Working Directory**: `C:\Users\oyesanyf\.gemini\antigravity\scratch\mcp_ide_engine\.agents\survey_explorer_gen3_3`  
**Handoff Type**: Hard (Investigation Complete)

---

## 1. Observation

### Obs 1: Existing Test Suite State in `crates/mcp-tests`
- File `crates/mcp-tests/src/lib.rs` defines `TestHarness` lines 15-24:
  ```rust
  pub struct TestHarness {
      pub runtime: Arc<EngineRuntime>,
      pub telemetry: Arc<EngineTelemetry>,
      pub scheduler: Arc<MultiLaneScheduler>,
      pub registry: Arc<CommandRegistry>,
      pub dispatcher: Arc<TaskDispatcher>,
      pub resource_monitor: Arc<ResourceMonitor>,
      pub mcp_server: Arc<McpServer>,
      pub web_state: AppState,
  }
  ```
- Lines 113-128 register a synthetic tool named `"tool_add"`:
  ```rust
  server.tools().register_fn("tool_add", Some("Adds numbers".to_string()), ...
  ```
  It does **not** register the 8 developer `@agent` tools (`write_code_file`, `read_code_file`, `list_directory`, `execute_cli_command`, `get_telemetry`, `recommend_best_model`, `calculate_layer_offload`, `run_command`).
- Existing test files in `crates/mcp-tests/tests/` (`concurrency_stress.rs`, `tier1_features.rs`, `tier2_boundaries.rs`, `tier3_combinations.rs`, `tier4_scenarios.rs`, `tier5_adversarial.rs`) run in-memory; none spawn `mcp-cli` as an external child process or test stdio pipes.
- Running `cargo test -p mcp-tests` failed with 161 compilation errors in `tier1_features.rs` and 177 in `tier2_boundaries.rs` due to API drift (e.g. `calculate_layer_offload` scope, `ModelSpec::llama_3_8b_instruct_q4`, `TaskOutput.value`). Meanwhile, `cargo test -p mcp-core` and `cargo test -p mcp-protocol` both passed 100% (27/27 and 19/19 tests respectively).

### Obs 2: `mcp-cli` Binary Spawning over Stdio
- `target/release/mcp-cli.exe` exists and runs `mcp serve --stdio`.
- In `crates/mcp-cli/src/main.rs` lines 38-41:
  ```rust
  tracing_subscriber::fmt()
      .with_env_filter(filter)
      .with_target(false)
      .init();
  ```
  And line 639:
  ```rust
  println!("{}", "Starting MCP Server on standard I/O streams...".green());
  ```
  Both write to `stdout`, contaminating the MCP JSON-RPC line stream.
- In `crates/mcp-protocol/src/transport/stdio.rs` lines 183-186:
  ```rust
  let trimmed = line.trim();
  if trimmed.is_empty() {
      return Ok(None);
  }
  ```
  Piping any empty line into `StdioStreamTransport` causes it to return `Ok(None)`, which `server.serve` treats as EOF/disconnect, terminating the server prematurely.
- In `crates/mcp-cli/src/main.rs` lines 28 and 52:
  `#[tokio::main]` creates an outer Tokio runtime, while `EngineRuntime::new(config)` creates an inner Tokio runtime. Dropping the inner runtime when `main()` exits while running on an outer worker thread triggers:
  `thread 'tokio-rt-worker' panicked at ... tokio-1.53.1\src\runtime\task\core.rs:427:22: JoinHandle polled after completion`.

### Obs 3: SSE Transport Server Status
- In `crates/mcp-cli/src/main.rs` lines 637-646:
  ```rust
  McpSubcommands::Serve(s_args) => {
      if s_args.stdio {
          println!("{}", "Starting MCP Server on standard I/O streams...".green());
          let transport = std::sync::Arc::new(mcp_protocol::transport::stdio::StdioStreamTransport::new(
              tokio::io::stdin(),
              tokio::io::stdout(),
          ));
          server.serve(transport).await?;
      }
  }
  ```
  `s_args.sse_port` is defined in `crates/mcp-cli/src/cli.rs`, but not handled in `main.rs`. Running `mcp-cli mcp serve --stdio=false --sse-port 3000` exits immediately with `Ok(())`.
- In `crates/mcp-web/src/server.rs`, `run_server` mounts an Axum server with REST, WebSockets, and `/api/events` (which broadcasts `EngineEvent` metrics, not MCP JSON-RPC).
- In `crates/mcp-protocol/src/transport/sse.rs`, `SseSessionManager`, `SseSession`, `SseServerTransport`, and `SseClientTransport` exist and are tested in `crates/mcp-protocol/tests/sse_transport_tests.rs`.

### Obs 4: All 8 @agent Tools Exposed in `mcp-cli`
In `crates/mcp-cli/src/main.rs`:
1. Line 286: `server.tools().register_fn("run_command", ...)`
2. Line 325: `server.tools().register_fn("execute_cli_command", ...)`
3. Line 353: `server.tools().register_fn("write_code_file", ...)`
4. Line 381: `server.tools().register_fn("read_code_file", ...)`
5. Line 408: `server.tools().register_fn("list_directory", ...)`
6. Line 434: `server.tools().register_fn("get_telemetry", ...)`
7. Line 450: `server.tools().register_fn("recommend_best_model", ...)`
8. Line 473: `server.tools().register_fn("calculate_layer_offload", ...)`
Running `target/release/mcp-cli.exe mcp tools list` outputs all 8 tools with valid descriptions.

### Obs 5: Cooperative Cancellation Support
- In `crates/mcp-protocol/src/server.rs` lines 164-173:
  ```rust
  "notifications/cancelled" => {
      if let Some(params_val) = notif.params {
          if let Ok(cancel_notif) = serde_json::from_value::<CancelledNotification>(params_val) {
              if let Some((_, token)) = self.active_requests.remove(&cancel_notif.request_id) {
                  debug!("Cancelling active request ID: {}", cancel_notif.request_id);
                  token.cancel();
              }
          }
      }
  }
  ```
  `McpServer` only checks for `"notifications/cancelled"`. `"$/cancelRequest"` is not handled.
- In `crates/mcp-cli/src/main.rs` lines 153-169:
  `execute_cli` creates `tokio::process::Command::new(...)`, but does not configure `proc.kill_on_drop(true)`.

---

## 2. Logic Chain

1. **Child Process Stdio Viability (from Obs 1, 2, 4)**:
   `mcp-cli` contains the full 8-tool MCP server. `McpClient::spawn_stdio` can spawn `mcp-cli mcp serve --stdio` and communicate via piped stdin/stdout. However, because `mcp-cli` currently writes non-JSON logs to stdout and `StdioStreamTransport` aborts on empty lines, the integration harness will either encounter stdout deserialization warnings or early connection drops unless:
   - `mcp-cli` is updated to write logs exclusively to `stderr`, and
   - `StdioStreamTransport::receive()` loops past empty lines instead of returning `Ok(None)`.

2. **Child Process SSE Viability (from Obs 3)**:
   Because `mcp-cli mcp serve` does not yet bind an HTTP listener for `--sse-port`, an integration test cannot spawn `mcp-cli` as a standalone child process in SSE mode without code changes to `crates/mcp-cli/src/main.rs`. However, the test harness *can* verify SSE transport end-to-end via `SseServerTransport` and `SseClientTransport` (as demonstrated in `crates/mcp-protocol/tests/sse_transport_tests.rs`).

3. **Test Architecture for R1, R2, R3, R4 (from Obs 1, 4, 5)**:
   - **R1 (Handshake & Discovery)**: Test pre-initialization rejection (`-32002`), `initialize`, `notifications/initialized`, schema verification for `tools/list` (8 tools), `resources/list` (`telemetry://system/status`), `prompts/list` (`analyze_task`), and clean process termination.
   - **R2 (@agent Tools)**: Test each of the 8 tools end-to-end using temporary test workspace directories, verifying non-blocking execution, exit codes, exact byte fidelity, live telemetry, tier classification, and layer offload calculation.
   - **R3 (High-Concurrency 30+)**: Use `tokio::task::JoinSet` to dispatch 36 simultaneous requests across mixed workload types (telemetry, model picking, file I/O, Rayon compute), asserting zero deadlocks, zero dropped connections, and 100% success rate.
   - **R4 (Cancellation & Fault Recovery)**: Verify in-flight task cancellation within 100ms. Inject malformed JSON and unknown methods, verifying structured JSON-RPC error codes (`-32700`, `-32601`, `-32602`) and asserting that the server process survives without crashing.

4. **Test Location & Cargo Invocation (from Obs 1, 2)**:
   Creating a single integration test file `crates/mcp-tests/tests/ide_mcp_integration.rs` provides the fastest compilation time and cleanly maps to `cargo test -p mcp-tests --test ide_mcp_integration -- --nocapture` and `cargo test --workspace --all-targets`.

---

## 3. Caveats

- **Network-Restricted Mode**: In this environment, tests cannot connect to remote cloud LLM endpoints; model recommendation tests must assert against local rule-based evaluation tiers (Small, Medium, Large, CloudApiFallback).
- **GPU Accelerator Availability**: On host environments without dedicated NVIDIA NVML GPUs, telemetry and offload calculations fallback gracefully to CPU/RAM mode. The test assertions must verify fallback behavior when `gpus.is_empty()`.
- **Existing `crates/mcp-tests` Compilation**: As observed in Obs 1, existing unit tests in `tier1_features.rs` and `tier2_boundaries.rs` currently fail compilation. The new `ide_mcp_integration.rs` test must be self-contained and independently compilable without relying on broken `tier1` or `tier2` imports.

---

## 4. Conclusion

1. **Integration Test Suite Target**: Implement `crates/mcp-tests/tests/ide_mcp_integration.rs` containing 5 modular test suites:
   - `test_r1_lifecycle_and_discovery`: Stdio child process spawn, handshake, capability lists, clean teardown.
   - `test_r1_sse_lifecycle`: Full SSE transport handshake and discovery.
   - `test_r2_agent_tools_suite`: All 8 developer tools tested end-to-end against disk and hardware.
   - `test_r3_high_concurrency_stress`: 36 simultaneous JSON-RPC tool calls across async worker tasks.
   - `test_r4_cancellation_and_error_recovery`: <100ms task cancellation and graceful error recovery.
2. **Key Upstream Codebase Adjustments Required for Implementer**:
   - `crates/mcp-protocol/src/transport/stdio.rs`: Fix `StdioStreamTransport::receive()` to ignore empty lines.
   - `crates/mcp-cli/src/main.rs`: Direct `tracing` and `mcp serve` logs to `stderr` instead of `stdout`.
   - `crates/mcp-protocol/src/server.rs`: Support `"$/cancelRequest"` in addition to `"notifications/cancelled"`.
   - `crates/mcp-cli/src/main.rs`: Add `.kill_on_drop(true)` to `execute_cli`.

---

## 5. Verification Method

To independently verify the findings in this report:

1. **Inspect Stdio Server Output**:
   ```powershell
   target\release\mcp-cli.exe mcp tools list
   ```
   Confirms that all 8 `@agent` tools are registered in the CLI binary.
2. **Inspect Upstream Crate Tests**:
   ```powershell
   cargo test -p mcp-protocol
   cargo test -p mcp-core
   ```
   Both pass 100%, proving the underlying protocol engine, stdio/SSE transports, priority scheduler, and cancellation tokens function correctly.
3. **Inspect Compilation Errors in Existing `mcp-tests`**:
   ```powershell
   cargo test -p mcp-tests --test tier1_features
   ```
   Reproduces the observed compilation errors in `tier1_features.rs` and demonstrates why `ide_mcp_integration.rs` should be an independent test target.
4. **Inspect Analysis Artifact**:
   Read `C:\Users\oyesanyf\.gemini\antigravity\scratch\mcp_ide_engine\.agents\survey_explorer_gen3_3\analysis.md` for complete architectural blueprints, JSON schemas, and test harnesses.
