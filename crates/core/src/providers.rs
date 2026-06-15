//! LLM providers implementation.

use anyhow::{bail, Context, Result};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::{Duration, Instant};

/// Configuration for an LLM model.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelConfig {
    pub name: String,
    pub api_provider: String,
    pub model_id: String,
    pub max_tokens: usize,
    pub temperature: f64,
    pub cost_per_1k_tokens: f64,
    pub rate_limit_per_minute: usize,
    pub timeout_seconds: u64,
}

impl Default for ModelConfig {
    fn default() -> Self {
        Self {
            name: "Default Model".to_string(),
            api_provider: "huggingface".to_string(),
            model_id: "gpt2".to_string(),
            max_tokens: 1000,
            temperature: 0.7,
            cost_per_1k_tokens: 0.0,
            rate_limit_per_minute: 100,
            timeout_seconds: 30,
        }
    }
}

/// The result returned by a provider execution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderResult {
    pub content: String,
    pub tokens_used: usize,
    pub cost: f64,
    pub latency_ms: f64,
    pub answer_type: String,
}

/// Common interface for all LLM providers.
#[async_trait::async_trait]
pub trait LLMProvider: Send + Sync {
    async fn generate_response(&self, prompt: &str) -> Result<ProviderResult>;
    fn config(&self) -> &ModelConfig;
}

// Factory to create provider instances
pub fn create_provider(config: ModelConfig) -> Box<dyn LLMProvider> {
    match config.api_provider.to_lowercase().as_str() {
        "openai" => Box::new(OpenAIProvider::new(config)),
        "anthropic" => Box::new(AnthropicProvider::new(config)),
        "gemini" => Box::new(GeminiProvider::new(config)),
        "local" => Box::new(LocalProvider::new(config)),
        _ => Box::new(HuggingFaceProvider::new(config)),
    }
}

// ==========================================
// OpenAI Provider
// ==========================================
pub struct OpenAIProvider {
    config: ModelConfig,
    client: Client,
    api_key: Option<String>,
}

impl OpenAIProvider {
    pub fn new(config: ModelConfig) -> Self {
        let client = Client::builder()
            .timeout(Duration::from_secs(config.timeout_seconds))
            .build()
            .unwrap_or_default();
        let api_key = std::env::var("OPENAI_API_KEY").ok();
        Self { config, client, api_key }
    }
}

#[async_trait::async_trait]
impl LLMProvider for OpenAIProvider {
    fn config(&self) -> &ModelConfig {
        &self.config
    }

    async fn generate_response(&self, _prompt: &str) -> Result<ProviderResult> {
        bail!("Paid models (OpenAI) are disabled and removed per system requirements.");
    }
}

// ==========================================
// Anthropic Provider
// ==========================================
pub struct AnthropicProvider {
    config: ModelConfig,
    client: Client,
    api_key: Option<String>,
}

impl AnthropicProvider {
    pub fn new(config: ModelConfig) -> Self {
        let client = Client::builder()
            .timeout(Duration::from_secs(config.timeout_seconds))
            .build()
            .unwrap_or_default();
        let api_key = std::env::var("ANTHROPIC_API_KEY").ok();
        Self { config, client, api_key }
    }
}

#[async_trait::async_trait]
impl LLMProvider for AnthropicProvider {
    fn config(&self) -> &ModelConfig {
        &self.config
    }

    async fn generate_response(&self, _prompt: &str) -> Result<ProviderResult> {
        bail!("Paid models (Anthropic) are disabled and removed per system requirements.");
    }
}

// ==========================================
// Gemini Provider
// ==========================================
pub struct GeminiProvider {
    config: ModelConfig,
    client: Client,
    api_key: Option<String>,
}

impl GeminiProvider {
    pub fn new(config: ModelConfig) -> Self {
        let client = Client::builder()
            .timeout(Duration::from_secs(config.timeout_seconds))
            .build()
            .unwrap_or_default();
        let api_key = std::env::var("GOOGLE_GEMINI_API_KEY").ok();
        Self { config, client, api_key }
    }
}

#[async_trait::async_trait]
impl LLMProvider for GeminiProvider {
    fn config(&self) -> &ModelConfig {
        &self.config
    }

    async fn generate_response(&self, _prompt: &str) -> Result<ProviderResult> {
        bail!("Paid models (Gemini) are disabled and removed per system requirements.");
    }
}

// ==========================================
// HuggingFace Provider
// ==========================================
pub struct HuggingFaceProvider {
    config: ModelConfig,
    client: Client,
    hf_token: Option<String>,
}

impl HuggingFaceProvider {
    pub fn new(config: ModelConfig) -> Self {
        let client = Client::builder()
            .timeout(Duration::from_secs(config.timeout_seconds))
            .build()
            .unwrap_or_default();
        let hf_token = std::env::var("HF_TOKEN")
            .or_else(|_| std::env::var("HUGGINGFACE_API_KEY"))
            .or_else(|_| std::env::var("HF_API_KEY"))
            .or_else(|_| std::env::var("HUGGINGFACE_TOKEN"))
            .ok();
        Self { config, client, hf_token }
    }
}

#[async_trait::async_trait]
impl LLMProvider for HuggingFaceProvider {
    fn config(&self) -> &ModelConfig {
        &self.config
    }

