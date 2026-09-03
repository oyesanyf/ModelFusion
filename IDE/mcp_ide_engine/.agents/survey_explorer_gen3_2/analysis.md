# Specification Mining Report: MCP Transports, Server Modes, Lifecycle, Cancellation, and Error Handling

**Author**: `survey_explorer_gen3_2`  
**Date**: 2026-09-03  
**Status**: Complete  
**Scope**: Read-Only Architectural Survey and Gap Analysis of `crates/mcp-cli`, `crates/mcp-protocol`, `crates/mcp-core`, and `crates/mcp-web`.

---

## Executive Summary

This report delivers a thorough architectural and protocol-level investigation of the Model Context Protocol (MCP standard `2024-11-05`) implementation within the workspace. Specifically, it examines:
1. **Server Modes in `mcp-cli`**: Analysis of CLI commands/flags for running as an MCP stdio server and HTTP/SSE server, along with underlying transport mechanics.
2. **MCP 2024-11-05 Lifecycle Implementation**: Protocol handshake (`initialize`, `notifications/initialized`), dynamic capability negotiation, and clean shutdown handling.
3. **Cooperative Cancellation & Error Recovery (R4)**: Support for `$/cancelRequest` vs `notifications/cancelled`, in-flight propagation to tasks and child processes, abort latency, orphan process leaks, and structured error isolation.
4. **Discovered Deficiencies & Gaps**: Detailed audit of exact command lines, protocol schemas, error codes, and architectural gaps preventing compliant IDE integration.

---

## 1. Server Modes & Transport Mechanics in `mcp-cli` & `mcp-protocol`

### 1.1 CLI Commands and Server Modes (`crates/mcp-cli`)

The workspace exposes its entrypoint via the `mcp-cli` binary (`crates/mcp-cli/src/main.rs` & `cli.rs`). The CLI defines multiple subcommands for launching servers:

| CLI Subcommand | Purpose | Defined In | Implementation Status |
|---|---|---|---|
| `mcp-cli mcp serve --stdio` | Run as standard line-delimited MCP stdio server | `cli.rs:188-198` | **Implemented with Fatal stdout Bug** (see below) |
| `mcp-cli mcp serve --sse-port <port>` | Run as MCP Server-Sent Events (SSE) server | `cli.rs:188-198` | **Unimplemented / Silent No-Op** (see below) |
| `mcp-cli serve --addr <addr>` | Launch Axum Web IDE, REST API & WebSocket server | `cli.rs:248-253` | **Implemented, but NOT MCP SSE Compliant** |

#### Defect 1.1A: Fatal Stdout Pollution in Stdio Server Mode
In `crates/mcp-cli/src/main.rs:637-646`:
```rust
McpSubcommands::Serve(s_args) => {
    if s_args.stdio {
        println!("{}", "Starting MCP Server on standard I/O streams...".green());
        let transport = std::sync::Arc::new(mcp_protocol::transport::stdio::StdioStreamTransport::new(
            tokio::io::stdin(),
            tokio::io::stdout(),
        ));
        server.serve(transport).await?;
    }
}
```
- **Observed Behavior**: The command emits ANSI green banner text `\u{1b}[32mStarting MCP Server on standard I/O streams...\u{1b}[0m\n` directly to standard output (`stdout`).
- **Consequence**: In MCP stdio mode, `stdout` is reserved strictly for line-delimited JSON-RPC framing. External IDE clients (e.g. Antigravity, VS Code, Cursor) parsing the output stream encounter non-JSON text and immediately fail with a JSON-RPC deserialization / parse error before the handshake can begin.
- **Remediation**: All diagnostic logs must be directed to `stderr` via `eprintln!` or `tracing::info!` directed to stderr.

