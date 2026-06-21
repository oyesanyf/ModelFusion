//! Memory-aware model selection utilities.
//!
//! Dynamically detects system resources (RAM, VRAM) and estimates model
//! runtime memory to filter out models that cannot run on the current hardware.

use std::process::Command;

/// Detected system memory resources.
#[derive(Debug, Clone)]
pub struct SystemMemory {
    pub total_ram_gb: f64,
    pub free_ram_gb: f64,
    pub gpu_name: Option<String>,
    pub gpu_vram_total_gb: f64,
    pub gpu_vram_free_gb: f64,
}

/// Backend execution mode — determines quantization/precision.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Backend {
    Transformers, // FP16 — ~2 bytes per param
    Ollama,       // Q4_0 — ~0.6 bytes per param
    OpenVINO,     // INT4 — ~0.5 bytes per param (optimized CPU inference)
}

/// Safety margin: only use 70% of free memory for model loading.
const SAFETY_FACTOR: f64 = 0.70;

/// Execution device for a model.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Device {
    Gpu,
    Cpu,
}

impl std::fmt::Display for Device {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Device::Gpu => write!(f, "cuda"),
            Device::Cpu => write!(f, "cpu"),
        }
    }
}

impl SystemMemory {
    /// Dynamically detect available system resources.
    pub fn detect() -> Self {
        let (total_ram_gb, free_ram_gb) = detect_ram();
        let (gpu_name, gpu_vram_total_gb, gpu_vram_free_gb) = detect_gpu();

        SystemMemory {
            total_ram_gb,
            free_ram_gb,
            gpu_name,
            gpu_vram_total_gb,
            gpu_vram_free_gb,
        }
    }

    /// Whether a usable GPU is detected.
    pub fn has_usable_gpu(&self) -> bool {
        self.gpu_name.is_some() && self.gpu_vram_free_gb > 0.5
    }

    /// GPU VRAM budget (with safety margin).
    pub fn gpu_budget_gb(&self) -> f64 {
        // Subtract a 1.5 GB base VRAM buffer for the OS display and CUDA execution contexts,
        // then allocate a safety fraction (70%) of the remaining free memory.
        ((self.gpu_vram_free_gb - 1.5) * SAFETY_FACTOR).max(0.0)
    }

    /// CPU RAM budget (with safety margin).
    pub fn ram_budget_gb(&self) -> f64 {
        // Subtract a 3.0 GB base memory buffer for the python/pytorch runtime execution context overhead,
        // then allocate a safety fraction (70%) of the remaining free memory.
        ((self.free_ram_gb - 3.0) * SAFETY_FACTOR).max(0.0)
    }

    /// Maximum memory budget for a single model — uses GPU if available, otherwise RAM.
    /// For the overall filter, we use the LARGER of the two (models that fit in either can run).
    pub fn model_budget_gb(&self) -> f64 {
        // Models can run on EITHER device, so the max budget is the larger resource pool
        self.ram_budget_gb().max(self.gpu_budget_gb())
    }

    /// Determine the best device for a model of the given estimated memory size.
    /// Prefers GPU when the model fits in VRAM.
    pub fn best_device_for_model(&self, model_memory_gb: f64) -> Device {
        if self.has_usable_gpu() && model_memory_gb <= self.gpu_budget_gb() {
            Device::Gpu
        } else {
            Device::Cpu
        }
    }

    /// Print a summary of detected resources.
    pub fn print_summary(&self) {
        println!("💾 [MEMORY] System RAM: {:.1} GB total, {:.1} GB free (budget: {:.1} GB per model)",
            self.total_ram_gb, self.free_ram_gb, self.ram_budget_gb());
        if let Some(ref gpu) = self.gpu_name {
            println!("🎮 [MEMORY] GPU: {} — {:.1} GB total VRAM, {:.1} GB free (budget: {:.1} GB)",
                gpu, self.gpu_vram_total_gb, self.gpu_vram_free_gb, self.gpu_budget_gb());
        } else {
            println!("🎮 [MEMORY] GPU: Not detected (CPU-only execution)");
        }
    }
}

