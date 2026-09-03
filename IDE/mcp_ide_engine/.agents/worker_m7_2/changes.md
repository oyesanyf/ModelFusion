# Changes Made — Milestone M7 Remediation

## Summary of Remediations

### 1. crates/mcp-cli/src/main.rs: Process Tree Termination & Grandchild Leak Prevention
- **Root Cause**:
  1. Tokio's `tokio::process::Command` with `kill_on_drop(true)` invokes `TerminateProcess` directly on the direct child handle (`cmd.exe`). On Windows, `TerminateProcess` terminates only the specified process without terminating its descendants. Consequently, grandchild processes spawned by `cmd /C` (such as `PING.EXE`, compiler processes, or build tools) survived as orphan background processes.
  2. Additionally, when cancellation was triggered by an outer task dispatcher (e.g., `mcp-core`'s `TaskDispatcher`), the future was dropped before the inner `select!` cancellation arm could execute. If `cmd.exe` was killed first by `kill_on_drop(true)` during future drop, subsequent `taskkill /F /T /PID <pid>` calls would fail with `ERROR: The process "<pid>" not found`, failing to kill descendant processes.
- **Fix**:
  - Implemented `ProcessTreeKillGuard` wrapping `tokio::process::Child` and `child_pid: Option<u32>`.
  - In its `Drop` implementation, if the task was not marked `completed`:
    - On Windows, executes `taskkill /F /T /PID <pid>` **before** dropping or terminating `cmd.exe`. Because `cmd.exe` is still open in the Windows process table, Windows successfully locates all descendant processes (e.g., `PING.EXE`) and forcefully terminates the entire process tree.
    - Explicitly invokes `self.child.start_kill()` to ensure the direct handle is cleaned up.
  - Implemented `wait_child_output` helper to read stdout and stderr asynchronously while waiting on `&mut child`, avoiding premature consumption of `child` ownership.
  - Retained explicit `_ = ctx.cancellation_token.cancelled() =>` handling in `execute_cli` with `taskkill /F /T /PID <pid>` and `guard.child.start_kill()`.
  - Updated `test_cli_command_cancellation_latency_and_kill` and `test_execute_cli_command_mcp_tool_cancellation` in `crates/mcp-cli/src/main.rs` to:
    - Assert that after cancellation, `tasklist /FI "IMAGENAME eq PING.EXE"` confirms that `PING.EXE` is 100% absent from the Windows process table.
    - Synchronize cancellation tests using `CLI_CANCEL_TEST_MUTEX` to prevent race conditions during concurrent test runner execution.

### 2. crates/mcp-web/src/lib.rs: Test Compilation Type Mismatch Fix
- **Root Cause**:
  `AppState::new(dispatcher, resource_monitor, server)` at line 92 passed `server: McpServer` directly, but `AppState::new` requires `mcp_server: Arc<McpServer>`.
- **Fix**:
  Wrapped `server` with `Arc::new(server)`.

### 3. crates/mcp-protocol/tests/adversarial_m7_tests.rs: Child Process Tree Cleanup in Test Suite
- **Fix**:
  Updated the `spawn_child_process` test tool in `adversarial_m7_tests.rs` to capture `child.id()` and run `taskkill /F /T /PID <pid>` upon cancellation. This prevents the 10 iterations of `ping -n 15 127.0.0.1` from leaking orphan background processes, reducing test execution time from 14.5s to 0.8s.
