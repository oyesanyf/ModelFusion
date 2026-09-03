//! Dynamic model tier classifier, inference router, and GPU layer offloader.
//!
//! Categorizes models into 5 fit tiers:
//! - **Micro / Nano**: 0.5B – 1.7B (~0.8 – 2.5 GB RAM)
//! - **Small**: 1.0B – 3.8B (~2.0 – 4.5 GB RAM / VRAM)
//! - **Medium**: 7.0B – 14.0B (~6.0 – 14.0 GB RAM / VRAM)
//! - **Large**: 30.0B – 70.0B (~16.0 – 48.0+ GB RAM / VRAM)
//! - **Cloud Fallback**: When local resources are insufficient or under memory pressure.
//!
//! Computes exact GPU layer offloading and recommends optimal execution targets.

use crate::gpu::GpuInfo;
use crate::sizing::{
    calculate_model_weights_memory, calculate_total_required_memory, KvCachePrecision,
    MemoryBreakdown, QuantizationType, DEFAULT_SAFETY_HEADROOM_MARGIN, DEFAULT_TENSOR_OVERHEAD,
};
use crate::telemetry::SystemSnapshot;
use serde::{Deserialize, Serialize};
use std::fmt;

/// Model scale and hardware fit tier.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum ModelTier {
    /// 0.5B – 1.7B (Ultra-lightweight / low-end CPU & integrated GPU)
    MicroNano,
    /// 1.0B – 3.8B (Entry GPU 4GB VRAM or 8GB CPU RAM)
    Small,
    /// 7.0B – 14.0B (Mid GPU 8-16GB VRAM or 16-32GB CPU RAM)
    Medium,
    /// 30.0B – 70.0B (High-end GPU 24-48GB VRAM or 64GB+ unified RAM)
    Large,
    /// Remote API fallback (Cloud endpoints like Claude / GPT-4o / DeepSeek)
    Cloud,
}

impl fmt::Display for ModelTier {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MicroNano => write!(f, "Micro/Nano (0.5B-1.7B)"),
            Self::Small => write!(f, "Small (1B-3B)"),
            Self::Medium => write!(f, "Medium (7B-8B)"),
            Self::Large => write!(f, "Large (14B-70B)"),
            Self::Cloud => write!(f, "Cloud Fallback"),
        }
    }
}

/// Architectural specification of an LLM for memory sizing and routing.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ModelSpec {
    /// Unique model identifier (e.g. "llama-3.1-8b-instruct-q4_k_m")
    pub id: String,
    /// Display name (e.g. "Llama 3.1 8B Instruct")
    pub name: String,
    /// Total parameter count
    pub parameters: u64,
    /// Quantization format
    pub quantization: QuantizationType,
    /// Total transformer decoder layers ($N_{\text{layers}}$)
    pub total_layers: usize,
    /// Number of Key-Value attention heads ($N_{\text{kv\_heads}}$)
    pub kv_heads: usize,
    /// Dimension per attention head ($D_{\text{head}}$)
    pub head_dim: usize,
    /// Hidden dimension ($D_{\text{model}}$)
    pub hidden_dim: usize,
    /// Default context length in tokens ($C_{\text{context}}$)
    pub default_context_length: usize,
    /// Fit tier classification
    pub tier: ModelTier,
}

impl ModelSpec {
    /// Creates a new model specification.
    pub fn new(
        id: &str,
        name: &str,
        parameters: u64,
        quantization: QuantizationType,
        total_layers: usize,
        kv_heads: usize,
        head_dim: usize,
        hidden_dim: usize,
        default_context_length: usize,
        tier: ModelTier,
    ) -> Self {
        Self {
            id: id.to_string(),
            name: name.to_string(),
            parameters,
            quantization,
            total_layers,
            kv_heads,
            head_dim,
            hidden_dim,
            default_context_length,
            tier,
        }
    }

