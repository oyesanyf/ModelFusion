pub mod schema;
pub mod models;
pub mod fusion;
pub mod judge;
pub mod skeletonizer;

use schema::ModelConfig;
use fusion::run_panel;
use judge::{judge_panel, write_final_answer};
use model_selection::{EnhancedModelSelector, SelectionStrategy};
use task_detection::IntelligentTaskDetector;
use std::path::Path;

/// Simple heuristic classifier to decide if prompt needs fusion.
pub fn classify_prompt(prompt: &str) -> bool {
    let lower = prompt.to_lowercase();

    // Bypass internal VS Code system welcome, handshake, and title generation prompts.
    // These are structurally long but do not benefit from consensus deliberation.
    if lower.contains("ultra-compact titles")
        || lower.contains("crafting ultra-compact titles")
        || lower.contains("github copilot by stating")
        || lower.contains("confirm that you are github copilot")
        || lower.contains("confirm that i am github copilot")
    {
        return false;
    }

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

    // Strip standard IDE system instruction headers to get the true user query word count
    let mut clean_prompt = lower;
    let system_headers = vec![
        "you are an expert ai programming assistant, working with a user in the vs code editor.",
        "you are an expert ai programming assistant, working with a user in the vs code editor",
        "you are an expert ai programming assistant, working with a user in the vs code window.",
        "you are an expert ai programming assistant, working with a user in the vs code window",
        "you are an expert ai programming assistant",
    ];
    for header in system_headers {
        if clean_prompt.starts_with(header) {
            clean_prompt = clean_prompt.replacen(header, "", 1);
        }
    }

    // Check word count (needs > 35 words in the actual user prompt)
    clean_prompt.split_whitespace().count() > 35
}

use anyhow::Context;

/// Return all model IDs from the database, ordered by decision_score.
/// Used by `--prepare-all-models` to batch-convert models.
pub fn get_all_model_ids(db_path: &Path) -> Vec<String> {
    match db::HuggingFaceModelDatabase::new(db_path) {
        Ok(db) => db.get_all_model_ids().unwrap_or_default(),
        Err(_) => Vec::new(),
    }
}

/// Return model IDs under a size threshold (in MB), ordered by decision_score.
/// Used by `--update` + `--prepare-all-models` to only convert small fast models.
pub fn get_small_model_ids(db_path: &Path, max_size_mb: f64) -> Vec<String> {
    match db::HuggingFaceModelDatabase::new(db_path) {
        Ok(db) => db.get_small_model_ids(max_size_mb).unwrap_or_default(),
        Err(_) => Vec::new(),
    }
}

/// Derive dynamic fusion model count based on live available runtime memory.
pub fn derive_fusion_model_count() -> usize {
    model_selection::memory::derive_fusion_model_count()
}

/// Truncate a long prompt only in the middle, NEVER at the end where the user's question lives.
/// Keeps the first 1,500 chars and the last 2,500 chars (`head + "\n...[middle truncated]...\n" + tail`),
/// and ensures any `<userRequest>` or `<prompt>` or text after `</attachments>`/`</context>` is placed at the VERY TOP.
pub fn preserve_head_and_tail_prompt(prompt: &str, max_chars: usize) -> String {
    let mut extracted_req = String::new();
    let lower = prompt.to_lowercase();
    for (open_tag, close_tag) in [
        ("<userrequest>", "</userrequest>"),
        ("<user_request>", "</user_request>"),
        ("<prompt>", "</prompt>"),
    ] {
        if let Some(s_idx) = lower.rfind(open_tag) {
            let content_start = s_idx + open_tag.len();
            if let Some(e_rel) = lower[content_start..].find(close_tag) {
                let candidate = prompt[content_start..content_start + e_rel].trim();
                if !candidate.is_empty() {
                    extracted_req = candidate.to_string();
                    break;
                }
            }
        }
    }
    if extracted_req.is_empty() {
        for close_tag in ["</attachments>", "</attachment>", "</context>"] {
            if let Some(idx) = lower.rfind(close_tag) {
                let after = prompt[idx + close_tag.len()..].trim();
                if !after.is_empty() && after.len() < 4000 {
                    extracted_req = after.to_string();
                    break;
                }
            }
        }
    }

    let base = if !extracted_req.is_empty() && !prompt.trim_start().starts_with("USER REQUEST:") {
        format!("USER REQUEST: {}\n\n{}", extracted_req, prompt)
    } else {
        prompt.to_string()
    };

    let char_count = base.chars().count();
    let limit = max_chars.max(4000);
    if char_count <= limit {
        return base;
    }
    let head_len = 1500;
    let tail_len = 2500;
    let head: String = base.chars().take(head_len).collect();
    let tail: String = base.chars().skip(char_count.saturating_sub(tail_len)).collect();
    format!("{}\n...[middle truncated]...\n{}", head, tail)
}

