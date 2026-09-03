# Model Context Protocol (MCP) Specification Analysis & Engineering Blueprint

**Document Version:** 1.0.0  
**Target Specification Standard:** MCP Protocol Version `2024-11-05`  
**Host Architecture:** Rust Multithreaded Async Engine (`tokio`)  
**Dual Role:** MCP Client (Orchestrator of external servers) & MCP Server (Exposer of IDE & host tools)

---

## Executive Summary

The Model Context Protocol (MCP) is an open standard protocol enabling AI applications (Clients/Hosts) and external tools/data sources (Servers) to communicate over structured JSON-RPC 2.0. In the `mcp_ide_engine`, MCP serves as both:
1. **The Core Integration Fabric (Client Role):** Connecting the IDE engine to arbitrary external MCP servers (e.g. Postgres, Git, GitHub, Filesystem, Memory, Custom CLI servers) across `stdio` child processes and `HTTP/SSE` remote endpoints.
2. **The Extensibility Surface (Server Role):** Exposing the engine's multithreaded task runner, hardware telemetry, model routing, and IDE workspace primitives to external AI agents and clients (e.g., Claude Desktop, Cursor, Zed, Web IDE clients).

To achieve **sub-millisecond dispatch overhead**, the engine relies on async lock-free tool routing, compiled JSON schemas, non-blocking I/O with Tokio framing, and zero-allocation message parsing.

---

