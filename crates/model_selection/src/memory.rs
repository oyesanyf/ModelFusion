//! Memory-aware model selection utilities.
//!
//! Dynamically detects system resources (RAM, VRAM) and estimates model
//! runtime memory to filter out models that cannot run on the current hardware.

use std::process::Command;
use std::sync::OnceLock;
use sysinfo::System;

/// Helper to construct a Command with CREATE_NO_WINDOW on Windows to prevent console flashing.
#[inline]
pub fn create_hidden_command(program: impl AsRef<std::ffi::OsStr>) -> Command {
    let mut cmd = Command::new(program);
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
    }
    cmd
}

/// RAII Guard that temporarily suspends IPv6 on the primary active network adapter during model downloads
/// to prevent Ollama IPv6 DNS / routing stalls, and automatically re-enables IPv6 upon Drop (exit/cancellation/panic).
#[derive(Debug)]
pub struct Ipv6SuspensionGuard {
    pub adapter_name: Option<String>,
    pub active: bool,
}

impl Ipv6SuspensionGuard {
    pub fn acquire() -> Self {
        #[cfg(windows)]
        {
            let output = create_hidden_command("powershell")
                .args(["-NoProfile", "-Command", "Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | Select-Object -ExpandProperty Name -First 1"])
                .output();
            if let Ok(out) = output {
                let adapter = String::from_utf8_lossy(&out.stdout).trim().to_string();
                if !adapter.is_empty() {
                    let _ = create_hidden_command("powershell")
                        .args(["-NoProfile", "-Command", &format!("Disable-NetAdapterBinding -Name '{}' -ComponentID ms_tcpip6 -ErrorAction SilentlyContinue", adapter)])
                        .output();
                    eprintln!("[NET] 🌐 Temporarily suspended IPv6 on adapter '{}' for reliable model download...", adapter);
                    return Self { adapter_name: Some(adapter), active: true };
                }
            }
        }
        Self { adapter_name: None, active: false }
    }
}

impl Drop for Ipv6SuspensionGuard {
    fn drop(&mut self) {
        if self.active {
            if let Some(ref adapter) = self.adapter_name {
                #[cfg(windows)]
                {
                    let _ = create_hidden_command("powershell")
                        .args(["-NoProfile", "-Command", &format!("Enable-NetAdapterBinding -Name '{}' -ComponentID ms_tcpip6 -ErrorAction SilentlyContinue", adapter)])
                        .output();
                    eprintln!("[NET] 🔄 Restored IPv6 binding on adapter '{}'.", adapter);
                }
            }
        }
    }
}

/// Process-level cache so hardware probes only run once per CLI invocation.
static SYSTEM_MEMORY_CACHE: OnceLock<SystemMemory> = OnceLock::new();

/// Detected system memory resources.
#[derive(Debug, Clone)]
pub struct SystemMemory {
    pub total_ram_gb: f64,
    pub free_ram_gb: f64,
    pub cpu_cores: usize,
    pub gpu_name: Option<String>,
    pub gpu_vram_total_gb: f64,
    pub gpu_vram_free_gb: f64,
}

/// Backend execution mode — determines quantization/precision.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Backend {
    Transformers, // FP16 — ~2 bytes per param
    Ollama,       // Q4_0 — ~0.6 bytes per param
    OpenVINO,     // INT4 — ~0.5 bytes per param (optimized CPU inference)
}

/// Safety margin: only use 70% of free memory for model loading.
const SAFETY_FACTOR: f64 = 0.70;

/// Execution device for a model.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Device {
    Gpu,
    Cpu,
}

impl std::fmt::Display for Device {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Device::Gpu => write!(f, "cuda"),
            Device::Cpu => write!(f, "cpu"),
        }
    }
}

/// Dynamic and static hardware requirements mapping.
#[derive(Debug, Clone)]
pub struct HardwareRequirements {
    pub min_ram_gb: f64,
    pub adequate_ram_gb: f64,
    pub min_vram_gb: f64,
    pub adequate_vram_gb: f64,
    pub min_cpu_cores: usize,
    pub adequate_cpu_cores: usize,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SuitabilityResult {
    Inadequate, // Fails minimum specs (filter out)
    Minimum,    // Meets minimum, but not adequate (penalize)
    Adequate,   // Fully adequate (bonus)
}

impl SystemMemory {
    /// Dynamically detect available system resources.
    /// Results are cached for the lifetime of the process so hardware is only
    /// probed once per CLI invocation even if called from multiple select_best_model() calls.
    pub fn detect() -> Self {
        SYSTEM_MEMORY_CACHE.get_or_init(|| {
            Self::detect_live()
        }).clone()
    }

    /// Dynamically detect current runtime system resources (probed live without caching).
    pub fn detect_live() -> Self {
        let mut sys = System::new_all();
        sys.refresh_all();

        let total_ram_gb = sys.total_memory() as f64 / 1_073_741_824.0;
        let free_ram_gb = sys.available_memory() as f64 / 1_073_741_824.0;
        let cpu_cores = sys.physical_core_count().unwrap_or_else(|| sys.cpus().len()).max(1);

        let (gpu_name, gpu_vram_total_gb, gpu_vram_free_gb) = detect_gpu();
        SystemMemory {
            total_ram_gb,
            free_ram_gb,
            cpu_cores,
            gpu_name,
            gpu_vram_total_gb,
            gpu_vram_free_gb,
        }
    }

    /// Whether a usable GPU is detected.
    pub fn has_usable_gpu(&self) -> bool {
        self.gpu_name.is_some() && self.gpu_vram_free_gb > 0.5
    }

    /// Runtime available VRAM in megabytes (MB).
    pub fn free_vram_mb(&self) -> f64 {
        self.gpu_vram_free_gb * 1024.0
    }

    /// GPU VRAM budget (with safety margin).
    pub fn gpu_budget_gb(&self) -> f64 {
        // Allow utilizing up to 85% of actual free VRAM, leaving a 15% safety margin
        (self.gpu_vram_free_gb * 0.85).max(0.0)
    }

    /// CPU RAM budget (with safety margin).
    pub fn ram_budget_gb(&self) -> f64 {
        // Subtract a 3.0 GB base memory buffer for the python/pytorch runtime execution context overhead,
        // then allocate a safety fraction (70%) of the remaining free memory.
        ((self.free_ram_gb - 3.0) * SAFETY_FACTOR).max(0.0)
    }

    /// Maximum memory budget for a single model — uses GPU if available, otherwise RAM.
    /// For the overall filter, we use the LARGER of the two (models that fit in either can run).
    pub fn model_budget_gb(&self) -> f64 {
        // Models can run on EITHER device, so the max budget is the larger resource pool
        self.ram_budget_gb().max(self.gpu_budget_gb())
    }

    /// Determine the best device for a model of the given estimated memory size.
    /// Prefers GPU when the model fits in VRAM.
    pub fn best_device_for_model(&self, model_memory_gb: f64) -> Device {
        if std::env::var("MODELFUSION_FORCE_GPU").is_ok() {
            Device::Gpu
        } else if std::env::var("MODELFUSION_FORCE_CPU").is_ok() {
            Device::Cpu
        } else if self.has_usable_gpu() && model_memory_gb <= self.gpu_budget_gb() {
            Device::Gpu
        } else {
            Device::Cpu
        }
    }

    /// Print a summary of detected resources.
    pub fn print_summary(&self) {
        println!("💾 [HARDWARE] CPU Cores: {} physical/logical", self.cpu_cores);
        println!("💾 [MEMORY] System RAM: {:.1} GB total, {:.1} GB free (budget: {:.1} GB per model)",
            self.total_ram_gb, self.free_ram_gb, self.ram_budget_gb());
        if let Some(ref gpu) = self.gpu_name {
            println!("🎮 [MEMORY] GPU: {} — {:.1} GB total VRAM, {:.1} GB free (budget: {:.1} GB)",
                gpu, self.gpu_vram_total_gb, self.gpu_vram_free_gb, self.gpu_budget_gb());
        } else {
            println!("🎮 [MEMORY] GPU: Not detected (CPU-only execution)");
        }
    }

    /// Derive the optimal number of models for a fusion panel based on live available runtime memory
    /// (runtime free RAM and runtime free VRAM).
    /// Free RAM >= 64GB or Free VRAM >= 24GB -> 7 models;
    /// >= 32GB/12GB -> 5 models;
    /// >= 16GB/6GB -> 4 models;
    /// >= 8GB/3GB -> 3 models;
    /// < 8GB -> 2 models.
    pub fn derive_fusion_model_count(&self) -> usize {
        let free_ram = self.free_ram_gb;
        let free_vram = self.gpu_vram_free_gb;

        if free_ram >= 64.0 || free_vram >= 24.0 {
            7
        } else if free_ram >= 32.0 || free_vram >= 12.0 {
            5
        } else if free_ram >= 16.0 || free_vram >= 6.0 {
            4
        } else if free_ram >= 8.0 || free_vram >= 3.0 {
            3
        } else {
            2
        }
    }

