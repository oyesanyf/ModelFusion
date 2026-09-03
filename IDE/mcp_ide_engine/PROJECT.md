# Project: High-Performance Multithreaded Rust CLI & IDE Engine with Native MCP and Dynamic Resource Allocation

## Architecture Overview
The system is built as a high-throughput, low-latency, modular Rust workspace designed for asynchronous execution, zero lock contention, native Model Context Protocol (MCP) support, real-time hardware telemetry, and unified developer tooling across CLI, TUI, and Web interfaces.

```
                               ┌────────────────────────────────────────────────┐
                               │             mcp-cli (Binary Crate)             │
                               │   Clap v4 CLI / Reedline REPL / JSON & Text    │
                               └──────┬──────────────────┬──────────────────────┘
                                      │                  │
               ┌──────────────────────┴──────┐    ┌──────┴──────────────────────┐
               │    mcp-tui (Ratatui IDE)    │    │     mcp-web (Axum IDE/API)  │
               │ Dashboard / Task / Telemetry│    │ REST / SSE / WebSockets / UI│
               └──────────────┬──────────────┘    └──────────────┬──────────────┘
                              │                                  │
                              └────────────────┬─────────────────┘
                                               │
               ┌───────────────────────────────┴────────────────────────────────┐
               │             Universal Command Bus & Event Bus                  │
               └──────┬────────────────────────┬────────────────────────┬───────┘
                      │                        │                        │
       ┌──────────────┴──────────────┐ ┌───────┴──────────────┐ ┌───────┴──────────────┐
       │     crates/mcp-core         │ │  crates/mcp-protocol │ │  crates/mcp-resource │
       │ Tokio Async Runtime Bridge  │ │ JSON-RPC 2.0 Engine  │ │ Hardware Telemetry   │
       │ Rayon Work-Stealing Pool    │ │ Client: Stdio & SSE  │ │ CPU / RAM / GPU NVML │
       │ 5-Level Priority Scheduler  │ │ Server: Tools/Prompt │ │ Dynamic Model Tier   │
       │ DashMap Task & Service Reg  │ │ Schema Validation    │ │ KV & VRAM Sizing     │
       │ Cooperative CancellationToken│ │ Sub-ms Tool Dispatch│ │ Layer Offloading     │
       └─────────────────────────────┘ └──────────────────────┘ └──────────────────────┘
                      │                        │                        │
       ┌──────────────┴────────────────────────┴────────────────────────┴───────┐
       │                   crates/mcp-bench & crates/mcp-tests                  │
       │    Criterion Latency Benchmarks (<5ms) & 50+ Concurrent Stress Tests   │
       └────────────────────────────────────────────────────────────────────────┘
```

---

