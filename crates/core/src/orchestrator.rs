//! HuggingFace Orchestrator - Main orchestration engine.

use crate::task_processor::{TaskResult, UniversalTaskProcessor};
use model_selection::{EnhancedModelSelector, SelectionStrategy};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use std::time::Instant;
use task_detection::IntelligentTaskDetector;

/// Result of an orchestration operation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrchestrationResult {
    pub success: bool,
    pub content: String,
    pub task_results: Vec<TaskResult>,
    pub total_cost: f64,
    pub total_tokens: usize,
    pub total_latency_ms: f64,
    pub models_used: Vec<String>,
    pub error_message: Option<String>,
}

/// Main orchestrator that integrates all components.
pub struct HuggingFaceOrchestrator {
    pub budget: f64,
    pub enable_ml: bool,
    pub verbose: bool,
    pub task_processor: UniversalTaskProcessor,
    pub total_cost: Mutex<f64>,
    pub total_tokens: Mutex<usize>,
    pub db_path: PathBuf,
    task_detector: IntelligentTaskDetector,
}

impl HuggingFaceOrchestrator {
    /// Create a new orchestrator.
    pub fn new(db_path: impl AsRef<Path>, budget: f64, enable_ml: bool, verbose: bool) -> Self {
        let db_path = db_path.as_ref().to_path_buf();
        let task_processor = UniversalTaskProcessor::new();

        // Print API key status to console as expected by CLI output
        let openai_ok = std::env::var("OPENAI_API_KEY").is_ok();
        let anthropic_ok = std::env::var("ANTHROPIC_API_KEY").is_ok();
        let gemini_ok = std::env::var("GOOGLE_GEMINI_API_KEY").is_ok();
        let hf_ok = std::env::var("HF_TOKEN").is_ok() 
            || std::env::var("HUGGINGFACE_API_KEY").is_ok()
            || std::env::var("HF_API_KEY").is_ok()
            || std::env::var("HUGGINGFACE_TOKEN").is_ok();

        println!("OK");
        println!("API Keys Loaded:");
        println!(
            "   openai: {}, anthropic: {}, gemini: {}, huggingface: {}",
            if openai_ok { "[LOADED]" } else { "[MISSING]" },
            if anthropic_ok { "[LOADED]" } else { "[MISSING]" },
            if gemini_ok { "[LOADED]" } else { "[MISSING]" },
            if hf_ok { "[LOADED]" } else { "[MISSING]" }
        );

        Self {
            budget,
            enable_ml,
            verbose,
            task_processor,
            total_cost: Mutex::new(0.0),
            total_tokens: Mutex::new(0),
            db_path,
            task_detector: IntelligentTaskDetector::new(),
        }
    }

