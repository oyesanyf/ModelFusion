use crate::fusion_engine::schema::{ModelConfig, ModelAnswer};
use crate::fusion_engine::models::call_model;
use futures::future::join_all;

pub async fn run_panel(
    prompt: &str,
    models: Vec<ModelConfig>,
) -> anyhow::Result<Vec<ModelAnswer>> {
    let is_local = std::env::var("MODELFUSION_USE_TRANSFORMERS").is_ok()
        || std::env::var("MODELFUSION_USE_OLLAMA").is_ok()
        || std::env::var("MODELFUSION_USE_OPENVINO").is_ok();

    if is_local {
        // Batched execution for local backends: run as many models concurrently
        // as can fit in available memory, then move to the next batch.
        let batch_size = calculate_batch_size(&models);
        println!("  [PANEL] Running {} models in batches of {} (memory-optimized)", models.len(), batch_size);

        let mut all_results = Vec::with_capacity(models.len());
        for (batch_idx, batch) in models.chunks(batch_size).enumerate() {
            let batch_num = batch_idx + 1;
            let total_batches = (models.len() + batch_size - 1) / batch_size;
            println!("  [BATCH {}/{}] Running {} models concurrently...", batch_num, total_batches, batch.len());

            if batch.len() == 1 {
                // Single model — run directly, no spawn overhead
                let model = &batch[0];
                let answer = call_model(model, prompt).await;
                all_results.push(ModelAnswer {
                    model_name: model.name.clone(),
                    answer: answer.unwrap_or_else(|e| format!("MODEL ERROR: {e}")),
                });
            } else {
                // Multiple models — run concurrently within the batch
                let tasks: Vec<_> = batch.iter().map(|model| {
                    let prompt = prompt.to_string();
                    let model = model.clone();
                    async move {
                        let answer = call_model(&model, &prompt).await;
                        ModelAnswer {
                            model_name: model.name.clone(),
                            answer: answer.unwrap_or_else(|e| format!("MODEL ERROR: {e}")),
                        }
                    }
                }).collect();
                let batch_results = join_all(tasks).await;
                all_results.extend(batch_results);
            }
        }
        Ok(all_results)
    } else {
        // Full concurrent execution for remote API backends (HuggingFace, OpenAI, etc.)
        let tasks = models.into_iter().map(|model| {
            let prompt = prompt.to_string();
            async move {
                let answer = call_model(&model, &prompt).await;
                ModelAnswer {
                    model_name: model.name.clone(),
                    answer: answer.unwrap_or_else(|e| format!("MODEL ERROR: {e}")),
                }
            }
        });
        let results = join_all(tasks).await;
        Ok(results)
    }
}

/// Calculate how many models can run concurrently based on available memory.
/// For Ollama: Ollama manages its own memory, but we still batch to avoid
/// overwhelming the server. For Transformers: each model loads into RAM/VRAM.
fn calculate_batch_size(models: &[ModelConfig]) -> usize {
    // Check if the user has explicitly requested a batch size override
    if let Ok(val) = std::env::var("MODELFUSION_BATCH_SIZE") {
        if let Ok(parsed) = val.parse::<usize>() {
            return parsed.max(1).min(models.len());
        }
    }

    // Default to sequential (batch size = 1) for all local execution backends
    // to prevent GPU timeout driver crashes (Windows TDR), OOM, and extreme system lag.
    1
}