/// Helper to determine if a prompt or task is a coding task for Recursive Flint
/// (`RecursiveSI/flint` / `flint:latest` 40B total / 2.5B active MoE) + Block Goose Coding Fusion.
pub fn is_coding_task_for_flint(detected_task: &str, prompt: &str) -> bool {
    let task_lower = detected_task.to_lowercase();
    let prompt_lower = prompt.to_lowercase();

    // 1. Task-level detection
    if task_lower.contains("code")
        || task_lower.contains("security")
        || task_lower.contains("software")
        || task_lower.contains("programming")
        || task_lower.contains("flint")
        || task_lower.contains("goose")
        || task_lower.contains("raptor")
    {
        return true;
    }

    // 2. Direct Flint / Goose / RAPTOR / Coding directives
    if prompt_lower.contains("flint")
        || prompt_lower.contains("goose")
        || prompt_lower.contains("raptor")
        || prompt_lower.contains("@agent code-helper")
        || prompt_lower.contains("@code-helper")
        || prompt_lower.contains("@agent security")
        || prompt_lower.contains("@security")
        || prompt_lower.contains("@agent graph-index")
        || prompt_lower.contains("@graph")
        || prompt_lower.contains("@agent vuln-scan")
    {
        return true;
    }

    // 3. Explicit code constructs & file creation requests (including typos like wrie, javafile, javacode, dend)
    prompt_lower.contains("def ")
        || prompt_lower.contains("fn ")
        || prompt_lower.contains("function ")
        || prompt_lower.contains("class ")
        || prompt_lower.contains("import ")
        || prompt_lower.contains("struct ")
        || prompt_lower.contains("impl ")
        || prompt_lower.contains("```")
        || prompt_lower.contains("code")
        || prompt_lower.contains("javafile")
        || prompt_lower.contains("javacode")
        || prompt_lower.contains("pyfile")
        || prompt_lower.contains("java")
        || prompt_lower.contains("python")
        || prompt_lower.contains("rust")
        || prompt_lower.contains("javascript")
        || prompt_lower.contains("typescript")
        || prompt_lower.contains("golang")
        || prompt_lower.contains("c++")
        || prompt_lower.contains("c#")
        || prompt_lower.contains("html")
        || prompt_lower.contains("css")
        || prompt_lower.contains("sql")
        || prompt_lower.contains("openai")
        || prompt_lower.contains("file")
        || prompt_lower.contains("script")
        || prompt_lower.contains("program")
        || prompt_lower.contains("algorithm")
        || prompt_lower.contains("bug")
        || prompt_lower.contains("refactor")
        || prompt_lower.contains("debug")
        || prompt_lower.contains("swe-bench")
        || prompt_lower.contains("terminal-bench")
}

