# Comprehensive Technical Analysis: MCP Tools, Schemas, and Endpoints

**Author**: `survey_explorer_gen3_1`  
**Date**: 2026-09-03  
**Working Directory**: `C:\Users\oyesanyf\.gemini\antigravity\scratch\mcp_ide_engine\.agents\survey_explorer_gen3_1`  
**Scope Boundary**: READ-ONLY codebase survey and architectural analysis  
**Target Specifications**: MCP 2024-11-05 Standard & Requirement R2 (`ORIGINAL_REQUEST.md`)

---

## 1. Executive Summary

This investigation surveys the Model Context Protocol (MCP) subsystem within the `mcp_ide_engine` workspace, focusing on `crates/mcp-protocol`, `crates/mcp-cli`, and their interfaces with `crates/mcp-core` and `crates/mcp-resource`.

### Core Findings
1. **Tool Registration Architecture**:
   - `crates/mcp-protocol` is purely a protocol library offering server/client engines, transports (Stdio, SSE, Channel), types, and schema compilation. It does not hardcode application tools.
   - All 8 specified MCP tools are registered in `crates/mcp-cli/src/main.rs` inside `setup_default_mcp_server()` (lines 281–532).
2. **Implementation Health of the 8 Tools**:
   - All 8 tools (`write_code_file`, `read_code_file`, `list_directory`, `execute_cli_command`, `get_telemetry`, `recommend_best_model`, `calculate_layer_offload`, `run_command`) exist and are registered.
   - However, **significant feature gaps exist** in 6 of the 8 tools regarding parameter support, byte fidelity, line ranges, recursive directory inspection, permissions, process cancellation, and real-time execution streaming.
3. **MCP 2024-11-05 Specification Conformance**:
   - `tools/list`, `resources/list`, and `prompts/list` conform to the JSON-RPC 2.0 and MCP 2024-11-05 schemas (using camelCase serialization and standard types).
   - Only 1 static resource (`telemetry://system/status`) and 1 prompt template (`analyze_task`) are registered by default.
4. **Critical Protocol & Transport Blockers**:
   - **Stdio stdout pollution**: `crates/mcp-cli/src/main.rs:639` prints an ANSI banner directly to `stdout` (`println!("Starting MCP Server on standard I/O streams...")`), corrupting initial JSON-RPC message framing for connecting IDE clients.
   - **Premature EOF on empty line**: `crates/mcp-protocol/src/transport/stdio.rs:185` returns `Ok(None)` when encountering a blank line, causing `McpServer::serve` to terminate prematurely.
   - **Missing SSE server in CLI**: Although `mcp_protocol::transport::sse::SseSessionManager` exists, `mcp-cli mcp serve --sse-port` is completely unhandled (does nothing).
   - **Incomplete Cancellation Support**: `McpServer::handle_notification` handles `notifications/cancelled`, but does **not** handle the standard LSP/MCP `$/cancelRequest` notification. Furthermore, tool execution closures ignore `_ctx.cancellation_token`, meaning in-flight tasks and child shell processes are never terminated upon cancellation, leaking orphan processes.

---

## 2. Detailed Tool Inventory & Registration Audit

| # | MCP Tool Name | Registered Location | Underlying Command | Schema Defined | Current Implementation Status & Deficiencies |
|---|---------------|---------------------|--------------------|----------------|---------------------------------------------|
| 1 | `write_code_file` | `mcp-cli/src/main.rs:353-377` | `write_file` (`main.rs:192-221`) | `path`, `content` | **Partial**. Handles directory creation, but lacks permissions support and binary/base64 encoding. |
| 2 | `read_code_file` | `mcp-cli/src/main.rs:381-404` | `read_file` (`main.rs:224-244`) | `path` | **Partial**. Fails on binary files (UTF-8 `read_to_string`); lacks line ranges (`start_line`, `end_line`); returns JSON wrapper instead of clean text. |
| 3 | `list_directory` | `mcp-cli/src/main.rs:408-430` | `list_dir` (`main.rs:247-272`) | `path` | **Partial**. 1-level shallow listing only (no recursive walk); metadata lacks timestamps (`mtime`), permissions, and symlink detection. |
| 4 | `execute_cli_command` | `mcp-cli/src/main.rs:325-349` | `execute_cli` (`main.rs:141-189`) | `command`, `cwd` | **Partial / Flawed**. Asynchronous via Tokio, but buffers full output with `proc.output().await` (no streaming); ignores cancellation token; child process leaks on drop. |
| 5 | `get_telemetry` | `mcp-cli/src/main.rs:434-445` | `ResourceMonitor::snapshot()` | `{ "type": "object" }` | **Complete**. Returns full `SystemSnapshot` with CPU, RAM, and GPU detection (NVML, DXGI, Apple Silicon, sysinfo fallback). |
| 6 | `recommend_best_model` | `mcp-cli/src/main.rs:449-469` | `ModelSelector::select_best_model` | `context_tokens` | **Complete**. Dynamic model tier classification across Micro/Nano, Small, Medium, Large, and Cloud Fallback. |
| 7 | `calculate_layer_offload` | `mcp-cli/src/main.rs:473-506` | `mcp_resource::selector::calculate_layer_offload` | `model`, `vram_gb` | **Partial**. Calculates valid layer distribution, but hardcodes `context_tokens` (4096) and `safety_margin` (0.15); naive model substring matching. |
| 8 | `run_command` | `mcp-cli/src/main.rs:286-321` | `TaskDispatcher::dispatch` | `command`, `args`, `priority` | **Complete / Flawed Cancellation**. Correctly routes across 5-lane priority scheduler; ignores `_ctx.cancellation_token`. |

