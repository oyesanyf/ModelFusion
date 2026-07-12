//! Multi-objective model selection.
//!
//! Evaluates and selects the best model for a given task using multi-objective scoring,
//! and supports different selection strategies.

pub mod memory;

use anyhow::Result;
use chrono::{DateTime, Utc};
use db::{HuggingFaceModelDatabase, ModelMetrics};
use serde::{Deserialize, Serialize};
use std::path::Path;

use memory::{SystemMemory, Backend, estimate_params_billions, estimate_runtime_memory_gb};

/// Different model selection strategies.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum SelectionStrategy {
    MultiObjective,
    CrossValidation,
    EnsembleMethods,
    HyperparameterTuning,
    BayesianOptimization,
    MetaLearning,
}

impl std::fmt::Display for SelectionStrategy {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let name = match self {
            Self::MultiObjective => "Multi-Objective Optimization",
            Self::CrossValidation => "Cross-Validation",
            Self::EnsembleMethods => "Ensemble Methods",
            Self::HyperparameterTuning => "Hyperparameter Tuning",
            Self::BayesianOptimization => "Bayesian Optimization",
            Self::MetaLearning => "Meta-Learning",
        };
        write!(f, "{}", name)
    }
}

/// Represents a model candidate with computed weights and evaluation scores.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelCandidate {
    pub model_id: String,
    pub downloads: i64,
    pub likes: i64,
    pub decision_score: f64,
    pub capability_score: f64,
    pub efficiency_score: f64,
    pub popularity_score: f64,
    pub size_mb: f64,
    pub license: String,
    pub freshness_score: f64,
    pub final_score: f64,
    pub confidence_score: f64,
    pub estimated_params_b: f64,
    pub estimated_memory_gb: f64,
}

/// Result of model selection.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SelectionResult {
    pub best_model: ModelCandidate,
    pub all_candidates: Vec<ModelCandidate>,
    pub strategy: SelectionStrategy,
    pub optimization_time_ms: u64,
    pub confidence_score: f64,
    pub reasoning: String,
}

/// Advanced selector using multi-objective criteria.
pub struct EnhancedModelSelector {
    db: HuggingFaceModelDatabase,
    open_licenses: Vec<String>,
}

impl EnhancedModelSelector {
    /// Create a new selector using the provided database path.
    pub fn new(db_path: impl AsRef<Path>) -> Result<Self> {
        let db = HuggingFaceModelDatabase::new(db_path)?;
        let open_licenses = vec![
            "apache-2.0".to_string(),
            "mit".to_string(),
            "cc-by-4.0".to_string(),
            "cc0-1.0".to_string(),
            "openrail".to_string(),
            "openrail++".to_string(),
            "bsd-3-clause".to_string(),
            "gpl-3.0".to_string(),
            "lgpl-3.0".to_string(),
            "cc-by-sa-4.0".to_string(),
            "unlicense".to_string(),
        ];
        Ok(Self { db, open_licenses })
    }