    /// Assess runtime hardware resources and activate Recursive Flint
    /// (`RecursiveSI/flint` / `flint:latest` 40B total / 2.5B active MoE) + Block Goose (`goose`)
    /// by default for all Coding and Multi-Model Fusion tasks (never blocked).
    pub fn assess_flint_for_task(&self, is_fusion_mode: bool, is_coding_task: bool) -> FlintResourceAssessment {
        let ollama_cached = is_ollama_model_cached("flint:latest") || is_ollama_model_cached("RecursiveSI/flint");
        let resources_available = self.free_ram_gb >= 12.0 || self.gpu_vram_free_gb >= 4.0 || ollama_cached;
        let compact_offload_available = self.free_ram_gb >= 6.0 || self.gpu_vram_free_gb >= 2.0 || ollama_cached;

        // Recursive Flint + Block Goose are NEVER blocked and are active by default for coding and fusion
        let flint_activated_in_fusion = true;

        let (active_tier, status_reason, coding_fusion_panel) = if self.free_ram_gb >= 24.0 || self.gpu_vram_free_gb >= 16.0 || ollama_cached {
            let panel = if self.free_ram_gb >= 48.0 || self.gpu_vram_free_gb >= 24.0 {
                vec![
                    "flint:latest".to_string(),
                    "RecursiveSI/flint".to_string(),
                    "qwen2.5:32b".to_string(),
                    "qwen2.5:7b".to_string(),
                    "deepseek-r1:32b".to_string(),
                ]
            } else {
                vec![
                    "flint:latest".to_string(),
                    "RecursiveSI/flint".to_string(),
                    "qwen2.5:7b".to_string(),
                    "deepseek-r1:1.5b".to_string(),
                ]
            };
            (
                "Tier 1: Full Flint 40B-A2.5B MoE + Block Goose + Coding Fusion (Default Active)".to_string(),
                "Recursive Flint (flint:latest 40B-A2.5B MoE) + Block Goose active by default for coding and fusion.".to_string(),
                panel,
            )
        } else if compact_offload_available {
            (
                "Tier 2: Compact Flint MoE + Block Goose + Fast Coding Fusion (Default Active)".to_string(),
                "Recursive Flint (flint:latest) + Block Goose active by default in compact mode.".to_string(),
                vec![
                    "flint:latest".to_string(),
                    "RecursiveSI/flint".to_string(),
                    "qwen2.5:7b".to_string(),
                    "deepseek-r1:1.5b".to_string(),
                ],
            )
        } else {
            let base = if self.free_ram_gb >= 6.0 { "qwen2.5:3b" } else { "qwen2.5:1.5b" };
            (
                "Tier 3: Lightweight Flint MoE + Block Goose Coding Fusion (Default Active)".to_string(),
                "Recursive Flint (flint:latest) + Block Goose active by default with lightweight verifiers.".to_string(),
                vec!["flint:latest".to_string(), base.to_string(), "deepseek-r1:1.5b".to_string()],
            )
        };

        FlintResourceAssessment {
            model_id: "RecursiveSI/flint".to_string(),
            ollama_tag: "flint:latest".to_string(),
            total_params_b: 40.0,
            active_params_b: 2.5,
            required_min_ram_gb: 6.0,
            required_min_vram_gb: 4.0,
            detected_free_ram_gb: self.free_ram_gb,
            detected_free_vram_gb: self.gpu_vram_free_gb,
            resources_available,
            compact_offload_available,
            ollama_cached,
            is_coding_task: is_coding_task || true,
            is_fusion_mode: is_fusion_mode || true,
            flint_activated_in_fusion,
            active_tier,
            recommended_context_tokens: 262_144,
            max_context_tokens: 524_288,
            temperature: 1.0,
            top_p: 0.95,
            top_k: 20,
            coding_fusion_panel,
            status_reason,
        }
    }

    /// Default evaluation for coding fusion with fusion mode and coding task enabled.
    pub fn assess_flint_coding_fusion(&self) -> FlintResourceAssessment {
        self.assess_flint_for_task(true, true)
    }

    /// Calibrate Z.ai General Language Model (GLM) variants for ModelFusion strictly when
    /// runtime memory resources are available (`free_ram_gb >= 8.0 || gpu_vram_free_gb >= 6.0`).
    /// Never activates GLM when runtime available memory is below the 8 GB RAM / 6 GB VRAM floor.
    pub fn assess_glm_for_fusion(&self) -> GlmResourceAssessment {
        let free_ram = self.free_ram_gb;
        let free_vram = self.gpu_vram_free_gb;
        let combined_free = free_ram + free_vram;

        // Strict resource gate: only activate GLM in fusion when runtime resources are available
        let resources_available = free_vram >= 6.0 || free_ram >= 8.0;
        if !resources_available {
            return GlmResourceAssessment {
                resources_available: false,
                glm_activated_in_fusion: false,
                model_id: "zai-org/GLM-4-9B-0414".to_string(),
                ollama_tag: "glm4:9b".to_string(),
                vram_sweet_spot_tag: None,
                moe_offload_tag: None,
                workstation_flagship_build: None,
                total_params_b: 9.0,
                active_params_b: 9.0,
                required_min_ram_gb: 8.0,
                required_min_vram_gb: 6.0,
                detected_free_ram_gb: free_ram,
                detected_free_vram_gb: free_vram,
                ollama_cached: false,
                active_tier: "Tier 0: Insufficient Runtime Memory (< 6 GB Free VRAM & < 8 GB Free RAM — GLM Disabled)".to_string(),
                status_reason: format!(
                    "GLM excluded from fusion: runtime Free RAM ({:.1} GB) < 8.0 GB and Free VRAM ({:.1} GB) < 6.0 GB.",
                    free_ram, free_vram
                ),
            };
        }

        let vram_sweet_spot_tag = if free_vram >= 36.0 {
            Some("glm-4.7-flash:q8_0".to_string())
        } else if free_vram >= 20.0 {
            Some("glm-4.7-flash:q4_K_M".to_string())
        } else if free_vram >= 16.0 {
            Some("glm4:9b-chat-q8_0".to_string())
        } else if free_vram >= 6.0 {
            Some("glm4:9b".to_string())
        } else {
            None
        };

        let (
            default_hf_id,
            default_ollama_tag,
            moe_offload_tag,
            workstation_flagship_build,
            total_params_b,
            active_params_b,
            active_tier,
            status_reason,
        ) = if combined_free >= 245.0 || free_ram >= 245.0 {
            (
                "zai-org/GLM-5.3",
                "glm-4.7-flash:bf16",
                Some("glm-4.7-flash:bf16".to_string()),
                Some("GLM-5.3-UD-Q2_K_XL (753B/40B active ~245 GB) & GLM-5.3-Flash-Q4_K_M (320B/18B active)".to_string()),
                753.0,
                40.0,
                "Tier 6: Frontier 256 GB+ Workstation/Cluster (GLM-5.1/5.2/5.3 744B-753B MoE & GLM-5.3-Flash 4-bit)".to_string(),
                "Frontier 256 GB+ tier active: supports GLM-5.1/5.2/5.3 (1-bit/2-bit) and GLM-5.3-Flash (4-bit).".to_string(),
            )
        } else if combined_free >= 210.0 || free_ram >= 210.0 {
            (
                "zai-org/GLM-4.7",
                "glm-4.7-flash:bf16",
                Some("glm-4.7-flash:bf16".to_string()),
                Some("GLM-4.7-Q4_K_M (355B 4-bit ~210 GB)".to_string()),
                355.0,
                32.0,
                "Tier 5: Heavy 210 GB+ Workstation (GLM-4.7 355B 4-bit + GLM-4.7-Flash 30B-A3.6B MoE)".to_string(),
                "Heavy 210 GB+ workstation tier active: supports full GLM-4.7 355B 4-bit and GLM-4.7-Flash.".to_string(),
            )
        } else if combined_free >= 128.0 || free_ram >= 128.0 {
            (
                "zai-org/GLM-4.7-Flash",
                if free_vram >= 6.0 && free_vram < 16.0 { "glm4:9b" } else { "glm-4.7-flash:q8_0" },
                Some("glm-4.7-flash:q8_0".to_string()),
                Some("GLM-4.7-UD-Q2_K_XL (355B 2-bit ~128 GB) / GLM-5.3-Flash-UD-IQ1_M (320B/18B 1-bit ~128 GB)".to_string()),
                30.0,
                3.6,
                "Tier 4: 128 GB+ Workstation Offload (GLM-4.7-Flash 30B-A3.6B MoE + In-VRAM GLM-4 9B + GLM-4.7 355B Q2_K)".to_string(),
                "Workstation 128 GB+ tier active: pairs in-VRAM glm4:9b (5.5 GB) with GLM-4.7-Flash (30B/3.6B active MoE) and supports 128 GB GLM-4.7 Q2_K / GLM-5.3-Flash IQ1_M.".to_string(),
            )
        } else if free_vram >= 36.0 || free_ram >= 36.0 {
            (
                "zai-org/GLM-4.7-Flash",
                "glm-4.7-flash:q8_0",
                Some("glm-4.7-flash:q8_0".to_string()),
                Some("GLM-4.7-Flash-Q8_0 (30B/3.6B active MoE 8-bit/16-bit)".to_string()),
                30.0,
                3.6,
                "Tier 3: 36-64 GB Memory (GLM-4.7-Flash 30B-A3.6B MoE 8-bit Q8_0 / FP16)".to_string(),
                "36-64 GB tier active: GLM-4.7-Flash (30B/3.6B active MoE) at 8-bit/full precision.".to_string(),
            )
        } else if free_vram >= 20.0 || free_ram >= 24.0 {
            (
                "zai-org/GLM-4.7-Flash",
                "glm-4.7-flash:q4_K_M",
                Some("glm-4.7-flash:q4_K_M".to_string()),
                Some("GLM-4.7-Flash-Q4_K_M (30B/3.6B active MoE 4-bit ~19 GB)".to_string()),
                30.0,
                3.6,
                "Tier 2: 24-36 GB Sweet Spot (GLM-4.7-Flash 30B-A3.6B MoE 4-bit Q4_K_M)".to_string(),
                "24-36 GB tier active: GLM-4.7-Flash (30B/3.6B active MoE) at 4-bit quantization.".to_string(),
            )
        } else if free_vram >= 16.0 || free_ram >= 16.0 {
            (
                "zai-org/GLM-4-9B-0414",
                "glm4:9b-chat-q8_0",
                Some("glm-4.7-flash:q2_K".to_string()),
                Some("GLM-4-9B (Q8_0 / FP16) or GLM-4.7-Flash (Q2_K)".to_string()),
                9.0,
                9.0,
                "Tier 1B: 16-20 GB Memory (GLM-4 9B Q8_0/FP16 or GLM-4.7-Flash Q2_K)".to_string(),
                "16-20 GB tier active: GLM-4 9B 8-bit/16-bit or 2-bit GLM-4.7-Flash.".to_string(),
            )
        } else {
            (
                "zai-org/GLM-4-9B-0414",
                "glm4:9b",
                Some("glm4:9b".to_string()),
                Some("GLM-4-9B / GLM-4V-9B / GLM-4.6V-Flash (4-bit Q4_K_M ~5.5-8 GB)".to_string()),
                9.0,
                9.0,
                "Tier 1A: 8-16 GB Memory (GLM-4 9B / GLM-4V 9B / GLM-4.6V-Flash 4-bit Q4_K_M)".to_string(),
                "8-16 GB tier active: GLM-4 9B family at 4-bit quantization (~5.5-8 GB).".to_string(),
            )
        };

        let cached_tags = get_ollama_cached_models();
        let resolved_ollama_tag = if free_vram >= 6.0 && free_vram < 16.0 && cached_tags.iter().any(|t| t == "glm4:9b" || t.starts_with("glm4:")) {
            cached_tags.iter().find(|t| t == &"glm4:9b" || t.starts_with("glm4:")).cloned().unwrap_or_else(|| "glm4:9b".to_string())
        } else if let Some(found) = cached_tags.iter().find(|t| t.starts_with("glm-4.7-flash") || t.starts_with("glm4")) {
            found.clone()
        } else {
            default_ollama_tag.to_string()
        };

        let ollama_cached = is_ollama_model_cached(&resolved_ollama_tag);

        GlmResourceAssessment {
            resources_available: true,
            glm_activated_in_fusion: true,
            model_id: default_hf_id.to_string(),
            ollama_tag: resolved_ollama_tag,
            vram_sweet_spot_tag,
            moe_offload_tag,
            workstation_flagship_build,
            total_params_b,
            active_params_b,
            required_min_ram_gb: 8.0,
            required_min_vram_gb: 6.0,
            detected_free_ram_gb: free_ram,
            detected_free_vram_gb: free_vram,
            ollama_cached,
            active_tier,
            status_reason,
        }
    }
}

/// Resource-gated Z.ai GLM assessment for ModelFusion.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct GlmResourceAssessment {
    pub resources_available: bool,
    pub glm_activated_in_fusion: bool,
    pub model_id: String,
    pub ollama_tag: String,
    pub vram_sweet_spot_tag: Option<String>,
    pub moe_offload_tag: Option<String>,
    pub workstation_flagship_build: Option<String>,
    pub total_params_b: f64,
    pub active_params_b: f64,
    pub required_min_ram_gb: f64,
    pub required_min_vram_gb: f64,
    pub detected_free_ram_gb: f64,
    pub detected_free_vram_gb: f64,
    pub ollama_cached: bool,
    pub active_tier: String,
    pub status_reason: String,
}

