# Architectural Specification & Deep Investigation: Resource Allocation, Unified IDE & Benchmark Harness (R3, R4, R5)

**Author:** Survey Explorer 3 (Resource & IDE Engine Architect)  
**Date:** 2026-09-02  
**Target Project:** `mcp_ide_engine` (High-Performance Multithreaded Rust CLI & IDE Engine)  
**Document Version:** 1.0.0-final  

---

## 1. Executive Summary & Architectural Scope

This document provides the exhaustive architectural design, technical specifications, concrete Rust data structures, algorithms, and verification harnesses for Requirements **R3**, **R4**, and **R5** of the `mcp_ide_engine` workspace:

1. **R3: Dynamic Local Resource Allocation & Model Selector**:
   - Real-time, non-blocking telemetry engine probing CPU utilization, available RAM, swap pressure, and GPU/VRAM capacity.
   - Robust cross-platform hardware detection with a 5-tier fallback chain (NVIDIA NVML $\rightarrow$ Windows DXGI $\rightarrow$ Apple Metal $\rightarrow$ Vulkan/wgpu $\rightarrow$ sysinfo Host CPU).
   - Dynamic Model Selector algorithm classifying models across 5 fit tiers (*Micro/Nano*, *Small*, *Medium*, *Large*, and *Cloud Fallback*) with exact KV cache, activation memory, quantization scaling, and layer offloading calculations.
2. **R4: Unified IDE & Tool Parity (TUI + Axum Web/SSE/WS)**:
   - Shared Execution Abstraction (`CommandRegistry`, `TaskDispatcher`, `EventBus`) guaranteeing **100% tool parity** between CLI commands, TUI interactive panels, and Web API/WebSocket endpoints.
   - High-throughput, multi-pane Terminal User Interface (TUI) powered by `ratatui` and `crossterm` featuring live sparklines, gauges, tool catalog runner, and MCP traffic inspector.
   - Embedded Web & API Server powered by `axum` and `tokio-tungstenite` providing full REST endpoints, Server-Sent Events (SSE) telemetry feeds, full-duplex WebSockets for streaming I/O, and an embedded single-binary dashboard.
3. **R5: Verification, Concurrency Stress & Benchmark Harness**:
   - `criterion`-based microbenchmarking suite validating task dispatch latency ($< 5\text{ms}$ benchmark ceiling, targeting $< 50\mu\text{s}$ async overhead), JSON-RPC serialization, and lock-free broadcast throughput.
   - High-concurrency stress test suite validating 50+ simultaneous asynchronous tasks with zero deadlocks, race conditions, or thread starvation under barrier synchronization.
   - 4-tier automated test framework (Unit, Subsystem, Stress/Concurrency, and End-to-End Opaque-Box).

```
+---------------------------------------------------------------------------------------+
|                                   USER INTERFACES                                     |
|  +------------------------+  +-------------------------+  +------------------------+  |
|  |       CLI Engine       |  |       Ratatui TUI       |  |  Axum Web / SSE / WS   |  |
|  |  (clap v4 / subcmds)   |  |  (Crossterm / widgets)  |  | (REST, WS, SSE, HTML)  |  |
|  +-----------+------------+  +------------+------------+  +-----------+------------+  |
+--------------|----------------------------|---------------------------|---------------+
               |                            |                           |
               +-------------------+        |        +------------------+
                                   v        v        v
+---------------------------------------------------------------------------------------+
|                              UNIFIED EXECUTION ENGINE                                 |
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  | CommandRegistry: Central registry of Builtin CLI Commands + Dynamic MCP Tools   |  |
|  +---------------------------------------------------------------------------------+  |
|  | TaskDispatcher: Asynchronous Worker Pool (Tokio multithreaded runtime)          |  |
|  +---------------------------------------------------------------------------------+  |
|  | EventBus: Multi-producer broadcast channel (tokio::sync::broadcast)             |  |
|  +---------------------------------------------------------------------------------+  |
+------------------------------------------+--------------------------------------------+
                                           |
                    +----------------------+----------------------+
                    v                                             v
+---------------------------------------+     +-----------------------------------------+
|     R2: MCP SUBSYSTEM (Client/Server) |     |   R3: RESOURCE & MODEL SELECTOR ENGINE  |
|  - JSON-RPC 2.0 Parser                |     |  - TelemetryEngine (sysinfo + NVML/DXGI)|
|  - Stdio & HTTP/SSE Transports        |     |  - Memory Sizing & KV Cache Calculator  |
|  - Tool/Prompt/Resource Registries    |     |  - Dynamic Model Selector & Router      |
+---------------------------------------+     +-----------------------------------------+
```

---

## 2. R3 Deep Dive: System Resource Telemetry Architecture

### 2.1 Telemetry Engine Requirements & Design Goals
The telemetry subsystem must provide real-time hardware visibility without imposing noticeable CPU or memory overhead on worker threads. Telemetry collection runs asynchronously on a dedicated background tick loop and publishes immutable snapshots to an atomic / watch channel.

Key Architectural Guarantees:
- **Zero-Block Read Access**: Readers obtain the latest `ResourceSnapshot` via `ArcSwap` or `tokio::sync::watch::Receiver` in $O(1)$ time with zero mutex lock contention.
- **Graceful Multi-Tier GPU Fallback**: If NVIDIA drivers or NVML DLLs are absent (common on non-NVIDIA or cloud VM setups), the system gracefully cascades to DirectX DXGI (Windows), Metal (macOS), Vulkan, or CPU-only modes without crashing or logging fatal errors.
- **Configurable Polling Intervals**: Default polling rate of $1000\text{ms}$ (1Hz) during normal execution, scaling to $250\text{ms}$ (4Hz) in active TUI/IDE modes.

### 2.2 Cross-Platform Hardware Detection Strategy & Fallback Chain