## 1. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Transport | Stdio Transport | Line-delimited JSON-RPC 2.0 streaming over process stdin/stdout | UTF-8 JSON lines on `stdin` | UTF-8 JSON lines on `stdout` | UTF-8 logs on `stderr`; Process exit code on termination | MCP Spec & RFC 8259 |
| 2 | Transport | HTTP/SSE Transport | Bi-directional transport using Server-Sent Events for server->client and HTTP POST for client->server | `GET /sse` (SSE connection), `POST /message?sessionId=<id>` (JSON-RPC payload) | `event: endpoint` with POST URI; `event: message` with JSON-RPC payload; `202 Accepted` on POST | HTTP 400 (Bad Request), 404 (Session Not Found), 500 (Internal Error) | MCP Spec 2024-11-05 |
| 3 | Lifecycle | Initialize Handshake | Version negotiation and capability declaration between client and server | `initialize` request: `protocolVersion`, `capabilities`, `clientInfo` | `InitializeResult`: `protocolVersion`, `capabilities`, `serverInfo`, `instructions` | `-32002` (Server not initialized), `-32602` (Incompatible version) | MCP Spec 2024-11-05 |
| 4 | Lifecycle | Initialized Notification | Client signals initialization completion; server transitions to active state | `notifications/initialized` notification (empty params) | None (Notification) | Drop connection if received out-of-order or duplicate | MCP Spec 2024-11-05 |
| 5 | Lifecycle | Ping / Liveness Check | Heartbeat mechanism to test transport and server liveness | `ping` request (`{}`) | Empty result (`{}`) | Request timeout if unresponsive | MCP Spec 2024-11-05 |
| 6 | Tools | `tools/list` | Enumerates available tools with input JSON schemas and pagination | `cursor` (optional pagination token) | `tools`: array of `Tool` objects (`name`, `description`, `inputSchema`), `nextCursor` | `-32603` Internal error if registry query fails | MCP Spec 2024-11-05 |
| 7 | Tools | `tools/call` | Executes a registered tool with argument validation and progress tracking | `name`: string, `arguments`: object, `_meta.progressToken` (optional) | `content`: array of `TextContent` / `ImageContent` / `EmbeddedResource`, `isError`: boolean | JSON-RPC error for protocol/validation failure; `isError: true` inside result for runtime tool failure | MCP Spec 2024-11-05 |
| 8 | Tools | `notifications/tools/list_changed` | Server notifies client that the tool catalog has been updated | None | None (Notification) | Ignored if client lacks tool capability | MCP Spec 2024-11-05 |
| 9 | Resources | `resources/list` | Enumerates static resources exposed by server | `cursor` (optional pagination token) | `resources`: array of `Resource` (`uri`, `name`, `description`, `mimeType`, `size`), `nextCursor` | `-32603` Internal error | MCP Spec 2024-11-05 |
| 10 | Resources | `resources/templates/list` | Enumerates dynamic RFC 6570 URI templates for parametric resources | `cursor` (optional pagination token) | `resourceTemplates`: array of `ResourceTemplate` (`uriTemplate`, `name`, `description`, `mimeType`), `nextCursor` | `-32603` Internal error | MCP Spec 2024-11-05 |
| 11 | Resources | `resources/read` | Reads the content of a specific resource by URI | `uri`: string (RFC 3986 URI) | `contents`: array of `TextResourceContents` or `BlobResourceContents` (base64) | `-32002` Resource not found, `-32602` Invalid URI | MCP Spec 2024-11-05 |
| 12 | Resources | `resources/subscribe` | Registers client interest in updates to a specific resource URI | `uri`: string | Empty result (`{}`) | `-32002` Resource not found | MCP Spec 2024-11-05 |
| 13 | Resources | `resources/unsubscribe` | Unregisters client interest in updates to a resource URI | `uri`: string | Empty result (`{}`) | `-32002` Subscription not found | MCP Spec 2024-11-05 |
| 14 | Resources | `notifications/resources/updated` | Server notifies client that a subscribed resource's content has changed | `uri`: string | None (Notification) | Client refreshes resource via `resources/read` | MCP Spec 2024-11-05 |
| 15 | Resources | `notifications/resources/list_changed` | Server notifies client that the resource list has changed | None | None (Notification) | Client invalidates resource cache | MCP Spec 2024-11-05 |
| 16 | Prompts | `prompts/list` | Enumerates pre-configured prompt templates with arguments | `cursor` (optional pagination token) | `prompts`: array of `Prompt` (`name`, `description`, `arguments`), `nextCursor` | `-32603` Internal error | MCP Spec 2024-11-05 |
| 17 | Prompts | `prompts/get` | Renders a prompt template with provided argument values | `name`: string, `arguments`: key-value map | `description`: string, `messages`: array of `PromptMessage` (`role`, `content`) | `-32002` Prompt not found, `-32602` Missing required arguments | MCP Spec 2024-11-05 |
| 18 | Prompts | `notifications/prompts/list_changed` | Server notifies client that available prompts have changed | None | None (Notification) | Client invalidates prompt cache | MCP Spec 2024-11-05 |
| 19 | Sampling | `sampling/createMessage` | Server requests LLM generation/completion from the client/host | `messages`, `modelPreferences`, `systemPrompt`, `includeContext`, `temperature`, `maxTokens`, `stopSequences` | `CreateMessageResult`: `model`, `stopReason`, `role`, `content` | `-32601` if client has not declared sampling capability; `-32000` on LLM failure | MCP Spec 2024-11-05 |
| 20 | Logging | `logging/setLevel` | Client configures the minimum log severity level emitted by server | `level`: `"debug" | "info" | "notice" | "warning" | "error" | "critical" | "alert" | "emergency"` | Empty result (`{}`) | `-32602` Invalid log level string | MCP Spec 2024-11-05 |
| 21 | Logging | `notifications/message` | Server streams diagnostic/logging messages to client | `level`: string, `logger`: string (optional), `data`: any JSON value | None (Notification) | Client routes to UI/debug pane | MCP Spec 2024-11-05 |
| 22 | Progress | `notifications/progress` | Server reports progress for long-running tool or resource operations | `progressToken`: string \| number, `progress`: number, `total`: number (optional) | None (Notification) | Dropped if progress token is unrecognized | MCP Spec 2024-11-05 |
| 23 | Cancellation | `notifications/cancelled` | Client or server notifies peer to abort an in-flight request | `requestId`: string \| number, `reason`: string (optional) | None (Notification) | Peer cancels active task/future and ignores pending responses | MCP Spec 2024-11-05 |
| 24 | Roots | `roots/list` | Server queries client for root workspace directories/URIs | None | `roots`: array of `Root` (`uri`, `name`) | `-32601` if client has not declared roots capability | MCP Spec 2024-11-05 |
| 25 | Roots | `notifications/roots/list_changed` | Client notifies server that workspace roots have been modified | None | None (Notification) | Server re-queries `roots/list` | MCP Spec 2024-11-05 |
| 26 | Architecture | MCP Client Engine Subsystem | Async manager that spawns, connects to, routes, and supervises external MCP servers | Server configuration registry (JSON/TOML), tool calls, resource reads | Unified tool/resource dispatch, aggregation, health monitoring | Auto-restart with backoff, fault isolation per server | System Architecture |
| 27 | Architecture | MCP Server Engine Subsystem | Embedded server exposing internal CLI commands, sysinfo, and IDE operations | Incoming stdio or SSE JSON-RPC requests | JSON-RPC responses conforming to MCP 2024-11-05 schemas | Standard JSON-RPC error frames | System Architecture |