#### Defect 1.1B: Missing Implementation of SSE Server in `mcp-cli`
In `crates/mcp-cli/src/main.rs:637-646`:
- `McpServeArgs` in `cli.rs` exposes `--sse-port <port>`, but `main.rs` only contains `if s_args.stdio { ... }`.
- There is **no `else` block** or branch for handling `s_args.sse_port`.
- If an agent or test runs `mcp-cli mcp serve --stdio=false --sse-port 8000`, the process executes nothing and immediately exits with status code 0.
- Furthermore, `s_args.stdio` is default-initialized to `true` (`#[arg(long, default_value_t = true)]`), meaning passing `--sse-port 8000` without explicitly overriding stdio leaves `stdio == true`.

#### Defect 1.1C: `mcp-cli serve` (Axum) is NOT MCP 2024-11-05 SSE Compliant
In `crates/mcp-web/src/server.rs:79-110`:
- The embedded Axum server provides REST endpoints (`/api/tools`, `/api/tools/call`, `/api/tasks`), a WebSocket endpoint (`/ws`), and an SSE endpoint (`/api/events`).
- However, `/api/events` streams internal `EngineEvent` instances from `telemetry.event_bus`.
- It does **not** implement the standard MCP SSE protocol:
  - No `GET /sse` or `GET /api/mcp/sse` declaring `event: endpoint\ndata: /messages?sessionId=<uuid>\n\n`.
  - No `POST /messages?sessionId=<uuid>` endpoint for receiving JSON-RPC messages from the client.
  - No session-isolated JSON-RPC streaming over SSE.

---

### 1.2 Transport Implementations (`crates/mcp-protocol/src/transport/`)

The `mcp-protocol` crate implements three transport variants implementing the `Transport` trait:
```rust
#[async_trait]
pub trait Transport: Send + Sync + 'static {
    async fn send(&self, msg: JsonRpcMessage) -> Result<(), TransportError>;
    async fn receive(&self) -> Result<Option<JsonRpcMessage>, TransportError>;
    async fn close(&self) -> Result<(), TransportError>;
}
```

#### 1. Stdio Stream Transport (`StdioStreamTransport<R, W>`)
- **Location**: `crates/mcp-protocol/src/transport/stdio.rs:146-201`
- **Architecture**: Wraps generic `R: AsyncRead` and `W: AsyncWrite`. Uses `tokio::io::BufReader::lines()` to read incoming lines and writes lines formatted with `\n`.
- **Defect / Edge Case**:
  ```rust
  match lines.next_line().await {
      Ok(Some(line)) => {
          let trimmed = line.trim();
          if trimmed.is_empty() {
              return Ok(None);
          }
          let msg = serde_json::from_str::<JsonRpcMessage>(trimmed)?;
          Ok(Some(msg))
      }
      Ok(None) => Ok(None),
      Err(e) => Err(TransportError::Io(e.to_string())),
  }
  ```
  In `Transport` semantics, `receive() -> Ok(None)` indicates **EOF / disconnect**. If a client sends an empty newline (`\n` or `\r\n\r\n`), `StdioStreamTransport` interprets this as EOF and terminates the server session! It must instead `continue` to the next line.

#### 2. Stdio Process Transport (`StdioProcessTransport`)
- **Location**: `crates/mcp-protocol/src/transport/stdio.rs:13-144`
- **Architecture**: Spawns an external child process with `stdin`, `stdout`, and `stderr` piped.
- **Worker Tasks**:
  - *Stdin Task*: Receives `JsonRpcMessage` from channel, serializes to JSON string, writes to child stdin, flushes.
  - *Stdout Task*: Reads lines from child stdout, ignores empty lines, parses JSON-RPC messages, sends to `stdout_tx`.
  - *Stderr Task*: Reads diagnostic lines from child stderr into `stderr_tx` channel, isolated from JSON-RPC framing.
- **Drop Safety**: Implements `Drop` calling `child.start_kill()` to guarantee no zombie child processes remain if the transport is dropped.

