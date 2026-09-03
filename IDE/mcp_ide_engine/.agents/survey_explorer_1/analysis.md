# Architectural Survey & Analysis Report: Core Multithreaded Engine, Task Scheduler & CLI

**Author**: Survey Explorer 1 (Core Concurrency Architect)  
**Target Project**: High-Performance Rust MCP CLI & IDE Engine  
**Milestone**: Survey & Architectural Design (M1)  
**Date**: 2026-09-02  
**Status**: COMPLETE  

---

## 1. Executive Summary

This architectural survey and design report establishes the multithreaded concurrency foundation, non-blocking task dispatcher, worker thread pool architecture, command-line interface (CLI) with interactive REPL, execution telemetry, cancellation hierarchies, and concurrency stress testing harness for the **High-Performance Rust MCP Multi-Agent IDE Engine**.

### Core Performance & Architectural Targets
1. **Sub-Millisecond Dispatch Overhead**: Internal task scheduling latency guaranteed under $1.0\text{ ms}$ (p95) and $< 5.0\text{ ms}$ SLA under maximum load.
2. **50+ Concurrent Task Saturation**: Rock-solid, deadlock-free, race-condition-free execution across 50 to 1,000+ simultaneous tasks with priority scheduling.
3. **Non-Blocking Dual-Runtime Execution**: Clean segregation between async I/O tasks (Tokio multi-threaded reactor) and CPU-intensive compute workloads (dedicated Rayon work-stealing thread pool).
4. **Cooperative Hierarchical Cancellation**: Microsecond cascading cancellation using `tokio_util::sync::CancellationToken` ensuring zero orphan child tasks or hanging sockets.
5. **Unified CLI & REPL Parity**: High-ergonomic Clap v4 command interface paired with an asynchronous REPL shell, full JSON-mode output for machine consumption, and seamless parity with TUI and Web IDE frontends.

---

## 2. Requirements Decomposition for R1 & System Concurrency

| Requirement Area | Specification / Acceptance Criteria | Architectural Solution |
| :--- | :--- | :--- |
| **R1.1 Runtime Concurrency** | Asynchronous execution of developer tasks, code analysis, and tool calls without blocking. | Tokio multi-threaded runtime (`rt-multi-thread`) with configurable worker threads matching logical CPU cores. |
| **R1.2 Compute Offloading** | CPU-heavy workloads (AST parsing, indexing, compression, diffs) must not stall I/O reactor. | Dedicated Rayon compute thread pool bridged to Tokio via non-blocking oneshot channels. |
| **R1.3 Priority Scheduling** | Developer tasks must be ordered by priority with starvation prevention. | Multi-lane priority scheduler (`Critical`, `High`, `Normal`, `Low`, `Background`) with weighted queue polling. |
| **R1.4 CLI & Machine Parity** | Rich CLI with subcommands, interactive REPL, flags, and JSON output mode. | Clap v4 derive API with dual output formatters (Human ANSI table/tree vs Strict JSON Schema). |
| **R1.5 Telemetry & Metrics** | Real-time tracking of thread utilization, queue latency, task states, and errors. | High-resolution telemetry via `metrics` and `quanta`, Tokio `RuntimeMetrics` sampler, and `tracing`. |
| **R1.6 Concurrency Safety** | 50+ simultaneous tasks with zero race conditions or deadlocks. | Lock-free concurrent data structures (`DashMap`, `crossbeam`), strict lock hierarchy, no sync mutexes held across `.await`. |

---

## 3. Concurrency & Runtime Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             Engine Orchestration Layer                           │
│     (TaskScheduler, SessionManager, MCP Client/Server Registry, IDE Router)      │
└───────────────────────┬──────────────────────────────────┬───────────────────────┘
                        │                                  │
         Async I/O Tasks & MCP Transports          Compute & CPU-Bound Tasks
                        │                                  │