/// Detect total and free system RAM (Windows).
fn detect_ram() -> (f64, f64) {
    // Total RAM
    let total = Command::new("powershell")
        .args(["-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB"])
        .output()
        .ok()
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .and_then(|s| s.trim().parse::<f64>().ok())
        .unwrap_or(8.0); // Conservative fallback

    // Free RAM (FreePhysicalMemory is in KB)
    let free = Command::new("powershell")
        .args(["-NoProfile", "-Command", "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1048576"])
        .output()
        .ok()
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .and_then(|s| s.trim().parse::<f64>().ok())
        .unwrap_or(4.0); // Conservative fallback

    (total, free)
}

/// Detect GPU name and VRAM via nvidia-smi.
fn detect_gpu() -> (Option<String>, f64, f64) {
    let output = Command::new("nvidia-smi")
        .args(["--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"])
        .output();

    match output {
        Ok(o) if o.status.success() => {
            let text = String::from_utf8_lossy(&o.stdout);
            let line = text.trim();
            let parts: Vec<&str> = line.split(',').map(|s| s.trim()).collect();
            if parts.len() >= 3 {
                let name = parts[0].to_string();
                let total_mb: f64 = parts[1].parse().unwrap_or(0.0);
                let free_mb: f64 = parts[2].parse().unwrap_or(0.0);
                (Some(name), total_mb / 1024.0, free_mb / 1024.0)
            } else {
                (None, 0.0, 0.0)
            }
        }
        _ => (None, 0.0, 0.0),
    }
}

/// Extract parameter count in billions from a model ID string.
///
/// Examples:
///   "Qwen/Qwen2.5-7B-Instruct" → Some(7.0)
///   "meta-llama/Llama-3.1-8B-Instruct" → Some(8.0)
///   "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B" → Some(1.5)
///   "deepseek-ai/DeepSeek-R1" → Some(671.0) (hardcoded known model)
pub fn estimate_params_billions(model_id: &str) -> Option<f64> {
    // Hardcoded known models that don't have param count in name
    let known_models: &[(&str, f64)] = &[
        ("DeepSeek-R1-0528", 671.0),
        ("DeepSeek-V3.2", 671.0),
        ("DeepSeek-V3-0324", 671.0),
        ("DeepSeek-V4-Pro", 800.0),
        ("DeepSeek-V4-Flash", 236.0),
        ("Mixtral-8x7B", 46.7),
        ("Mixtral-8x22B", 141.0),
        ("gpt2", 0.124),
        ("gpt2-medium", 0.355),
        ("gpt2-large", 0.774),
        ("gpt2-xl", 1.5),
        ("opt-125m", 0.125),
        ("opt-350m", 0.350),
        ("opt-1.3b", 1.3),
        ("opt-6.7b", 6.7),
        ("bloom-560m", 0.56),
        ("bloom-1b7", 1.7),
        ("bloom-7b1", 7.1),
    ];

    // Check hardcoded known models first (must check before regex to avoid false matches)
    let model_name = model_id.split('/').last().unwrap_or(model_id);
    for (name, params) in known_models {
        if model_name == *name {
            return Some(*params);
        }
    }

    // Special case: "DeepSeek-R1" exactly (not a distill variant)
    if model_name == "DeepSeek-R1" {
        return Some(671.0);
    }

    // Extract parameter count from patterns like "7B", "1.5B", "70b", "0.6B"
    // Scan through the model name looking for number+B patterns
    let lower = model_name.to_lowercase();
    let chars: Vec<char> = lower.chars().collect();
    let len = chars.len();

    let mut best_match: Option<f64> = None;
    let mut i = 0;
    while i < len {
        // Look for a digit
        if chars[i].is_ascii_digit() {
            let start = i;
            // Consume digits, dots, and 'x' (for patterns like 8x7)
            while i < len && (chars[i].is_ascii_digit() || chars[i] == '.') {
                i += 1;
            }
            // Check if followed by 'b' (billion)
            if i < len && chars[i] == 'b' {
                let num_str: String = chars[start..i].iter().collect();
                if let Ok(val) = num_str.parse::<f64>() {
                    if val > 0.0 && val < 2000.0 {
                        // Check it's not part of a longer word after 'b'
                        let after_b = i + 1;
                        let valid_boundary = after_b >= len
                            || !chars[after_b].is_ascii_alphabetic()
                            || chars[after_b] == '-'
                            || chars[after_b] == '_';
                        if valid_boundary {
                            best_match = Some(val);
                        }
                    }
                }
            }
            // Check for 'm' (million) — e.g., "125m"
            if i < len && chars[i] == 'm' {
                let num_str: String = chars[start..i].iter().collect();
                if let Ok(val) = num_str.parse::<f64>() {
                    if val > 50.0 && val < 10000.0 {
                        let after_m = i + 1;
                        let valid_boundary = after_m >= len
                            || !chars[after_m].is_ascii_alphabetic()
                            || chars[after_m] == '-'
                            || chars[after_m] == '_';
                        if valid_boundary {
                            best_match = Some(val / 1000.0); // Convert millions to billions
                        }
                    }
                }
            }
        }
        i += 1;
    }

    best_match
}