/// Run the model fusion pipeline.
pub async fn run_fusion(
    prompt: &str,
    context: Option<&str>,
    db_path: Option<&Path>,
    task_override: Option<&str>,
    strategy: Option<SelectionStrategy>,
    max_candidates: Option<usize>,
    fusion_mode: &str,
    forced_model: Option<&str>,
) -> anyhow::Result<String> {
    let db_path_ref = db_path.context("[FUSION] Database path is required and cannot be bypassed.")?;
 
    // Detect task name on the original prompt
    let detected_task = if let Some(t) = task_override {
        t.to_string()
    } else {
        let detector = IntelligentTaskDetector::new();
        let detection = detector.detect_task_type(prompt);
        eprintln!("🔍 [FUSION] Detected task: {} (confidence: {:.2})", detection.task_type, detection.confidence);
        detection.task_type
    };

    let strategy = strategy.unwrap_or(SelectionStrategy::MultiObjective);
    
    let selector = EnhancedModelSelector::new(db_path_ref)
        .context("⚠️ [FUSION] Failed to open database for model selection.")?;
        
    let forced_model = forced_model
        .map(|s| s.trim())
        .filter(|s| !s.is_empty() && *s != "modelfusion-local" && *s != "modelfusion" && *s != "auto" && *s != "default" && *s != "qwen2.5:1.5b");

    let max_candidates = match max_candidates {
        Some(n) if n > 1 => n,
        _ => derive_fusion_model_count(),
    }.max(2);
    eprintln!("⚡ [FUSION] Effective fusion panel model count: {}", max_candidates);

    if let Some(ref model_id) = forced_model {
        eprintln!("⚡ [FUSION] Forced model override active: using {}", model_id);
    }

    let is_multi_sample = fusion_mode == "multi-sample";

    // For multi-sample mode: select 1 best model, create N configs with different temperatures
    // For multi-model mode: select N different models (uses detected_task with text-generation fallback)
    let panel_task = detected_task.as_str();

    let (panel_models, fallback_pool) = if is_multi_sample {
        let (model_id, fallback) = if let Some(ref model_id) = forced_model {
            (model_id.to_string(), vec![])
        } else {
            let res = selector.select_best_model(panel_task, prompt, strategy, 3, None)
                .context("⚠️ [FUSION] Model selection failed from database.")?;
            if res.all_candidates.is_empty() {
                let cached = model_selection::memory::get_ollama_cached_models();
                if let Some(first_cached) = cached.first() {
                    (first_cached.clone(), vec![])
                } else {
                    return Err(anyhow::anyhow!("⚠️ [FUSION] No candidates found in database for task '{}'.", panel_task));
                }
            } else {
                let best = &res.best_model;
                eprintln!("📋 [FUSION] Selected model: {} (score: {:.2})", best.model_id, best.final_score);
                if best.estimated_params_b > 0.0 {
                    eprintln!("   ~{:.1}B params, ~{:.1} GB RAM", best.estimated_params_b, best.estimated_memory_gb);
                }
                let fb: Vec<_> = res.all_candidates.iter().skip(1).cloned().collect();
                (best.model_id.clone(), fb)
            }
        };

        eprintln!("⚡ [FUSION] Multi-sample mode: using 1 model with {} temperature variations", max_candidates);
        let temps: Vec<f32> = (0..max_candidates)
            .map(|i| 0.3 + (i as f32) * (0.8 / (max_candidates as f32 - 1.0).max(1.0)))
            .collect();

        let models: Vec<ModelConfig> = temps.iter().enumerate()
            .map(|(i, &t)| {
                eprintln!("  {}. Sample #{} (T={:.2})", i + 1, i + 1, t);
                ModelConfig::huggingface_with_temp(&model_id, t, i + 1)
            })
            .collect();
        (models, fallback)
    } else {
        // Multi-model: construct a panel of max_candidates models
        let mut panel_models: Vec<ModelConfig> = Vec::new();

        // 1. Default Recursive Flint (flint:latest / RecursiveSI/flint 40B-A2.5B MoE) + Block Goose in Fusion & Coding:
        // Always active by default for coding and fusion tasks (never blocked).
        let is_coding = is_coding_task_for_flint(&detected_task, prompt);
        let flint_eval = model_selection::memory::SystemMemory::detect_live().assess_flint_for_task(true, is_coding);
        eprintln!(
            "🔥 [FLINT + GOOSE DEFAULT FUSION] Resource Check: Free RAM {:.1} GB, Free VRAM {:.1} GB -> Tier: {} (Flint 40B-A2.5B Ready: {}, Ollama Cached: {})",
            flint_eval.detected_free_ram_gb,
            flint_eval.detected_free_vram_gb,
            flint_eval.active_tier,
            flint_eval.resources_available,
            flint_eval.ollama_cached
        );
        let mut flint_cfg = if flint_eval.ollama_cached {
            ModelConfig::local("flint:latest")
        } else {
            ModelConfig::huggingface("RecursiveSI/flint")
        };
        flint_cfg.temperature = Some(1.0);
        flint_cfg.name = format!(
            "Recursive Flint 40B-A2.5B MoE + Block Goose ({}, T=1.0)",
            if flint_eval.resources_available { "Full" } else { "Compact Q4" }
        );
        panel_models.push(flint_cfg);
        eprintln!(
            "🔥 [FLINT + GOOSE DEFAULT FUSION] Injected Recursive Flint (flint:latest) + Block Goose into Fusion Panel (Slot {})",
            panel_models.len()
        );

        // 1.25. Resource-Gated Z.ai GLM Specialist in Fusion:
        // Strictly activated ONLY when runtime resources are available (Free RAM >= 8.0 GB or Free VRAM >= 6.0 GB).
        let glm_eval = model_selection::memory::SystemMemory::detect_live().assess_glm_for_mode(true);
        if glm_eval.glm_activated_in_fusion && glm_eval.resources_available && panel_models.len() < max_candidates {
            let mut glm_cfg = if glm_eval.ollama_cached {
                ModelConfig::local(&glm_eval.ollama_tag)
            } else {
                ModelConfig::huggingface(&glm_eval.model_id)
            };
            glm_cfg.name = format!(
                "Z.ai GLM Specialist ({} — {})",
                glm_eval.ollama_tag, glm_eval.active_tier
            );
            panel_models.push(glm_cfg);
            eprintln!(
                "🧠 [GLM RESOURCE-GATED FUSION] Activated {} in Fusion Panel (Slot {}): {} | Quant: {} | Vision: {:?}",
                glm_eval.ollama_tag,
                panel_models.len(),
                glm_eval.status_reason,
                glm_eval.quantization_format,
                glm_eval.vision_variant_tag
            );
        } else {
            eprintln!(
                "🛡️ [GLM RESOURCE-GATED FUSION] Skipped GLM in Fusion Panel: {}",
                glm_eval.status_reason
            );
        }

        // 1.5. If forced_model is present and not already flint, add it next
        if let Some(ref model_id) = forced_model {
            if !panel_models.iter().any(|m| m.endpoint == *model_id || m.endpoint.contains("flint") && model_id.contains("flint")) {
                if model_selection::memory::is_ollama_model_cached(model_id) {
                    panel_models.push(ModelConfig::local(model_id));
                } else {
                    panel_models.push(ModelConfig::huggingface(model_id));
                }
            }
        }

        // 2. Query selector for candidates
        let fetch_pool_size = max_candidates * 3;
        let db_candidates_res = selector.select_best_model(panel_task, prompt, strategy, fetch_pool_size, None);

        let (db_candidates, mut leftover_db) = match db_candidates_res {
            Ok(res) => {
                eprintln!("📋 [FUSION] Model selection successful (detected task: '{}', selected strategy: {}).", detected_task, res.strategy);
                let mut cands = res.all_candidates;
                if let Some(ref model_id) = forced_model {
                    cands.retain(|c| &c.model_id != model_id);
                }
                (cands, vec![])
            }
            Err(e) => {
                eprintln!("⚠️ [FUSION] Warning querying candidates from database: {}", e);
                (vec![], vec![])
            }
        };

        // 3. Add database candidates to panel_models up to max_candidates
        let mut db_iter = db_candidates.into_iter();
        while panel_models.len() < max_candidates {
            if let Some(cand) = db_iter.next() {
                if !panel_models.iter().any(|m| m.endpoint == cand.model_id) {
                    panel_models.push(ModelConfig::huggingface(&cand.model_id));
                }
            } else {
                break;
            }
        }
        leftover_db.extend(db_iter);

        // 4. If panel_models.len() < max_candidates, check locally installed/cached models in Ollama
        if panel_models.len() < max_candidates {
            let cached = model_selection::memory::get_ollama_cached_models();
            for cm in cached {
                if panel_models.len() >= max_candidates {
                    break;
                }
                if !panel_models.iter().any(|m| m.endpoint == *cm || m.name.contains(cm.as_str())) {
                    panel_models.push(ModelConfig::local(&cm));
                }
            }
        }

        // 5. If panel_models is empty at this point, ensure we have at least one base candidate
        if panel_models.is_empty() {
            panel_models.push(ModelConfig::huggingface("qwen2.5:7b"));
        }

        // 6. If panel_models.len() < max_candidates, fill remaining slots with temperature variations of top candidate(s)
        if panel_models.len() < max_candidates {
            let base_models = panel_models.clone();
            let temp_steps = [0.3f32, 0.5, 0.7, 0.9, 0.4, 0.6, 0.8, 1.0];
            let mut step_idx = 0;
            while panel_models.len() < max_candidates {
                for base in &base_models {
                    if panel_models.len() >= max_candidates {
                        break;
                    }
                    let t = temp_steps[step_idx % temp_steps.len()];
                    step_idx += 1;
                    let sample_num = panel_models.len() + 1;
                    let mut var_config = base.clone();
                    var_config.temperature = Some(t);
                    var_config.name = format!("{} (var #{}, T={:.1})", base.name, sample_num, t);
                    panel_models.push(var_config);
                }
            }
        }

        eprintln!("📋 [FUSION] Primary panel ({}/{} models):", panel_models.len(), max_candidates);
        for (i, m) in panel_models.iter().enumerate() {
            eprintln!("  {}. {} (provider: {:?})", i + 1, m.name, m.provider);
        }
        if !leftover_db.is_empty() {
            eprintln!("📋 [FUSION] Fallback pool: {} additional models available", leftover_db.len());
        }

        (panel_models, leftover_db)
    };

    // Define the judge model
    let judge_model = if let Some(model_id) = forced_model {
        ModelConfig::huggingface(model_id)
    } else {
        let cached = model_selection::memory::get_ollama_cached_models();
        if let Some(m) = cached.iter().find(|m| m.contains("qwen") || m.contains("llama") || m.contains("deepseek") || m.contains("glm")) {
            ModelConfig::local(m)
        } else {
            let judge_res = selector.select_best_model("text-generation", "judge evaluation", strategy, 1, None)
                .context("⚠️ [FUSION] Failed to select judge model from database.")?;
            ModelConfig::huggingface(&judge_res.best_model.model_id)
        }
    };
    eprintln!("⚖️ [FUSION] Selected judge model: {}", judge_model.name);

    // Define the final writer model
    let writer_model = if let Some(model_id) = forced_model {
        ModelConfig::huggingface(model_id)
    } else {
        let cached = model_selection::memory::get_ollama_cached_models();
        if let Some(m) = cached.iter().find(|m| m.contains("qwen") || m.contains("llama") || m.contains("deepseek") || m.contains("glm")) {
            ModelConfig::local(m)
        } else {
            let writer_res = selector.select_best_model("text-generation", "final synthesis writing", strategy, 1, None)
                .context("⚠️ [FUSION] Failed to select writer model from database.")?;
            ModelConfig::huggingface(&writer_res.best_model.model_id)
        }
    };
    eprintln!("✍️ [FUSION] Selected writer model: {}", writer_model.name);

    let prompt_with_context = if let Some(ctx) = context {
        format!("{}\n\n### CONTEXT:\n{}", prompt, ctx)
    } else {
        let lower_prompt = prompt.to_lowercase();
        let has_workspace_keywords = lower_prompt.contains("workspace") 
            || lower_prompt.contains("whole folder") 
            || lower_prompt.contains("all files") 
            || lower_prompt.contains("in this project")
            || lower_prompt.contains("in the project");

        if has_workspace_keywords {
            eprintln!("📂 [FUSION] Workspace keywords detected. Compiling codebase skeleton map...");
            let skeletonizer = skeletonizer::WorkspaceSkeletonizer::new();
            let map = skeletonizer.build_skeleton_map(Path::new("d:\\harfile\\ModelFusion"), 12000);
            format!("{}\n\n{}", prompt, map)
        } else {
            prompt.to_string()
        }
    };

    eprintln!("[FUSION] Starting Model Fusion Pipeline...");
    let mode_label = if is_multi_sample { "samples" } else { "models" };
    eprintln!("[FUSION] Step 1: Running Panel of {} {} ...", panel_models.len(), mode_label);
    let prompt_with_context = preserve_head_and_tail_prompt(&prompt_with_context, 12000);
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
                eprintln!("  ❌ [FAILED] '{}' — Reason: {}", panel_answers[*idx].model_name, short_reason);
                eprintln!("  🔄 [FALLBACK] Replacing with '{}'", fallback_candidate.model_id);
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
        eprintln!("  * Received response from {}", ans.model_name);
        if ans.answer.starts_with("MODEL ERROR") {
            eprintln!("    [WARN] Warning: {}", ans.answer);
        }
    }

    // Count successful responses
    let success_count = panel_answers.iter().filter(|a| !a.answer.starts_with("MODEL ERROR")).count();
    eprintln!("[FUSION] Panel complete: {}/{} models responded successfully.", success_count, panel_answers.len());

    if success_count == 0 {
        return Err(anyhow::anyhow!("⚠️ [FUSION] All panel models failed. No responses to judge."));
    }

    eprintln!("[FUSION] Step 2: Judging panel responses...");
    let judge_json = judge_panel(&prompt_with_context, &panel_answers, &judge_model).await?;

    eprintln!("[FUSION] Step 3: Writing final synthesized answer...");
    let final_answer = write_final_answer(&prompt_with_context, &judge_json, &writer_model).await?;

    Ok(final_answer)
}