```
                   +-----------------------------+
                   | Initialize Telemetry Engine |
                   +--------------+--------------+
                                  |
                                  v
                      +-----------------------+
                      | Check NVIDIA NVML     |
                      | (libnvidia-ml / nvml) |
                      +-----------+-----------+
                                  |
                   +--------------+--------------+
           Success |                             | Failure / Not Found
                   v                             v
       +-----------------------+     +-----------------------+
       | Native NVIDIA VRAM &  |     | Check OS Platform     |
       | GPU Utilization Path  |     +-----------+-----------+
       +-----------------------+                 |
                               +-----------------+-----------------+
                               | Windows                           | Linux / macOS
                               v                                   v
                   +-----------------------+           +-----------------------+
                   | DirectX DXGI Adapter  |           | Apple Metal / Sysinfo |
                   | Query (VRAM / Shared) |           | Unified Memory Query  |
                   +-----------+-----------+           +-----------+-----------+
                               |                                   |
                               +-----------------+-----------------+
                                                 |
                                                 v
                                     +-----------------------+
                                     | Vulkan / wgpu Adapter |
                                     | Enumeration Fallback  |
                                     +-----------+-----------+
                                                 |
                                                 v
                                     +-----------------------+
                                     | Host System RAM Only  |
                                     | (sysinfo Base Profile)|
                                     +-----------------------+
```

#### Tier 1: NVIDIA Native NVML (`nvml-wrapper` / Dynamic Loading)
- Queries GPU device name, total VRAM, used VRAM, free VRAM, GPU core utilization percentage, memory controller utilization percentage, temperature, and power usage.
- Uses dynamic symbol loading (`libloading`) or safe wrappers around `nvmlInit_v2` / `nvmlDeviceGetMemoryInfo` so failure to find `nvml.dll` (Windows) or `libnvidia-ml.so` (Linux) results in a clean fallback rather than dynamic link failure at binary load time.

#### Tier 2: Windows DirectX DXGI
- On Windows systems where NVML is unavailable (e.g. AMD Radeon, Intel Arc, or virtualized Hyper-V/WSL instances), query `IDXGIFactory4::EnumAdapters1` / `DXGI_ADAPTER_DESC1`.
- Extracts `DedicatedVideoMemory` (VRAM), `DedicatedSystemMemory`, and `SharedSystemMemory`.

#### Tier 3: Apple Silicon Metal / Unified Memory
- On macOS Apple Silicon (M1/M2/M3/M4), CPU and GPU share unified system memory.
- Telemetry dynamically marks GPU VRAM as equal to available system RAM with unified memory architecture flags enabled.

#### Tier 4: Vulkan / wgpu Adapter Enumeration
- Queries `wgpu::Instance::enumerate_adapters` to identify adapter type (`DiscreteGpu`, `IntegratedGpu`, `Cpu`), backend (`Vulkan`, `Metal`, `Dx12`), and driver info.

#### Tier 5: Pure Host CPU & RAM (`sysinfo`)
- Universal fallback supported on all POSIX and Windows operating systems.
- Reads total RAM, available RAM, swap total, swap used, per-core CPU load, and CPU clock frequencies via `sysinfo::System`.

### 2.3 Rust Telemetry Data Structures & Type Definitions

```rust
use serde::{Deserialize, Serialize};
use std::time::SystemTime;

/// GPU Vendor Classification
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum GpuVendor {
    Nvidia,
    Amd,
    Intel,
    AppleSilicon,
    Unknown,
}

/// GPU Hardware Telemetry Snapshot
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GpuMetrics {
    pub device_id: u32,
    pub name: String,
    pub vendor: GpuVendor,
    pub total_vram_bytes: u64,
    pub used_vram_bytes: u64,
    pub free_vram_bytes: u64,
    pub gpu_utilization_pct: Option<f32>,
    pub memory_utilization_pct: Option<f32>,
    pub temperature_celsius: Option<f32>,
    pub power_watts: Option<f32>,
    pub is_unified_memory: bool,
    pub compute_capability: Option<(u32, u32)>, // e.g. (8, 9) for Ada Lovelace
}

/// Host CPU Telemetry Snapshot
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CpuMetrics {
    pub physical_core_count: usize,
    pub logical_core_count: usize,
    pub global_cpu_usage_pct: f32,
    pub per_core_usage_pct: Vec<f32>,
    pub cpu_brand: String,
    pub frequency_mhz: u64,
}

/// Host Memory & Swap Telemetry Snapshot
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryMetrics {
    pub total_ram_bytes: u64,
    pub used_ram_bytes: u64,
    pub available_ram_bytes: u64,
    pub free_ram_bytes: u64,
    pub total_swap_bytes: u64,
    pub used_swap_bytes: u64,
    pub memory_pressure_pct: f32, // (used_ram / total_ram) * 100.0
}

/// Comprehensive System Resource Snapshot
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceSnapshot {
    pub timestamp: SystemTime,
    pub cpu: CpuMetrics,
    pub memory: MemoryMetrics,
    pub gpus: Vec<GpuMetrics>,
    pub primary_gpu_index: Option<usize>,
}
```

### 2.4 Asynchronous Background Telemetry Engine Implementation Sketch

```rust
use std::sync::Arc;
use tokio::sync::watch;
use tokio::time::{interval, Duration};
use sysinfo::{CpuRefreshKind, MemoryRefreshKind, RefreshKind, System};

pub struct TelemetryEngine {
    snapshot_tx: watch::Sender<ResourceSnapshot>,
    snapshot_rx: watch::Receiver<ResourceSnapshot>,
}

impl TelemetryEngine {
    pub fn new(initial_interval: Duration) -> Self {
        let (initial_snapshot, mut sys, gpu_prober) = Self::init_probers();
        let (tx, rx) = watch::channel(initial_snapshot);

        tokio::spawn(async move {
            let mut ticker = interval(initial_interval);
            loop {
                ticker.tick().await;
                // Refresh sysinfo state incrementally (non-blocking)
                sys.refresh_specifics(
                    RefreshKind::new()
                        .with_cpu(CpuRefreshKind::everything())
                        .with_memory(MemoryRefreshKind::everything()),
                );

                let gpus = gpu_prober.probe();
                let snapshot = ResourceSnapshot {
                    timestamp: SystemTime::now(),
                    cpu: CpuMetrics {
                        physical_core_count: sys.physical_core_count().unwrap_or(1),
                        logical_core_count: sys.cpus().len(),
                        global_cpu_usage_pct: sys.global_cpu_usage(),
                        per_core_usage_pct: sys.cpus().iter().map(|c| c.cpu_usage()).collect(),
                        cpu_brand: sys.cpus().first().map(|c| c.brand().to_string()).unwrap_or_default(),
                        frequency_mhz: sys.cpus().first().map(|c| c.frequency()).unwrap_or(0),
                    },
                    memory: MemoryMetrics {
                        total_ram_bytes: sys.total_memory(),
                        used_ram_bytes: sys.used_memory(),
                        available_ram_bytes: sys.available_memory(),
                        free_ram_bytes: sys.free_memory(),
                        total_swap_bytes: sys.total_swap(),
                        used_swap_bytes: sys.used_swap(),
                        memory_pressure_pct: (sys.used_memory() as f32 / sys.total_memory() as f32) * 100.0,
                    },
                    primary_gpu_index: if gpus.is_empty() { None } else { Some(0) },
                    gpus,
                };

                let _ = tx.send(snapshot);
            }
        });

        Self {
            snapshot_tx: tx,
            snapshot_rx: rx,
        }
    }

    pub fn get_snapshot(&self) -> ResourceSnapshot {
        self.snapshot_rx.borrow().clone()
    }

    pub fn subscribe(&self) -> watch::Receiver<ResourceSnapshot> {
        self.snapshot_rx.clone()
    }
}
```