┌───────────────────────▼────────────────┐   ┌─────────────▼───────────────────────┐
│     Tokio Multi-Threaded Runtime       │   │      Rayon Work-Stealing Pool       │
│  - Non-blocking Network & Sockets      │   │  - Syntax Highlighting & AST Parse  │
│  - stdio / HTTP / SSE MCP Transport    │   │  - Diff Generation & Indexing       │
│  - File System Async I/O (tokio::fs)   │   │  - Large JSON Serialization         │
│  - Timers, Tickers & Watchdogs         │   │  - Heavy Regex Code Search          │
│  - Worker Threads: 1..N (Logical Cores)│   │  - Compute Workers: Physical Cores  │
└────────────────────────────────────────┘   └─────────────────────────────────────┘
```

### 3.1 Tokio Multi-Threaded Runtime Configuration

The core runtime uses a customized Tokio multi-threaded scheduler configured via `tokio::runtime::Builder`:

```rust
pub struct EngineRuntimeConfig {
    pub worker_threads: usize,
    pub max_blocking_threads: usize,
    pub thread_name_prefix: String,
    pub thread_keep_alive: std::time::Duration,
    pub enable_io: bool,
    pub enable_time: bool,
}

impl Default for EngineRuntimeConfig {
    fn default() -> Self {
        let logical_cpus = num_cpus::get();
        Self {
            worker_threads: logical_cpus.max(2),
            max_blocking_threads: 512,
            thread_name_prefix: "mcp-worker".to_string(),
            thread_keep_alive: std::time::Duration::from_secs(10),
            enable_io: true,
            enable_time: true,
        }
    }
}
```

#### Thread Naming Convention & Diagnostics
- `mcp-worker-{id}`: Tokio asynchronous event loop workers.
- `mcp-compute-{id}`: Dedicated Rayon compute threads.
- `mcp-io-blocking-{id}`: Blocking file/process spawn pool.
- `mcp-watchdog`: Dedicated deadlock and stall detection watchdog.

### 3.2 Dedicated Compute Thread Pool (Rayon Bridge)

To prevent CPU-intensive compute workloads from starving Tokio async workers (which would increase latency on MCP stdio/SSE socket channels), CPU-bound work is executed on a dedicated Rayon thread pool via an async non-blocking bridge:

```rust
pub struct ComputePool {
    pool: rayon::ThreadPool,
}

impl ComputePool {
    pub fn new(num_threads: usize) -> Result<Self, ComputeError> {
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(num_threads)
            .thread_name(|idx| format!("mcp-compute-{idx}"))
            .build()
            .map_err(ComputeError::ThreadPoolInit)?;
        Ok(Self { pool })
    }

    /// Spawns a compute closure onto the Rayon pool and returns a Tokio Future
    pub async fn spawn_compute<F, R>(&self, f: F) -> Result<R, ComputeError>
    where
        F: FnOnce() -> R + Send + 'static,
        R: Send + 'static,
    {
        let (tx, rx) = tokio::sync::oneshot::channel();
        self.pool.spawn(move || {
            let result = f();
            let _ = tx.send(result);
        });
        rx.await.map_err(|_| ComputeError::ComputeDropped)
    }
}
```

---

## 4. Task Scheduling Engine & Multi-Lane Priority Queue

### 4.1 Priority Classification & Scheduling Semantics

Tasks are classified into 5 discrete priority levels:

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, serde::Serialize, serde::Deserialize)]
#[repr(u8)]
pub enum TaskPriority {
    Critical = 0,   // System emergency, kill signals, heartbeats, watchdog alerts
    High = 1,       // Foreground interactive CLI actions, UI interactions, immediate MCP tool calls
    Normal = 2,     // Standard agent workflow tasks, multi-step tool pipelines
    Low = 3,        // Background AST re-indexing, cache warmups, batch file validations
    Background = 4, // Telemetry log flushing, repository archive checks, deep sweeps
}
```

### 4.2 Multi-Lane Lock-Free Priority Scheduler Design

To eliminate mutex contention when hundreds of tasks are scheduled per second, the scheduler utilizes a **multi-lane bounded queue structure** backed by lock-free queues (`crossbeam_queue::SegQueue`) or partitioned `tokio::sync::mpsc` channels with weighted scheduling:

```rust
pub struct MultiLaneScheduler {
    lanes: [crossbeam_queue::SegQueue<Arc<EngineTask>>; 5],
    notify: tokio::sync::Notify,
    active_tasks: dashmap::DashMap<TaskId, Arc<EngineTask>>,
    metrics: Arc<SchedulerMetrics>,
    weights: [u32; 5], // [16, 8, 4, 2, 1] for starvation prevention
}
```

#### Starvation Prevention Algorithm
1. **Weighted Round-Robin Drain**: In each scheduling cycle, up to $16$ `Critical`, $8$ `High`, $4$ `Normal`, $2$ `Low`, and $1$ `Background` tasks are dispatched.
2. **Aging Mechanism**: Tasks queued longer than $T_{\text{max\_wait}}$ ($5.0\text{ seconds}$ for Normal, $15.0\text{ seconds}$ for Low) are automatically promoted by one priority level.