/// Estimate the runtime memory (in GB) needed to load and run a model.
///
/// - Transformers (FP16): params_billions × 2 bytes × 1.2 overhead = params × 2.4 GB
/// - Ollama (Q4_0):       params_billions × 0.6 bytes × 1.2 overhead = params × 0.72 GB
/// - OpenVINO (INT4):     params_billions × 0.5 bytes × 1.2 overhead = params × 0.6 GB
pub fn estimate_runtime_memory_gb(params_billions: f64, backend: Backend) -> f64 {
    let bytes_per_param = match backend {
        Backend::Transformers => 2.0,  // float16
        Backend::Ollama => 0.6,       // q4_0 quantization
        Backend::OpenVINO => 0.5,     // int4 quantization (optimum-intel)
    };
    let overhead = 1.2; // KV cache, activations, OS overhead
    params_billions * bytes_per_param * overhead
}

/// Check if a model can fit in the available memory.
pub fn model_fits(params_billions: f64, backend: Backend, memory: &SystemMemory) -> bool {
    let required = estimate_runtime_memory_gb(params_billions, backend);
    required <= memory.model_budget_gb()
}

/// Check if Ollama is actually responding by making a real HTTP request.
fn is_ollama_responding(endpoint: &str) -> bool {
    // Use curl for a reliable check (powershell Invoke-WebRequest can give false positives)
    let result = Command::new("curl")
        .args(["-s", "-o", "nul", "-w", "%{http_code}", "--max-time", "3",
               &format!("{}/api/tags", endpoint)])
        .output();

    match result {
        Ok(o) => {
            let code = String::from_utf8_lossy(&o.stdout).trim().to_string();
            code == "200"
        }
        Err(_) => {
            // curl not available, try powershell as fallback
            let ps_result = Command::new("powershell")
                .args(["-NoProfile", "-Command",
                    &format!("try {{ $r = Invoke-WebRequest -Uri '{}/api/tags' -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop; $r.StatusCode }} catch {{ 'FAIL' }}", endpoint)])
                .output();
            match ps_result {
                Ok(o) => {
                    let text = String::from_utf8_lossy(&o.stdout).trim().to_string();
                    text == "200"
                }
                Err(_) => false,
            }
        }
    }
}

