# Handoff Report: Milestone M7 — Empirical Challenge & Adversarial Verification

## 1. Observation
- **Observation 1 (Child Process Orphan Leak on Windows)**:
  In `crates/mcp-cli/src/main.rs:156-176`, `execute_cli` wraps Windows shell execution as:
  ```rust
  #[cfg(windows)]
  let mut proc = tokio::process::Command::new("cmd");
  #[cfg(windows)]
  proc.args(&["/C", cmd_str]);
  ...
  proc.kill_on_drop(true);

  tokio::select! {
      _ = ctx.cancellation_token.cancelled() => {
          Err(mcp_core::registry::TaskError::Cancelled)
      }
      output_res = proc.output() => { ... }
  }
  ```
  When cancelled, `proc.output()` is dropped. Tokio drops `Child` and invokes `TerminateProcess(proc.handle, 1)`. On Windows, `TerminateProcess` terminates ONLY `cmd.exe` and does NOT kill grandchild processes spawned by `cmd.exe`.
  Empirical verification:
  Running:
  ```powershell
  cargo test -p mcp-cli --bin mcp-cli -- test_cli_command_cancellation_latency_and_kill; Start-Sleep -Milliseconds 200; Get-Process ping -ErrorAction SilentlyContinue
  ```
  Produces:
  ```
  test tests::test_cli_command_cancellation_latency_and_kill ... ok
  test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 3 filtered out; finished in 0.45s

  Handles  NPM(K)    PM(K)      WS(K)     CPU(s)     Id  SI ProcessName                                                  
  -------  ------    -----      -----     ------     --  -- -----------                                                  
       84       6     1016       4100       0.02   6620   1 PING                                                         
  ```
  The test passes because `matches!(wait_res, Err(mcp_core::registry::TaskError::Cancelled))` evaluates to true, but `PING.EXE` (PID 6620) is left actively running in the Windows process table.
  A query of `tasklist /FI "IMAGENAME eq PING.EXE"` revealed 10 leaked `PING.EXE` processes (PIDs 5784, 1044, 9044, 1328, 15864, 15240, 3796, 13724, 2712, 12376) accumulated from test runs.

- **Observation 2 (CLI HTTP/SSE Server Robustness)**:
  `mcp-cli mcp serve --sse-port <PORT>` successfully binds to TCP port `127.0.0.1:<PORT>`.
  - `GET /message` and `GET /messages` return HTTP 200 `{ "status": "ok", "service": "mcp-sse-server" }`.
  - `GET /sse` returns HTTP 200 with headers:
    - `content-type: text/event-stream`
    - `cache-control: no-cache`
    - `access-control-allow-origin: *`
  - Initial event streams: `event: endpoint\ndata: /message?sessionId=<uuid>\n\n`.
  - POST requests with `initialize` return HTTP 202 Accepted, and initialization response with `protocolVersion: "2024-11-05"` streams over the client's SSE session.
  - Concurrent clients (Client A and Client B) maintain strict session isolation with distinct UUIDs and zero message cross-talk.
  - Batch JSON-RPC requests (`[{...}, {...}]`) are accepted with HTTP 202 and responses stream back over SSE.
  - Invalid requests are handled cleanly: malformed JSON returns HTTP 400 Bad Request; invalid JSON-RPC format returns HTTP 400 with `-32700 Parse error`; unknown session ID returns HTTP 404 with `-32000`.
  - Abrupt client socket closure does not crash or degrade the server.

- **Observation 3 (Workspace Compilation Failure)**:
  `cargo test --workspace` fails during compilation of `mcp-web`:
  ```
  error[E0308]: mismatched types
    --> crates\mcp-web\src\lib.rs:92:53
     |
  92 |         AppState::new(dispatcher, resource_monitor, server)
     |         -------------                               ^^^^^^ expected `Arc<McpServer>`, found `McpServer`
     |         |
     |         arguments to this function are incorrect
  ```

## 2. Logic Chain
1. Requirement R4 in `ORIGINAL_REQUEST.md` specifies:
   *"Verify that cancellation tokens sent from the IDE ($/cancelRequest / notifications/cancelled) immediately terminate in-flight shell processes and queue items without orphan leaks"*
   And Acceptance Criteria:
   *"Long-running shell commands spawned via execute_cli are cleanly terminated upon cancellation with zero orphan process leaks."*
2. Worker M7 claimed that adding `proc.kill_on_drop(true)` in `execute_cli` resolved process leaks.
3. However, on Windows, executing `cmd.exe /C <command>` creates a process tree where `cmd.exe` is the parent and the target executable (`PING.EXE`, compiler, etc.) is the child.
4. When `tokio::select!` drops `proc.output()`, Tokio calls `TerminateProcess` on the handle of `cmd.exe`.
5. On Windows, `TerminateProcess` terminates only the specified process (`cmd.exe`). Child processes spawned by `cmd.exe` are orphaned and continue executing in the background until completion.
6. The test `test_cli_command_cancellation_latency_and_kill` checks only that the future cancelled within 500ms; it never inspects the OS process table.
7. Consequently, every cancelled command leaks an orphan background process.
8. Therefore, the requirement of zero orphan process leaks is NOT satisfied.

## 3. Caveats
- No implementation code was modified by this challenger (review-only mandate respected).
- The process leak specifically manifests on Windows when spawning via the intermediate shell `cmd /C`. On Unix systems, similar behavior occurs if process groups are not created via `setpgid` and killed via `killpg`.
- The CLI SSE server functionality is completely compliant and works as specified.

## 4. Conclusion
- **VERDICT: REJECT**.
- **Blocking Defect 1**: Child process orphan leak in `execute_cli` on Windows. Commands spawned via `execute_cli` leak active grandchild processes into Windows OS memory upon cancellation.
- **Remediation**:
  In `execute_cli` on Windows, wrap child processes in a Windows Job Object configured with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, or execute process tree termination (`taskkill /F /T /PID <pid>`) upon cancellation token trigger.
- **Blocking Defect 2**: `cargo test --workspace` fails due to `E0308` type mismatch in `crates/mcp-web/src/lib.rs:92:53` (`expected Arc<McpServer>, found McpServer`). Needs `Arc::new(server)`.

## 5. Verification Method
1. **Reproduce Child Process Orphan Leak**:
   Execute in PowerShell:
   ```powershell
   cargo test -p mcp-cli --bin mcp-cli -- test_cli_command_cancellation_latency_and_kill; Start-Sleep -Milliseconds 200; Get-Process ping -ErrorAction SilentlyContinue
   ```
   *Expected leak demonstration*: `PING.EXE` appears in the process list with an active PID despite the test passing.
   Clean up leaked process: `taskkill /F /IM PING.EXE`.

2. **Verify Workspace Build Failure**:
   ```bash
   cargo test --workspace
   ```
   *Expected error*: Compilation failure in `crates/mcp-web/src/lib.rs:92:53` with `error[E0308]: mismatched types`.

3. **Verify CLI SSE Server Mode**:
   ```bash
   cargo test -p mcp-cli --test-threads=1
   ```
   *Expected*: Passes unit tests for CLI SSE server and command dispatch.
