# Handoff Report: Milestone M7 — IDE MCP Engine, Transports & Cancellation Hardening

## 1. Observation
- **Task 1 (Stdout Pollution)**: In `crates/mcp-cli/src/main.rs:711`, `println!("Starting MCP Server on standard I/O streams...")` was writing banner text to `stdout`, corrupting stdio MCP clients (Claude Desktop, IDE LSP bridges). Additionally, `tracing_subscriber::fmt()` was writing logs to stdout by default.
- **Task 2 (Premature EOF on Blank Lines)**: In `crates/mcp-protocol/src/transport/stdio.rs:182`, `StdioStreamTransport::receive()` returned `Ok(None)` immediately when `trimmed.is_empty()`, which caused the server to interpret empty whitespace lines or carriage returns as an end-of-stream EOF.
- **Task 3 (CLI SSE Server Mode)**: In `crates/mcp-cli/src/main.rs:710`, `McpSubcommands::Serve` only checked `if s_args.stdio`. If `--sse-port <PORT>` was passed, it did nothing and exited immediately. The CLI lacked the Axum HTTP routing wiring for `/sse`, `/message`, and `/messages`.
- **Task 4 (`$/cancelRequest` LSP / IDE Support)**: In `crates/mcp-protocol/src/server.rs:135`, only `"notifications/cancelled"` was handled in `handle_notification`, and `handle_request` rejected any uninitialized method not equal to `"initialize"`. When clients sent `$/cancelRequest` (standard in LSP and many IDE MCP bridges) as either a request or notification, it was rejected or dropped. Furthermore, params containing `"id"` instead of `"requestId"` were not parsed.
- **Task 5 (Child Process Leaks in CLI)**: In `crates/mcp-cli/src/main.rs:156-170`, `tokio::process::Command` did not set `.kill_on_drop(true)`. In `setup_default_mcp_server`, `execute_cli_command` and `run_command` ignored `ctx.cancellation_token`, causing child processes to continue running even if cancelled, leaking orphan processes.

## 2. Logic Chain
- **Stdout Pollution Resolution**:
  - Replaced `println!` with `eprintln!` across all CLI stdio serve pathways.
  - Added `.with_writer(std::io::stderr)` to `tracing_subscriber::fmt()`.
  - Stdout is now reserved exclusively for valid JSON-RPC 2.0 framed messages, preventing JSON parsing errors in IDE transports.
- **Stdio Blank Line Handling**:
  - Refactored `StdioStreamTransport::receive()` into a `loop`: when `trimmed.is_empty()`, the loop continues reading the next line instead of returning `Ok(None)`. Only when `lines.next_line().await` returns `Ok(None)` (actual EOF) does the transport return `Ok(None)`.
- **SSE Server Mode Implementation**:
  - Added `axum`, `tower-http`, and `futures` to `crates/mcp-cli/Cargo.toml`.
  - Implemented `crates/mcp-cli/src/sse_server.rs` with `create_sse_router` and `run_mcp_sse_server`.
  - Routed `GET /sse` (creating session, spawning `server.serve(transport)`, streaming endpoint event then session events), `POST /message` and `POST /messages` (handling single or batch JSON-RPC messages and returning HTTP 202), and `GET /message` / `GET /messages` (health check returning 200 OK).
  - Wired `McpSubcommands::Serve(s_args)`: when `s_args.sse_port` is present, it binds `127.0.0.1:<port>` and runs the server until interrupted.
- **`$/cancelRequest` Handling**:
  - Added `parse_cancel_id(params_val: &Value)` resolving `requestId` or `id`.
  - In `handle_notification`: handled `"notifications/cancelled" | "$/cancelRequest"`, cancelling the active request token.
  - In `handle_request`: allowed `"$/cancelRequest"` pre-initialization, routed it to `handle_cancel_request`, and returned `JsonRpcResponse::success(id, Value::Null)`.
- **Process Leak Prevention & Cooperative Cancellation**:
  - Set `proc.kill_on_drop(true)` in `execute_cli`.
  - Wrapped execution in `tokio::select!` with `ctx.cancellation_token.cancelled()`, aborting in <100ms with `TaskError::Cancelled`.
  - Implemented `AutoCancelTaskOnDrop` guard in `run_command` and `execute_cli_command`. If cancelled or dropped, `dispatcher.cancel_task(&task_id)` triggers token cancellation immediately.

## 3. Caveats
- `cargo check --workspace` displays 11 pre-existing warnings in `crates/mcp-resource`, 2 in `crates/mcp-tui`, and 1 in `crates/mcp-web`. These crates belong to other workers and were intentionally left untouched to maintain module boundaries and avoid cross-milestone conflicts.
- Both crates under M7 ownership (`crates/mcp-protocol` and `crates/mcp-cli`) compile with zero compiler warnings and zero errors.

## 4. Conclusion
- Milestone M7 requirements are 100% complete and fully verified:
  1. Stdout pollution eliminated (all diagnostics/logs redirected to stderr).
  2. Stdio transport skips empty/whitespace lines without EOF.
  3. CLI SSE server mode implemented with full MCP 2024-11-05 endpoint discovery and bidirectional messaging.
  4. `$/cancelRequest` supported as both JSON-RPC notification and request with dual `requestId`/`id` parameter support.
  5. Deterministic child process kill-on-drop and sub-100ms cooperative cancellation verified.
  6. All 25 tests in `mcp-protocol` and `mcp-cli` pass cleanly.

## 5. Verification Method
Run the following commands in `C:\Users\oyesanyf\.gemini\antigravity\scratch\mcp_ide_engine`:
1. `cargo check --workspace`
   - Confirms full workspace compilation with code 0.
2. `cargo test -p mcp-protocol -p mcp-cli`
   - Verifies 25 tests pass with 0 failures:
     - `mcp-protocol`: 21 tests pass (`test_cancel_request_as_notification_and_request`, `test_stdio_stream_transport_blank_lines`, `test_stdio_duplex_stream_handshake_and_tool_call`, `test_sse_client_server_integration`, etc.)
     - `mcp-cli`: 4 tests pass (`test_cli_sse_server_real_tcp_roundtrip`, `test_execute_cli_command_mcp_tool_cancellation`, `test_cli_command_cancellation_latency_and_kill`, `test_cli_command_execution_success`).