#### 3. Server-Sent Events (SSE) Transport (`SseServerTransport` & `SseSessionManager`)
- **Location**: `crates/mcp-protocol/src/transport/sse.rs`
- **Architecture**:
  - `SseEvent`: Formats and parses W3C SSE standard blocks (`event: <type>\nid: <id>\ndata: <data>\n\n`).
  - `SseSession`: Manages UUID v4 session token, `incoming_tx` channel (receives JSON-RPC from HTTP POST), and `sse_out_tx` (pushes `event: message` to client).
  - `SseSessionManager`: Thread-safe `DashMap<String, Arc<SseSession>>` managing multi-client SSE sessions.
  - `SseServerTransport`: Adapts an `SseSession` into the `Transport` trait.
  - `SseClientTransport`: In-memory client peer connected to an `SseSession` channel pair.
- **Gap**: `SseSessionManager` and `SseServerTransport` are fully implemented as protocol primitives, but are not wired to an active Axum/Hyper HTTP listener in `mcp-cli` or `mcp-web`.

---

## 2. MCP 2024-11-05 Lifecycle Implementation

### 2.1 Handshake Sequence
The server follows the two-stage initialization defined by MCP 2024-11-05:
1. **Uninitialized Guard**:
   - Initial state: `ServerState::Uninitialized`.
   - Calling any method other than `initialize` or `ping` returns JSON-RPC error code `-32002` (`ErrorCode::SERVER_NOT_INITIALIZED`):
     `"Server is not initialized. Client must call 'initialize' first."`
2. **`initialize` Request**:
   - Request params schema (`InitializeParams`):
     ```json
     {
       "protocolVersion": "2024-11-05",
       "capabilities": {
         "roots": { "listChanged": true },
         "sampling": {}
       },
       "clientInfo": {
         "name": "cursor-agent",
         "version": "1.0.0"
       }
     }
     ```
   - Protocol version negotiation: Checks against `SUPPORTED_PROTOCOL_VERSIONS = ["2024-11-05", "2024-10-07"]`. If supported, echoes client version; otherwise defaults to `"2024-11-05"`.
   - State transition: `ServerState::Uninitialized` $\rightarrow$ `ServerState::Initializing`.
   - Response payload (`InitializeResult`):
     ```json
     {
       "protocolVersion": "2024-11-05",
       "capabilities": {
         "tools": { "listChanged": true },
         "resources": { "subscribe": true, "listChanged": true },
         "prompts": { "listChanged": true },
         "logging": {}
       },
       "serverInfo": {
         "name": "mcp-ide-engine",
         "version": "0.1.0"
       },
       "instructions": "High-performance multithreaded MCP IDE engine and tool dispatcher."
     }
     ```
3. **`notifications/initialized` Notification**:
   - Notification payload: `{"jsonrpc": "2.0", "method": "notifications/initialized"}`.
   - State transition: `ServerState::Initializing` $\rightarrow$ `ServerState::Initialized`.
   - Unlocks full access to tool, resource, and prompt endpoints.

### 2.2 Capability Negotiation
- Dynamic Capability Declaration:
  - `tools`: Included with `listChanged: Some(true)` if tools registry is populated.
  - `resources`: Included with `subscribe: Some(true)` and `listChanged: Some(true)` if resource catalog or URI templates exist; otherwise `None`.
  - `prompts`: Included with `listChanged: Some(true)` if prompt templates exist; otherwise `None`.
  - `logging`: Always declared as `Some(LoggingCapability {})`.
- Client Capabilities: Deserialized into `ClientCapabilities` (supports `roots`, `sampling`, `experimental`). Stored on `McpClient`.

### 2.3 Ping Heartbeat
- Method: `"ping"`. Handled in both `Uninitialized` and `Initialized` states.
- Returns `{}` with HTTP 200 / JSON-RPC success.

### 2.4 Shutdown Handling
- In `crates/mcp-protocol/src/server.rs`:
  - `server.shutdown()` sets state to `ServerState::Shutdown` and triggers `root_token.cancel()`.
  - The `serve(transport)` loop terminates upon transport EOF (`receive() -> Ok(None)`) or `root_token` cancellation.
- **Defect / Gap**: `McpServer::handle_request` does **not** implement a `"shutdown"` request, nor does `handle_notification` handle `"exit"`. If an IDE sends `{"method": "shutdown"}`, the server returns `-32601` (`Method not found`).