---

## 3. R3 Deep Dive: Dynamic Model Selector & Inference Router

### 3.1 Model Fit Classification Tiers

To balance inference speed, intelligence requirements, and hardware memory limits, models are categorized into five distinct tiers:

| Tier | Typical Parameter Range | Quantizations | Memory Footprint ($M_{\text{total}}$) | Typical Models | Hardware Target |
|---|---|---|---|---|---|
| **Micro / Nano** | 0.5B – 1.7B | Q4_K_M, Q8_0, FP16 | **0.8 GB – 2.2 GB** | Qwen 2.5 0.5B/1.5B, SmolLM 135M/1.7B | Low-end CPU (2-4 cores), 4GB RAM, Integrated GPU |
| **Small** | 3.0B – 7.0B | Q4_K_M, Q5_K_M, Q8_0 | **2.2 GB – 6.0 GB** | Llama 3.2 1B/3B, Phi-3.5 3.8B, Qwen 2.5 7B Q4 | Entry GPU (4-6GB VRAM, RTX 3050/2060) or 8GB CPU RAM |
| **Medium** | 8.0B – 14.0B | Q4_K_M, Q8_0 | **6.0 GB – 16.0 GB** | Llama 3.1 8B Q8, Qwen 2.5 14B Q4, Mistral 7B Q8 | Mid GPU (8-16GB VRAM, RTX 3060/4070) or 16-32GB CPU RAM |
| **Large** | 30.0B – 70.0B | Q4_K_M, Q5_K_M | **16.0 GB – 48.0+ GB** | Qwen 2.5 32B, Llama 3.3 70B Q4_K_M, Command-R+ | High-end GPU (24-48GB VRAM, RTX 3090/4090/A6000, Apple 64GB) |
| **Cloud Fallback** | Any / Ultra-scale | FP16 / Cloud API | **N/A (Remote)** | Claude 3.5 Sonnet, GPT-4o, DeepSeek V3/R1 | Cloud API (Low local RAM, thermal throttling, or ultra-reasoning) |

### 3.2 Mathematical Model Sizing & Memory Heuristic Formulation

The dynamic model selector calculates precise memory requirements before routing any model execution:

#### 1. Quantization Scaling Factor ($\beta_Q$)
The bytes-per-parameter factor $\beta_Q$ varies according to quantization scheme:
$$\beta_{\text{FP16}} = 2.000, \quad \beta_{\text{Q8\_0}} = 1.0625, \quad \beta_{\text{Q6\_K}} = 0.850, \quad \beta_{\text{Q5\_K\_M}} = 0.725, \quad \beta_{\text{Q4\_K\_M}} = 0.580, \quad \beta_{\text{Q3\_K\_M}} = 0.480, \quad \beta_{\text{Q2\_K}} = 0.380$$

#### 2. Model Weights Memory ($M_{\text{weights}}$)
$$M_{\text{weights}} = \left( P \times \beta_Q \times 1.05 \right) \text{ bytes}$$
*(Where $P$ is total parameter count, and $1.05$ represents tensor metadata, tensor alignment, and model header overhead).*

#### 3. KV Cache Memory ($M_{\text{kv}}$)
For Grouped-Query Attention (GQA) or Multi-Head Attention (MHA):
$$M_{\text{kv}} = 2 \times N_{\text{layers}} \times N_{\text{kv\_heads}} \times D_{\text{head}} \times C_{\text{context}} \times B_{\text{elem}} \times S_{\text{batch}}$$
- $N_{\text{layers}}$: Total transformer decoder layers (e.g. 32 for Llama 8B, 80 for Llama 70B).
- $N_{\text{kv\_heads}}$: Number of key-value heads (e.g. 8 for GQA in Llama 3.1 8B vs 32 query heads).
- $D_{\text{head}}$: Head dimension (typically $\text{HiddenDim} / N_{\text{heads}} = 128$).
- $C_{\text{context}}$: Target context length (e.g. 4096, 8192, 32768, 131072 tokens).
- $B_{\text{elem}}$: Bytes per KV element ($2.0$ for FP16, $1.0$ for FP8/Q8 KV cache).
- $S_{\text{batch}}$: Batch size (default $= 1$ for single-session developer IDE).

*Example Calculation*: For Llama 3.1 8B with $N_{\text{layers}}=32$, $N_{\text{kv\_heads}}=8$, $D_{\text{head}}=128$, $C=8192$, $B=2$, $S=1$:
$$M_{\text{kv}} = 2 \times 32 \times 8 \times 128 \times 8192 \times 2 \times 1 = 1,073,741,824\text{ bytes} = 1.00\text{ GB}$$

#### 4. Working / Activation Memory ($M_{\text{act}}$)
$$M_{\text{act}} = \max\left(256\text{ MB}, \left( \text{HiddenDim} \times C_{\text{context}} \times 4 \times B_{\text{elem}} \right)\right)$$
Typically between $256\text{ MB}$ and $1.5\text{ GB}$ for standard context lengths.

#### 5. Total Required Memory ($M_{\text{total}}$) & Headroom Margin ($\gamma$)
$$M_{\text{total}} = (M_{\text{weights}} + M_{\text{kv}} + M_{\text{act}}) \times (1 + \gamma)$$
Where $\gamma = 0.15$ (15% safety headroom margin) to guarantee zero Out-Of-Memory (OOM) crashes and avoid OS swap thrashing.

