# Original User Request

## 2026-09-02T16:12:39Z

Design and build a high-performance, multithreaded Rust CLI and IDE engine with native Model Context Protocol (MCP) support and dynamic local resource-aware model allocation.

Working directory: C:\Users\oyesanyf\.gemini\antigravity\scratch\mcp_ide_engine
Integrity mode: development

## Requirements

### R1. Multithreaded Core Engine & CLI
Deliver a high-throughput, low-latency command-line interface and execution runtime in Rust utilizing asynchronous concurrency and worker thread pools to handle parallel execution of developer tasks, code analysis, and tool calls without blocking.

### R2. Full Model Context Protocol (MCP) Integration
Implement a comprehensive MCP subsystem supporting both MCP client and server modes (over stdio and HTTP/SSE transports). The runtime must discover, register, execute, and monitor all configured MCP tools, prompts, and resources with strict validation and sub-millisecond dispatch overhead.

### R3. Dynamic Local Resource Allocation & Model Selector
Implement a real-time system resource monitor that probes available CPU threads, system RAM, and GPU/VRAM capacity. The engine must dynamically assess hardware limits and recommend or route inference and agent tasks to the optimal local model (or cloud fallback) based on real-time resource availability.

### R4. Unified IDE with Complete CLI & Tool Parity
Provide an interactive IDE interface (TUI and embedded web/API frontend) that exposes 100% of the CLI tools, command registry, MCP tool execution views, thread status monitors, and resource utilization metrics.

### R5. Verification, Test Harness & Benchmarking
Provide a complete automated test suite and benchmark suite validating end-to-end command execution, concurrent MCP tool invocation under load, resource metric accuracy, and error handling.

## Acceptance Criteria

### Core & Concurrency
- [ ] `cargo build --release` compiles without errors or unresolved warnings.
- [ ] All CLI commands execute concurrently across worker threads with verified non-blocking I/O.
- [ ] Concurrency stress test demonstrates parallel execution of 50+ simultaneous tasks with zero race conditions or deadlocks.

### MCP Subsystem
- [ ] MCP client and server conform to the Model Context Protocol specification for tool discovery, schema inspection, and execution.
- [ ] Multiple MCP tools can be invoked in parallel with isolated execution contexts and structured JSON-RPC responses.
- [ ] Errors from individual MCP tools are captured gracefully without crashing the host process.

### Resource Allocation & Model Picking
- [ ] Live resource telemetry accurately reports host CPU utilization, available RAM, and GPU detection.
- [ ] Model selector algorithm correctly classifies model fit tiers (e.g., small, medium, large) matching current available RAM/VRAM constraints.

### IDE Parity & Tooling
- [ ] IDE interface renders real-time views for active threads, resource graphs, registered CLI commands, and MCP tool catalogs.
- [ ] Any command callable via CLI is executable from the IDE with identical results and real-time streaming output.

### Verification & Quality
- [ ] `cargo test` passes 100% of unit, integration, and regression tests.
- [ ] Benchmark suite validates fast dispatch latency (< 5ms dispatch overhead for internal commands).

## 2026-09-03T19:26:42Z

Execute comprehensive, realistic IDE-mode integration tests and verification for all Model Context Protocol (MCP) tools and endpoints, replicating how AI agents (@agent) and developer extensions interact with the engine in Antigravity IDE, VS Code, and Cursor.

Working directory: C:\Users\oyesanyf\.gemini\antigravity\scratch\mcp_ide_engine
Integrity mode: development

## Requirements

### R1. Realistic IDE Client Simulation
Implement end-to-end integration test harnesses that spawn the MCP engine as a child process and communicate strictly over MCP 2024-11-05 JSON-RPC protocol transports (both stdio and HTTP/SSE). The harness must execute the full IDE client lifecycle: protocol handshake (`initialize`, `notifications/initialized`), capability negotiation, tool/resource/prompt discovery, and clean shutdown.

### R2. End-to-End @agent Tool Suite Testing
Test every MCP tool exposed to the IDE with realistic developer agent workflows:
- **Code Generation (`write_code_file`)**: Generate source files and scaffolding, verifying file writes, permissions, and directory tree creation.
- **Context Inspection (`read_code_file` & `list_directory`)**: Inspect workspace trees and retrieve file contents with exact byte fidelity.
- **Process Execution (`execute_cli_command`)**: Run build tools (`cargo`, `git`, compilers) asynchronously across background worker threads, capturing real-time stdout, stderr, duration, and exit codes.
- **Hardware Telemetry & Model Routing (`get_telemetry`, `recommend_best_model`, `calculate_layer_offload`)**: Probe host CPU, RAM, and GPU capacity and verify dynamic model tier classification and VRAM/RAM layer offload plans.
- **Priority Task Dispatch (`run_command`)**: Verify priority routing and non-blocking execution across the multi-lane scheduler.

### R3. High-Concurrency Multi-Tab / Multi-Agent Stress Testing
Simulate multiple concurrent IDE editor tabs and parallel `@agent` tool calls (30+ simultaneous JSON-RPC requests across worker threads), asserting non-blocking behavior, thread isolation, and zero race conditions or deadlocks.

### R4. Cooperative Cancellation & Error Recovery
Verify that cancellation tokens sent from the IDE (`$/cancelRequest` / `notifications/cancelled`) immediately terminate in-flight shell processes and queue items without orphan leaks, and verify that invalid arguments or tool failures return structured JSON-RPC errors without crashing the server process.

## Acceptance Criteria

### IDE MCP Protocol & Lifecycle
- [ ] Automated test suite spawns `mcp-cli` in stdio and SSE server modes, completing the full MCP handshake.
- [ ] `tools/list`, `resources/list`, and `prompts/list` return valid JSON schemas matching the MCP specification.

### Tool Parity & Code Generation
- [ ] `write_code_file` successfully generates nested files and directories, verified by `read_code_file`.
- [ ] `execute_cli_command` runs shell commands non-blockingly, returning stdout, stderr, and correct exit codes.
- [ ] Resource tools return live host hardware telemetry (NVML GPU, RAM, CPU) and calculate valid layer offloading.

### Concurrency & Reliability
- [ ] 30+ simultaneous IDE tool calls execute concurrently with zero timeouts, deadlocks, or crashed connections.
- [ ] In-flight task cancellation triggered by the IDE client cleanly aborts execution within 100ms.
- [ ] `cargo test` executes the complete IDE MCP integration test suite with 100% passing results.