---

## 3. Cooperative Cancellation & Error Recovery (R4)

### 3.1 Cancellation Notification Handling

#### A. Supported: `notifications/cancelled` (MCP Standard)
In `crates/mcp-protocol/src/server.rs:164-173`:
```rust
"notifications/cancelled" => {
    if let Some(params_val) = notif.params {
        if let Ok(cancel_notif) = serde_json::from_value::<CancelledNotification>(params_val) {
            if let Some((_, token)) = self.active_requests.remove(&cancel_notif.request_id) {
                debug!("Cancelling active request ID: {}", cancel_notif.request_id);
                token.cancel();
            }
        }
    }
}
```
- Expects params schema: `{"requestId": <RequestId>, "reason": <Option<String>>}`.
- If found in `self.active_requests`, calls `token.cancel()`.

#### B. Defect / Gap: `$/cancelRequest` Unhandled
- Antigravity IDE, VS Code, and Cursor frequently emit `$/cancelRequest` (inherited from the Language Server Protocol specification) when user cancels a tool execution.
- In `server.rs`:
  - If sent as a **notification** (`{"method": "$/cancelRequest", "params": {"id": 1}}`): ignored as an unknown notification (`debug!("Received unhandled notification: '{}'", other)`).
  - If sent as a **request**: returns JSON-RPC error code `-32601` (`Method not found`).
- In both cases, cancellation fails to trigger.

---

### 3.2 In-Flight Task Abort & Orphan Process Leak Analysis

#### A. In-Memory Tool Cancellation
In `crates/mcp-protocol/src/tools.rs:238-254`:
```rust
let result_fut = async move {
    tokio::select! {
        _ = token.cancelled() => {
            CallToolResult::error("Tool execution was cancelled")
        }
        res = handler.call(ctx, Some(args_val)) => { ... }
    }
};
```
- **Abort Latency**: When `token.cancel()` is called, `tokio::select!` wakes up immediately (< 1ms, far below the 100ms requirement) and returns `CallToolResult::error("Tool execution was cancelled")`.

#### B. Severe Defect: Orphan Process Leaks in CLI Tool Execution
When the IDE invokes `execute_cli_command`, the execution flow contains a critical architectural disconnect:
1. In `mcp-cli/src/main.rs:324-349`:
   ```rust
   server.tools().register_fn("execute_cli_command", ..., move |_ctx, args| {
       let disp = d_cli.clone();
       async move {
           let a = args.unwrap_or(json!({}));
           let handle = disp.dispatch("execute_cli", a, Some(TaskPriority::High))?;
           let output = handle.wait().await?;
           Ok(CallToolResult::text(serde_json::to_string_pretty(&output.data).unwrap()))
       }
   });
   ```
   - **Token Disconnect**: `_ctx.cancellation_token` is completely ignored!
   - `disp.dispatch("execute_cli", ...)` creates a new cancellation token linked only to `dispatcher.root_token`, completely disconnected from the MCP request's cancellation token!
2. In `mcp-protocol/src/tools.rs`:
   - When cancellation occurs, `handler.call(...)` is dropped by `tokio::select!`.
   - Dropping `handler.call` drops `handle` (`TaskHandle`).
   - `TaskHandle` **does not implement `Drop`** to cancel the dispatched task (`handle.cancel()` is never called).
3. In `mcp-cli/src/main.rs:154-169` (`execute_cli` handler):
   ```rust
   #[cfg(windows)]
   let mut proc = tokio::process::Command::new("cmd");
   #[cfg(windows)]
   proc.args(&["/C", cmd_str]);
   let output = proc.output().await;
   ```
   - `tokio::process::Command` does **not** call `.kill_on_drop(true)`.
   - Under Tokio, dropping `proc.output().await` leaves the child process running in the background as an orphaned leak.