---

## 3. In-Depth Analysis of Each Tool

### 3.1. `write_code_file`
- **Location**: `crates/mcp-cli/src/main.rs:353-377` (registration) and `192-221` (handler).
- **Input Schema**:
  ```json
  {
      "type": "object",
      "properties": {
          "path": { "type": "string", "description": "Target relative or absolute file path" },
          "content": { "type": "string", "description": "Code contents to write" }
      },
      "required": ["path", "content"]
  }
  ```
- **Directory Path Creation**:
  - Code: `if let Some(parent) = file_path.parent() { if !parent.as_os_str().is_empty() { tokio::fs::create_dir_all(parent).await... } }`.
  - **Verdict**: Successfully handles arbitrary nested parent directories before writing.
- **Permissions**:
  - Code: Direct call to `tokio::fs::write(file_path, content).await`.
  - **Verdict**: **Missing**. Does not support setting executable permissions (`0o755` on Unix/macOS) or read-only flags. An AI agent generating shell scripts or CLI binaries cannot set execute permissions via this tool.
- **UTF-8 vs. Binary Writes**:
  - Code: `args["content"].as_str()` extracts a UTF-8 string and passes it to `tokio::fs::write`.
  - **Verdict**: **Deficient**. There is no support for binary data or base64 decoding. Passing binary assets (images, fonts, precompiled wasm/binaries) will fail or corrupt byte content.
  - **Proposed Enhancement**: Add optional `encoding` parameter (`"utf-8"` default, `"base64"` optional) and optional `mode` parameter (e.g., `0o755`).

---

### 3.2. `read_code_file`
- **Location**: `crates/mcp-cli/src/main.rs:381-404` (registration) and `224-244` (handler).
- **Input Schema**:
  ```json
  {
      "type": "object",
      "properties": {
          "path": { "type": "string", "description": "Source file path to read" }
      },
      "required": ["path"]
  }
  ```
- **Exact Byte Fidelity**:
  - Code: `let content = tokio::fs::read_to_string(path).await`.
  - **Verdict**: **Deficient**. `read_to_string` strictly requires valid UTF-8. If invoked on binary files, images, or files with non-UTF-8 encodings (e.g. ISO-8859-1 or UTF-16), the tool fails with an I/O error (`stream did not contain valid UTF-8`).
- **Line Ranges**:
  - **Verdict**: **Missing**. The schema only defines `path`. There are no `start_line` / `end_line` or `offset` / `limit` parameters. In large codebases (e.g., reading 100 lines of a 50,000-line file), the client is forced to transfer the entire file over JSON-RPC.
- **Error Handling**:
  - Returns `TaskError::ExecutionFailed` on file missing or read failure, which is contained in `CallToolResult::text` or `ToolExecutionError`.
- **Response Format**:
  - The tool outputs `{ "path": path, "content": content, "bytes_read": content.len() }` serialized into the `Content::Text`. Returning a JSON wrapper rather than the raw file text or structured resource contents adds serialization overhead and requires agents to unwrap JSON.

---

### 3.3. `list_directory`
- **Location**: `crates/mcp-cli/src/main.rs:408-430` (registration) and `247-272` (handler).
- **Input Schema**:
  ```json
  {
      "type": "object",
      "properties": {
          "path": { "type": "string", "description": "Directory path to list, defaults to '.'" }
      }
  }
  ```
