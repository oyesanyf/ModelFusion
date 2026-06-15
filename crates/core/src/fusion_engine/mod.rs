pub mod schema;
pub mod models;
pub mod fusion;
pub mod judge;

use schema::ModelConfig;
use fusion::run_panel;
use judge::{judge_panel, write_final_answer};

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
pub async fn run_fusion(prompt: &str) -> anyhow::Result<String> {
    // Define the 3 panel models (Gemma-2-2b-it and DeepSeek R1 distilled thinking models)
    let panel_models = vec![
        ModelConfig::huggingface("google/gemma-2-2b-it"),
        ModelConfig::huggingface("deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"),
        ModelConfig::huggingface("deepseek-ai/DeepSeek-R1-Distill-Llama-8B"),
    ];

    // Define the judge model (strong reasoning open-weights thinking model)
    let judge_model = ModelConfig::huggingface("deepseek-ai/DeepSeek-R1-Distill-Qwen-32B");

    // Define the final writer model
    let writer_model = ModelConfig::huggingface("deepseek-ai/DeepSeek-R1-Distill-Qwen-32B");

    println!("🤖 [FUSION] Starting Model Fusion Pipeline...");
    println!("📋 [FUSION] Step 1: Running Panel of 3 models concurrently...");
    let panel_answers = run_panel(prompt, panel_models).await?;
    
    for ans in &panel_answers {
        println!("  • Received response from {}", ans.model_name);
        if ans.answer.starts_with("MODEL ERROR") {
            println!("    ⚠️ Warning: {}", ans.answer);
        }
    }

    println!("⚖️  [FUSION] Step 2: Judging panel responses...");
    let judge_json = judge_panel(prompt, &panel_answers, &judge_model).await?;

    println!("✍️  [FUSION] Step 3: Writing final synthesized answer...");
    let final_answer = write_final_answer(prompt, &judge_json, &writer_model).await?;

    Ok(final_answer)
}
