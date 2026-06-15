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

    async fn generate_response(&self, prompt: &str) -> Result<ProviderResult> {
        let start = Instant::now();
        let api_key = self.api_key.as_ref()
            .context("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")?;

        let url = "https://api.openai.com/v1/chat/completions";
        let body = serde_json::json!({
            "model": self.config.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature
        });

        let response = self.client.post(url)
            .bearer_auth(api_key)
            .json(&body)
            .send()
            .await?;

        if !response.status().is_success() {
            let err_text = response.text().await.unwrap_or_default();
            bail!("OpenAI API error: {}", err_text);
        }

        let data: serde_json::Value = response.json().await?;
        let content = data["choices"][0]["message"]["content"]
            .as_str()
            .unwrap_or_default()
            .to_string();
        let tokens_used = data["usage"]["total_tokens"].as_u64().unwrap_or(0) as usize;
        let cost = (tokens_used as f64 / 1000.0) * self.config.cost_per_1k_tokens;

        Ok(ProviderResult {
            content,
            tokens_used,
            cost,
            latency_ms: start.elapsed().as_millis() as f64,
            answer_type: "FINAL_ANSWER".to_string(),
        })
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

    async fn generate_response(&self, prompt: &str) -> Result<ProviderResult> {
        let start = Instant::now();
        let api_key = self.api_key.as_ref()
            .context("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.")?;

        let url = "https://api.anthropic.com/v1/messages";
        let body = serde_json::json!({
            "model": self.config.model_id,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": [{"role": "user", "content": prompt}]
        });

        let response = self.client.post(url)
            .header("x-api-key", api_key)
            .header("anthropic-version", "2023-06-01")
            .json(&body)
            .send()
            .await?;

        if !response.status().is_success() {
            let err_text = response.text().await.unwrap_or_default();
            bail!("Anthropic API error: {}", err_text);
        }

        let data: serde_json::Value = response.json().await?;
        let content = data["content"][0]["text"]
            .as_str()
            .unwrap_or_default()
            .to_string();

        let input_tokens = data["usage"]["input_tokens"].as_u64().unwrap_or(0) as usize;
        let output_tokens = data["usage"]["output_tokens"].as_u64().unwrap_or(0) as usize;
        let tokens_used = input_tokens + output_tokens;
        let cost = (tokens_used as f64 / 1000.0) * self.config.cost_per_1k_tokens;

        Ok(ProviderResult {
            content,
            tokens_used,
            cost,
            latency_ms: start.elapsed().as_millis() as f64,
            answer_type: "FINAL_ANSWER".to_string(),
        })
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

    async fn generate_response(&self, prompt: &str) -> Result<ProviderResult> {
        let start = Instant::now();
        let api_key = self.api_key.as_ref()
            .context("Gemini API key not found. Set GOOGLE_GEMINI_API_KEY environment variable.")?;

        let url = format!(
            "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent?key={}",
            self.config.model_id, api_key
        );

        let body = serde_json::json!({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": self.config.max_tokens,
                "temperature": self.config.temperature
            }
        });

        let response = self.client.post(&url)
            .json(&body)
            .send()
            .await?;

        if !response.status().is_success() {
            let err_text = response.text().await.unwrap_or_default();
            bail!("Gemini API error: {}", err_text);
        }

        let data: serde_json::Value = response.json().await?;
        let content = data["candidates"][0]["content"]["parts"][0]["text"]
            .as_str()
            .unwrap_or_default()
            .to_string();

        // Estimate tokens
        let tokens_used = prompt.split_whitespace().count() + content.split_whitespace().count();
        let cost = (tokens_used as f64 / 1000.0) * self.config.cost_per_1k_tokens;

        Ok(ProviderResult {
            content,
            tokens_used,
            cost,
            latency_ms: start.elapsed().as_millis() as f64,
            answer_type: "FINAL_ANSWER".to_string(),
        })
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
        let hf_token = std::env::var("HUGGINGFACE_API_KEY")
            .or_else(|_| std::env::var("HF_TOKEN"))
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

        // 1. Try Hugging Face Inference API
        if let Some(token) = &self.hf_token {
            let url = format!("https://api-inference.huggingface.co/models/{}", self.config.model_id);
            let body = serde_json::json!({
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature,
                    "do_sample": true
                }
            });

            let response = self.client.post(&url)
                .bearer_auth(token)
                .json(&body)
                .send()
                .await;

            if let Ok(res) = response {
                if res.status().is_success() {
                    let data: serde_json::Value = res.json().await?;
                    let mut content = String::new();

                    if let Some(arr) = data.as_array() {
                        if !arr.is_empty() {
                            content = arr[0]["generated_text"].as_str().unwrap_or_default().to_string();
                        }
                    } else if let Some(obj) = data.as_object() {
                        content = obj.get("generated_text")
                            .and_then(|v| v.as_str())
                            .unwrap_or_default()
                            .to_string();
                    } else {
                        content = data.to_string();
                    }

                    // Remove input prompt if the model prepended it
                    if content.starts_with(prompt) {
                        content = content[prompt.len()..].trim().to_string();
                    }

                    let tokens_used = prompt.split_whitespace().count() + content.split_whitespace().count();
                    return Ok(ProviderResult {
                        content,
                        tokens_used,
                        cost: 0.0,
                        latency_ms: start.elapsed().as_millis() as f64,
                        answer_type: "FINAL_ANSWER".to_string(),
                    });
                }
            }
        }

        // 2. Local fallback / Offline mock
        log::warn!("HuggingFace Inference API unavailable or token missing. Using offline fallback.");
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