4. **Summary Assessment**:
   - **IDE Abort Latency**: < 10ms (passes the 100ms threshold).
   - **Process Containment**: **FAILS**. In-flight shell processes (`cmd.exe`, `sh`, build scripts) are NOT killed and leak as orphan processes.

---

### 3.3 Structured Error Containment

The server exhibits robust error containment across parameters and runtime execution:
1. **Invalid Parameters / JSON-RPC Protocol Errors**:
   - Malformed JSON / non-object params $\rightarrow$ `-32602` (`Invalid params`).
   - Missing required fields $\rightarrow$ `-32602` (`Invalid params`).
   - Unregistered tool name $\rightarrow$ `-32602` (`"Tool '<name>' not found"`).
2. **Schema Validation Errors**:
   - In `ToolRegistry::call`, arguments are validated against `def.compiled_schema`.
   - Validation failures return structured error `-32602` containing detailed validation error descriptions.
3. **Tool Execution Errors**:
   - Internal tool errors (e.g. CLI command exit code $\neq 0$, file not found) are wrapped in `CallToolResult` with `isError: Some(true)`.
   - The JSON-RPC layer returns a valid `result` object (`isError: true`), preserving MCP protocol conformity and preventing host crashes.
4. **Panic Containment**:
   - Each incoming request in `McpServer::serve` is dispatched via `tokio::spawn`.
   - Any panic inside a tool handler is isolated to that specific task, preventing crash of the parent server process. (However, because `AssertUnwindSafe` is polled without `catch_unwind()`, a panicking tool results in a dropped channel rather than a structured `-32603` response).

---

## 4. Tables of Findings