/// Ensure Ollama is running. If it's not, auto-start `ollama serve` and wait for it.
pub fn ensure_ollama_running() -> Result<(), String> {
    let endpoint = std::env::var("LOCAL_OLLAMA_ENDPOINT")
        .unwrap_or_else(|_| "http://localhost:11434".to_string());

    // First check: is it already running?
    if is_ollama_responding(&endpoint) {
        return Ok(());
    }

    // Not running — start it
    println!("🦙 [OLLAMA] Ollama is not running. Starting 'ollama serve' automatically...");

    // Launch ollama serve as a background process
    let start_result = Command::new("cmd")
        .args(["/C", "start", "/B", "ollama", "serve"])
        .spawn();

    match start_result {
        Ok(_) => {
            println!("🦙 [OLLAMA] Started 'ollama serve'. Waiting for it to be ready...");
        }
        Err(e) => {
            return Err(format!("Failed to start 'ollama serve': {}. Is Ollama installed?", e));
        }
    }

    // Wait for Ollama to become responsive (up to 30 seconds)
    for i in 0..30 {
        std::thread::sleep(std::time::Duration::from_secs(1));
        if is_ollama_responding(&endpoint) {
            println!("🦙 [OLLAMA] Ollama is ready! (took {}s)", i + 1);
            return Ok(());
        }
        if (i + 1) % 5 == 0 {
            println!("🦙 [OLLAMA] Still waiting... ({}s)", i + 1);
        }
    }

    Err("Ollama failed to start within 30 seconds. Please start it manually with 'ollama serve'.".to_string())
}

/// Check if an OpenVINO model is cached/pre-converted on disk.
pub fn is_openvino_model_cached(model_id: &str) -> bool {
    let safe_name = model_id.split('/').last().unwrap_or(model_id).to_lowercase().replace(' ', "-");
    
    // Check in local 'ov_models' directory
    let ov_model_dir = std::path::Path::new("ov_models");
    if ov_model_dir.is_dir() {
        if let Ok(entries) = std::fs::read_dir(ov_model_dir) {
            for entry in entries.flatten() {
                if let Ok(name) = entry.file_name().into_string() {
                    if name.starts_with(&safe_name) {
                        let path = entry.path();
                        if path.join("openvino_model.xml").exists() || path.join("model.xml").exists() {
                            return true;
                        }
                    }
                }
            }
        }
    }
    
    // Check in system home directory cache (~/.cache/modelfusion_ov/)
    let home = std::env::var("USERPROFILE")
        .or_else(|_| std::env::var("HOME"))
        .ok();
        
    if let Some(home_path) = home {
        let cache_dir = std::path::Path::new(&home_path)
            .join(".cache")
            .join("modelfusion_ov")
            .join(model_id.replace('/', "_"));
            
        if cache_dir.is_dir() {
            if let Ok(devices) = std::fs::read_dir(cache_dir) {
                for device_entry in devices.flatten() {
                    if device_entry.path().join("model.xml").exists() {
                        return true;
                    }
                }
            }
        }
    }
    
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_param_extraction() {
        assert_eq!(estimate_params_billions("Qwen/Qwen2.5-7B-Instruct"), Some(7.0));
        assert_eq!(estimate_params_billions("meta-llama/Llama-3.1-8B-Instruct"), Some(8.0));
        assert_eq!(estimate_params_billions("Qwen/Qwen2.5-1.5B-Instruct"), Some(1.5));
        assert_eq!(estimate_params_billions("meta-llama/Llama-3.2-1B-Instruct"), Some(1.0));
        assert_eq!(estimate_params_billions("deepseek-ai/DeepSeek-R1"), Some(671.0));
        assert_eq!(estimate_params_billions("deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"), Some(1.5));
        assert_eq!(estimate_params_billions("facebook/opt-125m"), Some(0.125));
        assert_eq!(estimate_params_billions("Qwen/Qwen3-0.6B"), Some(0.6));
    }

    #[test]
    fn test_memory_estimation() {
        // 7B model, Transformers FP16: 7 × 2 × 1.2 = 16.8 GB
        let mem = estimate_runtime_memory_gb(7.0, Backend::Transformers);
        assert!((mem - 16.8).abs() < 0.01);

        // 7B model, Ollama Q4: 7 × 0.6 × 1.2 = 5.04 GB
        let mem = estimate_runtime_memory_gb(7.0, Backend::Ollama);
        assert!((mem - 5.04).abs() < 0.01);
    }
}