### 4.3 Task Descriptor & State Machine

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub struct TaskId(uuid::Uuid);

impl TaskId {
    pub fn new_v7() -> Self {
        Self(uuid::Uuid::now_v7())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum TaskState {
    Queued,
    Scheduled,
    Running,
    Paused,
    Completed,
    Failed,
    Cancelled,
    TimedOut,
}

pub struct EngineTask {
    pub id: TaskId,
    pub name: String,
    pub priority: TaskPriority,
    pub state: std::sync::atomic::AtomicU8, // Encodes TaskState
    pub cancellation_token: tokio_util::sync::CancellationToken,
    pub created_at: std::time::Instant,
    pub started_at: parking_lot::RwLock<Option<std::time::Instant>>,
    pub completed_at: parking_lot::RwLock<Option<std::time::Instant>>,
    pub task_type: TaskType,
}
```

```
           ┌──────────┐
           │  Queued  │
           └────┬─────┘
                │
         (Worker dequeues)
                │
                ▼
          ┌───────────┐
          │ Scheduled │
          └─────┬─────┘
                │
          (Exec begins)
                │
                ▼
           ┌─────────┐
    ┌──────┤ Running ├─────────────────────────┐
    │      └────┬────┘                         │
    │           │                              │
(Success)   (Error/Panic)            (Cancellation / Timeout)
    │           │                              │
    ▼           ▼                              ▼
┌───────────┐ ┌────────┐             ┌──────────────────┐
│ Completed │ │ Failed │             │ Cancelled/Timeout│
└───────────┘ └────────┘             └──────────────────┘
```

---

## 5. Cancellation Tokens & Cooperative Interruption

### 5.1 Hierarchical Token Tree

The engine organizes cancellation tokens in a strict hierarchical tree using `tokio_util::sync::CancellationToken`:

```
Engine Root Token (Global Shutdown)
  ├── Session Token (CLI REPL / IDE Connection)
  │     ├── Pipeline Job Token (Multi-Step Tool Orchestration)
  │     │     ├── Task Token 1 (MCP Tool Call A)
  │     │     └── Task Token 2 (Compute Diff B)
  │     └── Direct Task Token (Foreground CLI Command)
```

- When the **Engine Root Token** is cancelled, every session, job, and task is immediately notified.
- When a user presses `Ctrl+C` in interactive CLI mode, only the **current active Task Token** is cancelled, leaving the REPL session alive.

### 5.2 Async Cancellation Idiom & Cleanup Protocol

All asynchronous long-running tasks incorporate cancellation checks at yield points:

```rust
pub async fn execute_task_with_cancellation<F, Fut, R>(
    task: Arc<EngineTask>,
    fut: F,
) -> Result<R, TaskExecutionError>
where
    F: FnOnce(tokio_util::sync::CancellationToken) -> Fut,
    Fut: std::future::Future<Output = Result<R, TaskExecutionError>>,
{
    let token = task.cancellation_token.clone();
    tokio::select! {
        _ = token.cancelled() => {
            task.set_state(TaskState::Cancelled);
            Err(TaskExecutionError::Cancelled)
        }
        res = fut(token) => {
            match &res {
                Ok(_) => task.set_state(TaskState::Completed),
                Err(_) => task.set_state(TaskState::Failed),
            }
            res
        }
    }
}
```

---

## 6. Lock Contention & Deadlock Prevention Strategy

### 6.1 Architectural Rules for Concurrency Safety

1. **No Synchronous Mutexes Across `.await`**:
   The compiler lint `#![deny(clippy::await_holding_lock)]` is enforced across all workspace crates. Standard library mutexes (`std::sync::Mutex`) or `parking_lot::Mutex` must never be held across an `.await` suspension point to prevent thread starvation and deadlocks.
2. **Lock-Free Concurrent Maps (`DashMap`)**:
   Global state tables (such as `TaskRegistry`, `SessionRegistry`, `MCPToolRegistry`) are stored in `dashmap::DashMap`, which partitions data across 64+ independent shards, providing lock-free read access and minimal per-shard lock contention on writes.
3. **Strict Global Lock Order**:
   Where multiple locks must be acquired, the acquisition hierarchy is strictly:
   $$\text{EngineConfigLock} \longrightarrow \text{SessionLock} \longrightarrow \text{TaskLock} \longrightarrow \text{ResourceLock}$$
4. **Channel-Based Actor Communication**:
   Inter-subsystem data flow is decoupled using bounded channels (`tokio::sync::mpsc`, `tokio::sync::broadcast`, `tokio::sync::watch`).

### 6.2 Deadlock & Hang Watchdog

An asynchronous background watchdog task periodically samples running tasks:
- Detects tasks in `Running` state whose execution exceeds the task-specified timeout limit without yielding.
- Logs thread stack traces in debug builds and issues automatic cooperative cancellation to hanging tasks.

---

## 7. Execution Telemetry & Performance Metrics

### 7.1 High-Resolution Telemetry Metrics

```rust
pub struct EngineTelemetry {
    // Atomic Counters & Gauges
    pub active_tasks: std::sync::atomic::AtomicUsize,
    pub queued_tasks_by_priority: [std::sync::atomic::AtomicUsize; 5],
    pub completed_tasks_total: std::sync::atomic::AtomicU64,
    pub failed_tasks_total: std::sync::atomic::AtomicU64,
    pub cancelled_tasks_total: std::sync::atomic::AtomicU64,

    // Latency Tracking (Nanoseconds/Microseconds via quanta)
    pub dispatch_latency_nanos: parking_lot::RwLock<hdrhistogram::Histogram<u64>>,
    pub execution_duration_nanos: parking_lot::RwLock<hdrhistogram::Histogram<u64>>,
}
```

### 7.2 Tokio Runtime Metrics Integration

The engine periodically polls `tokio::runtime::RuntimeMetrics`:
- `workers_count`: Total number of active worker threads.
- `active_tasks_count`: Active futures currently being polled.
- `global_queue_depth`: Tasks waiting in the global scheduler queue.
- `worker_park_count` & `worker_noop_count`: Thread utilization statistics.
- `budget_forced_yield_count`: Cooperative yields triggered by Tokio cooperative scheduling budget.

---

## 8. Command-Line Interface (CLI) & REPL Architecture

### 8.1 Clap v4 Hierarchical Command Structure

```
mcp-engine [GLOBAL_FLAGS] <SUBCOMMAND>
├── run <COMMAND> [OPTIONS]
├── task <SUBCOMMAND>
│   ├── list [--all] [--priority <P>] [--json]
│   ├── status <TASK_ID>
│   ├── cancel <TASK_ID>
│   ├── stream <TASK_ID>
│   └── logs <TASK_ID> [--tail <N>]
├── mcp <SUBCOMMAND>
│   ├── list-tools [--server <NAME>]
│   ├── call <TOOL> --args <JSON> [--server <NAME>]
│   ├── list-prompts
│   ├── list-resources
│   ├── serve [--transport <stdio|sse>] [--port <PORT>]
│   └── inspect <SERVER>
├── resource <SUBCOMMAND>
│   ├── info [--json]
│   ├── top [--interval <MS>]
│   └── recommend --task <TYPE> [--context-length <N>]
├── ide <SUBCOMMAND>
│   ├── tui
│   └── web [--port <PORT>] [--bind <IP>]
├── repl
└── bench <SUBCOMMAND>
    ├── concurrency [--tasks <N>] [--concurrency <C>]
    ├── dispatch [--iterations <N>]
    └── mcp-echo [--requests <N>]
```

### 8.2 Global Flags Specification

- `-v, --verbose`: Increase logging output verbosity (can be repeated: `-vvv`).
- `-q, --quiet`: Suppress all non-essential console output.
- `--output <text|json|compact|table>`: Output rendering format.
- `--threads <NUM>`: Explicit worker thread pool override.
- `--config <PATH>`: Custom TOML configuration path.
- `--timeout <SECONDS>`: Global command timeout.

### 8.3 JSON Output Schema & Machine Parity

Every CLI command supports strict, structured JSON output (`--output json` or `--json`) conforming to typed JSON schemas for programmatic consumption by IDE plugins, scripts, and CI/CD pipelines:

```json
{
  "$schema": "https://mcp-engine.dev/schemas/task_output.json",
  "status": "success",
  "timestamp": "2026-09-02T16:15:00.000Z",
  "data": {
    "task_id": "018e3a2b-8a4e-7b2c-9a1d-4f6c8e9a0b1c",
    "priority": "High",
    "state": "Completed",
    "dispatch_latency_us": 142,
    "execution_duration_us": 12850,
    "result": {
      "tool": "filesystem_read",
      "status": "ok",
      "content": "..."
    }
  },
  "metrics": {
    "active_workers": 16,
    "queue_depth": 0
  }
}
```

### 8.4 Interactive REPL Subsystem

Built with `reedline` and an asynchronous event reactor:
- **Asynchronous Prompt**: Background tasks report completion asynchronously via non-intrusive status line updates without clobbering active input.
- **Tab Auto-Completion**: Context-aware completion for subcommands, MCP tool names, active task IDs, and local file system paths.
- **Signal Handling**: Dedicated Unix/Windows signal handler thread. Pressing `Ctrl+C` sends a cancellation signal to the active foreground task while keeping the REPL process responsive.

---

## 9. Concurrency Stress Testing & Benchmarking Architecture

### 9.1 50+ Concurrent Task Stress Test Suite

The stress testing framework (`mcp-bench` / `crates/mcp-core/tests/concurrency_stress.rs`) validates the engine against 6 rigorous stress profiles:

| Test Profile | Workload Description | Acceptance Invariant |
| :--- | :--- | :--- |
| **Profile 1: High-Concurrency Burst** | 500 simultaneous tasks dispatched across 5 priority levels in a single burst. | 100% completion; zero deadlocks; priority queue order preserved under load. |
| **Profile 2: Async I/O + Compute Hybrid** | 100 concurrent async MCP tool mocks + 50 heavy Rayon compute hashing tasks. | Zero thread starvation; async I/O p95 dispatch latency $< 2.0\text{ ms}$. |
| **Profile 3: Chaos Cancellation Storm** | 200 tasks launched; 50% randomly cancelled at microsecond intervals ($1\text{ ms}$ to $50\text{ ms}$). | Zero resource leaks; all child futures clean up; zero panics or orphaned processes. |
| **Profile 4: Backpressure & Saturation** | Continuous stream of 2,000 tasks exceeding pool capacity. | Memory RSS remains bounded; bounded queues enforce backpressure; zero OOM. |
| **Profile 5: Sub-Millisecond Dispatch Latency** | 10,000 tasks dispatched sequentially and concurrently, measured with `quanta`. | p50 dispatch latency $< 200\ \mu\text{s}$; p95 $< 1.0\text{ ms}$; p99 $< 3.0\text{ ms}$. |
| **Profile 6: Lock Contention & Loom Model Check** | Multi-threaded task registry access under heavy concurrent read/write churn. | Zero race conditions; zero lock inversion; clean Loom state verification. |

### 9.2 Benchmark Latency Verification Harness

```rust
pub struct DispatchBenchmark {
    pub iterations: usize,
    pub concurrency_levels: Vec<usize>, // e.g. [1, 10, 50, 100, 250, 500]
}

pub struct BenchmarkResult {
    pub concurrency: usize,
    pub total_tasks: usize,
    pub throughput_tasks_per_sec: f64,
    pub min_latency_us: f64,
    pub p50_latency_us: f64,
    pub p95_latency_us: f64,
    pub p99_latency_us: f64,
    pub max_latency_us: f64,
}
```

---

## 10. Recommended Cargo Workspace Structure & Crate Decomposition

To ensure modularity, fast incremental compilation, clean separation of concerns, and clean testing boundaries, a 10-crate Cargo workspace is recommended:

```
mcp_ide_engine/
├── Cargo.toml
├── crates/
│   ├── mcp-core/          # Concurrency engine, scheduler, task runtime, cancellation, telemetry
│   ├── mcp-protocol/      # MCP JSON-RPC 2.0 specifications, types, schemas, serialization
│   ├── mcp-transport/     # stdio, SSE, WebSocket transport framing and async codecs
│   ├── mcp-client/        # MCP Client engine, connection pool, tool invocation pipeline
│   ├── mcp-server/        # MCP Server host, tool/prompt/resource registry, server listeners
│   ├── mcp-resource/      # System telemetry (CPU, RAM, GPU/VRAM via sysinfo/NVML/DXGI), model selector
│   ├── mcp-cli/           # Clap CLI, REPL shell, command handlers, formatting
│   ├── mcp-tui/           # Ratatui TUI dashboard (threads, tasks, MCP tools, resource graphs)
│   ├── mcp-web/           # Axum REST & WebSocket server for Web IDE frontend
│   └── mcp-bench/         # Criterion benchmarks and concurrency stress harness
```

### 10.1 Recommended Dependency Matrix

```toml
[workspace]
resolver = "2"
members = [
    "crates/mcp-core",
    "crates/mcp-protocol",
    "crates/mcp-transport",
    "crates/mcp-client",
    "crates/mcp-server",
    "crates/mcp-resource",
    "crates/mcp-cli",
    "crates/mcp-tui",
    "crates/mcp-web",
    "crates/mcp-bench",
]

[workspace.dependencies]
# Concurrency & Async Runtime
tokio = { version = "1.38", features = ["full", "tracing"] }
tokio-util = { version = "0.7", features = ["sync", "codec", "rt"] }
rayon = "1.10"
crossbeam = "0.8"
crossbeam-queue = "0.3"
crossbeam-channel = "0.5"
parking_lot = { version = "0.12", features = ["deadlock_detection", "serde"] }
dashmap = { version = "6.0", features = ["serde", "rayon"] }
futures = "0.3"
futures-util = "0.3"
async-trait = "0.1"

# CLI & REPL
clap = { version = "4.5", features = ["derive", "env", "cargo", "string", "unicode"] }
reedline = "0.32"
colored = "2.1"
comfy-table = "7.1"
indicatif = { version = "0.17", features = ["tokio"] }

# Serialization & Protocols
serde = { version = "1.0", features = ["derive"] }
serde_json = { version = "1.0", features = ["raw_value", "preserve_order"] }
uuid = { version = "1.8", features = ["v7", "serde", "fast-rng"] }

# Telemetry & Observability
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "json", "time"] }
tracing-appender = "0.2"
metrics = "0.23"
metrics-exporter-prometheus = "0.15"
quanta = "0.12"
hdrhistogram = "7.5"

# Error Handling & Utilities
thiserror = "1.0"
anyhow = "1.0"
num_cpus = "1.16"

# Testing & Benchmarking
criterion = { version = "0.5", features = ["async_tokio"] }
proptest = "1.4"
tempfile = "3.10"
```

### 10.2 Workspace Profile Optimizations

```toml
[profile.release]
opt-level = 3
lto = "thin"
codegen-units = 1
panic = "unwind"
strip = "debuginfo"

[profile.bench]
opt-level = 3
lto = "thin"
codegen-units = 1
```

---

## 11. Core Interface Contracts (`mcp-core`)

Below are the primary Rust trait and struct definitions establishing the public API boundary for `mcp-core`:

```rust
pub mod core {
    use std::sync::Arc;
    use tokio_util::sync::CancellationToken;
    use crate::types::*;

    #[async_trait::async_trait]
    pub trait TaskExecutor: Send + Sync + 'static {
        async fn execute(
            &self,
            context: TaskExecutionContext,
            cancellation_token: CancellationToken,
        ) -> Result<TaskOutput, TaskError>;
    }

    pub struct TaskExecutionContext {
        pub task_id: TaskId,
        pub priority: TaskPriority,
        pub session_id: Option<SessionId>,
        pub telemetry: Arc<EngineTelemetry>,
    }

    #[async_trait::async_trait]
    pub trait EngineScheduler: Send + Sync + 'static {
        async fn submit(&self, task: NewTaskRequest) -> Result<TaskId, SchedulerError>;
        async fn cancel(&self, task_id: TaskId) -> Result<(), SchedulerError>;
        async fn get_task(&self, task_id: TaskId) -> Option<Arc<EngineTask>>;
        async fn list_tasks(&self, filter: TaskFilter) -> Vec<Arc<EngineTask>>;
        fn subscribe_events(&self) -> tokio::sync::broadcast::Receiver<EngineEvent>;
        fn telemetry_snapshot(&self) -> TelemetrySnapshot;
    }
}
```

---

## 12. Next Steps for Implementation (M2 Blueprint)

1. **Phase 1: `mcp-core` Engine Implementation**:
   - Implement `EngineRuntimeConfig`, `ComputePool`, `MultiLaneScheduler`, `EngineTask`, and `EngineTelemetry`.
   - Implement unit tests for priority queues, starvation aging, and cooperative cancellation tokens.
2. **Phase 2: `mcp-cli` & REPL Implementation**:
   - Build Clap derive models, JSON formatters, ANSI table formatters, and Reedline asynchronous REPL.
3. **Phase 3: Concurrency Stress Test Suite**:
   - Implement the 6 stress profiles in `crates/mcp-bench` to prove zero deadlocks and $< 1.0\text{ ms}$ dispatch latency across 50+ concurrent tasks.