/// Check if a model is part of the unblocked default stack (Recursive Flint, Block Goose, RAPTOR).
/// Invariant: Flint, Goose, and RAPTOR always have P_memory = 0.0 and are never blocked.
pub fn is_unblocked_default(model_id: &str) -> bool {
    let lower = model_id.to_lowercase();
    model_id == "flint:latest"
        || model_id == "RecursiveSI/flint"
        || model_id == "goose"
        || model_id == "raptor"
        || lower.contains("flint")
        || lower.contains("goose")
        || lower.contains("raptor")
}

/// Evaluation of Recursive Flint (40B total / 2.5B active MoE) suitability for Coding Fusion.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct FlintResourceAssessment {
    pub model_id: String,
    pub ollama_tag: String,
    pub total_params_b: f64,
    pub active_params_b: f64,
    pub required_min_ram_gb: f64,
    pub required_min_vram_gb: f64,
    pub detected_free_ram_gb: f64,
    pub detected_free_vram_gb: f64,
    pub resources_available: bool,
    pub compact_offload_available: bool,
    pub ollama_cached: bool,
    pub is_coding_task: bool,
    pub is_fusion_mode: bool,
    pub flint_activated_in_fusion: bool,
    pub active_tier: String,
    pub recommended_context_tokens: usize,
    pub max_context_tokens: usize,
    pub temperature: f32,
    pub top_p: f32,
    pub top_k: u32,
    pub coding_fusion_panel: Vec<String>,
    pub status_reason: String,
}

/// Convenience function to detect live system memory and derive the optimal fusion model count.
pub fn derive_fusion_model_count() -> usize {
    SystemMemory::detect_live().derive_fusion_model_count()
}


/// Calculate hardware requirements dynamically based on model size and backend.
pub fn get_requirements_for_model(params_b: f64, backend: Backend) -> HardwareRequirements {
    let runtime_memory = estimate_runtime_memory_gb(params_b, backend);
    
    let min_ram_gb = runtime_memory;
    let adequate_ram_gb = runtime_memory * 1.30;

    let (min_vram_gb, adequate_vram_gb) = if backend == Backend::Transformers {
        (runtime_memory, runtime_memory * 1.30)
    } else {
        (0.0, 0.0)
    };

    let (min_cpu_cores, adequate_cpu_cores) = if params_b <= 3.0 {
        (2, 4)
    } else if params_b <= 8.0 {
        (4, 6)
    } else {
        (6, 8)
    };

    HardwareRequirements {
        min_ram_gb,
        adequate_ram_gb,
        min_vram_gb,
        adequate_vram_gb,
        min_cpu_cores,
        adequate_cpu_cores,
    }
}

/// Evaluate whether system hardware matches Minimum and Adequate requirements.
pub fn evaluate_hardware_suitability(
    params_b: f64,
    backend: Backend,
    sys: &SystemMemory,
) -> SuitabilityResult {
    if params_b == 0.0 {
        return SuitabilityResult::Adequate;
    }

    let reqs = get_requirements_for_model(params_b, backend);

    // 1. Check minimum requirements (Strictly Dynamic Available Memory Law)
    let has_min_memory = sys.free_ram_gb >= reqs.min_ram_gb 
        || (sys.gpu_name.is_some() && sys.gpu_vram_free_gb >= reqs.min_vram_gb);
    let has_min_cores = sys.cpu_cores >= reqs.min_cpu_cores;

    if !has_min_memory || !has_min_cores {
        return SuitabilityResult::Inadequate;
    }

    // 2. Check adequacy requirements
    let has_adequate_memory = sys.model_budget_gb() >= reqs.adequate_ram_gb
        || (sys.gpu_name.is_some() && sys.gpu_budget_gb() >= reqs.adequate_vram_gb);
    let has_adequate_cores = sys.cpu_cores >= reqs.adequate_cpu_cores;

    if has_adequate_memory && has_adequate_cores {
        SuitabilityResult::Adequate
    } else {
        SuitabilityResult::Minimum
    }
}

