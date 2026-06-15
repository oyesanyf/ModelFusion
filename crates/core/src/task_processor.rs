//! Universal task processor.

use crate::providers::{create_provider, LLMProvider, ModelConfig, ProviderResult};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;
use std::sync::Mutex;
use std::time::Instant;

/// Result of a task processing operation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskResult {
    pub content: String,
    pub tokens_used: usize,
    pub cost: f64,
    pub latency_ms: f64,
    pub model_used: String,
    pub status: String,
    pub error_message: Option<String>,
}

/// Task configuration descriptor.
#[derive(Debug, Clone)]
pub struct TaskConfig {
    pub description: String,
    pub default_model: String,
    pub max_tokens: usize,
    pub temperature: f64,
}

/// Universal processor for all AI tasks.
pub struct UniversalTaskProcessor {
    providers: Mutex<HashMap<String, Box<dyn LLMProvider>>>,
    task_configs: HashMap<String, TaskConfig>,
}

impl Default for UniversalTaskProcessor {
    fn default() -> Self {
        Self::new()
    }
}

impl UniversalTaskProcessor {
    /// Create a new task processor.
    pub fn new() -> Self {
        let mut task_configs = HashMap::new();

        task_configs.insert(
            "text-generation".to_string(),
            TaskConfig {
                description: "Generate text based on a prompt".to_string(),
                default_model: "gpt-3.5-turbo".to_string(),
                max_tokens: 1000,
                temperature: 1.0,
            },
        );
        task_configs.insert(
            "text-classification".to_string(),
            TaskConfig {
                description: "Classify text into categories".to_string(),
                default_model: "gpt-3.5-turbo".to_string(),
                max_tokens: 200,
                temperature: 0.1,
            },
        );
        task_configs.insert(
            "summarization".to_string(),
            TaskConfig {
                description: "Summarize long text".to_string(),
                default_model: "gpt-3.5-turbo".to_string(),
                max_tokens: 500,
                temperature: 0.3,
            },
        );
        task_configs.insert(
            "translation".to_string(),
            TaskConfig {
                description: "Translate text between languages".to_string(),
                default_model: "gpt-3.5-turbo".to_string(),
                max_tokens: 1000,
                temperature: 0.3,
            },
        );
        task_configs.insert(
            "question-answering".to_string(),
            TaskConfig {
                description: "Answer questions based on context".to_string(),
                default_model: "gpt-3.5-turbo".to_string(),
                max_tokens: 500,
                temperature: 0.3,
            },
        );
        task_configs.insert(
            "sentiment-analysis".to_string(),
            TaskConfig {
                description: "Analyze sentiment of text".to_string(),
                default_model: "gpt-3.5-turbo".to_string(),
                max_tokens: 100,
                temperature: 0.1,
            },
        );
        task_configs.insert(
            "ner".to_string(),
            TaskConfig {
                description: "Named Entity Recognition".to_string(),
                default_model: "gpt-3.5-turbo".to_string(),
                max_tokens: 300,
                temperature: 0.1,
            },
        );

        // Security Tasks
        task_configs.insert(
            "spam-detection".to_string(),
            TaskConfig {
                description: "Detect spam content".to_string(),
                default_model: "gpt-3.5-turbo".to_string(),
                max_tokens: 100,
                temperature: 0.1,
            },
        );
        task_configs.insert(
            "malware-detection".to_string(),
            TaskConfig {
                description: "Detect malicious content".to_string(),
                default_model: "gpt-3.5-turbo".to_string(),
                max_tokens: 200,
                temperature: 0.1,
            },
        );
        task_configs.insert(
            "pii-detection".to_string(),
            TaskConfig {
                description: "Detect personally identifiable information".to_string(),
                default_model: "gpt-3.5-turbo".to_string(),
                max_tokens: 300,
                temperature: 0.1,
            },
        );

        Self {
            providers: Mutex::new(HashMap::new()),
            task_configs,
        }
    }

