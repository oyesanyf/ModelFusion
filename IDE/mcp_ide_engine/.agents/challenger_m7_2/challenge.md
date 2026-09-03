# Adversarial Challenge Report: Milestone M7 — CLI SSE Server & Process Cleanup

**Verdict: REJECT**

## Challenge Summary

**Overall risk assessment**: CRITICAL

While the CLI HTTP/SSE server implementation in `mcp-cli` is robust, protocol-compliant, and passes exhaustive adversarial stress testing on live TCP sockets, the child process cleanup implementation in `execute_cli` suffers from a **CRITICAL ORPHAN PROCESS LEAK** on Windows. Terminating `cmd.exe /C <command>` via Tokio's `kill_on_drop(true)` terminates only the intermediate shell process, leaving the child payload process (`PING.EXE`, compilers, build tools, etc.) permanently orphaned and running in the background.

Additionally, `cargo test --workspace` fails due to a pre-existing type mismatch in `crates/mcp-web/src/lib.rs:92:53`.

---

## Challenges

### [CRITICAL] Challenge 1: Child Process Orphan Leak on Cancellation in `execute_cli`

- **Assumption challenged**: Worker M7 and Challenger M7_1 assumed that setting `proc.kill_on_drop(true)` on `tokio::process::Command::new("cmd").args(&["/C", cmd_str])` ensures child OS processes are deterministically terminated without leaks upon cancellation.
- **Attack scenario**:
  1. An IDE client sends a `tools/call` JSON-RPC request for `execute_cli_command` with a long-running command (e.g. `ping -n 30 127.0.0.1` or `cargo build`).
  2. The command spawns under `cmd /C`. On Windows, `cmd.exe` spawns a grandchild process `PING.EXE`.
  3. The IDE client issues `$/cancelRequest` after 100ms.
  4. In `crates/mcp-cli/src/main.rs:173-176`, `tokio::select!` cancels the future and drops Tokio's `Child` process handle.
  5. Tokio's drop handler executes `TerminateProcess` on the handle for `cmd.exe`.
  6. On Windows, `TerminateProcess` terminates **ONLY** the direct process handle (`cmd.exe`). It does **NOT** terminate child processes of `cmd.exe` unless they are bound to a Windows Job Object configured with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, or killed via process-tree termination (`taskkill /F /T /PID <pid>`).
  7. As a result, `cmd.exe` exits immediately, the JSON-RPC cancellation response is returned in <80ms, but the actual payload process (`PING.EXE`) continues executing in the background for its entire duration.
- **Blast radius**:
  - AI agents and developer extensions repeatedly cancelling stuck or outdated build commands will leak background compiler/shell processes into Windows OS memory.
  - Orphan processes lock files, exhaust CPU/RAM, and cause concurrency race conditions with subsequent builds.
  - Direct violation of Milestone 7 Acceptance Criteria in `ORIGINAL_REQUEST.md`: *"Long-running shell commands spawned via execute_cli are cleanly terminated upon cancellation with zero orphan process leaks."*
- **Empirical Evidence**:
  - Running unit test `test_cli_command_cancellation_latency_and_kill`:
    ```powershell
    cargo test -p mcp-cli --bin mcp-cli -- test_cli_command_cancellation_latency_and_kill; Start-Sleep -Milliseconds 200; Get-Process ping -ErrorAction SilentlyContinue
    ```
    Output:
    ```
    test tests::test_cli_command_cancellation_latency_and_kill ... ok
    Handles  NPM(K)  PM(K)  WS(K)  CPU(s)    Id  SI ProcessName
         84       6   1016   4100    0.02  6620   1 PING
    ```
    The test passed, but PID 6620 remained actively executing in the Windows process table.
  - Inspection of `tasklist /FI "IMAGENAME eq PING.EXE"` revealed 10 accumulated leaked `PING.EXE` processes (PIDs 5784, 1044, 9044, 1328, 15864, 15240, 3796, 13724, 2712, 12376) left behind by test executions.