    /// Select the best model for a task based on the strategy.
    pub fn select_best_model(
        &self,
        task_name: &str,
        prompt: &str,
        strategy: SelectionStrategy,
        max_candidates: usize,
        max_model_params_b: Option<f64>,
    ) -> Result<SelectionResult> {
        let start_time = std::time::Instant::now();
        log::info!(
            "Selecting model for task '{}' using strategy: {:?}",
            task_name,
            strategy
        );

        // Map task name to database tags
        let pipeline_tag = self.map_task_to_tag(task_name);
        
        // Load candidates from the DB (load a larger set to allow filtering)
        let db_models = self.db.get_by_task(&pipeline_tag, 100)?;

        if db_models.is_empty() {
            anyhow::bail!("No models found in database for pipeline tag: {}", pipeline_tag);
        }

        let has_token = std::env::var("HF_TOKEN").is_ok()
            || std::env::var("HUGGINGFACE_API_KEY").is_ok()
            || std::env::var("HF_API_KEY").is_ok()
            || std::env::var("HUGGINGFACE_TOKEN").is_ok();

        let no_simulation = std::env::var("MODELFUSION_NO_SIMULATION").is_ok()
            || std::env::var("MODELFUSION_USE_TRANSFORMERS").is_ok()
            || std::env::var("MODELFUSION_USE_OPENVINO").is_ok()
            || std::env::var("MODELFUSION_USE_OLLAMA").is_ok()
            || has_token;

        let mut filtered_models = Vec::new();
        for m in db_models {
            if no_simulation && is_fictional_or_non_chat(&m.model_id) {
                continue;
            }
            // Filter by user budget (model size limit)
            if let Some(max_params) = max_model_params_b {
                let est = estimate_params_billions(&m.model_id).unwrap_or(0.0);
                if est > 0.0 && est > max_params + 1.0 {
                    // Allow +1B slack (e.g. budget=1 allows up to 2B models)
                    continue;
                }
            }
            filtered_models.push(m);
        }

        if filtered_models.is_empty() {
            anyhow::bail!("No real chat models found in database for task '{}' after filtering.", task_name);
        }

        // Calculate max downloads & likes for normalization
        let max_downloads = filtered_models.iter().map(|m| m.downloads).max().unwrap_or(1) as f64;
        let max_likes = filtered_models.iter().map(|m| m.likes).max().unwrap_or(1) as f64;

        let mut candidates = Vec::new();
        for m in &filtered_models {
            let freshness = self.calculate_freshness(m);
            let license_val = self.evaluate_license(m);

            let mut backend = if std::env::var("MODELFUSION_USE_OLLAMA").is_ok() || memory::is_ollama_model_cached(&m.model_id) {
                Backend::Ollama
            } else if std::env::var("MODELFUSION_USE_OPENVINO").is_ok() {
                Backend::OpenVINO
            } else {
                Backend::Transformers
            };

            // If using OpenVINO, but the model has not been pre-converted/cached yet,
            // we must budget for the heavy conversion step (which loads the full PyTorch model).
            let is_openvino = backend == Backend::OpenVINO;
            let is_cached = is_openvino && memory::is_openvino_model_cached(&m.model_id);
            if is_openvino && !is_cached {
                backend = Backend::Transformers;
            }

            // Weights for multi-objective scoring
            // downloads (0.3) + likes (0.2) + decision_score (0.2) + freshness (0.1) + license (0.1) + efficiency (0.1)
            let downloads_norm = if max_downloads > 0.0 { m.downloads as f64 / max_downloads } else { 0.0 };
            let likes_norm = if max_likes > 0.0 { m.likes as f64 / max_likes } else { 0.0 };
            
            // Stored on a 0.0 to 1.0 scale in the database, clamp to be safe
            let decision_norm = m.decision_score.clamp(0.0, 1.0);
            
            // Efficiency (prefer smaller models, but penalize tiny dummy models)
            let efficiency_val = if m.size_mb > 0.0 {
                // Decay score for very large models: e.g., score = 1 / (1 + size_gb)
                1.0 / (1.0 + (m.size_mb / 1000.0))
            } else {
                0.5 // Default neutral score
            };

            let mut final_score = downloads_norm * 0.3
                + likes_norm * 0.2
                + decision_norm * 0.2
                + freshness * 0.1
                + license_val * 0.1
                + efficiency_val * 0.1;

            // Apply strategy variations/stubs
            match strategy {
                SelectionStrategy::CrossValidation => {
                    // Slight variation based on meta evaluation
                    final_score += 0.02 * m.capability_score.clamp(0.0, 1.0);
                }
                SelectionStrategy::HyperparameterTuning => {
                    // Optimization stub variation
                    final_score += 0.01 * m.efficiency_score.clamp(0.0, 1.0);
                }
                SelectionStrategy::EnsembleMethods => {
                    // Combine decision + capability + popularity
                    final_score = (final_score + m.popularity_score.clamp(0.0, 1.0)) / 2.0;
                }
                SelectionStrategy::BayesianOptimization => {
                    final_score *= 1.02; // BO scalar boost stub
                }
                SelectionStrategy::MetaLearning => {
                    // Feature similarity mock modifier
                    if prompt.contains("code") && m.library_name.contains("transformers") {
                        final_score += 0.05;
                    }
                }
                SelectionStrategy::MultiObjective => {
                    // Sophisticated multi-objective optimization:
                    // Competing objectives: Accuracy vs Latency vs Memory constraints.
                    // Calculate capability/accuracy reward:
                    let accuracy_obj = m.capability_score.clamp(0.0, 1.0);
                    
                    // Calculate latency/speed reward:
                    let speed_obj = m.efficiency_score.clamp(0.0, 1.0);
                    
                    // Calculate memory compliance safety reward:
                    let memory = memory::SystemMemory::detect();
                    let estimated_params_b = estimate_params_billions(&m.model_id).unwrap_or(7.0);
                    let runtime_mem = estimate_runtime_memory_gb(estimated_params_b, backend);
                    let memory_obj = if runtime_mem <= memory.gpu_budget_gb() {
                        1.0 // High compliance (runs fully on fast GPU)
                    } else if runtime_mem <= memory.ram_budget_gb() {
                        0.5 // Medium compliance (runs on CPU)
                    } else {
                        0.1 // Low compliance (potential paging/thrashing)
                    };
                    
                    // Scalar weighting: 40% Accuracy, 30% Speed, 30% Memory Safety
                    final_score = accuracy_obj * 0.4 + speed_obj * 0.3 + memory_obj * 0.3;
                }
            }

            // Promote models cached in Ollama to ensure instant local response
            if memory::is_ollama_model_cached(&m.model_id) {
                final_score += 10.0;
            }

            let confidence = (final_score * 1.2).clamp(0.1, 1.0);

            let estimated_params_b = estimate_params_billions(&m.model_id).unwrap_or(0.0);

            // OpenVINO-aware scoring adjustment:
            // On first run, uncached models must be downloaded + converted (slow).
            // Strongly prefer ≤3B models which convert in ~2 min vs. ~15 min for 7B+.
            // Once cached, restore full scoring — conversion cost is already paid.
            if is_openvino {
                if is_cached {
                    // Cached model: small bonus to keep it ranked above uncached equivalents
                    final_score = (final_score + 0.15).min(1.0);
                } else if estimated_params_b > 3.0 {
                    // Uncached large model: heavy penalty — download+convert would take 10-15+ min
                    final_score = (final_score - 0.4).max(0.0);
                    log::debug!(
                        "[OPENVINO] Penalising uncached {:.1}B model '{}' (score {:.2} → {:.2})",
                        estimated_params_b, m.model_id, final_score + 0.4, final_score
                    );
                }
                // ≤3B uncached: no penalty — they convert fast (~2 min), keep normal score
            }

            let is_local = std::env::var("MODELFUSION_USE_TRANSFORMERS").is_ok()
                || std::env::var("MODELFUSION_USE_OPENVINO").is_ok()
                || std::env::var("MODELFUSION_USE_OLLAMA").is_ok()
                || std::env::var("MODELFUSION_USE_ONNX").is_ok();

            // Local Transformers cache-aware scoring:
            // If the model is already downloaded in local HuggingFace cache, prioritize it.
            // If not, penalize it to avoid unnecessary slow model downloads.
            let is_transformers = backend == Backend::Transformers;
            if is_local && is_transformers {
                let is_tf_cached = memory::is_transformers_model_cached(&m.model_id);
                if is_tf_cached {
                    // Boost cached models to keep them on top of uncached ones
                    final_score = (final_score + 0.35).min(1.0);
                    log::debug!("[TRANSFORMERS] Boosting cached model '{}' (score +0.35)", m.model_id);
                } else {
                    // Penalize uncached models to avoid downloading on slow connections
                    final_score = (final_score - 0.45).max(0.0);
                    log::debug!(
                        "[TRANSFORMERS] Penalising uncached model '{}' (score {:.2} → {:.2})",
                        m.model_id, final_score + 0.45, final_score
                    );
                }
            }


            // Hardware suitability scoring adjustment:
            let suitability = if is_local {
                let sys_mem = SystemMemory::detect();
                memory::evaluate_hardware_suitability(
                    estimated_params_b,
                    backend,
                    &sys_mem,
                )
            } else {
                memory::SuitabilityResult::Adequate
            };

            // Filter out models that do not meet minimum requirements immediately
            if is_local && suitability == memory::SuitabilityResult::Inadequate {
                log::debug!("Skipping candidate '{}' due to inadequate hardware resources", m.model_id);
                continue;
            }

            // Apply suitability boosts and penalties
            if suitability == memory::SuitabilityResult::Adequate {
                final_score = (final_score + 0.15).min(1.0);
            } else if suitability == memory::SuitabilityResult::Minimum {
                final_score = (final_score - 0.20).max(0.0);
            }

            let estimated_memory_gb = if estimated_params_b > 0.0 {
                estimate_runtime_memory_gb(estimated_params_b, backend)
            } else {
                0.0
            };

            candidates.push(ModelCandidate {
                model_id: m.model_id.clone(),
                downloads: m.downloads,
                likes: m.likes,
                decision_score: m.decision_score,
                capability_score: m.capability_score,
                efficiency_score: m.efficiency_score,
                popularity_score: m.popularity_score,
                size_mb: m.size_mb,
                license: m.license.clone(),
                freshness_score: freshness,
                final_score,
                confidence_score: confidence,
                estimated_params_b,
                estimated_memory_gb,
            });
        }

        // Sort candidates by final score descending
        candidates.sort_by(|a, b| b.final_score.partial_cmp(&a.final_score).unwrap());

        // When using Ollama, only keep models that have known Ollama equivalents
        if std::env::var("MODELFUSION_USE_OLLAMA").is_ok() {
            let ollama_models: &[&str] = &[
                "Qwen2.5-7B-Instruct", "Qwen2.5-3B-Instruct", "Qwen2.5-1.5B-Instruct",
                "Qwen2.5-0.5B-Instruct", "Qwen2.5-14B-Instruct", "Qwen2.5-Coder-7B-Instruct",
                "Qwen3-8B", "Qwen3-4B", "Qwen3-1.7B",
                "Llama-3.1-8B-Instruct", "Llama-3.2-3B-Instruct", "Llama-3.2-1B-Instruct",
                "DeepSeek-R1-Distill-Qwen-1.5B", "DeepSeek-R1-Distill-Qwen-7B",
                "DeepSeek-R1-Distill-Qwen-14B", "DeepSeek-R1-Distill-Qwen-32B",
                "DeepSeek-R1-Distill-Llama-8B",
                "gemma-2-2b-it", "gemma-2-9b-it", "gemma-3-4b-it", "gemma-3-12b-it",
                "Phi-3-mini-4k-instruct", "Phi-4-mini-instruct",
                "Mistral-7B-Instruct", "Mixtral-8x7B-Instruct",
            ];
            candidates.retain(|c| ollama_models.iter().any(|m| c.model_id.contains(m)));
        }

        let is_local = std::env::var("MODELFUSION_USE_TRANSFORMERS").is_ok()
            || std::env::var("MODELFUSION_USE_OPENVINO").is_ok()
            || std::env::var("MODELFUSION_USE_OLLAMA").is_ok()
            || std::env::var("MODELFUSION_USE_ONNX").is_ok();

        let verbose = std::env::var("MODELFUSION_VERBOSE").is_ok();
        if is_local {
            // Dynamic memory-aware filtering: detect system resources and exclude models that won't fit
            let sys_mem = SystemMemory::detect();
            if verbose {
                sys_mem.print_summary();
            }
            let budget = sys_mem.model_budget_gb();

            let before_count = candidates.len();
            candidates.retain(|c| {
                let suitability = memory::evaluate_hardware_suitability(
                    c.estimated_params_b,
                    if std::env::var("MODELFUSION_USE_OLLAMA").is_ok() || memory::is_ollama_model_cached(&c.model_id) { Backend::Ollama } else if std::env::var("MODELFUSION_USE_OPENVINO").is_ok() { Backend::OpenVINO } else { Backend::Transformers },
                    &sys_mem,
                );
                
                if suitability == memory::SuitabilityResult::Inadequate {
                    if verbose {
                        println!("  ❌ {} ({:.1}B params) — SKIPPED (Inadequate hardware)", c.model_id, c.estimated_params_b);
                    }
                    false
                } else {
                    let device = sys_mem.best_device_for_model(c.estimated_memory_gb);
                    let device_icon = if device == memory::Device::Gpu { "🎮 GPU" } else { "💻 CPU" };
                    let suitability_str = if suitability == memory::SuitabilityResult::Adequate { "Adequate" } else { "Minimum specs" };
                    if verbose {
                        println!("  ✅ {} ({:.1}B params, ~{:.1} GB) — {} [Suitability: {}]",
                            c.model_id, c.estimated_params_b, c.estimated_memory_gb, device_icon, suitability_str);
                    }
                    true
                }
            });
            if verbose && candidates.len() < before_count {
                println!("📋 [HARDWARE] Filtered: {} → {} models fit system requirements",
                    before_count, candidates.len());
            }

            if candidates.is_empty() {
                anyhow::bail!("No models fit within available system memory ({:.1} GB). Try closing other applications to free RAM.", budget);
            }
        } else {
            // Cloud execution: print candidate list cleanly without local hardware filters
            if verbose {
                println!("🌐 [CLOUD] Cloud Model Candidates:");
                for c in &candidates {
                    println!("  ✅ {} ({:.1}B params) — Remote Serverless Inference", c.model_id, c.estimated_params_b);
                }
            }
        }

        if candidates.len() > max_candidates {
            candidates.truncate(max_candidates);
        }

        let best_model = candidates[0].clone();
        let optimization_time_ms = start_time.elapsed().as_millis() as u64;

        let reasoning = format!(
            "Selected '{}' because it ranked highest (score: {:.2}, downloads: {}, likes: {}) for tag '{}' using {} strategy.",
            best_model.model_id,
            best_model.final_score,
            best_model.downloads,
            best_model.likes,
            pipeline_tag,
            strategy
        );

        Ok(SelectionResult {
            best_model: best_model.clone(),
            all_candidates: candidates,
            strategy,
            optimization_time_ms,
            confidence_score: best_model.confidence_score,
            reasoning,
        })
    }

