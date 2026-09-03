//! # MCP Resource Telemetry & Dynamic Model Selector
//!
//! Real-time hardware telemetry and local resource-aware model allocation for the MCP IDE Engine.
//!
//! Features:
//! - **Real-Time Hardware Telemetry**: Non-blocking background sampling of CPU core usage, system RAM, swap pressure, and process metrics via `sysinfo`.
//! - **Cross-Platform GPU Detection**: Multi-tier fallback cascade (NVIDIA NVML dynamic loading $\rightarrow$ Windows DXGI $\rightarrow$ Apple Metal $\rightarrow$ sysinfo fallback) returning GPU name, driver version, VRAM total, used, free, and compute features.
//! - **Mathematical Model Sizing**: Exact formulas for model weights ($M_{\text{weights}}$), KV Cache ($M_{\text{kv}}$), activation buffers ($M_{\text{act}}$), and configurable 15% safety headroom margin ($\gamma = 0.15$).
//! - **Dynamic Model Selector & Router**: Classifies model fit across 5 tiers (*Micro/Nano*, *Small*, *Medium*, *Large*, and *Cloud Fallback*) and computes optimal GPU layer offloading.

pub mod gpu;
pub mod selector;
pub mod sizing;
pub mod telemetry;

pub use gpu::{
    AppleMetalProber, DxgiProber, DynamicNvmlProber, GpuBackend, GpuDetector, GpuDetectorTrait,
    GpuInfo, GpuVendor, MockGpuProber, SysinfoFallbackProber,
};
pub use selector::{
    calculate_layer_offload, AllocationDecision, ExecutionTarget, LayerOffloadPlan, ModelSelector,
    ModelSpec, ModelTier,
};
pub use sizing::{
    calculate_activation_memory, calculate_kv_cache_memory, calculate_model_weights_memory,
    calculate_total_required_memory, KvCachePrecision, MemoryBreakdown, QuantizationType,
    DEFAULT_SAFETY_HEADROOM_MARGIN, DEFAULT_TENSOR_OVERHEAD,
};
pub use telemetry::{
    CpuMetrics, MemoryMetrics, ProcessMetrics, ResourceMonitor, SystemSnapshot,
};

use thiserror::Error;

/// Unified top-level error type for `mcp-resource`.
#[derive(Debug, Error)]
pub enum ResourceError {
    #[error("GPU detection error: {0}")]
    GpuDetection(String),

    #[error("Telemetry error: {0}")]
    Telemetry(String),

    #[error("Sizing calculation error: {0}")]
    Sizing(String),

    #[error("Model selection error: {0}")]
    Selector(String),

    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Insufficient memory for model {model_id}: required {required_bytes} bytes, available {available_bytes} bytes")]
    InsufficientMemory {
        model_id: String,
        required_bytes: u64,
        available_bytes: u64,
    },
}

/// Convenience Result type for MCP resource operations.
pub type Result<T> = std::result::Result<T, ResourceError>;

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    #[tokio::test]
    async fn test_end_to_end_resource_and_selector_pipeline() {
        // 1. Initialize live resource monitor
        let monitor = ResourceMonitor::new(Duration::from_millis(50));
        let snapshot = monitor.snapshot();

        assert!(snapshot.cpu.logical_core_count > 0);
        assert!(snapshot.memory.total_ram_bytes > 0);

        // 2. Query model catalog and select best model for current hardware
        let catalog = ModelSelector::default_catalog();
        let best_model = ModelSelector::select_best_model(&catalog, 4096, &snapshot);

        assert!(best_model.is_some());
        let decision = best_model.unwrap();
        assert!(!decision.model_id.is_empty());
        assert!(decision.memory_breakdown.total_required_bytes > 0);

        // 3. Clean shutdown
        monitor.shutdown();
    }
}