    /// Calculates memory footprint for a specific context length.
    pub fn calculate_memory_breakdown(
        &self,
        context_tokens: usize,
        batch_size: usize,
        safety_margin: f64,
    ) -> MemoryBreakdown {
        calculate_total_required_memory(
            self.parameters,
            self.quantization,
            self.total_layers,
            self.kv_heads,
            self.head_dim,
            self.hidden_dim,
            context_tokens,
            KvCachePrecision::FP16,
            batch_size,
            safety_margin,
        )
    }

    /// Calculates memory weight per individual layer in bytes.
    pub fn calculate_layer_weight_bytes(&self) -> u64 {
        let total_weights = calculate_model_weights_memory(
            self.parameters,
            self.quantization,
            DEFAULT_TENSOR_OVERHEAD,
        );
        total_weights / (self.total_layers.max(1) as u64)
    }

    // -----------------------------------------------------------------------
    // Standard Catalog Presets
    // -----------------------------------------------------------------------

    /// Qwen 2.5 0.5B (Micro/Nano)
    pub fn qwen_2_5_0_5b() -> Self {
        Self::new(
            "qwen-2.5-0.5b-instruct-q4_k_m",
            "Qwen 2.5 0.5B Instruct",
            490_000_000,
            QuantizationType::Q4_K_M,
            24,
            2,
            64,
            896,
            4096,
            ModelTier::MicroNano,
        )
    }

    /// Llama 3.2 1B (Small)
    pub fn llama_3_2_1b() -> Self {
        Self::new(
            "llama-3.2-1b-instruct-q4_k_m",
            "Llama 3.2 1B Instruct",
            1_230_000_000,
            QuantizationType::Q4_K_M,
            16,
            8,
            64,
            2048,
            8192,
            ModelTier::Small,
        )
    }

    /// Llama 3.2 3B (Small)
    pub fn llama_3_2_3b() -> Self {
        Self::new(
            "llama-3.2-3b-instruct-q4_k_m",
            "Llama 3.2 3B Instruct",
            3_210_000_000,
            QuantizationType::Q4_K_M,
            28,
            8,
            128,
            3072,
            8192,
            ModelTier::Small,
        )
    }

    /// Llama 3.1 8B (Medium)
    pub fn llama_3_1_8b() -> Self {
        Self::new(
            "llama-3.1-8b-instruct-q4_k_m",
            "Llama 3.1 8B Instruct",
            8_030_000_000,
            QuantizationType::Q4_K_M,
            32,
            8,
            128,
            4096,
            8192,
            ModelTier::Medium,
        )
    }

    /// Qwen 2.5 14B (Large / Mid-Large)
    pub fn qwen_2_5_14b() -> Self {
        Self::new(
            "qwen-2.5-14b-instruct-q4_k_m",
            "Qwen 2.5 14B Instruct",
            14_770_000_000,
            QuantizationType::Q4_K_M,
            48,
            8,
            128,
            5120,
            8192,
            ModelTier::Large,
        )
    }

    /// Llama 3.3 70B (Large)
    pub fn llama_3_3_70b() -> Self {
        Self::new(
            "llama-3.3-70b-instruct-q4_k_m",
            "Llama 3.3 70B Instruct",
            70_550_000_000,
            QuantizationType::Q4_K_M,
            80,
            8,
            128,
            8192,
            8192,
            ModelTier::Large,
        )
    }
}

/// Execution placement recommendation.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum ExecutionTarget {
    /// 100% of layers and KV cache execute in GPU VRAM
    GpuFull {
        device_id: u32,
        vram_allocated_bytes: u64,
    },
    /// Split execution: N layers on GPU, remaining layers in host system RAM
    Hybrid {
        device_id: u32,
        gpu_layers: usize,
        total_layers: usize,
        vram_bytes: u64,
        ram_bytes: u64,
    },
    /// 100% CPU execution in host system RAM
    CpuOnly {
        ram_allocated_bytes: u64,
        thread_count: usize,
    },
    /// Remote Cloud API fallback
    CloudFallback {
        reason: String,
        suggested_remote_model: String,
    },
}

