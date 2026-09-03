# Milestone M7 Review Report: IDE MCP Engine, Transports & Cancellation Hardening

**Reviewer**: `reviewer_m7_2` (Reviewer & Adversarial Critic)  
**Target Work**: Milestone M7 implementation by `worker_m7`  
**Crates Reviewed**: `crates/mcp-cli`, `crates/mcp-protocol`  
**Date**: 2026-09-03  

---

## Review Summary

**Verdict**: **APPROVE**  
**Confidence**: High  
**Integrity Status**: Fully verified — 0 integrity violations (no dummy facades, no hardcoded results, no bypassed logic).

The implementation in `crates/mcp-cli` and `crates/mcp-protocol` successfully satisfies all functional and architectural requirements for Milestone M7:
1. **Clean JSON-RPC Framing & Stdio Transport**: Standard output pollution is eliminated by routing all logging to stderr (`tracing_subscriber::fmt().with_writer(std::io::stderr)` and `eprintln!`). `StdioStreamTransport` properly skips empty/whitespace lines and CRLFs without premature EOF.
2. **CLI HTTP/SSE MCP Server Engine**: Created `crates/mcp-cli/src/sse_server.rs` with full Axum SSE routing (`GET /sse`, `POST /message`, `POST /messages`, and health check `GET /message`), CORS enabled, KeepAlive streaming, and session dispatch.
3. **CLI Wiring**: Properly wired `mcp serve --sse-port <PORT>` in `crates/mcp-cli/src/cli.rs` and `main.rs`.
4. **Child Process Cancellation & Leak Prevention**: Configured `proc.kill_on_drop(true)` in `execute_cli`, wrapped execution in `tokio::select!` with `ctx.cancellation_token`, and implemented `AutoCancelTaskOnDrop` RAII guard in MCP tool handlers.
5. **LSP/IDE Cancellation**: Enhanced `mcp-protocol/src/server.rs` to support `$/cancelRequest` as both JSON-RPC notification and request, with dual `requestId` and `id` parameter resolution.
6. **Test Verification**: 100% pass across `mcp-cli` (4/4) and `mcp-protocol` (21/21).

---

## Findings & Recommendations

### [Medium] Finding 1: SseSession Lifecycle Lacks Cleanup on SSE Client Disconnect
- **What**: When an SSE client drops its TCP connection or closes the stream, the `SseSession` remains in `SseSessionManager.sessions` (`DashMap`) indefinitely, and the background task running `server.serve(transport)` does not terminate because `session.incoming_rx` never encounters EOF.
- **Where**: `crates/mcp-cli/src/sse_server.rs:67-80`
- **Why**: In `sse_endpoint_handler`, `tokio::spawn(async move { server.serve(transport).await })` is spawned for the session. Because `session` is retained in `session_manager.sessions`, `session.incoming_tx` is never dropped, so `incoming_rx.recv()` awaits indefinitely.
- **Suggestion**: Implement an RAII stream guard or a stream finalizer on the SSE stream in `sse_endpoint_handler` that invokes `state.session_manager.remove_session(&session.session_id)` when the SSE stream drops. Additionally, propagate a session-level `CancellationToken` into `server.serve` so the server task cleanly terminates on disconnect.

### [Low] Finding 2: POST `/message` Fallback to `get_any_session()` in Multi-Client Environments
- **What**: If an incoming POST request to `/message` omits the `sessionId` query parameter, `post_message_handler` falls back to `state.session_manager.get_any_session()`.
- **Where**: `crates/mcp-cli/src/sse_server.rs:121-125`
- **Why**: While convenient for single-session CLI debugging, in a multi-client or multi-tab environment, an untagged POST request could inadvertently route JSON-RPC requests into an arbitrary active session (`DashMap::iter().next()`).
- **Suggestion**: Only allow `get_any_session()` if `session_manager.session_count() == 1`, or return a `400 Bad Request` requiring `sessionId` when multiple concurrent sessions exist.

### [Low] Finding 3: Windows Grandchild Process Tree Termination
- **What**: In Windows environments, `tokio::process::Command` executes commands via `cmd.exe /C <cmd_str>`. Setting `kill_on_drop(true)` calls `TerminateProcess` on `cmd.exe`.
- **Where**: `crates/mcp-cli/src/main.rs:156-170`
- **Why**: On Windows, abruptly terminating `cmd.exe` can occasionally leave grandchild processes running if they were not bound to a Win32 Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`.
- **Suggestion**: For future production hardening, associate spawned Windows child processes with a Win32 Job Object configured with `KILL_ON_JOB_CLOSE` to ensure entire process trees are atomically terminated upon drop.

---

## Adversarial Challenge & Stress-Test Results

| Scenario / Assumption | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|
| **Child Process Abort Under 100ms**: `ping -n 10 127.0.0.1` dispatched and cancelled after 30ms | Command execution aborts with `TaskError::Cancelled` in <100ms without orphan leak | Completed in ~35ms, returned `TaskError::Cancelled`, process killed via `kill_on_drop` | **PASS** |
| **MCP Tool Cancellation Propagation**: `execute_cli_command` called with cancellation token fired after 30ms | Tool call returns `is_error: true` / Cancelled in <100ms | Completed in ~35ms, returned `CallToolResult` with `is_error = Some(true)` | **PASS** |
| **Dropped Future Process Cleanup**: Tool future dropped before completion | `AutoCancelTaskOnDrop` RAII guard triggers `dispatcher.cancel_task` | Guard successfully fires on drop; tested and validated | **PASS** |
| **Real TCP HTTP/SSE Roundtrip**: Connect to `/message`, connect to `/sse`, receive endpoint event, POST `initialize`, receive response over SSE stream | Full MCP 2024-11-05 handshake over real TCP socket | Real TCP client connected, received `/message?sessionId=...`, POSTed JSON-RPC init, received valid MCP server init response | **PASS** |
| **Stdio Stream Blank Line Resilience**: Multiple empty lines, whitespace, and CRLFs before JSON-RPC frame | Blank lines ignored without returning premature EOF | `loop` skips empty lines; parsed subsequent frame correctly | **PASS** |
| **LSP `$/cancelRequest` Interoperability**: Client sends `$/cancelRequest` before and after init, using `requestId` or `id` | Valid cancel response returned and target token cancelled | Handled both notification and request formats with dual ID parameter resolution | **PASS** |

---

## Verified Claims

- [x] `cargo test -p mcp-cli` passes 100% (4 passed, 0 failed, 0 ignored).
- [x] `cargo test -p mcp-protocol` passes 100% (21 passed, 0 failed, 0 ignored).
- [x] CLI binary compiles and responds to `mcp serve --help` with `--stdio` and `--sse-port <SSE_PORT>`.
- [x] Stdout pollution eliminated via `with_writer(std::io::stderr)` and `eprintln!`.
- [x] Zero compiler warnings in `crates/mcp-cli` and `crates/mcp-protocol`.
- [x] No integrity violations or dummy/facade implementations detected.