/// Detect GPU name and VRAM via nvidia-smi.
fn detect_gpu() -> (Option<String>, f64, f64) {
    let output = create_hidden_command("nvidia-smi")
        .args(["--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"])
        .output();

    match output {
        Ok(o) if o.status.success() => {
            let text = String::from_utf8_lossy(&o.stdout);
            let line = text.trim();
            let parts: Vec<&str> = line.split(',').map(|s| s.trim()).collect();
            if parts.len() >= 3 {
                let name = parts[0].to_string();
                let total_mb: f64 = parts[1].parse().unwrap_or(0.0);
                let free_mb: f64 = parts[2].parse().unwrap_or(0.0);
                (Some(name), total_mb / 1024.0, free_mb / 1024.0)
            } else {
                (None, 0.0, 0.0)
            }
        }
        _ => (None, 0.0, 0.0),
    }
}

/// Extract parameter count in billions from a model ID string.
///
/// Examples:
///   "Qwen/Qwen2.5-7B-Instruct" → Some(7.0)
///   "meta-llama/Llama-3.1-8B-Instruct" → Some(8.0)
///   "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B" → Some(1.5)
///   "deepseek-ai/DeepSeek-R1" → Some(671.0) (hardcoded known model)
pub fn estimate_params_billions(model_id: &str) -> Option<f64> {
    // Hardcoded known models that don't have param count in name
    let known_models: &[(&str, f64)] = &[
        ("DeepSeek-R1-0528", 671.0),
        ("DeepSeek-V3.2", 671.0),
        ("DeepSeek-V3-0324", 671.0),
        ("DeepSeek-V4-Pro", 800.0),
        ("DeepSeek-V4-Flash", 236.0),
        ("flint", 40.0),
        ("Flint", 40.0),
        ("flint-40b", 40.0),
        ("flint-40b-a2.5b", 40.0),
        ("Mixtral-8x7B", 46.7),
        ("Mixtral-8x22B", 141.0),
        ("gpt2", 0.124),
        ("gpt2-medium", 0.355),
        ("gpt2-large", 0.774),
        ("gpt2-xl", 1.5),
        ("opt-125m", 0.125),
        ("opt-350m", 0.350),
        ("opt-1.3b", 1.3),
        ("opt-6.7b", 6.7),
        ("bloom-560m", 0.56),
        ("bloom-1b7", 1.7),
        ("bloom-7b1", 7.1),
        ("GLM-4-9B", 9.0),
        ("GLM-4-9B-0414", 9.0),
        ("GLM-4V-9B", 9.0),
        ("GLM-4.6V-Flash", 9.0),
        ("GLM-4.7-Flash", 30.0),
        ("GLM-4.7", 355.0),
        ("GLM-5.3-Flash", 320.0),
        ("GLM-5-FP8", 744.0),
        ("GLM-5", 744.0),
        ("GLM-5.1", 744.0),
        ("GLM-5.2", 744.0),
        ("GLM-5.3", 753.0),
    ];

    // Check hardcoded known models first (must check before regex to avoid false matches)
    let model_name = model_id.split('/').last().unwrap_or(model_id);
    for (name, params) in known_models {
        if model_name.eq_ignore_ascii_case(name) {
            return Some(*params);
        }
    }
    let lower_id = model_id.to_lowercase();
    if lower_id.starts_with("glm-4.7-flash") || lower_id.contains("/glm-4.7-flash") {
        return Some(30.0);
    } else if lower_id.starts_with("glm-4.7") || lower_id.contains("/glm-4.7") {
        return Some(355.0);
    } else if lower_id.starts_with("glm-5.3-flash") || lower_id.contains("/glm-5.3-flash") {
        return Some(320.0);
    } else if lower_id.starts_with("glm-5") || lower_id.contains("/glm-5") {
        return Some(744.0);
    } else if lower_id.starts_with("glm4") || lower_id.starts_with("glm-4") {
        return Some(9.0);
    }

    // Special case: "DeepSeek-R1" exactly (not a distill variant)
    if model_name == "DeepSeek-R1" {
        return Some(671.0);
    }

    if model_id.to_lowercase().contains("recursivesi/flint") || model_id.to_lowercase().starts_with("flint:") {
        return Some(40.0);
    }

    // Extract parameter count from patterns like "7B", "1.5B", "70b", "0.6B"
    // Scan through the model name looking for number+B patterns
    let lower = model_name.to_lowercase();
    let chars: Vec<char> = lower.chars().collect();
    let len = chars.len();

    let mut best_match: Option<f64> = None;
    let mut i = 0;
    while i < len {
        // Look for a digit
        if chars[i].is_ascii_digit() {
            let start = i;
            // Consume digits, dots, and 'x' (for patterns like 8x7)
            while i < len && (chars[i].is_ascii_digit() || chars[i] == '.') {
                i += 1;
            }
            // Check if followed by 'b' (billion)
            if i < len && chars[i] == 'b' {
                let num_str: String = chars[start..i].iter().collect();
                if let Ok(val) = num_str.parse::<f64>() {
                    if val > 0.0 && val < 2000.0 {
                        // Check it's not part of a longer word after 'b'
                        let after_b = i + 1;
                        let valid_boundary = after_b >= len
                            || !chars[after_b].is_ascii_alphabetic()
                            || chars[after_b] == '-'
                            || chars[after_b] == '_';
                        if valid_boundary {
                            best_match = Some(val);
                        }
                    }
                }
            }
            // Check for 'm' (million) — e.g., "125m"
            if i < len && chars[i] == 'm' {
                let num_str: String = chars[start..i].iter().collect();
                if let Ok(val) = num_str.parse::<f64>() {
                    if val > 50.0 && val < 10000.0 {
                        let after_m = i + 1;
                        let valid_boundary = after_m >= len
                            || !chars[after_m].is_ascii_alphabetic()
                            || chars[after_m] == '-'
                            || chars[after_m] == '_';
                        if valid_boundary {
                            best_match = Some(val / 1000.0); // Convert millions to billions
                        }
                    }
                }
            }
        }
        i += 1;
    }

    best_match
}

/// Estimate active parameters per token in billions.
/// For Mixture-of-Experts (MoE) models like Recursive Flint (`RecursiveSI/flint`),
/// only 2.5B active parameters execute per token out of 40B total parameters.
/// For dense models, returns the standard total parameter count.
pub fn estimate_active_params_billions(model_id: &str) -> Option<f64> {
    let lower = model_id.to_lowercase();
    if lower.contains("recursivesi/flint") || lower == "flint" || lower.starts_with("flint:") || lower.contains("flint-40b") {
        Some(2.5)
    } else if lower.contains("glm-4.7-flash") {
        Some(3.6)
    } else if lower.contains("glm-5.3-flash") {
        Some(18.0)
    } else if lower.contains("glm-5") {
        Some(40.0)
    } else if lower.contains("glm-4.7") {
        Some(32.0)
    } else {
        estimate_params_billions(model_id)
    }
}

/// Estimate the runtime memory (in GB) needed to load and run a model.
///
/// - Transformers (FP16): params_billions × 2 bytes × 1.2 overhead = params × 2.4 GB
/// - Ollama (Q4_0):       params_billions × 0.6 bytes × 1.2 overhead = params × 0.72 GB
/// - OpenVINO (INT4):     params_billions × 0.5 bytes × 1.2 overhead = params × 0.6 GB
pub fn estimate_runtime_memory_gb(params_billions: f64, backend: Backend) -> f64 {
    let bytes_per_param = match backend {
        Backend::Transformers => 2.0,  // float16
        Backend::Ollama => 0.6,       // q4_0 quantization
        Backend::OpenVINO => 0.5,     // int4 quantization (optimum-intel)
    };
    let overhead = 1.2; // KV cache, activations, OS overhead
    params_billions * bytes_per_param * overhead
}

/// Check if a model can fit in the available memory.
pub fn model_fits(params_billions: f64, backend: Backend, memory: &SystemMemory) -> bool {
    let required = estimate_runtime_memory_gb(params_billions, backend);
    required <= memory.model_budget_gb()
}

/// Check if Ollama is actually responding by making a real HTTP request.
pub fn is_ollama_responding(endpoint: &str) -> bool {
    let client = reqwest::blocking::Client::builder()
        .no_proxy()
        .timeout(std::time::Duration::from_millis(3000))
        .build()
        .unwrap_or_default();
    let url = format!("{}/api/tags", endpoint.trim_end_matches('/'));
    for _ in 0..2 {
        if let Ok(r) = client.get(&url).header("Origin", "null").send() {
            if r.status().is_success() {
                return true;
            }
        }
        std::thread::sleep(std::time::Duration::from_millis(150));
    }
    false
}

/// Check if Ollama is installed on the system (in PATH or common installation paths).
pub fn is_ollama_installed() -> bool {
    let check_installed = create_hidden_command("where")
        .arg("ollama")
        .output();

    if let Ok(output) = check_installed {
        if output.status.success() {
            let stdout = String::from_utf8_lossy(&output.stdout);
            for line in stdout.lines() {
                let trimmed = line.trim();
                let p = std::path::PathBuf::from(trimmed);
                if p.is_file() {
                    return true;
                }
            }
        }
    }

    let mut common_candidates = Vec::new();
    if let Ok(local_app_data) = std::env::var("LOCALAPPDATA") {
        common_candidates.push(std::path::PathBuf::from(local_app_data).join("Programs").join("Ollama").join("ollama.exe"));
    }
    if let Ok(prog_files) = std::env::var("ProgramFiles") {
        common_candidates.push(std::path::PathBuf::from(prog_files).join("Ollama").join("ollama.exe"));
    }
    common_candidates.push(std::path::PathBuf::from(r"C:\Program Files\Ollama\ollama.exe"));

    for cand in common_candidates {
        if cand.is_file() {
            return true;
        }
    }

    false
}