## Feature Inventory

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Tokio Async Core Runtime | Multi-threaded async engine with work-stealing reactor for non-blocking I/O | M1 | R1 |
| 2 | Rayon Compute Worker Pool | Offloads CPU-intensive analysis and computation without starving async reactor | M1 | R1 |
| 3 | 5-Level Priority Task Scheduler | Multi-lane queue with starvation prevention and priority-ordered execution | M1 | R1 |
| 4 | Universal Command Registry | Centralized registry for all executable commands, tools, and actions | M1 | R1, R4 |
| 5 | Lock-Free Task Registry | DashMap-backed state store for concurrent task tracking and metrics | M1 | R1 |
| 6 | Cooperative Cancellation Token | Hierarchical cancellation propagation with deterministic cleanup | M1 | R1 |
| 7 | Task Execution Telemetry | High-resolution quanta timer recording dispatch, queue, and execution latency | M1 | R1, R5 |
| 8 | JSON-RPC 2.0 Protocol Engine | Fast serializer/deserializer and protocol envelope routing | M2 | R2 |
| 9 | Stdio MCP Transport | Line-delimited JSON-RPC over stdin/stdout with stderr log separation | M2 | R2 |
| 10 | HTTP / SSE MCP Transport | Asynchronous Server-Sent Events stream with HTTP POST command endpoint | M2 | R2 |
| 11 | MCP Protocol Lifecycle | Initialization handshake, capability negotiation, and graceful shutdown | M2 | R2 |
| 12 | MCP Tool Registry & Execution | Tool registration, JSON Schema validation, sub-millisecond isolated dispatch | M2 | R2 |
| 13 | MCP Resource Subsystem | Static/dynamic resource provider with URI template resolution and subscriptions | M2 | R2 |
| 14 | MCP Prompt Management | Prompt catalog, parameter interpolation, and structured message generation | M2 | R2 |
| 15 | MCP Client Subsystem | Process supervision for external MCP child servers and SSE connections | M2 | R2 |
| 16 | MCP Server Subsystem | Exposes engine capabilities, local tools, and telemetry to external MCP hosts | M2 | R2 |
| 17 | Tool Error Isolation | Captures tool failures gracefully via isError response without process crash | M2 | R2 |
| 18 | Cross-Platform Telemetry Engine | Real-time probing of host CPU usage, core count, and system RAM via sysinfo | M3 | R3 |
| 19 | Multi-Backend GPU Detection | GPU detection supporting NVML, Windows DXGI, and sysinfo fallback | M3 | R3 |
| 20 | Dynamic VRAM/RAM Tracker | Background async polling with non-blocking watch channel snapshot updates | M3 | R3 |
| 21 | Model Memory Sizing Formulas | Precise computation of model weights, KV cache, activation buffer + 15% margin | M3 | R3 |
| 22 | Dynamic Model Selector | Classifies model fit tiers (Small, Medium, Large, Cloud) based on available RAM/VRAM | M3 | R3 |
| 23 | GPU Layer Offloading Calculator | Computes maximum number of model layers safely offloadable to GPU VRAM | M3 | R3 |
| 24 | Interactive Ratatui TUI | 5-tab terminal IDE (Dashboard, Tasks/Threads, Telemetry, MCP Tools, Logs) | M4 | R4 |
| 25 | Embedded Axum Web & API Server | REST API, SSE event streams, full-duplex WebSockets, and embedded HTML IDE | M4 | R4 |
| 26 | Universal Tool Parity | 100% identical command execution, schema validation, and streaming output | M4 | R4 |
| 27 | Clap v4 CLI Interface | Command-line tool with rich subcommands, JSON output, and non-blocking I/O | M5 | R1, R4 |
| 28 | Interactive Reedline REPL | Interactive shell with syntax highlighting, auto-completion, and command history | M5 | R1, R4 |
| 29 | 50+ Concurrent Task Stress Test | High-concurrency harness validating zero deadlocks and zero race conditions | M6 / Test | R1, R5 |
| 30 | Fast Dispatch Latency Benchmark | Criterion latency suite validating < 5ms dispatch overhead under load | M6 / Test | R5 |
| 31 | 4-Tier Opaque-Box E2E Suite | 100% passing E2E verification across all user requirement tiers | M6 / Test | R5 |
| 32 | Adversarial Hardening (Tier 5) | White-box stress testing, failure injection, and coverage boundary hardening | M6 / Test | R5 |
| 33 | Stdio Clean JSON-RPC Stream & Newline Handling | Strict stderr-only logging, non-JSON filter, blank line handling | M7 | R1 |
| 34 | CLI HTTP/SSE MCP Server Engine | Full MCP 2024-11-05 SSE JSON-RPC listener in mcp-cli serve --sse-port | M7 | R1 |
| 35 | IDE Cancellation & Leak-Free Process Control | $/cancelRequest & notifications/cancelled, kill_on_drop child process management | M7 | R4 |
| 36 | Realistic IDE Client Simulation Test Suite | Child-process stdio & SSE simulation, 8 @agent tools, 30+ concurrency stress | M8 | R1, R2, R3, R4 |


---

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Core Multithreaded Engine & Dispatcher | `crates/mcp-core`: Tokio/Rayon runtime, 5-level priority queue, cancellation, DashMap registry, command bus, telemetry | none | DONE |
| M2 | Model Context Protocol (MCP) Subsystem | `crates/mcp-protocol`: JSON-RPC 2.0, Stdio & SSE transports, Client & Server modes, Tool/Resource/Prompt engines | M1 | DONE |
| M3 | Dynamic Resource Telemetry & Model Selector | `crates/mcp-resource`: CPU/RAM/GPU monitoring (NVML/DXGI/sysinfo), model memory formulas, tier routing & layer offloader | M1 | DONE |
| M4 | Unified IDE Interfaces (TUI & Web) | `crates/mcp-tui` & `crates/mcp-web`: Ratatui 5-tab TUI, Axum REST/WebSocket server, embedded dashboard with tool parity | M1, M2, M3 | DONE |
| M5 | Unified CLI Binary, REPL & Integration | `crates/mcp-cli`: Clap v4 CLI, Reedline REPL, top-level integration, end-to-end command routing | M1, M2, M3, M4 | DONE |
| M6 | Final Verification, Hardening & Benchmarks | `crates/mcp-bench`, `crates/mcp-tests`: 100% E2E test pass (Tiers 1-4), Tier 5 Adversarial hardening, 50+ concurrency stress test, < 5ms benchmark | M5, TEST_READY | DONE |
| M7 | IDE MCP Engine, Transports & Cancellation Hardening | `crates/mcp-protocol`, `crates/mcp-cli`: Stdout leak fix, Stdio EOF fix, CLI SSE server mode, $/cancelRequest handling, child process leak fix | M1-M6 | DONE |
| M8 | IDE Client Simulation & Concurrency Test Suite | `crates/mcp-tests`: Child process spawn (stdio & SSE), full handshake, all 8 @agent tools, 30+ concurrency stress, <100ms cancellation | M7 | DONE |