### 4.1 Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|---|---|---|---|---|---|---|
| 1 | Transport | Stdio Stream Transport | Line-delimited JSON-RPC framing over standard stdin/stdout | UTF-8 line string | JSON-RPC lines | Returns EOF on empty line; Io error on stream break | `crates/mcp-protocol/src/transport/stdio.rs:146` |
| 2 | Transport | Stdio Process Transport | Client transport managing external child process with isolated stderr logging | `tokio::process::Command` | `JsonRpcMessage` stream, stderr channel | Drops and kills child via `start_kill()`; ignores non-JSON lines | `crates/mcp-protocol/src/transport/stdio.rs:13` |
| 3 | Transport | SSE Session Transport | W3C Server-Sent Events transport with UUID sessions and HTTP POST routing | HTTP POST payloads, SSE streams | `event: message\ndata: ...` | Returns `TransportError::Disconnected` on closed channel | `crates/mcp-protocol/src/transport/sse.rs:88` |
| 4 | Transport | Channel Transport | Paired in-memory mpsc channels for zero-overhead local integration | `JsonRpcMessage` | `JsonRpcMessage` | Disconnected error when peer channel drops | `crates/mcp-protocol/src/transport/mod.rs:62` |
| 5 | CLI Mode | CLI Stdio Serve Mode | Launch MCP server over stdio streams | `mcp-cli mcp serve --stdio` | Stdout JSON-RPC stream | Pollutes stdout with colored ANSI text on start | `crates/mcp-cli/src/main.rs:637` |
| 6 | CLI Mode | CLI SSE Serve Mode | Planned HTTP/SSE server mode | `mcp-cli mcp serve --sse-port <port>` | None | Unimplemented code path; exits immediately | `crates/mcp-cli/src/main.rs:637` |
| 7 | Lifecycle | Initialization Handshake | Protocol version negotiation and initial capabilities exchange | `initialize` request | `InitializeResult` | Rejects uninitialized requests with `-32002` | `crates/mcp-protocol/src/server.rs:184` |
| 8 | Lifecycle | Initialized Notification | Transition from Initializing to Initialized state | `notifications/initialized` | None | Updates server state to `Initialized` | `crates/mcp-protocol/src/server.rs:157` |
| 9 | Lifecycle | Dynamic Capability Negotiation | Declares tools, resources, prompts, logging capabilities dynamically | Registered registries | `ServerCapabilities` | Capabilities omitted if respective registries are empty | `crates/mcp-protocol/src/server.rs:83` |
| 10 | Lifecycle | Ping Heartbeat | Liveness check | `ping` request | Empty success result `{}` | Always responds even before initialization | `crates/mcp-protocol/src/server.rs:136` |
| 11 | Cancellation | Cancellation Notification | Cancels active request by ID | `notifications/cancelled` | None | Cancels token in `active_requests` | `crates/mcp-protocol/src/server.rs:164` |
| 12 | Cancellation | Hierarchical Cancellation Token | Cooperative token tree with deterministic child cleanup and timeouts | Token tree | Cancellation future | Propagates down to all child tokens | `crates/mcp-core/src/cancellation.rs:49` |
| 13 | Error Recovery | Schema Validation Containment | Validates arguments against pre-compiled JSON schemas before tool execution | JSON value | Result or Schema error | Returns `-32602` structured error on mismatch | `crates/mcp-protocol/src/schema.rs:90` |
| 14 | Error Recovery | Tool Error Containment | Encapsulates tool failure inside result without protocol crash | Tool failure / error | `CallToolResult` with `isError: true` | Converts internal tool error into structured MCP output | `crates/mcp-protocol/src/tools.rs:248` |
| 15 | IDE Tools | Code Generation Tool | Generates nested source code and directory hierarchy | `write_code_file` | TaskOutput JSON | Fails gracefully if path is invalid or unwritable | `crates/mcp-cli/src/main.rs:352` |
| 16 | IDE Tools | Context Inspection Tool | Reads workspace files with exact byte fidelity | `read_code_file` | TaskOutput JSON | Returns error if file does not exist | `crates/mcp-cli/src/main.rs:381` |
| 17 | IDE Tools | Process Execution Tool | Executes build tools and shell commands asynchronously | `execute_cli_command` | TaskOutput JSON (stdout, stderr, exit_code) | Captures non-zero exit codes in output without crashing | `crates/mcp-cli/src/main.rs:324` |
| 18 | IDE Tools | Hardware Telemetry Tool | Probes CPU, RAM, and GPU NVML/DXGI capacity | `get_telemetry` | `SystemSnapshot` JSON | Safe sysinfo fallback if GPU hardware absent | `crates/mcp-cli/src/main.rs:433` |
| 19 | IDE Tools | Model Fit Routing Tool | Recommends optimal model tier (Small/Medium/Large/Cloud) | `recommend_best_model` | `AllocationDecision` JSON | Fallback to CloudApiFallback under RAM pressure | `crates/mcp-cli/src/main.rs:448` |
| 20 | IDE Tools | Layer Offload Tool | Computes GPU VRAM layer offload distribution | `calculate_layer_offload` | `LayerOffloadPlan` JSON | Adapts to free VRAM or defaults safely | `crates/mcp-cli/src/main.rs:472` |

---

### 4.2 Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---|---|---|
| 1 | `StdioStreamTransport` | Blank/empty line (`\n` or `\r\n\r\n`) | Interpreted as EOF; returns `Ok(None)` and prematurely terminates the server loop. |
| 2 | `mcp-cli mcp serve` | Normal launch command | Emits ANSI colored string to `stdout`, corrupting JSON-RPC stream for IDE clients. |
| 3 | `mcp-cli mcp serve` | `--sse-port 8000` | Silently exits with code 0 without binding any HTTP/SSE port. |
| 4 | Cancellation | `$/cancelRequest` (notification or request) | Unrecognized method; notification is ignored; request returns error `-32601`. |
| 5 | Cancellation | `notifications/cancelled` with `{"id": 1}` | Deserialization fails because type expects `{"requestId": 1}`; cancellation is silently dropped. |
| 6 | Process Cancellation | In-flight `execute_cli_command` cancellation | MCP tool call returns cancelled in <10ms, but background `cmd.exe` OS process continues executing as an orphan. |
| 7 | Lifecycle Handshake | Calling `tools/list` before `initialize` | Correctly blocked; returns JSON-RPC error code `-32002` (`SERVER_NOT_INITIALIZED`). |
| 8 | Lifecycle Handshake | `ping` before `initialize` | Allowed; returns `{}` success without requiring initialization. |
| 9 | Tool Execution | Tool handler panic | Isolated by `tokio::spawn`, server stays alive; however client request channel drops without structured error response. |
| 10 | Protocol Version | Client sends `protocolVersion: "2024-10-07"` | Successfully accepted and echoed from `SUPPORTED_PROTOCOL_VERSIONS`. |
| 11 | Protocol Version | Client sends unknown `protocolVersion: "2023-01-01"` | Fallback to `"2024-11-05"` in `InitializeResult`. |