---

## 2. Edge Cases & Boundary Conditions

| # | Feature | Input / Condition | Observed / Required Behavior |
|---|---------|-------------------|-----------------------------|
| 1 | Stdio Transport | Server outputs non-JSON-RPC lines on `stdout` (e.g. standard print statements) | Transport parser fails framing or returns Parse Error `-32700`. **Rule:** Server implementations MUST route all debug output to `stderr`; `stdout` is strictly reserved for line-delimited JSON-RPC messages. |
| 2 | Stdio Transport | Child process crashes or exits unexpectedly while requests are pending | Transport layer detects EOF on stdout stream, cancels all pending oneshot channels, marks server status as `Crashed`, and returns JSON-RPC error `-32000` (Server disconnected) to callers. |
| 3 | Stdio Transport | Server hangs during execution of `tools/call` without responding | Client enforces configurable timeout (e.g. 30s). Upon timeout, client issues `notifications/cancelled`, drops request waiter, and returns Timeout error. |
| 4 | SSE Transport | Client disconnects HTTP connection before response is streamed | Server detects broken SSE channel, aborts associated task worker via cancellation token, and cleans up session state. |
| 5 | SSE Transport | Client sends HTTP POST message without valid `sessionId` query param | HTTP server responds with HTTP 400 Bad Request or HTTP 404 Session Not Found. |
| 6 | Handshake | Client sends `tools/call` before sending `notifications/initialized` | Server responds with JSON-RPC error `-32002` (Server not initialized). |
| 7 | Handshake | Protocol version mismatch (e.g., client requests unsupported future version) | Server responds with highest supported protocol version in `InitializeResult` (e.g. `2024-11-05`) or errors if backwards incompatible. |
| 8 | Tools | Tool execution encounters domain error (e.g. file not found in bash tool) | Tool returns JSON-RPC success (`result`) with `isError: true` and error explanation in `content[0].text`. The JSON-RPC envelope itself is NOT an error (`error` is null). |
| 9 | Tools | Tool arguments fail JSON Schema validation (e.g. missing required field) | Engine rejects invocation before execution with JSON-RPC error code `-32602` (Invalid params) containing schema validation diagnostics. |
| 10 | Tools | Tool produces massive binary or text output (> 100MB) | Content streaming or memory limiting enforced; engine caps text payloads and supports resource reference returns (`EmbeddedResource`) instead of raw in-memory buffers. |
| 11 | Resources | Request for non-existent URI in `resources/read` | Returns JSON-RPC error `-32002` with descriptive error message (e.g. "Resource 'file:///unknown.txt' not found"). |
| 12 | Resources | Resource URI matches dynamic template with missing template variables | Returns `-32602` Invalid params detailing missing template arguments. |
| 13 | Cancellation | Client sends `notifications/cancelled` for a request that has already finished | Server safely ignores notification; no error generated. |
| 14 | Progress | Server emits progress notifications with non-monotonic progress or `progress > total` | Client clamps progress value between 0.0 and 1.0 (or 100%) for UI display without panicking. |
| 15 | Sampling | Server issues `sampling/createMessage` when host has no active local or cloud model | Client returns JSON-RPC error `-32000` indicating model provider unavailable. |
| 16 | Multithreading | 50 concurrent `tools/call` dispatched across worker threads simultaneously | Engine dispatches concurrently via `tokio::spawn` worker pools; distinct request IDs prevent message cross-talk; sub-millisecond route resolution. |

