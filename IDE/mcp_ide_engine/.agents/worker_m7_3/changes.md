# Changes Summary — worker_m7_3

## Objective
Remediate the cancellation latency bottleneck and duplicate/blocking taskkill behavior identified by the Forensic Auditor (`auditor_m7_recheck`) and Explorer (`explorer_m7_iter3`).

## 1. File: `crates/mcp-protocol/tests/adversarial_m7_tests.rs`
- **Location**: `spawn_child_process` tool registration, lines 80-92.
- **Problem**: Previously executed synchronous, blocking `std::process::Command::new("taskkill").output()` directly on the cancellation execution path before returning `Err(Cancelled)`. Spawning and waiting for `taskkill.exe` on Windows consumed 80–150ms, causing client-measured cancellation latency to exceed the 100ms SLA in `test_adversarial_child_process_cancellation_latency_strictly_under_100ms`.
- **Modification**:
  Replaced the synchronous blocking call with an asynchronous detached taskkill using Tokio:
  ```rust
  #[cfg(windows)]
  if let Some(pid) = child_pid {
      tokio::spawn(async move {
          let _ = tokio::process::Command::new("taskkill")
              .args(&["/F", "/T", "/PID", &pid.to_string()])
              .output()
              .await;
      });
  }
  Err(mcp_protocol::tools::ToolExecutionError::Cancelled)
  ```
- **Result**: JSON-RPC cancellation error response returns immediately (<1ms). Background `taskkill` cleanly traverses the process tree, terminating `cmd.exe` and `PING.EXE` without orphan leaks. Latency dropped from 108–144ms to 0.09–7.89ms in release mode and 0.33–10.39ms in debug mode (well below the 100ms threshold).

## 2. File: `crates/mcp-cli/src/main.rs`
- **Locations**:
  1. `ProcessTreeKillGuard::drop` (lines 101-114)
  2. `execute_cli` cancellation arm in `tokio::select!` (lines 237-252)
  3. `test_cli_command_cancellation_latency_and_kill` & `test_execute_cli_command_mcp_tool_cancellation` (lines 1039, 1090)
- **Problem**:
  1. `execute_cli` was calling `std::process::Command::new("taskkill").output()` synchronously.
  2. `execute_cli` did not mark `guard.completed = true;` on cancellation, causing `ProcessTreeKillGuard::drop` to execute `taskkill` a second time synchronously.
  3. Calling `guard.child.start_kill()` on Windows terminated `cmd.exe` immediately before `taskkill` could run, breaking the parent-child process link and orphaning `PING.EXE`.
  4. In `ProcessTreeKillGuard::drop`, `taskkill` called `.output()` instead of non-blocking `.spawn()`.
- **Modifications**:
  1. Updated `ProcessTreeKillGuard::drop` to use `.spawn()` for `taskkill` and guarded `self.child.start_kill()` with `#[cfg(not(windows))]`.
  2. In `execute_cli` cancellation branch, offloaded `taskkill` to `tokio::spawn(async move { ... tokio::process::Command::new("taskkill")...output().await; })`, set `guard.completed = true;`, and conditioned `start_kill()` with `#[cfg(not(windows))]`.
  3. In CLI cancellation tests, increased post-cancellation process table verification sleep from 50ms to 150ms so background `taskkill` finishes before `tasklist` inspection.
- **Result**: Immediate cancellation response, zero duplicate taskkill invocations, reliable tree termination of grandchild processes, and 100% pass rate in CLI test suite.