- **Recursive Directory Inspection**:
  - Code: `let mut read_dir = tokio::fs::read_dir(path).await; while let Ok(Some(entry)) = read_dir.next_entry().await { ... }`.
  - **Verdict**: **Missing**. Inspection is strictly 1-level deep. There is no `recursive: bool` or `max_depth: usize` parameter. An agent cannot inspect a project directory tree in a single tool call.
- **Metadata**:
  - Returned fields: `name: String`, `is_dir: bool`, `size_bytes: u64`.
  - **Verdict**: **Incomplete**. Missing file modification timestamps (`mtime`), permissions (readonly / executable), file extension, and symlink flags (`is_symlink`).

---

### 3.4. `execute_cli_command`
- **Location**: `crates/mcp-cli/src/main.rs:325-349` (registration) and `141-189` (handler).
- **Input Schema**:
  ```json
  {
      "type": "object",
      "properties": {
          "command": { "type": "string", "description": "The shell command line to execute" },
          "cwd": { "type": "string", "description": "Optional working directory" }
      },
      "required": ["command"]
  }
  ```
- **Asynchronous Execution**:
  - Code: Dispatched via `TaskDispatcher::dispatch("execute_cli", a, Some(TaskPriority::High))` into Tokio async runtime.
  - **Verdict**: Non-blocking with respect to the MCP request loop.
- **Real-Time stdout/stderr Capture**:
  - Code: `let output = proc.output().await;`.
  - **Verdict**: **Missing**. `proc.output().await` buffers all stdout and stderr in memory until the child process terminates. For long-running operations (e.g. `cargo build --release` or large test suites), no output is streamed to the client during execution.
- **Exit Codes & Error Status**:
  - Captures `exit_code: output.status.code().unwrap_or(-1)`.
  - However, in `crates/mcp-cli/src/main.rs:346`, the tool returns `Ok(CallToolResult::text(...))` regardless of exit code! As a result, `CallToolResult.is_error` is `Some(false)` even when the shell command exits with code 1 or 127, violating the MCP convention where non-zero command failures report `is_error: true`.
- **Cancellation & Orphan Process Leaks (CRITICAL)**:
  - In `crates/mcp-cli/src/main.rs:336`: `move |_ctx, args|` discards `_ctx.cancellation_token`.
  - `proc.output().await` does **not** call `.kill_on_drop(true)`.
  - When an IDE sends a cancellation notification (`notifications/cancelled`), `_ctx` is not linked to the dispatched task, and even if dropped, the spawned OS process (`cmd.exe` or `sh`) continues running unmonitored.

---

### 3.5. `get_telemetry`
- **Location**: `crates/mcp-cli/src/main.rs:434-445` (registration).
- **Input Schema**: `{ "type": "object" }`.
- **Hardware Metrics Probed**:
  - Host CPU: Physical core count, logical threads, global CPU usage %, per-core percentages, CPU brand, clock frequency (`crates/mcp-resource/src/telemetry.rs:22-36`).
  - System RAM: Total, used, available, free, swap total/used, memory pressure percentage (`telemetry.rs:39-55`).
  - Host Process: PID, process CPU %, RSS memory bytes, virtual memory (`telemetry.rs:75-85`).
  - GPU Telemetry: Dynamic fallback chain (`crates/mcp-resource/src/gpu.rs`):
    1. NVIDIA NVML (via dynamic loading of `nvml.dll` / `libnvidia-ml.so`)
    2. Windows DXGI (via dynamic loading of `dxgi.dll`)
    3. Apple Silicon Metal unified memory
    4. Host System RAM fallback
  - **Verdict**: **Fully conforms** to Requirement R2 and provides rich host telemetry.

---

### 3.6. `recommend_best_model`
- **Location**: `crates/mcp-cli/src/main.rs:449-469` (registration).
- **Input Schema**:
  ```json
  {
      "type": "object",
      "properties": {
          "context_tokens": { "type": "integer", "description": "Expected context length in tokens, defaults to 4096" }
      }
  }
  ```