---

## 3. Protocol Framing & JSON-RPC 2.0 Base Specification

All MCP communication is framed using the **JSON-RPC 2.0** specification (RFC 8259).

### 3.1 Message Envelopes

#### 1. Request Object
Sent by either Client or Server to invoke a remote method expecting a response:
```json
{
  "jsonrpc": "2.0",
  "id": 1001,
  "method": "tools/call",
  "params": {
    "name": "run_command",
    "arguments": {
      "command": "cargo check"
    }
  }
}
```
- `jsonrpc`: MUST be exactly `"2.0"`.
- `id`: MUST be a unique `string` or `integer` (64-bit integer recommended in Rust: `u64` or `i64`). Floating point is disallowed.
- `method`: MUST be a `string` naming the MCP method.
- `params`: An optional `object` containing arguments.

#### 2. Success Response Object
Sent in response to a Request when execution succeeds:
```json
{
  "jsonrpc": "2.0",
  "id": 1001,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Finished dev [unoptimized + debuginfo] target(s) in 0.12s"
      }
    ],
    "isError": false
  }
}
```
- `id`: MUST match the `id` of the Request being responded to.
- `result`: The payload returned by the method.

#### 3. Error Response Object
Sent in response to a Request when a protocol or unhandled server error occurs:
```json
{
  "jsonrpc": "2.0",
  "id": 1001,
  "error": {
    "code": -32602,
    "message": "Invalid params: missing required field 'command'",
    "data": {
      "missing_fields": ["command"]
    }
  }
}
```
- `id`: MUST match the request `id`, or `null` if the request `id` could not be parsed.
- `error.code`: Integer error code.
- `error.message`: Short human-readable string summary.
- `error.data`: Optional structured diagnostic data.

#### 4. Notification Object
One-way message that does NOT expect a response:
```json
{
  "jsonrpc": "2.0",
  "method": "notifications/progress",
  "params": {
    "progressToken": "tok-482",
    "progress": 45,
    "total": 100
  }
}
```
- MUST NOT contain an `id` member.

### 3.2 Standard JSON-RPC & MCP Error Codes

| Code | Constant | Meaning / Usage in MCP |
|---|---|---|
| `-32700` | `PARSE_ERROR` | Invalid JSON received by the transport parser. |
| `-32600` | `INVALID_REQUEST` | The JSON sent is not a valid JSON-RPC 2.0 Request object. |
| `-32601` | `METHOD_NOT_FOUND` | The requested method does not exist or capability is not enabled. |
| `-32602` | `INVALID_PARAMS` | Invalid method parameter(s) or schema validation failure. |
| `-32603` | `INTERNAL_ERROR` | Internal runtime or engine error. |
| `-32002` | `NOT_INITIALIZED` | Client issued requests before completing `initialize`/`initialized` handshake. |
| `-32001` | `RESOURCE_NOT_FOUND` | Resource URI does not exist or cannot be resolved. |
| `-32000` | `SERVER_ERROR_GENERIC`| Generic custom server error / execution failure. |

---

## 4. Transports Specification

### 4.1 Stdio Transport (Standard Input / Standard Output)

The Stdio transport runs external MCP servers as child sub-processes. Communication occurs via standard OS pipes:
- **Client Output -> Server `stdin`**: Line-delimited UTF-8 JSON-RPC strings terminated by `\n` (or `\r\n`).
- **Server `stdout` -> Client Input**: Line-delimited UTF-8 JSON-RPC strings terminated by `\n` (or `\r\n`).
- **Server `stderr`**: Dedicated to human-readable log messages and diagnostics. The client captures `stderr` and streams it to the IDE log viewer without interpreting it as JSON-RPC messages.

#### Rust Async Stdio Engine Implementation:
```rust
use tokio::process::{Child, ChildStdin, ChildStdout, Command};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader, BufWriter};

pub struct StdioTransport {
    child: Child,
    writer: BufWriter<ChildStdin>,
    reader: BufReader<ChildStdout>,
}
```
**Sub-millisecond Guarantees:**
- Unbuffered `write_all` with immediate flush for message latency.
- Dedicated background reader task utilizing `tokio::io::LinesStream` pushing into an unbounded or high-capacity `mpsc::channel`.
- Process supervision: monitors exit signals, automatically reaps zombies, and cleans up pipes on drop.

