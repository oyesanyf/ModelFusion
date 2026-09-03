# Handoff Report: MCP Tools, Schemas, and Endpoints Survey

**Agent**: `survey_explorer_gen3_1`  
**Working Directory**: `C:\Users\oyesanyf\.gemini\antigravity\scratch\mcp_ide_engine\.agents\survey_explorer_gen3_1`  
**Handoff Type**: Hard (Investigation complete)  
**Detailed Report**: `analysis.md` (in same directory)

---

## 1. Observation

1. **Tool Registration in `crates/mcp-cli`**:
   - In `crates/mcp-cli/src/main.rs:281-532` (`setup_default_mcp_server`), all 8 MCP tools are registered on `McpServer::tools()`:
     - `run_command` (`main.rs:286-321`)
     - `execute_cli_command` (`main.rs:325-349`)
     - `write_code_file` (`main.rs:353-377`)
     - `read_code_file` (`main.rs:381-404`)
     - `list_directory` (`main.rs:408-430`)
     - `get_telemetry` (`main.rs:434-445`)
     - `recommend_best_model` (`main.rs:449-469`)
     - `calculate_layer_offload` (`main.rs:473-506`)
   - `crates/mcp-protocol` contains the tool registry engine (`tools.rs:136-261`), schema compiler (`schema.rs`), and server dispatcher (`server.rs`), but does not pre-register application tools.
2. **Deficiencies in Tool Implementations**:
   - `write_code_file`: Path creation is supported (`main.rs:207`), but file permissions are not configurable and binary/base64 writing is unsupported (`main.rs:199, 212`).
   - `read_code_file`: Uses `tokio::fs::read_to_string` (`main.rs:235`), failing on non-UTF-8 or binary files; lacks line range parameters (`start_line`, `end_line`).
   - `list_directory`: Only inspects the single directory level (`main.rs:254-268`); no `recursive` or `max_depth` parameter; metadata lacks timestamps and permissions.
   - `execute_cli_command`: Buffers execution output with `proc.output().await` (`main.rs:168`) without streaming; ignores `_ctx.cancellation_token` (`main.rs:336`); does not set `.kill_on_drop(true)` (`main.rs:154-165`), creating orphan background processes upon cancellation.
   - `calculate_layer_offload`: Hardcodes `context_tokens = 4096` and `safety_margin = 0.15` (`main.rs:503`).
3. **Specification Conformance (MCP 2024-11-05)**:
   - `tools/list` (`server.rs:221-228`), `resources/list` (`server.rs:284-291`), and `prompts/list` (`server.rs:391-398`) serialize to valid JSON-RPC 2.0 responses using `camelCase` and conform to MCP 2024-11-05 schemas.
   - Only 1 static resource (`telemetry://system/status`) and 1 prompt template (`analyze_task`) are registered by default in `main.rs:510-530`.
4. **Transport & Protocol Critical Bugs**:
   - **Stdout Contamination**: `crates/mcp-cli/src/main.rs:639` emits an ANSI string (`println!("{}", "Starting MCP Server on standard I/O streams...".green());`) directly into stdout, corrupting JSON-RPC stream framing for stdio clients.
   - **Premature EOF on Blank Line**: `crates/mcp-protocol/src/transport/stdio.rs:185` returns `Ok(None)` when `line.trim().is_empty()`, causing `server.serve()` to break its event loop and terminate.
   - **Missing CLI SSE Server**: `crates/mcp-cli/src/main.rs:637-646` ignores `--sse-port` and non-stdio serve requests.
   - **Ignored `$/cancelRequest`**: `crates/mcp-protocol/src/server.rs:156-178` only checks for `notifications/cancelled`; `$/cancelRequest` is dropped.
5. **Test Suite Compilation Defect**:
   - `crates/mcp-tests/Cargo.toml` lacks `axum` and `mcp-cli` dependencies.
   - `tier2_boundaries.rs` accesses obsolete field `out.value` instead of `out.data` on `TaskOutput`.

---

## 2. Logic Chain

1. From **Observation 1 & 2**: All 8 tools are present in `mcp-cli`, but `write_code_file`, `read_code_file`, `list_directory`, and `execute_cli_command` lack parameters needed for realistic IDE agent workflows (permissions, binary/base64 encoding, line ranges, recursive directory trees, and streaming output).
2. From **Observation 2 & 4**: Because `execute_cli_command` discards `_ctx.cancellation_token` and does not set `.kill_on_drop(true)` on `tokio::process::Command`, cancelling a tool call in Antigravity/VS Code does not terminate the underlying OS process. This violates Acceptance Criterion R4 ("In-flight task cancellation triggered by the IDE client cleanly aborts execution without orphan leaks").
3. From **Observation 4**: In stdio mode, emitting non-JSON text to stdout (`main.rs:639`) corrupts the JSON-RPC channel. Simultaneously, handling blank lines as EOF (`stdio.rs:185`) causes premature server termination. In SSE mode, the lack of an HTTP listener in `mcp-cli` prevents spawning the CLI in SSE server mode.
4. **Conclusion**: While the core architecture and type definitions strictly align with MCP 2024-11-05, the implementation in `mcp-cli` and `mcp-protocol` requires targeted fixes to Stdio/SSE transports, cancellation wiring, and tool schemas/handlers to satisfy the integration test suite and R2/R4 requirements.

---

## 3. Caveats

- **External GPU Hardware**: On machines without dedicated NVIDIA or DXGI GPUs, `get_telemetry` and `recommend_best_model` fall back to sysinfo RAM/CPU and simulated offloading.
- **`mcp-web` vs. `mcp-cli` SSE**: `mcp-web` runs an Axum server with REST/WebSocket APIs, whereas `mcp_protocol::transport::sse::SseSessionManager` is designed for pure MCP JSON-RPC over SSE. The CLI must expose this SSE transport directly on `--sse-port`.

---

## 4. Conclusion

1. **Tool Coverage**: All 8 tools exist in `mcp-cli`, but require schema and handler enhancements:
   - `write_code_file`: add `encoding` (`"utf-8"`/`"base64"`) and `mode` (permissions).
   - `read_code_file`: add `start_line`, `end_line`, and raw byte/binary fallback.
   - `list_directory`: add `recursive: bool` and `max_depth: usize` with extended metadata.
   - `execute_cli_command`: set `.kill_on_drop(true)`, link cancellation tokens, and stream stdout/stderr.
   - `calculate_layer_offload`: expose `context_tokens` and `safety_margin`.
2. **Protocol & Transport Fixes**:
   - Redirect `mcp-cli` banner print to `eprintln!`.
   - Prevent blank lines from returning `Ok(None)` in `StdioStreamTransport`.
   - Implement `$/cancelRequest` handling in `McpServer`.
   - Implement Axum/hyper SSE listener in `mcp-cli` for `mcp serve --sse-port`.

---

## 5. Verification Method

1. **Verify Tool Registrations**:
   Inspect `crates/mcp-cli/src/main.rs:281-532` with `view_file`.
2. **Verify Protocol Types & Specs**:
   Inspect `crates/mcp-protocol/src/types.rs` (`Tool`, `Resource`, `Prompt`, `ListToolsResult`, `InitializeResult`).
3. **Verify Build Health**:
   Run `cargo check --workspace` and `cargo test --no-run`.
4. **Detailed Reference**:
   Read `analysis.md` in this directory for exact code diff blueprints and schema specifications.