- **Dynamic Tier Classification**:
  - Implemented in `crates/mcp-resource/src/selector.rs:380-450` via `ModelSelector::select_best_model`.
  - Evaluates models against 5 tiers: `MicroNano` (0.5B–1.7B), `Small` (1B–3B), `Medium` (7B–8B), `Large` (14B–70B), and `CloudFallback`.
  - Factors in model weights, KV cache sizing per token, activation buffers, and a 15% safety headroom margin.
  - Automatically routes to `ExecutionTarget::CloudFallback` if host memory pressure exceeds 92%.
  - **Verdict**: **Fully conforms** to Requirement R2.

---

### 3.7. `calculate_layer_offload`
- **Location**: `crates/mcp-cli/src/main.rs:473-506` (registration).
- **Input Schema**:
  ```json
  {
      "type": "object",
      "properties": {
          "model": { "type": "string", "description": "Model family or ID (e.g. llama-3.1-8b, llama-3.2-3b, llama-3.3-70b)" },
          "vram_gb": { "type": "number", "description": "Override available VRAM in Gigabytes" }
      }
  }
  ```
- **Offload Calculation**:
  - Implemented in `crates/mcp-resource/src/selector.rs:300-357`.
  - Computes `gpu_layers`, `cpu_layers`, `total_layers`, `vram_allocated_bytes`, `ram_allocated_bytes`, and offload mode flags (`is_full_gpu`, `is_hybrid`, `is_cpu_only`).
- **Gaps**:
  - `context_tokens` is hardcoded to 4096 in `crates/mcp-cli/src/main.rs:503`, despite model memory depending heavily on context length.
  - Model resolution relies on simple string matching (`if model.contains("70b") ...`).
  - Does not accept quantization parameters (defaults to Q4_K_M).

---

### 3.8. `run_command`
- **Location**: `crates/mcp-cli/src/main.rs:286-321` (registration).
- **Input Schema**:
  ```json
  {
      "type": "object",
      "properties": {
          "command": { "type": "string" },
          "args": { "type": "object" },
          "priority": { "type": "string", "enum": ["Critical", "High", "Normal", "Low", "Background"] }
      },
      "required": ["command"]
  }
  ```
- **Priority Task Dispatch**:
  - Maps priority strings to `TaskPriority` and queues task through `TaskDispatcher::dispatch`.
  - Dispatches across the 5-lane scheduler with starvation prevention and high-resolution timing.
- **Gaps**:
  - Closure ignores `_ctx.cancellation_token`. Dispatched tasks cannot be cancelled from the MCP interface.

---

## 4. MCP 2024-11-05 Specification Conformance Analysis

### 4.1. Protocol Lifecycle & Negotiation
- **`initialize` Request & Response**:
  - Conforms to MCP 2024-11-05. Client sends `protocolVersion: "2024-11-05"`, `capabilities`, `clientInfo`. Server responds with `protocolVersion: "2024-11-05"`, server `capabilities`, `serverInfo`, `instructions`.
  - Server verifies state: non-`initialize` and non-`ping` requests before initialization are rejected with JSON-RPC error code `-32002` (`SERVER_NOT_INITIALIZED`).
- **`notifications/initialized`**:
  - Conforms to MCP 2024-11-05. Transitions server from `Initializing` to `Initialized`.
- **`ping`**:
  - Conforms. Responds with empty object `{}`.

### 4.2. `tools/list` Conformance
- Response schema:
  ```json
  {
    "tools": [
      {
        "name": "write_code_file",
        "description": "Writes or generates source code...",
        "inputSchema": {
          "type": "object",
          "properties": { ... },
          "required": [ ... ]
        }
      }
    ]
  }
  ```
- Uses `camelCase` (`inputSchema`, `nextCursor`).
- Input schemas are pre-compiled and validated via `crates/mcp-protocol/src/schema.rs` (`CompiledSchema`).
- **Conformance Rating: STRICTLY CONFORMS**.

### 4.3. `resources/list` Conformance
- Response schema:
  ```json
  {
    "resources": [
      {
        "uri": "telemetry://system/status",
        "name": "System Hardware Telemetry",
        "description": "Live CPU, RAM, and GPU load statistics",
        "mimeType": "application/json"
      }
    ]
  }
  ```
- Uses `camelCase` (`mimeType`, `nextCursor`).
- Also supports `resources/templates/list` for RFC 6570 dynamic templates.
- **Conformance Rating: STRICTLY CONFORMS**.
- *Gap*: Only 1 static resource is currently registered. No dynamic workspace file resources are registered.