### 4.2 HTTP with Server-Sent Events (SSE) Transport

The HTTP/SSE transport enables networked, distributed, or web-based MCP communication.

#### Connection Workflow:
```
Client                              Server
  |                                   |
  |--- GET /sse --------------------->| (Establishes SSE Stream)
  |<-- HTTP 200 (text/event-stream)---|
  |<-- event: endpoint --------------|
  |    data: /message?sessionId=123   | (Provides POST URI)
  |                                   |
  |--- POST /message?sessionId=123 -->| (Client sends JSON-RPC Request)
  |    body: {"jsonrpc":"2.0",...}    |
  |<-- HTTP 202 Accepted -------------|
  |                                   |
  |<-- event: message ----------------| (Server delivers Response/Notification)
  |    data: {"jsonrpc":"2.0",...}    |
  |                                   |
```

#### SSE Headers:
- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `Connection: keep-alive`
- `Access-Control-Allow-Origin: *` (CORS support for Web IDE frontends)

#### Message Delivery:
- **Requests from Client**: Sent via standard HTTP `POST` to the session-specific endpoint. The HTTP response is an empty `202 Accepted` (or `200 OK`). The actual JSON-RPC response is delivered asynchronously over the open SSE stream.
- **Requests from Server**: Pushed over the SSE stream as `event: message`. The client responds via HTTP POST with matching request `id`.

---

## 5. Protocol Lifecycle & Capability Negotiation

### 5.1 Lifecycle State Machine

```
   [Disconnected]
         |
         | (Spawn Process / Open SSE)
         v
   [Uninitialized]
         |
         | Client sends `initialize`
         v
   [Initializing]
         |
         | Server responds `InitializeResult`
         | Client sends `notifications/initialized`
         v
   [Initialized (Operational)] <-------------------+
         |                                         |
         | Normal Operations (tools, resources)    | Ping / Pong
         |                                         |
         v                                         +
   [Shutting Down]
         |
         | (Close Transport / Kill Child)
         v
   [Disconnected]
```

### 5.2 Handshake Schemas

#### 1. `initialize` Request (Client -> Server)
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "roots": {
        "listChanged": true
      },
      "sampling": {}
    },
    "clientInfo": {
      "name": "mcp-ide-engine",
      "version": "0.1.0"
    }
  }
}
```

#### 2. `InitializeResult` (Server -> Client)
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {
        "listChanged": true
      },
      "resources": {
        "subscribe": true,
        "listChanged": true
      },
      "prompts": {
        "listChanged": true
      },
      "logging": {}
    },
    "serverInfo": {
      "name": "host-system-tools",
      "version": "1.0.0"
    },
    "instructions": "Use these tools to inspect system hardware, execute workspace builds, and manage tasks."
  }
}
```

#### 3. `notifications/initialized` (Client -> Server)
```json
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```

---

## 6. Primitives & JSON Schemas

### 6.1 Tools Primitive

#### `tools/list`
- **Request**:
  ```json
  { "method": "tools/list", "params": { "cursor": "page-token-123" } }
  ```
- **Response Result**:
  ```json
  {
    "tools": [
      {
        "name": "execute_shell",
        "description": "Runs a non-blocking shell command on the host engine worker pool.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "command": {
              "type": "string",
              "description": "The command line string to execute."
            },
            "cwd": {
              "type": "string",
              "description": "Optional working directory."
            },
            "timeout_ms": {
              "type": "integer",
              "description": "Timeout in milliseconds."
            }
          },
          "required": ["command"]
        }
      }
    ],
    "nextCursor": null
  }
  ```

#### `tools/call`
- **Request**:
  ```json
  {
    "method": "tools/call",
    "params": {
      "name": "execute_shell",
      "arguments": {
        "command": "cargo --version"
      },
      "_meta": {
        "progressToken": 42
      }
    }
  }
  ```
- **Response Result**:
  ```json
  {
    "content": [
      {
        "type": "text",
        "text": "cargo 1.80.0 (0514e5a99 2024-07-21)"
      }
    ],
    "isError": false
  }
  ```