    async fn generate_response(&self, prompt: &str) -> Result<ProviderResult> {
        let start = Instant::now();

        // 1. Try Hugging Face Inference API via new router
        if let Some(token) = &self.hf_token {
            let url = "https://router.huggingface.co/v1/chat/completions";
            
            let mut messages = Vec::new();
            if prompt.contains("You are an expert judge model") {
                messages.push(serde_json::json!({
                    "role": "system",
                    "content": "You are an expert judge model evaluating and comparing multiple assistant responses. You MUST return a valid JSON object ONLY. Do not write a markdown introduction, explanations, or conversational text. Follow the requested schema exactly."
                }));
            } else if prompt.contains("Use the judge analysis below") {
                messages.push(serde_json::json!({
                    "role": "system",
                    "content": "You are a professional synthesizer and writer. Use the judge analysis to write the final answer. Prioritize consensus, mention uncertainty, and do not pretend disagreement is resolved."
                }));
            }
            
            messages.push(serde_json::json!({
                "role": "user",
                "content": prompt
            }));

            let body = serde_json::json!({
                "model": self.config.model_id,
                "messages": messages,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature
            });

            let response = self.client.post(url)
                .bearer_auth(token)
                .json(&body)
                .send()
                .await;

            match response {
                Ok(res) => {
                    let status = res.status();
                    if status.is_success() {
                        let data: serde_json::Value = res.json().await?;
                        let mut content = String::new();

                        if let Some(choice) = data["choices"].get(0) {
                            if let Some(msg) = choice.get("message") {
                                let reasoning = msg.get("reasoning_content")
                                    .and_then(|v| v.as_str())
                                    .unwrap_or("");
                                let body_content = msg.get("content")
                                    .and_then(|v| v.as_str())
                                    .unwrap_or("");

                                if !reasoning.is_empty() {
                                    content.push_str(&format!("<think>\n{}\n</think>\n", reasoning));
                                }
                                content.push_str(body_content);
                            }
                        }

                        let tokens_used = prompt.split_whitespace().count() + content.split_whitespace().count();
                        return Ok(ProviderResult {
                            content,
                            tokens_used,
                            cost: 0.0,
                            latency_ms: start.elapsed().as_millis() as f64,
                            answer_type: "FINAL_ANSWER".to_string(),
                        });
                    } else {
                        let err_body = res.text().await.unwrap_or_else(|_| "Unavailable".to_string());
                        log::warn!(
                            "HuggingFace Inference API returned status {} for model {}. Details: {}. Using offline fallback.",
                            status,
                            self.config.model_id,
                            err_body
                        );
                    }
                }
                Err(e) => {
                    log::warn!(
                        "HuggingFace Inference API request failed for model {}: {}. Using offline fallback.",
                        self.config.model_id,
                        e
                    );
                }
            }
        } else {
            log::warn!("HuggingFace API token is missing. Using offline fallback.");
        }

        // 2. Local fallback / Offline mock
        let fallback_content = format!(
            "[Offline Fallback for {}] This is a mock response because the HuggingFace API key is missing or the Inference API returned an error. Received prompt: \"{}\"",
            self.config.model_id, prompt
        );
        let tokens_used = prompt.split_whitespace().count() + fallback_content.split_whitespace().count();

        Ok(ProviderResult {
            content: fallback_content,
            tokens_used,
            cost: 0.0,
            latency_ms: start.elapsed().as_millis() as f64,
            answer_type: "MOCK_ANSWER".to_string(),
        })
    }
}

// ==========================================
// Local Provider (Ollama)
// ==========================================
pub struct LocalProvider {
    config: ModelConfig,
    client: Client,
}

impl LocalProvider {
    pub fn new(config: ModelConfig) -> Self {
        let client = Client::builder()
            .timeout(Duration::from_secs(config.timeout_seconds))
            .build()
            .unwrap_or_default();
        Self { config, client }
    }
}

#[async_trait::async_trait]
impl LLMProvider for LocalProvider {
    fn config(&self) -> &ModelConfig {
        &self.config
    }

    async fn generate_response(&self, prompt: &str) -> Result<ProviderResult> {
        let start = Instant::now();
        let endpoint = std::env::var("LOCAL_OLLAMA_ENDPOINT")
            .unwrap_or_else(|_| "http://localhost:11434".to_string());
        let url = format!("{}/api/generate", endpoint.trim_end_matches('/'));

        let body = serde_json::json!({
            "model": self.config.model_id,
            "prompt": prompt,
            "stream": false,
            "options": {
                "temperature": self.config.temperature
            }
        });

        let response = self.client.post(&url)
            .json(&body)
            .send()
            .await;

        match response {
            Ok(res) => {
                if res.status().is_success() {
                    let data: serde_json::Value = res.json().await?;
                    let content = data["response"].as_str().unwrap_or_default().to_string();
                    let tokens_used = prompt.split_whitespace().count() + content.split_whitespace().count();
                    
                    Ok(ProviderResult {
                        content,
                        tokens_used,
                        cost: 0.0,
                        latency_ms: start.elapsed().as_millis() as f64,
                        answer_type: "LOCAL_ANSWER".to_string(),
                    })
                } else {
                    let err_text = res.text().await.unwrap_or_default();
                    bail!("Local Ollama API error: {}", err_text);
                }
            }
            Err(e) => {
                log::warn!("Local Ollama API call failed: {}. Falling back to mock local response.", e);
                let mock_content = format!(
                    "[Local Fallback for {}] Ollama is not running at {}. Mock response for prompt: \"{}\"",
                    self.config.model_id, endpoint, prompt
                );
                let tokens_used = prompt.split_whitespace().count() + mock_content.split_whitespace().count();
                Ok(ProviderResult {
                    content: mock_content,
                    tokens_used,
                    cost: 0.0,
                    latency_ms: start.elapsed().as_millis() as f64,
                    answer_type: "LOCAL_MOCK_ANSWER".to_string(),
                })
            }
        }
    }
}