### 4.4. `prompts/list` Conformance
- Response schema:
  ```json
  {
    "prompts": [
      {
        "name": "analyze_task",
        "description": "Generate prompt for task performance analysis",
        "arguments": [
          {
            "name": "task_id",
            "description": "Task execution ID",
            "required": true
          }
        ]
      }
    ]
  }
  ```
- **Conformance Rating: STRICTLY CONFORMS**.
- *Gap*: Only 1 prompt is currently registered.

---

## 5. Critical Architectural Gaps and Defects

### 5.1. Defect: Subprocess Stdio stdout Contamination
- **File & Line**: `crates/mcp-cli/src/main.rs:639`
- **Code**:
  ```rust
  McpSubcommands::Serve(s_args) => {
      if s_args.stdio {
          println!("{}", "Starting MCP Server on standard I/O streams...".green());
          let transport = std::sync::Arc::new(...);
          server.serve(transport).await?;
      }
  }
  ```
- **Impact**: Any IDE client (VS Code, Cursor, Antigravity) that spawns `mcp-cli mcp serve --stdio` expects line-delimited JSON-RPC exclusively on stdout. Writing non-JSON ANSI text to stdout crashes client JSON parsers or drops the initial handshake.
- **Remediation**: Remove `println!` or redirect banner logging to `eprintln!` (stderr).

---

### 5.2. Defect: Blank Line Triggers False EOF in StdioStreamTransport
- **File & Line**: `crates/mcp-protocol/src/transport/stdio.rs:183-186`
- **Code**:
  ```rust
  match lines.next_line().await {
      Ok(Some(line)) => {
          let trimmed = line.trim();
          if trimmed.is_empty() {
              return Ok(None); // <-- Interpreted as EOF!
          }
          let msg = serde_json::from_str::<JsonRpcMessage>(trimmed)?;
          Ok(Some(msg))
      }
      Ok(None) => Ok(None),
      Err(e) => Err(TransportError::Io(e.to_string())),
  }
  ```
- **Impact**: In line-delimited JSON-RPC, clients may send empty lines (e.g. carriage returns or spacing). Returning `Ok(None)` causes `server.serve()` to break its loop and shut down the server process.
- **Remediation**: Loop on empty lines until a non-empty line or true EOF (`Ok(None)`) is reached.

---

### 5.3. Defect: Missing SSE Server Mode in `mcp-cli`
- **File & Line**: `crates/mcp-cli/src/main.rs:637-646`
- **Code**:
  ```rust
  McpSubcommands::Serve(s_args) => {
      if s_args.stdio {
          ...
      }
      // If s_args.stdio == false, or s_args.sse_port is provided, execution falls through!
  }
  ```
- **Impact**: Requirement R1 and Acceptance Criterion 1 require spawning `mcp-cli` in both stdio and SSE server modes. The CLI currently has no implementation to launch an HTTP/SSE server when `mcp serve --sse-port <PORT>` is invoked.
- **Remediation**: When `sse_port` is specified (or `!stdio`), bind an Axum HTTP server using `mcp_protocol::transport::sse::SseSessionManager` serving `GET /sse` (SSE event stream emitting `endpoint` event) and `POST /message` (JSON-RPC message receiver).

---

### 5.4. Defect: `$/cancelRequest` Notification Discarded
- **File & Line**: `crates/mcp-protocol/src/server.rs:156-178`
- **Code**:
  ```rust
  match notif.method.as_str() {
      "notifications/initialized" => { ... }
      "notifications/cancelled" => { ... }
      other => { debug!("Received unhandled notification: '{}'", other); }
  }
  ```
- **Impact**: Standard IDE clients send `$/cancelRequest` with `{"requestId": ...}` or `{"id": ...}`. Currently, `McpServer` ignores this method entirely, failing Requirement R4.
- **Remediation**: Add a handler for `$/cancelRequest` extracting `id` or `requestId` and triggering the cancellation token.

---

### 5.5. Defect: Disconnected Tool Cancellation & Process Leaks
- **File & Line**: `crates/mcp-cli/src/main.rs:336-348` and `154-165`
- **Impact**:
  1. Tool closures do not propagate `_ctx.cancellation_token` to `disp.dispatch()`.
  2. `tokio::process::Command` does not use `.kill_on_drop(true)`.
  3. When an agent cancels a long-running command (e.g. `cargo build`), the underlying OS process keeps running in the background as an orphaned process.
- **Remediation**:
  - Connect `_ctx.cancellation_token` to the task dispatch handle.
  - Set `.kill_on_drop(true)` on `tokio::process::Command` in `execute_cli`.

