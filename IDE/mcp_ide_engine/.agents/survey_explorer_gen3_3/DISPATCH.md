## 2026-09-03T19:28:40Z
You are survey_explorer_gen3_3.
Your working directory is: C:\Users\oyesanyf\.gemini\antigravity\scratch\mcp_ide_engine\.agents\survey_explorer_gen3_3.
Read C:\Users\oyesanyf\.gemini\antigravity\scratch\mcp_ide_engine\ORIGINAL_REQUEST.md (specifically ## 2026-09-03T19:26:42Z), C:\Users\oyesanyf\.gemini\antigravity\scratch\mcp_ide_engine\PROJECT.md, and C:\Users\oyesanyf\.gemini\antigravity\scratch\mcp_ide_engine\TEST_INFRA.md.

Your objective is to investigate how to implement the integration test suite and harness to verify all acceptance criteria:
1. Inspect existing tests in crates/mcp-tests:
   - What test files exist? What utilities/harnesses exist?
   - Can an integration test spawn mcp-cli binary as a child process in stdio mode and communicate via piped stdin/stdout?
   - Can an integration test spawn mcp-cli in SSE server mode and connect via HTTP/SSE client?
2. Formulate the test architecture for:
   - R1: Spawning mcp-cli child process, full MCP 2024-11-05 handshake, capability discovery, clean shutdown in stdio and SSE.
   - R2: End-to-end testing of each @agent tool (write_code_file, read_code_file, list_directory, execute_cli_command, get_telemetry, recommend_best_model, calculate_layer_offload, run_command).
   - R3: High-concurrency stress test: 30+ simultaneous JSON-RPC tool calls across worker threads with zero timeouts, deadlocks, or crashed connections.
   - R4: Cancellation test: in-flight task cancellation within 100ms via $/cancelRequest, error recovery without server crashes.
3. Determine if tests should be in crates/mcp-tests/tests/ide_mcp_integration.rs or separate files, and how cargo test will run them.

Scope boundary: READ-ONLY. Do not write or edit codebase files.
Write findings to analysis.md and handoff.md in your working directory.
When finished, send a message to your caller (parent) with a concise summary and references to your files.
