# Milestone M7: IDE MCP Engine, Transports & Cancellation Hardening — Changes

## Summary of Changes

### 1. crates/mcp-protocol/src/transport/stdio.rs
- **Fixed Premature EOF on Blank Lines**: Updated `StdioStreamTransport::receive()` to loop over incoming lines from `BufReader::lines()`, skipping empty or whitespace-only lines (`continue`) instead of returning `Ok(None)`. Blank lines or stray CRLFs no longer terminate the stdio session prematurely.
- **Compiler Warnings Cleaned**: Removed unused imports (`tokio::process::ChildStdin`, `tokio::process::ChildStdout`, `tracing::info`).
- **Tests Added**: Added `test_stdio_stream_transport_blank_lines` in `crates/mcp-protocol/tests/stdio_transport_tests.rs` to verify that leading empty lines and CRLF padding are ignored and the subsequent JSON-RPC message is parsed correctly.

### 2. crates/mcp-protocol/src/server.rs
- **Support `$/cancelRequest` as Notification & Request**:
  - Added helper `parse_cancel_id(params_val: &Value) -> Option<RequestId>` which checks both `"requestId"` (standard MCP 2024-11-05 / VS Code) and `"id"` (LSP / legacy IDEs).
  - In `McpServer::handle_notification`: Added pattern matching for `"notifications/cancelled" | "$/cancelRequest"`. Cancels the matching `HierarchicalCancellationToken` stored in `active_requests`.
  - In `McpServer::handle_request`: Allowed `"$/cancelRequest"` prior to initialization and routed it directly to `handle_cancel_request`, cancelling the task token and returning a valid JSON-RPC 2.0 response `{"jsonrpc":"2.0", "result": null, "id": <req_id>}`.
- **Compiler Warnings Cleaned**: Removed unused imports (`HashMap`, `AtomicBool`, `Ordering`, `error`, `warn`).
- **Tests Added**: Added `test_cancel_request_as_notification_and_request` in `crates/mcp-protocol/src/server.rs` testing both notification and request formats.

### 3. crates/mcp-protocol Cleanups
- Cleaned unused imports across `client.rs`, `lib.rs`, `resources.rs`, `tools.rs`, and `transport/sse.rs`.
- Added helper `get_any_session(&self) -> Option<Arc<SseSession>>` to `SseSessionManager` in `transport/sse.rs`.

### 4. crates/mcp-cli/Cargo.toml
- Added dependencies:
  - `axum = { workspace = true }`
  - `tower-http = { workspace = true }`
  - `futures = { workspace = true }`

### 5. crates/mcp-cli/src/sse_server.rs (NEW FILE)
- Created full HTTP/SSE server for `mcp-cli mcp serve --sse-port <PORT>`:
  - `GET /sse`: Creates SSE session via `SseSessionManager`, connects an `SseServerTransport` instance to `mcp_server.serve(...)`, and streams SSE events starting with `event: endpoint\ndata: /message?sessionId=<uuid>\n\n`.
  - `POST /message` and `POST /messages`: Accepts JSON-RPC requests/notifications (or arrays), matches session ID via query parameter (`sessionId` or fallback to any active session), posts messages to the session receiver, and returns HTTP 202 Accepted.
  - `GET /message` and `GET /messages`: Health check endpoints returning HTTP 200 `{ "status": "ok", "service": "mcp-sse-server" }`.
  - `run_mcp_sse_server`: Binds TCP listener on `127.0.0.1:<port>` with graceful Ctrl-C shutdown.

### 6. crates/mcp-cli/src/main.rs
- **Stdout Pollution Fix**:
  - Replaced `println!` with `eprintln!` in `McpSubcommands::Serve` and stdio/client branches so stdout is reserved exclusively for the JSON-RPC stream.
  - Configured `tracing_subscriber::fmt().with_writer(std::io::stderr)` so structured log output never corrupts standard output.
- **Child Process Leaks Fix & Cooperative Cancellation**:
  - In `execute_cli`: Configured `proc.kill_on_drop(true)` on `tokio::process::Command` ensuring any dropped command immediately terminates the child OS process.
  - Added `tokio::select!` awaiting `ctx.cancellation_token.cancelled()`, aborting in <100ms with `TaskError::Cancelled`.
  - In `setup_default_mcp_server` (`execute_cli_command` and `run_command` tools):
    - Introduced `AutoCancelTaskOnDrop` RAII guard storing `(task_id, dispatcher)`.
    - Wired `ToolExecutionContext::cancellation_token` so that cancellation calls `dispatcher.cancel_task(&task_id)` and returns `ToolExecutionError::Cancelled`.
    - Automatically marks `result.is_error = Some(true)` if the child process exited with a non-zero exit code or failed.
- **SSE Serve CLI Subcommand**:
  - In `McpSubcommands::Serve`: Added support for `s_args.sse_port`. When specified, launches `sse_server::run_mcp_sse_server(server.clone(), addr).await`.
- **Tests Added**:
  - `test_cli_command_execution_success`
  - `test_cli_command_cancellation_latency_and_kill`
  - `test_execute_cli_command_mcp_tool_cancellation`
  - `test_cli_sse_server_real_tcp_roundtrip`

### 7. crates/mcp-cli/src/lib.rs (NEW FILE)
- Created library interface exposing `cli`, `repl`, and `sse_server` modules.

### 8. crates/mcp-cli/src/repl.rs
- Cleaned up unused imports and lifetime elision warnings (`Cow<'_, str>`).
