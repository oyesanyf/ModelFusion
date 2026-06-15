pub mod schema;
pub mod models;
pub mod fusion;
pub mod judge;

use schema::ModelConfig;
use fusion::run_panel;
use judge::{judge_panel, write_final_answer};
use model_selection::{EnhancedModelSelector, SelectionStrategy};
use task_detection::IntelligentTaskDetector;
use std::path::Path;

/// Simple heuristic classifier to decide if prompt needs fusion.
pub fn classify_prompt(prompt: &str) -> bool {
    let lower = prompt.to_lowercase();
    let keywords = vec![
        "compare", "analyze", "evaluate", "synthesize", "perspective", 
        "discuss", "opinion", "different", "best way", "pro and con",
        "versus", "vs", "difference between"
    ];
    for kw in keywords {
        if lower.contains(kw) {
            return true;
        }
    }
    // Check word count
    prompt.split_whitespace().count() > 20
}

/// Run the model fusion pipeline.
pub async fn run_fusion(
    prompt: &str,
    db_path: Option<&Path>,
    task_override: Option<&str>,
    strategy: Option<SelectionStrategy>,
) -> anyhow::Result<String> {
    let mut panel_models = Vec::new();
    let mut used_selection = false;

    let openai_active = std::env::var("OPENAI_API_KEY").is_ok();
    let gemini_active = std::env::var("GOOGLE_GEMINI_API_KEY").is_ok();

    if let Some(db_path_ref) = db_path {
        if !openai_active && !gemini_active {
            // Detect task name
            let task_name = if let Some(t) = task_override {
                t.to_string()
            } else {
                let detector = IntelligentTaskDetector::new();
                let detection = detector.detect_task_type(prompt);
                println!("🔍 [FUSION] Detected task: {} (confidence: {:.2})", detection.task_type, detection.confidence);
                detection.task_type
            };

            let strategy = strategy.unwrap_or(SelectionStrategy::MultiObjective);
            
            match EnhancedModelSelector::new(db_path_ref) {
                Ok(selector) => {
                    match selector.select_best_model(&task_name, prompt, strategy, 10) {
                        Ok(res) => {
                            println!("📋 [FUSION] Model selection successful for task '{}' (strategy: {}).", task_name, res.strategy);
                            println!("📋 [FUSION] Selected models for the panel:");
                            for (i, candidate) in res.all_candidates.iter().enumerate() {
                                println!("  {}. {} (score: {:.2})", i + 1, candidate.model_id, candidate.final_score);
                                panel_models.push(ModelConfig::huggingface(&candidate.model_id));
                            }
                            if !panel_models.is_empty() {
                                used_selection = true;
                            }
                        }
                        Err(e) => {
                            println!("⚠️ [FUSION] Model selection failed: {}. Falling back to default 10 models.", e);
                        }
                    }
                }
                Err(e) => {
                    println!("⚠️ [FUSION] Could not open database for model selection: {}. Falling back to default 10 models.", e);
                }
            }
        }
    }

    if !used_selection {
        if std::env::var("OPENAI_API_KEY").is_ok() {
            println!("[FUSION] Using OpenAI models for panel (OPENAI_API_KEY found):");
            let defaults = vec![
                "gpt-4o-mini",
                "gpt-4o",
                "gpt-4-turbo",
                "gpt-4",
                "gpt-4o-mini",
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4o",
            ];
            for (i, m) in defaults.iter().enumerate() {
                println!("  {}. {}", i + 1, m);
                panel_models.push(ModelConfig::openai(m));
            }
        } else if std::env::var("GOOGLE_GEMINI_API_KEY").is_ok() {
            println!("[FUSION] Using Gemini models for panel (GOOGLE_GEMINI_API_KEY found):");
            let defaults = vec![
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
            ];
            for (i, m) in defaults.iter().enumerate() {
                println!("  {}. {}", i + 1, m);
                panel_models.push(ModelConfig::google(m));
            }
        } else {
            println!("[FUSION] Using default 10 models for panel:");
            let defaults = vec![
                "meta-llama/Llama-3.1-8B-Instruct",
                "meta-llama/Meta-Llama-3-8B-Instruct",
                "Qwen/Qwen2.5-7B-Instruct",
                "Qwen/Qwen2.5-Coder-7B-Instruct",
                "Qwen/Qwen2.5-Coder-32B-Instruct",
                "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
                "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
                "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
                "Qwen/QwQ-32B",
                "CohereLabs/aya-expanse-32b",
            ];
            for (i, m) in defaults.iter().enumerate() {
                println!("  {}. {}", i + 1, m);
                panel_models.push(ModelConfig::huggingface(m));
            }
        }
    }

    // Define the judge model
    let judge_model = if std::env::var("OPENAI_API_KEY").is_ok() {
        ModelConfig::openai("gpt-4o")
    } else if std::env::var("GOOGLE_GEMINI_API_KEY").is_ok() {
        ModelConfig::google("gemini-1.5-pro")
    } else {
        ModelConfig::huggingface("deepseek-ai/DeepSeek-R1-Distill-Qwen-32B")
    };

    // Define the final writer model
    let writer_model = if std::env::var("OPENAI_API_KEY").is_ok() {
        ModelConfig::openai("gpt-4o")
    } else if std::env::var("GOOGLE_GEMINI_API_KEY").is_ok() {
        ModelConfig::google("gemini-1.5-pro")
    } else {
        ModelConfig::huggingface("deepseek-ai/DeepSeek-R1-Distill-Qwen-32B")
    };

    println!("[FUSION] Starting Model Fusion Pipeline...");
    println!("[FUSION] Step 1: Running Panel of {} models concurrently...", panel_models.len());
    let panel_answers = run_panel(prompt, panel_models).await?;
    
    for ans in &panel_answers {
        println!("  * Received response from {}", ans.model_name);
        if ans.answer.starts_with("MODEL ERROR") {
            println!("    [WARN] Warning: {}", ans.answer);
        }
    }

    println!("[FUSION] Step 2: Judging panel responses...");
    let judge_json = judge_panel(prompt, &panel_answers, &judge_model).await?;

    println!("[FUSION] Step 3: Writing final synthesized answer...");
    let final_answer = write_final_answer(prompt, &judge_json, &writer_model).await?;

    Ok(final_answer)
}