/// Check if the Ollama endpoint is accepting requests with CORS Origin headers (e.g. Origin: null from file:/// or browser origins).
pub fn is_ollama_cors_ready(endpoint: &str) -> bool {
    let client = reqwest::blocking::Client::builder()
        .no_proxy()
        .timeout(std::time::Duration::from_millis(800))
        .build()
        .unwrap_or_default();
    let url = format!("{}/api/tags", endpoint.trim_end_matches('/'));
    client.get(&url)
        .header("Origin", "null")
        .send()
        .map(|r| r.status().is_success())
        .unwrap_or(false)
}

/// Ensure Ollama is running. If it's not, auto-start `ollama serve` and wait for it.
pub fn ensure_ollama_running() -> Result<(), String> {
    let endpoint = std::env::var("LOCAL_OLLAMA_ENDPOINT")
        .unwrap_or_else(|_| "http://127.0.0.1:11434".to_string());

    // Always guarantee OLLAMA_ORIGINS=* is injected into current process environment
    std::env::set_var("OLLAMA_ORIGINS", "*");

    // First check: is it already running?
    if is_ollama_responding(&endpoint) {
        return Ok(());
    }

    // If not responding, ensure any hung/dead instances are terminated so port 11434 is immediately freed
    #[cfg(windows)]
    {
        let _ = create_hidden_command("taskkill")
            .args(["/F", "/IM", "ollama.exe", "/IM", "ollama_llama_server.exe", "/T"])
            .output();
        std::thread::sleep(std::time::Duration::from_millis(500));
    }

    // Check if Ollama is installed: PATH first, then common installation paths
    let mut ollama_path: Option<std::path::PathBuf> = None;

    let check_installed = create_hidden_command("where")
        .arg("ollama")
        .output();

    if let Ok(output) = check_installed {
        if output.status.success() {
            let stdout = String::from_utf8_lossy(&output.stdout);
            for line in stdout.lines() {
                let trimmed = line.trim();
                let p = std::path::PathBuf::from(trimmed);
                if p.is_file() {
                    ollama_path = Some(p);
                    break;
                }
            }
        }
    }

    if ollama_path.is_none() {
        let mut common_candidates = Vec::new();
        if let Ok(local_app_data) = std::env::var("LOCALAPPDATA") {
            common_candidates.push(std::path::PathBuf::from(local_app_data).join("Programs").join("Ollama").join("ollama.exe"));
        }
        if let Ok(prog_files) = std::env::var("ProgramFiles") {
            common_candidates.push(std::path::PathBuf::from(prog_files).join("Ollama").join("ollama.exe"));
        }
        common_candidates.push(std::path::PathBuf::from(r"C:\Program Files\Ollama\ollama.exe"));

        for cand in common_candidates {
            if cand.is_file() {
                ollama_path = Some(cand);
                break;
            }
        }
    }

    // If not found at all, auto-download and install silently
    if ollama_path.is_none() {
        eprintln!("🦙 [OLLAMA] Ollama is not installed. Downloading and installing silently (this may take a minute)...");
        let temp_dir = std::env::temp_dir();
        let installer_path = temp_dir.join("OllamaSetup.exe");
        let client = reqwest::blocking::Client::builder()
            .timeout(std::time::Duration::from_secs(180))
            .build()
            .unwrap_or_default();
        let mut downloaded_ok = false;
        if let Ok(mut r) = client.get("https://ollama.com/download/OllamaSetup.exe").send() {
            if r.status().is_success() {
                if let Ok(mut f) = std::fs::File::create(&installer_path) {
                    if std::io::copy(&mut r, &mut f).is_ok() {
                        downloaded_ok = true;
                    }
                }
            }
        }

        if downloaded_ok {
            let status = create_hidden_command(&installer_path)
                .args(["/SILENT", "/NORESTART"])
                .status();
            if let Ok(st) = status {
                if st.success() {
                    eprintln!("🦙 [OLLAMA] Installation complete!");
                    std::thread::sleep(std::time::Duration::from_secs(3));
                }
            }
        } else {
            eprintln!("🦙 [OLLAMA] Failed to download Ollama installer automatically.");
        }

        // Re-check where ollama or common paths
        if let Ok(output) = create_hidden_command("where").arg("ollama").output() {
            if output.status.success() {
                let stdout = String::from_utf8_lossy(&output.stdout);
                for line in stdout.lines() {
                    let p = std::path::PathBuf::from(line.trim());
                    if p.is_file() {
                        ollama_path = Some(p);
                        break;
                    }
                }
            }
        }

        if ollama_path.is_none() {
            let mut post_candidates = Vec::new();
            if let Ok(local_app_data) = std::env::var("LOCALAPPDATA") {
                post_candidates.push(std::path::PathBuf::from(local_app_data).join("Programs").join("Ollama").join("ollama.exe"));
            }
            if let Ok(prog_files) = std::env::var("ProgramFiles") {
                post_candidates.push(std::path::PathBuf::from(prog_files).join("Ollama").join("ollama.exe"));
            }
            post_candidates.push(std::path::PathBuf::from(r"C:\Program Files\Ollama\ollama.exe"));

            for cand in post_candidates {
                if cand.is_file() {
                    ollama_path = Some(cand);
                    break;
                }
            }
        }

        if ollama_path.is_none() {
            return Err("Failed to locate Ollama executable after installation. Please download it from https://ollama.com".to_string());
        }
    }

    // Once ollama.exe exists (found or installed):
    if let Some(ref path) = ollama_path {
        if let Some(ollama_dir) = path.parent() {
            let current_path = std::env::var("PATH").unwrap_or_default();
            std::env::set_var("PATH", format!("{};{}", ollama_dir.display(), current_path));
        }
    }

    // Not running — start it
    eprintln!("🦙 [OLLAMA] Ollama is not running. Starting 'ollama serve' automatically...");

    let ollama_exec = if let Some(ref path) = ollama_path {
        path.to_string_lossy().to_string()
    } else {
        "ollama".to_string()
    };

    // Ensure OLLAMA_ORIGINS=* is active so local browsers/file origins are never rejected with 403 Forbidden
    std::env::set_var("OLLAMA_ORIGINS", "*");

    // Launch ollama serve with OLLAMA_ORIGINS=* and CREATE_NO_WINDOW (0x08000000) only.
    // CRITICAL: Never combine CREATE_NO_WINDOW with DETACHED_PROCESS (0x00000008); Win32 CreateProcessW
    // ignores CREATE_NO_WINDOW when DETACHED_PROCESS is set, causing child llama-server.exe to open a visible console window.
    let mut direct_cmd = create_hidden_command(&ollama_exec);
    direct_cmd.arg("serve");
    direct_cmd.env("OLLAMA_ORIGINS", "*");
    direct_cmd.stdin(std::process::Stdio::null());
    direct_cmd.stdout(std::process::Stdio::null());
    direct_cmd.stderr(std::process::Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        direct_cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
    }
    let start_result = direct_cmd.spawn();

    match start_result {
        Ok(_) => {
            eprintln!("🦙 [OLLAMA] Started 'ollama serve'. Waiting for it to be ready...");
        }
        Err(e) => {
            return Err(format!("Failed to start 'ollama serve': {}. Is Ollama installed?", e));
        }
    }

    // Wait for Ollama to become responsive (up to 30 seconds)
    for i in 0..30 {
        std::thread::sleep(std::time::Duration::from_secs(1));
        if is_ollama_responding(&endpoint) {
            eprintln!("🦙 [OLLAMA] Ollama is ready! (took {}s)", i + 1);
            return Ok(());
        }
        if (i + 1) % 5 == 0 {
            eprintln!("🦙 [OLLAMA] Still waiting... ({}s)", i + 1);
        }
    }

    Err("Ollama failed to start within 30 seconds. Please start it manually with 'ollama serve'.".to_string())
}

/// Forcefully recover and restart Ollama if it is unresponsive, hung, or returning 500.
/// Kills any orphaned or stalled runner/daemon processes and starts a fresh `ollama serve`.
pub fn recover_and_restart_ollama() -> Result<(), String> {
    eprintln!("🦙 [OLLAMA WATCHDOG] 🔄 Initiating deep recovery & restart of Ollama engine...");

    #[cfg(windows)]
    {
        let _ = create_hidden_command("taskkill")
            .args(["/F", "/IM", "ollama.exe", "/IM", "ollama_llama_server.exe", "/T"])
            .output();
        std::thread::sleep(std::time::Duration::from_millis(1000));
    }
    #[cfg(not(windows))]
    {
        let _ = std::process::Command::new("pkill")
            .args(["-9", "-f", "ollama"])
            .output();
        std::thread::sleep(std::time::Duration::from_millis(1000));
    }

    // Now start clean daemon with OLLAMA_ORIGINS=*
    ensure_ollama_running()
}