    /// Process a task with options.
    pub async fn process_task(
        &self,
        task_name: &str,
        prompt: &str,
        model_id: Option<&str>,
        max_tokens_override: Option<usize>,
        temperature_override: Option<f64>,
        options: HashMap<String, String>,
    ) -> TaskResult {
        let start = Instant::now();
        let normalized_task = task_name.trim().to_lowercase().replace('_', "-");
        let lookup_name = match normalized_task.as_str() {
            "text-analysis" | "text_analysis" => "text-classification",
            other => other,
        };

        let task_config = match self.task_configs.get(lookup_name) {
            Some(cfg) => cfg.clone(),
            None => {
                return TaskResult {
                    content: format!("Unknown task: {}", task_name),
                    tokens_used: 0,
                    cost: 0.0,
                    latency_ms: start.elapsed().as_millis() as f64,
                    model_used: "unknown".to_string(),
                    status: "error".to_string(),
                    error_message: Some(format!("Task '{}' not supported", task_name)),
                }
            }
        };

        let final_model_id = model_id.unwrap_or(&task_config.default_model).to_string();

        let mut providers = self.providers.lock().unwrap();
        let provider = if let Some(p) = providers.get(&final_model_id) {
            p
        } else {
            let api_provider = self.determine_api_provider(&final_model_id);
            let cost_per_1k = self.get_cost_for_model(&final_model_id);
            let config = ModelConfig {
                name: final_model_id.clone(),
                api_provider,
                model_id: final_model_id.clone(),
                max_tokens: max_tokens_override.unwrap_or(task_config.max_tokens),
                temperature: temperature_override.unwrap_or(task_config.temperature),
                cost_per_1k_tokens: cost_per_1k,
                rate_limit_per_minute: 100,
                timeout_seconds: 30,
            };
            let p = create_provider(config);
            providers.insert(final_model_id.clone(), p);
            providers.get(&final_model_id).unwrap()
        };

        let formatted_prompt = self.format_prompt_for_task(lookup_name, prompt, &options);

        match provider.generate_response(&formatted_prompt).await {
            Ok(ProviderResult {
                content,
                tokens_used,
                cost,
                latency_ms,
                ..
            }) => TaskResult {
                content,
                tokens_used,
                cost,
                latency_ms,
                model_used: final_model_id,
                status: "success".to_string(),
                error_message: None,
            },
            Err(e) => TaskResult {
                content: format!("Error: {}", e),
                tokens_used: 0,
                cost: 0.0,
                latency_ms: start.elapsed().as_millis() as f64,
                model_used: final_model_id,
                status: "error".to_string(),
                error_message: Some(e.to_string()),
            },
        }
    }

    /// Process a file based task (text parsing, mock image/audio visual).
    pub async fn process_file_analysis(
        &self,
        file_path: &Path,
        task_name: &str,
        prompt: &str,
        model_id: Option<&str>,
        options: HashMap<String, String>,
    ) -> TaskResult {
        let start = Instant::now();
        if !file_path.exists() {
            return TaskResult {
                content: format!("File not found: {}", file_path.display()),
                tokens_used: 0,
                cost: 0.0,
                latency_ms: 0.0,
                model_used: "unknown".to_string(),
                status: "error".to_string(),
                error_message: Some(format!("File not found: {}", file_path.display())),
            };
        }

        let ext = file_path
            .extension()
            .and_then(|s| s.to_str())
            .unwrap_or("")
            .to_lowercase();

        match ext.as_str() {
            "jpg" | "jpeg" | "png" | "gif" | "bmp" | "webp" => {
                let image_prompt = format!("Analyze this image: {}\n\n{}", file_path.display(), prompt);
                self.process_task(task_name, &image_prompt, model_id, None, None, options).await
            }
            "mp3" | "wav" | "m4a" | "flac" => {
                let audio_prompt = format!("Analyze this audio file: {}\n\n{}", file_path.display(), prompt);
                self.process_task(task_name, &audio_prompt, model_id, None, None, options).await
            }
            "txt" | "md" | "py" | "js" | "html" | "css" | "rs" => {
                match std::fs::read_to_string(file_path) {
                    Ok(content) => {
                        let combined_prompt = format!("File content:\n{}\n\n{}", content, prompt);
                        self.process_task(task_name, &combined_prompt, model_id, None, None, options).await
                    }
                    Err(e) => TaskResult {
                        content: format!("Error reading file: {}", e),
                        tokens_used: 0,
                        cost: 0.0,
                        latency_ms: start.elapsed().as_millis() as f64,
                        model_used: "unknown".to_string(),
                        status: "error".to_string(),
                        error_message: Some(e.to_string()),
                    },
                }
            }
            _ => TaskResult {
                content: format!("Unsupported file extension: {}", ext),
                tokens_used: 0,
                cost: 0.0,
                latency_ms: 0.0,
                model_used: "unknown".to_string(),
                status: "error".to_string(),
                error_message: Some(format!("Unsupported file extension: {}", ext)),
            },
        }
    }