    /// Map higher-level task name to database pipeline_tag.
    fn map_task_to_tag(&self, task_name: &str) -> String {
        match task_name.to_lowercase().as_str() {
            "text-classification" | "sentiment" | "sentiment-analysis" | "spam" => "text-classification".to_string(),
            "question-answering" | "qa" | "question" => "question-answering".to_string(),
            "summarization" | "summary" => "summarization".to_string(),
            "translation" => "translation".to_string(),
            "image-classification" => "image-classification".to_string(),
            "object-detection" => "object-detection".to_string(),
            "automatic-speech-recognition" | "speech-recognition" | "asr" => "automatic-speech-recognition".to_string(),
            "code-analysis" => "text-generation".to_string(), // Text-generation is the backend tag for general LLM coding
            "malware-detection" => "text-classification".to_string(),
            other => other.to_string(),
        }
    }

    /// Freshness score decays over a year from 1.0 to 0.1.
    fn calculate_freshness(&self, m: &ModelMetrics) -> f64 {
        DateTime::parse_from_rfc3339(&m.last_modified)
            .or_else(|_| DateTime::parse_from_str(&m.last_modified, "%Y-%m-%dT%H:%M:%S%.fZ"))
            .map(|dt| {
                let days = (Utc::now() - dt.with_timezone(&Utc)).num_days();
                (1.0 - (days as f64 / 365.0)).clamp(0.1, 1.0)
            })
            .unwrap_or(0.5)
    }