    /// Process a task through task type detection, model selection, and execution.
    pub async fn process_task(
        &self,
        prompt: &str,
        task_override: Option<&str>,
        model_override: Option<&str>,
        use_openai: bool,
        file_path: Option<&str>,
        selection_strategy: Option<SelectionStrategy>,
        options: HashMap<String, String>,
    ) -> OrchestrationResult {
        let start = Instant::now();

        // Check budget limit
        {
            let current_cost = *self.total_cost.lock().unwrap();
            if use_openai && current_cost >= self.budget {
                return OrchestrationResult {
                    success: false,
                    content: "Budget exceeded".to_string(),
                    task_results: Vec::new(),
                    total_cost: current_cost,
                    total_tokens: *self.total_tokens.lock().unwrap(),
                    total_latency_ms: start.elapsed().as_millis() as f64,
                    models_used: Vec::new(),
                    error_message: Some("Budget limit reached (use HuggingFace models for free processing)".to_string()),
                };
            }
        }

        // Determine/detect task name
        let task_name = if let Some(t) = task_override {
            t.to_string()
        } else {
            let detection = self.task_detector.detect_task_type(prompt);
            if self.verbose {
                println!(
                    "🔍 [DETECTOR] Detected task: {} (confidence: {:.2})",
                    detection.task_type, detection.confidence
                );
            }
            detection.task_type
        };

        // Determine final model selection
        let mut candidates = Vec::new();
        let selection_info;

        if let Some(m) = model_override {
            candidates.push(m.to_string());
            selection_info = "forced model".to_string();
        } else if use_openai {
            // Default to meta-llama/Llama-3.1-8B-Instruct if OpenAI requested
            candidates.push("meta-llama/Llama-3.1-8B-Instruct".to_string());
            selection_info = "default openai model".to_string();
        } else {
            // Use enhanced selection from DB
            match EnhancedModelSelector::new(&self.db_path) {
                Err(e) => {
                    log::warn!("Could not open database for selection: {}. Using fallback model.", e);
                    candidates.push("gpt2".to_string());
                    selection_info = "db error fallback".to_string();
                }
                Ok(selector) => {
                    let strategy = selection_strategy.unwrap_or(SelectionStrategy::MultiObjective);
                    match selector.select_best_model(&task_name, prompt, strategy, 10) {
                        Err(e) => {
                            log::warn!("Selection failed: {}. Using fallback model.", e);
                            candidates.push("gpt2".to_string());
                            selection_info = "selection failure fallback".to_string();
                        }
                        Ok(res) => {
                            if self.verbose {
                                println!(
                                    "📋 [SELECTION] Strategy: {}, Best Model: {}, Confidence: {:.2}",
                                    res.strategy, res.best_model.model_id, res.confidence_score
                                );
                            }
                            candidates = res.all_candidates.into_iter().map(|c| c.model_id).collect();
                            selection_info = format!("strategy: {}", res.strategy);
                        }
                    }
                }
            }
        }

        if candidates.is_empty() {
            candidates.push("gpt2".to_string());
        }

        // Execute task (loop through candidates in order of ranking)
        let mut final_result = None;
        let mut models_used = Vec::new();

        for model_id in &candidates {
            if self.verbose {
                println!("[ORCHESTRATOR] Routing task '{}' to model '{}' ({})", task_name, model_id, selection_info);
            }
            models_used.push(model_id.clone());

            let res = if let Some(fp) = file_path {
                self.task_processor
                    .process_file_analysis(Path::new(fp), &task_name, prompt, Some(model_id), options.clone())
                    .await
            } else {
                self.task_processor
                    .process_task(&task_name, prompt, Some(model_id), None, None, options.clone())
                    .await
            };

            let is_failure = res.status != "success" 
                || res.content.starts_with("[Offline Fallback") 
                || res.content.contains("mock response")
                || res.content.contains("API request failed");

            if !is_failure {
                final_result = Some(res);
                break;
            } else {
                log::warn!("⚠️ Model '{}' failed or went offline. Trying next candidate...", model_id);
            }
        }

        // If all candidates failed, use the result of the first candidate (which contains the offline fallback output)
        let task_result = match final_result {
            Some(res) => res,
            None => {
                log::warn!("❌ All candidates failed or went offline. Returning final offline fallback.");
                if let Some(fp) = file_path {
                    self.task_processor
                        .process_file_analysis(Path::new(fp), &task_name, prompt, Some(&candidates[0]), options.clone())
                        .await
                } else {
                    self.task_processor
                        .process_task(&task_name, prompt, Some(&candidates[0]), None, None, options.clone())
                        .await
                }
            }
        };

        // Accumulate statistics
        let mut cost_lock = self.total_cost.lock().unwrap();
        let mut tokens_lock = self.total_tokens.lock().unwrap();

        *cost_lock += task_result.cost;
        *tokens_lock += task_result.tokens_used;

        let success = task_result.status == "success" && !task_result.content.starts_with("[Offline Fallback");
        let content = task_result.content.clone();
        let err_msg = task_result.error_message.clone();

        OrchestrationResult {
            success,
            content,
            task_results: vec![task_result],
            total_cost: *cost_lock,
            total_tokens: *tokens_lock,
            total_latency_ms: start.elapsed().as_millis() as f64,
            models_used,
            error_message: err_msg,
        }
    }
}