### 6.2 Resources Primitive

#### `resources/list`
- **Response Result**:
  ```json
  {
    "resources": [
      {
        "uri": "sysinfo://metrics/live",
        "name": "System Resource Telemetry",
        "description": "Live CPU, RAM, and GPU utilization metrics updated every 500ms.",
        "mimeType": "application/json"
      }
    ]
  }
  ```

#### `resources/templates/list`
- **Response Result**:
  ```json
  {
    "resourceTemplates": [
      {
        "uriTemplate": "workspace://files/{path}",
        "name": "Workspace File Access",
        "description": "Access files in the active workspace directory.",
        "mimeType": "text/plain"
      }
    ]
  }
  ```

#### `resources/read`
- **Request**:
  ```json
  { "method": "resources/read", "params": { "uri": "sysinfo://metrics/live" } }
  ```
- **Response Result**:
  ```json
  {
    "contents": [
      {
        "uri": "sysinfo://metrics/live",
        "mimeType": "application/json",
        "text": "{\"cpu_usage_pct\":14.2,\"ram_available_mb\":24576,\"gpu_vram_free_mb\":8192}"
      }
    ]
  }
  ```

### 6.3 Prompts Primitive

#### `prompts/list`
- **Response Result**:
  ```json
  {
    "prompts": [
      {
        "name": "explain_code",
        "description": "Generates a structured breakdown of a selected code block.",
        "arguments": [
          {
            "name": "code",
            "description": "The source code snippet.",
            "required": true
          },
          {
            "name": "language",
            "description": "Programming language (e.g. rust, python).",
            "required": false
          }
        ]
      }
    ]
  }
  ```

#### `prompts/get`
- **Request**:
  ```json
  {
    "method": "prompts/get",
    "params": {
      "name": "explain_code",
      "arguments": {
        "code": "fn main() { println!(\"Hello\"); }",
        "language": "rust"
      }
    }
  }
  ```
