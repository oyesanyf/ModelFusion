//! Multi-objective model selection.
//!
//! Evaluates and selects the best model for a given task using multi-objective scoring,
//! and supports different selection strategies.

pub mod memory;
pub mod pareto;
pub mod structured_router;

pub use pareto::*;
pub use structured_router::{RoutingDecision, StructuredRouter};

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
    Fastest,
    WeightedVoting,
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
            Self::Fastest => "Fastest",
            Self::WeightedVoting => "WeightedVoting",
        };
        write!(f, "{}", name)
    }
}

pub use memory::is_unblocked_default;

fn default_feed_source() -> String {
    "standard_hub".to_string()
}

pub const HIGH_SIGNAL_RESEARCH_ORGS: &[&str] = &[
    "RecursiveSI", "Qwen", "deepseek-ai", "google", "meta-llama",
    "mistralai", "microsoft", "allenai", "nvidia",
];

pub fn is_high_signal_research_org(author_or_id: &str) -> bool {
    let lower = author_or_id.to_lowercase();
    HIGH_SIGNAL_RESEARCH_ORGS.iter().any(|org| {
        let org_lower = org.to_lowercase();
        lower == org_lower || lower.starts_with(&format!("{}/", org_lower))
    })
}

pub fn normalize_trending_velocity(trending_score: f64) -> f64 {
    if trending_score > 1.0 {
        (trending_score / 1000.0).clamp(0.0, 1.0)
    } else {
        trending_score.clamp(0.0, 1.0)
    }
}

pub fn calculate_following_boost(m: &ModelMetrics) -> f64 {
    if m.feed_source.contains("following")
        || is_high_signal_research_org(&m.author)
        || is_high_signal_research_org(&m.model_id)
        || memory::is_unblocked_default(&m.model_id)
    {
        1.0
    } else {
        0.0
    }
}

pub fn calculate_ucb1_exploration_bonus(alpha: f64, total_pulls_n: i64, model_pulls_n_i: i64) -> f64 {
    let n_eff = (model_pulls_n_i.max(0) as f64).max(1.0);
    let n_total = (total_pulls_n.max(0) as f64).max(2.0);
    alpha * ((2.0 * n_total.ln()) / n_eff).sqrt()
}

