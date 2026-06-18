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
    fusion_mode: &str,
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

    let is_multi_sample = fusion_mode == "multi-sample";

    // For multi-sample mode: select 1 best model, create N configs with different temperatures
    // For multi-model mode: select N different models
    let panel_task = "text-generation";

    let (panel_models, fallback_pool) = if is_multi_sample {
        // Multi-sample: 1 model, N temperature variations — much faster for local execution
        let res = selector.select_best_model(panel_task, prompt, strategy, 3)
            .context("⚠️ [FUSION] Model selection failed from database.")?;
        
        if res.all_candidates.is_empty() {
            return Err(anyhow::anyhow!("⚠️ [FUSION] No candidates found in database for task '{}'.", panel_task));
        }

        let best = &res.best_model;
        println!("⚡ [FUSION] Multi-sample mode: using 1 model with {} temperature variations", max_candidates);
        println!("📋 [FUSION] Selected model: {} (score: {:.2})", best.model_id, best.final_score);
        if best.estimated_params_b > 0.0 {
            println!("   ~{:.1}B params, ~{:.1} GB RAM", best.estimated_params_b, best.estimated_memory_gb);
        }

        // Generate evenly spaced temperatures from 0.3 to 1.1
        let temps: Vec<f32> = (0..max_candidates)
            .map(|i| 0.3 + (i as f32) * (0.8 / (max_candidates as f32 - 1.0).max(1.0)))
            .collect();

        let models: Vec<ModelConfig> = temps.iter().enumerate()
            .map(|(i, &t)| {
                println!("  {}. Sample #{} (T={:.2})", i + 1, i + 1, t);
                ModelConfig::huggingface_with_temp(&best.model_id, t, i + 1)
            })
            .collect();

        // Fallback: remaining candidates from DB as different models
        let fallback: Vec<_> = res.all_candidates.iter().skip(1).cloned().collect();
        (models, fallback)
    } else {
        // Multi-model: N different models (original behavior)
        let fetch_pool_size = max_candidates * 3;
        let res = selector.select_best_model(panel_task, prompt, strategy, fetch_pool_size)
            .context("⚠️ [FUSION] Model selection failed from database.")?;
            
        if res.all_candidates.is_empty() {
            return Err(anyhow::anyhow!("⚠️ [FUSION] No candidates found in database for task '{}'.", panel_task));
        }
        
        let primary: Vec<_> = res.all_candidates.iter().take(max_candidates).cloned().collect();
        let fallback: Vec<_> = res.all_candidates.iter().skip(max_candidates).cloned().collect();

        if primary.len() < max_candidates {
            println!("⚠️ [FUSION] Requested {} panel models, but only {} fit in available memory. Automatically reduced panel size.",
                max_candidates, primary.len());
        }

        println!("📋 [FUSION] Model selection successful (detected task: '{}', selected strategy: {}).", detected_task, res.strategy);
        println!("📋 [FUSION] Primary panel ({}/{} models):", primary.len(), max_candidates);
        for (i, candidate) in primary.iter().enumerate() {
            if candidate.estimated_params_b > 0.0 {
                println!("  {}. {} (score: {:.2}, ~{:.1}B params, ~{:.1} GB RAM)",
                    i + 1, candidate.model_id, candidate.final_score,
                    candidate.estimated_params_b, candidate.estimated_memory_gb);
            } else {
                println!("  {}. {} (score: {:.2})", i + 1, candidate.model_id, candidate.final_score);
            }
        }
        if !fallback.is_empty() {
            println!("📋 [FUSION] Fallback pool: {} additional models available", fallback.len());
        }

        let models: Vec<ModelConfig> = primary.iter()
            .map(|c| ModelConfig::huggingface(&c.model_id))
            .collect();
        (models, fallback)
    };

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
    let mode_label = if is_multi_sample { "samples" } else { "models" };
    println!("[FUSION] Step 1: Running Panel of {} {} ...", panel_models.len(), mode_label);
    let mut panel_answers = run_panel(&prompt_with_context, panel_models.clone()).await?;
    
    // Dynamic fallback: replace failed models with fallback candidates
    let mut fallback_iter = fallback_pool.iter();
    let mut retry_count = 0;
    loop {
        let failed_indices: Vec<usize> = panel_answers.iter().enumerate()
            .filter(|(_, ans)| ans.answer.starts_with("MODEL ERROR"))
            .map(|(i, _)| i)
            .collect();

        if failed_indices.is_empty() || retry_count >= fallback_pool.len() {
            break;
        }

        for idx in &failed_indices {
            if let Some(fallback_candidate) = fallback_iter.next() {
                // Extract the error reason from the failed answer
                let error_reason = panel_answers[*idx].answer
                    .strip_prefix("MODEL ERROR: ")
                    .unwrap_or(&panel_answers[*idx].answer);
                // Truncate long errors to keep output readable
                let short_reason = if error_reason.len() > 200 {
                    format!("{}...", &error_reason[..200])
                } else {
                    error_reason.to_string()
                };
                println!("  ❌ [FAILED] '{}' — Reason: {}", panel_answers[*idx].model_name, short_reason);
                println!("  🔄 [FALLBACK] Replacing with '{}'", fallback_candidate.model_id);
                let fallback_config = ModelConfig::huggingface(&fallback_candidate.model_id);
                let replacement_answers = run_panel(&prompt_with_context, vec![fallback_config]).await?;
                if let Some(replacement) = replacement_answers.into_iter().next() {
                    panel_answers[*idx] = replacement;
                }
                retry_count += 1;
            } else {
                break;
            }
        }

        // Check if we still have failures and have fallbacks left
        let remaining_failures = panel_answers.iter().filter(|a| a.answer.starts_with("MODEL ERROR")).count();
        if remaining_failures == 0 || fallback_iter.len() == 0 {
            break;
        }
    }

    for ans in &panel_answers {
        println!("  * Received response from {}", ans.model_name);
        if ans.answer.starts_with("MODEL ERROR") {
            println!("    [WARN] Warning: {}", ans.answer);
        }
    }

    // Count successful responses
    let success_count = panel_answers.iter().filter(|a| !a.answer.starts_with("MODEL ERROR")).count();
    println!("[FUSION] Panel complete: {}/{} models responded successfully.", success_count, panel_answers.len());

    if success_count == 0 {
        return Err(anyhow::anyhow!("⚠️ [FUSION] All panel models failed. No responses to judge."));
    }

    println!("[FUSION] Step 2: Judging panel responses...");
    let judge_json = judge_panel(&prompt_with_context, &panel_answers, &judge_model).await?;

    println!("[FUSION] Step 3: Writing final synthesized answer...");
    let final_answer = write_final_answer(&prompt_with_context, &judge_json, &writer_model).await?;

    Ok(final_answer)
}