- **Response Result**:
  ```json
  {
    "description": "Code explanation prompt",
    "messages": [
      {
        "role": "user",
        "content": {
          "type": "text",
          "text": "Please explain this rust code:\n\n```rust\nfn main() { println!(\"Hello\"); }\n```"
        }
      }
    ]
  }
  ```

### 6.4 Sampling Primitive (`sampling/createMessage`)

Enables the MCP server to leverage the host's AI inference engine:
```json
{
  "jsonrpc": "2.0",
  "id": "samp-1",
  "method": "sampling/createMessage",
  "params": {
    "messages": [
      {
        "role": "user",
        "content": {
          "type": "text",
          "text": "Summarize this compiler diagnostic error: error[E0382]: use of moved value"
        }
      }
    ],
    "modelPreferences": {
      "hints": [{ "name": "qwen2.5-coder-7b" }],
      "speedPriority": 0.8,
      "intelligencePriority": 0.7
    },
    "systemPrompt": "You are an expert Rust compiler diagnostic assistant.",
    "maxTokens": 500,
    "temperature": 0.2
  }
}
```
**Result**:
```json
{
  "jsonrpc": "2.0",
  "id": "samp-1",
  "result": {
    "model": "qwen2.5-coder-7b-q4",
    "stopReason": "endTurn",
    "role": "assistant",
    "content": {
      "type": "text",
      "text": "This error occurs because a value was moved and then subsequently accessed..."
    }
  }
}
```

---

## 7. Dual Client & Server Architecture in Rust

```
+===================================================================================+
|                              MCP IDE ENGINE (RUST)                                |
|                                                                                   |
|  +-------------------------------------+   +------------------------------------+ |
|  |           MCP SERVER ROLE           |   |          MCP CLIENT ROLE           | |
|  | (Exposes Host Tools/Sys/IDE to Ext) |   | (Orchestrates External MCP Servers)| |
|  +-------------------------------------+   +------------------------------------+ |
|  | Transports:                         |   | Server Supervisor:                 | |
|  |  * Stdio Server (CLI / Agent mode)  |   |  * Process Spawner & Stdio Pipes   | |
|  |  * Axum SSE Server (Web/API mode)   |   |  * SSE Client Session Pool         | |
|  |                                     |   |  * Health Watchdog & Ping Heartbeat| |
|  | Built-in Registries:                |   |                                    | |
|  |  * Tools: CLI commands, sysinfo     |   | Aggregated Catalog:                | |
|  |  * Resources: metrics, thread graph |   |  * Namespaced Tool Routing         | |
|  |  * Prompts: IDE prompt templates    |   |  * Dynamic Resource Merging        | |
|  |                                     |   |  * Sampling Host Handler           | |
|  +-------------------------------------+   +------------------------------------+ |
|                                     |         |                                   |
|                                     v         v                                   |
|  +------------------------------------------------------------------------------+ |
|  |                 ASYNC DISPATCH ROUTER & WORKER THREAD POOL                   | |
|  |  * Tokio multi-threaded runtime (rayon for CPU intensive tasks)              | |
|  |  * Lock-free registry (`dashmap` / `arc-swap`)                               | |
|  |  * Compiled JSON schema validator (`jsonschema` crate)                       | |
|  |  * Sub-millisecond dispatch (< 1ms routing & validation)                     | |
|  |  * Isolation: `tokio_util::sync::CancellationToken` & Timeout bounds         | |
|  +------------------------------------------------------------------------------+ |
+===================================================================================+
```

### 7.1 Key Rust Crate & Type Strategy

```rust
// Core JSON-RPC Data Structures (serde-compatible)
use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcRequest {
    pub jsonrpc: String,
    pub id: Option<RequestId>,
    pub method: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub params: Option<Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
#[serde(untagged)]
pub enum RequestId {
    Int(i64),
    Str(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcResponse {
    pub jsonrpc: String,
    pub id: Option<RequestId>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<JsonRpcError>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcError {
    pub code: i32,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<Value>,
}
```

---

## 8. Sub-Millisecond Dispatch & Performance Blueprint

To ensure tool invocations meet the sub-millisecond dispatch overhead requirement:
1. **Zero-Lock Dispatch Table**: Tools and handlers are registered in a lock-free `DashMap<String, Arc<dyn ToolHandler>>` or an immutable `ArcSwap<HashMap<...>>` refreshed via copy-on-write during configuration reload. Lookup latency is ~50-150 nanoseconds.
2. **Pre-Compiled JSON Schemas**: Input schemas for tools are parsed and compiled once at registration time using `jsonschema::JSONSchema::compile`. At invocation time, validation is evaluated against memory in ~5-15 microseconds without re-parsing schema ASTs.
3. **Dedicated Async Channels**: Outgoing RPC requests are assigned an `id` and a `tokio::sync::oneshot::Sender<JsonRpcResponse>` stored in a concurrent pending-requests table (`DashMap<RequestId, oneshot::Sender>`). When the transport receives a response matching the `id`, it removes the sender and completes the future in < 10 microseconds.
4. **Isolated Task Spawning**: Each `tools/call` executes inside an isolated `tokio::spawn` task accompanied by a `CancellationToken`. Panics are caught with `std::panic::AssertUnwindSafe` to ensure tool execution errors never destabilize the engine host.

---

## 9. Verification & Test Suite Matrix

| Test Suite | Scope | Target Invariants |
|---|---|---|
| `test_jsonrpc_framing` | Unit | Serialization & deserialization of requests, responses, errors, and notifications. |
| `test_stdio_transport` | Integration | Spawning mock MCP server child process, line-delimited communication, stderr isolation. |
| `test_sse_transport` | Integration | SSE connection establishment, endpoint discovery, HTTP POST request delivery, streaming responses. |
| `test_handshake_lifecycle` | Unit / State | Enforcing state transitions: rejecting calls prior to `initialized`, handling version negotiation. |
| `test_tool_dispatch_concurrency` | Stress | 50+ concurrent tool calls dispatched in parallel; verifying zero race conditions and sub-millisecond routing latency. |
| `test_cancellation_and_progress`| Integration | Emitting progress tokens during execution, triggering cancellation mid-flight, and verifying task termination. |
| `test_dual_server_client` | E2E | Engine MCP Client querying Engine MCP Server across stdio pipe. |

