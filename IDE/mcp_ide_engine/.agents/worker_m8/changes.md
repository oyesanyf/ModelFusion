# Changes Recorded — Milestone M8: Realistic IDE Client Simulation & Concurrency Test Suite

## 1. `crates/mcp-tests/Cargo.toml`
- Added required test dependencies:
  - `tokio = { version = "1.36", features = ["full"] }`
  - `reqwest = { version = "0.12", features = ["json", "stream"] }`
  - `futures-util = "0.3"`
  - `tempfile = "3.10"`
  - `serde_json = "1.0"`

## 2. `crates/mcp-tests/tests/ide_mcp_integration.rs`
- Implemented realistic, end-to-end integration test harness `StdioTestHarness` spawning the compiled `mcp-cli` binary.
- Added 5 comprehensive tests:
  - `test_r1_stdio_lifecycle_and_discovery`: Validates JSON-RPC handshake (`initialize` with protocolVersion `2024-11-05`, capabilities, serverInfo), initialized notification, full schema discovery for `tools/list`, `resources/list`, `prompts/list`, and clean shutdown.
  - `test_r1_sse_lifecycle_and_discovery`: Starts `mcp-cli mcp serve --sse-port <port>`, connects to `GET /sse`, performs session handshake via `POST /message?sessionId=...`, verifies `tools/list` response over SSE stream, and cleanly tears down.
  - `test_r2_all_eight_agent_tools_execution`: Exercises all 8 @agent developer tools: `write_code_file`, `read_code_file`, `list_directory`, `execute_cli_command`, `get_telemetry`, `recommend_best_model`, `calculate_layer_offload`, `run_command` with real filesystem manipulation in temp directories.
  - `test_r3_high_concurrency_multi_agent_stress`: Dispatches 35 simultaneous IDE requests across parallel tasks with zero deadlocks, full thread isolation, zero dropped requests, completing in < 1.0s.
  - `test_r4_cooperative_cancellation_and_error_recovery`: Tests `$/cancelRequest` aborting in-flight long-running CLI process (`ping -n 20 127.0.0.1`), verifying SLA < 100ms, asserting zero leaked orphan processes in Windows process table (`tasklist /FI "IMAGENAME eq PING.EXE"`), and testing structured error handling for unknown methods (-32601), invalid schema parameters (-32602), nonexistent tools, and malformed stream recovery.
- Fixed `StdioTestHarness::drop` to only terminate the child process when `Arc::strong_count(&self.child) <= 1` to prevent premature process termination when harness clones are dropped.

## 3. `crates/mcp-cli/src/main.rs`
- Replaced nested Tokio runtime creation with `EngineRuntime::from_handle(tokio::runtime::Handle::current(), compute_workers)`.
- Introduced `ACTIVE_CLI_PIDS` registry (`LazyLock<parking_lot::Mutex<HashMap<TaskId, u32>>>`) to track child process IDs spawned by `execute_cli`.
- In `ProcessTreeKillGuard::drop`, `AutoCancelTaskOnDrop::drop`, and `execute_cli` cancellation handler:
  - Trigger non-blocking process tree termination on cancellation using `tokio::spawn` with `taskkill /F /T /PID <pid>`.
  - Configured child taskkill commands with `Stdio::null()` to prevent sharing or breaking the parent `mcp-cli` stdio pipes.

## 4. `crates/mcp-core/src/cancellation.rs`
- Fixed `HierarchicalCancellationToken`:
  - In `cancelled(&self)`: Added early exit `if self.is_cancelled() { return; }` to immediately return when token is already cancelled.
  - In `cancel(&self)`: Ensured both atomic boolean and underlying `tokio_token` are cancelled and propagated to child tokens.
  - In `child_token_with_name`: Cancelled child tokio token immediately if parent is already cancelled.

## 5. `crates/mcp-protocol/src/transport/stdio.rs`
- Enhanced `StdioStreamTransport::receive()`:
  - Replaced immediate error exit on malformed JSON lines with a warning and stream continuation, ensuring server survives adversarial or corrupted line injection without terminating the connection.

## 6. `crates/mcp-protocol/src/server.rs`
- Updated `McpServer::serve` to gracefully handle transport end-of-stream and errors without crashing or printing unhandled panics.

## 7. `crates/mcp-resource/src/selector.rs`
- Adjusted `ModelSelector::select_best_tier` thresholds:
  - Refined Medium tier conditions (`vram_gb >= 6.0 && ram_gb >= 20.0 || ram_gb >= 24.0`) to cleanly distinguish 4GB/16GB entry systems (classified as Small) from 8GB/32GB mid-tier systems (classified as Medium).

## 8. `crates/mcp-tests/tests/concurrency_stress.rs`
- Updated `ToolRegistry::call` invocation to supply modern parameter schema (`CallToolParams`, `HierarchicalCancellationToken::new_root`, `None`).
