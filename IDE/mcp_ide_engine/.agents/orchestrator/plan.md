# Master Plan: High-Performance Rust MCP CLI & IDE Engine

## Objective
Design, implement, rigorously test, and benchmark a high-performance multithreaded Rust CLI and IDE engine with native Model Context Protocol (MCP) client/server support and dynamic local resource-aware model allocation.

## Execution Tracks
1. **Survey Phase (Step 0)**
   - Explorer 1: Core multithreaded runtime, non-blocking task dispatcher, worker pool architecture, CLI interface (clap, tokio, crossbeam/rayon).
   - Spec Miner 2: Official MCP spec extraction (JSON-RPC 2.0, stdio & HTTP/SSE transports, tools, prompts, resources, protocol lifecycle, schema validation).
   - Explorer 3: System resource monitor (sysinfo, NVML/DirectX GPU detection, memory/VRAM tracking, model picking heuristic) + Unified IDE (Ratatui TUI + Axum Web API / WebSocket frontend) + Benchmark Harness (<5ms dispatch overhead).

2. **Synthesis & Architecture Blueprint (Step 1)**
   - Consolidate explorer/miner findings into `PROJECT.md` and `TEST_INFRA.md`.
   - Formulate modular Cargo workspace structure (`mcp-core`, `mcp-protocol`, `mcp-resource`, `mcp-tui`, `mcp-server`, `mcp-cli`, etc.).
   - Define strict interface contracts between modules.

3. **Parallel Execution (Step 2 & 3)**
   - Dual-Track Execution:
     - Implementation Sub-orchestrators for Core Engine, MCP Subsystem, Resource Allocation & Dynamic Routing, IDE (TUI + Web API).
     - E2E Testing Orchestrator / Test Writers for 4-tier requirement-driven opaque-box test suite (Tiers 1-4).
   - Every implementation milestone gated by:
     - Compilation & Unit Tests
     - 2x Reviewers (APPROVE)
     - 2x Challengers (Empirical Verification)
     - 1x Forensic Auditor (CLEAN - Binary Veto)

4. **Integration & Final Verification (Step 4)**
   - Phase 1: 100% Pass on all E2E test suite tiers (Tiers 1-4).
   - Phase 2: Adversarial coverage hardening (Tier 5) with Challengers probing race conditions, deadlocks, throughput limits, and edge cases.
   - Benchmark verification: <5ms dispatch latency under load, 50+ concurrent tasks with zero deadlocks.

5. **Final Presentation & Reporting (Step 5)**
   - Generate full project summary, benchmarks, verification results, and notify Sentinel via `send_message`.