---

### 5.6. Defect: `mcp-tests` Compilation Failures & Missing Dependencies
- **File & Line**: `crates/mcp-tests/Cargo.toml` & `crates/mcp-tests/tests/tier2_boundaries.rs`
- **Impact**: Running `cargo test` fails to compile `mcp-tests` because `axum` and `mcp-cli` are missing from `crates/mcp-tests/Cargo.toml` `[dependencies]`. Furthermore, test files use outdated field accessors on `TaskOutput` (`out.value` instead of `out.data`).
- **Remediation**:
  1. Add `axum = { workspace = true }` and `mcp-cli = { path = "../mcp-cli" }` to `crates/mcp-tests/Cargo.toml`.
  2. Update test assertions in `mcp-tests/tests/tier2_boundaries.rs` to use `out.data` instead of `out.value`.

---

## 6. Actionable Implementation Blueprint for Implementation Agents

To satisfy R1, R2, R3, R4, and all acceptance criteria, the following modifications are recommended:

### 1. In `crates/mcp-protocol`:
1. **Fix Stdio Empty Lines** (`transport/stdio.rs`):
   ```rust
   // Loop until a non-empty line is read or EOF is reached:
   loop {
       match lines.next_line().await {
           Ok(Some(line)) => {
               let trimmed = line.trim();
               if !trimmed.is_empty() {
                   return Ok(Some(serde_json::from_str::<JsonRpcMessage>(trimmed)?));
               }
           }
           Ok(None) => return Ok(None),
           Err(e) => return Err(TransportError::Io(e.to_string())),
       }
   }
   ```
2. **Support `$/cancelRequest`** (`server.rs`):
   ```rust
   "$/cancelRequest" | "notifications/cancelled" => {
       if let Some(params_val) = notif.params {
           let req_id = params_val.get("requestId")
               .or_else(|| params_val.get("id"))
               .and_then(|v| serde_json::from_value::<RequestId>(v.clone()).ok());
           if let Some(id) = req_id {
               if let Some((_, token)) = self.active_requests.remove(&id) {
                   token.cancel();
               }
           }
       }
   }
   ```

### 2. In `crates/mcp-cli`:
1. **Clean up Stdio Output** (`main.rs:639`):
   - Replace `println!` with `eprintln!` so stdout remains pure JSON-RPC.
2. **Implement CLI SSE Server** (`main.rs` & `cli.rs`):
   - Add Axum-based HTTP/SSE listener when `--sse-port <PORT>` is provided or `--stdio=false`.
   - Route `GET /sse` $\to$ creates SSE session, sends `event: endpoint\ndata: /message?sessionId=<ID>\n\n`.
   - Route `POST /message` $\to$ forwards JSON-RPC body to `session.handle_incoming_post(msg)`.
3. **Enhance `write_code_file`** (`main.rs`):
   - Add optional `encoding` (`"utf-8"` or `"base64"`).
   - Add optional `mode` (integer permissions, e.g. `0o755`).
4. **Enhance `read_code_file`** (`main.rs`):
   - Add optional `start_line` (1-indexed) and `end_line` (1-indexed).
   - Add optional `encoding` (`"utf-8"` or `"base64"`).
   - Read bytes via `tokio::fs::read` to support binary assets and handle non-UTF-8 files gracefully.
5. **Enhance `list_directory`** (`main.rs`):
   - Add optional `recursive: bool` (default `false`) and `max_depth: usize` (default `1`).
   - Add metadata fields: `modified_ms`, `is_readonly`, `is_symlink`.
6. **Harden `execute_cli_command`** (`main.rs`):
   - Set `.kill_on_drop(true)` on `tokio::process::Command`.
   - Link `_ctx.cancellation_token` to task execution so `cancel` aborts the shell process immediately.
   - Set `is_error: Some(true)` in `CallToolResult` if process exits with non-zero code.
7. **Enhance `calculate_layer_offload`** (`main.rs`):
   - Accept optional `context_tokens: usize` (default `4096`).
   - Accept optional `safety_margin: f64` (default `0.15`).

---

## 7. Conclusion

The core MCP infrastructure (`mcp-protocol`) is architecturally sound and compiles cleanly with sub-millisecond dispatch and robust JSON Schema validation. However, to pass the IDE integration test suite and realistic `@agent` workflows, the identified gaps in tool parameter support, stdout contamination, Stdio/SSE server transport handling, and cooperative child process cancellation must be remediated.
