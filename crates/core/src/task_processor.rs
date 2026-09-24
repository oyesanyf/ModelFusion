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
    providers: Mutex<HashMap<String, std::sync::Arc<dyn LLMProvider>>>,
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
                default_model: "meta-llama/Llama-3.1-8B-Instruct".to_string(),
                max_tokens: 1000,
                temperature: 1.0,
            },
        );
        task_configs.insert(
            "text-classification".to_string(),
            TaskConfig {
                description: "Classify text into categories".to_string(),
                default_model: "meta-llama/Llama-3.1-8B-Instruct".to_string(),
                max_tokens: 200,
                temperature: 0.1,
            },
        );
        task_configs.insert(
            "summarization".to_string(),
            TaskConfig {
                description: "Summarize long text".to_string(),
                default_model: "meta-llama/Llama-3.1-8B-Instruct".to_string(),
                max_tokens: 500,
                temperature: 0.3,
            },
        );
        task_configs.insert(
            "translation".to_string(),
            TaskConfig {
                description: "Translate text between languages".to_string(),
                default_model: "meta-llama/Llama-3.1-8B-Instruct".to_string(),
                max_tokens: 1000,
                temperature: 0.3,
            },
        );
        task_configs.insert(
            "question-answering".to_string(),
            TaskConfig {
                description: "Answer questions based on context".to_string(),
                default_model: "meta-llama/Llama-3.1-8B-Instruct".to_string(),
                max_tokens: 500,
                temperature: 0.3,
            },
        );
        task_configs.insert(
            "sentiment-analysis".to_string(),
            TaskConfig {
                description: "Analyze sentiment of text".to_string(),
                default_model: "meta-llama/Llama-3.1-8B-Instruct".to_string(),
                max_tokens: 100,
                temperature: 0.1,
            },
        );
        task_configs.insert(
            "ner".to_string(),
            TaskConfig {
                description: "Named Entity Recognition".to_string(),
                default_model: "meta-llama/Llama-3.1-8B-Instruct".to_string(),
                max_tokens: 300,
                temperature: 0.1,
            },
        );
 
        // Security Tasks
        task_configs.insert(
            "spam-detection".to_string(),
            TaskConfig {
                description: "Detect spam content".to_string(),
                default_model: "meta-llama/Llama-3.1-8B-Instruct".to_string(),
                max_tokens: 100,
                temperature: 0.1,
            },
        );
        task_configs.insert(
            "malware-detection".to_string(),
            TaskConfig {
                description: "Detect malicious content".to_string(),
                default_model: "meta-llama/Llama-3.1-8B-Instruct".to_string(),
                max_tokens: 200,
                temperature: 0.1,
            },
        );
        task_configs.insert(
            "pii-detection".to_string(),
            TaskConfig {
                description: "Detect personally identifiable information".to_string(),
                default_model: "meta-llama/Llama-3.1-8B-Instruct".to_string(),
                max_tokens: 300,
                temperature: 0.1,
            },
        );

        // Code and Data Science Tasks
        task_configs.insert(
            "code-summary-generation".to_string(),
            TaskConfig {
                description: "Summarize, review, or transform code".to_string(),
                default_model: "meta-llama/Llama-3.1-8B-Instruct".to_string(),
                max_tokens: 1500,
                temperature: 0.2,
            },
        );
        task_configs.insert(
            "code-vulnerability-detection".to_string(),
            TaskConfig {
                description: "Detect security vulnerabilities in code".to_string(),
                default_model: "meta-llama/Llama-3.1-8B-Instruct".to_string(),
                max_tokens: 1000,
                temperature: 0.1,
            },
        );
        task_configs.insert(
            "code-generation".to_string(),
            TaskConfig {
                description: "Generate implementation code".to_string(),
                default_model: "meta-llama/Llama-3.1-8B-Instruct".to_string(),
                max_tokens: 2000,
                temperature: 0.2,
            },
        );
        task_configs.insert(
            "data-science".to_string(),
            TaskConfig {
                description: "Data science, statistical modeling, and machine learning pipelines".to_string(),
                default_model: "meta-llama/Llama-3.1-8B-Instruct".to_string(),
                max_tokens: 4096,
                temperature: 0.2,
            },
        );
        task_configs.insert(
            "data-analyst".to_string(),
            TaskConfig {
                description: "Data analytics, exploratory analysis, and visualization guidance".to_string(),
                default_model: "meta-llama/Llama-3.1-8B-Instruct".to_string(),
                max_tokens: 4096,
                temperature: 0.2,
            },
        );
        task_configs.insert(
            "table-question-answering".to_string(),
            TaskConfig {
                description: "Tabular data QA and schema reasoning".to_string(),
                default_model: "meta-llama/Llama-3.1-8B-Instruct".to_string(),
                max_tokens: 1000,
                temperature: 0.1,
            },
        );
        task_configs.insert(
            "feature-extraction".to_string(),
            TaskConfig {
                description: "Extract high-dimensional features and embeddings".to_string(),
                default_model: "meta-llama/Llama-3.1-8B-Instruct".to_string(),
                max_tokens: 500,
                temperature: 0.0,
            },
        );
        task_configs.insert(
            "token-classification".to_string(),
            TaskConfig {
                description: "Token-level entity and label classification".to_string(),
                default_model: "meta-llama/Llama-3.1-8B-Instruct".to_string(),
                max_tokens: 500,
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
            "code-analysis" | "code_analysis" => "code-summary-generation",
            "datascience" => "data-science",
            "dataanalyst" | "jupyter" => "data-analyst",
            other => other,
        };

        let task_config = self.task_configs.get(lookup_name).cloned().unwrap_or_else(|| {
            TaskConfig {
                description: format!("Dynamic execution for task {}", task_name),
                default_model: "meta-llama/Llama-3.1-8B-Instruct".to_string(),
                max_tokens: 1000,
                temperature: 0.7,
            }
        });

        let final_model_id = model_id.unwrap_or(&task_config.default_model).to_string();

        let provider = {
            let mut providers = self.providers.lock().unwrap();
            if let Some(p) = providers.get(&final_model_id) {
                p.clone()
            } else {
                let api_provider = self.determine_api_provider(&final_model_id);
                let cost_per_1k = self.get_cost_for_model(&final_model_id);
                let base_timeout = 30;
                let token_processing_time = prompt.len() as u64 / 40;
                let generation_time = max_tokens_override.unwrap_or(task_config.max_tokens) as u64 / 10;
                let adaptive_default = base_timeout + token_processing_time + generation_time;

                let custom_timeout = options.get("timeout")
                    .or_else(|| options.get("x-timeout"))
                    .and_then(|t| t.parse::<u64>().ok())
                    .or_else(|| std::env::var("MODELFUSION_TIMEOUT").ok().and_then(|t| t.parse::<u64>().ok()))
                    .unwrap_or(adaptive_default);

                let config = ModelConfig {
                    name: final_model_id.clone(),
                    api_provider,
                    model_id: final_model_id.clone(),
                    max_tokens: max_tokens_override.unwrap_or(task_config.max_tokens),
                    temperature: temperature_override.unwrap_or(task_config.temperature),
                    cost_per_1k_tokens: cost_per_1k,
                    rate_limit_per_minute: 100,
                    timeout_seconds: custom_timeout,
                };
                let p: std::sync::Arc<dyn LLMProvider> = std::sync::Arc::from(create_provider(config));
                providers.insert(final_model_id.clone(), p.clone());
                p
            }
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
            "jpg" | "jpeg" | "png" | "gif" | "bmp" | "webp" | "svg" => {
                let image_prompt = format!("Analyze this image: {}\n\n{}", file_path.display(), prompt);
                self.process_task(task_name, &image_prompt, model_id, None, None, options).await
            }
            "mp3" | "wav" | "m4a" | "flac" | "ogg" | "aac" => {
                let audio_prompt = format!("Analyze this audio file: {}\n\n{}", file_path.display(), prompt);
                self.process_task(task_name, &audio_prompt, model_id, None, None, options).await
            }
            _ => {
                match std::fs::read(file_path) {
                    Ok(bytes) => {
                        let content = format_file_content(file_path, &bytes);
                        let combined_prompt = format!("File ({}):\n{}\n\n{}", file_path.display(), content, prompt);
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
        } else if lower.contains(':') || lower.starts_with("ollama") || model_selection::memory::is_ollama_model_cached(&lower) {
            "local".to_string()
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
            "data-science" | "data-analyst" => {
                format!(
                    "You are an expert Chief Data Scientist, Statistician, and Senior Machine Learning Engineer.\n\
                    Perform an in-depth, rigorous, production-ready data science and machine learning analysis.\n\n\
                    CRITICAL REQUIREMENTS:\n\
                    1. Provide COMPLETE, fully functional, production-grade Python code with all necessary imports (pandas, numpy, scikit-learn, statsmodels, seaborn, matplotlib).\n\
                    2. Address dataset structure, repeated measures, and data leakage (e.g. use GroupKFold if subject/group IDs are present).\n\
                    3. Perform feature engineering, including categorical encodings, interaction terms, and baseline checks.\n\
                    4. Train and benchmark multiple predictive models (e.g. Baseline Linear/Mixed Models, Random Forest, Gradient Boosting).\n\
                    5. Evaluate with robust cross-validation, compute comprehensive metrics (RMSE, MAE, R-squared), and analyze feature importance.\n\
                    6. Conclude with clear mathematical and practical interpretations of the results. Never cut off or provide partial stubs.\n\n\
                    Dataset Context & Instructions:\n{}",
                    prompt
                )
            }
            _ => prompt.to_string(),
        }
    }
}

/// Helper to extract clean content/metadata from diverse file types (notebooks, parquet, excel, code, text)
pub fn format_file_content(file_path: &Path, bytes: &[u8]) -> String {
    let filename = file_path.file_name().and_then(|n| n.to_str()).unwrap_or("");
    let lower = filename.to_lowercase();
    let limit = bytes.len().min(256 * 1024);
    let slice = &bytes[..limit];

    if lower.ends_with(".ipynb") {
        if let Ok(val) = serde_json::from_slice::<serde_json::Value>(slice) {
            if let Some(cells) = val.get("cells").and_then(|c| c.as_array()) {
                let mut notebook_repr = format!("Jupyter Notebook: {} (Total cells: {})\n\n", filename, cells.len());
                for (idx, cell) in cells.iter().enumerate() {
                    let cell_type = cell.get("cell_type").and_then(|t| t.as_str()).unwrap_or("code");
                    let source = cell.get("source")
                        .map(|s| {
                            if let Some(arr) = s.as_array() {
                                arr.iter().filter_map(|l| l.as_str()).collect::<Vec<_>>().join("")
                            } else if let Some(st) = s.as_str() {
                                st.to_string()
                            } else {
                                String::new()
                            }
                        })
                        .unwrap_or_default();
                    if !source.trim().is_empty() {
                        notebook_repr.push_str(&format!("--- [Cell {} ({})] ---\n{}\n\n", idx + 1, cell_type, source.trim()));
                    }
                }
                return notebook_repr;
            }
        }
        return String::from_utf8_lossy(slice).to_string();
    }

    if lower.ends_with(".parquet") {
        let mut strings = Vec::new();
        let mut curr = String::new();
        for &b in slice {
            if b.is_ascii_graphic() || b == b' ' {
                curr.push(b as char);
            } else {
                if curr.len() >= 3 && !curr.chars().all(|c| c.is_ascii_punctuation()) {
                    strings.push(curr.clone());
                }
                curr.clear();
            }
        }
        if curr.len() >= 3 && !curr.chars().all(|c| c.is_ascii_punctuation()) {
            strings.push(curr);
        }
        let mut seen = std::collections::HashSet::new();
        let unique_strings: Vec<String> = strings.into_iter().filter(|s| seen.insert(s.clone())).take(60).collect();
        return format!("Parquet Dataset: {} (Size: {} bytes)\nSchema / Column Tokens Extracted:\n{}", filename, bytes.len(), unique_strings.join(", "));
    }

    if lower.ends_with(".xlsx") || lower.ends_with(".xls") {
        let mut strings = Vec::new();
        let mut curr = String::new();
        for &b in slice {
            if b.is_ascii_alphanumeric() || b == b'_' || b == b'-' || b == b'.' {
                curr.push(b as char);
            } else {
                if curr.len() >= 4 {
                    strings.push(curr.clone());
                }
                curr.clear();
            }
        }
        if curr.len() >= 4 {
            strings.push(curr);
        }
        let mut seen = std::collections::HashSet::new();
        let unique_strings: Vec<String> = strings.into_iter().filter(|s| seen.insert(s.clone())).take(60).collect();
        return format!("Excel Workbook: {} (Size: {} bytes)\nWorkbook / Sheet / Field Tokens Extracted:\n{}", filename, bytes.len(), unique_strings.join(", "));
    }

    String::from_utf8_lossy(slice).to_string()
}