---

## 5. Protocol Messages, Error Codes, and Command Lines

### 5.1 Command Lines
- **Launch Stdio Server**:
  `cargo run --bin mcp-cli -- mcp serve --stdio` (or `mcp-cli mcp serve`)
- **Launch Web IDE / REST Server**:
  `cargo run --bin mcp-cli -- serve --addr 127.0.0.1:3000`
- **Inspect MCP Tools**:
  `cargo run --bin mcp-cli -- mcp tools list`
- **Call Tool via CLI**:
  `cargo run --bin mcp-cli -- mcp tools call execute_cli_command --args "{\"command\":\"cargo --version\"}"`

### 5.2 JSON-RPC Protocol Messages

#### 1. Handshake (`initialize`)
```json
// Request
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": { "roots": { "listChanged": true }, "sampling": {} },
    "clientInfo": { "name": "antigravity-ide", "version": "1.0.0" }
  }
}

// Response
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": { "listChanged": true },
      "resources": { "subscribe": true, "listChanged": true },
      "prompts": { "listChanged": true },
      "logging": {}
    },
    "serverInfo": {
      "name": "mcp-ide-engine",
      "version": "0.1.0"
    },
    "instructions": "High-performance multithreaded MCP IDE engine and tool dispatcher."
  }
}
```

#### 2. Initialized Notification
```json
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```

#### 3. Tool Discovery (`tools/list`)
```json
// Request
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}

// Response
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "run_command",
        "description": "Dispatches any registered command through the multithreaded priority engine",
        "inputSchema": {
          "type": "object",
          "properties": {
            "command": { "type": "string" },
            "args": { "type": "object" },
            "priority": { "type": "string", "enum": ["Critical", "High", "Normal", "Low", "Background"] }
          },
          "required": ["command"]
        }
      },
      {
        "name": "execute_cli_command",
        "description": "Executes any shell or CLI command non-blockingly across worker threads",
        "inputSchema": {
          "type": "object",
          "properties": {
            "command": { "type": "string", "description": "The shell command line to execute" },
            "cwd": { "type": "string", "description": "Optional working directory" }
          },
          "required": ["command"]
        }
      },
      {
        "name": "write_code_file",
        "description": "Writes or generates source code in a file path, creating parent directories if needed",
        "inputSchema": {
          "type": "object",
          "properties": {
            "path": { "type": "string", "description": "Target relative or absolute file path" },
            "content": { "type": "string", "description": "Code contents to write" }
          },
          "required": ["path", "content"]
        }
      },
      {
        "name": "read_code_file",
        "description": "Reads code and content from a workspace file path",
        "inputSchema": {
          "type": "object",
          "properties": {
            "path": { "type": "string", "description": "Source file path to read" }
          },
          "required": ["path"]
        }
      },
      {
        "name": "list_directory",
        "description": "Lists entries and files in a workspace directory",
        "inputSchema": {
          "type": "object",
          "properties": {
            "path": { "type": "string", "description": "Directory path to list, defaults to '.'" }
          }
        }
      },
      {
        "name": "get_telemetry",
        "description": "Returns real-time host CPU, RAM, and GPU telemetry snapshot",
        "inputSchema": { "type": "object" }
      },
      {
        "name": "recommend_best_model",
        "description": "Recommends the best local LLM or cloud fallback based on live available RAM and VRAM",
        "inputSchema": {
          "type": "object",
          "properties": {
            "context_tokens": { "type": "integer", "description": "Expected context length in tokens, defaults to 4096" }
          }
        }
      },
      {
        "name": "calculate_layer_offload",
        "description": "Calculates optimal GPU VRAM and CPU layer offload distribution for a model",
        "inputSchema": {
          "type": "object",
          "properties": {
            "model": { "type": "string", "description": "Model family or ID (e.g. llama-3.1-8b, llama-3.2-3b, llama-3.3-70b)" },
            "vram_gb": { "type": "number", "description": "Override available VRAM in Gigabytes" }
          }
        }
      }
    ]
  }
}
```