    fn determine_api_provider(&self, model_id: &str) -> String {
        let lower = model_id.to_lowercase();
        if lower.starts_with("gpt-") || lower.starts_with("whisper-") {
            "openai".to_string()
        } else if lower.starts_with("claude-") {
            "anthropic".to_string()
        } else if lower.starts_with("gemini-") {
            "gemini".to_string()
        } else {
            "huggingface".to_string()
        }
    }

    fn get_cost_for_model(&self, model_id: &str) -> f64 {
        let lower = model_id.to_lowercase();
        if lower == "gpt-5-mini" || lower == "gpt-5-mini-vision" {
            0.03
        } else if lower == "gpt-3.5-turbo" {
            0.002
        } else if lower.starts_with("whisper-") {
            0.006
        } else if lower.starts_with("claude-3") {
            0.015
        } else if lower.starts_with("claude-2") {
            0.008
        } else if lower.starts_with("gemini-pro") {
            0.00125
        } else {
            0.0 // HuggingFace is free
        }
    }

    fn format_prompt_for_task(
        &self,
        task_name: &str,
        prompt: &str,
        options: &HashMap<String, String>,
    ) -> String {
        match task_name {
            "text-classification" => {
                let categories = options
                    .get("categories")
                    .cloned()
                    .unwrap_or_else(|| "positive, negative, neutral".to_string());
                format!(
                    "Classify the following text into one of these categories: {}\n\nText: {}\n\nCategory:",
                    categories, prompt
                )
            }
            "summarization" => {
                format!("Summarize the following text in a concise way:\n\n{}\n\nSummary:", prompt)
            }
            "translation" => {
                let target_lang = options
                    .get("target_language")
                    .cloned()
                    .unwrap_or_else(|| "English".to_string());
                format!("Translate the following text to {}:\n\n{}\n\nTranslation:", target_lang, prompt)
            }
            "question-answering" => {
                if let Some(context) = options.get("context") {
                    format!("Context: {}\n\nQuestion: {}\n\nAnswer:", context, prompt)
                } else {
                    format!("Answer the following question: {}", prompt)
                }
            }
            "sentiment-analysis" => {
                format!(
                    "Analyze the sentiment of the following text. Respond with only: positive, negative, or neutral.\n\nText: {}\n\nSentiment:",
                    prompt
                )
            }
            "ner" => {
                format!(
                    "Extract named entities from the following text. For each entity, specify the type (PERSON, ORGANIZATION, LOCATION, etc.):\n\n{}\n\nEntities:",
                    prompt
                )
            }
            "spam-detection" => {
                format!(
                    "Determine if the following text is spam or legitimate. Respond with only: spam or legitimate.\n\nText: {}\n\nClassification:",
                    prompt
                )
            }
            "malware-detection" => {
                format!(
                    "Analyze the following content for potential malware or malicious intent. Respond with only: malicious or safe.\n\nContent: {}\n\nAnalysis:",
                    prompt
                )
            }
            "pii-detection" => {
                format!(
                    "Identify any personally identifiable information (PII) in the following text. List each piece of PII and its type (email, phone, address, etc.):\n\n{}\n\nPII Found:",
                    prompt
                )
            }
            _ => prompt.to_string(),
        }
    }
}