    /// License evaluation: returns 1.0 for open-source licenses, 0.2 for unknown/proprietary.
    fn evaluate_license(&self, m: &ModelMetrics) -> f64 {
        let lic = m.license.to_lowercase();
        if self.open_licenses.iter().any(|open| lic.contains(open)) {
            1.0
        } else if lic == "unknown" || lic.is_empty() {
            0.5
        } else {
            0.2 // Restricted
        }
    }
}

/// Ensemble selection logic.
pub struct EnsembleModelSelector;

impl EnsembleModelSelector {
    /// Perform voting / weighted average ensemble selection over candidates.
    pub fn select_ensemble(candidates: &[ModelCandidate]) -> Option<ModelCandidate> {
        if candidates.is_empty() {
            return None;
        }

        // Weighted voting strategy using normalized decision + capability score
        let mut best: Option<&ModelCandidate> = None;
        let mut max_weighted_score = -1.0;

        for c in candidates {
            // Ensemble score = 0.5 * final_score + 0.3 * decision_score + 0.2 * capability_score
            let score = c.final_score * 0.5
                + c.decision_score.clamp(0.0, 1.0) * 0.3
                + c.capability_score.clamp(0.0, 1.0) * 0.2;

            if score > max_weighted_score {
                max_weighted_score = score;
                best = Some(c);
            }
        }

        best.cloned()
    }
}

fn is_fictional_or_non_chat(model_id: &str) -> bool {
    let lower = model_id.to_lowercase();
    
    // Fictional models in the db
    if lower.contains("gemma-4")
        || lower.contains("qwen3")
        || lower.contains("gpt-5.5")
        || lower.contains("glm-5.2")
        || lower.contains("gpt-oss")
    {
        return true;
    }
    
    // Non-chat models in the db under text-generation or QA
    if lower.contains("electra")
        || lower.contains("colbert")
        || lower.contains("gpt2")
        || lower.contains("contriever")
        || lower.contains("opt-125m")
        || lower.contains("roberta")
        || lower.contains("bert")
        || lower.contains("deberta")
        || lower.contains("splinter")
        || lower.contains("koelectra")
        || lower.contains("yolos")
        || lower.contains("transformer")
        || lower.contains("detr")
        || lower.contains("tiny-")
        || lower.contains("trl-internal-testing")
        || lower.contains("tiny-random")
        || lower.contains("dummy")
    {
        return true;
    }
    
    false
}