/// Layer offloading calculation result.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LayerOffloadPlan {
    /// Number of transformer layers offloaded to GPU
    pub gpu_layers: usize,
    /// Number of transformer layers executing in system RAM
    pub cpu_layers: usize,
    /// Total layers in model
    pub total_layers: usize,
    /// Estimated VRAM required for offloaded layers + KV cache + activations
    pub vram_allocated_bytes: u64,
    /// Estimated system RAM required for remaining CPU layers
    pub ram_allocated_bytes: u64,
    /// True if 100% of layers fit in GPU VRAM
    pub is_full_gpu: bool,
    /// True if some layers are on GPU and some on CPU
    pub is_hybrid: bool,
    /// True if 0 layers are on GPU
    pub is_cpu_only: bool,
    /// True if the configuration is physically feasible
    pub is_feasible: bool,
}

/// Calculates GPU layer offload allocation:
/// $$N_{\text{gpu\_layers}} = \min\left(N_{\text{layers}}, \left\lfloor \frac{V_{\text{free}} \times (1 - \gamma) - M_{\text{kv\_gpu}} - M_{\text{act}}}{M_{\text{layer\_weight}}} \right\rfloor\right)$$
pub fn calculate_layer_offload(
    model_spec: &ModelSpec,
    available_vram_bytes: u64,
    context_tokens: usize,
    safety_margin: f64,
) -> LayerOffloadPlan {
    let breakdown = model_spec.calculate_memory_breakdown(context_tokens, 1, safety_margin);
    let total_layers = model_spec.total_layers.max(1);
    let layer_weight = model_spec.calculate_layer_weight_bytes();

    // VRAM available after applying safety margin
    let usable_vram = ((available_vram_bytes as f64) * (1.0 - safety_margin)) as u64;

    // Full GPU check
    if usable_vram >= breakdown.base_total_bytes {
        return LayerOffloadPlan {
            gpu_layers: total_layers,
            cpu_layers: 0,
            total_layers,
            vram_allocated_bytes: breakdown.total_required_bytes,
            ram_allocated_bytes: 0,
            is_full_gpu: true,
            is_hybrid: false,
            is_cpu_only: false,
            is_feasible: true,
        };
    }

    // Fixed overhead in VRAM (KV cache + working activations)
    let fixed_vram_overhead = breakdown.kv_cache_bytes + breakdown.activation_bytes;

    if usable_vram <= fixed_vram_overhead {
        // Not even enough VRAM for KV cache and activations -> Pure CPU
        return LayerOffloadPlan {
            gpu_layers: 0,
            cpu_layers: total_layers,
            total_layers,
            vram_allocated_bytes: 0,
            ram_allocated_bytes: breakdown.total_required_bytes,
            is_full_gpu: false,
            is_hybrid: false,
            is_cpu_only: true,
            is_feasible: true,
        };
    }

    let vram_for_layers = usable_vram.saturating_sub(fixed_vram_overhead);
    let offloadable_layers = if layer_weight > 0 {
        ((vram_for_layers as f64) / (layer_weight as f64)).floor() as usize
    } else {
        total_layers
    };

    let offloadable_layers = offloadable_layers.min(total_layers);
    let cpu_layers = total_layers - offloadable_layers;

    let vram_allocated =
        fixed_vram_overhead + (offloadable_layers as u64 * layer_weight);
    let ram_allocated = (cpu_layers as u64 * layer_weight) + (breakdown.headroom_bytes / 2);

    LayerOffloadPlan {
        gpu_layers: offloadable_layers,
        cpu_layers,
        total_layers,
        vram_allocated_bytes: vram_allocated,
        ram_allocated_bytes: ram_allocated,
        is_full_gpu: offloadable_layers == total_layers,
        is_hybrid: offloadable_layers > 0 && offloadable_layers < total_layers,
        is_cpu_only: offloadable_layers == 0,
        is_feasible: true,
    }
}