#[cfg(test)]
mod flint_fusion_tests {
    use super::*;

    #[test]
    fn test_is_coding_task_for_flint() {
        // Coding tasks -> True
        assert!(is_coding_task_for_flint("code-generation", "Implement binary search"));
        assert!(is_coding_task_for_flint("text-generation", "def calculate_primes(n):"));
        assert!(is_coding_task_for_flint("text-generation", "fn main() { println!(\"hello\"); }"));
        assert!(is_coding_task_for_flint("text-generation", "@agent flint-coding implement red-black tree"));
        assert!(is_coding_task_for_flint("text-generation", "@code-helper write a rust http server"));
        assert!(is_coding_task_for_flint("software-engineering", "fix memory leak in c++"));

        // Non-coding tasks -> False
        assert!(!is_coding_task_for_flint("text-generation", "Write an essay about the history of Nigeria"));
        assert!(!is_coding_task_for_flint("finance", "What is the market capitalization of Apple?"));
        assert!(!is_coding_task_for_flint("legal", "What are the essential clauses in a non-disclosure agreement?"));
        assert!(!is_coding_task_for_flint("translation", "Translate this paragraph into French"));
        assert!(!is_coding_task_for_flint("summarization", "Summarize this medical case report"));
        assert!(is_coding_task_for_flint("text-generation", "create a javafile that can be able to dend prompts to openai"));
        assert!(is_coding_task_for_flint("text-generation", "wrie javacode that can call open ai llm"));
    }

    #[test]
    fn test_preserve_head_and_tail_prompt() {
        let pqc_attachment = "import os\ndef pqc(): pass\n".repeat(1000);
        let raw = format!(
            "System: IDE Assistant\n<attachments>\n{}\n</attachments>\n<userRequest>create a javafile that can be able to dend prompts to openai</userRequest>",
            pqc_attachment
        );
        let preserved = preserve_head_and_tail_prompt(&raw, 4000);
        assert!(preserved.starts_with("USER REQUEST: create a javafile that can be able to dend prompts to openai"));
        assert!(preserved.contains("...[middle truncated]..."));
        assert!(preserved.ends_with("<userRequest>create a javafile that can be able to dend prompts to openai</userRequest>"));
    }
}