### 3.3 Layer Offload & Hybrid Execution Calculation
When available VRAM ($V_{\text{free}}$) is insufficient to fit the entire model but can fit a subset of layers:
$$N_{\text{gpu\_layers}} = \min\left(N_{\text{layers}}, \left\lfloor \frac{V_{\text{free}} \times (1 - \gamma) - M_{\text{kv\_gpu}} - M_{\text{act}}}{M_{\text{layer\_weight}}} \right\rfloor\right)$$
Where $M_{\text{layer\_weight}} = M_{\text{weights}} / N_{\text{layers}}$.

If $N_{\text{gpu\_layers}} \ge N_{\text{layers}}$, execution is **Full GPU**.  
If $0 < N_{\text{gpu\_layers}} < N_{\text{layers}}$, execution is **Hybrid GPU/CPU Offload**.  
If $N_{\text{gpu\_layers}} == 0$, execution is **Pure CPU** (provided $M_{\text{total}} \le \text{RAM}_{\text{avail}} \times (1 - \gamma)$).  
If $M_{\text{total}} > \text{RAM}_{\text{avail}} \times (1 - \gamma)$, execution triggers **Cloud Fallback**.

### 3.4 Dynamic Model Selector Implementation Design

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ExecutionTarget {
    GpuFull { device_id: u32, vram_allocated_bytes: u64 },
    Hybrid { device_id: u32, gpu_layers: usize, total_layers: usize, vram_bytes: u64, ram_bytes: u64 },
    CpuOnly { ram_allocated_bytes: u64, thread_count: usize },
    CloudFallback { reason: String, suggested_remote_model: String },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelRoutingDecision {
    pub model_id: String,
    pub tier: String,
    pub quantization: String,
    pub target: ExecutionTarget,
    pub estimated_memory_bytes: u64,
    pub safety_headroom_bytes: u64,
    pub confidence_score: f32, // 0.0 to 1.0
    pub diagnostics: Vec<String>,
}

pub struct ModelSelector;

impl ModelSelector {
    pub fn evaluate(
        manifest: &ModelManifest,
        target_context_tokens: usize,
        telemetry: &ResourceSnapshot,
    ) -> ModelRoutingDecision {
        let weights_bytes = manifest.calculate_weights_memory();
        let kv_bytes = manifest.calculate_kv_memory(target_context_tokens);
        let act_bytes = manifest.calculate_activation_memory(target_context_tokens);
        let total_required = ((weights_bytes + kv_bytes + act_bytes) as f64 * 1.15) as u64;

        // Check Primary GPU
        if let Some(gpu_idx) = telemetry.primary_gpu_index {
            let gpu = &telemetry.gpus[gpu_idx];
            if gpu.free_vram_bytes >= total_required {
                return ModelRoutingDecision {
                    model_id: manifest.id.clone(),
                    tier: manifest.tier.clone(),
                    quantization: manifest.quantization.clone(),
                    target: ExecutionTarget::GpuFull {
                        device_id: gpu.device_id,
                        vram_allocated_bytes: total_required,
                    },
                    estimated_memory_bytes: total_required,
                    safety_headroom_bytes: (total_required as f64 * 0.15) as u64,
                    confidence_score: 0.98,
                    diagnostics: vec![format!("Full GPU fit on {} (Free VRAM: {} MB, Req: {} MB)",
                        gpu.name, gpu.free_vram_bytes / (1024 * 1024), total_required / (1024 * 1024))],
                };
            }

            // Check Hybrid Offload
            if gpu.free_vram_bytes > (kv_bytes + act_bytes + (weights_bytes / manifest.total_layers as u64 * 4)) {
                let layer_weight = weights_bytes / manifest.total_layers as u64;
                let available_for_layers = gpu.free_vram_bytes.saturating_sub(kv_bytes + act_bytes);
                let offloadable_layers = ((available_for_layers as f64 * 0.85) / layer_weight as f64) as usize;
                let offloadable_layers = offloadable_layers.min(manifest.total_layers);

                let remaining_layers = manifest.total_layers - offloadable_layers;
                let remaining_ram_req = remaining_layers as u64 * layer_weight;

                if telemetry.memory.available_ram_bytes > (remaining_ram_req as f64 * 1.2) as u64 {
                    return ModelRoutingDecision {
                        model_id: manifest.id.clone(),
                        tier: manifest.tier.clone(),
                        quantization: manifest.quantization.clone(),
                        target: ExecutionTarget::Hybrid {
                            device_id: gpu.device_id,
                            gpu_layers: offloadable_layers,
                            total_layers: manifest.total_layers,
                            vram_bytes: available_for_layers,
                            ram_bytes: remaining_ram_req,
                        },
                        estimated_memory_bytes: total_required,
                        safety_headroom_bytes: (total_required as f64 * 0.15) as u64,
                        confidence_score: 0.85,
                        diagnostics: vec![format!("Hybrid offload: {}/{} layers on GPU", offloadable_layers, manifest.total_layers)],
                    };
                }
            }
        }

        // Check Pure CPU RAM
        if telemetry.memory.available_ram_bytes >= total_required {
            return ModelRoutingDecision {
                model_id: manifest.id.clone(),
                tier: manifest.tier.clone(),
                quantization: manifest.quantization.clone(),
                target: ExecutionTarget::CpuOnly {
                    ram_allocated_bytes: total_required,
                    thread_count: telemetry.cpu.physical_core_count.max(1),
                },
                estimated_memory_bytes: total_required,
                safety_headroom_bytes: (total_required as f64 * 0.15) as u64,
                confidence_score: 0.70,
                diagnostics: vec![format!("CPU execution on {} cores (Available RAM: {} MB)",
                    telemetry.cpu.physical_core_count, telemetry.memory.available_ram_bytes / (1024 * 1024))],
            };
        }

        // Fallback to Cloud
        ModelRoutingDecision {
            model_id: manifest.id.clone(),
            tier: manifest.tier.clone(),
            quantization: "cloud-api".to_string(),
            target: ExecutionTarget::CloudFallback {
                reason: format!("Insufficient local memory. Required: {} MB, Avail RAM: {} MB, Free VRAM: {} MB",
                    total_required / (1024 * 1024),
                    telemetry.memory.available_ram_bytes / (1024 * 1024),
                    telemetry.gpus.first().map(|g| g.free_vram_bytes / (1024 * 1024)).unwrap_or(0)),
                suggested_remote_model: "claude-3-5-sonnet-20241022".to_string(),
            },
            estimated_memory_bytes: 0,
            safety_headroom_bytes: 0,
            confidence_score: 0.95,
            diagnostics: vec!["Triggered automatic cloud routing fallback".to_string()],
        }
    }
}
```

---

## 4. R4 Deep Dive: Unified IDE Architecture & Tool Parity

### 4.1 100% Tool Parity Principle
A foundational requirement of `mcp_ide_engine` is that **any tool or command available in the CLI is identically executable via the TUI and Web interfaces**. This is achieved through the **Unified Command Bus Architecture**:

```
                              +-------------------------+
                              |   Unified Command Bus   |
                              +------------+------------+
                                           |
                +--------------------------+--------------------------+
                |                          |                          |
                v                          v                          v
     +--------------------+      +--------------------+      +--------------------+
     |    CLI Pipeline    |      |    Ratatui TUI     |      |  Axum Web / API    |
     |  (Args & Flags)    |      | (Keybinds / Forms) |      | (REST / WebSocket) |
     +----------+---------+      +----------+---------+      +----------+---------+
                |                           |                           |
                +-------------------+       |       +-------------------+
                                    |       |       |
                                    v       v       v
                            +-------------------------------+
                            |        CommandRegistry        |
                            |  (Builtins + MCP Tool Catalog)|
                            +---------------+---------------+
                                            |
                                            v
                            +-------------------------------+
                            |   TaskDispatcher (Async)      |
                            |   - Worker Thread Pool        |
                            |   - CancellationTokens        |
                            |   - TaskHandle Tracking       |
                            +---------------+---------------+
                                            |
                                            v
                            +-------------------------------+
                            |      EventBus Broadcast       |
                            |  (Logs, Status, Telemetry)    |
                            +-------------------------------+
```

### 4.2 Universal Command Registry & Execution Trait

```rust
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::sync::Arc;
use tokio_util::sync::CancellationToken;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommandDescriptor {
    pub id: String,
    pub name: String,
    pub description: String,
    pub category: CommandCategory,
    pub parameter_schema: Value, // JSON Schema for input validation
    pub is_mcp_tool: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CommandCategory {
    System,
    Resource,
    McpManagement,
    DeveloperTask,
    CodeAnalysis,
    Custom,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskExecutionEvent {
    pub task_id: String,
    pub command_id: String,
    pub timestamp: std::time::SystemTime,
    pub payload: TaskEventPayload,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TaskEventPayload {
    Started { parameters: Value },
    Progress { progress: f32, message: String },
    StdoutChunk(String),
    StderrChunk(String),
    Completed { result: Value, duration_ms: u64 },
    Failed { error_code: i32, error_message: String },
    Cancelled,
}

#[async_trait]
pub trait ExecutableCommand: Send + Sync {
    fn descriptor(&self) -> CommandDescriptor;
    async fn execute(
        &self,
        params: Value,
        cancel_token: CancellationToken,
        event_tx: tokio::sync::mpsc::UnboundedSender<TaskExecutionEvent>,
    ) -> Result<Value, CommandError>;
}
```

---

### 4.3 Ratatui TUI Interface Architecture

#### Layout & Pane Composition
The TUI is designed using `ratatui` (v0.28+) and `crossterm` (v0.28+) with an ergonomic, responsive multi-view tabbed layout:

```
+----------------------------------------------------------------------------------------------------+
| MCP IDE Engine v1.0.0 | Runtime: ACTIVE | Workers: 16 | MCP Servers: 3 | 2026-09-02 16:14:00 UTC   |
+----------------------------------------------------------------------------------------------------+
| [1] Dashboard  | [2] Command Runner  | [3] MCP Inspector  | [4] Task Monitor  | [5] Model Selector |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  +--------------------------------------------+  +----------------------------------------------+  |
|  | CPU Telemetry (16 Cores)                   |  | Memory & VRAM Telemetry                      |  |
|  | Load: 24.5%  [||||||||........] 3.8 GHz    |  | RAM: 14.2/32.0 GB [|||||||||||..........]    |  |
|  | Sparkline: _.-~-._.-~-._.-~-._.-~-._.-~-._  |  | VRAM: 6.1/16.0 GB [|||||||||.............]   |  |
|  +--------------------------------------------+  +----------------------------------------------+  |
|                                                                                                    |
|  +----------------------------------------------------------------------------------------------+  |
|  | Active Tasks & Worker Thread Pool                                                            |  |
|  | ID      Command             Worker  Duration  Status      Progress                           |  |
|  | #1042   mcp/analyze_ast     #3      142ms     RUNNING     [================>....] 75%        |  |
|  | #1043   resource/model_fit  #7      12ms      SUCCESS     [=====================] 100%       |  |
|  | #1044   mcp/fetch_resource  #1      89ms      RUNNING     [==========>..........] 50%        |  |
|  +----------------------------------------------------------------------------------------------+  |
|                                                                                                    |
|  +----------------------------------------------------------------------------------------------+  |
|  | Live Streaming Output & JSON-RPC Traffic Log                                                 |  |
|  | [16:14:00.102] [TASK #1042] Parsed 42 AST nodes from src/core/engine.rs                       |  |
|  | [16:14:00.115] [MCP] <-- jsonrpc: "2.0", method: "tools/call", id: 89, params: {...}        |  |
|  | [16:14:00.120] [MCP] --> jsonrpc: "2.0", result: { content: [...] }, id: 89                  |  |
|  +----------------------------------------------------------------------------------------------+  |
+----------------------------------------------------------------------------------------------------+
| <Tab> Switch View | <Ctrl+P> Command Palette | <Enter> Execute | <Esc> Cancel | <q> Quit Engine    |
+----------------------------------------------------------------------------------------------------+
```

#### TUI Multi-Pane Widget Roster
1. **Header Widget**: Displays engine operational state, worker pool utilization, active MCP server connections, uptime, and system clock.
2. **Dashboard Tab (`DashboardWidget`)**:
   - `Sparkline` widgets rendering 60-second rolling CPU and memory load histories.
   - `Gauge` widgets rendering System RAM, Swap Pressure, and GPU VRAM allocations.
   - Summary count cards for completed/active/failed tasks.
3. **Command & Tool Runner Tab (`RunnerWidget`)**:
   - Left Pane: Filterable list of all registered CLI builtins and dynamic MCP tools.
   - Right-Top Pane: JSON parameter form editor with syntax validation against `parameter_schema`.
   - Right-Bottom Pane: Real-time ANSI colored streaming log viewer (`Paragraph` widget with auto-scroll).
4. **MCP Inspector Tab (`McpInspectorWidget`)**:
   - Connected MCP server list (stdio child process PIDs, SSE remote endpoints).
   - Tool schema tree explorer with input/output type annotations.
   - Live JSON-RPC traffic monitor showing raw message frames with millisecond timestamps.
5. **Task & Worker Monitor Tab (`TaskMonitorWidget`)**:
   - `Table` widget listing all worker threads, current assignment, task execution time, CPU time, and state (`Queued`, `Running`, `Completed`, `Failed`, `Cancelled`).
   - Interactive keybindings to inspect task stack traces or issue graceful cancellation tokens (`<c>` to cancel selected task).
6. **Resource & Model Matrix Tab (`ModelMatrixWidget`)**:
   - Full hardware inventory table (CPU cores, cache levels, RAM banks, GPU CUDA/Vulkan descriptors).
   - Interactive Model Selector Simulator: Adjust sliders for context window length (1k to 128k), parameter size (1B to 70B), and quantization (Q4 to FP16) to see real-time calculation of $M_{\text{weights}}$, $M_{\text{kv}}$, $M_{\text{act}}$, estimated token latency, and routing verdict.

#### Non-Blocking TUI Event Loop Design
```rust
pub async fn run_tui(
    mut terminal: ratatui::Terminal<ratatui::backend::CrosstermBackend<std::io::Stdout>>,
    mut app: TuiApp,
    event_bus: tokio::sync::broadcast::Receiver<EngineEvent>,
) -> Result<(), Box<dyn std::error::Error>> {
    use crossterm::event::{EventStream, Event, KeyCode, KeyModifiers};
    use futures::StreamExt;

    let mut event_stream = EventStream::new();
    let mut render_interval = tokio::time::interval(Duration::from_millis(33)); // 30 FPS cap

    loop {
        tokio::select! {
            _ = render_interval.tick() => {
                terminal.draw(|f| app.render(f))?;
            }
            maybe_event = event_stream.next() => {
                if let Some(Ok(event)) = maybe_event {
                    match event {
                        Event::Key(key) => {
                            if key.code == KeyCode::Char('q') && key.modifiers.contains(KeyModifiers::CONTROL) {
                                break;
                            }
                            app.handle_key_event(key).await;
                        }
                        Event::Resize(w, h) => {
                            app.handle_resize(w, h);
                        }
                        _ => {}
                    }
                }
            }
            Ok(engine_event) = event_bus.recv() => {
                app.handle_engine_event(engine_event);
            }
        }
    }
    Ok(())
}
```

---

### 4.4 Axum Embedded Web & API Interface

#### Embedded Architecture
The web interface is served directly from the compiled binary with zero external runtime dependencies. Frontend single-page application assets (HTML/CSS/JS) are embedded at compile time using `rust-embed` or raw string constants.

#### REST & Streaming API Endpoints

| Method | Endpoint | Description | Streaming / Payload |
|---|---|---|---|
| `GET` | `/api/v1/health` | Engine health, uptime, worker pool status | JSON (`HealthResponse`) |
| `GET` | `/api/v1/resources/snapshot` | Instantaneous CPU/RAM/GPU telemetry | JSON (`ResourceSnapshot`) |
| `POST` | `/api/v1/resources/models/evaluate`| Query model selector routing heuristic | Input: `ModelQuery`, Output: `ModelRoutingDecision` |
| `GET` | `/api/v1/tools` | Enumerate all CLI builtins & MCP tools | JSON (`Vec<CommandDescriptor>`) |
| `POST` | `/api/v1/tools/execute` | Dispatch command asynchronously | Input: `ExecuteRequest`, Output: `{ task_id }` |
| `GET` | `/api/v1/tasks` | List active, queued, and historical tasks | JSON (`Vec<TaskSummary>`) |
| `GET` | `/api/v1/tasks/:id` | Detailed task status & buffered logs | JSON (`TaskDetail`) |
| `POST` | `/api/v1/tasks/:id/cancel`| Gracefully cancel active task | JSON (`{ success: bool }`) |
| `GET` | `/api/v1/events/sse` | **Server-Sent Events** streaming telemetry & logs | `text/event-stream` (`TaskExecutionEvent`) |
| `GET` | `/api/v1/ws` | **Full-Duplex WebSocket** session | Bidirectional JSON frames & streaming I/O |

#### Axum Route Setup & WebSocket Streaming Handler

```rust
use axum::{
    extract::{ws::{Message, WebSocket, WebSocketUpgrade}, Path, State},
    response::{sse::{Event, KeepAlive, Sse}, IntoResponse, Json},
    routing::{get, post},
    Router,
};
use futures::{sink::SinkExt, stream::StreamExt};
use std::sync::Arc;

pub fn create_router(engine: Arc<EngineRuntime>) -> Router {
    Router::new()
        .route("/api/v1/health", get(health_handler))
        .route("/api/v1/resources/snapshot", get(get_resources_handler))
        .route("/api/v1/resources/models/evaluate", post(evaluate_model_handler))
        .route("/api/v1/tools", get(list_tools_handler))
        .route("/api/v1/tools/execute", post(execute_tool_handler))
        .route("/api/v1/tasks", get(list_tasks_handler))
        .route("/api/v1/tasks/:id", get(get_task_handler))
        .route("/api/v1/tasks/:id/cancel", post(cancel_task_handler))
        .route("/api/v1/events/sse", get(sse_handler))
        .route("/api/v1/ws", get(ws_handler))
        .with_state(engine)
}

async fn ws_handler(
    ws: WebSocketUpgrade,
    State(engine): State<Arc<EngineRuntime>>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_socket(socket, engine))
}

async fn handle_socket(socket: WebSocket, engine: Arc<EngineRuntime>) {
    let (mut sender, mut receiver) = socket.split();
    let mut broadcast_rx = engine.event_bus.subscribe();

    let mut send_task = tokio::spawn(async move {
        while let Ok(event) = broadcast_rx.recv().await {
            if let Ok(json) = serde_json::to_string(&event) {
                if sender.send(Message::Text(json)).await.is_err() {
                    break; // Client disconnected
                }
            }
        }
    });

    let mut recv_task = tokio::spawn(async move {
        while let Some(Ok(msg)) = receiver.next().await {
            if let Message::Text(text) = msg {
                // Parse client command and dispatch to EngineRuntime
                let _ = engine.handle_client_ws_message(&text).await;
            }
        }
    });

    tokio::select! {
        _ = (&mut send_task) => recv_task.abort(),
        _ = (&mut recv_task) => send_task.abort(),
    };
}
```

---

## 5. R5 Deep Dive: Benchmark & Verification Harness Design

### 5.1 Verification Objectives & Acceptance Thresholds
Requirement R5 mandates a rigorous benchmark and test harness validating performance, correctness, and stability under load:
1. **Dispatch Overhead Benchmark**: Task dispatch latency must be verified at **$< 5\text{ms}$** (target: $< 50\mu\text{s}$ internal async queue overhead).
2. **High-Concurrency Stress Test**: Simultaneous execution of **50+ concurrent tasks** with zero deadlocks, race conditions, or dropped events.
3. **MCP Throughput**: High-frequency JSON-RPC 2.0 serialization/deserialization capable of handling $> 100,000\text{ msg/sec}$.
4. **Non-Blocking Telemetry Overhead**: Telemetry sampling cycle amortized overhead $< 1\text{ms}$ per tick.

---

### 5.2 Criterion Microbenchmark Suite (`benches/`)

```rust
use criterion::{black_box, criterion_group, criterion_main, Criterion, Throughput};
use mcp_core::dispatcher::TaskDispatcher;
use mcp_protocol::jsonrpc::{JsonRpcRequest, JsonRpcResponse};
use serde_json::json;

fn bench_task_dispatch_latency(c: &mut Criterion) {
    let runtime = tokio::runtime::Builder::new_multi_thread()
        .worker_threads(4)
        .enable_all()
        .build()
        .unwrap();

    let dispatcher = TaskDispatcher::new(16);

    let mut group = c.benchmark_group("Dispatcher Latency");
    group.throughput(Throughput::Elements(1));

    group.bench_function("dispatch_null_task", |b| {
        b.iter(|| {
            runtime.block_on(async {
                let task_id = dispatcher.dispatch("system/noop", json!({})).await.unwrap();
                black_box(task_id);
            });
        });
    });

    group.finish();
}

fn bench_jsonrpc_serialization(c: &mut Criterion) {
    let sample_request = JsonRpcRequest {
        jsonrpc: "2.0".to_string(),
        id: json!(42),
        method: "tools/call".to_string(),
        params: Some(json!({
            "name": "analyze_ast",
            "arguments": {
                "file_path": "src/core/runtime.rs",
                "depth": 3,
                "include_docs": true
            }
        })),
    };

    let serialized = serde_json::to_string(&sample_request).unwrap();

    let mut group = c.benchmark_group("MCP JSON-RPC 2.0");
    group.throughput(Throughput::Bytes(serialized.len() as u64));

    group.bench_function("serialize_tool_call_request", |b| {
        b.iter(|| {
            let s = serde_json::to_string(black_box(&sample_request)).unwrap();
            black_box(s);
        });
    });

    group.bench_function("deserialize_tool_call_request", |b| {
        b.iter(|| {
            let req: JsonRpcRequest = serde_json::from_str(black_box(&serialized)).unwrap();
            black_box(req);
        });
    });

    group.finish();
}

criterion_group!(benches, bench_task_dispatch_latency, bench_jsonrpc_serialization);
criterion_main!(benches);
```

---

### 5.3 Concurrency Stress Test Suite (50+ Simultaneous Tasks)

```rust
#[cfg(test)]
mod concurrency_tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::Arc;
    use tokio::sync::Barrier;
    use tokio::time::{timeout, Duration};

    #[tokio::test(flavor = "multi_thread", worker_threads = 8)]
    async fn test_50_plus_concurrent_tasks_no_deadlock() {
        const CONCURRENT_TASKS: usize = 64; // Exceeds 50 requirement
        let dispatcher = Arc::new(TaskDispatcher::new(16));
        let barrier = Arc::new(Barrier::new(CONCURRENT_TASKS));
        let completed_count = Arc::new(AtomicUsize::new(0));

        let mut handles = Vec::with_capacity(CONCURRENT_TASKS);

        for task_idx in 0..CONCURRENT_TASKS {
            let d = dispatcher.clone();
            let b = barrier.clone();
            let c = completed_count.clone();

            handles.push(tokio::spawn(async move {
                // Wait until all 64 tasks are spawned before firing simultaneously
                b.wait().await;

                // Dispatch task into engine
                let task_id = d.dispatch("stress/compute_hash", serde_json::json!({
                    "iteration": task_idx,
                    "payload": "concurrency_stress_verification_vector"
                })).await.expect("Task dispatch failed");

                // Await completion with strict timeout guarantee
                let result = timeout(Duration::from_millis(5000), d.wait_for_task(&task_id))
                    .await
                    .expect("Task execution timed out (potential deadlock!)")
                    .expect("Task internal error");

                assert!(result.is_success());
                c.fetch_add(1, Ordering::SeqCst);
            }));
        }

        // Await all spawned test runners
        for handle in handles {
            handle.await.expect("Tokio task join failed");
        }

        // Verify exact completion count
        assert_eq!(
            completed_count.load(Ordering::SeqCst),
            CONCURRENT_TASKS,
            "Not all concurrent tasks completed successfully!"
        );
    }

    #[tokio::test(flavor = "multi_thread", worker_threads = 4)]
    async fn test_rapid_concurrent_task_cancellation() {
        const CANCEL_TASKS: usize = 50;
        let dispatcher = Arc::new(TaskDispatcher::new(8));
        let mut cancel_handles = Vec::with_capacity(CANCEL_TASKS);

        for i in 0..CANCEL_TASKS {
            let d = dispatcher.clone();
            let task_id = d.dispatch("stress/long_sleep", serde_json::json!({ "duration_secs": 60 }))
                .await
                .unwrap();

            cancel_handles.push((task_id, d));
        }

        // Cancel all 50 tasks simultaneously
        for (task_id, d) in cancel_handles {
            let cancelled = d.cancel_task(&task_id).await;
            assert!(cancelled, "Task cancellation failed for {}", task_id);
        }

        // Assert all tasks transitions to Cancelled state within 100ms
        tokio::time::sleep(Duration::from_millis(100)).await;
        let active_tasks = dispatcher.list_active_tasks().await;
        assert_eq!(active_tasks.len(), 0, "Zombie tasks remained in active queue after cancellation!");
    }
}
```

---

### 5.4 4-Tier Automated Test Framework

```
+---------------------------------------------------------------------------------------+
|                                4-TIER TEST FRAMEWORK                                  |
+---------------------------------------------------------------------------------------+
| Tier 1: Unit & Algorithm Tests                                                        |
| - Model sizing formulas (weights, KV cache, activation memory scaling)                |
| - GPU detection fallback cascade logic & mock vendor probes                           |
| - Command parser & JSON-RPC schema validator                                          |
+---------------------------------------------------------------------------------------+
| Tier 2: Subsystem Integration Tests                                                   |
| - MCP Client/Server Stdio & SSE roundtrip communication                               |
| - Axum REST, SSE, and WebSocket endpoint contract testing                             |
| - Telemetry snapshot broadcast & watch channel subscriber test                        |
+---------------------------------------------------------------------------------------+
| Tier 3: Concurrency & Stress Tests                                                    |
| - 50+ to 200 simultaneous task storm under barrier synchronization                     |
| - Rapid concurrent cancellation & teardown validation                                 |
| - High-throughput EventBus broadcast load test (10k msgs/sec fan-out)                  |
+---------------------------------------------------------------------------------------+
| Tier 4: End-to-End Opaque-Box Acceptance Tests                                        |
| - CLI binary invocation with real parameter passing                                   |
| - Headless TUI event injection & terminal frame verification                          |
| - Complete CLI/TUI/Web tool parity verification across all registered commands        |
+---------------------------------------------------------------------------------------+
```

---

## 6. Rust Workspace & Crate Architecture

To enforce clean separation of concerns, rapid incremental compilation, and modular maintainability, the following workspace structure is specified:

```
mcp_ide_engine/
├── Cargo.toml                    # Workspace definition & shared dependency versions
├── crates/
│   ├── mcp-core/                 # Core engine runtime, dispatcher, worker pool, event bus
│   ├── mcp-protocol/             # JSON-RPC 2.0 schemas, MCP 2024-11-05 spec primitives
│   ├── mcp-resource/             # Sysinfo, NVML/DXGI fallback, telemetry, model selector
│   ├── mcp-tui/                  # Ratatui + Crossterm interactive terminal UI
│   ├── mcp-web/                  # Axum REST, SSE, WebSocket server, embedded dashboard
│   ├── mcp-cli/                  # Clap v4 CLI entrypoint and command runner
│   ├── mcp-bench/                # Criterion benchmark suites (<5ms latency validation)
│   └── mcp-tests/                # 4-tier integration & stress test suites
```

### 6.1 Recommended Crate Dependency Matrix

| Crate | Core Dependencies & Versions | Rationale & Responsibility |
|---|---|---|
| `mcp-core` | `tokio` (v1.40+, features: `full`), `tokio-util`, `async-trait`, `parking_lot`, `dashmap`, `tracing` | High-throughput asynchronous runtime, thread pool, event bus, lock-free routing |
| `mcp-protocol` | `serde`, `serde_json`, `jsonschema`, `thiserror` | MCP specification conformance, JSON-RPC 2.0 schemas, zero-allocation parsing |
| `mcp-resource` | `sysinfo` (v0.31+), `nvml-wrapper` (v0.10+), `windows` (features: `Win32_Graphics_Dxgi`), `wgpu` | Cross-platform hardware telemetry, GPU detection fallback chain, model sizing algorithms |
| `mcp-tui` | `ratatui` (v0.28+), `crossterm` (v0.28+), `unicode-width` | Interactive fullscreen TUI, sparklines, gauges, ANSI log streaming, keybinding engine |
| `mcp-web` | `axum` (v0.7+), `tower`, `tower-http` (cors, trace), `tokio-tungstenite`, `rust-embed` | Embedded REST API, SSE streaming, full-duplex WebSockets, bundled UI dashboard |
| `mcp-cli` | `clap` (v4.5+, features: `derive`), `colored`, `indicatif` | Developer CLI parser, subcommands, interactive prompts |
| `mcp-bench` | `criterion` (v0.5+, features: `async_tokio`) | Microbenchmarking dispatch latency, serialization speed, telemetry overhead |

---

## 7. Implementation Milestones & Risk Mitigation

| Risk / Challenge | Probability | Impact | Architectural Mitigation Strategy |
|---|---|---|---|
| **GPU Telemetry Panic on Non-NVIDIA Systems** | High | Critical | Implement dynamic symbol loading / safe wrapper for NVML. If NVML fails to initialize, log a trace warning and immediately cascade to DXGI / Metal / sysinfo fallback. Never panic. |
| **TUI Terminal Corruption on Panic** | Medium | Medium | Install custom `std::panic::set_hook` that restores terminal alternate screen, disables raw mode, and unhides cursor before printing panic trace. |
| **WebSocket Backpressure & Buffer Bloat** | Medium | High | Use bounded broadcast channels (`tokio::sync::broadcast`) with lag detection. If a slow web client falls behind, drop stale telemetry ticks rather than blocking worker threads. |
| **Concurrency Deadlock under Heavy Load** | Low | High | Enforce strict lock hierarchy (never hold locks across `.await` points), use lock-free data structures (`DashMap`, `ArcSwap`), and wrap all task joins with explicit timeouts. |
| **Memory KV Cache Overflow with Large Context** | Medium | High | Model selector dynamically calculates exact $M_{\text{kv}}$ based on requested context tokens ($C_{\text{context}}$) and enforces a 15% safety headroom margin before approving local GPU execution. |

---

## 8. Summary of Findings & Next Steps

1. **R3 (Resource Allocation & Model Selector)** is fully specified with exact formulas for model weights, KV cache, and activation memory, along with a 5-tier cross-platform GPU fallback chain.
2. **R4 (Unified IDE & Parity)** achieves 100% tool parity through a central `CommandRegistry` and `EventBus` shared by the CLI, Ratatui TUI, and Axum Web/WebSocket servers.
3. **R5 (Verification & Benchmarks)** provides Criterion benchmarks validating $< 5\text{ms}$ dispatch latency and automated stress tests validating 50+ concurrent tasks with zero deadlocks.

This concludes the architectural investigation for R3, R4, and R5. The blueprint is ready for synthesis and implementation.