- **Mitigation**:
  On Windows, child process execution must:
  1. Associate child processes with a Windows Job Object configured with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` (e.g. via `windows-sys` or `winapi`), OR
  2. Perform explicit process tree termination on cancellation using `taskkill /F /T /PID <pid>` before returning, OR
  3. Parse and spawn the executable directly without the `cmd /C` shell wrapper when possible.

---

### [HIGH] Challenge 2: Workspace Build & Test Suite Failure in `mcp-web`

- **Assumption challenged**: Worker M7 reported that all tests pass across the milestone. While unit tests in `mcp-protocol` and `mcp-cli` pass, `cargo test --workspace` fails.
- **Attack scenario**:
  Running `cargo test --workspace` triggers compilation failure in `crates/mcp-web/src/lib.rs:92:53`:
  ```
  error[E0308]: mismatched types
    --> crates\mcp-web\src\lib.rs:92:53
     |
  92 |         AppState::new(dispatcher, resource_monitor, server)
     |         -------------                               ^^^^^^ expected `Arc<McpServer>`, found `McpServer`
     |         |
     |         arguments to this function are incorrect
  ```
- **Blast radius**: Breaks root CI/CD workspace pipeline and violates acceptance criterion: *"cargo test executes the complete IDE MCP integration test suite with 100% passing results."*
- **Mitigation**: Convert `server` into `Arc<McpServer>` via `server.into()` or `Arc::new(server)`.

---

## Stress Test Results

| Test Scenario | Target | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|:---:|
| CLI SSE Server Health Endpoints | `GET /message`, `GET /messages` | Return HTTP 200 `{ "status": "ok", "service": "mcp-sse-server" }` | Returned HTTP 200 with exact JSON payload | **PASS** |
| Live TCP Port & SSE Headers | `GET /sse` | HTTP 200, `content-type: text/event-stream`, `cache-control: no-cache` | Returned exact headers and chunked stream | **PASS** |
| Initial Endpoint Discovery Event | `GET /sse` | `event: endpoint\ndata: /message?sessionId=<uuid>\n\n` | Received valid endpoint URL and UUID | **PASS** |
| Protocol Handshake over SSE | `POST /message` (`initialize` + `notifications/initialized`) | Returns HTTP 202; SSE stream yields `protocolVersion: "2024-11-05"` | Returned HTTP 202; handshake response received in <50ms | **PASS** |
| Tool Catalog Listing | `tools/list` via SSE | Returns all 8 registered IDE tools | Returned all 8 tools with valid schemas | **PASS** |
| Tool Invocation over SSE | `tools/call` (`get_telemetry`) | Returns CPU/RAM/GPU telemetry text | Telemetry snapshot received over SSE stream | **PASS** |
| Multi-Session SSE Isolation | Concurrent Client A & B | Client A only receives Client A messages; Client B only receives Client B | Verified distinct UUIDs and zero cross-talk | **PASS** |
| Batch JSON-RPC Requests | POST array `[{...}, {...}]` | Returns HTTP 202; both responses stream over SSE | Both response IDs received on SSE stream | **PASS** |
| Malformed JSON Handling | POST invalid JSON syntax | Returns HTTP 400 Bad Request | Returned HTTP 400 Bad Request | **PASS** |
| Invalid JSON-RPC Envelope | POST `{"id": {"invalid": "obj"}}` | Returns HTTP 400 with code -32700 | Returned HTTP 400 with -32700 Parse error | **PASS** |
| Unknown Session ID | POST with non-existent UUID | Returns HTTP 404 with code -32000 | Returned HTTP 404 with -32000 | **PASS** |
| Abrupt Client Disconnection | Close socket on Client B mid-stream | Server remains healthy for Client A | Server unaffected; subsequent requests processed cleanly | **PASS** |
| **Child Process Orphan Leak on Cancellation** | **`execute_cli` long-running command cancellation** | **Spawned child process (`PING.EXE`) cleanly killed upon cancellation; ZERO orphan leaks** | **`cmd.exe` killed, but `PING.EXE` survived running in background** | **FAIL** |
| **Workspace Test Suite** | `cargo test --workspace` | All workspace crates compile and pass tests | `mcp-web` compilation error (`E0308`) | **FAIL** |

---

## Unchallenged Areas

- **Linux / macOS signal propagation**: Testing was performed on Windows 11 host environment. Unix process group signals (`setpgid` / `killpg`) were not tested on Linux.