---

## Interface Contracts

### 1. `mcp-core` $\leftrightarrow$ `mcp-protocol`
- **Command Dispatch**: `TaskDispatcher::dispatch(CommandRequest) -> TaskHandle<CommandResponse>`
- **Cancellation**: `CancellationToken::child_token()` passed down into JSON-RPC handler tasks.
- **Telemetry Record**: `TelemetrySink::record_dispatch(tool_name: &str, duration: Duration)`.

### 2. `mcp-core` $\leftrightarrow$ `mcp-resource`
- **Telemetry Watcher**: `ResourceMonitor::subscribe() -> tokio::sync::watch::Receiver<SystemSnapshot>`.
- **Model Recommendation**: `ModelSelector::recommend(task_requirements: &ModelRequirements) -> AllocationDecision`.

### 3. `mcp-core` $\leftrightarrow$ `mcp-tui` / `mcp-web` / `mcp-cli`
- **Command Registry**: `CommandRegistry::register(CommandDefinition)`, `CommandRegistry::list() -> Vec<CommandMetadata>`.
- **Event Streaming**: `EventBus::subscribe() -> broadcast::Receiver<EngineEvent>`.

---

## Code Layout

```
mcp_ide_engine/
├── Cargo.toml                     # Root workspace manifest
├── Cargo.lock
├── PROJECT.md                     # Master project architecture & milestones
├── TEST_INFRA.md                  # E2E test infrastructure specification
├── TEST_READY.md                  # Signal for test suite completion
├── crates/
│   ├── mcp-core/                  # Multithreaded runtime, scheduler, command bus
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── runtime.rs         # Tokio + Rayon execution bridge
│   │       ├── scheduler.rs       # 5-level priority queue with starvation prevention
│   │       ├── registry.rs        # Universal CommandRegistry & DashMap task table
│   │       ├── cancellation.rs    # Cooperative cancellation token hierarchy
│   │       └── telemetry.rs       # Nanosecond latency metrics & event bus
│   ├── mcp-protocol/              # Complete Model Context Protocol implementation
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── types.rs           # JSON-RPC 2.0 and MCP schema types
│   │       ├── transport/         # Stdio and HTTP/SSE transport implementations
│   │       │   ├── mod.rs
│   │       │   ├── stdio.rs
│   │       │   └── sse.rs
│   │       ├── client.rs          # MCP Client supervisor and connection pool
│   │       ├── server.rs          # MCP Server engine and request router
│   │       ├── tools.rs           # Tool registration, schema validation, execution
│   │       ├── resources.rs       # Resource catalog, reading, and subscriptions
│   │       └── prompts.rs         # Prompt catalog and argument interpolation
│   ├── mcp-resource/              # Resource telemetry & dynamic model allocator
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── telemetry.rs       # Real-time CPU, RAM, and GPU probing
│   │       ├── gpu.rs             # Multi-backend GPU detection (NVML, DXGI, sysinfo)
│   │       ├── sizing.rs          # Model weight, KV cache, and activation formulas
│   │       └── selector.rs        # Dynamic model tier classifier & layer offloader
│   ├── mcp-tui/                   # Interactive Terminal User Interface (Ratatui)
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── app.rs             # TUI application state machine
│   │       ├── ui.rs              # 5-tab rendering layout & widgets
│   │       └── event.rs           # Crossterm terminal input & background event loop
│   ├── mcp-web/                   # Embedded Web & API server (Axum)
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs
│   │       ├── server.rs          # Axum router, REST endpoints, SSE & WebSocket
│   │       └── assets.rs          # Embedded HTML/JS/CSS IDE dashboard
│   ├── mcp-cli/                   # Main executable CLI & Reedline REPL
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── main.rs
│   │       ├── cli.rs             # Clap v4 argument definition and parsing
│   │       └── repl.rs            # Interactive Reedline REPL
│   ├── mcp-bench/                 # Latency & throughput Criterion microbenchmarks
│   │   ├── Cargo.toml
│   │   └── benches/
│   │       ├── dispatch.rs        # Task dispatch latency benchmarks (<5ms)
│   │       └── jsonrpc.rs         # Serialization & tool invocation benchmarks
│   └── mcp-tests/                 # High-concurrency stress tests & E2E suite
│       ├── Cargo.toml
│       └── tests/
│           ├── concurrency_stress.rs  # 50+ simultaneous tasks stress test
│           ├── tier1_features.rs      # Feature coverage
│           ├── tier2_boundaries.rs    # Boundary and edge cases
│           ├── tier3_combinations.rs  # Cross-feature interactions
│           └── tier4_scenarios.rs     # Real-world IDE and MCP workflows
└── .agents/                       # Agent metadata, plans, progress, handoffs
```
