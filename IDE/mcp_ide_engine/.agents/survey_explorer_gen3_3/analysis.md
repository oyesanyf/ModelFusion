# Comprehensive Architecture & Investigation Report: IDE MCP Integration Test Suite & Harness

**Author**: survey_explorer_gen3_3  
**Date**: 2026-09-03  
**Scope**: Read-Only Architecture Survey & Integration Harness Design  
**Target Workspace**: `crates/mcp-tests` & `mcp_ide_engine`

---

## 1. Executive Summary

This investigation analyzes how to implement a realistic, end-to-end integration test suite and test harness verifying all acceptance criteria for the Model Context Protocol (MCP) subsystem of the MCP IDE Engine (`ORIGINAL_REQUEST.md` ## 2026-09-03T19:26:42Z).

### Core Findings Matrix

| Focus Area | Investigation Finding | Critical Risks / Blockers Identified | Recommended Test Solution |
|---|---|---|---|
| **Child Process Spawning (stdio)** | `mcp-cli` can be spawned via `tokio::process::Command` using `target/release/mcp-cli.exe` or `target/debug/mcp-cli.exe` with `mcp serve --stdio`. `mcp-protocol::client::McpClient::spawn_stdio` provides the transport abstraction. | **1.** `mcp-cli` prints logs to stdout (`println!` and default `tracing_subscriber` format), contaminating line-delimited JSON-RPC stdout.<br>**2.** `StdioStreamTransport::receive()` treats empty lines (`""`) as EOF (`return Ok(None)`), causing immediate server shutdown if empty lines are piped.<br>**3.** Nested Tokio runtime conflict on exit (`EngineRuntime::new` inside `#[tokio::main]`). | Test harness must use `StdioProcessTransport` with resilient line filtering, and codebase should direct all logging in `mcp-cli` to `stderr`. |
| **SSE Transport Server** | `mcp-protocol` has full SSE transport primitives (`SseSessionManager`, `SseServerTransport`, `SseClientTransport`), but `mcp-cli mcp serve` currently does **not** implement `--sse-port`, and `mcp-web` lacks the MCP 2024-11-05 SSE JSON-RPC router (`/sse` & `/message`). | Child process SSE mode cannot connect unless `mcp-cli` or `mcp-web` wires an Axum/Hyper SSE router. | Test suite should test SSE via `SseServerTransport` / `SseClientTransport` and in-process HTTP listener, while testing stdio out-of-process. |
| **R1: Handshake & Discovery** | MCP 2024-11-05 handshake requires `initialize` $\to$ `InitializeResult` $\to$ `notifications/initialized`, followed by `tools/list`, `resources/list`, and `prompts/list`. | Before `notifications/initialized`, only `initialize` and `ping` are permitted. Sending `tools/list` early returns error code `-32002` (Server Not Initialized). | Implement strict state machine verification in harness, validating protocol version negotiation and schema definitions. |
| **R2: @agent Tools Suite** | 8 real tools are exposed in `mcp-cli` (`write_code_file`, `read_code_file`, `list_directory`, `execute_cli_command`, `get_telemetry`, `recommend_best_model`, `calculate_layer_offload`, `run_command`). Existing `crates/mcp-tests` uses a synthetic `tool_add` instead. | The existing `mcp-tests/src/lib.rs` `TestHarness` does **not** register the 8 `@agent` tools; those are defined only in `crates/mcp-cli/src/main.rs`. | Harness must test against the actual server instance (either spawned child process or `setup_default_mcp_server` shared helper). |
| **R3: Concurrency Stress (30+)** | Multi-lane scheduler and async reactor handle concurrent tasks cleanly. | In-flight stdio piping requires non-blocking mutex serialization over the single child stdin stream. | Client harness utilizes `McpClient` request multiplexing with atomic `RequestId` tracking across 30+ parallel worker tasks via `tokio::task::JoinSet`. |
| **R4: Cooperative Cancellation & Errors** | MCP spec uses `notifications/cancelled`. Dispatch prompt requires support for `$/cancelRequest` and <100ms cancellation. | **1.** `McpServer::handle_notification` currently handles `notifications/cancelled`, but does **not** handle `$/cancelRequest`.<br>**2.** In `execute_cli_command`, child `proc` does not set `kill_on_drop(true)` nor does `TaskHandle` implement `Drop`. | Implement `$/cancelRequest` handler in `McpServer`, verify <100ms abort latency, and test error recovery on malformed/invalid JSON-RPC without server crash. |

---

## 2. Inspection of `crates/mcp-tests` and Existing Infrastructure

### 2.1 File Inventory
`crates/mcp-tests` currently contains:
- `Cargo.toml`: Declares dependencies on `mcp-core`, `mcp-protocol`, `mcp-resource`, `mcp-tui`, `mcp-web`.
- `src/lib.rs`: Defines `TestHarness::new(worker_threads, compute_threads)`.
- `tests/concurrency_stress.rs`: In-memory tests dispatching synthetic tasks (`fast_calc`, `delay`, `heavy_compute`, `tool_add`).
- `tests/tier1_features.rs`: Unit-level coverage tests for individual feature flags.
- `tests/tier2_boundaries.rs`: Boundary and negative tests.
- `tests/tier3_combinations.rs`: Pairwise feature interactions.
- `tests/tier4_scenarios.rs`: 6 high-level scenarios (routing, parallel tools, TUI+web, compute burst, cancellation, memory pressure) using `ChannelTransport`.
- `tests/tier5_adversarial.rs`: Adversarial edge cases.

### 2.2 Critical Infrastructure Gaps in Existing Tests
1. **Opaque-Box Gap**: Every test in `crates/mcp-tests` currently runs **in-process** via direct Rust function calls or in-memory `ChannelTransport`. None of the tests spawn `mcp-cli` as an external child process or test line-delimited JSON-RPC framing over operating system pipes.
2. **Tool Disparity**: The existing `TestHarness` in `mcp-tests/src/lib.rs` registers only `tool_add`, `metrics://system/load`, and `code_review`. It does **not** register any of the actual developer `@agent` tools:
   - `write_code_file`
   - `read_code_file`
   - `list_directory`
   - `execute_cli_command`
   - `get_telemetry`
   - `recommend_best_model`
   - `calculate_layer_offload`
   - `run_command`
   These tools are currently declared only in `crates/mcp-cli/src/main.rs` (`setup_default_mcp_server`).
3. **Compilation Drift**: `tier1_features.rs` and `tier2_boundaries.rs` currently fail compilation due to outdated API references (e.g. `ModelSpec::llama_3_8b_instruct_q4`, `TaskOutput.value`, and `tools.call` 3-argument signature change).

---

## 3. Child Process Spawning & Transports Analysis

### 3.1 Spawning `mcp-cli` in Stdio Mode
Can an integration test spawn `mcp-cli` and communicate via piped stdin/stdout?
**Answer: YES**, but with specific prerequisites.

#### Mechanism:
The test harness locates `mcp-cli.exe` and invokes `mcp serve --stdio`:
```rust
let bin_path = get_mcp_cli_binary_path();
let mut cmd = tokio::process::Command::new(bin_path);
cmd.args(&["mcp", "serve", "--stdio"]);
let client = McpClient::spawn_stdio(cmd, "test-ide-client", "1.0.0")?;
```

#### Locating the Binary:
Cargo integration tests in `crates/mcp-tests/tests/` can resolve the workspace binary via:
```rust
pub fn get_mcp_cli_binary_path() -> std::path::PathBuf {
    if let Ok(path) = std::env::var("CARGO_BIN_EXE_mcp-cli") {
        return std::path::PathBuf::from(path);
    }
    if let Ok(current_exe) = std::env::current_exe() {
        let target_dir = current_exe.parent().unwrap().parent().unwrap();
        let bin = target_dir.join(format!("mcp-cli{}", std::env::consts::EXE_SUFFIX));
        if bin.exists() {
            return bin;
        }
    }
    let manifest = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    let ws_root = manifest.parent().unwrap().parent().unwrap();
    let release_bin = ws_root.join("target/release").join(format!("mcp-cli{}", std::env::consts::EXE_SUFFIX));
    if release_bin.exists() { return release_bin; }
    let debug_bin = ws_root.join("target/debug").join(format!("mcp-cli{}", std::env::consts::EXE_SUFFIX));
    if debug_bin.exists() { return debug_bin; }
    panic!("mcp-cli binary not found. Build with `cargo build --bin mcp-cli` first.");
}
```

#### Three Identified Defects in `mcp-cli` Stdio Server:
1. **Stdout Pollution**:
   In `crates/mcp-cli/src/main.rs`:
   - Line 38: `tracing_subscriber::fmt().init()` logs to `stdout` by default.
   - Line 639: `println!("{}", "Starting MCP Server on standard I/O streams...".green());` writes ANSI text to `stdout`.
   *Fix Requirement*: Direct all logging and startup messages to `stderr` (`.with_writer(std::io::stderr)` and `eprintln!`).
2. **Premature EOF on Empty Lines**:
   In `crates/mcp-protocol/src/transport/stdio.rs`:
   ```rust
   // StdioStreamTransport::receive()
   if trimmed.is_empty() {
       return Ok(None); // BUG: Treats empty line as EOF!
   }
   ```
   *Fix Requirement*: Should be a loop that skips empty lines (`continue;`), matching `StdioProcessTransport`.
3. **Nested Tokio Runtime Panic on Process Exit**:
   `crates/mcp-cli/src/main.rs` uses `#[tokio::main]`, and then calls `EngineRuntime::new(config)` which initializes a second `tokio::runtime::Runtime`. When `main` exits, dropping the inner runtime inside the outer async worker panics with `JoinHandle polled after completion`.
   *Fix Requirement*: Use `EngineRuntime::from_handle(tokio::runtime::Handle::current(), ...)` when inside `#[tokio::main]`.

---

### 3.2 Spawning `mcp-cli` in SSE Server Mode
Can an integration test spawn `mcp-cli` in SSE server mode and connect via HTTP/SSE client?
**Answer: NOT in the current CLI implementation**, because:
1. In `crates/mcp-cli/src/cli.rs`, `McpServeArgs` defines:
   ```rust
   pub struct McpServeArgs {
       pub stdio: bool,
       pub sse_port: Option<u16>,
   }
   ```
2. But in `crates/mcp-cli/src/main.rs` lines 637-646:
   ```rust
   McpSubcommands::Serve(s_args) => {
       if s_args.stdio {
           ...
           server.serve(transport).await?;
       }
   }
   ```
   If `--stdio=false` or `--sse-port <port>` is passed, the match arm does nothing and exits immediately with `Ok(())`.
3. In `crates/mcp-web/src/server.rs`, `run_server` provides an Axum server with REST, WebSockets, and `/api/events` (which broadcasts `EngineEvent` metrics, **not** MCP 2024-11-05 JSON-RPC).
4. In `crates/mcp-protocol/src/transport/sse.rs`, full SSE transport logic exists: `SseSessionManager`, `SseSession`, `SseServerTransport`, and `SseClientTransport`.

#### Proposed SSE Architecture for Tests:
For integration testing of SSE:
- **Approach A (In-Process HTTP SSE Server)**: Use Axum or `tokio::net::TcpListener` in the test harness with `SseSessionManager`, running `McpServer::serve(server_transport)` and connecting `McpClient` via `SseClientTransport`.
- **Approach B (CLI Enhancement)**: Implement `s_args.sse_port` in `mcp-cli` by mounting an Axum router with `GET /sse` and `POST /message?sessionId=:id`, allowing `mcp-cli` to be spawned as an external process listening on an ephemeral port.

---

## 4. Test Architecture Formulation

The integration test suite must verify the 4 core requirements:

```
                               ┌────────────────────────────────────────────────────────┐
                               │             crates/mcp-tests/tests/                    │
                               │             ide_mcp_integration.rs                    │
                               └────────────────────────┬───────────────────────────────┘
                                                        │
         ┌──────────────────────────────┬───────────────┴──────────────┬──────────────────────────────┐
         ▼                              ▼                              ▼                              ▼
  ┌──────────────┐              ┌──────────────┐              ┌──────────────┐              ┌──────────────┐
  │   Suite R1   │              │   Suite R2   │              │   Suite R3   │              │   Suite R4   │
  │ Handshake &  │              │ @agent Tools │              │ High Load    │              │ Cancellation │
  │ Lifecycle    │              │ Suite (8/8)  │              │ (30+ Concur) │              │ & Recovery   │
  └──────────────┘              └──────────────┘              └──────────────┘              └──────────────┘
```

---

### 4.1 Requirement 1: Realistic IDE Client Simulation (Handshake & Discovery)

#### Protocol Handshake Flow (MCP 2024-11-05):
1. **Pre-Initialization Guard**:
   - Send `tools/list` before handshake.
   - Assert server returns JSON-RPC error `-32002` (`ServerNotInitialized`).
2. **`initialize` Request**:
   - Client sends:
     ```json
     {
       "jsonrpc": "2.0",
       "id": 1,
       "method": "initialize",
       "params": {
         "protocolVersion": "2024-11-05",
         "capabilities": { "roots": { "listChanged": true } },
         "clientInfo": { "name": "antigravity-ide-client", "version": "1.0.0" }
       }
     }
     ```
   - Server returns `InitializeResult`:
     - `protocolVersion`: `"2024-11-05"`
     - `serverInfo.name`: `"mcp-ide-engine"`
     - `capabilities.tools.listChanged`: `true`
     - `capabilities.resources.subscribe`: `true`
     - `capabilities.prompts.listChanged`: `true`
3. **`notifications/initialized` Notification**:
   - Client sends one-way notification:
     ```json
     { "jsonrpc": "2.0", "method": "notifications/initialized" }
     ```
   - Server transitions state from `Initializing` to `Initialized`.
4. **Capability Discovery Inspection**:
   - Call `tools/list`: Assert exactly 8 tools returned, each with valid `inputSchema`.
   - Call `resources/list`: Assert `telemetry://system/status` is present with valid MIME type.
   - Call `prompts/list`: Assert `analyze_task` template is present.
5. **Clean Shutdown & Teardown**:
   - Client drops/closes stdio streams.
   - Child process terminates cleanly with exit code 0 within 500ms.

---

### 4.2 Requirement 2: End-to-End @agent Tool Suite Testing

Every exposed tool must be executed over the live protocol channel against realistic workspace files:

```
   IDE Agent Call (tools/call)
             │
             ▼
 ┌───────────────────────┐
 │   MCP Server Router   │
 └───────────┬───────────┘
             │
             ├──► write_code_file      ──► Creates nested file & writes UTF-8 code
             ├──► read_code_file       ──► Reads back exact bytes from disk
             ├──► list_directory       ──► Lists directory tree & verifies metadata
             ├──► execute_cli_command  ──► Spawns non-blocking async process, returns stdout/code
             ├──► get_telemetry        ──► Live host CPU/RAM/GPU snapshot
             ├──► recommend_best_model ──► Evaluates RAM/VRAM against context requirements
             ├──► calculate_layer_offload ──► Computes GPU/CPU layer split
             └──► run_command          ──► Routes task through multi-lane priority scheduler
```

#### Detailed Test Verification Matrix:

| Tool Name | Input Payload | Verification Assertions |
|---|---|---|
| `write_code_file` | `path: "<tmp>/src/engine/mod.rs"`, `content: "pub fn init() -> bool { true }"` | `bytes_written > 0`, `status == "success"`. File exists on disk at path with exact content. Parent directory `<tmp>/src/engine` created. |
| `read_code_file` | `path: "<tmp>/src/engine/mod.rs"` | `content == "pub fn init() -> bool { true }"`, `bytes_read == content.len()`. Reading nonexistent file returns structured JSON-RPC error. |
| `list_directory` | `path: "<tmp>"` | Directory entries list includes `src` with `is_dir: true`. Directory entries for `src/engine` includes `mod.rs` with `is_dir: false` and `size_bytes > 0`. |
| `execute_cli_command` | `command: "echo test_exec"`, `cwd: "<tmp>"` | Non-blocking async execution. Returns `exit_code: 0`, `stdout` contains `"test_exec"`, `duration_ms > 0`. |
| `get_telemetry` | `{}` | `cpu.logical_core_count > 0`, `memory.total_ram_bytes > 0`, `memory.available_ram_bytes > 0`, `process.pid > 0`. |
| `recommend_best_model` | `context_tokens: 4096` | Returns recommendation decision with `model_id`, `tier` (e.g. `Small`, `Medium`, `Large`, or `CloudApiFallback`), and valid memory breakdown. |
| `calculate_layer_offload` | `model: "llama-3.1-8b"`, `vram_gb: 12.0` | `total_layers == 32`, `gpu_layers > 0`, `cpu_layers >= 0`, `gpu_layers + cpu_layers == 32`, `vram_allocated_bytes > 0`. |
| `run_command` | `command: "echo"`, `args: { "msg": "ide_event" }`, `priority: "High"` | Priority dispatch through scheduler. Returns `msg == "ide_event"`. |

---

### 4.3 Requirement 3: High-Concurrency Multi-Tab / Multi-Agent Stress Testing

#### Concurrency Scenario:
Simulate 4 concurrent IDE editor tabs, each with 8 parallel agent queries (total **32 simultaneous requests**), plus 4 background telemetry polling loops (total **36 concurrent in-flight JSON-RPC requests**).

#### Implementation Architecture:
```rust
#[tokio::test]
async fn test_high_concurrency_30_plus_simultaneous_tool_calls() {
    let harness = IdeTestHarness::spawn().await.unwrap();
    let client = harness.client();
    let total_concurrent = 36;
    let mut join_set = tokio::task::JoinSet::new();

    let start_time = std::time::Instant::now();

    for i in 0..total_concurrent {
        let c = client.clone();
        join_set.spawn(async move {
            match i % 4 {
                0 => {
                    // Telemetry Probe
                    c.call_tool("get_telemetry", None).await
                }
                1 => {
                    // Model Recommendation
                    c.call_tool("recommend_best_model", Some(json!({ "context_tokens": 4096 }))).await
                }
                2 => {
                    // Layer Offload Calculation
                    c.call_tool("calculate_layer_offload", Some(json!({ "model": "llama-3.1-8b", "vram_gb": 8.0 }))).await
                }
                _ => {
                    // Command Bus Execution
                    c.call_tool("run_command", Some(json!({ "command": "echo", "args": { "iter": i } }))).await
                }
            }
        });
    }

    let mut successful = 0;
    while let Some(res) = join_set.join_next().await {
        let tool_res = res.expect("Join error").expect("Tool call error");
        assert_eq!(tool_res.is_error, Some(false));
        successful += 1;
    }

    assert_eq!(successful, total_concurrent);
    let duration = start_time.elapsed();
    assert!(duration < Duration::from_secs(10), "36 concurrent requests took too long: {:?}", duration);
    harness.teardown().await;
}
```

#### Stress Invariants:
1. **Zero Timeouts**: Every request completes within a 10-second timeout window.
2. **Zero Deadlocks**: Concurrent worker threads do not starve or block each other.
3. **Zero Connection Drops**: Stdio line stream remains unbroken and synchronized.
4. **Data Isolation**: Response payload matches the specific arguments of each Request ID.

---

### 4.4 Requirement 4: Cooperative Cancellation & Error Recovery

#### Cancellation Architecture & Gap Analysis:
The specification states:
> "Verify that cancellation tokens sent from the IDE (`$/cancelRequest` / `notifications/cancelled`) immediately terminate in-flight shell processes and queue items without orphan leaks, and verify that invalid arguments or tool failures return structured JSON-RPC errors without crashing the server process."

#### 1. Cancellation Notification Gap:
In `crates/mcp-protocol/src/server.rs` line 164:
```rust
"notifications/cancelled" => {
    if let Some(params_val) = notif.params {
        if let Ok(cancel_notif) = serde_json::from_value::<CancelledNotification>(params_val) {
            if let Some((_, token)) = self.active_requests.remove(&cancel_notif.request_id) {
                token.cancel();
            }
        }
    }
}
```
`McpServer` only checks for `"notifications/cancelled"`. It does **not** recognize `"$/cancelRequest"` (which is standard in LSP and VS Code extensions).
*Proposed Fix*: In `McpServer::handle_notification`, match both `"notifications/cancelled"` and `"$/cancelRequest"`. Also in `McpServer::handle_request`, handle `"$/cancelRequest"` as a request returning `json!({})`.

#### 2. Process Cleanup on Cancellation:
In `execute_cli_command`:
- Currently `tokio::process::Command` does not have `.kill_on_drop(true)`.
- When cancellation occurs, the future is dropped, but the underlying OS process might continue running in Windows (`cmd /C`).
*Proposed Fix*: Add `.kill_on_drop(true)` to `tokio::process::Command` in `execute_cli`.

#### 3. Latency Verification (< 100ms):
```rust
#[tokio::test]
async fn test_in_flight_cancellation_within_100ms() {
    let harness = IdeTestHarness::spawn().await.unwrap();
    let client = harness.client();

    // 1. Dispatch a long-running tool call (sleep 5000ms)
    let req_id = RequestId::Int(999);
    let cancel_client = client.clone();

    let start_cancel = Arc::new(tokio::sync::Notify::new());
    let cancel_done = Arc::new(tokio::sync::Notify::new());
    let cancel_duration = Arc::new(parking_lot::Mutex::new(Duration::ZERO));

    // Background task sending the call
    let call_fut = tokio::spawn({
        let c = client.clone();
        let notify_start = start_cancel.clone();
        async move {
            notify_start.notify_one();
            c.call_tool("run_command", Some(json!({
                "command": "sleep",
                "args": { "duration_ms": 5000 }
            }))).await
        }
    });

    start_cancel.notified().await;
    tokio::time::sleep(Duration::from_millis(50)).await;

    // Send cancellation token
    let t0 = std::time::Instant::now();
    client.cancel_request(req_id, Some("IDE User Abort".into())).await.unwrap();
    let elapsed = t0.elapsed();

    // Verification: Cancellation dispatch completes in < 100ms
    assert!(elapsed < Duration::from_millis(100), "Cancellation took >100ms: {:?}", elapsed);

    // Call future should abort immediately without waiting 5000ms
    let res = tokio::time::timeout(Duration::from_millis(300), call_fut).await.expect("Call did not abort");
    
    // Server remains responsive
    let ping_res = client.ping().await;
    assert!(ping_res.is_ok(), "Server crashed or hung after cancellation");
    harness.teardown().await;
}
```

#### 4. Negative Testing & Fault Isolation:
- **Malformed JSON**: Send raw string `"{invalid-json\n"`. Verify transport recovers or emits JSON-RPC `-32700` (`ParseError`) without crashing the server process.
- **Unknown Method**: Send `{ "method": "invalid/method" }`. Verify response code `-32601` (`MethodNotFound`).
- **Schema Validation Rejection**: Send `write_code_file` without required `path` argument. Verify response code `-32602` (`InvalidParams`).
- **Liveness Proof**: Following all error injections, invoke `tools/list` and `read_code_file` to prove the server runtime remains healthy.

---

## 5. Test Organization & Cargo Test Execution

### 5.1 Single File vs. Modular Structure
**Recommendation**: Place the tests in a dedicated integration test file:
`crates/mcp-tests/tests/ide_mcp_integration.rs`

#### Rationale:
1. **Compilation Speed**: Compiling one test binary takes significantly less time than compiling 4 separate test binaries (linking in Rust workspace with 8 crates and Tokio/Axum takes ~15-20 seconds per binary).
2. **Cargo Convention**: `tests/ide_mcp_integration.rs` maps directly to a standalone integration test target recognized by `cargo test -p mcp-tests --test ide_mcp_integration`.
3. **Clean Modularity**: Sub-suites are cleanly divided inside the file into modules:
   - `mod test_r1_handshake_and_lifecycle;`
   - `mod test_r2_agent_tools_suite;`
   - `mod test_r3_concurrency_stress;`
   - `mod test_r4_cancellation_and_recovery;`
   - `mod test_sse_transport_integration;`
   - `mod harness;`

### 5.2 Cargo Test Command Line
The test suite can be run individually or as part of the workspace:
- Run IDE integration test suite alone:
  ```bash
  cargo test -p mcp-tests --test ide_mcp_integration -- --nocapture
  ```
- Run full test suite across workspace:
  ```bash
  cargo test --workspace --all-targets
  ```

---

## 6. Detailed Implementation Blueprint for `ide_mcp_integration.rs`

### 6.1 Shared In-Process & Out-of-Process Test Server Setup
To allow testing both the spawned child process (`mcp-cli`) and in-process servers with parity, create a shared server factory in `crates/mcp-cli` or `crates/mcp-tests`:

```rust
pub fn create_ide_mcp_server() -> (Arc<McpServer>, Arc<TaskDispatcher>, Arc<ResourceMonitor>) {
    let telemetry = Arc::new(EngineTelemetry::new());
    let config = EngineRuntimeConfig::new().worker_threads(4).compute_threads(2);
    let runtime = Arc::new(EngineRuntime::new(config).unwrap());
    let scheduler = Arc::new(MultiLaneScheduler::new(telemetry.clone()));
    let registry = Arc::new(CommandRegistry::new());

    // Register 7 builtin commands: echo, sleep, compute_hash, execute_cli, write_file, read_file, list_dir
    register_builtin_commands(&registry);

    let dispatcher = TaskDispatcher::new(
        registry.clone(),
        scheduler.clone(),
        runtime.clone(),
        telemetry.clone(),
        4,
    );
    let resource_monitor = Arc::new(ResourceMonitor::new(Duration::from_millis(100)));
    let mcp_server = Arc::new(setup_default_mcp_server(&dispatcher, &resource_monitor).unwrap());

    (mcp_server, dispatcher, resource_monitor)
}
```

### 6.2 Test Case Mapping Table

| AC Requirement | Test Identifier | Target Condition | Verification Check |
|---|---|---|---|
| **AC 1.1** | `test_r1_handshake_stdio_child_process` | `mcp-cli` child process stdio | Full handshake completes, protocolVersion negotiated to `2024-11-05`. |
| **AC 1.2** | `test_r1_schema_conformance` | `tools/list`, `resources/list`, `prompts/list` | All schemas conform to MCP 2024-11-05 spec. |
| **AC 1.3** | `test_r1_handshake_sse_server` | SSE transport stream + HTTP POST | Handshake & tool call over SSE session. |
| **AC 2.1** | `test_r2_write_and_read_code_file` | `write_code_file` + `read_code_file` | Recursive parent dirs created, exact byte fidelity read back. |
| **AC 2.2** | `test_r2_list_directory_inspection` | `list_directory` | Exact file entries, sizes, and directory flags verified. |
| **AC 2.3** | `test_r2_execute_cli_command_async` | `execute_cli_command` | Executes non-blockingly, captures exit code, duration, stdout. |
| **AC 2.4** | `test_r2_hardware_telemetry_and_model_routing` | `get_telemetry`, `recommend_best_model`, `calculate_layer_offload` | Returns live CPU/RAM/GPU, tier recommendation, and layer offload. |
| **AC 2.5** | `test_r2_priority_task_dispatch` | `run_command` | Dispatches task through multi-lane scheduler with priority order. |
| **AC 3.1** | `test_r3_high_concurrency_30_plus_calls` | 36 concurrent tool calls | 100% success rate, 0 deadlocks, 0 dropped connections. |
| **AC 4.1** | `test_r4_task_cancellation_within_100ms` | Cancellation during in-flight sleep | Abort latency < 100ms, no orphaned process. |
| **AC 4.2** | `test_r4_fault_isolation_and_recovery` | Malformed JSON & invalid tool | Structured JSON-RPC errors returned, server survives without crashing. |

---

## 7. Recommended Codebase Fixes Before Integration Suite Execution

During this investigation, three upstream source code defects were discovered that will directly impact the integration test harness if not resolved by the implementation agent:

1. **Fix `StdioStreamTransport::receive()`**:
   In `crates/mcp-protocol/src/transport/stdio.rs`, line 184:
   Change `if trimmed.is_empty() { return Ok(None); }` to loop until a non-empty line or EOF, preventing accidental server shutdown on blank lines.
2. **Fix `mcp-cli` Stderr Logging**:
   In `crates/mcp-cli/src/main.rs`:
   Configure `tracing_subscriber::fmt().with_writer(std::io::stderr)` and replace `println!` with `eprintln!` in `handle_mcp` so stdout remains pure JSON-RPC.
3. **Fix Support for `$/cancelRequest`**:
   In `crates/mcp-protocol/src/server.rs`:
   Add handler for `$/cancelRequest` in `handle_notification` (and in `handle_request` returning `{}`), so IDE clients using LSP-style cancellation tokens can abort in-flight requests.
4. **Fix `proc.kill_on_drop(true)` in `execute_cli`**:
   In `crates/mcp-cli/src/main.rs`:
   Set `proc.kill_on_drop(true)` so child shell processes are terminated immediately upon cancellation.