/// Check if an OpenVINO model is cached/pre-converted on disk.
pub fn is_openvino_model_cached(model_id: &str) -> bool {
    // Build a lowercase search key from just the model name (after the org prefix).
    // e.g. "Qwen/Qwen2.5-7B-Instruct" → "qwen2.5-7b-instruct"
    let safe_name = model_id.split('/').last().unwrap_or(model_id).to_lowercase().replace(' ', "-");

    // Check in local 'ov_models' directory.
    // Matches both:
    //   - Direct naming: "qwen2.5-7b-instruct-ov"  (starts_with safe_name)
    //   - OV Hub naming: "OpenVINO--Qwen2.5-7B-Instruct-int4-ov" (case-insensitive contains)
    let ov_model_dir = std::path::Path::new("ov_models");
    if ov_model_dir.is_dir() {
        if let Ok(entries) = std::fs::read_dir(ov_model_dir) {
            for entry in entries.flatten() {
                if let Ok(name) = entry.file_name().into_string() {
                    let name_lower = name.to_lowercase();
                    let is_match = name_lower.starts_with(&safe_name)
                        || name_lower.contains(&safe_name);
                    if is_match {
                        let path = entry.path();
                        if path.join("openvino_model.xml").exists() || path.join("model.xml").exists() {
                            return true;
                        }
                    }
                }
            }
        }
    }
    
    // Check in system home directory cache (~/.cache/modelfusion_ov/)
    let home = std::env::var("USERPROFILE")
        .or_else(|_| std::env::var("HOME"))
        .ok();
        
    if let Some(home_path) = home {
        let cache_dir = std::path::Path::new(&home_path)
            .join(".cache")
            .join("modelfusion_ov")
            .join(model_id.replace('/', "_"));
            
        if cache_dir.is_dir() {
            if let Ok(devices) = std::fs::read_dir(cache_dir) {
                for device_entry in devices.flatten() {
                    if device_entry.path().join("model.xml").exists() {
                        return true;
                    }
                }
            }
        }
    }
    
    false
}

/// Check if a HuggingFace transformers model is cached/downloaded in the local HF hub cache.
pub fn is_transformers_model_cached(model_id: &str) -> bool {
    let folder_name = format!("models--{}", model_id.replace('/', "--"));

    if let Ok(hf_home) = std::env::var("HF_HOME") {
        let cache_path = std::path::Path::new(&hf_home).join("hub").join(&folder_name);
        if cache_path.is_dir() {
            return true;
        }
    }

    let home = std::env::var("USERPROFILE")
        .or_else(|_| std::env::var("HOME"))
        .ok();
        
    if let Some(home_path) = home {
        let cache_path = std::path::Path::new(&home_path)
            .join(".cache")
            .join("huggingface")
            .join("hub")
            .join(&folder_name);
        
        if cache_path.is_dir() {
            // Check if there are snapshots or lock files indicating complete/partial download
            let snapshots = cache_path.join("snapshots");
            if snapshots.is_dir() {
                if let Ok(mut entries) = std::fs::read_dir(snapshots) {
                    if entries.next().is_some() {
                        return true;
                    }
                }
            }
            return true;
        }
    }
    false
}

fn map_hf_to_ollama(hf_model_id: &str) -> String {
    let id = hf_model_id.to_lowercase();
    if id.contains("qwen2") && id.contains("72b") { "qwen2.5:72b".to_string() }
    else if id.contains("qwen2") && id.contains("32b") { "qwen2.5:32b".to_string() }
    else if id.contains("qwen2") && id.contains("14b") { "qwen2.5:14b".to_string() }
    else if id.contains("qwen2") && id.contains("7b") { "qwen2.5:7b".to_string() }
    else if id.contains("qwen2") && id.contains("3b") { "qwen2.5:3b".to_string() }
    else if id.contains("qwen2") && id.contains("1.5b") { "qwen2.5:1.5b".to_string() }
    else if id.contains("qwen2") && id.contains("0.5b") { "qwen2.5:0.5b".to_string() }
    else if id.contains("llama-3.1") && id.contains("8b") { "llama3.1".to_string() }
    else if id.contains("llama-3.2") && id.contains("3b") { "llama3.2:3b".to_string() }
    else if id.contains("llama-3.2") && id.contains("1b") { "llama3.2:1b".to_string() }
    else if id.contains("deepseek-r1-distill") && id.contains("qwen-1.5b") { "deepseek-r1:1.5b".to_string() }
    else if id.contains("gemma-2") && id.contains("2b") { "gemma2:2b".to_string() }
    else if id.contains("recursivesi/flint") || id == "flint" || id.starts_with("flint:") { "flint:latest".to_string() }
    else if id.contains("glm-4.7-flash") { "glm-4.7-flash:latest".to_string() }
    else if id.contains("glm-4-9b") || id.contains("glm4") || id.contains("glm-4v") || id.contains("glm-4.6v") { "glm4:9b".to_string() }
    else if id.contains("glm-5.3-flash") { "glm-5.3-flash:latest".to_string() }
    else if id.contains("glm-5.3") { "glm-5.3:latest".to_string() }
    else if id.contains("glm-5.2") { "glm-5.2:latest".to_string() }
    else { hf_model_id.to_string() }
}

/// Cached Ollama model list — cached with a short TTL (10s), never permanently caching empty results.
/// This prevents stale empty results if queried before Ollama was ready.
static OLLAMA_CACHED_TAGS: std::sync::RwLock<Option<(std::time::Instant, Vec<String>)>> = std::sync::RwLock::new(None);

pub fn get_ollama_cached_models() -> Vec<String> {
    if let Ok(guard) = OLLAMA_CACHED_TAGS.read() {
        if let Some((instant, tags)) = guard.as_ref() {
            if !tags.is_empty() && instant.elapsed().as_secs() < 10 {
                return tags.clone();
            }
        }
    }

    let endpoint = std::env::var("LOCAL_OLLAMA_ENDPOINT")
        .unwrap_or_else(|_| "http://127.0.0.1:11434".to_string());
    let tags_url = format!("{}/api/tags", endpoint.trim_end_matches('/'));

    let mut fetched_tags: Vec<String> = Vec::new();

    // 1. Try reqwest::blocking inside a dedicated thread so it never conflicts with an async Tokio runtime
    let tags_url_clone = tags_url.clone();
    if let Ok(thread_tags) = std::thread::spawn(move || -> Vec<String> {
        if let Ok(client) = reqwest::blocking::Client::builder()
            .no_proxy()
            .timeout(std::time::Duration::from_millis(1500))
            .build()
        {
            if let Ok(res) = client.get(&tags_url_clone).send() {
                if res.status().is_success() {
                    if let Ok(json) = res.json::<serde_json::Value>() {
                        if let Some(models) = json["models"].as_array() {
                            return models
                                .iter()
                                .filter_map(|m| m["name"].as_str().map(|s| s.to_lowercase()))
                                .collect();
                        }
                    }
                }
            }
        }
        Vec::new()
    }).join() {
        fetched_tags = thread_tags;
    }

    // 2. Fallback to curl with proxy bypass and timeout if reqwest was empty
    if fetched_tags.is_empty() {
        let result = create_hidden_command("curl")
            .args(["-s", "--noproxy", "*", "--max-time", "2", &tags_url])
            .output();

        if let Ok(o) = result {
            if o.status.success() {
                let stdout_str = String::from_utf8_lossy(&o.stdout);
                if let Ok(json) = serde_json::from_str::<serde_json::Value>(&stdout_str) {
                    if let Some(models) = json["models"].as_array() {
                        fetched_tags = models
                            .iter()
                            .filter_map(|m| m["name"].as_str().map(|s| s.to_lowercase()))
                            .collect();
                    }
                }
            }
        }
    }

    // 3. Fallback to `ollama list` CLI if HTTP endpoints did not return models
    if fetched_tags.is_empty() {
        if let Ok(o) = create_hidden_command("ollama").args(["list"]).output() {
            if o.status.success() {
                let stdout_str = String::from_utf8_lossy(&o.stdout);
                for line in stdout_str.lines().skip(1) {
                    if let Some(name) = line.split_whitespace().next() {
                        if !name.trim().is_empty() {
                            fetched_tags.push(name.to_lowercase());
                        }
                    }
                }
            }
        }
    }

    // Only cache if non-empty
    if !fetched_tags.is_empty() {
        if let Ok(mut guard) = OLLAMA_CACHED_TAGS.write() {
            *guard = Some((std::time::Instant::now(), fetched_tags.clone()));
        }
    }

    fetched_tags
}

