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

use anyhow::Context;

/// Run the model fusion pipeline.
pub async fn run_fusion(
    prompt: &str,
    context: Option<&str>,
    db_path: Option<&Path>,
    task_override: Option<&str>,
    strategy: Option<SelectionStrategy>,
    max_candidates: Option<usize>,
) -> anyhow::Result<String> {
    let db_path_ref = db_path.context("[FUSION] Database path is required and cannot be bypassed.")?;
 
    // Detect task name on the original prompt
    let detected_task = if let Some(t) = task_override {
        t.to_string()
    } else {
        let detector = IntelligentTaskDetector::new();
        let detection = detector.detect_task_type(prompt);
        println!("🔍 [FUSION] Detected task: {} (confidence: {:.2})", detection.task_type, detection.confidence);
        detection.task_type
    };

    let strategy = strategy.unwrap_or(SelectionStrategy::MultiObjective);
    
    let selector = EnhancedModelSelector::new(db_path_ref)
        .context("⚠️ [FUSION] Failed to open database for model selection.")?;
        
    let max_candidates = max_candidates.unwrap_or(10);
    // We always use text-generation models for the fusion panel, judge, and writer to ensure chat compatibility.
    let panel_task = "text-generation";
    let res = selector.select_best_model(panel_task, prompt, strategy, max_candidates)
        .context("⚠️ [FUSION] Model selection failed from database.")?;
        
    if res.all_candidates.is_empty() {
        return Err(anyhow::anyhow!("⚠️ [FUSION] No candidates found in database for task '{}'.", panel_task));
    }
    
    println!("📋 [FUSION] Model selection successful (detected task: '{}', selected strategy: {}).", detected_task, res.strategy);
    println!("📋 [FUSION] Selected models for the panel:");
    let mut panel_models = Vec::new();
    for (i, candidate) in res.all_candidates.iter().enumerate() {
        println!("  {}. {} (score: {:.2})", i + 1, candidate.model_id, candidate.final_score);
        panel_models.push(ModelConfig::huggingface(&candidate.model_id));
    }

    // Define the judge model from the database (best text-generation model)
    let judge_res = selector.select_best_model("text-generation", "judge evaluation", strategy, 1)
        .context("⚠️ [FUSION] Failed to select judge model from database.")?;
    let judge_model = ModelConfig::huggingface(&judge_res.best_model.model_id);
    println!("⚖️ [FUSION] Selected judge model from database: {}", judge_res.best_model.model_id);

    // Define the final writer model from the database (best text-generation model)
    let writer_res = selector.select_best_model("text-generation", "final synthesis writing", strategy, 1)
        .context("⚠️ [FUSION] Failed to select writer model from database.")?;
    let writer_model = ModelConfig::huggingface(&writer_res.best_model.model_id);
    println!("✍️ [FUSION] Selected writer model from database: {}", writer_res.best_model.model_id);

    let prompt_with_context = if let Some(ctx) = context {
        format!("{}\n\n### CONTEXT:\n{}", prompt, ctx)
    } else {
        prompt.to_string()
    };

    println!("[FUSION] Starting Model Fusion Pipeline...");
    println!("[FUSION] Step 1: Running Panel of {} models concurrently...", panel_models.len());
    let panel_answers = run_panel(&prompt_with_context, panel_models).await?;
    
    for ans in &panel_answers {
        println!("  * Received response from {}", ans.model_name);
        if ans.answer.starts_with("MODEL ERROR") {
            println!("    [WARN] Warning: {}", ans.answer);
        }
    }

    println!("[FUSION] Step 2: Judging panel responses...");
    let judge_json = judge_panel(&prompt_with_context, &panel_answers, &judge_model).await?;

    println!("[FUSION] Step 3: Writing final synthesized answer...");
    let final_answer = write_final_answer(&prompt_with_context, &judge_json, &writer_model).await?;

    Ok(final_answer)
}
