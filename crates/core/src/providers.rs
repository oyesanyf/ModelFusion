#![allow(dead_code)]
//! LLM providers implementation.

use anyhow::{bail, Result};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::{Duration, Instant};

/// Locate a Python script relative to the executable, searching up to 5 parent directories.
fn find_script(relative_path: &str) -> String {
    // Search upward from the exe directory
    if let Ok(mut exe_path) = std::env::current_exe() {
        exe_path.pop(); // strip the exe filename → get the containing dir
        let mut check_dir = exe_path;
        for _ in 0..5 {
            let script = check_dir.join(relative_path);
            if script.exists() {
                return script.to_string_lossy().into_owned();
            }
            if !check_dir.pop() { break; }
        }
    }
    // Also search upward from the current working directory
    if let Ok(mut cwd) = std::env::current_dir() {
        for _ in 0..5 {
            let script = cwd.join(relative_path);
            if script.exists() {
                return script.to_string_lossy().into_owned();
            }
            if !cwd.pop() { break; }
        }
    }
    relative_path.to_string()
}

static INIT_PYTHON: std::sync::Once = std::sync::Once::new();

fn ensure_python_packages() {
    INIT_PYTHON.call_once(|| {
        println!("🔷 Checking Python multimodal dependencies...");
        
        let py_check = std::process::Command::new("python")
            .arg("-c")
            .arg("import sys; print(sys.version)")
            .output();
            
        if py_check.is_err() {
            println!("⚠️ [WARNING] 'python' command not found. Please install Python to run local models.");
            return;
        }

        let check = std::process::Command::new("python")
            .arg("-c")
            .arg("import importlib.util; ok = all(importlib.util.find_spec(p) is not None for p in ['torch', 'transformers', 'accelerate', 'PIL', 'soundfile', 'librosa', 'pypdf']); print('OK' if ok else 'FAIL')")
            .output();

        let needs_install = match check {
            Ok(out) => {
                let out_str = String::from_utf8_lossy(&out.stdout).trim().to_string();
                out_str != "OK"
            }
            Err(_) => true,
        };

        if needs_install {
            println!("📥 [AUTO-INSTALL] Installing/updating missing local Python dependencies (this may take a few minutes)...");
            let install_status = std::process::Command::new("python")
                .args(["-m", "pip", "install", "torch", "transformers", "accelerate", "pillow", "soundfile", "librosa", "pypdf", "--quiet"])
                .status();
                
            match install_status {
                Ok(status) if status.success() => {
                    println!("✅ [AUTO-INSTALL] Dependencies installed successfully!");
                }
                _ => {
                    println!("⚠️ [AUTO-INSTALL] Automatic installation failed. Please run manually: pip install torch transformers accelerate pillow soundfile librosa pypdf");
                }
            }
        } else {
            println!("✅ Local Python multimodal dependencies are fully satisfied.");
        }
    });
}

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
            model_id: "HuggingFaceTB/SmolLM2-135M-Instruct".to_string(),
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
            .timeout(Duration::from_secs(config.timeout_seconds.min(10)))
            .danger_accept_invalid_certs(true)
            .build()
            .unwrap_or_default();
        let hf_token = std::env::var("HF_TOKEN")
            .or_else(|_| std::env::var("HUGGINGFACE_API_KEY"))
            .or_else(|_| std::env::var("HF_API_KEY"))
            .or_else(|_| std::env::var("HUGGINGFACE_TOKEN"))
            .ok()
            .filter(|t| {
                !t.is_empty() && !t.contains("YOUR_")
            });
        Self { config, client, hf_token }
    }

    async fn execute_openvino(&self, prompt: &str, start: &Instant) -> Result<ProviderResult> {
        let script_path = find_script("src/scripts/run_model_openvino.py");
        let ov_model_dir = std::env::var("MODELFUSION_OV_MODEL_DIR")
            .unwrap_or_else(|_| "ov_models".to_string());
        let weight_format = std::env::var("MODELFUSION_OV_WEIGHT_FORMAT")
            .unwrap_or_else(|_| "int8".to_string());

        let timeout_duration = std::time::Duration::from_secs(self.config.timeout_seconds.max(900));
        let output = tokio::time::timeout(
            timeout_duration,
            tokio::process::Command::new("python")
                .env("PYTHONIOENCODING", "utf-8")
                .arg(&script_path)
                .arg(&self.config.model_id)
                .arg(prompt)
                .arg(self.config.max_tokens.to_string())
                .arg(self.config.temperature.to_string())
                .arg(&ov_model_dir)
                .arg(&weight_format)
                .kill_on_drop(true)
                .output()
        ).await;

        match output {
            Ok(Ok(out)) => {
                if out.status.success() {
                    let content = String::from_utf8_lossy(&out.stdout).trim().to_string();
                    let tokens_used = prompt.split_whitespace().count() + content.split_whitespace().count();
                    Ok(ProviderResult {
                        content,
                        tokens_used,
                        cost: 0.0,
                        latency_ms: start.elapsed().as_millis() as f64,
                        answer_type: "OPENVINO_ANSWER".to_string(),
                    })
                } else {
                    let err_msg = String::from_utf8_lossy(&out.stderr).trim().to_string();
                    bail!("OpenVINO execution failed: {}", err_msg);
                }
            }
            Ok(Err(e)) => bail!("Failed to start OpenVINO script: {}", e),
            Err(_) => bail!("OpenVINO execution timed out after {} seconds", timeout_duration.as_secs()),
        }
    }

    async fn execute_onnx(&self, prompt: &str, start: &Instant) -> Result<ProviderResult> {
        ensure_python_packages();
        let script_path = find_script("src/scripts/run_model_onnx.py");
        let device_arg = {
            let sys_mem = model_selection::memory::SystemMemory::detect();
            let estimated_params_b = model_selection::memory::estimate_params_billions(&self.config.model_id).unwrap_or(0.0);
            let estimated_memory_gb = model_selection::memory::estimate_runtime_memory_gb(estimated_params_b, model_selection::memory::Backend::Transformers);
            let device = sys_mem.best_device_for_model(estimated_memory_gb);
            device.to_string()
        };

        let timeout_duration = std::time::Duration::from_secs(self.config.timeout_seconds.max(600));
        let output = tokio::time::timeout(
            timeout_duration,
            tokio::process::Command::new("python")
                .env("PYTHONIOENCODING", "utf-8")
                .arg(&script_path)
                .arg(&self.config.model_id)
                .arg(prompt)
                .arg(self.config.max_tokens.to_string())
                .arg(self.config.temperature.to_string())
                .arg(device_arg)
                .kill_on_drop(true)
                .output()
        ).await;

        match output {
            Ok(Ok(out)) => {
                if out.status.success() {
                    let content = String::from_utf8_lossy(&out.stdout).trim().to_string();
                    let tokens_used = prompt.split_whitespace().count() + content.split_whitespace().count();
                    Ok(ProviderResult {
                        content,
                        tokens_used,
                        cost: 0.0,
                        latency_ms: start.elapsed().as_millis() as f64,
                        answer_type: "ONNX_ANSWER".to_string(),
                    })
                } else {
                    let err_msg = String::from_utf8_lossy(&out.stderr).trim().to_string();
                    bail!("ONNX execution failed: {}", err_msg);
                }
            }
            Ok(Err(e)) => bail!("Failed to start ONNX script: {}", e),
            Err(_) => bail!("ONNX execution timed out after {} seconds", timeout_duration.as_secs()),
        }
    }

    async fn execute_transformers(&self, prompt: &str, start: &Instant) -> Result<ProviderResult> {
        ensure_python_packages();
        let script_path = find_script("src/scripts/run_model_transformers.py");
        let device_arg = {
            let sys_mem = model_selection::memory::SystemMemory::detect();
            let estimated_params_b = model_selection::memory::estimate_params_billions(&self.config.model_id).unwrap_or(0.0);
            let estimated_memory_gb = model_selection::memory::estimate_runtime_memory_gb(estimated_params_b, model_selection::memory::Backend::Transformers);
            let device = sys_mem.best_device_for_model(estimated_memory_gb);
            device.to_string()
        };

        let timeout_duration = std::time::Duration::from_secs(self.config.timeout_seconds.max(300));
        let output = tokio::time::timeout(
            timeout_duration,
            tokio::process::Command::new("python")
                .env("PYTHONIOENCODING", "utf-8")
                .arg(&script_path)
                .arg(&self.config.model_id)
                .arg(prompt)
                .arg(self.config.max_tokens.to_string())
                .arg(self.config.temperature.to_string())
                .arg(device_arg)
                .kill_on_drop(true)
                .output()
        ).await;

        match output {
            Ok(Ok(out)) => {
                if out.status.success() {
                    let content = String::from_utf8_lossy(&out.stdout).trim().to_string();
                    let tokens_used = prompt.split_whitespace().count() + content.split_whitespace().count();
                    Ok(ProviderResult {
                        content,
                        tokens_used,
                        cost: 0.0,
                        latency_ms: start.elapsed().as_millis() as f64,
                        answer_type: "LOCAL_TRANSFORMERS_ANSWER".to_string(),
                    })
                } else {
                    let err_msg = String::from_utf8_lossy(&out.stderr).trim().to_string();
                    bail!("Transformers execution failed: {}", err_msg);
                }
            }
            Ok(Err(e)) => bail!("Failed to start Transformers script: {}", e),
            Err(_) => bail!("Transformers execution timed out after {} seconds", timeout_duration.as_secs()),
        }
    }

    async fn execute_ollama(&self, prompt: &str, start: &Instant) -> Result<ProviderResult> {
        let ollama_model = map_hf_to_ollama(&self.config.model_id);
        let endpoint = std::env::var("LOCAL_OLLAMA_ENDPOINT")
            .unwrap_or_else(|_| "http://127.0.0.1:11434".to_string());
        
        let url = format!("{}/api/chat", endpoint.trim_end_matches('/'));
        let mut messages = Vec::new();
        if prompt.contains("You are an expert judge model") {
            messages.push(serde_json::json!({
                "role": "system",
                "content": "You are an expert judge model. Return a valid JSON object ONLY."
            }));
        } else if prompt.contains("Use the judge analysis below") {
            messages.push(serde_json::json!({
                "role": "system",
                "content": "You are a professional synthesizer. Write a comprehensive final answer."
            }));
        }
        messages.push(serde_json::json!({
            "role": "user",
            "content": prompt
        }));

        let body = serde_json::json!({
            "model": ollama_model,
            "messages": messages,
            "stream": false,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens
            }
        });

        let client = reqwest::Client::builder()
            .no_proxy()
            .connect_timeout(std::time::Duration::from_secs(3))
            .timeout(std::time::Duration::from_secs(300))
            .build()?;

        let res = client.post(&url).json(&body).send().await?;
        if res.status().is_success() {
            let data: serde_json::Value = res.json().await?;
            let content = data["message"]["content"]
                .as_str()
                .unwrap_or_default()
                .to_string();
            let tokens_used = prompt.split_whitespace().count() + content.split_whitespace().count();
            Ok(ProviderResult {
                content,
                tokens_used,
                cost: 0.0,
                latency_ms: start.elapsed().as_millis() as f64,
                answer_type: "OLLAMA_ANSWER".to_string(),
            })
        } else {
            let err_text = res.text().await.unwrap_or_default();
            bail!("Ollama error: {}", err_text);
        }
    }
}

