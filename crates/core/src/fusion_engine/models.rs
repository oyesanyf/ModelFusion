use crate::fusion_engine::schema::{ModelConfig, Provider};
use crate::providers::{create_provider, ModelConfig as CoreModelConfig};

pub async fn call_model(model: &ModelConfig, prompt: &str) -> anyhow::Result<String> {
    let core_provider_str = match model.provider {
        Provider::OpenAI => "openai",
        Provider::Anthropic => "anthropic",
        Provider::Google => "gemini",
        Provider::Local => "local",
        Provider::HuggingFace => "huggingface",
    };

    let core_config = CoreModelConfig {
        name: model.name.clone(),
        api_provider: core_provider_str.to_string(),
        model_id: model.endpoint.clone(),
        max_tokens: 1500,
        temperature: 0.7,
        cost_per_1k_tokens: 0.0,
        rate_limit_per_minute: 60,
        timeout_seconds: 30,
    };

    let provider = create_provider(core_config);
    let result = provider.generate_response(prompt).await?;
    Ok(result.content)
}
