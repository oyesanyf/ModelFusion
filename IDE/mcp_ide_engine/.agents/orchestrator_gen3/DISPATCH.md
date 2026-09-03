# Dispatch Message

## 2026-09-03T19:27:34Z
Project Orchestrator (Gen 3) for MCP IDE Engine.
Objective: Execute comprehensive, realistic IDE-mode integration tests and verification for all Model Context Protocol (MCP) tools and endpoints, replicating how AI agents (@agent) and developer extensions interact with the engine in Antigravity IDE, VS Code, and Cursor.
Requirements: R1 (IDE Client Simulation - stdio & SSE), R2 (E2E @agent Tool Suite Testing), R3 (High-Concurrency Stress Testing 30+ simultaneous requests), R4 (Cooperative Cancellation & Error Recovery).
Acceptance Criteria:
- Automated test suite spawns mcp-cli in stdio and SSE server modes, completing full MCP handshake.
- tools/list, resources/list, prompts/list return valid JSON schemas matching MCP specification.
- write_code_file successfully generates nested files and directories, verified by read_code_file.
- execute_cli_command runs shell commands non-blockingly, returning stdout, stderr, and correct exit codes.
- Resource tools return live host hardware telemetry (NVML GPU, RAM, CPU) and calculate valid layer offloading.
- 30+ simultaneous IDE tool calls execute concurrently with zero timeouts, deadlocks, or crashed connections.
- In-flight task cancellation triggered by the IDE client cleanly aborts execution within 100ms.
- cargo test executes the complete IDE MCP integration test suite with 100% passing results.