#[async_trait::async_trait]
impl LLMProvider for HuggingFaceProvider {
    fn config(&self) -> &ModelConfig {
        &self.config
    }

    async fn generate_response(&self, prompt: &str) -> Result<ProviderResult> {
        let start = Instant::now();

        // If any of the local backend environment variables are set, or if we are executing a local fallback
        let is_local = std::env::var("MODELFUSION_USE_OPENVINO").is_ok()
            || std::env::var("MODELFUSION_USE_ONNX").is_ok()
            || std::env::var("MODELFUSION_USE_TRANSFORMERS").is_ok()
            || std::env::var("MODELFUSION_USE_OLLAMA").is_ok();

        if is_local {
            let mut errors = Vec::new();

            // 1. Try Ollama first (fastest local provider)
            match self.execute_ollama(prompt, &start).await {
                Ok(res) => return Ok(res),
                Err(e) => {
                    let err_msg = format!("Ollama failed: {}", e);
                    log::warn!("⚠️ {}", err_msg);
                    errors.push(err_msg);
                }
            }

            // 2. Try OpenVINO next
            if std::env::var("MODELFUSION_USE_OPENVINO").is_ok() {
                match self.execute_openvino(prompt, &start).await {
                    Ok(res) => return Ok(res),
                    Err(e) => {
                        let err_msg = format!("OpenVINO failed: {}", e);
                        log::warn!("⚠️ {}", err_msg);
                        errors.push(err_msg);
                    }
                }
            }

            // 3. Try ONNX Runtime next
            if std::env::var("MODELFUSION_USE_ONNX").is_ok() || std::env::var("MODELFUSION_USE_OPENVINO").is_ok() {
                match self.execute_onnx(prompt, &start).await {
                    Ok(res) => return Ok(res),
                    Err(e) => {
                        let err_msg = format!("ONNX Runtime failed: {}", e);
                        log::warn!("⚠️ {}", err_msg);
                        errors.push(err_msg);
                    }
                }
            }

            // 4. Try Python Transformers next
            if std::env::var("MODELFUSION_USE_TRANSFORMERS").is_ok() 
                || std::env::var("MODELFUSION_USE_OPENVINO").is_ok() 
                || std::env::var("MODELFUSION_USE_ONNX").is_ok() 
            {
                match self.execute_transformers(prompt, &start).await {
                    Ok(res) => return Ok(res),
                    Err(e) => {
                        let err_msg = format!("Python Transformers failed: {}", e);
                        log::warn!("⚠️ {}", err_msg);
                        errors.push(err_msg);
                    }
                }
            }

            bail!(
                "All local backends failed for model {}. Execution errors: {:?}",
                self.config.model_id,
                errors
            );
        }

        // 1. Try Hugging Face Serverless Inference API
        // 1. Try Hugging Face Serverless Inference API
        if let Some(token) = &self.hf_token {
            let model_id_lower = self.config.model_id.to_lowercase();
            // Heuristic to check if the model is a chat/instruction model that supports OpenAI-compatible chat API
            let is_chat_model = (model_id_lower.contains("instruct") 
                || model_id_lower.contains("chat") 
                || model_id_lower.contains("llama")
                || model_id_lower.contains("qwen")
                || model_id_lower.contains("gemma")
                || model_id_lower.contains("phi")
                || model_id_lower.contains("deepseek")
                || model_id_lower.contains("mistral")
                || model_id_lower.contains("mixtral")
                || model_id_lower.contains("qtsumm")
                || model_id_lower.contains("summary")
                || model_id_lower.contains("summarization"))
                && !model_id_lower.contains("bert")
                && !model_id_lower.contains("t5")
                && !model_id_lower.contains("whisper")
                && !model_id_lower.contains("bart");

            let (clean_prompt, images, _audio) = extract_media_from_prompt(prompt);

            let response = if is_chat_model {
                let url = format!(
                    "https://router.huggingface.co/hf-inference/models/{}/v1/chat/completions",
                    self.config.model_id
                );
                let mut messages = Vec::new();
                if clean_prompt.contains("You are an expert judge model") {
                    messages.push(serde_json::json!({
                        "role": "system",
                        "content": "You are an expert judge model evaluating and comparing multiple assistant responses. You MUST return a valid JSON object ONLY. Do not write a markdown introduction, explanations, or conversational text. Follow the requested schema exactly."
                    }));
                } else if clean_prompt.contains("Use the judge analysis below") {
                    messages.push(serde_json::json!({
                        "role": "system",
                        "content": "You are a professional synthesizer and writer. Use the judge analysis to write the final answer. Prioritize consensus, mention uncertainty, and do not pretend disagreement is resolved."
                    }));
                }
                
                let user_content = if images.is_empty() {
                    serde_json::json!(prompt)
                } else {
                    let mut content_parts = Vec::new();
                    content_parts.push(serde_json::json!({
                        "type": "text",
                        "text": clean_prompt
                    }));
                    for img_b64 in &images {
                        content_parts.push(serde_json::json!({
                            "type": "image_url",
                            "image_url": {
                                "url": format!("data:image/png;base64,{}", img_b64)
                            }
                        }));
                    }
                    serde_json::json!(content_parts)
                };

                messages.push(serde_json::json!({
                    "role": "user",
                    "content": user_content
                }));

                let body = serde_json::json!({
                    "model": self.config.model_id,
                    "messages": messages,
                    "max_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature
                });

                self.client.post(&url)
                    .bearer_auth(token)
                    .json(&body)
                    .send()
                    .await
            } else {
                // Standard task pipeline endpoint (e.g. for summarization, translation, classification)
                let url = format!(
                    "https://router.huggingface.co/hf-inference/models/{}",
                    self.config.model_id
                );
                let body = serde_json::json!({
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": self.config.max_tokens,
                        "temperature": self.config.temperature.max(0.1)
                    }
                });

                self.client.post(&url)
                    .bearer_auth(token)
                    .json(&body)
                    .send()
                    .await
            };

            match response {
                Ok(res) => {
                    let status = res.status();
                    if status.is_success() {
                        let data: serde_json::Value = res.json().await?;
                        let mut content = String::new();

                        if is_chat_model {
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
                        } else {
                            // Parse standard Inference API array output: [{"summary_text": "..."}, ...] or [{"generated_text": "..."}]
                            if let Some(arr) = data.as_array() {
                                if let Some(first) = arr.get(0) {
                                    if let Some(text) = first.get("summary_text").and_then(|v| v.as_str()) {
                                        content = text.to_string();
                                    } else if let Some(text) = first.get("translation_text").and_then(|v| v.as_str()) {
                                        content = text.to_string();
                                    } else if let Some(text) = first.get("generated_text").and_then(|v| v.as_str()) {
                                        content = text.to_string();
                                    } else if let Some(text) = first.get("text").and_then(|v| v.as_str()) {
                                        content = text.to_string();
                                    }
                                }
                            } else if let Some(obj) = data.as_object() {
                                if let Some(text) = obj.get("summary_text").and_then(|v| v.as_str()) {
                                    content = text.to_string();
                                } else if let Some(text) = obj.get("generated_text").and_then(|v| v.as_str()) {
                                    content = text.to_string();
                                }
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
                        eprintln!("⚠️ [REMOTE FAILURE] HuggingFace API returned status {} for model {}. Details: {}. Falling back to local offline execution...", status, self.config.model_id, err_body);
                        std::env::set_var("MODELFUSION_USE_TRANSFORMERS", "1");
                        let local_provider = HuggingFaceProvider::new(self.config.clone());
                        return local_provider.generate_response(prompt).await;
                    }
                }
                Err(e) => {
                    eprintln!("⚠️ [CONNECTION ERROR] HuggingFace API is unreachable for model {}: {}. Falling back to local offline execution...", self.config.model_id, e);
                    std::env::set_var("MODELFUSION_USE_TRANSFORMERS", "1");
                    let local_provider = HuggingFaceProvider::new(self.config.clone());
                    return local_provider.generate_response(prompt).await;
                }
            }
        } else {
            eprintln!("⚠️ [TOKEN MISSING] HuggingFace API token is missing. Falling back to local offline execution...");
            std::env::set_var("MODELFUSION_USE_TRANSFORMERS", "1");
            let local_provider = HuggingFaceProvider::new(self.config.clone());
            return local_provider.generate_response(prompt).await;
        }
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
            .no_proxy()
            .connect_timeout(Duration::from_secs(3))
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
            .unwrap_or_else(|_| "http://127.0.0.1:11434".to_string());
        let url = format!("{}/api/generate", endpoint.trim_end_matches('/'));

        let (clean_prompt, images, _audio) = extract_media_from_prompt(prompt);

        let mut body = serde_json::json!({
            "model": self.config.model_id,
            "prompt": clean_prompt,
            "stream": false,
            "options": {
                "temperature": self.config.temperature
            }
        });

        if !images.is_empty() {
            body["images"] = serde_json::json!(images);
        }

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
                if std::env::var("MODELFUSION_NO_SIMULATION").is_ok() {
                    bail!("Local Ollama API call failed for model {}: {}", self.config.model_id, e);
                }
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

/// Maps HuggingFace model IDs to their Ollama equivalents.
pub fn map_hf_to_ollama(hf_model_id: &str) -> String {
    let id = hf_model_id.to_lowercase();
    match id.as_str() {
        // Qwen family
        _ if id.contains("qwen2") && id.contains("72b") => "qwen2.5:72b".to_string(),
        _ if id.contains("qwen2") && id.contains("32b") => "qwen2.5:32b".to_string(),
        _ if id.contains("qwen2") && id.contains("14b") => "qwen2.5:14b".to_string(),
        _ if id.contains("qwen2") && id.contains("7b") => "qwen2.5:7b".to_string(),
        _ if id.contains("qwen2") && id.contains("3b") => "qwen2.5:3b".to_string(),
        _ if id.contains("qwen2") && id.contains("1.5b") => "qwen2.5:1.5b".to_string(),
        _ if id.contains("qwen2") && id.contains("0.5b") => "qwen2.5:0.5b".to_string(),
        _ if id.contains("qwen2.5-coder") && id.contains("7b") => "qwen2.5-coder:7b".to_string(),
        _ if id.contains("qwen3") && id.contains("8b") => "qwen3:8b".to_string(),
        _ if id.contains("qwen3") && id.contains("4b") => "qwen3:4b".to_string(),
        _ if id.contains("qwen3") && id.contains("1.7b") => "qwen3:1.7b".to_string(),
        _ if id.contains("qwen3") && id.contains("0.6b") => "qwen3:0.6b".to_string(),

        // Llama family
        _ if id.contains("llama-3.1") && id.contains("70b") => "llama3.1:70b".to_string(),
        _ if id.contains("llama-3.1") && id.contains("8b") => "llama3.1".to_string(),
        _ if id.contains("llama-3.2") && id.contains("3b") => "llama3.2:3b".to_string(),
        _ if id.contains("llama-3.2") && id.contains("1b") => "llama3.2:1b".to_string(),
        _ if id.contains("llama-3.3") && id.contains("70b") => "llama3.3:70b".to_string(),

        // DeepSeek family
        _ if id.contains("deepseek-r1-distill") && id.contains("qwen-1.5b") => "deepseek-r1:1.5b".to_string(),
        _ if id.contains("deepseek-r1-distill") && id.contains("qwen-7b") => "deepseek-r1:7b".to_string(),
        _ if id.contains("deepseek-r1-distill") && id.contains("qwen-14b") => "deepseek-r1:14b".to_string(),
        _ if id.contains("deepseek-r1-distill") && id.contains("qwen-32b") => "deepseek-r1:32b".to_string(),
        _ if id.contains("deepseek-r1-distill") && id.contains("llama-8b") => "deepseek-r1:8b".to_string(),
        _ if id.contains("deepseek-r1-distill") && id.contains("llama-70b") => "deepseek-r1:70b".to_string(),

        // Gemma family
        _ if id.contains("gemma-2") && id.contains("2b") => "gemma2:2b".to_string(),
        _ if id.contains("gemma-2") && id.contains("9b") => "gemma2:9b".to_string(),
        _ if id.contains("gemma-2") && id.contains("27b") => "gemma2:27b".to_string(),
        _ if id.contains("gemma-3") && id.contains("4b") => "gemma3:4b".to_string(),
        _ if id.contains("gemma-3") && id.contains("12b") => "gemma3:12b".to_string(),
        _ if id.contains("gemma-3") && id.contains("27b") => "gemma3:27b".to_string(),

        // Phi family
        _ if id.contains("phi-3") && id.contains("mini") => "phi3:mini".to_string(),
        _ if id.contains("phi-4") && id.contains("mini") => "phi4-mini".to_string(),

        // Mistral family
        _ if id.contains("mistral") && id.contains("7b") => "mistral:7b".to_string(),
        _ if id.contains("mixtral") && id.contains("8x7b") => "mixtral:8x7b".to_string(),

        // Fallback: unrecognized HuggingFace models don't exist in Ollama.
        // Use the smallest available model as a safe default.
        _ => {
            log::warn!("No Ollama equivalent for '{}', falling back to qwen2.5:1.5b", hf_model_id);
            "qwen2.5:1.5b".to_string()
        }
    }
}

/// List of HuggingFace model ID substrings that are known to have Ollama equivalents
/// and are small enough to run locally.
pub const OLLAMA_COMPATIBLE_MODELS: &[&str] = &[
    "Qwen2.5-7B-Instruct",
    "Qwen2.5-3B-Instruct",
    "Qwen2.5-1.5B-Instruct",
    "Qwen2.5-0.5B-Instruct",
    "Qwen2.5-14B-Instruct",
    "Qwen2.5-Coder-7B-Instruct",
    "Qwen3-8B",
    "Qwen3-4B",
    "Qwen3-1.7B",
    "Llama-3.1-8B-Instruct",
    "Llama-3.2-3B-Instruct",
    "Llama-3.2-1B-Instruct",
    "DeepSeek-R1-Distill-Qwen-1.5B",
    "DeepSeek-R1-Distill-Qwen-7B",
    "DeepSeek-R1-Distill-Qwen-14B",
    "DeepSeek-R1-Distill-Qwen-32B",
    "DeepSeek-R1-Distill-Llama-8B",
    "gemma-2-2b-it",
    "gemma-2-9b-it",
    "gemma-3-4b-it",
    "gemma-3-12b-it",
    "Phi-3-mini-4k-instruct",
    "Phi-4-mini-instruct",
    "Mistral-7B-Instruct",
    "Mixtral-8x7B-Instruct",
];

/// Returns true if a model ID is known to be available in Ollama.
pub fn is_ollama_compatible(model_id: &str) -> bool {
    OLLAMA_COMPATIBLE_MODELS.iter().any(|m| model_id.contains(m))
}

pub fn extract_media_from_prompt(prompt: &str) -> (String, Vec<String>, Vec<String>) {
    let mut clean_prompt = String::new();
    let mut images = Vec::new();
    let mut audio_clips = Vec::new();
    
    let mut current_pos = 0;
    while current_pos < prompt.len() {
        let remaining_str = &prompt[current_pos..];
        let img_start = remaining_str.find("[IMAGE:");
        let aud_start = remaining_str.find("[AUDIO:");
        
        match (img_start, aud_start) {
            (Some(i_idx), Some(a_idx)) => {
                if i_idx < a_idx {
                    // Process image first
                    let abs_start = current_pos + i_idx;
                    clean_prompt.push_str(&prompt[current_pos..abs_start]);
                    let remaining = &prompt[abs_start + 7..];
                    if let Some(end_idx) = remaining.find(']') {
                        images.push(remaining[..end_idx].to_string());
                        current_pos = abs_start + 7 + end_idx + 1;
                    } else {
                        clean_prompt.push_str(&prompt[abs_start..]);
                        current_pos = prompt.len();
                    }
                } else {
                    // Process audio first
                    let abs_start = current_pos + a_idx;
                    clean_prompt.push_str(&prompt[current_pos..abs_start]);
                    let remaining = &prompt[abs_start + 7..];
                    if let Some(end_idx) = remaining.find(']') {
                        audio_clips.push(remaining[..end_idx].to_string());
                        current_pos = abs_start + 7 + end_idx + 1;
                    } else {
                        clean_prompt.push_str(&prompt[abs_start..]);
                        current_pos = prompt.len();
                    }
                }
            }
            (Some(i_idx), None) => {
                let abs_start = current_pos + i_idx;
                clean_prompt.push_str(&prompt[current_pos..abs_start]);
                let remaining = &prompt[abs_start + 7..];
                if let Some(end_idx) = remaining.find(']') {
                    images.push(remaining[..end_idx].to_string());
                    current_pos = abs_start + 7 + end_idx + 1;
                } else {
                    clean_prompt.push_str(&prompt[abs_start..]);
                    current_pos = prompt.len();
                }
            }
            (None, Some(a_idx)) => {
                let abs_start = current_pos + a_idx;
                clean_prompt.push_str(&prompt[current_pos..abs_start]);
                let remaining = &prompt[abs_start + 7..];
                if let Some(end_idx) = remaining.find(']') {
                    audio_clips.push(remaining[..end_idx].to_string());
                    current_pos = abs_start + 7 + end_idx + 1;
                } else {
                    clean_prompt.push_str(&prompt[abs_start..]);
                    current_pos = prompt.len();
                }
            }
            (None, None) => {
                clean_prompt.push_str(remaining_str);
                break;
            }
        }
    }
    
    (clean_prompt, images, audio_clips)
}
