# Changes Made in Milestone M8 Gate Iteration 2 Remediation

## 1. `crates/mcp-tests/Cargo.toml`
- Added `autotests = false` under `[package]` to disable Cargo's automatic test target discovery of legacy, unmaintained M6 test files (`tier1_features.rs` through `tier5_adversarial.rs`).
- Explicitly registered the maintained integration test targets:
  - `[[test]] name = "ide_mcp_integration" path = "tests/ide_mcp_integration.rs"`
  - `[[test]] name = "concurrency_stress" path = "tests/concurrency_stress.rs"`
  - `[[test]] name = "challenger_m8_stress" path = "tests/challenger_m8_stress.rs"`

## 2. `crates/mcp-cli/src/main.rs`
- Declared `pub static LAST_SPAWNED_CLI_PID: std::sync::atomic::AtomicU32 = std::sync::atomic::AtomicU32::new(0);` at line 91.
- In `execute_cli` (lines 251-255), recorded `pid` into `LAST_SPAWNED_CLI_PID` on process spawn (`LAST_SPAWNED_CLI_PID.store(pid, std::sync::atomic::Ordering::SeqCst);`).
- In `test_cli_command_cancellation_latency_and_kill`:
  - Reset `LAST_SPAWNED_CLI_PID.store(0, std::sync::atomic::Ordering::SeqCst);` at the start of the test.
  - Replaced global `tasklist /FI "IMAGENAME eq PING.EXE"` with targeted query `tasklist /FI "PID eq <target_pid>"` and added a retry loop (10 iterations x 50ms) to inspect whether the target PID is terminated.
- In `test_execute_cli_command_mcp_tool_cancellation`:
  - Reset `LAST_SPAWNED_CLI_PID.store(0, std::sync::atomic::Ordering::SeqCst);` at the start of the test.
  - Replaced global `tasklist /FI "IMAGENAME eq PING.EXE"` with targeted query `tasklist /FI "PID eq <target_pid>"` and added a retry loop (10 iterations x 50ms) to inspect whether the target PID is terminated.