pub fn is_ollama_model_cached(model_id: &str) -> bool {
    let target = map_hf_to_ollama(model_id).to_lowercase();
    let cached = get_ollama_cached_models();
    let (target_base, target_tag) = if let Some((base, tag)) = target.split_once(':') {
        (base, Some(tag))
    } else {
        (target.as_str(), None)
    };

    cached.iter().any(|m| {
        let m_lower = m.to_lowercase();
        if m_lower == target {
            return true;
        }
        if let Some((m_base, m_tag)) = m_lower.split_once(':') {
            if m_base == target_base {
                match target_tag {
                    Some(tt) => m_tag == tt || m_tag.starts_with(tt),
                    None => true,
                }
            } else {
                false
            }
        } else {
            m_lower == target_base
        }
    })
}

/// Ensure FFmpeg is available on the system.
/// Auto-discovers FFmpeg across PATH, standard paths, WinGet packages, local bundle paths,
/// or automatically installs it silently if missing.
pub fn ensure_ffmpeg_available() -> Result<std::path::PathBuf, String> {
    // 1. Probe PATH via `where` on Windows or `which` on Unix
    #[cfg(windows)]
    let check_cmd = "where";
    #[cfg(not(windows))]
    let check_cmd = "which";

    if let Ok(output) = create_hidden_command(check_cmd).arg("ffmpeg").output() {
        if output.status.success() {
            let stdout = String::from_utf8_lossy(&output.stdout);
            for line in stdout.lines() {
                let p = std::path::PathBuf::from(line.trim());
                if p.is_file() {
                    return Ok(p);
                }
            }
        }
    }

    // 2. Check candidate filesystem paths
    let mut candidates = Vec::new();
    if let Ok(curr_exe) = std::env::current_exe() {
        if let Some(parent) = curr_exe.parent() {
            candidates.push(parent.join("ffmpeg.exe"));
            candidates.push(parent.join("ffmpeg"));
        }
    }
    candidates.push(std::path::PathBuf::from("IDE/bin/ffmpeg.exe"));
    candidates.push(std::path::PathBuf::from("browser/bin/ffmpeg.exe"));
    candidates.push(std::path::PathBuf::from("IDE/bin/ffmpeg"));
    candidates.push(std::path::PathBuf::from("browser/bin/ffmpeg"));

    if let Ok(local_app_data) = std::env::var("LOCALAPPDATA") {
        let lad = std::path::PathBuf::from(&local_app_data);
        candidates.push(lad.join("ModelFusion").join("bin").join("ffmpeg.exe"));
        candidates.push(lad.join("ffmpeg").join("bin").join("ffmpeg.exe"));
        candidates.push(lad.join("Programs").join("ffmpeg").join("bin").join("ffmpeg.exe"));
        candidates.push(lad.join("Microsoft").join("WinGet").join("Links").join("ffmpeg.exe"));

        // Scan WinGet package directories
        let winget_pkg_dir = lad.join("Microsoft").join("WinGet").join("Packages");
        if winget_pkg_dir.is_dir() {
            if let Ok(entries) = std::fs::read_dir(&winget_pkg_dir) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    let name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
                    if name.contains("FFmpeg") {
                        if let Ok(subentries) = std::fs::read_dir(&path) {
                            for sub in subentries.flatten() {
                                let sub_path = sub.path();
                                candidates.push(sub_path.join("bin").join("ffmpeg.exe"));
                                candidates.push(sub_path.join("ffmpeg.exe"));
                            }
                        }
                    }
                }
            }
        }
    }

    if let Ok(prog_files) = std::env::var("ProgramFiles") {
        let pf = std::path::PathBuf::from(&prog_files);
        candidates.push(pf.join("ffmpeg").join("bin").join("ffmpeg.exe"));
        candidates.push(pf.join("FFmpeg").join("bin").join("ffmpeg.exe"));
    }
    candidates.push(std::path::PathBuf::from(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"));

    for cand in &candidates {
        if cand.is_file() {
            // Found existing binary! Inject directory into current process PATH
            if let Some(parent) = cand.parent() {
                let current_path = std::env::var("PATH").unwrap_or_default();
                std::env::set_var("PATH", format!("{};{}", parent.display(), current_path));
            }
            return Ok(cand.clone());
        }
    }

    // 3. If not found on Windows, attempt silent auto-installation
    #[cfg(windows)]
    {
        eprintln!("🎬 [FFMPEG] FFmpeg not found. Attempting automated silent installation...");
        let winget_res = create_hidden_command("winget")
            .args([
                "install",
                "--id",
                "Gyan.FFmpeg",
                "--accept-package-agreements",
                "--accept-source-agreements",
                "--silent",
                "--disable-interactivity",
            ])
            .status();

        if let Ok(st) = winget_res {
            if st.success() {
                eprintln!("🎬 [FFMPEG] WinGet installation succeeded. Re-scanning candidates...");
            }
        }

        // Re-check after WinGet
        for cand in &candidates {
            if cand.is_file() {
                if let Some(parent) = cand.parent() {
                    let current_path = std::env::var("PATH").unwrap_or_default();
                    std::env::set_var("PATH", format!("{};{}", parent.display(), current_path));
                }
                return Ok(cand.clone());
            }
        }

        // 4. Fallback direct download and extraction
        let temp_dir = std::env::temp_dir();
        let zip_path = temp_dir.join("ffmpeg-essentials.zip");
        let extract_dir = temp_dir.join("ffmpeg_extract");
        let target_dir = std::env::var("LOCALAPPDATA")
            .map(|l| std::path::PathBuf::from(l).join("ModelFusion").join("bin"))
            .unwrap_or_else(|_| std::path::PathBuf::from("IDE/bin"));
        let target_ffmpeg = target_dir.join("ffmpeg.exe");

        let client = reqwest::blocking::Client::builder()
            .timeout(std::time::Duration::from_secs(180))
            .build()
            .unwrap_or_default();

        if let Ok(mut r) = client.get("https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip").send() {
            if r.status().is_success() {
                if let Ok(mut f) = std::fs::File::create(&zip_path) {
                    if std::io::copy(&mut r, &mut f).is_ok() {
                        let _ = std::fs::create_dir_all(&extract_dir);
                        let ps_cmd = format!(
                            "Expand-Archive -Path '{}' -DestinationPath '{}' -Force",
                            zip_path.display(),
                            extract_dir.display()
                        );
                        let _ = create_hidden_command("powershell")
                            .args(["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", &ps_cmd])
                            .status();

                        // Find extracted ffmpeg.exe
                        if let Ok(entries) = std::fs::read_dir(&extract_dir) {
                            for ent in entries.flatten() {
                                let cand = ent.path().join("bin").join("ffmpeg.exe");
                                if cand.is_file() {
                                    let _ = std::fs::create_dir_all(&target_dir);
                                    let _ = std::fs::copy(&cand, &target_ffmpeg);
                                    let current_path = std::env::var("PATH").unwrap_or_default();
                                    std::env::set_var("PATH", format!("{};{}", target_dir.display(), current_path));
                                    return Ok(target_ffmpeg);
                                }
                            }
                        }
                    }
                }
            }
        }

        if target_ffmpeg.is_file() {
            return Ok(target_ffmpeg);
        }
    }

    Err("FFmpeg executable could not be found or installed. Please install FFmpeg (winget install Gyan.FFmpeg)".to_string())
}

/// Check if FFmpeg is available.
pub fn is_ffmpeg_available() -> bool {
    ensure_ffmpeg_available().is_ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::SelectionStrategy;

    #[test]
    fn test_param_extraction() {
        assert_eq!(estimate_params_billions("Qwen/Qwen2.5-7B-Instruct"), Some(7.0));
        assert_eq!(estimate_params_billions("meta-llama/Llama-3.1-8B-Instruct"), Some(8.0));
        assert_eq!(estimate_params_billions("Qwen/Qwen2.5-1.5B-Instruct"), Some(1.5));
        assert_eq!(estimate_params_billions("meta-llama/Llama-3.2-1B-Instruct"), Some(1.0));
        assert_eq!(estimate_params_billions("deepseek-ai/DeepSeek-R1"), Some(671.0));
        assert_eq!(estimate_params_billions("deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"), Some(1.5));
        assert_eq!(estimate_params_billions("facebook/opt-125m"), Some(0.125));
        assert_eq!(estimate_params_billions("Qwen/Qwen3-0.6B"), Some(0.6));
    }

    #[test]
    fn test_transformers_cache() {
        assert!(!is_transformers_model_cached("nonexistent-test/definitely-not-cached-model-xyz"));
        let is_cached = is_transformers_model_cached("Qwen/Qwen2.5-1.5B-Instruct")
            || is_transformers_model_cached("HuggingFaceTB/SmolLM2-135M-Instruct")
            || is_transformers_model_cached("apple/OpenELM-1_1B-Instruct");
        println!("Test model cached: {}", is_cached);
        assert!(is_cached);
    }

    #[test]
    fn test_print_model_scores() {
        let db_candidates = [
            "IDE/db/hf_models.db",
            "db/hf_models.db",
            "../../IDE/db/hf_models.db",
            "../../db/hf_models.db",
        ];
        let db_path = match db_candidates.iter().find(|p| std::path::Path::new(p).exists()) {
            Some(p) => *p,
            None => return,
        };
        let selector = match crate::EnhancedModelSelector::new(db_path) {
            Ok(s) => s,
            Err(_) => return,
        };
        let res = match selector.select_best_model("text-generation", "compare python vs rust", SelectionStrategy::MultiObjective, 10, None) {
            Ok(r) => r,
            Err(_) => return,
        };
        println!("Best model: {}", res.best_model.model_id);
        for (idx, candidate) in res.all_candidates.iter().enumerate() {
            println!(
                "{}. {} - Final Score: {:.4} (params: {:.2}B, cached: {})",
                idx + 1,
                candidate.model_id,
                candidate.final_score,
                candidate.estimated_params_b,
                is_transformers_model_cached(&candidate.model_id)
            );
        }
    }
    #[test]
    fn test_param_extraction_additional() {
        assert_eq!(estimate_params_billions("zai-org/GLM-4.7-Flash"), Some(30.0));
        assert_eq!(estimate_params_billions("zai-org/GLM-5-FP8"), Some(744.0));
        assert_eq!(estimate_params_billions("zai-org/GLM-5.2"), Some(744.0));
    }

    #[test]
    fn test_memory_estimation() {
        // 7B model, Transformers FP16: 7 × 2 × 1.2 = 16.8 GB
        let mem = estimate_runtime_memory_gb(7.0, Backend::Transformers);
        assert!((mem - 16.8).abs() < 0.01);

        // 7B model, Ollama Q4: 7 × 0.6 × 1.2 = 5.04 GB
        let mem = estimate_runtime_memory_gb(7.0, Backend::Ollama);
        assert!((mem - 5.04).abs() < 0.01);
    }

    #[test]
    fn test_derive_fusion_model_count_tiers() {
        let mem_64 = SystemMemory {
            total_ram_gb: 128.0,
            free_ram_gb: 64.0,
            cpu_cores: 16,
            gpu_name: None,
            gpu_vram_total_gb: 0.0,
            gpu_vram_free_gb: 0.0,
        };
        assert_eq!(mem_64.derive_fusion_model_count(), 7);

        let mem_32 = SystemMemory {
            total_ram_gb: 64.0,
            free_ram_gb: 32.0,
            cpu_cores: 16,
            gpu_name: None,
            gpu_vram_total_gb: 0.0,
            gpu_vram_free_gb: 0.0,
        };
        assert_eq!(mem_32.derive_fusion_model_count(), 5);

        let mem_16 = SystemMemory {
            total_ram_gb: 32.0,
            free_ram_gb: 16.0,
            cpu_cores: 8,
            gpu_name: None,
            gpu_vram_total_gb: 0.0,
            gpu_vram_free_gb: 0.0,
        };
        assert_eq!(mem_16.derive_fusion_model_count(), 4);

        let mem_8 = SystemMemory {
            total_ram_gb: 16.0,
            free_ram_gb: 8.0,
            cpu_cores: 4,
            gpu_name: None,
            gpu_vram_total_gb: 0.0,
            gpu_vram_free_gb: 0.0,
        };
        assert_eq!(mem_8.derive_fusion_model_count(), 3);

        let mem_4 = SystemMemory {
            total_ram_gb: 8.0,
            free_ram_gb: 4.0,
            cpu_cores: 2,
            gpu_name: None,
            gpu_vram_total_gb: 0.0,
            gpu_vram_free_gb: 0.0,
        };
        assert_eq!(mem_4.derive_fusion_model_count(), 2);
    }

    #[test]
    fn test_flint_parameters_and_active_moe() {
        assert_eq!(estimate_params_billions("RecursiveSI/flint"), Some(40.0));
        assert_eq!(estimate_params_billions("flint"), Some(40.0));
        assert_eq!(estimate_params_billions("flint:latest"), Some(40.0));
        assert_eq!(estimate_params_billions("flint-40b"), Some(40.0));
        assert_eq!(estimate_active_params_billions("RecursiveSI/flint"), Some(2.5));
        assert_eq!(estimate_active_params_billions("flint"), Some(2.5));
        assert_eq!(estimate_active_params_billions("Qwen/Qwen2.5-7B-Instruct"), Some(7.0));
        assert_eq!(map_hf_to_ollama("RecursiveSI/flint"), "flint:latest");
    }

    #[test]
    fn test_flint_dual_gate_law() {
        let mem_high = SystemMemory {
            total_ram_gb: 64.0,
            free_ram_gb: 32.0,
            cpu_cores: 16,
            gpu_name: None,
            gpu_vram_total_gb: 0.0,
            gpu_vram_free_gb: 0.0,
        };
        // 1. Coding task + Fusion mode + High resources -> Flint active in fusion with flint:latest default
        let eval_coding = mem_high.assess_flint_for_task(true, true);
        assert!(eval_coding.resources_available);
        assert!(eval_coding.flint_activated_in_fusion);
        assert_eq!(eval_coding.coding_fusion_panel[0], "flint:latest");
        assert!(eval_coding.coding_fusion_panel.contains(&"RecursiveSI/flint".to_string()));

        // 2. Low resources -> Flint still active by default, unblocked
        let mem_low = SystemMemory {
            total_ram_gb: 16.0,
            free_ram_gb: 8.0,
            cpu_cores: 4,
            gpu_name: None,
            gpu_vram_total_gb: 0.0,
            gpu_vram_free_gb: 0.0,
        };
        let eval_low = mem_low.assess_flint_for_task(true, true);
        assert!(eval_low.flint_activated_in_fusion);
        assert_eq!(eval_low.coding_fusion_panel[0], "flint:latest");
    }

    #[test]
    fn test_glm_resource_gated_fusion_calibration() {
        // 1. Insufficient runtime memory (< 6 GB VRAM & < 8 GB Free RAM): GLM must NOT activate in fusion
        let mem_insufficient = SystemMemory {
            total_ram_gb: 64.0,
            free_ram_gb: 4.5,
            cpu_cores: 8,
            gpu_name: Some("Busy GPU".to_string()),
            gpu_vram_total_gb: 8.0,
            gpu_vram_free_gb: 2.0,
        };
        let eval_off = mem_insufficient.assess_glm_for_fusion();
        assert!(!eval_off.resources_available);
        assert!(!eval_off.glm_activated_in_fusion);

        // 2. 8-16 GB tier: GLM-4 9B active
        let mem_8_16 = SystemMemory {
            total_ram_gb: 16.0,
            free_ram_gb: 10.0,
            cpu_cores: 8,
            gpu_name: Some("RTX 4060".to_string()),
            gpu_vram_total_gb: 8.0,
            gpu_vram_free_gb: 6.5,
        };
        let eval_9b = mem_8_16.assess_glm_for_fusion();
        assert!(eval_9b.resources_available);
        assert!(eval_9b.glm_activated_in_fusion);
        assert_eq!(eval_9b.vram_sweet_spot_tag.as_deref(), Some("glm4:9b"));

        // 3. 24 GB VRAM tier: GLM-4.7-Flash Q4_K_M active
        let mem_24vram = SystemMemory {
            total_ram_gb: 32.0,
            free_ram_gb: 24.0,
            cpu_cores: 16,
            gpu_name: Some("RTX 4090".to_string()),
            gpu_vram_total_gb: 24.0,
            gpu_vram_free_gb: 22.0,
        };
        let eval_47flash = mem_24vram.assess_glm_for_fusion();
        assert!(eval_47flash.resources_available);
        assert!(eval_47flash.glm_activated_in_fusion);
        assert_eq!(
            eval_47flash.vram_sweet_spot_tag.as_deref(),
            Some("glm-4.7-flash:q4_K_M")
        );
        assert_eq!(eval_47flash.total_params_b, 30.0);
        assert_eq!(eval_47flash.active_params_b, 3.6);

        // 4. Workstation 128 GB+ tier (Dell Precision 7920 Tower profile: ~176 GB Free RAM + 6.6 GB Free VRAM)
        let mem_workstation = SystemMemory {
            total_ram_gb: 223.65,
            free_ram_gb: 176.4,
            cpu_cores: 36,
            gpu_name: Some("Quadro RTX 4000".to_string()),
            gpu_vram_total_gb: 8.0,
            gpu_vram_free_gb: 6.6,
        };
        let eval_ws = mem_workstation.assess_glm_for_fusion();
        assert!(eval_ws.resources_available);
        assert!(eval_ws.glm_activated_in_fusion);
        assert_eq!(eval_ws.vram_sweet_spot_tag.as_deref(), Some("glm4:9b"));
        assert_eq!(
            eval_ws.moe_offload_tag.as_deref(),
            Some("glm-4.7-flash:q8_0")
        );
        assert!(eval_ws
            .workstation_flagship_build
            .as_deref()
            .unwrap_or("")
            .contains("GLM-4.7"));
    }

}