/// Comprehensive model routing and resource allocation decision.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct AllocationDecision {
    /// Evaluated model ID
    pub model_id: String,
    /// Model tier
    pub tier: ModelTier,
    /// Quantization format
    pub quantization: QuantizationType,
    /// Recommended execution target
    pub target: ExecutionTarget,
    /// Memory sizing breakdown
    pub memory_breakdown: MemoryBreakdown,
    /// Layer offloading details
    pub layer_offload: LayerOffloadPlan,
    /// Confidence score (0.0 to 1.0)
    pub confidence_score: f32,
    /// Decision rationale and telemetry diagnostics
    pub diagnostics: Vec<String>,
}

/// Dynamic model selection and inference router.
pub struct ModelSelector;

impl ModelSelector {
    /// Evaluates a model against the live system resource snapshot using default safety margin.
    pub fn evaluate(
        model_spec: &ModelSpec,
        context_tokens: usize,
        snapshot: &SystemSnapshot,
    ) -> AllocationDecision {
        Self::evaluate_with_config(
            model_spec,
            context_tokens,
            snapshot,
            DEFAULT_SAFETY_HEADROOM_MARGIN,
        )
    }

    /// Evaluates a model with custom safety headroom margin.
    pub fn evaluate_with_config(
        model_spec: &ModelSpec,
        context_tokens: usize,
        snapshot: &SystemSnapshot,
        safety_margin: f64,
    ) -> AllocationDecision {
        let breakdown =
            model_spec.calculate_memory_breakdown(context_tokens, 1, safety_margin);
        let mut diagnostics = Vec::new();

        // Check severe memory pressure condition (> 92% RAM used)
        if snapshot.memory.memory_pressure_pct > 92.0 {
            diagnostics.push(format!(
                "Host memory pressure is critical ({:.1}% RAM utilized). Routing to Cloud Fallback.",
                snapshot.memory.memory_pressure_pct
            ));
            return AllocationDecision {
                model_id: model_spec.id.clone(),
                tier: model_spec.tier,
                quantization: model_spec.quantization,
                target: ExecutionTarget::CloudFallback {
                    reason: format!(
                        "Critical host RAM pressure ({:.1}%)",
                        snapshot.memory.memory_pressure_pct
                    ),
                    suggested_remote_model: "claude-3-5-sonnet-20241022".to_string(),
                },
                memory_breakdown: breakdown.clone(),
                layer_offload: LayerOffloadPlan {
                    gpu_layers: 0,
                    cpu_layers: model_spec.total_layers,
                    total_layers: model_spec.total_layers,
                    vram_allocated_bytes: 0,
                    ram_allocated_bytes: 0,
                    is_full_gpu: false,
                    is_hybrid: false,
                    is_cpu_only: false,
                    is_feasible: false,
                },
                confidence_score: 0.95,
                diagnostics,
            };
        }

        // 1. Evaluate Primary GPU (if available)
        if let Some(gpu) = snapshot.primary_gpu() {
            let offload_plan = calculate_layer_offload(
                model_spec,
                gpu.free_vram_bytes,
                context_tokens,
                safety_margin,
            );

            // Full GPU fit
            if offload_plan.is_full_gpu {
                diagnostics.push(format!(
                    "Full GPU execution on {} ({}) with {} MB free VRAM (req: {} MB)",
                    gpu.name,
                    gpu.detection_backend,
                    gpu.free_vram_mb(),
                    breakdown.total_required_mb() as u64
                ));

                return AllocationDecision {
                    model_id: model_spec.id.clone(),
                    tier: model_spec.tier,
                    quantization: model_spec.quantization,
                    target: ExecutionTarget::GpuFull {
                        device_id: gpu.device_id,
                        vram_allocated_bytes: breakdown.total_required_bytes,
                    },
                    memory_breakdown: breakdown,
                    layer_offload: offload_plan,
                    confidence_score: 0.99,
                    diagnostics,
                };
            }

            // Hybrid GPU/CPU fit
            if offload_plan.is_hybrid {
                let ram_avail = snapshot.memory.available_ram_bytes;
                if ram_avail >= offload_plan.ram_allocated_bytes {
                    diagnostics.push(format!(
                        "Hybrid offload on {}: {}/{} layers on GPU ({} MB VRAM), {} layers in host RAM ({} MB RAM)",
                        gpu.name,
                        offload_plan.gpu_layers,
                        offload_plan.total_layers,
                        offload_plan.vram_allocated_bytes / (1024 * 1024),
                        offload_plan.cpu_layers,
                        offload_plan.ram_allocated_bytes / (1024 * 1024)
                    ));

                    return AllocationDecision {
                        model_id: model_spec.id.clone(),
                        tier: model_spec.tier,
                        quantization: model_spec.quantization,
                        target: ExecutionTarget::Hybrid {
                            device_id: gpu.device_id,
                            gpu_layers: offload_plan.gpu_layers,
                            total_layers: offload_plan.total_layers,
                            vram_bytes: offload_plan.vram_allocated_bytes,
                            ram_bytes: offload_plan.ram_allocated_bytes,
                        },
                        memory_breakdown: breakdown,
                        layer_offload: offload_plan,
                        confidence_score: 0.88,
                        diagnostics,
                    };
                } else {
                    diagnostics.push(format!(
                        "Hybrid offload attempted ({} GPU layers), but insufficient host RAM for remaining layers (Avail: {} MB, Req: {} MB)",
                        offload_plan.gpu_layers,
                        ram_avail / (1024 * 1024),
                        offload_plan.ram_allocated_bytes / (1024 * 1024)
                    ));
                }
            }
        }

        // 2. Evaluate Pure CPU Host RAM
        let available_ram = snapshot.memory.available_ram_bytes;
        let usable_ram = ((available_ram as f64) * (1.0 - safety_margin)) as u64;

        if usable_ram >= breakdown.base_total_bytes {
            let thread_count = snapshot.cpu.physical_core_count.max(1);
            diagnostics.push(format!(
                "Pure CPU execution on {} cores (Available RAM: {} MB, Req: {} MB)",
                thread_count,
                available_ram / (1024 * 1024),
                breakdown.total_required_mb() as u64
            ));

            return AllocationDecision {
                model_id: model_spec.id.clone(),
                tier: model_spec.tier,
                quantization: model_spec.quantization,
                target: ExecutionTarget::CpuOnly {
                    ram_allocated_bytes: breakdown.total_required_bytes,
                    thread_count,
                },
                memory_breakdown: breakdown.clone(),
                layer_offload: LayerOffloadPlan {
                    gpu_layers: 0,
                    cpu_layers: model_spec.total_layers,
                    total_layers: model_spec.total_layers,
                    vram_allocated_bytes: 0,
                    ram_allocated_bytes: breakdown.total_required_bytes,
                    is_full_gpu: false,
                    is_hybrid: false,
                    is_cpu_only: true,
                    is_feasible: true,
                },
                confidence_score: 0.75,
                diagnostics,
            };
        }

        // 3. Fallback to Cloud API
        let free_vram_mb = snapshot
            .primary_gpu()
            .map(|g| g.free_vram_mb())
            .unwrap_or(0);
        diagnostics.push(format!(
            "Insufficient local memory for {}. Total required: {} MB, Available RAM: {} MB, Free VRAM: {} MB. Falling back to Cloud.",
            model_spec.name,
            breakdown.total_required_mb() as u64,
            available_ram / (1024 * 1024),
            free_vram_mb
        ));

        AllocationDecision {
            model_id: model_spec.id.clone(),
            tier: model_spec.tier,
            quantization: model_spec.quantization,
            target: ExecutionTarget::CloudFallback {
                reason: format!(
                    "Insufficient memory (Req: {} MB, Avail RAM: {} MB, Free VRAM: {} MB)",
                    breakdown.total_required_mb() as u64,
                    available_ram / (1024 * 1024),
                    free_vram_mb
                ),
                suggested_remote_model: "claude-3-5-sonnet-20241022".to_string(),
            },
            memory_breakdown: breakdown,
            layer_offload: LayerOffloadPlan {
                gpu_layers: 0,
                cpu_layers: model_spec.total_layers,
                total_layers: model_spec.total_layers,
                vram_allocated_bytes: 0,
                ram_allocated_bytes: 0,
                is_full_gpu: false,
                is_hybrid: false,
                is_cpu_only: false,
                is_feasible: false,
            },
            confidence_score: 0.95,
            diagnostics,
        }
    }