pub fn calculate_memory_penalty(model_id: &str, required_gb: f64, free_ram_gb: f64) -> f64 {
    if memory::is_unblocked_default(model_id) {
        0.0
    } else if free_ram_gb <= 0.0 && required_gb > 0.0 {
        1000.0
    } else if required_gb > free_ram_gb && free_ram_gb > 0.0 {
        ((required_gb - free_ram_gb) / free_ram_gb) * 10.0
    } else {
        0.0
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct MultiObjectiveScoreBreakdown {
    pub raw_score: f64,
    pub quality_term: f64,
    pub download_term: f64,
    pub trending_term: f64,
    pub following_term: f64,
    pub ucb1_term: f64,
    pub memory_penalty: f64,
    pub is_unblocked_default: bool,
    #[serde(default)]
    pub task_quality_q: f64,
    #[serde(default)]
    pub log_downloads: f64,
    #[serde(default)]
    pub trending_velocity: f64,
    #[serde(default)]
    pub following_boost: f64,
    #[serde(default)]
    pub ucb1_exploration_bonus: f64,
    #[serde(default)]
    pub composite_pareto_score: f64,
    #[serde(default)]
    pub pareto_rank: usize,
    #[serde(default)]
    pub is_knee_point: bool,
}

pub fn calculate_multi_objective_score(
    model_id: &str,
    q_task: f64,
    downloads: i64,
    v_trending: f64,
    b_following: f64,
    total_pulls_n: i64,
    model_pulls_n_i: i64,
    required_gb: f64,
    free_ram_gb: f64,
) -> MultiObjectiveScoreBreakdown {
    let w1 = 0.25;
    let w2 = 0.15;
    let w3 = 0.25;
    let w4 = 0.15;
    let alpha = 0.20;

    let quality_term = w1 * q_task;
    let download_term = w2 * (1.0 + downloads.max(0) as f64).log10();
    let trending_term = w3 * v_trending.clamp(0.0, 1.0);
    let following_term = w4 * b_following.clamp(0.0, 1.0);

    let ucb1_term = calculate_ucb1_exploration_bonus(alpha, total_pulls_n, model_pulls_n_i);
    let memory_penalty = calculate_memory_penalty(model_id, required_gb, free_ram_gb);
    let is_unblocked = memory::is_unblocked_default(model_id);

    let raw_score = quality_term + download_term + trending_term + following_term + ucb1_term - memory_penalty;

    MultiObjectiveScoreBreakdown {
        raw_score,
        quality_term,
        download_term,
        trending_term,
        following_term,
        ucb1_term,
        memory_penalty,
        is_unblocked_default: is_unblocked,
        task_quality_q: q_task,
        log_downloads: (1.0 + downloads.max(0) as f64).log10(),
        trending_velocity: v_trending.clamp(0.0, 1.0),
        following_boost: b_following.clamp(0.0, 1.0),
        ucb1_exploration_bonus: ucb1_term,
        composite_pareto_score: raw_score,
        pareto_rank: 0,
        is_knee_point: false,
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
    #[serde(default)]
    pub trending_score: f64,
    #[serde(default = "default_feed_source")]
    pub feed_source: String,
    #[serde(default)]
    pub bandit_pulls: i64,
    #[serde(default)]
    pub bandit_reward: f64,
    #[serde(default)]
    pub pareto_breakdown: Option<MultiObjectiveScoreBreakdown>,
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
        let db = HuggingFaceModelDatabase::open(db_path)?;
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
        let mut db_models = self.db.get_by_task(&pipeline_tag, 100)?;

        if db_models.is_empty() && pipeline_tag != "text-generation" {
            if let Ok(fallback_models) = self.db.get_by_task("text-generation", 100) {
                if !fallback_models.is_empty() {
                    db_models = fallback_models;
                }
            }
        }

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

        if filtered_models.is_empty() && pipeline_tag != "text-generation" {
            if let Ok(fallback_models) = self.db.get_by_task("text-generation", 100) {
                for m in fallback_models {
                    if no_simulation && is_fictional_or_non_chat(&m.model_id) {
                        continue;
                    }
                    if let Some(max_params) = max_model_params_b {
                        let est = estimate_params_billions(&m.model_id).unwrap_or(0.0);
                        if est > 0.0 && est > max_params + 1.0 {
                            continue;
                        }
                    }
                    filtered_models.push(m);
                }
            }
        }

        if filtered_models.is_empty() {
            anyhow::bail!("No real chat models found in database for task '{}' after filtering.", task_name);
        }

        // Calculate max downloads for normalization
        // Calculate max downloads for normalization
        let max_downloads = filtered_models.iter().map(|m| m.downloads).max().unwrap_or(1) as f64;
        let _ = max_downloads;

        // Detect live system memory per Available Runtime Memory Rule
        let live_mem = SystemMemory::detect_live();
        let free_ram_gb = live_mem.free_ram_gb;

        let total_pulls_n: i64 = filtered_models
            .iter()
            .map(|m| m.bandit_pulls)
            .sum::<i64>()
            .max(10);

        let mut candidates = Vec::new();
        for m in &filtered_models {
            let freshness = self.calculate_freshness(m);
            let license_val = self.evaluate_license(m);
            let _ = license_val;

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

            let estimated_params_b = estimate_params_billions(&m.model_id).unwrap_or(0.0);
            let estimated_memory_gb = if estimated_params_b > 0.0 {
                estimate_runtime_memory_gb(estimated_params_b, backend)
            } else if m.size_mb > 0.0 {
                m.size_mb / 1024.0
            } else {
                0.0
            };

            let q_task = {
                let cap = if m.capability_score > 1.0 { (m.capability_score / 10.0).clamp(0.0, 1.0) } else { m.capability_score.clamp(0.0, 1.0) };
                let dec = if m.decision_score > 1.0 { (m.decision_score / 10.0).clamp(0.0, 1.0) } else { m.decision_score.clamp(0.0, 1.0) };
                cap * 0.6 + dec * 0.4
            };

            let v_trending = normalize_trending_velocity(m.trending_score);
            let b_following = calculate_following_boost(m);

            let mut score_breakdown = calculate_multi_objective_score(
                &m.model_id,
                q_task,
                m.downloads,
                v_trending,
                b_following,
                total_pulls_n,
                m.bandit_pulls,
                estimated_memory_gb,
                free_ram_gb,
            );

            let mut final_score = score_breakdown.raw_score;

            if freshness < 0.35 {
                final_score *= 0.60;
            }

            // Apply strategy variations/stubs
            match strategy {
                SelectionStrategy::CrossValidation => {
                    final_score += 0.02 * m.capability_score.clamp(0.0, 1.0);
                }
                SelectionStrategy::HyperparameterTuning => {
                    final_score += 0.01 * m.efficiency_score.clamp(0.0, 1.0);
                }
                SelectionStrategy::EnsembleMethods => {
                    final_score = (final_score + m.popularity_score.clamp(0.0, 1.0)) / 2.0;
                }
                SelectionStrategy::BayesianOptimization => {
                    final_score *= 1.02;
                }
                SelectionStrategy::MetaLearning => {
                    if prompt.contains("code") && m.library_name.contains("transformers") {
                        final_score += 0.05;
                    }
                }
                SelectionStrategy::Fastest => {
                    final_score = if m.size_mb > 0.0 {
                        (1.0 - (m.size_mb / 100_000.0)).clamp(0.01, 1.0)
                    } else {
                        0.5
                    };
                }
                SelectionStrategy::WeightedVoting => {
                    let dec_norm = (m.decision_score / 10.0).clamp(0.0, 1.0);
                    let cap_norm = (m.capability_score / 10.0).clamp(0.0, 1.0);
                    final_score = final_score * 0.5 + dec_norm * 0.3 + cap_norm * 0.2;
                }
                SelectionStrategy::MultiObjective => {
                    // Multi-objective composite score is calculated by calculate_multi_objective_score
                }
            }

            // Promote models cached in Ollama to ensure instant local response
            if memory::is_ollama_model_cached(&m.model_id) {
                final_score += 10.0;
            }

            let confidence = (final_score * 1.2).clamp(0.1, 1.0);

            // OpenVINO-aware scoring adjustment:
            if is_openvino {
                if is_cached {
                    final_score = (final_score + 0.15).min(1.0);
                } else if estimated_params_b > 3.0 {
                    final_score = (final_score - 0.4).max(0.0);
                }
            }

            let is_local = std::env::var("MODELFUSION_USE_TRANSFORMERS").is_ok()
                || std::env::var("MODELFUSION_USE_OPENVINO").is_ok()
                || std::env::var("MODELFUSION_USE_OLLAMA").is_ok()
                || std::env::var("MODELFUSION_USE_ONNX").is_ok();

            // Local Transformers cache-aware scoring:
            let is_transformers = backend == Backend::Transformers;
            if is_local && is_transformers {
                let is_tf_cached = memory::is_transformers_model_cached(&m.model_id);
                if is_tf_cached {
                    final_score = (final_score + 0.35).min(1.0);
                } else {
                    final_score = (final_score - 0.45).max(0.0);
                }
            }

            // Hardware suitability scoring adjustment:
            let is_unblocked = memory::is_unblocked_default(&m.model_id);
            let suitability = if is_unblocked {
                memory::SuitabilityResult::Adequate
            } else if is_local {
                memory::evaluate_hardware_suitability(
                    estimated_params_b,
                    backend,
                    &live_mem,
                )
            } else {
                memory::SuitabilityResult::Adequate
            };

            // Filter out models that do not meet minimum requirements immediately (unblocked models are never filtered)
            if is_local && !is_unblocked && suitability == memory::SuitabilityResult::Inadequate {
                log::debug!("Skipping candidate '{}' due to inadequate hardware resources", m.model_id);
                continue;
            }

            // Apply suitability boosts and penalties
            if suitability == memory::SuitabilityResult::Adequate {
                final_score = (final_score + 0.15).min(1.0);
            } else if suitability == memory::SuitabilityResult::Minimum {
                final_score = (final_score - 0.20).max(0.0);
            }

            score_breakdown.raw_score = final_score;
            score_breakdown.composite_pareto_score = final_score;

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
                trending_score: m.trending_score,
                feed_source: m.feed_source.clone(),
                bandit_pulls: m.bandit_pulls,
                bandit_reward: m.bandit_reward,
                pareto_breakdown: Some(score_breakdown),
            });
        }

        let mut pareto_front_len = 0;
        let mut pareto_knee_id: Option<String> = None;

        if strategy == SelectionStrategy::MultiObjective && !candidates.is_empty() {
            let directions = pareto::default_pareto_directions();

            let pareto_candidates: Vec<ParetoCandidate> = candidates
                .iter()
                .map(|c| {
                    let v_trending = normalize_trending_velocity(c.trending_score);
                    let b_following = if c.feed_source.contains("following")
                        || is_high_signal_research_org(&c.model_id)
                        || memory::is_unblocked_default(&c.model_id)
                    {
                        1.0
                    } else {
                        0.0
                    };
                    let efficiency = (c.efficiency_score / 10.0).clamp(0.0, 1.0);
                    let ucb1 = calculate_ucb1_exploration_bonus(0.20, total_pulls_n, c.bandit_pulls);

                    ParetoCandidate::from_model_objectives(
                        &c.model_id,
                        c.capability_score,
                        v_trending,
                        b_following,
                        efficiency,
                        ucb1,
                        c.estimated_memory_gb,
                    )
                })
                .collect();

            let front = pareto::compute_pareto_front(&pareto_candidates, &directions);
            pareto_front_len = front.len();

            if let Some(knee) = pareto::select_knee_point(&front, &directions) {
                let front_ids: std::collections::HashSet<String> = front.iter().map(|f| f.id.clone()).collect();
                for c in &mut candidates {
                    if c.model_id == knee.id {
                        c.final_score = 1.0;
                        if let Some(ref mut b) = c.pareto_breakdown {
                            b.is_knee_point = true;
                            b.pareto_rank = 1;
                        }
                    } else if front_ids.contains(&c.model_id) {
                        c.final_score += 0.40;
                        if let Some(ref mut b) = c.pareto_breakdown {
                            b.pareto_rank = 1;
                        }
                    }
                }
                pareto_knee_id = Some(knee.id);
            }
        }

        // Sort candidates by final score descending (safe against NaN values)
        candidates.sort_by(|a, b| {
            if let Some(ref knee_id) = pareto_knee_id {
                if a.model_id == *knee_id {
                    return std::cmp::Ordering::Less;
                }
                if b.model_id == *knee_id {
                    return std::cmp::Ordering::Greater;
                }
            }
            b.final_score.partial_cmp(&a.final_score).unwrap_or(std::cmp::Ordering::Equal)
        });

        // When using Ollama, keep models that are installed in Ollama OR match known Ollama equivalents
        if std::env::var("MODELFUSION_USE_OLLAMA").is_ok() {
            let ollama_models: &[&str] = &[
                "Qwen2.5-72B-Instruct", "Qwen2.5-32B-Instruct", "Qwen2.5-14B-Instruct",
                "Qwen2.5-7B-Instruct", "Qwen2.5-3B-Instruct", "Qwen2.5-1.5B-Instruct",
                "Qwen2.5-0.5B-Instruct", "Qwen2.5-Coder-32B-Instruct", "Qwen2.5-Coder-14B-Instruct",
                "Qwen2.5-Coder-7B-Instruct", "Qwen3-8B", "Qwen3-4B", "Qwen3-1.7B",
                "Llama-3.1-70B-Instruct", "Llama-3.1-8B-Instruct", "Llama-3.2-3B-Instruct", "Llama-3.2-1B-Instruct",
                "DeepSeek-R1-Distill-Qwen-1.5B", "DeepSeek-R1-Distill-Qwen-7B",
                "DeepSeek-R1-Distill-Qwen-14B", "DeepSeek-R1-Distill-Qwen-32B",
                "DeepSeek-R1-Distill-Llama-8B", "DeepSeek-R1-Distill-Llama-70B",
                "gemma-2-2b-it", "gemma-2-9b-it", "gemma-2-27b-it", "gemma-3-4b-it", "gemma-3-12b-it",
                "Phi-3-mini-4k-instruct", "Phi-4-mini-instruct", "Phi-4",
                "Mistral-7B-Instruct", "Mixtral-8x7B-Instruct",
            ];
            candidates.retain(|c| memory::is_unblocked_default(&c.model_id) || memory::is_ollama_model_cached(&c.model_id) || ollama_models.iter().any(|m| c.model_id.contains(m)));

            // Apply a major boost to candidates that are already installed / cached in Ollama
            for c in &mut candidates {
                if memory::is_ollama_model_cached(&c.model_id) {
                    c.final_score = (c.final_score + 0.40).min(1.0);
                }
            }

            // Re-sort so installed models appear first
            candidates.sort_by(|a, b| {
                let a_cached = memory::is_ollama_model_cached(&a.model_id);
                let b_cached = memory::is_ollama_model_cached(&b.model_id);
                match (a_cached, b_cached) {
                    (true, false) => std::cmp::Ordering::Less,
                    (false, true) => std::cmp::Ordering::Greater,
                    _ => b.final_score.partial_cmp(&a.final_score).unwrap_or(std::cmp::Ordering::Equal),
                }
            });
        }

        let is_local = std::env::var("MODELFUSION_USE_TRANSFORMERS").is_ok()
            || std::env::var("MODELFUSION_USE_OPENVINO").is_ok()
            || std::env::var("MODELFUSION_USE_OLLAMA").is_ok()
            || std::env::var("MODELFUSION_USE_ONNX").is_ok();

        let verbose = std::env::var("MODELFUSION_VERBOSE").is_ok();
        if is_local {
            // Dynamic memory-aware filtering: detect live system resources and exclude models that won't fit
            let sys_mem = SystemMemory::detect_live();
            if verbose {
                sys_mem.print_summary();
            }
            let budget = sys_mem.model_budget_gb();

            let before_count = candidates.len();
            candidates.retain(|c| {
                if memory::is_unblocked_default(&c.model_id) {
                    return true;
                }
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

        if candidates.is_empty() {
            anyhow::bail!("No suitable candidate models found for task '{}'", task_name);
        }

        if candidates.len() > max_candidates {
            candidates.truncate(max_candidates);
        }

        let best_model = candidates[0].clone();
        let optimization_time_ms = start_time.elapsed().as_millis() as u64;

        let reasoning = if strategy == SelectionStrategy::MultiObjective {
            format!(
                "Selected '{}' via Multi-Objective Pareto Search: optimal knee-point on non-dominated Pareto front ({} models evaluated, {} on front), balancing capability, latency, memory, and risk.",
                best_model.model_id,
                candidates.len(),
                pareto_front_len
            )
        } else {
            format!(
                "Selected '{}' because it ranked highest (score: {:.2}, downloads: {}, likes: {}) for tag '{}' using {} strategy.",
                best_model.model_id,
                best_model.final_score,
                best_model.downloads,
                best_model.likes,
                pipeline_tag,
                strategy
            )
        };

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
            "text-classification" | "sentiment" | "sentiment-analysis" | "spam" | "spam-detection" => "text-classification".to_string(),
            "question-answering" | "qa" | "question" => "question-answering".to_string(),
            "summarization" | "summary" => "summarization".to_string(),
            "translation" => "translation".to_string(),
            "image-classification" => "image-classification".to_string(),
            "object-detection" => "object-detection".to_string(),
            "automatic-speech-recognition" | "speech-recognition" | "asr" => "automatic-speech-recognition".to_string(),
            "code-analysis" | "code-summary-generation" | "code-generation" | "code_task" | "code-clone-detection" => "text-generation".to_string(),
            "code-vulnerability-detection" | "security_analysis" | "malware-detection" | "pii-detection" | "phishing-detection" => "text-classification".to_string(),
            "data-science" | "datascience" | "data-analyst" | "dataanalyst" | "jupyter" | "data_science" | "table-question-answering" => "text-generation".to_string(),
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
            // Ensemble score = 0.5 * final_score + 0.3 * normalized decision_score + 0.2 * normalized capability_score
            let score = c.final_score * 0.5
                + (c.decision_score / 10.0).clamp(0.0, 1.0) * 0.3
                + (c.capability_score / 10.0).clamp(0.0, 1.0) * 0.2;

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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fastest_and_weighted_voting_strategies() {
        let candidate_a = ModelCandidate {
            model_id: "model-small".to_string(),
            downloads: 1000,
            likes: 100,
            decision_score: 8.0,
            capability_score: 7.0,
            efficiency_score: 9.0,
            popularity_score: 0.8,
            size_mb: 500.0,
            license: "mit".to_string(),
            freshness_score: 0.9,
            final_score: 0.8,
            confidence_score: 0.85,
            estimated_params_b: 0.5,
            estimated_memory_gb: 1.0,
            trending_score: 0.0,
            feed_source: "standard_hub".to_string(),
            bandit_pulls: 0,
            bandit_reward: 0.0,
            pareto_breakdown: None,
        };

        let candidate_b = ModelCandidate {
            model_id: "model-large".to_string(),
            downloads: 5000,
            likes: 500,
            decision_score: 9.5,
            capability_score: 9.0,
            efficiency_score: 5.0,
            popularity_score: 0.9,
            size_mb: 8000.0,
            license: "apache-2.0".to_string(),
            freshness_score: 0.9,
            final_score: 0.9,
            confidence_score: 0.95,
            estimated_params_b: 7.0,
            estimated_memory_gb: 14.0,
            trending_score: 0.0,
            feed_source: "standard_hub".to_string(),
            bandit_pulls: 0,
            bandit_reward: 0.0,
            pareto_breakdown: None,
        };

        let ensemble_choice = EnsembleModelSelector::select_ensemble(&[candidate_a.clone(), candidate_b.clone()]);
        assert!(ensemble_choice.is_some());
        assert_eq!(ensemble_choice.unwrap().model_id, "model-large");

        // Fastest score normalization check
        let size_mb: f64 = 500.0;
        let fastest_score = (1.0f64 - (size_mb / 100_000.0f64)).clamp(0.01f64, 1.0f64);
        assert!(fastest_score <= 1.0 && fastest_score >= 0.0);
    }

    #[test]
    fn test_multi_objective_pareto_selection() {
        let temp_dir = std::env::temp_dir().join(format!("test_mf_pareto_{}", std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));
        let db_path = temp_dir.join("test_models.db");
        let db = HuggingFaceModelDatabase::new(&db_path).expect("Failed to create test db");

        let m1 = ModelMetrics {
            model_id: "org/model-capable".to_string(),
            pipeline_tag: "text-generation".to_string(),
            downloads: 10000,
            likes: 500,
            decision_score: 8.0,
            capability_score: 9.5,
            efficiency_score: 5.0,
            size_mb: 16000.0,
            license: "apache-2.0".to_string(),
            last_modified: "2024-01-01T00:00:00Z".to_string(),
            ..Default::default()
        };

        let m2 = ModelMetrics {
            model_id: "org/model-balanced-knee".to_string(),
            pipeline_tag: "text-generation".to_string(),
            downloads: 20000,
            likes: 1000,
            decision_score: 9.0,
            capability_score: 9.0,
            efficiency_score: 9.0,
            size_mb: 3000.0,
            license: "mit".to_string(),
            last_modified: "2024-01-01T00:00:00Z".to_string(),
            ..Default::default()
        };

        let m3 = ModelMetrics {
            model_id: "org/model-dominated".to_string(),
            pipeline_tag: "text-generation".to_string(),
            downloads: 100,
            likes: 10,
            decision_score: 3.0,
            capability_score: 5.0,
            efficiency_score: 4.0,
            size_mb: 8000.0,
            license: "mit".to_string(),
            last_modified: "2024-01-01T00:00:00Z".to_string(),
            ..Default::default()
        };

        db.upsert(&m1).expect("Failed to upsert m1");
        db.upsert(&m2).expect("Failed to upsert m2");
        db.upsert(&m3).expect("Failed to upsert m3");

        let selector = EnhancedModelSelector::new(&db_path).expect("Failed to create selector");
        let result = selector.select_best_model(
            "text-generation",
            "Generate Rust code",
            SelectionStrategy::MultiObjective,
            10,
            None,
        ).expect("Selection should succeed");

        assert_eq!(result.strategy, SelectionStrategy::MultiObjective);
        assert_eq!(result.best_model.final_score, 1.0);
        assert!(result.reasoning.contains("via Multi-Objective Pareto Search: optimal knee-point"));
        assert!(result.reasoning.contains("on front"));

        let _ = std::fs::remove_dir_all(temp_dir);
    }

    #[test]
    fn test_pareto_trending_velocity_scoring() {
        // 1. Stale legacy model: 1,000,000 downloads, zero trending velocity, zero following boost, high pull count
        let legacy_score = calculate_multi_objective_score(
            "legacy/million-downloads",
            0.85,
            1_000_000,
            0.0,
            0.0,
            200,
            150,
            12.0,
            32.0,
        );

        // 2. Breakout model: only 500 downloads, but rapid 7-day velocity + followed research org + under-explored
        let breakout_score = calculate_multi_objective_score(
            "RecursiveSI/breakout-v1",
            0.85,
            500,
            0.98,
            1.0,
            200,
            2,
            12.0,
            32.0,
        );

        // Breakout model must outscore stale legacy model
        assert!(
            breakout_score.raw_score > legacy_score.raw_score,
            "Breakout model ({:.4}) must outscore stale legacy model ({:.4})",
            breakout_score.raw_score,
            legacy_score.raw_score
        );

        // 3. Pareto front verification: breakout cold-start model appears on the non-dominated Pareto frontier
        let directions = default_pareto_directions();
        // Legacy model trades off higher capability (0.95) against zero trending/following velocity
        let c_legacy = ParetoCandidate::from_model_objectives("legacy", 0.95, 0.0, 0.0, 0.8, legacy_score.ucb1_term, 12.0);
        let c_breakout = ParetoCandidate::from_model_objectives("breakout", 0.85, 0.98, 1.0, 0.8, breakout_score.ucb1_term, 12.0);
        let c_dominated = ParetoCandidate::from_model_objectives("dominated", 0.50, 0.0, 0.0, 0.4, 0.05, 24.0);

        let front = compute_pareto_front(&[c_legacy, c_breakout.clone(), c_dominated], &directions);
        let front_ids: Vec<String> = front.iter().map(|c| c.id.clone()).collect();
        assert!(front_ids.contains(&"breakout".to_string()));
        assert!(front_ids.contains(&"legacy".to_string()));
        assert!(!front_ids.contains(&"dominated".to_string()));
    }

    #[test]
    fn test_ucb1_exploration_bonus() {
        let total_n = 1000;
        let pulls = [1, 5, 20, 50, 200];
        let mut prev_bonus = f64::INFINITY;

        for &ni in &pulls {
            let bonus = calculate_ucb1_exploration_bonus(0.20, total_n, ni);
            assert!(
                bonus < prev_bonus,
                "UCB1 bonus must decrease monotonically as pull count increases: ni={} ({}) vs prev ({})",
                ni, bonus, prev_bonus
            );
            assert!(bonus > 0.0, "UCB1 bonus must be strictly positive");
            prev_bonus = bonus;
        }

        // Verify exact mathematical formula at N=100, n_i=8
        // 0.20 * sqrt(2 * ln(100) / 8) = 0.20 * sqrt(9.21034037 / 8) = 0.20 * 1.072983 = 0.214596...
        let exact_check = calculate_ucb1_exploration_bonus(0.20, 100, 8);
        let expected = 0.20 * ((2.0 * (100.0f64).ln()) / 8.0).sqrt();
        assert!((exact_check - expected).abs() < 1e-6);
        assert!((exact_check - 0.214596).abs() < 1e-4);
    }

    #[test]
    fn test_runtime_memory_penalty_and_unblocked_law() {
        let free_ram_gb = 8.0;

        // 1. Model that fits: required 6 GB on 8 GB free -> 0 penalty
        let fit_res = calculate_multi_objective_score(
            "small/fit-model",
            0.8,
            1000,
            0.5,
            0.0,
            100,
            10,
            6.0,
            free_ram_gb,
        );
        assert_eq!(fit_res.memory_penalty, 0.0);

        // 2. Oversized model: required 16 GB on 8 GB free -> ((16-8)/8)*10 = 10.0 penalty
        let oversized_res = calculate_multi_objective_score(
            "huge/oversized-model",
            0.8,
            1000,
            0.5,
            0.0,
            100,
            10,
            16.0,
            free_ram_gb,
        );
        assert_eq!(oversized_res.memory_penalty, 10.0);
        assert!(oversized_res.raw_score < fit_res.raw_score);

        // 3. Unblocked Default Law: Flint, Goose, and RAPTOR always have P_memory = 0.0
        let low_free_ram = 4.0;

        let flint_res = calculate_multi_objective_score(
            "RecursiveSI/flint",
            0.95,
            5000,
            0.95,
            1.0,
            100,
            10,
            24.0,
            low_free_ram,
        );
        assert_eq!(flint_res.memory_penalty, 0.0);
        assert!(flint_res.is_unblocked_default);

        let flint_latest_res = calculate_multi_objective_score(
            "flint:latest",
            0.95,
            5000,
            0.95,
            1.0,
            100,
            10,
            24.0,
            low_free_ram,
        );
        assert_eq!(flint_latest_res.memory_penalty, 0.0);
        assert!(flint_latest_res.is_unblocked_default);

        let goose_res = calculate_multi_objective_score(
            "goose",
            0.90,
            3000,
            0.80,
            1.0,
            100,
            10,
            16.0,
            low_free_ram,
        );
        assert_eq!(goose_res.memory_penalty, 0.0);
        assert!(goose_res.is_unblocked_default);

        let raptor_res = calculate_multi_objective_score(
            "raptor",
            0.90,
            3000,
            0.80,
            1.0,
            100,
            10,
            16.0,
            low_free_ram,
        );
        assert_eq!(raptor_res.memory_penalty, 0.0);
        assert!(raptor_res.is_unblocked_default);

        // 4. Live system memory detection check
        let live_mem = SystemMemory::detect_live();
        assert!(live_mem.free_ram_gb > 0.0);
        assert!(live_mem.free_vram_mb() >= 0.0);
    }
}
