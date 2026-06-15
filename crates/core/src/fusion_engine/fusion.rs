use crate::fusion_engine::schema::{ModelConfig, ModelAnswer};
use crate::fusion_engine::models::call_model;
use futures::future::join_all;

pub async fn run_panel(
    prompt: &str,
    models: Vec<ModelConfig>,
) -> anyhow::Result<Vec<ModelAnswer>> {
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