    /// Selects the best fitting model tier based on current system resource availability.
    pub fn select_best_tier(snapshot: &SystemSnapshot) -> ModelTier {
        let total_free_vram = snapshot.total_free_vram_bytes();
        let avail_ram = snapshot.memory.available_ram_bytes;
        let vram_gb = total_free_vram as f64 / (1024.0 * 1024.0 * 1024.0);
        let ram_gb = avail_ram as f64 / (1024.0 * 1024.0 * 1024.0);

        if vram_gb >= 18.0 || ram_gb >= 48.0 {
            ModelTier::Large
        } else if vram_gb >= 6.0 && ram_gb >= 20.0 || ram_gb >= 24.0 {
            ModelTier::Medium
        } else if vram_gb >= 2.0 || ram_gb >= 6.0 {
            ModelTier::Small
        } else if ram_gb >= 2.5 {
            ModelTier::MicroNano
        } else {
            ModelTier::Cloud
        }
    }

    /// Selects the highest quality model from a catalog that can run locally (preferring Full GPU or Hybrid).
    pub fn select_best_model<'a>(
        catalog: &'a [ModelSpec],
        context_tokens: usize,
        snapshot: &SystemSnapshot,
    ) -> Option<AllocationDecision> {
        let mut best_decision: Option<AllocationDecision> = None;
        let mut best_score: f64 = -1.0;

        for model in catalog {
            let decision = Self::evaluate(model, context_tokens, snapshot);

            let score = match &decision.target {
                ExecutionTarget::GpuFull { .. } => (model.parameters as f64) * 3.0,
                ExecutionTarget::Hybrid { gpu_layers, total_layers, .. } => {
                    let ratio = *gpu_layers as f64 / *total_layers as f64;
                    (model.parameters as f64) * (1.0 + ratio)
                }
                ExecutionTarget::CpuOnly { .. } => (model.parameters as f64) * 0.8,
                ExecutionTarget::CloudFallback { .. } => -100.0,
            };

            if score > best_score {
                best_score = score;
                best_decision = Some(decision);
            }
        }

        best_decision
    }

    /// Returns the default standard catalog of models.
    pub fn default_catalog() -> Vec<ModelSpec> {
        vec![
            ModelSpec::qwen_2_5_0_5b(),
            ModelSpec::llama_3_2_1b(),
            ModelSpec::llama_3_2_3b(),
            ModelSpec::llama_3_1_8b(),
            ModelSpec::qwen_2_5_14b(),
            ModelSpec::llama_3_3_70b(),
        ]
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::gpu::GpuVendor;

    fn make_test_snapshot(free_vram_gb: f64, avail_ram_gb: f64) -> SystemSnapshot {
        let free_vram_bytes = (free_vram_gb * 1024.0 * 1024.0 * 1024.0) as u64;
        let avail_ram_bytes = (avail_ram_gb * 1024.0 * 1024.0 * 1024.0) as u64;
        let total_ram_bytes = avail_ram_bytes * 2;

        let gpus = if free_vram_gb > 0.0 {
            vec![GpuInfo::new_mock(
                0,
                "Mock NVIDIA RTX 4090",
                GpuVendor::Nvidia,
                free_vram_bytes,
                free_vram_bytes,
                Some((8, 9)),
            )]
        } else {
            Vec::new()
        };

        SystemSnapshot {
            timestamp: std::time::SystemTime::now(),
            cpu: crate::telemetry::CpuMetrics {
                physical_core_count: 8,
                logical_core_count: 16,
                global_cpu_usage_pct: 10.0,
                per_core_usage_pct: vec![10.0; 16],
                cpu_brand: "AMD Ryzen 9".to_string(),
                frequency_mhz: 3800,
            },
            memory: crate::telemetry::MemoryMetrics {
                total_ram_bytes,
                used_ram_bytes: total_ram_bytes - avail_ram_bytes,
                available_ram_bytes: avail_ram_bytes,
                free_ram_bytes: avail_ram_bytes,
                total_swap_bytes: 16 * 1024 * 1024 * 1024,
                used_swap_bytes: 0,
                memory_pressure_pct: 50.0,
            },
            process: crate::telemetry::ProcessMetrics {
                pid: 1234,
                process_cpu_usage_pct: 1.0,
                process_memory_bytes: 100 * 1024 * 1024,
                process_virtual_memory_bytes: 200 * 1024 * 1024,
            },
            primary_gpu_index: if gpus.is_empty() { None } else { Some(0) },
            gpus,
        }
    }

    #[test]
    fn test_full_gpu_routing() {
        let snap = make_test_snapshot(24.0, 32.0); // 24GB VRAM, 32GB RAM
        let model = ModelSpec::llama_3_1_8b(); // ~6GB req
        let decision = ModelSelector::evaluate(&model, 8192, &snap);

        match decision.target {
            ExecutionTarget::GpuFull { vram_allocated_bytes, .. } => {
                assert!(vram_allocated_bytes > 0);
            }
            other => panic!("Expected GpuFull, got {:?}", other),
        }
    }

    #[test]
    fn test_hybrid_offload_routing() {
        let snap = make_test_snapshot(4.0, 32.0); // 4GB VRAM, 32GB RAM (cannot fit all 8B weights)
        let model = ModelSpec::llama_3_1_8b();
        let decision = ModelSelector::evaluate(&model, 4096, &snap);

        match decision.target {
            ExecutionTarget::Hybrid { gpu_layers, total_layers, .. } => {
                assert!(gpu_layers > 0 && gpu_layers < total_layers);
                assert_eq!(total_layers, 32);
            }
            other => panic!("Expected Hybrid, got {:?}", other),
        }
    }

    #[test]
    fn test_cpu_only_routing() {
        let snap = make_test_snapshot(0.0, 32.0); // 0 GPU VRAM, 32GB RAM
        let model = ModelSpec::llama_3_1_8b();
        let decision = ModelSelector::evaluate(&model, 8192, &snap);

        match decision.target {
            ExecutionTarget::CpuOnly { ram_allocated_bytes, thread_count } => {
                assert!(ram_allocated_bytes > 0);
                assert_eq!(thread_count, 8);
            }
            other => panic!("Expected CpuOnly, got {:?}", other),
        }
    }

    #[test]
    fn test_cloud_fallback_under_severe_memory_constraint() {
        let snap = make_test_snapshot(0.0, 1.0); // 0 GPU, 1GB RAM (insufficient for 8B model)
        let model = ModelSpec::llama_3_1_8b();
        let decision = ModelSelector::evaluate(&model, 8192, &snap);

        match decision.target {
            ExecutionTarget::CloudFallback { .. } => {}
            other => panic!("Expected CloudFallback, got {:?}", other),
        }
    }
}