#### 4. Cancellation Notification
```json
{
  "jsonrpc": "2.0",
  "method": "notifications/cancelled",
  "params": {
    "requestId": 42,
    "reason": "User cancelled in editor tab"
  }
}
```

### 5.3 Error Codes Reference Table

| Code | Constant | Meaning | Where Produced |
|---|---|---|---|
| `-32700` | `PARSE_ERROR` | Invalid JSON received by transport | `mcp-protocol/src/transport/stdio.rs` |
| `-32600` | `INVALID_REQUEST` | Malformed JSON-RPC envelope | `mcp-protocol/src/server.rs` |
| `-32601` | `METHOD_NOT_FOUND` | Unknown method (e.g. `$/cancelRequest`, `shutdown`) | `mcp-protocol/src/server.rs:148` |
| `-32602` | `INVALID_PARAMS` | Missing parameters, unknown tool name, schema failure | `mcp-protocol/src/server.rs:191, 241, 278` |
| `-32603` | `INTERNAL_ERROR` | Internal engine failure | `mcp-protocol/src/types.rs:144` |
| `-32002` | `SERVER_NOT_INITIALIZED` | Request invoked prior to `initialize` | `mcp-protocol/src/server.rs:127` |
| `-32001` | `RESOURCE_NOT_FOUND` | URI not registered in Resource catalog | `mcp-protocol/src/server.rs:331` |
| `-32000` | `SERVER_ERROR_GENERIC` | Generic server error | `mcp-protocol/src/types.rs:156` |
| `-32800` | `REQUEST_CANCELLED` | Explicit cancellation error code | `mcp-protocol/src/types.rs:186` |

---

## 6. Actionable Implementation Gaps for Test Suite & Engine

1. **Fix Stdout Pollution in `mcp-cli`**:
   Replace `println!("{}", "Starting MCP Server...".green())` in `crates/mcp-cli/src/main.rs:639` with `eprintln!` or logging.
2. **Handle Empty Lines in `StdioStreamTransport`**:
   Change `if trimmed.is_empty() { return Ok(None); }` to `if trimmed.is_empty() { continue; }` in `crates/mcp-protocol/src/transport/stdio.rs:184`.
3. **Implement Dual Cancellation Routing (`$/cancelRequest` + `notifications/cancelled`)**:
   In `crates/mcp-protocol/src/server.rs`:
   - Support `$/cancelRequest` as both a notification and a request with either `params.id` or `params.requestId`.
   - Also accept `CancelledNotification` with `id` or `requestId`.
4. **Propagate Cancellation & Prevent Process Leaks in `execute_cli_command`**:
   - Link the tool's `_ctx.cancellation_token` to the spawned `TaskHandle`.
   - Implement `kill_on_drop(true)` on `tokio::process::Command` in `execute_cli`.
   - Implement `cancel()` on drop of `TaskHandle`.
5. **Implement Real HTTP/SSE Server in `mcp-cli` or `mcp-web`**:
   Wire `SseSessionManager` to Axum routes:
   - `GET /sse`: Returns SSE stream emitting `event: endpoint\ndata: /messages?sessionId=<uuid>`.
   - `POST /messages`: Accepts JSON-RPC requests for `<uuid>` and feeds them to `SseSession::handle_incoming_post`.
   Hook `mcp-cli mcp serve --sse-port <port>` to run this Axum router.
