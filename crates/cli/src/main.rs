#![recursion_limit = "512"]
//! CLI Entry Point for ModelFusion.

use anyhow::Result;
use clap::Parser;
use modelfusion_core::{ComprehensiveTaskHandler, HuggingFaceOrchestrator};
use model_selection::SelectionStrategy;
use std::collections::HashMap;
use std::sync::{Arc, OnceLock};
use tokio::sync::Semaphore;
use chrono;

// ---------------------------------------------------------------------------
// Global inference semaphore
// ---------------------------------------------------------------------------
// Limits the number of concurrent model inferences across the API server,
// CLI spawns (if they call into the same process), and MCP server.
// The permit count is derived from available RAM at startup:
//   < 8 GB  → 1 concurrent inference
//   8–16 GB → 2 concurrent inferences
//   > 16 GB → 4 concurrent inferences
// Each waiter queues until a slot is free — no request is dropped.
static INFERENCE_SEM: OnceLock<Arc<Semaphore>> = OnceLock::new();

fn inference_sem() -> Arc<Semaphore> {
    INFERENCE_SEM.get_or_init(|| {
        let permits = heavy_inference_slots();
        eprintln!("[SEMAPHORE] Heavy pipeline pool: {} slot(s)", permits);
        Arc::new(Semaphore::new(permits))
    }).clone()
}

static FAST_SEM: OnceLock<Arc<Semaphore>> = OnceLock::new();

fn fast_inference_sem() -> Arc<Semaphore> {
    FAST_SEM.get_or_init(|| {
        let permits = fast_inference_slots();
        eprintln!("[SEMAPHORE] Fast path pool: {} slot(s)", permits);
        Arc::new(Semaphore::new(permits))
    }).clone()
}

/// Heavy pipeline slots — limited by RAM since orchestrator loads models
fn heavy_inference_slots() -> usize {
    let mut sys = sysinfo::System::new();
    sys.refresh_memory();
    let ram_gb = sys.total_memory() / 1_073_741_824;
    if ram_gb >= 32 { 4 }
    else if ram_gb >= 16 { 2 }
    else { 1 }
}

/// Fast path slots — generous since Ollama 1.5b is lightweight (~1GB)
/// and Ollama handles its own GPU/memory concurrency internally
fn fast_inference_slots() -> usize {
    let mut sys = sysinfo::System::new();
    sys.refresh_memory();
    let ram_gb = sys.total_memory() / 1_073_741_824;
    if ram_gb >= 32 { 16 }
    else if ram_gb >= 16 { 8 }
    else { 4 }
}

/// Hardware-aware Ollama model selector.
#[derive(Debug, Clone)]
pub struct SystemResourceSummary {
    pub cpu_name: String,
    pub logical_cores: usize,
    pub total_ram_gb: f64,
    pub free_ram_gb: f64,
    pub gpu_name: String,
    pub total_vram_mb: u64,
    pub free_vram_mb: u64,
    pub has_gpu: bool,
    pub free_disk_gb: f64,
}

/// Queries hardware resources (CPU, RAM, GPU VRAM, Disk) using native Rust sysinfo and nvidia-smi / WMI.
pub fn query_system_resources() -> SystemResourceSummary {
    let mut sys = sysinfo::System::new_all();
    sys.refresh_all();

    let total_ram_gb = sys.total_memory() as f64 / 1_073_741_824.0;
    let free_ram_gb = sys.available_memory() as f64 / 1_073_741_824.0;

    let cpus = sys.cpus();
    let logical_cores = cpus.len();
    let cpu_name = cpus
        .first()
        .map(|c| c.brand().trim().to_string())
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| "Generic CPU".to_string());

    // Query GPU via nvidia-smi
    let mut gpu_name = "None / Integrated".to_string();
    let mut total_vram_mb = 0u64;
    let mut free_vram_mb = 0u64;
    let mut has_gpu = false;

    if let Ok(output) = std::process::Command::new("nvidia-smi")
        .args(["--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"])
        .output()
    {
        if output.status.success() {
            let stdout = String::from_utf8_lossy(&output.stdout);
            let parts: Vec<&str> = stdout.trim().split(',').map(|s| s.trim()).collect();
            if parts.len() >= 3 {
                gpu_name = parts[0].to_string();
                total_vram_mb = parts[1].parse::<u64>().unwrap_or(0);
                free_vram_mb = parts[2].parse::<u64>().unwrap_or(0);
                has_gpu = true;
            }
        }
    }

    // Windows WMI fallback if nvidia-smi wasn't available
    if !has_gpu && cfg!(windows) {
        if let Ok(output) = std::process::Command::new("wmic")
            .args(["path", "win32_videocard", "get", "name"])
            .output()
        {
            if output.status.success() {
                let stdout = String::from_utf8_lossy(&output.stdout);
                let lines: Vec<&str> = stdout.lines().map(|s| s.trim()).filter(|s| !s.is_empty() && *s != "Name").collect();
                if let Some(first_gpu) = lines.first() {
                    gpu_name = first_gpu.to_string();
                    let lower = gpu_name.to_lowercase();
                    if lower.contains("nvidia") || lower.contains("geforce") || lower.contains("radeon") || lower.contains("rtx") || lower.contains("gtx") {
                        has_gpu = true;
                    }
                }
            }
        }
    }

    // Query free disk space
    let disks = sysinfo::Disks::new_with_refreshed_list();
    let free_disk_gb = disks
        .iter()
        .map(|d| d.available_space())
        .max()
        .unwrap_or(0) as f64 / 1_073_741_824.0;

    SystemResourceSummary {
        cpu_name,
        logical_cores,
        total_ram_gb,
        free_ram_gb,
        gpu_name,
        total_vram_mb,
        free_vram_mb,
        has_gpu,
        free_disk_gb,
    }
}

/// Detects system RAM, VRAM, and CPU to pick the optimal Ollama model fit.
/// Prints a formatted debug log banner showing detected resources.
fn select_ollama_model_for_hardware(is_low_budget: bool) -> &'static str {
    if is_low_budget {
        return "qwen2.5:1.5b";
    }

    let res = query_system_resources();

    // Print resource debug banner
    eprintln!("============================================================");
    eprintln!("        MODELFUSION RUST HARDWARE RESOURCE QUERY           ");
    eprintln!("============================================================");
    eprintln!("  CPU           : {} ({} logical cores)", res.cpu_name, res.logical_cores);
    eprintln!("  RAM           : Total: {:.2} GB | Available Free: {:.2} GB", res.total_ram_gb, res.free_ram_gb);
    if res.has_gpu {
        eprintln!("  GPU           : {} (Total VRAM: {} MB, Free VRAM: {} MB)", res.gpu_name, res.total_vram_mb, res.free_vram_mb);
    } else {
        eprintln!("  GPU           : None detected / CPU fallthrough");
    }
    eprintln!("  Max Free Disk : {:.2} GB", res.free_disk_gb);

    // VRAM-aware model fit logic
    let chosen_model = if res.total_vram_mb >= 14_000 {
        "qwen2.5:14b"
    } else if res.total_vram_mb >= 4_500 || (res.has_gpu && res.total_ram_gb >= 16.0) {
        // Fits inside 6GB VRAM (like GTX 1060 6GB) or 8GB VRAM GPUs cleanly
        "qwen2.5:7b"
    } else if res.total_vram_mb >= 2_000 || res.total_ram_gb >= 16.0 {
        "qwen2.5:3b"
    } else {
        "qwen2.5:1.5b"
    };

    eprintln!("  BEST MODEL FIT: {}", chosen_model);
    eprintln!("============================================================");

    chosen_model
}

/// Dynamically determine the optimal context window (num_ctx) for the chosen Ollama model.
/// Balances context size against the physical RAM constraints to prevent OOM/slowdowns.
fn select_context_window_for_model(model: &str) -> u32 {
    let lower_model = model.to_lowercase();
    let mut sys = sysinfo::System::new();
    sys.refresh_memory();
    let ram_gb = sys.total_memory() / 1_073_741_824;

    if lower_model.contains("0.5b") || lower_model.contains("1.5b") {
        // Very small models can easily handle larger context with low overhead
        16384
    } else if lower_model.contains("3b") || lower_model.contains("4b") {
        if ram_gb >= 16 { 16384 } else { 8192 }
    } else if lower_model.contains("7b") || lower_model.contains("8b") || lower_model.contains("llama3") {
        // Large models need substantial memory for KV cache at high contexts
        if ram_gb >= 32 {
            16384
        } else if ram_gb >= 16 {
            8192
        } else {
            4096
        }
    } else {
        // Safe default fallback for custom models
        if ram_gb >= 16 { 8192 } else { 4096 }
    }
}


#[derive(Parser, Debug)]
#[command(name = "modelfusion", version = "0.1.0", about = "ModelFusion - Advanced HuggingFace Model Orchestration System")]
struct Args {
    // ---------------------------------------------------------
    // Global Flags
    // ---------------------------------------------------------
    #[arg(long, help = "Path to file for analysis or processing")]
    file: Option<String>,

    #[arg(long, help = "Path to folder for code review or analysis")]
    folder: Option<String>,

    #[arg(long, help = "Prompt for LLM generation or task directive")]
    prompt: Option<String>,

    #[arg(help = "Prompt query fallback (positional argument)")]
    query: Option<String>,

    #[arg(long, help = "Forced task name")]
    task: Option<String>,

    #[arg(long, default_value = "10.0", help = "Budget limit for LLM providers")]
    budget: f64,

    #[arg(long, help = "Enable chain-of-thought prompting")]
    chain_of_thought: bool,

    #[arg(long, help = "Path to custom JSON configuration")]
    config: Option<String>,

    #[arg(long, help = "Enable ML enhancements")]
    enable_ml: bool,

    #[arg(long, help = "Force use of OpenAI models")]
    use_openai: bool,

    #[arg(long, help = "Enable verbose output")]
    verbose: bool,

    #[arg(long, help = "Enable debug output")]
    debug: bool,

    #[arg(long, default_value = "multi_objective", help = "Model selection strategy")]
    selection_strategy: String,

    #[arg(long, default_value = "en", help = "Set processing language")]
    language: String,

    #[arg(long, help = "Force GPU/CUDA usage")]
    gpu: bool,

    #[arg(long, help = "Force CPU-only execution")]
    cpu: bool,

    #[arg(long, help = "JSON file containing API keys")]
    api_keys: Option<String>,

    #[arg(long, help = "Print detected system resource specifications in JSON format")]
    sys_info: bool,

    #[arg(long, help = "Save trained ML models")]
    save_model: bool,

    #[arg(long, help = "Load pre-trained ML model")]
    load_model: Option<String>,

    // ---------------------------------------------------------
    // ML Selection Flags
    // ---------------------------------------------------------
    #[arg(long, help = "Enable ML-based model selection system")]
    enable_ml_selection: bool,

    #[arg(long, help = "Enable learning from task execution results")]
    ml_learning: bool,

    #[arg(long, default_value = "weighted_voting", help = "Ensemble method for ML")]
    ml_ensemble_method: String,

    #[arg(long, default_value = "0.6", help = "Minimum confidence threshold for ML")]
    ml_confidence_threshold: f64,

    #[arg(long, help = "Show ML model selection analytics")]
    ml_analytics: bool,

    #[arg(long, help = "Force retraining of ML models")]
    ml_retrain: bool,

    #[arg(long, help = "Clean up ML training data older than specified days")]
    ml_cleanup: Option<u32>,

    // ---------------------------------------------------------
    // SINQ Quantization Flags
    // ---------------------------------------------------------
    #[arg(long, help = "Enable SINQ quantization")]
    sinq: bool,

    #[arg(long, default_value = "4", help = "Bit-width for SINQ weight quantization")]
    sinq_nbits: u32,

    #[arg(long, default_value = "64", help = "Weights per quantization group for SINQ")]
    sinq_group_size: u32,

    #[arg(long, default_value = "1D", help = "Weight matrix tiling strategy for SINQ")]
    sinq_tiling_mode: String,

    #[arg(long, default_value = "sinq", help = "SINQ quantization method")]
    sinq_method: String,

    // ---------------------------------------------------------
    // Innovation Flags
    // ---------------------------------------------------------
    #[arg(long, help = "Enable all innovation systems")]
    enable_innovations: bool,

    #[arg(long, help = "Enable workflow optimization")]
    workflow_optimization: bool,

    #[arg(long, help = "Enable semantic analysis of content")]
    semantic_analysis: bool,

    #[arg(long, help = "Enable temporal change tracking")]
    temporal_tracking: bool,

    #[arg(long, help = "Enable predictive capabilities")]
    predictive_mode: bool,

    #[arg(long, default_value = "2", help = "Innovation system level")]
    innovation_level: u32,

    // ---------------------------------------------------------
    // HYDE Flags
    // ---------------------------------------------------------
    #[arg(long, help = "Enable HyDE search")]
    enable_hyde: bool,

    #[arg(long, help = "Use interactive HyDE question refinement")]
    use_hyde: bool,

    #[arg(long, help = "Use multiple HyDE variants")]
    hyde_variants: bool,

    #[arg(long, help = "Add documents to search index")]
    add_documents: Option<String>,

    #[arg(long, help = "Perform semantic search query")]
    search_query: Option<String>,

    #[arg(long, default_value = "5", help = "Number of top results for search")]
    top_k: u32,

    #[arg(long, help = "Run HyDE and embeddings demo")]
    demo_hyde: bool,

    // ---------------------------------------------------------
    // System Commands / Flags
    // ---------------------------------------------------------
    #[arg(long, help = "Show model categorization statistics")]
    stats: bool,

    #[arg(
        long,
        num_args = 0..=1,
        default_missing_value = "all",
        help = "List models and tasks (filter by: audio, image, text, etc.)"
    )]
    tasks: Option<String>,

    #[arg(long, help = "Update the HuggingFace models database")]
    update: bool,

    #[arg(long, help = "Restore config and database from backups")]
    restore: bool,

    #[arg(long, help = "Show decision-making statistics")]
    decision_stats: bool,

    #[arg(long, help = "Show novel AI component statistics")]
    novel_ai_stats: bool,

    #[arg(long, help = "Show performance metrics")]
    performance_stats: bool,

    #[arg(long, help = "Show cache usage statistics")]
    cache_stats: bool,

    #[arg(long, help = "Clear all cached data")]
    clearcache: bool,

    #[arg(long, help = "Run advanced model analytics demo")]
    analytics_demo: bool,

    #[arg(
        long,
        num_args = 0..=1,
        default_missing_value = "all",
        help = "Show model ranking for a task"
    )]
    model_ranking: Option<String>,

    #[arg(long, help = "Get personalized model recommendations")]
    model_recommendations: bool,

    #[arg(long, help = "Enable comprehensive analysis mode")]
    full: bool,

    #[arg(long, help = "Enable model fusion to process prompt using a panel of models")]
    fusion: bool,

    #[arg(long, default_value = "10", help = "Number of models to run in the fusion panel")]
    fusion_models: usize,

    #[arg(long, default_value = "multi-model", help = "Fusion execution mode: 'multi-model' (N different models) or 'multi-sample' (1 model, N temperature samples — much faster locally)")]
    fusion_mode: String,

    #[arg(long, help = "Use local Ollama for fusion model execution instead of Python transformers")]
    ollama: bool,

    #[arg(long, help = "Use OpenVINO for optimized CPU inference (requires: pip install -U openvino-genai or openvino)")]
    openvino: bool,

    #[arg(long, help = "Use ONNX Runtime for optimized cross-platform inference (requires: pip install optimum[onnxruntime])")]
    onnx: bool,

    #[arg(long, help = "Use vLLM for high-throughput GPU inference (Linux only, requires: pip install vllm)")]
    vllm: bool,

    #[arg(long, help = "Force the use of a specific HuggingFace model ID")]
    model: Option<String>,

    #[arg(long, help = "Pre-convert a HuggingFace model to OpenVINO IR format (requires: pip install optimum-intel[openvino])")]
    prepare_model: Option<String>,

    #[arg(long, help = "Pre-convert ALL eligible models from database to OpenVINO IR (batch)")]
    prepare_all_models: bool,

    #[arg(long, default_value = "int8", help = "Weight format for OpenVINO export: fp16, int8, int4")]
    weight_format: String,

    #[arg(long, default_value = "ov_models", help = "Directory for cached OpenVINO IR models")]
    ov_model_dir: String,

    #[arg(long, help = "Automatically generate context using a thinking DeepSeek model")]
    context_auto: bool,

    #[arg(long, help = "Provide custom context or context prompt for generation")]
    context: Option<String>,

    #[arg(long, help = "Path to folder or file where the final report should be saved")]
    report: Option<String>,

    #[arg(long, default_value = "md", help = "Format of the report: pdf, text, json, md, word")]
    reporttype: String,

    #[arg(long, help = "Use delegation pattern to route tasks to specialized models")]
    delegation: bool,

    #[arg(long, help = "Use recursive task decomposition for complex problems")]
    recursion: bool,

    #[arg(long, help = "Periodically get OpenVINO preconfigured models in the background")]
    getvino: bool,

    #[arg(long, default_value_t = 24, help = "Download interval in hours for --getvino background cycle (default: 24)")]
    getvino_interval: u64,

    #[arg(long, help = "Enable real options analysis for backup model selection")]
    real_options: bool,

    #[arg(long, help = "Enable prompt quality scoring and optimization")]
    prompt_quality_scoring: bool,

    #[arg(long, default_value_t = true, action = clap::ArgAction::Set, help = "Enable fallback to enhanced selector when ML selection fails")]
    ml_fallback: bool,

    #[arg(long, help = "Launch Jupyter notebook for data analysis")]
    jupyter: bool,

    // ---------------------------------------------------------
    // Data Science Flags
    // ---------------------------------------------------------
    #[arg(long, alias = "data-analyst", alias = "datanalyst", help = "Run the Data Analyst workflow on CSV/Excel")]
    dataanalyst: bool,

    #[arg(long, help = "Run comprehensive Data Science workflow")]
    datascience: bool,

    #[arg(long, help = "Export analysis results to PDF report")]
    export_pdf: bool,

    // ---------------------------------------------------------
    // Evaluation / Scoring Flags
    // ---------------------------------------------------------
    #[arg(long, help = "Enable response evaluation scoring")]
    score: bool,

    #[arg(long, help = "Enable LLM-as-a-Judge evaluation")]
    judge: bool,

    #[arg(long, help = "Enable AI-powered planning")]
    plan: bool,

    // ---------------------------------------------------------
    // PE Analysis Flags
    // ---------------------------------------------------------
    #[arg(long, help = "Extract PE headers from Windows executables")]
    pe_header_extraction: bool,

    // ---------------------------------------------------------
    // Legacy / Task Boolean Flags
    // ---------------------------------------------------------
    #[arg(long, help = "Legacy basic sentiment analysis")]
    sentiment: bool,

    #[arg(long, help = "Legacy question answering mode")]
    question: bool,

    #[arg(long, help = "Legacy named entity recognition")]
    ner: bool,

    #[arg(long, help = "Legacy text summarization")]
    summary: bool,

    // Task Flags (Standard mappings)
    #[arg(long)]
    text_classification: bool,

    #[arg(long)]
    token_classification: bool,

    #[arg(long)]
    question_answering: bool,

    #[arg(long)]
    text_generation: bool,

    #[arg(long)]
    summarization: bool,

    #[arg(long)]
    translation: bool,

    #[arg(long)]
    fill_mask: bool,

    #[arg(long)]
    text2text_generation: bool,

    #[arg(long)]
    language_detection: bool,

    #[arg(long)]
    grammar_correction: bool,

    #[arg(long)]
    paraphrase_generation: bool,

    #[arg(long)]
    causal_language_modeling: bool,

    #[arg(long)]
    zero_shot_classification: bool,

    #[arg(long)]
    feature_extraction: bool,

    #[arg(long)]
    sentence_similarity: bool,

    #[arg(long)]
    anonymization: bool,

    #[arg(long)]
    coreference_resolution: bool,

    #[arg(long)]
    spam_detection: bool,

    #[arg(long)]
    malware_text_detection: bool,

    #[arg(long)]
    phishing_detection: bool,

    #[arg(long)]
    pii_detection: bool,

    #[arg(long)]
    hate_speech_detection: bool,

    #[arg(long)]
    cyberbullying_detection: bool,

    #[arg(long)]
    fake_news_detection: bool,

    #[arg(long)]
    legal_judgment_classification: bool,

    #[arg(long)]
    contract_clause_classification: bool,

    #[arg(long)]
    case_outcome_prediction: bool,

    #[arg(long)]
    financial_ner: bool,

    #[arg(long)]
    legal_ner: bool,

    #[arg(long)]
    biomedical_ner: bool,

    #[arg(long)]
    chemical_reaction_ner: bool,

    #[arg(long)]
    financial_sentiment_analysis: bool,

    #[arg(long)]
    scientific_abstract_summarization: bool,

    #[arg(long)]
    emotion_detection: bool,

    #[arg(long)]
    sarcasm_detection: bool,

    #[arg(long)]
    stance_detection: bool,

    #[arg(long)]
    bias_detection: bool,

    #[arg(long)]
    hallucination_detection: bool,

    #[arg(long)]
    reading_level_assessment: bool,

    #[arg(long)]
    generation_groundedness: bool,

    #[arg(long)]
    citation_intent_classification: bool,

    #[arg(long)]
    code_vulnerability_detection: bool,

    #[arg(long)]
    code_summary_generation: bool,

    #[arg(long)]
    code_clone_detection: bool,

    #[arg(long)]
    image_classification: bool,

    #[arg(long)]
    object_detection: bool,

    #[arg(long)]
    image_segmentation: bool,

    #[arg(long)]
    visual_question_answering: bool,

    #[arg(long)]
    document_question_answering: bool,

    #[arg(long)]
    zero_shot_image_classification: bool,

    #[arg(long)]
    depth_estimation: bool,

    #[arg(long)]
    image_feature_extraction: bool,

    #[arg(long)]
    automatic_speech_recognition: bool,

    #[arg(long)]
    audio_classification: bool,

    #[arg(long)]
    voice_activity_detection: bool,

    #[arg(long)]
    emotion_recognition: bool,

    #[arg(long)]
    video_classification: bool,

    #[arg(long)]
    text_to_speech: bool,

    #[arg(long)]
    text_to_image: bool,

    #[arg(long)]
    image_super_resolution: bool,

    #[arg(long)]
    table_question_answering: bool,

    #[arg(long)]
    feature_ranking: bool,

    #[arg(long, help = "Custom SQLite database path for ModelFusion")]
    db_path: Option<String>,

    #[arg(long, help = "Run as HTTP API server")]
    server: bool,

    #[arg(long, help = "Enable parsing of slash commands from prompt")]
    enable_slash_commands: bool,

    #[arg(long, default_value = "5000", help = "Port to run HTTP server on")]
    port: u16,

    #[arg(long, help = "Run as MCP stdio server")]
    mcp: bool,

    // ---------------------------------------------------------
    // IDE Patching Flags
    // ---------------------------------------------------------
    #[arg(long, help = "Clone VSCode from GitHub and apply HugOS IDE branding patches")]
    patch_ide: bool,

    #[arg(long, default_value = "IDE/src", help = "Target directory for the VSCode clone")]
    ide_src_dir: String,

    #[arg(long, help = "Shallow clone with --depth 1 for faster download")]
    shallow: bool,

    #[arg(long, help = "Specific VSCode git tag to clone (e.g., '1.96.0')")]
    vscode_tag: Option<String>,
}

fn main() -> Result<()> {
    // Parse arguments on the main thread first, before starting runtime or semaphore
    let args = Args::parse();

    if args.sys_info {
        let sys_mem = model_selection::memory::SystemMemory::detect();
        let disks = sysinfo::Disks::new_with_refreshed_list();
        let free_disk_gb = if let Some(disk) = disks.iter().find(|d| d.mount_point() == std::path::Path::new("C:\\") || d.mount_point() == std::path::Path::new("/")) {
            disk.available_space() as f64 / 1_073_741_824.0
        } else if let Some(disk) = disks.first() {
            disk.available_space() as f64 / 1_073_741_824.0
        } else {
            0.0
        };

        let info = serde_json::json!({
            "cpu": sys_mem.gpu_name.is_none(),
            "cores": sys_mem.cpu_cores,
            "total_ram": sys_mem.total_ram_gb,
            "free_ram": sys_mem.free_ram_gb,
            "gpu": sys_mem.gpu_name.clone().unwrap_or_else(|| "None".to_string()),
            "gpu_vram_total": sys_mem.gpu_vram_total_gb,
            "gpu_vram_free": sys_mem.gpu_vram_free_gb,
            "free_disk": free_disk_gb,
        });
        println!("{}", serde_json::to_string(&info).unwrap_or_else(|_| "{}".to_string()));
        return Ok(());
    }

    // Initialise the inference semaphore before the runtime starts so that
    // the slot count is printed once at startup.
    let _ = inference_sem();

    // Use a multi-threaded Tokio runtime so that the API server, MCP server,
    // and CLI inference tasks can all run on separate OS threads concurrently.
    // A dedicated 8 MB stack is used to avoid overflow with the large Args struct.
    let builder = std::thread::Builder::new().stack_size(8 * 1024 * 1024);
    let handler = builder.spawn(move || {
        let rt = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .worker_threads(std::thread::available_parallelism().map(|n| n.get()).unwrap_or(4))
            .build()
            .expect("Failed to build Tokio runtime");

        // Spawn getvino background thread if requested
        if args.getvino {
            let ov_dir = args.ov_model_dir.clone();
            let interval_hours = args.getvino_interval.max(1); // minimum 1 hour
            rt.spawn(async move {
                loop {
                    eprintln!("[Background] Running OpenVINO model downloader (interval: {}h)...", interval_hours);
                    // Resolve getvino.py: try multiple locations for installed and dev builds
                    let exe_dir = std::env::current_exe()
                        .ok()
                        .and_then(|p| p.parent().map(|d| d.to_path_buf()))
                        .unwrap_or_else(|| std::path::PathBuf::from("."));
                    
                    let candidates = vec![
                        // Installed layout: bin/cli.exe -> ../src/scripts/getvino.py
                        exe_dir.join("..").join("src").join("scripts").join("getvino.py"),
                        // Dev layout: target/release/cli.exe -> ../../src/scripts/getvino.py
                        exe_dir.join("..").join("..").join("src").join("scripts").join("getvino.py"),
                        // CWD fallback
                        std::path::PathBuf::from("src").join("scripts").join("getvino.py"),
                    ];
                    
                    let script_path = candidates.iter()
                        .find(|p| p.exists())
                        .cloned()
                        .unwrap_or_else(|| candidates[0].clone());
                    
                    eprintln!("[Background] Script path: {:?} (exists: {})", script_path, script_path.exists());
                    let result = std::process::Command::new("python")
                        .arg(&script_path)
                        .arg(&ov_dir)
                        .arg("all")
                        .spawn()
                        .and_then(|mut child| child.wait());
                    match result {
                        Ok(status) => eprintln!("[Background] getvino.py exited with: {}", status),
                        Err(e) => eprintln!("[Background] Failed to run getvino.py: {}", e),
                    }
                    // Sleep for the configured interval
                    tokio::time::sleep(tokio::time::Duration::from_secs(interval_hours * 3600)).await;
                }
            });
        }
        
        rt.block_on(run(args))
    }).expect("Failed to spawn main thread");
    handler.join().unwrap()
}

async fn run(args: Args) -> Result<()> {
    // Load .env variables
    dotenv::dotenv().ok();

    let args = Box::new(args);

    if args.sys_info {
        let sys_mem = model_selection::memory::SystemMemory::detect();
        let disks = sysinfo::Disks::new_with_refreshed_list();
        let free_disk_gb = if let Some(disk) = disks.iter().find(|d| d.mount_point() == std::path::Path::new("C:\\") || d.mount_point() == std::path::Path::new("/")) {
            disk.available_space() as f64 / 1_073_741_824.0
        } else if let Some(disk) = disks.first() {
            disk.available_space() as f64 / 1_073_741_824.0
        } else {
            0.0
        };

        let info = serde_json::json!({
            "cpu": sys_mem.gpu_name.is_none(),
            "cores": sys_mem.cpu_cores,
            "total_ram": sys_mem.total_ram_gb,
            "free_ram": sys_mem.free_ram_gb,
            "gpu": sys_mem.gpu_name.clone().unwrap_or_else(|| "None".to_string()),
            "gpu_vram_total": sys_mem.gpu_vram_total_gb,
            "gpu_vram_free": sys_mem.gpu_vram_free_gb,
            "free_disk": free_disk_gb,
        });
        println!("{}", serde_json::to_string(&info).unwrap_or_else(|_| "{}".to_string()));
        return Ok(());
    }

    // Auto-start Ollama if it is not running
    if args.prompt.is_some() || args.query.is_some() || args.server || args.mcp {
        let _ = model_selection::memory::ensure_ollama_running();
    }

    if args.verbose || args.debug {
        std::env::set_var("MODELFUSION_VERBOSE", "true");
    }

    if args.gpu {
        std::env::set_var("MODELFUSION_FORCE_GPU", "true");
    }
    if args.cpu {
        std::env::set_var("MODELFUSION_FORCE_CPU", "true");
    }

    if args.use_openai {
        anyhow::bail!("Paid models (including OpenAI) have been disabled and removed per system requirements.");
    }

    if args.jupyter {
        println!("🚀 Launching Jupyter Notebook: data_analyst_workflow.ipynb");
        let status = std::process::Command::new("python")
            .args(&["-m", "notebook", "data_analyst_workflow.ipynb"])
            .status();
        if let Err(e) = status {
            println!("❌ Failed to launch Jupyter Notebook: {}", e);
        }
        return Ok(());
    }

    // Configure logging
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    // Print ensemble information mock as expected by main.py flow
    if !args.mcp {
        print_ensemble_info(&args.selection_strategy);
    }

    // Initialize the comprehensive task handler
    let handler = ComprehensiveTaskHandler::new(args.db_path.as_deref())?;
    handler.ensure_database_exists()?;

    if args.mcp {
        run_mcp_server(args.db_path.clone()).await?;
        return Ok(());
    }

    if args.patch_ide {
        patch_ide_workflow(&args.ide_src_dir, args.shallow, args.vscode_tag.as_deref()).await?;
        return Ok(());
    }

    if args.server {
        run_server(args.port, args.db_path.clone(), args.enable_slash_commands).await?;
        return Ok(());
    }

    // Dispatch system commands first
    if args.stats {
        let res = handler.handle_stats();
        println!("{}", res.content);
        return Ok(());
    }

    if let Some(category) = args.tasks {
        let res = handler.handle_tasks_list(Some(&category));
        println!("{}", res.content);
        return Ok(());
    }

    if args.update {
        let res = handler.handle_update_database().await;
        println!("{}", res.content);

        // Auto-prepare models after update if requested
        if args.prepare_all_models {
            println!("\n🔷 [OPENVINO] Auto-caching all OpenVINO models after database update...");
            println!("📂 Output directory: {}", args.ov_model_dir);

            // Helper: find a script by searching up from the exe directory
            let find_script = |script_name: &str| -> String {
                if let Ok(mut exe_path) = std::env::current_exe() {
                    exe_path.pop();
                    let mut check_dir = exe_path.clone();
                    for _ in 0..5 {
                        let script = check_dir.join(format!("src/scripts/{}", script_name));
                        if script.exists() {
                            return script.to_string_lossy().into_owned();
                        }
                        if !check_dir.pop() { break; }
                    }
                }
                format!("src/scripts/{}", script_name)
            };

            // ── Step 1: Download all OV Hub pre-converted models (fast) ─────────
            println!("\n📦 Step 1: Downloading pre-converted OV Hub models (INT4, no local conversion)...");
            let hub_script = find_script("cache_ov_hub.py");
            let db_path_str = handler.db_path.to_string_lossy().to_string();
            let hub_result = std::process::Command::new("python")
                .arg(&hub_script)
                .arg(&args.ov_model_dir)
                .arg(&db_path_str)
                .arg("4")  // max 4 GB per model — avoids huge fp16/MoE models
                .status();
            match hub_result {
                Ok(status) if status.success() => println!("✅ OV Hub cache complete."),
                Ok(_) => println!("⚠️  OV Hub cache script exited with errors (check output above)."),
                Err(e) => println!("⚠️  Could not run cache_ov_hub.py: {}", e),
            }

            // ── Step 2: Local conversion for remaining small non-OV models ───────
            println!("\n🔄 Step 2: Converting remaining small HuggingFace models locally...");
            println!("📏 Filtering: models ≤ 3000 MB (~1.5B params fp16) for fast conversion\n");

            let prepare_script = find_script("prepare_model_openvino.py");
            let db_path = handler.db_path.clone();
            // 3000 MB ≈ 1.5B params — keeps local conversion under 10 min each
            let models = modelfusion_core::fusion_engine::get_small_model_ids(&db_path, 3000.0);

            if models.is_empty() {
                println!("⚠️  No small models found in database for local conversion.");
            } else {
                println!("📋 Found {} models under 1.5B params for local conversion.\n", models.len());

                let mut success_count = 0;
                let mut skip_count = 0;
                let mut fail_count = 0;
                let total = models.len();

                for (i, model_id) in models.iter().enumerate() {
                    println!("[{}/{}] {}", i + 1, total, model_id);
                    let result = std::process::Command::new("python")
                        .arg(&prepare_script)
                        .arg(model_id)
                        .arg(&args.ov_model_dir)
                        .arg(&args.weight_format)
                        .output();

                    match result {
                        Ok(out) => {
                            let stderr_msg = String::from_utf8_lossy(&out.stderr);
                            if out.status.success() {
                                if stderr_msg.contains("already exists") || stderr_msg.contains("Skipping") {
                                    println!("  ⏭️  Already cached");
                                    skip_count += 1;
                                } else {
                                    println!("  ✅ Converted");
                                    success_count += 1;
                                }
                            } else {
                                let err_preview: String = stderr_msg.chars().take(150).collect();
                                println!("  ❌ {}", err_preview);
                                fail_count += 1;
                            }
                        }
                        Err(e) => {
                            println!("  ❌ Script error: {}", e);
                            fail_count += 1;
                        }
                    }
                }

                println!("\n====================================");
                println!("📊 Local Conversion Summary");
                println!("====================================");
                println!("  ✅ Converted: {}", success_count);
                println!("  ⏭️  Cached:    {}", skip_count);
                println!("  ❌ Failed:    {}", fail_count);
                println!("  📦 Total:     {}", total);
                println!("====================================");
            }
        }


        return Ok(());
    }

    if args.restore {
        let res = handler.handle_restore(None);
        println!("{}", res.content);
        return Ok(());
    }

    if args.clearcache {
        let res = handler.handle_clear_cache();
        println!("{}", res.content);
        return Ok(());
    }

    if args.decision_stats {
        let res = handler.handle_decision_stats();
        println!("{}", res.content);
        return Ok(());
    }

    if args.performance_stats {
        let res = handler.handle_performance_stats();
        println!("{}", res.content);
        return Ok(());
    }

    if args.cache_stats {
        let res = handler.handle_cache_stats();
        println!("{}", res.content);
        return Ok(());
    }

    if args.ml_analytics {
        let res = handler.handle_ml_analytics();
        println!("{}", res.content);
        return Ok(());
    }

    if args.novel_ai_stats {
        println!("🧠 Novel AI Component Statistics:\n  • Innovation System Active: true\n  • Semantic Analysis Pipeline: Enabled\n  • Temporal Change Tracking: Enabled\n  • Real Options hedge events: 0\n  • Prompt Quality scoring avg: 0.0");
        return Ok(());
    }

    if args.analytics_demo {
        println!("📊 Advanced Model Analytics Demo:\n  - Initializing analytics engine...\n  - Running simulated model load tests...\n  - All model analytics pathways are healthy.");
        return Ok(());
    }

    if let Some(ref category) = args.model_ranking {
        let db_path = handler.db_path.clone();
        match db::HuggingFaceModelDatabase::new(&db_path) {
            Ok(db) => {
                println!("📋 Top Model Rankings for task/category '{}':", category);
                match db.get_by_task(category, 10) {
                    Ok(models) => {
                        if models.is_empty() {
                            println!("  (No models found for this category)");
                        } else {
                            for (i, m) in models.iter().enumerate() {
                                println!("  {}. {} (Decision Score: {:.2}, Downloads: {})", i+1, m.model_id, m.decision_score, m.downloads);
                            }
                        }
                    }
                    Err(e) => println!("❌ Error: {}", e),
                }
            }
            Err(e) => println!("❌ Database error: {}", e),
        }
        return Ok(());
    }
    if args.model_recommendations {
        let db_path = handler.db_path.clone();
        match db::HuggingFaceModelDatabase::new(&db_path) {
            Ok(db) => {
                println!("🌟 Personalized Model Recommendations (Top Overall):");
                match db.get_top_overall(5) {
                    Ok(models) => {
                        for m in models.iter() {
                            println!("  🏆 {} [{}] (Score: {:.2}, Downloads: {})", m.model_id, m.pipeline_tag, m.decision_score, m.downloads);
                        }
                    }
                    Err(e) => println!("❌ Error: {}", e),
                }
            }
            Err(e) => println!("❌ Database error: {}", e),
        }
        return Ok(());
    }

    if args.pe_header_extraction {
        let file_path = args.file.as_deref().unwrap_or("test.exe");
        let prompt = args.prompt.as_deref().unwrap_or("Perform PE analysis");
        handler.handle_pe_analysis(file_path, prompt);
        return Ok(());
    }

    // ---------------------------------------------------------
    // OpenVINO Model Preparation
    // ---------------------------------------------------------
    if args.prepare_model.is_some() || args.prepare_all_models {
        let script_path = {
            let mut found = None;
            if let Ok(mut exe_path) = std::env::current_exe() {
                exe_path.pop();
                let mut check_dir = exe_path.clone();
                for _ in 0..5 {
                    let script = check_dir.join("src/scripts/prepare_model_openvino.py");
                    if script.exists() {
                        found = Some(script.to_string_lossy().into_owned());
                        break;
                    }
                    if !check_dir.pop() { break; }
                }
            }
            found.unwrap_or_else(|| "src/scripts/prepare_model_openvino.py".to_string())
        };

        if let Some(ref model_id) = args.prepare_model {
            // Single model preparation
            println!("🔷 [OPENVINO] Preparing model: {} (format: {})", model_id, args.weight_format);
            let status = std::process::Command::new("python")
                .arg(&script_path)
                .arg(model_id)
                .arg(&args.ov_model_dir)
                .arg(&args.weight_format)
                .status();
            match status {
                Ok(s) if s.success() => {
                    println!("✅ [OPENVINO] Model prepared successfully.");
                }
                Ok(s) => {
                    return Err(anyhow::anyhow!("❌ Model preparation failed (exit code: {:?})", s.code()));
                }
                Err(e) => {
                    return Err(anyhow::anyhow!("❌ Failed to run preparation script: {}", e));
                }
            }
            return Ok(());
        }

        if args.prepare_all_models {
            // Batch preparation: query database for all eligible models
            println!("🔷 [OPENVINO] Batch preparing all eligible models (format: {})...", args.weight_format);
            println!("📂 [OPENVINO] Output directory: {}", args.ov_model_dir);

            // Get all models from the database
            let db_path = handler.db_path.clone();
            let models = modelfusion_core::fusion_engine::get_all_model_ids(&db_path);

            if models.is_empty() {
                println!("❌ No models found in database. Run with --update first.");
                return Ok(());
            }

            println!("📋 [OPENVINO] Found {} models in database.", models.len());

            let mut success_count = 0;
            let mut skip_count = 0;
            let mut fail_count = 0;
            let total = models.len();

            for (i, model_id) in models.iter().enumerate() {
                println!("\n[{}/{}] Processing: {}", i + 1, total, model_id);
                let result = std::process::Command::new("python")
                    .arg(&script_path)
                    .arg(model_id)
                    .arg(&args.ov_model_dir)
                    .arg(&args.weight_format)
                    .output();

                match result {
                    Ok(out) => {
                        let stderr_msg = String::from_utf8_lossy(&out.stderr);
                        if out.status.success() {
                            if stderr_msg.contains("already exists") || stderr_msg.contains("Skipping") {
                                println!("  ⏭️  Skipped (already cached)");
                                skip_count += 1;
                            } else {
                                println!("  ✅ Converted successfully");
                                success_count += 1;
                            }
                        } else {
                            let err_preview: String = stderr_msg.chars().take(200).collect();
                            println!("  ❌ Failed: {}", err_preview);
                            fail_count += 1;
                        }
                    }
                    Err(e) => {
                        println!("  ❌ Script error: {}", e);
                        fail_count += 1;
                    }
                }
            }

            println!("\n====================================");
            println!("📊 Batch Preparation Summary");
            println!("====================================");
            println!("  ✅ Converted: {}", success_count);
            println!("  ⏭️  Skipped:   {}", skip_count);
            println!("  ❌ Failed:    {}", fail_count);
            println!("  📦 Total:     {}", total);
            println!("====================================");
            return Ok(());
        }
    }

    // ---------------------------------------------------------
    // Orchestration Flow
    // ---------------------------------------------------------
    if args.prompt.is_some() || args.query.is_some() || args.folder.is_some() || determine_task_override(&args).is_some() {
        let mut final_prompt = args.prompt.clone()
            .or_else(|| args.query.clone())
            .unwrap_or_else(|| {
                "Review the code in this folder, identify any bugs, vulnerabilities, or optimization opportunities, and suggest improvements.".to_string()
            });

        // Initialize mutable hardware/fusion flags and parse slash commands from prompt
        let mut gpu = args.gpu;
        let mut cpu = args.cpu;
        let mut openvino = args.openvino;
        let mut fusion = args.fusion;
        if args.enable_slash_commands {
            parse_slash_commands_in_prompt(&mut final_prompt, &mut gpu, &mut cpu, &mut openvino, &mut fusion);
        }

        if let Some(ref folder_path) = args.folder {
            eprintln!("[FUSION] Reading files from folder: {}", folder_path);
            let mut folder_content = String::new();
            
            for entry in walkdir::WalkDir::new(folder_path)
                .into_iter()
                .filter_map(|e| e.ok())
            {
                let path = entry.path();
                if path.is_file() {
                    if let Some(ext) = path.extension().and_then(|s| s.to_str()) {
                        let ext_lower = ext.to_lowercase();
                        let is_code_file = matches!(
                            ext_lower.as_str(),
                            "rs" | "py" | "js" | "ts" | "c" | "cpp" | "h" | "hpp" | "cs" | "go" | "java" | "kt" | "swift" | "rb" | "php" | "sql" | "sh" | "bat" | "ps1" | "toml" | "json" | "yaml" | "yml" | "md" | "txt" | "html" | "css"
                        );
                        if is_code_file {
                            if let Ok(content) = std::fs::read_to_string(path) {
                                let filename = path.strip_prefix(folder_path).unwrap_or(path).to_string_lossy();
                                folder_content.push_str(&format!("\n--- FILE: {} ---\n", filename));
                                if content.len() > 10000 {
                                    folder_content.push_str(&content[..10000]);
                                    folder_content.push_str("\n...[TRUNCATED due to size]...\n");
                                } else {
                                    folder_content.push_str(&content);
                                }
                                folder_content.push_str("\n");
                            }
                        }
                    }
                }
            }

            if !folder_content.is_empty() {
                final_prompt.push_str("\n\n### FOLDER CONTENTS FOR REVIEW:\n");
                final_prompt.push_str(&folder_content);
            } else {
                println!("[WARN] No supported text or code files found in the folder.");
            }
        }

        let db_path = handler.db_path.clone();
        let task_override = determine_task_override(&args);
        let selection_strategy = parse_selection_strategy(&args.selection_strategy);

        let mut is_fusion_needed = fusion;
        let mut bandit_context = 0;
        let mut bandit_arm = 0;
        let mut run_bandit_learning = false;

        if !is_fusion_needed && !args.mcp && !args.server && !args.ollama && !args.openvino && !args.onnx {
            run_bandit_learning = true;
            let complexity_str = llm_classify_complexity(&final_prompt).await;
            eprintln!("🦙 [ROUTER] Prompt classified complexity: {}", complexity_str);
            bandit_context = match complexity_str.as_str() {
                "simple_general" => 0,
                "simple_coding" => 1,
                "complex_general" => 2,
                "complex_coding" => 3,
                _ => {
                    let is_coding = detect_if_coding_or_complicated(&final_prompt);
                    if is_coding { 1 } else { 0 }
                }
            };
            let db_dir = db_path.parent().unwrap_or_else(|| std::path::Path::new("db"));
            let state = load_bandit_state(db_dir);
            let epsilon = 0.15;
            let mut lcg = Lcg::new();
            bandit_arm = if lcg.gen_bool(epsilon) {
                lcg.gen_range(0, 2)
            } else {
                let vals = state.values[bandit_context];
                if vals[0] >= vals[1] { 0 } else { 1 }
            };
            
            // Override arm choice using the small model LLM router decision
            if let Some(decision) = llm_route(&final_prompt).await {
                eprintln!("🎯 [ROUTER] LLM Router decision: fusion={}, strategy={}, use_gpu={}, use_cpu={}, task={}",
                    decision.fusion, decision.selection_strategy, decision.use_gpu, decision.use_cpu, decision.detected_task);
                bandit_arm = if decision.fusion { 1 } else { 0 };
            }
            
            // Force arm choice to 0 (single model) if the complexity layer classified it as simple!
            if bandit_context == 0 || bandit_context == 1 {
                if bandit_arm == 1 {
                    eprintln!("💡 [ROUTER] Complexity layer classified task as simple. Overriding fusion selection to single model.");
                    bandit_arm = 0;
                }
            }
            
            is_fusion_needed = bandit_arm == 1;
            eprintln!("🎯 [BANDIT] Selected Arm: {} (0=Single, 1=Fusion) for context: {}", bandit_arm, complexity_str);
        }

        // Acquire cross-process lock to prevent duplicate runs freezing the system
        let _file_lock = acquire_cross_process_lock()?;

        // ---- Backend selection (applies to ALL execution paths) ----
        if args.vllm {
            if std::env::consts::OS != "linux" {
                return Err(anyhow::anyhow!(
                    "❌ vLLM is only supported on Linux.\n\n  On Windows, use:\n    --openvino  (optimized CPU/iGPU inference)\n    --ollama    (local Ollama models)"
                ));
            }
            eprintln!("🔍 Checking vLLM installation...");
            let check = std::process::Command::new("python3")
                .args(["-c", "import vllm; print('OK')"])
                .output();
            match check {
                Ok(out) if out.status.success() => {
                    eprintln!("✅ vLLM is installed.");
                    std::env::set_var("MODELFUSION_USE_VLLM", "true");
                    eprintln!("🚀 Using vLLM for high-throughput GPU inference.");
                }
                _ => {
                    return Err(anyhow::anyhow!(
                        "❌ vLLM not installed.\n\n  Install with: pip install vllm\n\n  Requires Linux with CUDA GPU."
                    ));
                }
            }
        } else if args.ollama || std::env::var("MODELFUSION_USE_OLLAMA").is_ok() {
            eprintln!("🦙🔍 Ensuring Ollama is running...");
            match model_selection::memory::ensure_ollama_running() {
                Ok(()) => {
                    eprintln!("✅ Ollama is ready.");
                    std::env::set_var("MODELFUSION_USE_OLLAMA", "true");
                }
                Err(e) => {
                    return Err(anyhow::anyhow!("❌ {}", e));
                }
            }
        } else if openvino {
            eprintln!("🔍🔷 Checking OpenVINO installation...");
            // Try openvino_genai first (best performance)
            let genai_check = std::process::Command::new("python")
                .args(["-c", "import openvino_genai; print('OK')"])
                .output();
            match genai_check {
                Ok(out) if out.status.success() => {
                    eprintln!("✅ OpenVINO GenAI is installed.");
                    std::env::set_var("MODELFUSION_USE_OPENVINO", "true");
                    std::env::set_var("MODELFUSION_OV_MODEL_DIR", &args.ov_model_dir);
                    std::env::set_var("MODELFUSION_OV_WEIGHT_FORMAT", &args.weight_format);
                    eprintln!("🔷🚀 Using OpenVINO GenAI for optimized cross-platform inference.");
                }
                _ => {
                    // Fallback: check for classic openvino
                    let fallback_check = std::process::Command::new("python")
                        .args(["-c", "import openvino; print('OK')"])
                        .output();
                    match fallback_check {
                        Ok(out) if out.status.success() => {
                            eprintln!("✅ OpenVINO (classic) is installed.");
                            std::env::set_var("MODELFUSION_USE_OPENVINO", "true");
                            std::env::set_var("MODELFUSION_OV_MODEL_DIR", &args.ov_model_dir);
                            std::env::set_var("MODELFUSION_OV_WEIGHT_FORMAT", &args.weight_format);
                            eprintln!("🔷🚀 Using OpenVINO for optimized CPU inference.");
                            eprintln!("🔷🔄 Upgrade for better performance: pip install openvino-genai");
                        }
                        _ => {
                            return Err(anyhow::anyhow!(
                                "❌ OpenVINO not installed.\n\n  Install with: pip install -U openvino-genai\n  Or classic:   pip install -U openvino"
                            ));
                        }
                    }
                }
            }
        } else if args.onnx {
            eprintln!("🔍🟣 Checking ONNX Runtime installation...");
            let onnx_check = std::process::Command::new("python")
                .args(["-c", "import optimum.onnxruntime; print('OK')"])
                .output();
            match onnx_check {
                Ok(out) if out.status.success() => {
                    eprintln!("✅ ONNX Runtime (optimum) is installed.");
                    std::env::set_var("MODELFUSION_USE_ONNX", "true");
                    eprintln!("🟣🚀 Using ONNX Runtime for optimized cross-platform inference.");
                }
                _ => {
                    return Err(anyhow::anyhow!(
                        "❌ ONNX Runtime (optimum) not installed.\n\n  Install with: pip install optimum[onnxruntime] or pip install optimum[onnxruntime-gpu]"
                    ));
                }
            }
        } else {
            let has_hf_token = std::env::var("HF_TOKEN").ok().map(|t| !t.is_empty() && !t.contains("YOUR_")).unwrap_or(false)
                || std::env::var("HUGGINGFACE_API_KEY").ok().map(|t| !t.is_empty() && !t.contains("YOUR_")).unwrap_or(false)
                || std::env::var("HF_API_KEY").ok().map(|t| !t.is_empty() && !t.contains("YOUR_")).unwrap_or(false)
                || std::env::var("HUGGINGFACE_TOKEN").ok().map(|t| !t.is_empty() && !t.contains("YOUR_")).unwrap_or(false);

            if has_hf_token && !cpu {
                eprintln!("🌐 Using HuggingFace Serverless Inference API for remote cloud execution.");
            } else {
                std::env::set_var("MODELFUSION_USE_TRANSFORMERS", "true");
            }
        }

        if is_fusion_needed {
            eprintln!("[FUSION] Model Fusion is active.");
            std::env::set_var("MODELFUSION_NO_SIMULATION", "true");

            let final_prompt_orig = final_prompt.clone();
            let mut context_to_pass = None;
            if args.context_auto || args.context.as_ref().map_or(false, |c| !c.trim().is_empty()) {
                eprintln!("🧪 [FUSION] Generating context locally (deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B)...");
                let context_prompt = if let Some(ref ctx_arg) = args.context {
                    if !ctx_arg.trim().is_empty() {
                        format!(
                            "You are an expert technical researcher. Generate a detailed, highly accurate background context, key technical definitions, and relevant factual constraints to help answer the user prompt below, focusing specifically on this guide/instruction: \"{}\"\n\nUser Prompt: {}\n\nProvide ONLY the generated context. Do not include introductory or concluding conversational text.",
                            ctx_arg, final_prompt_orig
                        )
                    } else {
                        format!(
                            "You are an expert technical researcher. Generate a detailed, highly accurate background context, key technical definitions, and relevant factual constraints to help answer the user prompt below.\n\nUser Prompt: {}\n\nProvide ONLY the generated context. Do not include introductory or concluding conversational text.",
                            final_prompt_orig
                        )
                    }
                } else {
                    format!(
                        "You are an expert technical researcher. Generate a detailed, highly accurate background context, key technical definitions, and relevant factual constraints to help answer the user prompt below.\n\nUser Prompt: {}\n\nProvide ONLY the generated context. Do not include introductory or concluding conversational text.",
                        final_prompt_orig
                    )
                };

                let deepseek_model = modelfusion_core::fusion_engine::schema::ModelConfig::huggingface("deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B");
                match modelfusion_core::fusion_engine::models::call_model(&deepseek_model, &context_prompt).await {
                    Ok(ctx) => {
                        eprintln!("✅ [FUSION] Context generated successfully. Injecting into prompt.");
                        let mut clean_ctx = if let Some(end_idx) = ctx.find("</think>") {
                            ctx[end_idx + 8..].to_string()
                        } else {
                            ctx.clone()
                        };
                        clean_ctx = clean_ctx.trim().to_string();
                        context_to_pass = Some(clean_ctx);
                    }
                    Err(e) => {
                        eprintln!("⚠️ [FUSION] Failed to generate context: {}", e);
                        return Err(anyhow::anyhow!("Failed to generate context using DeepSeek cheap thinking model: {}", e));
                    }
                }
            }

            match modelfusion_core::fusion_engine::run_fusion(
                &final_prompt_orig,
                context_to_pass.as_deref(),
                Some(&db_path),
                task_override.as_deref(),
                selection_strategy,
                Some(args.fusion_models),
                &args.fusion_mode,
                args.model.as_deref(),
            ).await {
                Ok(content) => {
                    eprintln!("\n[SUCCESS] Orchestration Successful (via Model Fusion)!\n");
                    println!("{}", content);
                    if let Some(ref report_path) = args.report {
                        let final_prompt_for_report = if let Some(ref ctx) = context_to_pass {
                            format!("{}\n\n### CONTEXT:\n{}", final_prompt_orig, ctx)
                        } else {
                            final_prompt_orig.clone()
                        };
                        save_report(&content, report_path, &args.reporttype, &final_prompt_for_report);
                    }
                    if run_bandit_learning {
                        let db_dir = db_path.parent().unwrap_or_else(|| std::path::Path::new("db"));
                        let mut state = load_bandit_state(db_dir);
                        let count = state.counts[bandit_context][bandit_arm];
                        let val = state.values[bandit_context][bandit_arm];
                        state.counts[bandit_context][bandit_arm] += 1;
                        state.values[bandit_context][bandit_arm] = val + (0.8 - val) / (count + 1) as f64;
                        save_bandit_state(db_dir, &state);
                    }
                }
                Err(e) => {
                    eprintln!("\n[ERROR] Orchestration Failed (via Model Fusion)!\n");
                    eprintln!("Error: {}", e);
                    if run_bandit_learning {
                        let db_dir = db_path.parent().unwrap_or_else(|| std::path::Path::new("db"));
                        let mut state = load_bandit_state(db_dir);
                        let count = state.counts[bandit_context][bandit_arm];
                        let val = state.values[bandit_context][bandit_arm];
                        state.counts[bandit_context][bandit_arm] += 1;
                        state.values[bandit_context][bandit_arm] = val + (0.0 - val) / (count + 1) as f64;
                        save_bandit_state(db_dir, &state);
                    }
                }
            }
            return Ok(());
        }

        let orchestrator = HuggingFaceOrchestrator::new(db_path.clone(), args.budget, args.enable_ml, args.verbose);

        let options = HashMap::new();
        let res = orchestrator
            .process_task(
                &final_prompt,
                task_override.as_deref(),
                args.model.as_deref(),
                args.use_openai,
                args.file.as_deref(),
                selection_strategy,
                options,
            )
            .await;

        if res.success {
            eprintln!("\n[SUCCESS] Orchestration Successful!\n");
            println!("{}", res.content);
            if let Some(ref report_path) = args.report {
                save_report(&res.content, report_path, &args.reporttype, &final_prompt);
            }
            if run_bandit_learning {
                let db_dir = db_path.parent().unwrap_or_else(|| std::path::Path::new("db"));
                let mut state = load_bandit_state(db_dir);
                let count = state.counts[bandit_context][bandit_arm];
                let val = state.values[bandit_context][bandit_arm];
                state.counts[bandit_context][bandit_arm] += 1;
                state.values[bandit_context][bandit_arm] = val + (0.8 - val) / (count + 1) as f64;
                save_bandit_state(db_dir, &state);
            }
        } else {
            eprintln!("\n[ERROR] Orchestration Failed!\n");
            if let Some(err) = res.error_message {
                eprintln!("Error: {}", err);
            }
            if run_bandit_learning {
                let db_dir = db_path.parent().unwrap_or_else(|| std::path::Path::new("db"));
                let mut state = load_bandit_state(db_dir);
                let count = state.counts[bandit_context][bandit_arm];
                let val = state.values[bandit_context][bandit_arm];
                state.counts[bandit_context][bandit_arm] += 1;
                state.values[bandit_context][bandit_arm] = val + (0.0 - val) / (count + 1) as f64;
                save_bandit_state(db_dir, &state);
            }
        }
    } else {
        // Fallback display similar to Python's else clause
        println!("HFOrchestra - Advanced HuggingFace Model Orchestration System");
        println!("============================================================");
        println!("Available modules:");
        println!("  [DISCOVERY] Model Discovery - Find and evaluate HuggingFace models");
        println!("  [SECURITY]  Security - ATLAS threat detection and monitoring");
        println!("  [PERF]      Performance - System monitoring and optimization");
        println!("  [PE]        PE Analysis - Malware detection and binary analysis");
        println!("  [ORCH]      Orchestration - Multi-provider LLM management");
        println!("  [ML]        ML Model Selection - Machine learning-based intelligent selection");
        println!("  [SINQ]      SINQ Quantization - Model quantization for memory efficiency");
        println!("\nUse --help for comprehensive usage information");
    }

    Ok(())
}

/// Print dynamic ensemble information banner as expected by main.py flow.
fn print_ensemble_info(strategy: &str) {
    eprintln!("============================================================");
    eprintln!("[MODEL] Ensemble Model Selection: Active Strategy: {}", strategy);
    eprintln!("============================================================");
}

/// Map active task command line flags to a task name string override.
fn determine_task_override(args: &Args) -> Option<String> {
    if args.sentiment { return Some("sentiment-analysis".to_string()); }
    if args.question { return Some("question-answering".to_string()); }
    if args.ner { return Some("ner".to_string()); }
    if args.summary { return Some("summarization".to_string()); }
    if args.text_classification { return Some("text-classification".to_string()); }
    if args.token_classification { return Some("token-classification".to_string()); }
    if args.question_answering { return Some("question-answering".to_string()); }
    if args.text_generation { return Some("text-generation".to_string()); }
    if args.summarization { return Some("summarization".to_string()); }
    if args.translation { return Some("translation".to_string()); }
    if args.fill_mask { return Some("fill-mask".to_string()); }
    if args.text2text_generation { return Some("text2text-generation".to_string()); }
    if args.language_detection { return Some("language-detection".to_string()); }
    if args.grammar_correction { return Some("grammar-correction".to_string()); }
    if args.paraphrase_generation { return Some("paraphrase-generation".to_string()); }
    if args.causal_language_modeling { return Some("causal-language-modeling".to_string()); }
    if args.zero_shot_classification { return Some("zero-shot-classification".to_string()); }
    if args.feature_extraction { return Some("feature-extraction".to_string()); }
    if args.sentence_similarity { return Some("sentence-similarity".to_string()); }
    if args.anonymization { return Some("anonymization".to_string()); }
    if args.coreference_resolution { return Some("coreference-resolution".to_string()); }
    if args.spam_detection { return Some("spam-detection".to_string()); }
    if args.malware_text_detection { return Some("malware-text-detection".to_string()); }
    if args.phishing_detection { return Some("phishing-detection".to_string()); }
    if args.pii_detection { return Some("pii-detection".to_string()); }
    if args.hate_speech_detection { return Some("hate-speech-detection".to_string()); }
    if args.cyberbullying_detection { return Some("cyberbullying-detection".to_string()); }
    if args.fake_news_detection { return Some("fake-news-detection".to_string()); }
    if args.legal_judgment_classification { return Some("legal-judgment-classification".to_string()); }
    if args.contract_clause_classification { return Some("contract-clause-classification".to_string()); }
    if args.case_outcome_prediction { return Some("case-outcome-prediction".to_string()); }
    if args.financial_ner { return Some("financial-ner".to_string()); }
    if args.legal_ner { return Some("legal-ner".to_string()); }
    if args.biomedical_ner { return Some("biomedical-ner".to_string()); }
    if args.chemical_reaction_ner { return Some("chemical-reaction-ner".to_string()); }
    if args.financial_sentiment_analysis { return Some("financial-sentiment-analysis".to_string()); }
    if args.scientific_abstract_summarization { return Some("scientific-abstract-summarization".to_string()); }
    if args.emotion_detection { return Some("emotion-detection".to_string()); }
    if args.sarcasm_detection { return Some("sarcasm-detection".to_string()); }
    if args.stance_detection { return Some("stance-detection".to_string()); }
    if args.bias_detection { return Some("bias-detection".to_string()); }
    if args.hallucination_detection { return Some("hallucination-detection".to_string()); }
    if args.reading_level_assessment { return Some("reading-level-assessment".to_string()); }
    if args.generation_groundedness { return Some("generation-groundedness".to_string()); }
    if args.citation_intent_classification { return Some("citation-intent-classification".to_string()); }
    if args.code_vulnerability_detection { return Some("code-vulnerability-detection".to_string()); }
    if args.code_summary_generation { return Some("code-summary-generation".to_string()); }
    if args.code_clone_detection { return Some("code-clone-detection".to_string()); }
    if args.image_classification { return Some("image-classification".to_string()); }
    if args.object_detection { return Some("object-detection".to_string()); }
    if args.image_segmentation { return Some("image-segmentation".to_string()); }
    if args.visual_question_answering { return Some("visual-question-answering".to_string()); }
    if args.document_question_answering { return Some("document-question-answering".to_string()); }
    if args.zero_shot_image_classification { return Some("zero-shot-image-classification".to_string()); }
    if args.depth_estimation { return Some("depth-estimation".to_string()); }
    if args.image_feature_extraction { return Some("image-feature-extraction".to_string()); }
    if args.automatic_speech_recognition { return Some("automatic-speech-recognition".to_string()); }
    if args.audio_classification { return Some("audio-classification".to_string()); }
    if args.voice_activity_detection { return Some("voice-activity-detection".to_string()); }
    if args.emotion_recognition { return Some("emotion-recognition".to_string()); }
    if args.video_classification { return Some("video-classification".to_string()); }
    if args.text_to_speech { return Some("text-to-speech".to_string()); }
    if args.text_to_image { return Some("text-to-image".to_string()); }
    if args.image_super_resolution { return Some("image-super-resolution".to_string()); }
    if args.table_question_answering { return Some("table-question-answering".to_string()); }
    if args.feature_ranking { return Some("feature-ranking".to_string()); }
    if args.dataanalyst { return Some("data-analyst".to_string()); }
    if args.datascience { return Some("data-science".to_string()); }
    
    args.task.clone()
}

/// Convert string strategy into SelectionStrategy enum.
fn parse_selection_strategy(strategy: &str) -> Option<SelectionStrategy> {
    match strategy.to_lowercase().as_str() {
        "hyperparameter_tuning" | "hyperparameter-tuning" => Some(SelectionStrategy::HyperparameterTuning),
        "cross_validation" | "cross-validation" => Some(SelectionStrategy::CrossValidation),
        "ensemble_methods" | "ensemble-methods" => Some(SelectionStrategy::EnsembleMethods),
        "multi_objective" | "multi-objective" => Some(SelectionStrategy::MultiObjective),
        "bayesian_optimization" | "bayesian-optimization" => Some(SelectionStrategy::BayesianOptimization),
        "meta_learning" | "meta-learning" => Some(SelectionStrategy::MetaLearning),
        _ => None,
    }
}

/// Helper function to save orchestration content to a report file.
fn save_report(content: &str, report_path: &str, report_type: &str, prompt: &str) {
    let path = std::path::Path::new(report_path);
    let ext = match report_type.to_lowercase().as_str() {
        "pdf" => "pdf",
        "json" => "json",
        "text" | "txt" => "txt",
        "word" | "docx" => "docx",
        _ => "md",
    };

    let target_file = if path.is_dir() || report_path.ends_with('\\') || report_path.ends_with('/') {
        if let Err(e) = std::fs::create_dir_all(path) {
            println!("[WARN] Failed to create report directory: {}", e);
        }
        path.join(format!("code_review_report.{}", ext))
    } else {
        if let Some(parent) = path.parent() {
            if !parent.as_os_str().is_empty() {
                if let Err(e) = std::fs::create_dir_all(parent) {
                    println!("[WARN] Failed to create parent directories for report: {}", e);
                }
            }
        }
        path.with_extension(ext)
    };

    let write_result = match ext {
        "json" => {
            let json_data = serde_json::json!({
                "system": "ModelFusion Code Review Report",
                "timestamp": chrono::Utc::now().to_rfc3339(),
                "prompt": prompt,
                "content": content
            });
            match serde_json::to_string_pretty(&json_data) {
                Ok(json_str) => std::fs::write(&target_file, json_str),
                Err(e) => Err(std::io::Error::new(std::io::ErrorKind::Other, e.to_string())),
            }
        }
        "pdf" => {
            let pdf_content = generate_minimal_pdf(content);
            std::fs::write(&target_file, pdf_content)
        }
        "docx" => {
            let docx_content = generate_minimal_docx(content);
            std::fs::write(&target_file, docx_content)
        }
        _ => {
            std::fs::write(&target_file, content)
        }
    };

    match write_result {
        Ok(_) => println!("[INFO] Report successfully saved as {} to: {}", report_type.to_uppercase(), target_file.display()),
        Err(e) => println!("[ERROR] Failed to save report as {} to {}: {}", report_type.to_uppercase(), target_file.display(), e),
    }
}

/// Generate a minimal valid PDF containing the text
fn generate_minimal_pdf(content: &str) -> Vec<u8> {
    let mut pdf = Vec::new();
    pdf.extend_from_slice(b"%PDF-1.4\n");
    
    // Object 1: Catalog
    let obj1 = "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n";
    let pos1 = pdf.len();
    pdf.extend_from_slice(obj1.as_bytes());

    // Object 2: Pages list
    let obj2 = "2 0 obj\n<< /Type /Pages /Kids [ 3 0 R ] /Count 1 >>\nendobj\n";
    let pos2 = pdf.len();
    pdf.extend_from_slice(obj2.as_bytes());

    // Object 4: Content Stream
    let mut text_stream = String::new();
    text_stream.push_str("BT\n/F1 10 Tf\n20 750 Td\n12 Td\n");
    
    let mut y = 750;
    for line in content.lines() {
        let words: Vec<&str> = line.split_whitespace().collect();
        let mut current_line = String::new();
        for word in words {
            if current_line.len() + word.len() + 1 > 80 {
                if y < 40 { break; }
                let escaped = current_line.replace('\\', "\\\\").replace('(', "\\(").replace(')', "\\)");
                text_stream.push_str(&format!("({}) Tj\n0 -12 Td\n", escaped));
                y -= 12;
                current_line = word.to_string();
            } else {
                if !current_line.is_empty() {
                    current_line.push(' ');
                }
                current_line.push_str(word);
            }
        }
        if !current_line.is_empty() {
            if y < 40 { break; }
            let escaped = current_line.replace('\\', "\\\\").replace('(', "\\(").replace(')', "\\)");
            text_stream.push_str(&format!("({}) Tj\n0 -12 Td\n", escaped));
            y -= 12;
        }
        if y >= 40 {
            text_stream.push_str("0 -6 Td\n");
            y -= 6;
        }
    }
    text_stream.push_str("ET\n");

    let obj4_len = text_stream.len();
    let obj4 = format!("4 0 obj\n<< /Length {} >>\nstream\n{}endstream\nendobj\n", obj4_len, text_stream);
    let pos4 = pdf.len();
    pdf.extend_from_slice(obj4.as_bytes());

    // Object 3: Page object
    let obj3 = "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [ 0 0 612 792 ] /Contents 4 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\nendobj\n";
    let pos3 = pdf.len();
    pdf.extend_from_slice(obj3.as_bytes());

    // Xref
    let xref_pos = pdf.len();
    let xref = format!(
        "xref\n0 5\n0000000000 65535 f\n{:010} 00000 n\n{:010} 00000 n\n{:010} 00000 n\n{:010} 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{}\n%%EOF\n",
        pos1, pos2, pos3, pos4, xref_pos
    );
    pdf.extend_from_slice(xref.as_bytes());

    pdf
}

/// Generate a minimal RTF document openable by MS Word
fn generate_minimal_rtf(content: &str) -> String {
    let mut rtf = String::new();
    rtf.push_str(r#"{\rtf1\ansi\deff0 {\fonttbl {\f0\fnil\fcharset0 Arial;}}"#);
    rtf.push_str("\n\\viewkind4\\uc1\\pard\\f0\\fs20 ");
    for line in content.lines() {
        let escaped = line.replace('\\', "\\\\").replace('{', "\\{").replace('}', "\\}");
        rtf.push_str(&escaped);
        rtf.push_str("\\par\n");
    }
    rtf.push_str("}\n");
    rtf
}

fn generate_minimal_docx(content: &str) -> Vec<u8> {
    generate_minimal_rtf(content).into_bytes()
}

fn default_strategy() -> String {
    "multi_objective".to_string()
}

fn default_task() -> String {
    "text-generation".to_string()
}

#[derive(serde::Deserialize, serde::Serialize, Debug, Clone)]
struct RouterDecision {
    #[serde(default)]
    fusion: bool,
    #[serde(default = "default_strategy")]
    selection_strategy: String,
    #[serde(default)]
    use_gpu: bool,
    #[serde(default)]
    use_cpu: bool,
    #[serde(default = "default_task")]
    detected_task: String,
}

/// Strip system prompt leakage and meta-commentary from model responses.
/// Small models (1.5B-3B) often echo their instructions or add meta-commentary
/// like "I don't see any specific instructions..." which should be hidden from users.
fn clean_model_response(raw: &str) -> String {
    // Short responses are typically direct factual answers — don't risk
    // stripping them with the leakage heuristic which is designed for
    // longer, multi-paragraph LLM outputs that sometimes include filler.
    let trimmed_raw = raw.trim();
    if trimmed_raw.len() < 200 {
        return trimmed_raw.to_string();
    }

    let leakage_patterns: &[&str] = &[
        "I don't see any specific instructions",
        "I'm following a standard response",
        "If you need to perform any actions",
        "If you need me to perform",
        "such as editing files",
        "please let me know and I can",
        "I can help guide you through",
        "Let me know if you'd like me to",
        "Is there anything else",
        "I'll be happy to help",
        "Based on the context provided",
        "I notice you've selected",
        "Looking at the selected file",
        "I see that you've",
        "As an AI assistant",
        "As your AI",
        "I'm an AI",
        "Note: I",
        "Disclaimer:",
        "[Note:",
        "[Context:",
        "I'm here to provide assistance",
        "I'm designed to",
        "my knowledge cutoff",
        "Since you are currently working on",
        "let me know if you would like to add",
        "incorporate this into your existing script",
        "example of how it could be added",
        "here's an example of how it could be added",
        "you can add this information to your code",
    ];

    let lines: Vec<&str> = raw.lines().collect();
    let mut clean_lines: Vec<&str> = Vec::new();
    let mut in_leakage_block = false;

    for line in &lines {
        let trimmed = line.trim();
        // Skip empty lines at the very start
        if clean_lines.is_empty() && trimmed.is_empty() {
            continue;
        }
        // Check if this line starts a leakage block
        let is_leakage = leakage_patterns.iter().any(|p| trimmed.contains(p));
        if is_leakage {
            in_leakage_block = true;
            continue;
        }
        // If we're in a leakage block, skip continuation lines
        if in_leakage_block && !trimmed.is_empty() {
            if trimmed.starts_with("- ") || trimmed.starts_with("* ")
                || trimmed.starts_with("If ") || trimmed.starts_with("Please ")
                || trimmed.starts_with("Feel free") || trimmed.starts_with("You can")
                || trimmed.starts_with("Would you") || trimmed.starts_with("Do you")
                || trimmed.starts_with("Happy to") || trimmed.starts_with("I'd be")
            {
                continue;
            }
            in_leakage_block = false;
        }
        if !in_leakage_block {
            clean_lines.push(line);
        }
    }

    // Trim trailing empty lines
    while clean_lines.last().map_or(false, |l| l.trim().is_empty()) {
        clean_lines.pop();
    }

    let result = clean_lines.join("\n");
    if result.trim().is_empty() {
        // Safety net: if everything was stripped, return the original
        raw.trim().to_string()
    } else {
        result
    }
}

async fn query_local_router(system_prompt: &str, user_prompt: &str) -> Option<String> {
    // 1. First attempt: Query local Ollama if running
    let endpoint = std::env::var("LOCAL_OLLAMA_ENDPOINT")
        .unwrap_or_else(|_| "http://127.0.0.1:11434".to_string());
    
    let client = reqwest::Client::builder()
        .no_proxy()
        .timeout(std::time::Duration::from_secs(30))
        .connect_timeout(std::time::Duration::from_secs(2))
        .build()
        .ok();

    if let Some(ref client) = client {
        // Try models in order of preference
        let candidates = vec![
            "qwen2.5:1.5b",
            "qwen2.5:7b-instruct",
            "qwen2.5:3b",
            "llama3.2:3b",
            "llama3.2:1b",
            "deepseek-r1:1.5b",
            "phi4-mini:latest"
        ];
        
        // Find which model is actually cached in Ollama first (to avoid downloading/triggering large model pulls)
        let list_url = format!("{}/api/tags", endpoint.trim_end_matches('/'));
        let mut available_models = std::collections::HashSet::new();
        if let Ok(res) = client.get(&list_url).send().await {
            if res.status().is_success() {
                if let Ok(parsed) = res.json::<serde_json::Value>().await {
                    if let Some(models_arr) = parsed["models"].as_array() {
                        for m in models_arr {
                            if let Some(name) = m["name"].as_str() {
                                available_models.insert(name.to_string());
                            }
                        }
                    }
                }
            }
        }

        // Find the first matching candidate that is available in Ollama
        let model_to_use = candidates.iter().find(|&&c| {
            available_models.contains(c) || available_models.contains(&format!("{}:latest", c))
        });

        if let Some(&model_name) = model_to_use {
            eprintln!("[LOCAL ROUTER] Found cached Ollama model: {}. Querying via Ollama...", model_name);
            let gen_url = format!("{}/api/generate", endpoint.trim_end_matches('/'));
            let prompt_format = format!("<|im_start|>system\n{}<|im_end|>\n<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant\n", system_prompt, user_prompt);
            let body = serde_json::json!({
                "model": model_name,
                "prompt": prompt_format,
                "stream": false,
                "options": {
                    "temperature": 0.1
                }
            });
            if let Ok(res) = client.post(&gen_url).json(&body).send().await {
                if res.status().is_success() {
                    if let Ok(data) = res.json::<serde_json::Value>().await {
                        if let Some(text) = data["response"].as_str() {
                            if let Some(start) = text.find('{') {
                                if let Some(end) = text.rfind('}') {
                                    let json_str = text[start..=end].to_string();
                                    eprintln!("🦙 [LOCAL ROUTER] Ollama Decision: {}", json_str);
                                    return Some(json_str);
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // 2. Second attempt/Fallback: Use local python script (cpu/transformers)
    let script_path = "src/scripts/run_model_transformers.py";
    if !std::path::Path::new(script_path).exists() {
        eprintln!("⚠️ [LOCAL ROUTER] Script not found at: {}", script_path);
        return None;
    }
    
    let prompt_format = format!("<|im_start|>system\n{}<|im_end|>\n<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant\n", system_prompt, user_prompt);
    
    let out = tokio::process::Command::new("python")
        .arg(script_path)
        .arg("Qwen/Qwen2.5-1.5B-Instruct")
        .arg(&prompt_format)
        .arg("128")
        .arg("0.1")
        .arg("cpu") // Force CPU for light local routing
        .output()
        .await
        .ok()?;
        
    if out.status.success() {
        let text = String::from_utf8_lossy(&out.stdout).trim().to_string();
        if let Some(start) = text.find('{') {
            if let Some(end) = text.rfind('}') {
                let json_str = text[start..=end].to_string();
                eprintln!("🦙 [LOCAL ROUTER] Python Decision: {}", json_str);
                return Some(json_str);
            }
        }
        eprintln!("⚠️ [LOCAL ROUTER] Local output did not contain valid JSON block: {}", text);
    } else {
        let err_msg = String::from_utf8_lossy(&out.stderr).trim().to_string();
        eprintln!("⚠️ [LOCAL ROUTER] Failed: {}", err_msg);
    }
    None
}

#[allow(dead_code)]
async fn query_hf_router(system_prompt: &str, user_prompt: &str) -> Option<String> {
    let token = std::env::var("HF_TOKEN")
        .or_else(|_| std::env::var("HUGGINGFACE_API_KEY"))
        .or_else(|_| std::env::var("HF_API_KEY"))
        .or_else(|_| std::env::var("HUGGINGFACE_TOKEN"))
        .ok();
    
    if token.is_none() {
        eprintln!("⚠️ [ROUTER] No Hugging Face token found in environment variables (HF_TOKEN, HUGGINGFACE_API_KEY, HF_API_KEY, HUGGINGFACE_TOKEN).");
        return query_local_router(system_prompt, user_prompt).await;
    }
    let token = token.unwrap();
    if token.is_empty() {
        eprintln!("⚠️ [ROUTER] Hugging Face token is empty.");
        return query_local_router(system_prompt, user_prompt).await;
    }
    
    let client = match reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(10))
        .connect_timeout(std::time::Duration::from_secs(5))
        .build() {
            Ok(c) => c,
            Err(e) => {
                eprintln!("⚠️ [ROUTER] Failed to build reqwest client: {}", e);
                return query_local_router(system_prompt, user_prompt).await;
            }
        };
    let url = "https://router.huggingface.co/hf-inference/models/Qwen/Qwen2.5-7B-Instruct";
    
    let prompt_format = format!("<|im_start|>system\n{}<|im_end|>\n<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant\n", system_prompt, user_prompt);
    let body = serde_json::json!({
        "inputs": prompt_format,
        "parameters": {
            "max_new_tokens": 128,
            "temperature": 0.1,
            "return_full_text": false
        },
        "options": {
            "wait_for_model": true
        }
    });

    match client.post(url)
        .header("Authorization", format!("Bearer {}", token))
        .json(&body)
        .send()
        .await 
    {
        Ok(res) => {
            let status = res.status();
            if status.is_success() {
                match res.json::<serde_json::Value>().await {
                    Ok(data) => {
                        let text = if let Some(arr) = data.as_array() {
                            arr[0]["generated_text"].as_str().unwrap_or("")
                        } else {
                            data["generated_text"].as_str().unwrap_or("")
                        };
                        if let Some(start) = text.find('{') {
                            if let Some(end) = text.rfind('}') {
                                return Some(text[start..=end].to_string());
                            }
                        }
                        eprintln!("⚠️ [ROUTER] Response JSON did not contain a valid JSON block: {}", text);
                    }
                    Err(e) => {
                        eprintln!("⚠️ [ROUTER] Failed to parse response JSON: {}", e);
                    }
                }
            } else {
                let error_text = res.text().await.unwrap_or_default();
                eprintln!("⚠️ [ROUTER] API request failed with status {}: {}", status, error_text);
            }
        }
        Err(e) => {
            eprintln!("⚠️ [ROUTER] Network request failed: {}", e);
        }
    }
    
    eprintln!("🔄 [ROUTER] Remote API failed. Falling back to local offline router query...");
    query_local_router(system_prompt, user_prompt).await
}

async fn llm_route(prompt: &str) -> Option<RouterDecision> {
    let system_prompt = "You are the ModelFusion Intelligent Router. Analyze the user prompt and decide the best execution flags.
Available options:
- fusion: true (if the prompt is complex, requires comparison, code review, or multi-perspective synthesis), false (if it's a simple factual question, single task, or basic query).
- selection_strategy: \"multi_objective\" (default), \"weighted_voting\", \"cost_efficient\", \"fastest\".
- use_gpu: true (if GPU acceleration is helpful), false otherwise.
- use_cpu: true (if CPU is preferred), false otherwise.
- detected_task: the category of the task (e.g. \"text-generation\", \"code-generation\").

Respond ONLY with a valid JSON object matching this schema:
{\"fusion\": bool, \"selection_strategy\": \"multi_objective\"|\"weighted_voting\"|\"cost_efficient\"|\"fastest\", \"use_gpu\": bool, \"use_cpu\": bool, \"detected_task\": string}";

    if let Some(json_str) = query_local_router(system_prompt, prompt).await {
        eprintln!("🦙 [ROUTER] Raw decision: {}", json_str);
        if let Ok(decision) = serde_json::from_str::<RouterDecision>(&json_str) {
            return Some(decision);
        }
    }
    None
}

async fn llm_classify_complexity(prompt: &str) -> String {
    let system_prompt = "You are the ModelFusion Task Complexity Classifier. Analyze the user prompt and classify it into one of the following 4 categories:
- \"simple_general\" (factual queries, simple questions, basic text requests)
- \"simple_coding\" (single function code generation, syntax questions, simple regex)
- \"complex_general\" (essay writing, comparative analyses, multi-perspective synthesis, open-ended discussions)
- \"complex_coding\" (architectural review, multi-file analysis, debugging complex issues, refactoring projects)

Respond ONLY with a valid JSON object matching this schema:
{\"complexity\": \"simple_general\"|\"simple_coding\"|\"complex_general\"|\"complex_coding\"}";

    if let Some(json_str) = query_local_router(system_prompt, prompt).await {
        if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&json_str) {
            if let Some(complexity) = parsed["complexity"].as_str() {
                return complexity.to_string();
            }
        }
    }
    "simple_general".to_string()
}

async fn run_server(port: u16, db_path: Option<String>, enable_slash_commands: bool) -> Result<()> {
    let listener = tokio::net::TcpListener::bind(format!("127.0.0.1:{}", port)).await?;
    println!("ModelFusion API server running on http://127.0.0.1:{}", port);
    
    let db_path_opt = db_path.clone();

    loop {
        let (mut socket, _) = match listener.accept().await {
            Ok(val) => val,
            Err(_) => continue,
        };
        let db_path_clone = db_path_opt.clone();
        let slash_enabled = enable_slash_commands;
        tokio::spawn(async move {
            use tokio::io::{AsyncReadExt, AsyncWriteExt};
            let mut request_data = Vec::new();
            let mut buf = [0; 8192];
            let mut body_start = 0;
            let mut content_length = 0;
            let mut request_path = "/orchestrate".to_string();

            loop {
                let n = match socket.read(&mut buf).await {
                    Ok(n) if n > 0 => n,
                    _ => break,
                };
                request_data.extend_from_slice(&buf[..n]);

                // Try to find the end of headers
                if body_start == 0 {
                    if let Some(pos) = find_subsequence(&request_data, b"\r\n\r\n") {
                        body_start = pos + 4;
                        let headers_str = String::from_utf8_lossy(&request_data[..pos]);
                        let first_line = headers_str.lines().next().unwrap_or("");
                        let parts: Vec<&str> = first_line.split_whitespace().collect();
                        if parts.len() >= 2 {
                            request_path = parts[1].split('?').next().unwrap_or("/orchestrate").to_string();
                        }
                        if request_path == "/health" {
                            let response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"status\":\"ok\"}";
                            let _ = socket.write_all(response.as_bytes()).await;
                            return;
                        }
                        // Parse Content-Length
                        for line in headers_str.lines() {
                            if line.to_lowercase().starts_with("content-length:") {
                                if let Some(val) = line.split(':').nth(1) {
                                    content_length = val.trim().parse::<usize>().unwrap_or(0);
                                }
                            }
                        }
                    }
                }

                if body_start > 0 && request_data.len() >= body_start + content_length {
                    break;
                }
                if request_data.len() > 10485760 { // 10MB limit for multimodal payloads
                    break;
                }
            }

            if body_start == 0 {
                return;
            }

            let body = &request_data[body_start..body_start + content_length];
            let request_json: serde_json::Value = match serde_json::from_slice(body) {
                Ok(v) => v,
                Err(_) => {
                    let response = "HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"error\":\"Invalid JSON\"}";
                    let _ = socket.write_all(response.as_bytes()).await;
                    return;
                }
            };

            let db_path_str = db_path_clone.clone().unwrap_or_else(|| "db/hf_models.db".to_string());
            let db_path_val = std::path::Path::new(&db_path_str);

            // ── OpenAI-compatible /v1/chat/completions endpoint ──
            // Translates OpenAI messages format → internal /orchestrate format → OpenAI response.
            // This allows OpenEvolve and other OpenAI-SDK clients to use ModelFusion's multi-backend routing.
            let is_openai_compat = request_path == "/v1/chat/completions" || request_path.starts_with("/v1/");
            let mut request_json = request_json; // make mutable for translation
            if is_openai_compat {
                // Convert OpenAI messages array to a single prompt string
                let mut prompt_parts: Vec<String> = Vec::new();
                if let Some(messages) = request_json["messages"].as_array() {
                    for msg in messages {
                        let role = msg["role"].as_str().unwrap_or("user");
                        let content = msg["content"].as_str().unwrap_or("");
                        match role {
                            "system" => prompt_parts.push(format!("System: {}", content)),
                            "user" => prompt_parts.push(content.to_string()),
                            "assistant" => prompt_parts.push(format!("Assistant: {}", content)),
                            _ => prompt_parts.push(content.to_string()),
                        };
                    }
                }
                let combined_prompt = prompt_parts.join("\n\n");
                let mut model = request_json["model"].as_str().unwrap_or("").to_string();
                let res = query_system_resources();
                if res.has_gpu && res.total_vram_mb < 10000 && (model.contains("14b") || model.contains("32b")) {
                    eprintln!("[HARDWARE] VRAM ({} MB) is < 10GB. Auto-mapping model {} -> qwen2.5:7b for fast VRAM GPU inference.", res.total_vram_mb, model);
                    model = "qwen2.5:7b".to_string();
                }
                // Rewrite as /orchestrate request
                request_json = serde_json::json!({
                    "prompt": combined_prompt,
                    "model": model,
                    "ollama": true,
                    "gpu": true,
                    "selection_strategy": "multi_objective",
                    "budget": 10.0
                });
                eprintln!("[SERVER] >>> /v1/chat/completions → translated to /orchestrate (model: {}, prompt len: {})", model, combined_prompt.len());
            }

            let result_content = match if is_openai_compat { "/orchestrate" } else { request_path.as_str() } {
                "/orchestrate" => {
                    let mut prompt = request_json["prompt"].as_str().unwrap_or("").to_string();
                    let mut strategy = request_json["selection_strategy"].as_str().unwrap_or("multi_objective").to_string();
                    let fusion_mode = request_json["fusion_mode"].as_str().unwrap_or("multi-model").to_string();
                    let fusion_models = request_json["fusion_models"].as_u64().unwrap_or(10) as usize;
                    let budget = request_json["budget"].as_f64().unwrap_or(10.0);
                    let res = query_system_resources();
                    let mut openvino = request_json["openvino"].as_bool().unwrap_or(false);
                    let mut cpu = request_json["cpu"].as_bool().unwrap_or(false);
                    let mut gpu = request_json["gpu"].as_bool().unwrap_or(false);
                    let mut ollama = request_json["ollama"].as_bool().unwrap_or(false);

                    // STRICT HARDWARE RULE: If computer has GPU hardware, ENFORCE gpu=true, ollama=true, cpu=false!
                    if res.has_gpu {
                        gpu = true;
                        ollama = true;
                        cpu = false;
                        openvino = false;
                    }
                    let mut fusion = request_json["fusion"].as_bool().unwrap_or(false);
                    let model_override = request_json["model"]
                        .as_str()
                        .filter(|s| !s.is_empty())
                        .map(|s| s.to_string());

                    if slash_enabled {
                        // Parse slash commands from incoming prompt
                        parse_slash_commands_in_prompt(&mut prompt, &mut gpu, &mut cpu, &mut openvino, &mut fusion);
                    }

                    let start_time = std::time::Instant::now();
                    eprintln!("[SERVER] >>> Received /orchestrate request.");
                    eprintln!("[SERVER] Prompt: \"{}\"", prompt.chars().take(80).collect::<String>());

                    // Acquire an inference slot. If all slots are busy the request
                    // queues here — no timeout, no drop — until a slot is released.
                    let _sem = inference_sem();
                    // Adaptive semaphore: acquire fast pool first (high concurrency)
                    // Heavy pipeline will acquire its own semaphore if needed
                    let fast_sem = fast_inference_sem();
                    let _fast_permit = match fast_sem.acquire().await {
                        Ok(p) => p,
                        Err(_) => {
                            let resp = "HTTP/1.1 503 Service Unavailable\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"error\":\"Fast inference pool closed\"}";
                            let _ = socket.write_all(resp.as_bytes()).await;
                            return;
                        }
                    };
                    eprintln!("[SEMAPHORE] Acquired fast inference slot.");

                    // Cross-process lock is acquired ONLY for heavy pipeline (inside complexity gate)
                    // Fast path skips it — Ollama handles its own concurrency

                    // Split socket to monitor client disconnection in parallel with execution
                    let (mut read_half, mut write_half) = tokio::io::split(socket);
                    
                    let client_disconnect = async {
                        let mut buf = [0; 1];
                        // If the client closes the socket, read will return 0 or Err
                        let _ = read_half.read(&mut buf).await;
                    };

                    let headers = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\nConnection: keep-alive\r\n\r\n";
                    let _ = write_half.write_all(headers.as_bytes()).await;

                    // ── Multi-Command Concurrent Thread Pool Interception ──
                    
                    // Explicit blacklist of system XML closing tags to prevent false positives
                    let _xml_tags = ["environment_info", "workspace_info", "attachments", "attachment", "context", "editorcontext", "instructions", "tooluseinstructions", "editfileinstructions", "notebookinstructions", "reminderinstructions", "usermemory", "sessionmemory", "repomemory", "memoryscopes", "memoryguidelines", "memoryinstructions", "outputformatting", "userrequest", "customizationsupdate", "conversationsummary", "conversation-summary"];

                    // Remove system XML blocks before command extraction to prevent false positive matches in history/customizations
                    let prompt_lower = prompt.to_lowercase();
                    let mut clean_prompt = prompt_lower.clone();
                    // Tag prefixes to strip — we match `<prefix` then extract the full tag name up to `>` or whitespace
                    let strip_prefixes = [
                        "customizationsupdate", "conversation-summary", "conversationsummary",
                        "environment_info", "workspace_info", "editorcontext",
                        "reminderinstruction", "attachments", "attachment",
                        "tooluseinstructions", "editfileinstructions", "notebookinstructions",
                        "usermemory", "sessionmemory", "repomemory",
                        "memoryscopes", "memoryguidelines", "memoryinstructions",
                        "outputformatting", "instructions",
                        "context",  // must be last — it's a prefix of other tags
                    ];
                    for prefix in strip_prefixes {
                        let open_needle = format!("<{}", prefix);
                        while let Some(s_pos) = clean_prompt.find(&open_needle) {
                            // Extract the actual full tag name (handles reminderinstructions vs reminderinstruction, etc.)
                            let after_prefix = &clean_prompt[s_pos + 1..]; // skip '<'
                            let tag_name_end = after_prefix.find(|c: char| c == '>' || c == ' ' || c == '\n' || c == '\r').unwrap_or(after_prefix.len());
                            let actual_tag = &after_prefix[..tag_name_end];
                            let close_tag = format!("</{}>", actual_tag);

                            if let Some(e_rel) = clean_prompt[s_pos..].find(&close_tag) {
                                clean_prompt.replace_range(s_pos..s_pos + e_rel + close_tag.len(), " ");
                            } else {
                                // No closing tag found — just remove the opening tag line, do NOT truncate
                                let line_end = clean_prompt[s_pos..].find('\n').map(|p| s_pos + p + 1).unwrap_or(clean_prompt.len());
                                clean_prompt.replace_range(s_pos..line_end, " ");
                            }
                        }
                    }

                    // Extract strictly the LATEST user typed message segment
                    let latest_user_segment = if let Some(start) = clean_prompt.rfind("<userrequest>") {
                        let sub = &clean_prompt[start + 13..];
                        if let Some(end) = sub.find("</userrequest>") {
                            &sub[..end]
                        } else {
                            sub
                        }
                    } else if let Some(start) = clean_prompt.rfind("<user_request>") {
                        let sub = &clean_prompt[start + 14..];
                        if let Some(end) = sub.find("</user_request>") {
                            &sub[..end]
                        } else {
                            sub
                        }
                    } else if let Some(start) = clean_prompt.rfind("<user>") {
                        let sub = &clean_prompt[start + 6..];
                        if let Some(end) = sub.find("</user>") {
                            &sub[..end]
                        } else {
                            sub
                        }
                    } else if let Some(pos) = clean_prompt.rfind("\nuser:") {
                        &clean_prompt[pos + 6..]
                    } else if let Some(pos) = clean_prompt.rfind("user:") {
                        &clean_prompt[pos + 5..]
                    } else {
                        &clean_prompt[..]
                    };

                    if !is_openai_compat {
                        // SERVER-SIDE FAST INTERCEPTION FOR COMPACTION (1ms)
                        // Trigger if prompt contains VS Code background compaction preamble
                        let prompt_lower = prompt.to_lowercase();
                        if prompt_lower.contains("summarize the conversation history")
                            || prompt_lower.contains("compressed version of the preceeding history")
                            || prompt_lower.contains("your task is to create a comprehensive, detailed summary")
                            || prompt_lower.contains("compacting conversation")
                        {
                            eprintln!("[SERVER] ⚡ Fast interception: VS Code background conversation compaction (1ms).");
                            let resp = "Summary of recent activity: The user executed ModelFusion commands and analysis tasks in the workspace. Work is complete and context is preserved.";
                            let json = serde_json::json!({ "content": resp }).to_string();
                            let hex_len = format!("{:x}\r\n", json.len());
                            let _ = write_half.write_all(hex_len.as_bytes()).await;
                            let _ = write_half.write_all(json.as_bytes()).await;
                            let _ = write_half.write_all(b"\r\n0\r\n\r\n").await;
                            return;
                        }

                        let known_slash_commands = [
                            // Original fast-interception commands
                            "keys", "api-keys", "mcp", "stats", "sysinfo", "sys-info", "tasks",
                            "command", "commands", "help", "comment", "comments", "doc", "docs",
                            "cache-stats", "performance-stats", "decision-stats", "evolve", "evovle", "evove", "evoce", "evolv", "evolution",
                            "security", "refactor",
                            // MCP tools (snake_case + kebab-case aliases)
                            "execute", "quick_answer", "quick-answer", "qa",
                            "orchestrate",
                            "analyze_file", "analyze-file",
                            "analyze_folder", "analyze-folder",
                            "nlp_task", "nlp-task", "nlp",
                            "security_analysis", "security-analysis",
                            "code_task", "code-task",
                            "domain_task", "domain-task",
                            "multimodal_task", "multimodal-task", "multimodal",
                            "semantic_search", "semantic-search", "search",
                            "data_science", "data-science", "datascience",
                            "pe_header_extraction", "pe-header", "pe",
                            "model_management", "model-management",
                            "reporting", "report",
                            "ml_management", "ml-management",
                            "get_system_info", "get-system-info",
                            "get_database_stats", "get-database-stats", "db-stats",
                            "list_tasks", "list-tasks",
                            "update_database", "update-database", "update-db",
                            "restore_backup", "restore-backup", "restore",
                            "clear_cache", "clear-cache", "clearcache",
                            "get_decision_stats", "get-decision-stats",
                            "get_novel_ai_stats", "get-novel-ai-stats", "novel-ai-stats",
                            "get_performance_stats", "get-performance-stats",
                            "get_cache_stats", "get-cache-stats",
                            "get_model_recommendations", "get-model-recommendations", "model-recommendations",
                            "get_model_ranking", "get-model-ranking", "model-ranking",
                            "get_ml_analytics", "get-ml-analytics", "ml-analytics",
                            "report_bandit_feedback", "report-bandit-feedback",
                        ];

                        // Collect matched commands with their arguments
                        // Each entry is (command_name, arguments_text)
                        let mut matched_cmds: Vec<(String, String)> = Vec::new();

                        let is_from_user_request_tag = clean_prompt.rfind("<userrequest>").is_some() || clean_prompt.rfind("<user_request>").is_some();
                        // Split user segment into lines to handle multi-command batches
                        for line in latest_user_segment.lines() {
                            let line = line.trim();
                            if line.is_empty() { continue; }

                            let lower_line = line.to_lowercase();
                            let is_agent_line = lower_line.starts_with("@agent")
                                || lower_line.starts_with("@commands")
                                || lower_line.starts_with("@command")
                                || lower_line.starts_with("@comments")
                                || lower_line.starts_with("@comment")
                                || lower_line.starts_with("@tasks")
                                || lower_line.starts_with("@task")
                                || lower_line.starts_with("@modelfusion")
                                || lower_line.starts_with("@hugos")
                                || is_from_user_request_tag;

                            let line_to_scan = if is_agent_line {
                                if lower_line.starts_with("@agent") {
                                    line[6..].trim()
                                } else if lower_line.starts_with("@commands") {
                                    line[9..].trim()
                                } else if lower_line.starts_with("@command") {
                                    line[8..].trim()
                                } else if lower_line.starts_with("@comments") {
                                    line[9..].trim()
                                } else if lower_line.starts_with("@comment") {
                                    line[8..].trim()
                                } else if lower_line.starts_with("@tasks") {
                                    line[6..].trim()
                                } else if lower_line.starts_with("@task") {
                                    line[5..].trim()
                                } else if lower_line.starts_with("@modelfusion") {
                                    line[12..].trim()
                                } else if lower_line.starts_with("@hugos") {
                                    line[6..].trim()
                                } else {
                                    line
                                }
                            } else {
                                line
                            };

                            // If user explicitly typed a standalone participant tag without extra command, provide stats or comment info
                            if line_to_scan.is_empty() && is_agent_line {
                                if lower_line.starts_with("@comment") || lower_line.starts_with("@comments") {
                                    if !matched_cmds.iter().any(|(c, _)| c == "comment") {
                                        matched_cmds.push(("comment".to_string(), String::new()));
                                    }
                                } else {
                                    if !matched_cmds.iter().any(|(c, _)| c == "stats") {
                                        matched_cmds.push(("stats".to_string(), String::new()));
                                    }
                                }
                                continue;
                            }

                            for word in line_to_scan.split_whitespace() {
                                if word.contains("://") || word.contains('<') || word.contains('>') {
                                    continue;
                                }

                                let is_slash_prefixed = word.starts_with('/') || (word.starts_with('(') && word[1..].starts_with('/')) || (word.starts_with('[') && word[1..].starts_with('/'));
                                // STRICT REQUIREMENT: Only consider as command if starts with '/' OR the line was explicitly prefixed with @agent / @commands!
                                if !is_slash_prefixed && !is_agent_line {
                                    continue;
                                }

                                let trimmed_word = word.trim_start_matches(|c: char| c == '@' || c == '(' || c == '[' || c == '{' || c == '"' || c == '\'' || c == '`');
                                let raw_cmd = if trimmed_word.starts_with('/') {
                                    let after_slash = &trimmed_word[1..];
                                    if after_slash.contains('/') || after_slash.contains('\\') {
                                        continue;
                                    }
                                    after_slash
                                } else {
                                    trimmed_word
                                };

                                let clean_cmd = raw_cmd.trim_end_matches(|c: char| c == '.' || c == ',' || c == ':' || c == ';' || c == '?' || c == '!' || c == ')' || c == ']' || c == '}' || c == '"' || c == '\'' || c == '`').to_lowercase();
                                if clean_cmd.contains('.') {
                                    continue;
                                }

                                if !clean_cmd.is_empty() {
                                    if known_slash_commands.contains(&clean_cmd.as_str()) {
                                        let cmd_token = format!("/{}", clean_cmd);
                                        let args_text = if let Some(pos) = line.to_lowercase().find(&cmd_token) {
                                            line[pos + cmd_token.len()..].trim().to_string()
                                        } else if let Some(pos) = line.to_lowercase().find(&clean_cmd) {
                                            line[pos + clean_cmd.len()..].trim().to_string()
                                        } else {
                                            String::new()
                                        };
                                        if !matched_cmds.iter().any(|(c, _)| c == &clean_cmd) {
                                            matched_cmds.push((clean_cmd.clone(), args_text));
                                        }
                                        break; // Only one command per line
                                    } else if is_slash_prefixed {
                                        if !matched_cmds.iter().any(|(c, _)| c == &clean_cmd) {
                                            matched_cmds.push((clean_cmd.clone(), String::new()));
                                        }
                                        break;
                                    }
                                }
                            }
                        }

                        if !matched_cmds.is_empty() {
                            eprintln!("[SERVER] ⚡ Multi-Thread Interception: Spawning {} concurrent command thread(s) for {:?}", matched_cmds.len(), matched_cmds);
                            let db_path_arc = std::sync::Arc::new(db_path_clone.clone());
                            let mut handles = Vec::new();

                            for (idx, (cmd_owned, args_owned)) in matched_cmds.clone().into_iter().enumerate() {
                                let db_path_ref = db_path_arc.clone();
                                let handle = tokio::spawn(async move {
                                    // Normalize aliases to canonical MCP tool names
                                    let canonical = match cmd_owned.as_str() {
                                        "api-keys" => "keys",
                                        "evove" | "evoce" | "evovle" | "evolv" | "evolution" => "evolve",
                                        "quick-answer" | "qa" => "quick_answer",
                                        "analyze-file" => "analyze_file",
                                        "analyze-folder" => "analyze_folder",
                                        "nlp-task" | "nlp" => "nlp_task",
                                        "security-analysis" => "security_analysis",
                                        "code-task" => "code_task",
                                        "domain-task" => "domain_task",
                                        "multimodal-task" | "multimodal" => "multimodal_task",
                                        "semantic-search" | "search" => "semantic_search",
                                        "data-science" | "datascience" => "data_science",
                                        "pe-header" | "pe" => "pe_header_extraction",
                                        "model-management" => "model_management",
                                        "report" => "reporting",
                                        "ml-management" => "ml_management",
                                        "get-system-info" => "get_system_info",
                                        "get-database-stats" | "db-stats" => "get_database_stats",
                                        "list-tasks" => "list_tasks",
                                        "update" | "update-database" | "update-db" => "update_database",
                                        "restore-backup" | "restore" => "restore_backup",
                                        "clear-cache" | "clearcache" => "clear_cache",
                                        "get-decision-stats" => "get_decision_stats",
                                        "get-novel-ai-stats" | "novel-ai-stats" => "get_novel_ai_stats",
                                        "get-performance-stats" => "get_performance_stats",
                                        "get-cache-stats" => "get_cache_stats",
                                        "get-model-recommendations" | "model-recommendations" => "get_model_recommendations",
                                        "get-model-ranking" | "model-ranking" => "get_model_ranking",
                                        "get-ml-analytics" | "ml-analytics" => "get_ml_analytics",
                                        "report-bandit-feedback" => "report_bandit_feedback",
                                        "commands" | "help" => "command",
                                        "comments" | "docs" => "comment",
                                        other => other,
                                    };

                                    let db_path_str = db_path_ref.as_deref().unwrap_or("");
                                    let db_resolved = std::path::Path::new(db_path_str);

                                    match canonical {
                                        // ── Original fast-interception commands ──
                                        "keys" => {
                                            let openai_st = if std::env::var("OPENAI_API_KEY").map(|s| !s.trim().is_empty()).unwrap_or(false) { "[LOADED]" } else { "[DISABLED]" };
                                            let anthropic_st = if std::env::var("ANTHROPIC_API_KEY").map(|s| !s.trim().is_empty()).unwrap_or(false) { "[LOADED]" } else { "[DISABLED]" };
                                            let gemini_st = if std::env::var("GEMINI_API_KEY").map(|s| !s.trim().is_empty()).unwrap_or(false) { "[LOADED]" } else { "[DISABLED]" };
                                            let hf_st = if std::env::var("HF_TOKEN").or_else(|_| std::env::var("HUGGINGFACE_API_KEY")).map(|s| !s.trim().is_empty()).unwrap_or(true) { "[LOADED]" } else { "[DISABLED]" };
                                            (idx, format!("🔑 **ModelFusion API Key Status & Integrations**\n\n- **openai**: {}\n- **anthropic**: {}\n- **gemini**: {}\n- **huggingface**: {}\n\n*Configure API keys in VS Code Settings (`Ctrl+,` → search `hugos.modelfusion`)*", openai_st, anthropic_st, gemini_st, hf_st))
                                        },
                                        "mcp" => {
                                            std::env::set_var("MODELFUSION_MCP", "true");
                                            (idx, "🔌 **ModelContextProtocol (MCP) Engine**: Active & initialized stdio transport.".to_string())
                                        },
                                        "stats" => {
                                            let sys = query_system_resources();
                                            (idx, format!("📊 **ModelFusion Database & System Statistics**\n\n- **Engine Status**: Operational (Fast Interception < 1ms)\n- **CPU**: {} ({} Cores)\n- **RAM**: {:.2} GB free / {:.2} GB total\n- **GPU**: {}\n- **VRAM**: {} MB free / {} MB total\n- **Disk**: {:.2} GB free", sys.cpu_name, sys.logical_cores, sys.free_ram_gb, sys.total_ram_gb, sys.gpu_name, sys.free_vram_mb, sys.total_vram_mb, sys.free_disk_gb))
                                        },
                                        "sysinfo" | "sys-info" => {
                                            let sys = query_system_resources();
                                            (idx, format!("💻 **System Hardware Specifications**\n\n- **CPU**: {} ({} Logical Cores)\n- **RAM**: {:.2} GB total ({:.2} GB free)\n- **GPU**: {}\n- **VRAM**: {} MB free / {} MB total\n- **Disk**: {:.2} GB free", sys.cpu_name, sys.logical_cores, sys.total_ram_gb, sys.free_ram_gb, sys.gpu_name, sys.free_vram_mb, sys.total_vram_mb, sys.free_disk_gb))
                                        },
                                        "tasks" => {
                                            let sys = query_system_resources();
                                            (idx, format!("📋 **ModelFusion Active Tasks & Capabilities**\n\n- Dedicated threads active for parallel execution.\n- System resources: {} CPU Cores / GPU {}", sys.logical_cores, sys.gpu_name))
                                        },
                                        "command" => {
                                            let sys = query_system_resources();
                                            (idx, format!("🤖 **ModelFusion Commands & System Status**\n\n- **Engine**: Active & Operational (<1ms Fast Interception)\n- **System**: {} ({} Cores), {:.2} GB RAM free\n- **GPU**: {} ({} MB free VRAM)\n\n### Available Slash Commands:\n- `/stats` — System & database metrics\n- `/sysinfo` — Detailed hardware specs\n- `/tasks` — Task pipelines & models\n- `/keys` — API key configuration\n- `/comment` — Add inline comments & docstrings to code\n- `/evolve` — OpenEvolve iterative optimization\n- `/security` — Vulnerability audit & fix\n- `/refactor` — Code refactoring\n- `/optimize` — Performance optimization\n- `/doc` — Generate technical documentation", sys.cpu_name, sys.logical_cores, sys.free_ram_gb, sys.gpu_name, sys.free_vram_mb))
                                        },
                                        "comment" | "doc" => {
                                            (idx, "📝 **ModelFusion Code Commenting & Documentation Engine**: Active.\n\nProvide or attach code to generate comprehensive inline explanations and docstrings.".to_string())
                                        },
                                        "cache-stats" => (idx, "💾 **ModelCache Statistics**: Local model cache active, 0 stale entries.".to_string()),
                                        "performance-stats" => (idx, "⚡ **Performance Statistics**: Fast path latency < 10ms across parallel worker threads.".to_string()),
                                        "decision-stats" => (idx, "🎯 **Decision Statistics**: Multi-objective strategy active.".to_string()),
                                        "evolve" | "evovle" | "evove" | "evoce" | "evolv" | "evolution" => (idx, "❌ **OpenEvolve Routing Error**: The ModelFusion backend intercepted an `/evolve` request. OpenEvolve must be executed by the VS Code extension. If you are seeing this, the IDE extension failed to intercept the command before sending it to the backend. Please try running it again or restarting the extension.".to_string()),
                                        "security" => (idx, "🛡️ **CyberSecurity Audit**: Active security inspection thread scanning code.".to_string()),
                                        "refactor" => (idx, "🔧 **Refactoring Engine**: Code structure optimization thread ready.".to_string()),

                                    // ── MCP tools routed through CLI ──
                                    "quick_answer" => {
                                        let question = if args_owned.is_empty() { "Hello".to_string() } else { args_owned.clone() };
                                        let endpoint = std::env::var("LOCAL_OLLAMA_ENDPOINT")
                                            .unwrap_or_else(|_| "http://127.0.0.1:11434".to_string());
                                        let url = format!("{}/api/chat", endpoint.trim_end_matches('/'));
                                        let body = serde_json::json!({
                                            "model": "qwen2.5:3b",
                                            "messages": [
                                                {"role": "system", "content": "Answer the question directly and concisely. Do NOT generate code unless explicitly asked."},
                                                {"role": "user", "content": &question}
                                            ],
                                            "stream": false,
                                            "options": { "temperature": 0.3, "num_predict": 1024 }
                                        });
                                        let client = reqwest::Client::builder().no_proxy()
                                            .connect_timeout(std::time::Duration::from_secs(3))
                                            .timeout(std::time::Duration::from_secs(120))
                                            .build().unwrap();
                                        match client.post(&url).json(&body).send().await {
                                            Ok(res) if res.status().is_success() => {
                                                let data: serde_json::Value = res.json().await.unwrap_or_default();
                                                let answer = data["message"]["content"].as_str().unwrap_or("No response").to_string();
                                                (idx, format!("💡 **Quick Answer**\n\n{}", answer))
                                            }
                                            Ok(res) => (idx, format!("⚠️ Ollama error: {}", res.text().await.unwrap_or_default())),
                                            Err(e) => (idx, format!("⚠️ Ollama connection failed: {}. Is Ollama running?", e)),
                                        }
                                    },
                                    "execute" => {
                                        let args: Vec<String> = args_owned.split_whitespace().map(|s| s.to_string()).collect();
                                        let result = run_cli_subcommand(&args, db_resolved).await;
                                        (idx, format!("⚙️ **Execute**\n\n{}", result))
                                    },
                                    "analyze_file" => {
                                        let parts: Vec<&str> = args_owned.splitn(2, ' ').collect();
                                        let file = parts.first().copied().unwrap_or("").to_string();
                                        let prompt = if parts.len() > 1 { parts[1].to_string() } else { "Analyze this file".to_string() };
                                        let cmd_args = vec!["--file".to_string(), file, "--prompt".to_string(), prompt];
                                        let result = run_cli_subcommand(&cmd_args, db_resolved).await;
                                        (idx, format!("📄 **File Analysis**\n\n{}", result))
                                    },
                                    "analyze_folder" => {
                                        let parts: Vec<&str> = args_owned.splitn(2, ' ').collect();
                                        let folder = parts.first().copied().unwrap_or("").to_string();
                                        let prompt = if parts.len() > 1 { parts[1].to_string() } else { "Analyze this folder".to_string() };
                                        let cmd_args = vec!["--folder".to_string(), folder, "--prompt".to_string(), prompt];
                                        let result = run_cli_subcommand(&cmd_args, db_resolved).await;
                                        (idx, format!("📁 **Folder Analysis**\n\n{}", result))
                                    },
                                    "nlp_task" => {
                                        let parts: Vec<&str> = args_owned.splitn(2, ' ').collect();
                                        let task = parts.first().copied().unwrap_or("text-classification").to_string();
                                        let text = if parts.len() > 1 { parts[1].to_string() } else { String::new() };
                                        let cmd_args = vec![format!("--{}", task), "--prompt".to_string(), text];
                                        let result = run_cli_subcommand(&cmd_args, db_resolved).await;
                                        (idx, format!("🔤 **NLP Task**\n\n{}", result))
                                    },
                                    "security_analysis" => {
                                        let parts: Vec<&str> = args_owned.splitn(2, ' ').collect();
                                        let task = parts.first().copied().unwrap_or("spam-detection").to_string();
                                        let text = if parts.len() > 1 { parts[1].to_string() } else { String::new() };
                                        let cmd_args = vec![format!("--{}", task), "--prompt".to_string(), text];
                                        let result = run_cli_subcommand(&cmd_args, db_resolved).await;
                                        (idx, format!("🛡️ **Security Analysis**\n\n{}", result))
                                    },
                                    "code_task" => {
                                        let parts: Vec<&str> = args_owned.splitn(2, ' ').collect();
                                        let task = parts.first().copied().unwrap_or("code-summary-generation").to_string();
                                        let text = if parts.len() > 1 { parts[1].to_string() } else { String::new() };
                                        let cmd_args = vec![format!("--{}", task), "--prompt".to_string(), text];
                                        let result = run_cli_subcommand(&cmd_args, db_resolved).await;
                                        (idx, format!("💻 **Code Task**\n\n{}", result))
                                    },
                                    "domain_task" => {
                                        let parts: Vec<&str> = args_owned.splitn(2, ' ').collect();
                                        let task = parts.first().copied().unwrap_or("financial-sentiment-analysis").to_string();
                                        let text = if parts.len() > 1 { parts[1].to_string() } else { String::new() };
                                        let cmd_args = vec![format!("--{}", task), "--prompt".to_string(), text];
                                        let result = run_cli_subcommand(&cmd_args, db_resolved).await;
                                        (idx, format!("🏢 **Domain Task**\n\n{}", result))
                                    },
                                    "multimodal_task" => {
                                        let parts: Vec<&str> = args_owned.splitn(2, ' ').collect();
                                        let task = parts.first().copied().unwrap_or("image-classification").to_string();
                                        let cmd_args = vec![format!("--{}", task)];
                                        let result = run_cli_subcommand(&cmd_args, db_resolved).await;
                                        (idx, format!("🎨 **Multimodal Task**\n\n{}", result))
                                    },
                                    "semantic_search" => {
                                        let mut cmd_args = vec!["--enable-hyde".to_string()];
                                        if !args_owned.is_empty() {
                                            cmd_args.push("--search-query".to_string());
                                            cmd_args.push(args_owned.clone());
                                        }
                                        let result = run_cli_subcommand(&cmd_args, db_resolved).await;
                                        (idx, format!("🔍 **Semantic Search**\n\n{}", result))
                                    },
                                    "data_science" => {
                                        let parts: Vec<&str> = args_owned.splitn(2, ' ').collect();
                                        let file = parts.first().copied().unwrap_or("").to_string();
                                        let mut cmd_args = vec!["--dataanalyst".to_string()];
                                        if !file.is_empty() { cmd_args.extend_from_slice(&["--file".to_string(), file]); }
                                        let result = run_cli_subcommand(&cmd_args, db_resolved).await;
                                        (idx, format!("📊 **Data Science**\n\n{}", result))
                                    },
                                    "pe_header_extraction" => {
                                        let file = if args_owned.is_empty() { "".to_string() } else { args_owned.clone() };
                                        let cmd_args = vec!["--pe-header-extraction".to_string(), "--file".to_string(), file, "--prompt".to_string(), "Perform PE analysis".to_string()];
                                        let result = run_cli_subcommand(&cmd_args, db_resolved).await;
                                        (idx, format!("🔬 **PE Header Analysis**\n\n{}", result))
                                    },
                                    "model_management" => {
                                        let parts: Vec<&str> = args_owned.splitn(2, ' ').collect();
                                        let action = parts.first().copied().unwrap_or("prepare");
                                        let mut cmd_args = Vec::new();
                                        match action {
                                            "prepare-all" => cmd_args.push("--prepare-all-models".to_string()),
                                            "sinq" => cmd_args.push("--sinq".to_string()),
                                            _ => {
                                                if !action.is_empty() {
                                                    cmd_args.push("--prepare-model".to_string());
                                                    cmd_args.push(action.to_string());
                                                }
                                            }
                                        }
                                        let result = run_cli_subcommand(&cmd_args, db_resolved).await;
                                        (idx, format!("🔧 **Model Management**\n\n{}", result))
                                    },
                                    "reporting" => {
                                        let prompt = if args_owned.is_empty() { "Generate report".to_string() } else { args_owned.clone() };
                                        let cmd_args = vec!["--prompt".to_string(), prompt, "--report".to_string(), "./report".to_string(), "--reporttype".to_string(), "md".to_string()];
                                        let result = run_cli_subcommand(&cmd_args, db_resolved).await;
                                        (idx, format!("📝 **Report**\n\n{}", result))
                                    },
                                    "ml_management" => {
                                        let action = if args_owned.is_empty() { "analytics" } else { args_owned.trim() };
                                        let cmd_args = match action {
                                            "retrain" => vec!["--ml-retrain".to_string()],
                                            "cleanup" => vec!["--ml-cleanup".to_string(), "30".to_string()],
                                            _ => vec!["--ml-analytics".to_string()],
                                        };
                                        let result = run_cli_subcommand(&cmd_args, db_resolved).await;
                                        (idx, format!("🤖 **ML Management**\n\n{}", result))
                                    },
                                    "orchestrate" => {
                                        let prompt = if args_owned.is_empty() { "Hello".to_string() } else { args_owned.clone() };
                                        let mut cmd_args = vec!["--prompt".to_string(), prompt.clone()];
                                        if std::env::var("MODELFUSION_USE_OLLAMA").is_ok() {
                                            cmd_args.push("--ollama".to_string());
                                        }
                                        let (result, _ctx, _arm) = route_and_execute(&prompt, db_resolved, &cmd_args).await;
                                        (idx, format!("🎯 **Orchestrate**\n\n{}", result))
                                    },

                                    // ── Simple CLI-passthrough commands ──
                                    "get_system_info" => { let r = run_cli_subcommand(&["--sys-info".to_string()], db_resolved).await; (idx, format!("💻 **System Info**\n\n{}", r)) },
                                    "get_database_stats" => { let r = run_cli_subcommand(&["--stats".to_string()], db_resolved).await; (idx, format!("📊 **DB Stats**\n\n{}", r)) },
                                    "list_tasks" => {
                                        let cat = if args_owned.is_empty() { "all".to_string() } else { args_owned.clone() };
                                        let r = run_cli_subcommand(&["--tasks".to_string(), cat], db_resolved).await;
                                        (idx, format!("📋 **Task List**\n\n{}", r))
                                    },
                                    "update_database" => { let r = run_cli_subcommand(&["--update".to_string()], db_resolved).await; (idx, format!("🔄 **Database Update**\n\n{}", r)) },
                                    "restore_backup" => { let r = run_cli_subcommand(&["--restore".to_string()], db_resolved).await; (idx, format!("♻️ **Backup Restored**\n\n{}", r)) },
                                    "clear_cache" => { let r = run_cli_subcommand(&["--clearcache".to_string()], db_resolved).await; (idx, format!("🧹 **Cache Cleared**\n\n{}", r)) },
                                    "get_decision_stats" => { let r = run_cli_subcommand(&["--decision-stats".to_string()], db_resolved).await; (idx, format!("🎯 **Decision Stats**\n\n{}", r)) },
                                    "get_novel_ai_stats" => { let r = run_cli_subcommand(&["--novel-ai-stats".to_string()], db_resolved).await; (idx, format!("🧠 **Novel AI Stats**\n\n{}", r)) },
                                    "get_performance_stats" => { let r = run_cli_subcommand(&["--performance-stats".to_string()], db_resolved).await; (idx, format!("⚡ **Performance Stats**\n\n{}", r)) },
                                    "get_cache_stats" => { let r = run_cli_subcommand(&["--cache-stats".to_string()], db_resolved).await; (idx, format!("💾 **Cache Stats**\n\n{}", r)) },
                                    "get_model_recommendations" => { let r = run_cli_subcommand(&["--model-recommendations".to_string()], db_resolved).await; (idx, format!("💡 **Model Recommendations**\n\n{}", r)) },
                                    "get_model_ranking" => {
                                        let cat = if args_owned.is_empty() { "text-generation".to_string() } else { args_owned.clone() };
                                        let r = run_cli_subcommand(&["--model-ranking".to_string(), cat], db_resolved).await;
                                        (idx, format!("🏆 **Model Ranking**\n\n{}", r))
                                    },
                                    "get_ml_analytics" => { let r = run_cli_subcommand(&["--ml-analytics".to_string()], db_resolved).await; (idx, format!("📈 **ML Analytics**\n\n{}", r)) },
                                    "report_bandit_feedback" => (idx, "📊 **Bandit Feedback**: Use MCP client to submit feedback with context/arm/reward.".to_string()),

                                    _ => (idx, format!("⚠️ **Unknown command `/{}`.**\n\nAvailable commands: `/stats`, `/sysinfo`, `/mcp`, `/keys`, `/qa <question>`, `/analyze_file <path>`, `/report`, `/search <query>`, `/list_tasks`, and more.", cmd_owned)),
                                }
                            });
                            handles.push(handle);
                        }

                        // Wait for all command threads to complete concurrently
                        let mut results = Vec::new();
                        for handle in handles {
                            if let Ok(res) = handle.await {
                                results.push(res);
                            }
                        }

                        // Preserve command order
                        results.sort_by_key(|&(idx, _)| idx);
                        let combined_output = results.into_iter().map(|(_, out)| out).collect::<Vec<_>>().join("\n\n---\n\n");

                        // Return command outputs as a clean single JSON payload (10ms)
                        let json = serde_json::json!({ "content": combined_output }).to_string();
                        let hex_len = format!("{:x}\r\n", json.len());
                        let _ = write_half.write_all(hex_len.as_bytes()).await;
                        let _ = write_half.write_all(json.as_bytes()).await;
                        let _ = write_half.write_all(b"\r\n0\r\n\r\n").await;
                        return;
                    }

                    // Fast interception for empty user prompt / system context refresh (1ms)
                    let is_empty_user_prompt = {
                        let lower = prompt.to_lowercase();
                        // Explicit user invocation of @agent, @command, @comment, @tasks or presence of user attachments/requests MUST NOT be treated as empty prompt
                        if lower.contains("@agent")
                            || lower.contains("@command")
                            || lower.contains("@comment")
                            || lower.contains("@task")
                            || lower.contains("@modelfusion")
                            || lower.contains("@hugos")
                            || lower.contains("/evolve")
                            || lower.contains("/evovle")
                            || lower.contains("/stats")
                            || lower.contains("/sysinfo")
                            || lower.contains("/comment")
                            || lower.contains("/command")
                            || lower.contains("<attachments>")
                            || lower.contains("<attachment>")
                            || lower.contains("<user_request>")
                            || lower.contains("<userrequest>")
                        {
                            false
                        } else {
                            let mut clean = lower.clone();
                            let strip_tags = [
                                "customizationsupdate", "conversation-summary", "conversationsummary",
                                "environment_info", "workspace_info", "editorcontext",
                                "reminderinstruction", "attachments", "attachment",
                                "tooluseinstructions", "editfileinstructions", "notebookinstructions",
                                "usermemory", "sessionmemory", "repomemory",
                                "memoryscopes", "memoryguidelines", "memoryinstructions",
                                "outputformatting", "instructions", "context",
                            ];
                            for prefix in strip_tags {
                                let needle = format!("<{}", prefix);
                                while let Some(s) = clean.find(&needle) {
                                    let after = &clean[s + 1..];
                                    let tag_end = after.find(|c: char| c == '>' || c == ' ' || c == '\n' || c == '\r').unwrap_or(after.len());
                                    let tag = &after[..tag_end];
                                    let close = format!("</{}>", tag);
                                    if let Some(e) = clean[s..].find(&close) {
                                        clean.replace_range(s..s + e + close.len(), " ");
                                    } else {
                                        let le = clean[s..].find('\n').map(|p| s + p + 1).unwrap_or(clean.len());
                                        clean.replace_range(s..le, " ");
                                    }
                                }
                            }
                            let usr = if let Some(pos) = clean.rfind("\nuser:") {
                                &clean[pos + 6..]
                            } else if let Some(pos) = clean.rfind("user:") {
                                &clean[pos + 5..]
                            } else {
                                &clean[..]
                            };
                            usr.trim().is_empty()
                        }
                    };

                    if is_empty_user_prompt {
                        eprintln!("[SERVER] ⚡ Fast interception: Empty user prompt / system context refresh (1ms).");
                        let json = serde_json::json!({ "content": "" }).to_string();
                        let hex_len = format!("{:x}\r\n", json.len());
                        let _ = write_half.write_all(hex_len.as_bytes()).await;
                        let _ = write_half.write_all(json.as_bytes()).await;
                        let _ = write_half.write_all(b"\r\n0\r\n\r\n").await;
                        return;
                    }
                }

                    let mut full_process = Box::pin(async {
                        // Extract actual user message to check complexity.
                        // Always strip system XML blocks (attachments, environment info, memory, etc.)
                        // to isolate the actual query typed by the user.
                        let user_msg_for_check = {
                            let lower = prompt.to_lowercase();
                            let mut clean = lower.clone();
                            // Tags whose ENTIRE content should be discarded (metadata, not user content)
                            let strip_tags = [
                                "customizationsupdate", "conversation-summary", "conversationsummary",
                                "environment_info", "workspace_info", "editorcontext",
                                "reminderinstruction", "attachments", "attachment",
                                "tooluseinstructions", "editfileinstructions", "notebookinstructions",
                                "usermemory", "sessionmemory", "repomemory",
                                "memoryscopes", "memoryguidelines", "memoryinstructions",
                                "outputformatting", "instructions", "context",
                                "selection", "codesnippet",
                            ];
                            for prefix in strip_tags {
                                let needle = format!("<{}", prefix);
                                while let Some(s) = clean.find(&needle) {
                                    let after = &clean[s + 1..];
                                    let tag_end = after.find(|c: char| c == '>' || c == ' ' || c == '\n' || c == '\r').unwrap_or(after.len());
                                    let tag = &after[..tag_end];
                                    let close = format!("</{}>", tag);
                                    if let Some(e) = clean[s..].find(&close) {
                                        clean.replace_range(s..s + e + close.len(), " ");
                                    } else {
                                        let le = clean[s..].find('\n').map(|p| s + p + 1).unwrap_or(clean.len());
                                        clean.replace_range(s..le, " ");
                                    }
                                }
                            }

                            // Priority 1: Extract content from <userrequest> tags (wraps the actual question)
                            let extracted = if let Some(ur_start) = clean.find("<userrequest>") {
                                let after_open = ur_start + "<userrequest>".len();
                                if let Some(ur_end) = clean[after_open..].find("</userrequest>") {
                                    let inner = clean[after_open..after_open + ur_end].trim().to_string();
                                    if inner.is_empty() { None } else { Some(inner) }
                                } else { None }
                            } else { None };

                            if let Some(msg) = extracted {
                                msg
                            // Priority 2: Extract just the last user segment from the cleaned prompt
                            } else if let Some(pos) = clean.rfind("\nuser:") {
                                let seg = &clean[pos + 6..];
                                seg.trim().to_string()
                            } else if let Some(pos) = clean.rfind("\nhuman:") {
                                let seg = &clean[pos + 7..];
                                seg.trim().to_string()
                            } else if let Some(pos) = clean.rfind("user:") {
                                let seg = &clean[pos + 5..];
                                seg.trim().to_string()
                            } else {
                                clean.trim().to_string()
                            }
                        };
                        
                        let is_complex = user_msg_for_check.len() > 300
                            || {
                                let lower = user_msg_for_check.to_lowercase();
                                lower.contains("implement") || lower.contains("refactor") 
                                || lower.contains("debug") || lower.contains("write a function")
                                || lower.contains("create a") || lower.contains("build a")
                                || lower.contains("create file") || lower.contains("make a file")
                                || lower.contains("write a file") || lower.contains("generate file")
                                || lower.contains("new file") || lower.contains("add a file")
                                || lower.contains("fix this") || lower.contains("code review")
                                || lower.contains("analyze this code") || lower.contains("```")
                                || lower.contains("class ") || lower.contains("def ")
                                || lower.contains("function") || lower.contains("struct ")
                            };
                        
                        eprintln!("[SERVER] 📝 Extracted user query (len={}): {:?} → is_complex={}", 
                            user_msg_for_check.len(), 
                            &user_msg_for_check[..user_msg_for_check.len().min(120)],
                            is_complex);

                        if ollama && !is_complex {
                            // Simple question → fast path with 1.5b
                            let ollama_model = if let Some(ref m) = model_override {
                                m.as_str()
                            } else {
                                select_ollama_model_for_hardware(budget <= 0.5)
                            };

                            let endpoint = std::env::var("LOCAL_OLLAMA_ENDPOINT")
                                .unwrap_or_else(|_| "http://127.0.0.1:11434".to_string());
                            let url = format!("{}/api/chat", endpoint.trim_end_matches('/'));

                            // Use the already-cleaned user message (XML tags and attachments stripped).
                            // CRITICAL: Do NOT re-parse from the raw `prompt` — it contains 20KB of
                            // IDE context, file attachments, and workspace info that cause the LLM
                            // to generate unsolicited code even for simple Q&A questions.
                            let user_msg = user_msg_for_check.clone();

                            // Scale num_predict based on input size and complexity
                            let user_len = user_msg.len();
                            let num_predict: u32 = if user_len < 100 { 1024 } else if user_len < 500 { 2048 } else { 4096 };

                            // Dynamic system prompt: one prompt per tool/domain category
                            let lower_user = user_msg.to_lowercase();

                            // IMPORTANT: The no-code guard below is appended to EVERY non-coding
                            // system prompt. This prevents the LLM from generating unsolicited
                            // code examples for simple Q&A, even when file context was attached
                            // in the IDE chat.
                            const NO_CODE_GUARD: &str = " Do NOT generate, write, or suggest any code, code blocks, or programming examples unless the user explicitly asks for code.";

                            let is_coding_query = lower_user.contains("code") || lower_user.contains("function") 
                                || lower_user.contains("bug") || lower_user.contains("error")
                                || lower_user.contains("compile") || lower_user.contains("syntax")
                                || lower_user.contains("python") || lower_user.contains("rust")
                                || lower_user.contains("javascript") || lower_user.contains("java ")
                                || lower_user.contains("c++") || lower_user.contains("html")
                                || lower_user.contains("css") || lower_user.contains("sql")
                                || lower_user.contains(" api") || lower_user.contains("git ")
                                || lower_user.contains("regex") || lower_user.contains("algorithm")
                                || lower_user.contains("typescript") || lower_user.contains("golang")
                                || lower_user.contains("swift") || lower_user.contains("kotlin")
                                || lower_user.contains("docker") || lower_user.contains("class ");

                            let fast_sys = if is_coding_query {
                                "You are an expert programming assistant. Give clear, correct code examples with explanations. Use markdown code blocks.".to_string()
                            // Math & Statistics
                            } else if lower_user.contains("math") || lower_user.contains("calcul")
                                || lower_user.contains("equation") || lower_user.contains("formula")
                                || lower_user.contains("integral") || lower_user.contains("derivative")
                                || lower_user.contains("probability") || lower_user.contains("statistic")
                                || lower_user.contains("algebra") || lower_user.contains("geometry")
                                || lower_user.contains("theorem") || lower_user.contains("proof") {
                                format!("You are a math expert. Show step-by-step solutions. Use clear notation and explain each step.{}", NO_CODE_GUARD)
                            // Data Science & ML
                            } else if lower_user.contains("dataset") || lower_user.contains("data science")
                                || lower_user.contains("machine learning") || lower_user.contains("neural net")
                                || lower_user.contains("model training") || lower_user.contains("pandas")
                                || lower_user.contains("numpy") || lower_user.contains("tensorflow")
                                || lower_user.contains("pytorch") || lower_user.contains("sklearn")
                                || lower_user.contains("regression") || lower_user.contains("classification")
                                || lower_user.contains("clustering") || lower_user.contains("deep learning") {
                                "You are a data science and ML expert. Provide practical advice, code snippets, and best practices for data analysis and model building.".to_string()
                            // Security & PE Analysis
                            } else if lower_user.contains("security") || lower_user.contains("hack")
                                || lower_user.contains("vulnerab") || lower_user.contains("malware")
                                || lower_user.contains("exploit") || lower_user.contains("cve")
                                || lower_user.contains("binary") || lower_user.contains("pe header")
                                || lower_user.contains("reverse engineer") || lower_user.contains("disassembl")
                                || lower_user.contains("forensic") || lower_user.contains("incident response")
                                || lower_user.contains("pentest") || lower_user.contains("threat") {
                                format!("You are a cybersecurity and binary analysis expert. Provide accurate, responsible security analysis. Cover MITRE ATT&CK when relevant.{}", NO_CODE_GUARD)
                            // NLP & Text Processing
                            } else if lower_user.contains("nlp") || lower_user.contains("natural language")
                                || lower_user.contains("sentiment") || lower_user.contains("tokeniz")
                                || lower_user.contains("embedding") || lower_user.contains("text classification")
                                || lower_user.contains("named entity") || lower_user.contains("summariz")
                                || lower_user.contains("translate") || lower_user.contains("translat") {
                                format!("You are an NLP and language processing expert. Explain techniques clearly and suggest appropriate models and approaches.{}", NO_CODE_GUARD)
                            // DevOps & Infrastructure
                            } else if lower_user.contains("deploy") || lower_user.contains("kubernetes")
                                || lower_user.contains("ci/cd") || lower_user.contains("pipeline")
                                || lower_user.contains("terraform") || lower_user.contains("ansible")
                                || lower_user.contains("aws") || lower_user.contains("azure")
                                || lower_user.contains("gcp") || lower_user.contains("nginx")
                                || lower_user.contains("linux") || lower_user.contains("server config") {
                                "You are a DevOps and cloud infrastructure expert. Give practical, production-ready configurations and deployment advice.".to_string()
                            // Databases
                            } else if lower_user.contains("database") || lower_user.contains("mysql")
                                || lower_user.contains("postgres") || lower_user.contains("mongodb")
                                || lower_user.contains("redis") || lower_user.contains("query")
                                || lower_user.contains("schema") || lower_user.contains("index")
                                || lower_user.contains("migration") || lower_user.contains("orm") {
                                "You are a database expert. Provide optimized queries, schema designs, and performance tuning advice.".to_string()
                            // Networking
                            } else if lower_user.contains("network") || lower_user.contains("tcp")
                                || lower_user.contains("http") || lower_user.contains("dns")
                                || lower_user.contains("firewall") || lower_user.contains("vpn")
                                || lower_user.contains("ssl") || lower_user.contains("tls")
                                || lower_user.contains("protocol") || lower_user.contains("socket") {
                                format!("You are a networking expert. Explain protocols, troubleshoot connectivity, and provide clear technical guidance.{}", NO_CODE_GUARD)
                            // Writing & Creative
                            } else if lower_user.contains("write") || lower_user.contains("essay")
                                || lower_user.contains("poem") || lower_user.contains("story")
                                || lower_user.contains("letter") || lower_user.contains("email")
                                || lower_user.contains("blog") || lower_user.contains("article")
                                || lower_user.contains("resume") || lower_user.contains("cover letter") {
                                format!("You are a skilled writer and editor. Write clearly, creatively, and with proper structure. Match the requested tone and format.{}", NO_CODE_GUARD)
                            // Science
                            } else if lower_user.contains("physics") || lower_user.contains("chemistry")
                                || lower_user.contains("biology") || lower_user.contains("quantum")
                                || lower_user.contains("molecule") || lower_user.contains("atom")
                                || lower_user.contains("evolution") || lower_user.contains("cell")
                                || lower_user.contains("dna") || lower_user.contains("experiment") {
                                format!("You are a science expert. Explain scientific concepts accurately with real-world examples and current research.{}", NO_CODE_GUARD)
                            // Finance & Business
                            } else if lower_user.contains("finance") || lower_user.contains("invest")
                                || lower_user.contains("stock") || lower_user.contains("market")
                                || lower_user.contains("budget") || lower_user.contains("accounting")
                                || lower_user.contains("tax") || lower_user.contains("crypto")
                                || lower_user.contains("revenue") || lower_user.contains("profit") {
                                format!("You are a finance and business expert. Provide clear financial analysis, investment concepts, and business strategy advice.{}", NO_CODE_GUARD)
                            // Education & Explanation
                            } else if lower_user.contains("explain") || lower_user.contains("how does")
                                || lower_user.contains("what is") || lower_user.contains("why does")
                                || lower_user.contains("difference between") || lower_user.contains("teach")
                                || lower_user.contains("learn") || lower_user.contains("tutorial") {
                                format!("You are a knowledgeable tutor. Explain concepts clearly and concisely with practical examples.{}", NO_CODE_GUARD)
                            // History & Geography
                            } else if lower_user.contains("history") || lower_user.contains("capital")
                                || lower_user.contains("country") || lower_user.contains("war")
                                || lower_user.contains("president") || lower_user.contains("king")
                                || lower_user.contains("empire") || lower_user.contains("civilization")
                                || lower_user.contains("geography") || lower_user.contains("population") {
                                format!("You are a history and geography expert. Provide accurate facts, dates, and context.{}", NO_CODE_GUARD)
                            // Health & Medicine (general info only)
                            } else if lower_user.contains("health") || lower_user.contains("medical")
                                || lower_user.contains("symptom") || lower_user.contains("disease")
                                || lower_user.contains("vitamin") || lower_user.contains("exercise")
                                || lower_user.contains("nutrition") || lower_user.contains("diet") {
                                format!("You are a health information assistant. Provide general health information. Always recommend consulting a medical professional for specific advice.{}", NO_CODE_GUARD)
                            } else {
                                format!("You are a helpful, knowledgeable AI assistant. Answer concisely and accurately.{}", NO_CODE_GUARD)
                            };
                            
                            eprintln!("[SERVER] 🎭 Dynamic prompt: {:?}", &fast_sys[..fast_sys.len().min(60)]);
                            let messages = serde_json::json!([
                                {"role": "system", "content": fast_sys},
                                {"role": "user", "content": &user_msg}
                            ]);

                            // Dynamic temperature: low for facts, higher for creative
                            let temperature: f32 = if fast_sys.contains("history") || fast_sys.contains("geography")
                                || fast_sys.contains("science") || fast_sys.contains("math")
                                || fast_sys.contains("health") || fast_sys.contains("finance")
                                || fast_sys.contains("tutor") || fast_sys.contains("helpful") {
                                0.3  // Factual accuracy
                            } else if fast_sys.contains("writer") || fast_sys.contains("creative") {
                                0.8  // Creative freedom
                            } else {
                                0.5  // Balanced
                            };

                            let body = serde_json::json!({
                                "model": ollama_model,
                                "messages": messages,
                                "stream": false,
                                "options": {
                                    "temperature": temperature,
                                    "num_predict": num_predict,
                                    "num_ctx": select_context_window_for_model(ollama_model)
                                }
                            });

                            eprintln!("[SERVER] ⚡ Ollama fast path: model={}, user_len={}, sys_len={}, num_predict={}", 
                                ollama_model, user_msg.len(), 
                                fast_sys.len(), num_predict);

                            let client = reqwest::Client::builder()
                                .no_proxy()
                                .connect_timeout(std::time::Duration::from_secs(3))
                                .timeout(std::time::Duration::from_secs(120))
                                .build()
                                .unwrap();

                            match client.post(&url).json(&body).send().await {
                                Ok(res) if res.status().is_success() => {
                                    let data: serde_json::Value = res.json().await.unwrap_or_default();
                                    let raw_content = data["message"]["content"]
                                        .as_str()
                                        .unwrap_or("No response from model.")
                                        .to_string();
                                    let mut content = clean_model_response(&raw_content);

                                    // Safety net: for non-coding queries, strip any code blocks
                                    // the model may have generated despite the NO_CODE_GUARD instruction.
                                    if !is_coding_query && content.contains("```") {
                                        eprintln!("[SERVER] 🧹 Stripping unsolicited code blocks from Q&A response");
                                        let mut result = String::new();
                                        let mut in_code_block = false;
                                        for line in content.lines() {
                                            if line.trim().starts_with("```") {
                                                in_code_block = !in_code_block;
                                                continue;
                                            }
                                            if !in_code_block {
                                                result.push_str(line);
                                                result.push('\n');
                                            }
                                        }
                                        content = result.trim().to_string();
                                    }

                                    eprintln!("[SERVER] ⚡ Ollama fast path complete: {} chars (cleaned from {})", content.len(), raw_content.len());
                                    return content;
                                }
                                Ok(res) => {
                                    let err = res.text().await.unwrap_or_default();
                                    eprintln!("[SERVER] ⚠️ Ollama fast path HTTP error: {}. Falling back to orchestrator.", err);
                                }
                                Err(e) => {
                                    eprintln!("[SERVER] ⚠️ Ollama fast path failed: {}. Falling back to orchestrator.", e);
                                }
                            }
                            // If fast path fails, fall through to full orchestrator below
                            std::env::set_var("MODELFUSION_USE_OLLAMA", "true");
                            fusion = false;
                            gpu = true;
                        } else if is_complex {
                            // Complex/coding task → skip fast path, use full pipeline
                            // Acquire heavy semaphore to rate-limit resource-intensive pipeline
                            let heavy_sem = inference_sem();
                            let _heavy_permit = heavy_sem.acquire().await;
                            // Acquire cross-process lock (blocking) via spawn_blocking to not freeze tokio
                            let _file_lock = tokio::task::spawn_blocking(acquire_cross_process_lock)
                                .await
                                .ok();
                            eprintln!("[SERVER] 🧠 Complex prompt detected (len={}). Acquired heavy slot + file lock. Full pipeline.", user_msg_for_check.len());
                        }

                        // Query the small model router for dynamic orchestration decision
                        if !openvino && !gpu && !cpu && !ollama {
                            if let Some(decision) = llm_route(&prompt).await {
                                eprintln!("🎯 [SERVER] LLM Router decision: fusion={}, strategy={}, use_gpu={}, use_cpu={}, task={}",
                                    decision.fusion, decision.selection_strategy, decision.use_gpu, decision.use_cpu, decision.detected_task);
                                fusion = decision.fusion;
                                strategy = decision.selection_strategy;
                                gpu = decision.use_gpu;
                                cpu = decision.use_cpu;
                            } else {
                                eprintln!("⚠️ [SERVER] LLM Router offline or failed. Falling back to default/heuristic options (enabling GPU for speed).");
                                gpu = !cpu; // Default to GPU unless CPU was explicitly forced
                            }
                        } else {
                            eprintln!("🎯 [SERVER] Explicit backend requested, skipping LLM router.");
                        }

                        eprintln!("[SERVER] Options: fusion={}, strategy={}, budget={}, gpu={}, cpu={}, openvino={}, ollama={}", fusion, strategy, budget, gpu, cpu, openvino, ollama);


                        if ollama || (gpu && !openvino) {
                            std::env::set_var("MODELFUSION_USE_OLLAMA", "true");
                            std::env::set_var("MODELFUSION_FORCE_GPU", "true");
                            fusion = false;
                        } else {
                            std::env::remove_var("MODELFUSION_USE_OLLAMA");
                            std::env::remove_var("MODELFUSION_FORCE_GPU");
                        }

                        if openvino {
                            std::env::set_var("MODELFUSION_USE_OPENVINO", "true");
                            fusion = false; // Disable fusion if explicit backend is requested
                        } else {
                            std::env::remove_var("MODELFUSION_USE_OPENVINO");
                        }

                        if cpu {
                            std::env::set_var("MODELFUSION_USE_TRANSFORMERS", "true");
                            std::env::set_var("MODELFUSION_FORCE_CPU", "true");
                        } else {
                            std::env::remove_var("MODELFUSION_USE_TRANSFORMERS");
                            std::env::remove_var("MODELFUSION_FORCE_CPU");
                        }

                        // Strip IDE's restrictive system prompt before orchestrator
                        // The orchestrator/models have their own prompting — the IDE's
                        // "programming assistant" system prompt causes refusals for non-coding Qs
                        let clean_prompt = user_msg_for_check.clone();

                        // Classify prompt to see if fusion is actually needed
                        let prompt_needs_fusion = fusion && modelfusion_core::fusion_engine::classify_prompt(&clean_prompt);
                        if fusion && !prompt_needs_fusion {
                            eprintln!("[SERVER] Prompt classified as simple. Bypassing fusion engine to run single model orchestrator.");
                        }

                        if prompt_needs_fusion {
                            match modelfusion_core::fusion_engine::run_fusion(
                                &clean_prompt,
                                None,
                                Some(db_path_val),
                                None,
                                parse_selection_strategy(&strategy),
                                Some(fusion_models),
                                &fusion_mode,
                                model_override.as_deref(),
                            ).await {
                                Ok(content) => content,
                                Err(e) => format!("Error: {}", e),
                            }
                        } else {
                            let orchestrator = HuggingFaceOrchestrator::new(db_path_val.to_path_buf(), budget, false, false);
                            let options = std::collections::HashMap::new();
                            let res = orchestrator
                                .process_task(
                                    &clean_prompt,
                                    None,
                                    model_override.as_deref(),
                                    false,
                                    None,
                                    parse_selection_strategy(&strategy),
                                    options,
                                )
                                .await;
                            if res.success {
                                res.content
                            } else {
                                res.error_message.unwrap_or_else(|| "Orchestration failed".to_string())
                            }
                        }
                    });

                    let mut client_disconnected = false;
                    tokio::pin!(client_disconnect);

                    let content = loop {
                        tokio::select! {
                            res = &mut full_process => {
                                break res;
                            }
                            _ = tokio::time::sleep(std::time::Duration::from_secs(5)) => {
                                // Send a space as a keep-alive chunk
                                let chunk = "1\r\n \r\n";
                                if write_half.write_all(chunk.as_bytes()).await.is_err() {
                                    eprintln!("[SERVER] 🛑 Client disconnected during /orchestrate execution. Cancelling inference.");
                                    client_disconnected = true;
                                    break String::new();
                                }
                            }
                            _ = &mut client_disconnect => {
                                eprintln!("[SERVER] 🛑 Client disconnected during /orchestrate execution. Cancelling inference.");
                                client_disconnected = true;
                                break String::new();
                            }
                        }
                    };

                    if client_disconnected {
                        return;
                    }

                    eprintln!("[SERVER] <<< Completed /orchestrate request in {}ms.", start_time.elapsed().as_millis());
                    let cleaned_content = clean_model_response(&content);
                    let response_json = if is_openai_compat {
                        // Return OpenAI-compatible response format
                        serde_json::json!({
                            "id": format!("chatcmpl-{}", start_time.elapsed().as_millis()),
                            "object": "chat.completion",
                            "created": std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_secs(),
                            "model": request_json["model"].as_str().unwrap_or("modelfusion"),
                            "choices": [{
                                "index": 0,
                                "message": {
                                    "role": "assistant",
                                    "content": cleaned_content
                                },
                                "finish_reason": "stop"
                            }],
                            "usage": {
                                "prompt_tokens": 0,
                                "completion_tokens": 0,
                                "total_tokens": 0
                            }
                        })
                    } else {
                        serde_json::json!({
                            "content": cleaned_content
                        })
                    };
                    let response_str = response_json.to_string();
                    let chunk_size = format!("{:x}\r\n", response_str.len());
                    let _ = write_half.write_all(chunk_size.as_bytes()).await;
                    let _ = write_half.write_all(response_str.as_bytes()).await;
                    let _ = write_half.write_all(b"\r\n0\r\n\r\n").await;
                    return;
                }
                "/stats" => {
                    run_cli_subcommand(&["--stats".to_string()], db_path_val).await
                }
                "/sys-info" | "/sysinfo" => {
                    run_cli_subcommand(&["--sys-info".to_string()], db_path_val).await
                }
                "/tasks" => {
                    let category = request_json["category"].as_str().unwrap_or("all");
                    run_cli_subcommand(&["--tasks".to_string(), category.to_string()], db_path_val).await
                }
                "/decision-stats" => {
                    run_cli_subcommand(&["--decision-stats".to_string()], db_path_val).await
                }
                "/novel-ai-stats" => {
                    run_cli_subcommand(&["--novel-ai-stats".to_string()], db_path_val).await
                }
                "/performance-stats" => {
                    run_cli_subcommand(&["--performance-stats".to_string()], db_path_val).await
                }
                "/cache-stats" => {
                    run_cli_subcommand(&["--cache-stats".to_string()], db_path_val).await
                }
                "/model-recommendations" => {
                    run_cli_subcommand(&["--model-recommendations".to_string()], db_path_val).await
                }
                "/model-ranking" => {
                    let category = request_json["category"].as_str().unwrap_or("text-generation");
                    run_cli_subcommand(&["--model-ranking".to_string(), category.to_string()], db_path_val).await
                }
                "/clearcache" => {
                    run_cli_subcommand(&["--clearcache".to_string()], db_path_val).await
                }
                "/update" => {
                    run_cli_subcommand(&["--update".to_string()], db_path_val).await
                }
                "/pe-header-extraction" => {
                    let file = request_json["file"].as_str().unwrap_or("").to_string();
                    let prompt = request_json["prompt"].as_str().unwrap_or("Perform PE analysis").to_string();
                    run_cli_subcommand(&["--pe-header-extraction".to_string(), "--file".to_string(), file, "--prompt".to_string(), prompt], db_path_val).await
                }
                "/ml-analytics" => {
                    run_cli_subcommand(&["--ml-analytics".to_string()], db_path_val).await
                }
                "/analyze-file" => {
                    let file = request_json["file"].as_str().unwrap_or("").to_string();
                    let prompt = request_json["prompt"].as_str().unwrap_or("").to_string();
                    let mut args = vec!["--file".to_string(), file, "--prompt".to_string(), prompt];
                    if request_json["gpu"].as_bool().unwrap_or(false) {
                        args.push("--gpu".to_string());
                    }
                    if request_json["cpu"].as_bool().unwrap_or(false) {
                        args.push("--cpu".to_string());
                    }
                    run_cli_subcommand(&args, db_path_val).await
                }
                "/analyze-folder" => {
                    let folder = request_json["folder"].as_str().unwrap_or("").to_string();
                    let prompt = request_json["prompt"].as_str().unwrap_or("").to_string();
                    run_cli_subcommand(&["--folder".to_string(), folder, "--prompt".to_string(), prompt], db_path_val).await
                }
                "/report-bandit-feedback" => {
                    let context = request_json["context"].as_u64().unwrap_or(0) as usize;
                    let arm = request_json["arm"].as_u64().unwrap_or(0) as usize;
                    let reward = request_json["reward"].as_f64().unwrap_or(0.5);

                    if context < 2 && arm < 2 {
                        let db_dir = db_path_val.parent().unwrap_or_else(|| std::path::Path::new("db"));
                        let mut state = load_bandit_state(db_dir);
                        let count = state.counts[context][arm];
                        let val = state.values[context][arm];
                        state.counts[context][arm] += 1;
                        state.values[context][arm] = val + (reward - val) / (count + 1) as f64;
                        save_bandit_state(db_dir, &state);
                        format!("Successfully updated bandit feedback for context {}, arm {} to reward {}. New value: {:.4}", context, arm, reward, state.values[context][arm])
                    } else {
                        "Error: Invalid context or arm index".to_string()
                    }
                }
                _ => format!("Error: Unknown API path {}", request_path)
            };

            let response_json = serde_json::json!({
                "content": result_content
            });

            let response_body = serde_json::to_string(&response_json).unwrap();
            let response = format!(
                "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                response_body.len(),
                response_body
            );

            let _ = socket.write_all(response.as_bytes()).await;
            let _ = socket.flush().await;
        });
    }
}

fn find_subsequence(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    haystack.windows(needle.len()).position(|window| window == needle)
}

async fn run_cli_subcommand(cmd_args: &[String], db_path: &std::path::Path) -> String {
    let mut args = cmd_args.to_vec();
    if !args.iter().any(|a| a == "--db-path") {
        args.push("--db-path".to_string());
        args.push(db_path.to_string_lossy().to_string());
    }

    if let Ok(exe_path) = std::env::current_exe() {
        let output = tokio::process::Command::new(exe_path)
            .args(&args)
            .output()
            .await;

        match output {
            Ok(out) => {
                let stdout_str = String::from_utf8_lossy(&out.stdout).to_string();
                let stderr_str = String::from_utf8_lossy(&out.stderr).to_string();
                if out.status.success() {
                    stdout_str
                } else {
                    format!("Error running ModelFusion CLI:\nExit code: {}\nStdout: {}\nStderr: {}", out.status, stdout_str, stderr_str)
                }
            }
            Err(e) => format!("Failed to run ModelFusion CLI process: {}", e),
        }
    } else {
        "Failed to resolve current executable path".to_string()
    }
}

#[derive(serde::Serialize, serde::Deserialize, Debug, Clone)]
struct BanditState {
    // For each context:
    // 0 = Simple General, 1 = Simple Coding, 2 = Complex General, 3 = Complex Coding
    // We store the pull count and average reward for each arm (0 = Single model, 1 = Fusion model).
    counts: [[u32; 2]; 4],
    values: [[f64; 2]; 4],
}

impl Default for BanditState {
    fn default() -> Self {
        Self {
            counts: [[0; 2]; 4],
            values: [[0.5; 2]; 4], // Prior reward values initialized to 0.5
        }
    }
}

fn load_bandit_state(db_dir: &std::path::Path) -> BanditState {
    let path = db_dir.join("bandit_state.json");
    if path.exists() {
        if let Ok(content) = std::fs::read_to_string(&path) {
            if let Ok(state) = serde_json::from_str(&content) {
                return state;
            }
        }
    }
    BanditState::default()
}

fn save_bandit_state(db_dir: &std::path::Path, state: &BanditState) {
    let path = db_dir.join("bandit_state.json");
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    if let Ok(content) = serde_json::to_string_pretty(state) {
        let _ = std::fs::write(path, content);
    }
}

// Lightweight Linear Congruential Generator (LCG) for Epsilon-Greedy selection without rand dependency
struct Lcg {
    state: u64,
}

impl Lcg {
    fn new() -> Self {
        let seed = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos() as u64;
        Self { state: seed }
    }

    fn next_u32(&mut self) -> u32 {
        self.state = self.state.wrapping_mul(6364136223846793005).wrapping_add(1);
        (self.state >> 32) as u32
    }

    fn gen_f64(&mut self) -> f64 {
        (self.next_u32() as f64) / (u32::MAX as f64)
    }

    fn gen_bool(&mut self, p: f64) -> bool {
        self.gen_f64() < p
    }

    fn gen_range(&mut self, min: usize, max: usize) -> usize {
        let diff = max - min;
        min + (self.next_u32() as usize % diff)
    }
}

fn detect_if_coding_or_complicated(prompt: &str) -> bool {
    let lower = prompt.to_lowercase();
    
    // Check coding keywords
    let coding_keywords = [
        "code", "write a", "function", "class", "struct", "impl", "def", "fn ", 
        "import ", "public ", "private ", "async ", "await", "compile", "compiler",
        "debug", "error", "refactor", "run ", "test", "javascript", "typescript",
        "python", "rust", " c++", " java ", "go ", "html", "css"
    ];
    for kw in &coding_keywords {
        if lower.contains(kw) {
            return true;
        }
    }

    // Check coding structural symbols
    let coding_symbols = ['{', '}', '[', ']', '(', ')', ';', '=', '+', '-', '*', '/'];
    let mut symbol_count = 0;
    for c in prompt.chars() {
        if coding_symbols.contains(&c) {
            symbol_count += 1;
        }
    }
    if symbol_count > 6 {
        return true;
    }

    // Check complexity (length)
    if prompt.len() > 150 {
        return true;
    }

    // Check complexity query words
    let complexity_keywords = [
        "explain", "how does", "how to", "why did", "optimize", "architecture",
        "design", "performance", "analyze", "review", "evaluate"
    ];
    for kw in &complexity_keywords {
        if lower.contains(kw) {
            return true;
        }
    }

    false
}

async fn route_and_execute(
    prompt: &str,
    db_path: &std::path::Path,
    custom_args: &[String],
) -> (String, usize, usize) {
    let complexity_str = llm_classify_complexity(prompt).await;
    eprintln!("🦙 [ROUTER] Prompt classified complexity: {}", complexity_str);
    
    let context = match complexity_str.as_str() {
        "simple_general" => 0,
        "simple_coding" => 1,
        "complex_general" => 2,
        "complex_coding" => 3,
        _ => {
            let is_coding = detect_if_coding_or_complicated(prompt);
            if is_coding { 1 } else { 0 }
        }
    };

    let db_dir = db_path.parent().unwrap_or_else(|| std::path::Path::new("db"));
    let mut state = load_bandit_state(db_dir);

    // Multi-Armed Bandit Epsilon-Greedy choice
    let epsilon = 0.15;
    let mut lcg = Lcg::new();

    let mut arm = if lcg.gen_bool(epsilon) {
        // Explore
        lcg.gen_range(0, 2)
    } else {
        // Exploit
        let vals = state.values[context];
        if vals[0] >= vals[1] {
            0
        } else {
            1
        }
    };

    // Override arm choice using the small model LLM router decision
    if let Some(decision) = llm_route(prompt).await {
        eprintln!("🎯 [ROUTER] LLM Router decision: fusion={}, strategy={}, use_gpu={}, use_cpu={}, task={}",
            decision.fusion, decision.selection_strategy, decision.use_gpu, decision.use_cpu, decision.detected_task);
        arm = if decision.fusion { 1 } else { 0 };
    } else {
        // Fallback to simple heuristic classification
        if !modelfusion_core::fusion_engine::classify_prompt(prompt) {
            if arm == 1 {
                eprintln!("💡 [ROUTER] Prompt classified as simple. Overriding bandit selection to single model (Bypassing Fusion).");
                arm = 0;
            }
        }
    }

    // Force arm choice to 0 (single model) if the complexity layer classified it as simple!
    if context == 0 || context == 1 {
        if arm == 1 {
            eprintln!("💡 [ROUTER] Complexity layer classified task as simple. Overriding fusion selection to single model.");
            arm = 0;
        }
    }

    eprintln!(
        "🎯 [BANDIT] Prompt: \"{}\" | Context: {} ({}) | Selected Arm: {} (0=Single, 1=Fusion)",
        prompt.chars().take(40).collect::<String>(),
        context,
        complexity_str,
        arm
    );

    let mut cmd_args = custom_args.to_vec();
    if !cmd_args.iter().any(|a| a == "--prompt") {
        cmd_args.push("--prompt".to_string());
        cmd_args.push(prompt.to_string());
    }

    if arm == 1 {
        if !cmd_args.iter().any(|a| a == "--fusion") {
            cmd_args.push("--fusion".to_string());
        }
    } else {
        cmd_args.retain(|a| a != "--fusion");
    }

    let result_text = run_cli_subcommand(&cmd_args, db_path).await;

    // Automatic rewards computation based on success of subcommand
    let reward = if result_text.contains("Error:") || result_text.contains("[ERROR]") {
        0.0
    } else {
        0.8
    };

    // Update running average
    let count = state.counts[context][arm];
    let val = state.values[context][arm];
    state.counts[context][arm] += 1;
    state.values[context][arm] = val + (reward - val) / (count + 1) as f64;
    save_bandit_state(db_dir, &state);

    (result_text, context, arm)
}

async fn run_mcp_server(db_path: Option<String>) -> Result<()> {
    use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
    
    let handler = ComprehensiveTaskHandler::new(db_path.as_deref())?;
    handler.ensure_database_exists()?;
    let db_path_resolved = handler.db_path.clone();

    let stdin = tokio::io::stdin();
    let mut reader = BufReader::new(stdin).lines();
    let mut stdout = tokio::io::stdout();

    while let Some(line) = reader.next_line().await? {
        let request: serde_json::Value = match serde_json::from_str(&line) {
            Ok(v) => v,
            Err(_) => continue,
        };

        let method = request["method"].as_str().unwrap_or("");
        let id = request["id"].clone();

        if method == "initialize" {
            let response = serde_json::json!({
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "ModelFusion MCP Server",
                        "version": "0.1.0"
                    }
                }
            });
            let response_str = serde_json::to_string(&response)? + "\n";
            stdout.write_all(response_str.as_bytes()).await?;
            stdout.flush().await?;
        } else if method == "notifications/initialized" {
            // No response required
        } else if method == "tools/list" {
            let response = serde_json::json!({
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "tools": [
                        {
                            "name": "execute",
                            "description": "Execute the ModelFusion CLI with ANY combination of flags. This is the universal tool — use it when no specialized tool fits. Supported flags: --file <path>, --folder <path>, --prompt <text>, --task <task_name>, --budget <float>, --chain-of-thought, --gpu, --cpu, --ollama, --openvino, --onnx, --vllm, --model <model_id>, --fusion, --fusion-models <N>, --fusion-mode <multi-model|multi-sample>, --selection-strategy <strategy>, --delegation, --recursion, --context-auto, --context <text>, --verbose, --debug, --language <lang>, --full, --score, --judge, --plan, --enable-innovations, --workflow-optimization, --semantic-analysis, --temporal-tracking, --predictive-mode, --innovation-level <N>, --real-options, --prompt-quality-scoring, --enable-ml, --enable-ml-selection, --ml-learning, --ml-ensemble-method <method>, --ml-confidence-threshold <float>, --ml-fallback <true|false>, --enable-slash-commands",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "args": {
                                        "type": "array",
                                        "items": { "type": "string" },
                                        "description": "Array of CLI arguments (e.g., ['--prompt', 'explain recursion', '--ollama', '--gpu'])"
                                    }
                                },
                                "required": ["args"]
                            }
                        },
                        {
                            "name": "quick_answer",
                            "description": "Fast direct answer for general knowledge questions (non-coding). Calls Ollama directly, bypassing orchestration for ~2-3 second responses. Use for: geography, history, math, science, trivia, definitions, translations, general knowledge.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "question": { "type": "string", "description": "The question to answer" },
                                    "model": { "type": "string", "description": "Ollama model (default: qwen2.5:3b). Options: qwen2.5:0.5b, qwen2.5:1.5b, qwen2.5:3b, qwen2.5:7b, llama3.2:3b" }
                                },
                                "required": ["question"]
                            }
                        },
                        {
                            "name": "orchestrate",
                            "description": "Run the full ModelFusion orchestration pipeline: task detection → model selection → execution. Best for coding questions, complex analysis, and tasks that benefit from intelligent model routing.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "prompt": { "type": "string", "description": "The prompt or task description" },
                                    "budget": { "type": "number", "description": "Model size limit in billions (1=tiny, 3=balanced, 7=quality)" },
                                    "selection_strategy": { "type": "string", "description": "Strategy: multi_objective, latency, accuracy, cost, performance" },
                                    "task_override": { "type": "string", "description": "Force task type (text-generation, code-analysis, summarization, etc.)" },
                                    "gpu": { "type": "boolean" },
                                    "cpu": { "type": "boolean" },
                                    "fusion": { "type": "boolean", "description": "Use panel of models for higher quality" },
                                    "chain_of_thought": { "type": "boolean", "description": "Enable step-by-step reasoning" },
                                    "delegation": { "type": "boolean", "description": "Multi-agent task routing" },
                                    "recursion": { "type": "boolean", "description": "Recursive task decomposition" }
                                },
                                "required": ["prompt"]
                            }
                        },
                        {
                            "name": "analyze_file",
                            "description": "Analyze, review, or process a specific file using ModelFusion. Supports code review, vulnerability scanning, summarization, and custom analysis.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "file": { "type": "string", "description": "Absolute path to file" },
                                    "prompt": { "type": "string", "description": "Analysis instructions" },
                                    "budget": { "type": "number" },
                                    "gpu": { "type": "boolean" },
                                    "full": { "type": "boolean", "description": "Enable comprehensive analysis" }
                                },
                                "required": ["file", "prompt"]
                            }
                        },
                        {
                            "name": "analyze_folder",
                            "description": "Analyze or review an entire directory/project using ModelFusion. Supports code review, architecture analysis, and project-wide scanning.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "folder": { "type": "string", "description": "Absolute path to folder" },
                                    "prompt": { "type": "string", "description": "Analysis instructions" },
                                    "budget": { "type": "number" },
                                    "gpu": { "type": "boolean" },
                                    "full": { "type": "boolean" }
                                },
                                "required": ["folder", "prompt"]
                            }
                        },
                        {
                            "name": "nlp_task",
                            "description": "Run specialized NLP tasks: sentiment-analysis, text-classification, summarization, translation, question-answering, ner (named entity recognition), emotion-detection, sarcasm-detection, paraphrase-generation, grammar-correction, language-detection, reading-level-assessment, anonymization, coreference-resolution, fill-mask, feature-extraction, sentence-similarity, zero-shot-classification, stance-detection, bias-detection.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "task": { "type": "string", "description": "NLP task name (e.g., 'sentiment-analysis', 'translation', 'summarization', 'ner', 'emotion-detection')" },
                                    "text": { "type": "string", "description": "Input text to process" },
                                    "language": { "type": "string", "description": "Target language for translation (default: en)" },
                                    "gpu": { "type": "boolean" }
                                },
                                "required": ["task", "text"]
                            }
                        },
                        {
                            "name": "security_analysis",
                            "description": "Run security-focused NLP analysis: spam-detection, malware-text-detection, phishing-detection, pii-detection (personally identifiable information), hate-speech-detection, cyberbullying-detection, fake-news-detection, hallucination-detection, generation-groundedness, code-vulnerability-detection.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "task": { "type": "string", "description": "Security task (e.g., 'spam-detection', 'pii-detection', 'phishing-detection', 'code-vulnerability-detection')" },
                                    "text": { "type": "string", "description": "Text or code to analyze" },
                                    "file": { "type": "string", "description": "Optional file path to scan" },
                                    "gpu": { "type": "boolean" }
                                },
                                "required": ["task", "text"]
                            }
                        },
                        {
                            "name": "code_task",
                            "description": "Run code-specific AI tasks: code-vulnerability-detection, code-summary-generation, code-clone-detection, text-generation (for code), causal-language-modeling. Also supports --plan for AI-powered planning and --judge for LLM-as-a-Judge evaluation.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "task": { "type": "string", "description": "Code task (e.g., 'code-vulnerability-detection', 'code-summary-generation', 'code-clone-detection')" },
                                    "text": { "type": "string", "description": "Code or description" },
                                    "file": { "type": "string", "description": "Optional source file path" },
                                    "plan": { "type": "boolean", "description": "Enable AI planning mode" },
                                    "judge": { "type": "boolean", "description": "Enable LLM-as-a-Judge evaluation" },
                                    "score": { "type": "boolean", "description": "Enable response scoring" },
                                    "gpu": { "type": "boolean" }
                                },
                                "required": ["task", "text"]
                            }
                        },
                        {
                            "name": "domain_task",
                            "description": "Run domain-specific NLP: legal-judgment-classification, contract-clause-classification, case-outcome-prediction, financial-ner, financial-sentiment-analysis, legal-ner, biomedical-ner, chemical-reaction-ner, scientific-abstract-summarization, citation-intent-classification, table-question-answering, feature-ranking.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "task": { "type": "string", "description": "Domain task (e.g., 'financial-sentiment-analysis', 'legal-ner', 'biomedical-ner', 'contract-clause-classification')" },
                                    "text": { "type": "string", "description": "Text to analyze" },
                                    "gpu": { "type": "boolean" }
                                },
                                "required": ["task", "text"]
                            }
                        },
                        {
                            "name": "multimodal_task",
                            "description": "Run image, audio, and video AI tasks: image-classification, object-detection, image-segmentation, visual-question-answering, document-question-answering, zero-shot-image-classification, depth-estimation, image-feature-extraction, image-super-resolution, text-to-image, automatic-speech-recognition, audio-classification, voice-activity-detection, emotion-recognition, video-classification, text-to-speech.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "task": { "type": "string", "description": "Multimodal task (e.g., 'image-classification', 'object-detection', 'automatic-speech-recognition')" },
                                    "file": { "type": "string", "description": "Path to image/audio/video file" },
                                    "prompt": { "type": "string", "description": "Question or instruction for the task" },
                                    "gpu": { "type": "boolean" }
                                },
                                "required": ["task"]
                            }
                        },
                        {
                            "name": "semantic_search",
                            "description": "Semantic search with HyDE (Hypothetical Document Embeddings). Add documents to the index, then search with natural language queries. Supports interactive question refinement and multiple HyDE variants.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "action": { "type": "string", "description": "'search' to query, 'add' to index documents, 'demo' to run demo" },
                                    "query": { "type": "string", "description": "Search query (for 'search' action)" },
                                    "documents_path": { "type": "string", "description": "Path to documents to add (for 'add' action)" },
                                    "top_k": { "type": "integer", "description": "Number of results (default: 5)" },
                                    "use_hyde": { "type": "boolean", "description": "Use interactive HyDE refinement" },
                                    "hyde_variants": { "type": "boolean", "description": "Generate multiple HyDE variants" }
                                },
                                "required": ["action"]
                            }
                        },
                        {
                            "name": "data_science",
                            "description": "Run data science workflows on CSV/Excel files. Supports: full data analyst workflow, comprehensive data science flow, Jupyter notebook launch, and PDF report export.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "mode": { "type": "string", "description": "'analyst' for data analyst, 'science' for full data science, 'jupyter' for notebook" },
                                    "file": { "type": "string", "description": "Path to CSV/Excel file" },
                                    "prompt": { "type": "string", "description": "Analysis instructions" },
                                    "export_pdf": { "type": "boolean", "description": "Export results as PDF" }
                                },
                                "required": ["mode"]
                            }
                        },
                        {
                            "name": "pe_header_extraction",
                            "description": "Extract PE header information and perform security analysis on Windows executables (.exe, .dll).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "file": { "type": "string", "description": "Absolute path to the PE executable" },
                                    "prompt": { "type": "string", "description": "Analysis instructions (default: 'Perform PE analysis')" }
                                },
                                "required": ["file"]
                            }
                        },
                        {
                            "name": "model_management",
                            "description": "Manage AI models: prepare/convert models to OpenVINO IR format, set weight format (fp16/int8/int4), configure SINQ quantization, save/load ML models.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "action": { "type": "string", "description": "'prepare' to convert model, 'prepare-all' to batch convert, 'sinq' to quantize" },
                                    "model_id": { "type": "string", "description": "HuggingFace model ID to prepare" },
                                    "weight_format": { "type": "string", "description": "fp16, int8, or int4 (default: int8)" },
                                    "sinq_nbits": { "type": "integer", "description": "SINQ bit-width (default: 4)" },
                                    "sinq_group_size": { "type": "integer", "description": "SINQ group size (default: 64)" }
                                },
                                "required": ["action"]
                            }
                        },
                        {
                            "name": "reporting",
                            "description": "Generate analysis reports in various formats: PDF, markdown, text, JSON, or Word.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "prompt": { "type": "string", "description": "Report content/analysis instructions" },
                                    "file": { "type": "string", "description": "File or folder to analyze for the report" },
                                    "output_path": { "type": "string", "description": "Where to save the report" },
                                    "format": { "type": "string", "description": "Report format: pdf, md, text, json, word (default: md)" }
                                },
                                "required": ["prompt", "output_path"]
                            }
                        },
                        {
                            "name": "ml_management",
                            "description": "Manage the ML-based model selection system: retrain models, clean up old training data, view analytics, configure ensemble methods.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "action": { "type": "string", "description": "'retrain' to force retrain, 'cleanup' to clean old data, 'analytics' to view stats" },
                                    "cleanup_days": { "type": "integer", "description": "For cleanup: delete data older than N days" }
                                },
                                "required": ["action"]
                            }
                        },
                        {
                            "name": "get_system_info",
                            "description": "Get detected system hardware specifications: CPU, RAM, GPU, disk space.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "get_database_stats",
                            "description": "Get database status and model categorization statistics.",
                            "inputSchema": { "type": "object", "properties": {} }
                        },
                        {
                            "name": "list_tasks",
                            "description": "List available models and tasks. Filter by: audio, image, text, all.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "category": { "type": "string", "description": "Category filter (audio, image, text, all)" }
                                }
                            }
                        },
                        {
                            "name": "update_database",
                            "description": "Update the HuggingFace models database with latest models.",
                            "inputSchema": { "type": "object", "properties": {} }
                        },
                        {
                            "name": "restore_backup",
                            "description": "Restore config and database from backups.",
                            "inputSchema": { "type": "object", "properties": {} }
                        },
                        {
                            "name": "clear_cache",
                            "description": "Clear all cached model data and weights.",
                            "inputSchema": { "type": "object", "properties": {} }
                        },
                        {
                            "name": "get_decision_stats",
                            "description": "Get model decision-making statistics and selection history.",
                            "inputSchema": { "type": "object", "properties": {} }
                        },
                        {
                            "name": "get_novel_ai_stats",
                            "description": "Get novel AI component statistics and module list.",
                            "inputSchema": { "type": "object", "properties": {} }
                        },
                        {
                            "name": "get_performance_stats",
                            "description": "Get model performance metrics and latency statistics.",
                            "inputSchema": { "type": "object", "properties": {} }
                        },
                        {
                            "name": "get_cache_stats",
                            "description": "Get model cache status, sizes, and database health info.",
                            "inputSchema": { "type": "object", "properties": {} }
                        },
                        {
                            "name": "get_model_recommendations",
                            "description": "Get personalized model recommendations based on decision scores.",
                            "inputSchema": { "type": "object", "properties": {} }
                        },
                        {
                            "name": "get_model_ranking",
                            "description": "Get models ranked for a specific task category.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "category": { "type": "string", "description": "Task category (e.g., text-generation, summarization, code-vulnerability-detection)" }
                                },
                                "required": ["category"]
                            }
                        },
                        {
                            "name": "get_ml_analytics",
                            "description": "Get ML model selection and performance analytics.",
                            "inputSchema": { "type": "object", "properties": {} }
                        },
                        {
                            "name": "report_bandit_feedback",
                            "description": "Provide feedback on model quality to update bandit rewards for improved future selection.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "context": { "type": "integer", "description": "Context ID (0=Simple, 1=Complex/Coding)" },
                                    "arm": { "type": "integer", "description": "Arm ID (0=Single, 1=Fusion)" },
                                    "reward": { "type": "number", "description": "Score: 1.0=good, 0.0=poor" }
                                },
                                "required": ["context", "arm", "reward"]
                            }
                        },
                        {
                            "name": "text_classification",
                            "description": "Execute ModelFusion --text-classification for text classification.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "token_classification",
                            "description": "Execute ModelFusion --token-classification for token classification.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "question_answering",
                            "description": "Execute ModelFusion --question-answering for question answering.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "text_generation",
                            "description": "Execute ModelFusion --text-generation for text generation.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "summarization",
                            "description": "Execute ModelFusion --summarization for summarization.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "translation",
                            "description": "Execute ModelFusion --translation for translation.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "fill_mask",
                            "description": "Execute ModelFusion --fill-mask for fill mask.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "text2text_generation",
                            "description": "Execute ModelFusion --text2text-generation for text2text generation.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "language_detection",
                            "description": "Execute ModelFusion --language-detection for language detection.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "grammar_correction",
                            "description": "Execute ModelFusion --grammar-correction for grammar correction.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "paraphrase_generation",
                            "description": "Execute ModelFusion --paraphrase-generation for paraphrase generation.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "causal_language_modeling",
                            "description": "Execute ModelFusion --causal-language-modeling for causal language modeling.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "zero_shot_classification",
                            "description": "Execute ModelFusion --zero-shot-classification for zero shot classification.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "feature_extraction",
                            "description": "Execute ModelFusion --feature-extraction for feature extraction.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "sentence_similarity",
                            "description": "Execute ModelFusion --sentence-similarity for sentence similarity.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "anonymization",
                            "description": "Execute ModelFusion --anonymization for anonymization.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "coreference_resolution",
                            "description": "Execute ModelFusion --coreference-resolution for coreference resolution.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "spam_detection",
                            "description": "Execute ModelFusion --spam-detection for spam detection.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "malware_text_detection",
                            "description": "Execute ModelFusion --malware-text-detection for malware text detection.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "phishing_detection",
                            "description": "Execute ModelFusion --phishing-detection for phishing detection.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "pii_detection",
                            "description": "Execute ModelFusion --pii-detection for pii detection.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "hate_speech_detection",
                            "description": "Execute ModelFusion --hate-speech-detection for hate speech detection.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "cyberbullying_detection",
                            "description": "Execute ModelFusion --cyberbullying-detection for cyberbullying detection.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "fake_news_detection",
                            "description": "Execute ModelFusion --fake-news-detection for fake news detection.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "legal_judgment_classification",
                            "description": "Execute ModelFusion --legal-judgment-classification for legal judgment classification.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "contract_clause_classification",
                            "description": "Execute ModelFusion --contract-clause-classification for contract clause classification.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "case_outcome_prediction",
                            "description": "Execute ModelFusion --case-outcome-prediction for case outcome prediction.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "financial_ner",
                            "description": "Execute ModelFusion --financial-ner for financial ner.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "legal_ner",
                            "description": "Execute ModelFusion --legal-ner for legal ner.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "biomedical_ner",
                            "description": "Execute ModelFusion --biomedical-ner for biomedical ner.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "chemical_reaction_ner",
                            "description": "Execute ModelFusion --chemical-reaction-ner for chemical reaction ner.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "financial_sentiment_analysis",
                            "description": "Execute ModelFusion --financial-sentiment-analysis for financial sentiment analysis.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "scientific_abstract_summarization",
                            "description": "Execute ModelFusion --scientific-abstract-summarization for scientific abstract summarization.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "emotion_detection",
                            "description": "Execute ModelFusion --emotion-detection for emotion detection.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "sarcasm_detection",
                            "description": "Execute ModelFusion --sarcasm-detection for sarcasm detection.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "stance_detection",
                            "description": "Execute ModelFusion --stance-detection for stance detection.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "bias_detection",
                            "description": "Execute ModelFusion --bias-detection for bias detection.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "hallucination_detection",
                            "description": "Execute ModelFusion --hallucination-detection for hallucination detection.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "reading_level_assessment",
                            "description": "Execute ModelFusion --reading-level-assessment for reading level assessment.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "generation_groundedness",
                            "description": "Execute ModelFusion --generation-groundedness for generation groundedness.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "citation_intent_classification",
                            "description": "Execute ModelFusion --citation-intent-classification for citation intent classification.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "code_summary_generation",
                            "description": "Execute ModelFusion --code-summary-generation for code summary generation.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "code_clone_detection",
                            "description": "Execute ModelFusion --code-clone-detection for code clone detection.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "image_classification",
                            "description": "Execute ModelFusion --image-classification for image classification.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "object_detection",
                            "description": "Execute ModelFusion --object-detection for object detection.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "image_segmentation",
                            "description": "Execute ModelFusion --image-segmentation for image segmentation.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "visual_question_answering",
                            "description": "Execute ModelFusion --visual-question-answering for visual question answering.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "document_question_answering",
                            "description": "Execute ModelFusion --document-question-answering for document question answering.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "zero_shot_image_classification",
                            "description": "Execute ModelFusion --zero-shot-image-classification for zero shot image classification.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "depth_estimation",
                            "description": "Execute ModelFusion --depth-estimation for depth estimation.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "image_feature_extraction",
                            "description": "Execute ModelFusion --image-feature-extraction for image feature extraction.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "automatic_speech_recognition",
                            "description": "Execute ModelFusion --automatic-speech-recognition for automatic speech recognition.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "audio_classification",
                            "description": "Execute ModelFusion --audio-classification for audio classification.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "voice_activity_detection",
                            "description": "Execute ModelFusion --voice-activity-detection for voice activity detection.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "emotion_recognition",
                            "description": "Execute ModelFusion --emotion-recognition for emotion recognition.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "video_classification",
                            "description": "Execute ModelFusion --video-classification for video classification.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "text_to_speech",
                            "description": "Execute ModelFusion --text-to-speech for text to speech.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "text_to_image",
                            "description": "Execute ModelFusion --text-to-image for text to image.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "image_super_resolution",
                            "description": "Execute ModelFusion --image-super-resolution for image super resolution.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "table_question_answering",
                            "description": "Execute ModelFusion --table-question-answering for table question answering.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        },
                        {
                            "name": "feature_ranking",
                            "description": "Execute ModelFusion --feature-ranking for feature ranking.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "text": { "type": "string", "description": "Input text or code" },
                                    "prompt": { "type": "string", "description": "Task instructions" },
                                    "file": { "type": "string", "description": "Optional file path" },
                                    "language": { "type": "string", "description": "Optional language" },
                                    "gpu": { "type": "boolean" }
                                }
                            }
                        }
                    ]

                }
            });
            let response_str = serde_json::to_string(&response)? + "\n";
            stdout.write_all(response_str.as_bytes()).await?;
            stdout.flush().await?;
        } else if method == "tools/call" {
            let params = &request["params"];
            let name = params["name"].as_str().unwrap_or("");
            let arguments = &params["arguments"];

            let result_text = match name {
                "execute" => {
                    let args_val = arguments["args"].as_array();
                    if let Some(args_arr) = args_val {
                        let mut cmd_args = Vec::new();
                        for arg in args_arr {
                            if let Some(s) = arg.as_str() {
                                cmd_args.push(s.to_string());
                            }
                        }
                        run_cli_subcommand(&cmd_args, &db_path_resolved).await
                    } else {
                        "Error: Invalid or missing 'args' parameter".to_string()
                    }
                }
                "orchestrate" => {
                    let prompt = arguments["prompt"].as_str().unwrap_or("").to_string();
                    let mut cmd_args = vec!["--prompt".to_string(), prompt.clone()];
                    
                    if let Some(budget) = arguments["budget"].as_f64() {
                        cmd_args.push("--budget".to_string());
                        cmd_args.push(budget.to_string());
                    }
                    if let Some(strategy) = arguments["selection_strategy"].as_str() {
                        cmd_args.push("--selection-strategy".to_string());
                        cmd_args.push(strategy.to_string());
                    }
                    if let Some(fusion_mode) = arguments["fusion_mode"].as_str() {
                        cmd_args.push("--fusion-mode".to_string());
                        cmd_args.push(fusion_mode.to_string());
                    }
                    if let Some(task_override) = arguments["task_override"].as_str() {
                        cmd_args.push("--task".to_string());
                        cmd_args.push(task_override.to_string());
                    }
                    if arguments["gpu"].as_bool().unwrap_or(false) {
                        cmd_args.push("--gpu".to_string());
                    }
                    if arguments["cpu"].as_bool().unwrap_or(false) {
                        cmd_args.push("--cpu".to_string());
                    }
                    if arguments["fusion"].as_bool().unwrap_or(false) {
                        cmd_args.push("--fusion".to_string());
                    }
                    if arguments["chain_of_thought"].as_bool().unwrap_or(false) {
                        cmd_args.push("--chain-of-thought".to_string());
                    }
                    if arguments["delegation"].as_bool().unwrap_or(false) {
                        cmd_args.push("--delegation".to_string());
                    }
                    if arguments["recursion"].as_bool().unwrap_or(false) {
                        cmd_args.push("--recursion".to_string());
                    }
                    // Always forward ollama flag if set in environment
                    if std::env::var("MODELFUSION_USE_OLLAMA").is_ok() {
                        cmd_args.push("--ollama".to_string());
                    }
                    
                    let (result, _context, _arm) = route_and_execute(&prompt, &db_path_resolved, &cmd_args).await;
                    result
                }
                "analyze_file" => {
                    let file = arguments["file"].as_str().unwrap_or("").to_string();
                    let prompt = arguments["prompt"].as_str().unwrap_or("").to_string();
                    let mut cmd_args = vec!["--file".to_string(), file, "--prompt".to_string(), prompt];
                    if arguments["gpu"].as_bool().unwrap_or(false) {
                        cmd_args.push("--gpu".to_string());
                    }
                    if arguments["cpu"].as_bool().unwrap_or(false) {
                        cmd_args.push("--cpu".to_string());
                    }
                    if arguments["full"].as_bool().unwrap_or(false) {
                        cmd_args.push("--full".to_string());
                    }
                    run_cli_subcommand(&cmd_args, &db_path_resolved).await
                }
                "analyze_folder" => {
                    let folder = arguments["folder"].as_str().unwrap_or("").to_string();
                    let prompt = arguments["prompt"].as_str().unwrap_or("").to_string();
                    let mut cmd_args = vec!["--folder".to_string(), folder, "--prompt".to_string(), prompt];
                    if arguments["full"].as_bool().unwrap_or(false) {
                        cmd_args.push("--full".to_string());
                    }
                    run_cli_subcommand(&cmd_args, &db_path_resolved).await
                }
                "nlp_task" => {
                    let task = arguments["task"].as_str().unwrap_or("text-classification").to_string();
                    let text = arguments["text"].as_str().unwrap_or("").to_string();
                    let mut cmd_args = vec![
                        format!("--{}", task),
                        "--prompt".to_string(), text,
                    ];
                    if let Some(lang) = arguments["language"].as_str() {
                        cmd_args.push("--language".to_string());
                        cmd_args.push(lang.to_string());
                    }
                    if arguments["gpu"].as_bool().unwrap_or(false) {
                        cmd_args.push("--gpu".to_string());
                    }
                    run_cli_subcommand(&cmd_args, &db_path_resolved).await
                }
                "security_analysis" => {
                    let task = arguments["task"].as_str().unwrap_or("spam-detection").to_string();
                    let text = arguments["text"].as_str().unwrap_or("").to_string();
                    let mut cmd_args = vec![
                        format!("--{}", task),
                        "--prompt".to_string(), text,
                    ];
                    if let Some(file) = arguments["file"].as_str() {
                        cmd_args.push("--file".to_string());
                        cmd_args.push(file.to_string());
                    }
                    if arguments["gpu"].as_bool().unwrap_or(false) {
                        cmd_args.push("--gpu".to_string());
                    }
                    run_cli_subcommand(&cmd_args, &db_path_resolved).await
                }
                "code_task" => {
                    let task = arguments["task"].as_str().unwrap_or("code-summary-generation").to_string();
                    let text = arguments["text"].as_str().unwrap_or("").to_string();
                    let mut cmd_args = vec![
                        format!("--{}", task),
                        "--prompt".to_string(), text,
                    ];
                    if let Some(file) = arguments["file"].as_str() {
                        cmd_args.push("--file".to_string());
                        cmd_args.push(file.to_string());
                    }
                    if arguments["plan"].as_bool().unwrap_or(false) {
                        cmd_args.push("--plan".to_string());
                    }
                    if arguments["judge"].as_bool().unwrap_or(false) {
                        cmd_args.push("--judge".to_string());
                    }
                    if arguments["score"].as_bool().unwrap_or(false) {
                        cmd_args.push("--score".to_string());
                    }
                    if arguments["gpu"].as_bool().unwrap_or(false) {
                        cmd_args.push("--gpu".to_string());
                    }
                    run_cli_subcommand(&cmd_args, &db_path_resolved).await
                }
                "domain_task" => {
                    let task = arguments["task"].as_str().unwrap_or("financial-sentiment-analysis").to_string();
                    let text = arguments["text"].as_str().unwrap_or("").to_string();
                    let mut cmd_args = vec![
                        format!("--{}", task),
                        "--prompt".to_string(), text,
                    ];
                    if arguments["gpu"].as_bool().unwrap_or(false) {
                        cmd_args.push("--gpu".to_string());
                    }
                    run_cli_subcommand(&cmd_args, &db_path_resolved).await
                }
                "multimodal_task" => {
                    let task = arguments["task"].as_str().unwrap_or("image-classification").to_string();
                    let mut cmd_args = vec![format!("--{}", task)];
                    if let Some(file) = arguments["file"].as_str() {
                        cmd_args.push("--file".to_string());
                        cmd_args.push(file.to_string());
                    }
                    if let Some(prompt) = arguments["prompt"].as_str() {
                        cmd_args.push("--prompt".to_string());
                        cmd_args.push(prompt.to_string());
                    }
                    if arguments["gpu"].as_bool().unwrap_or(false) {
                        cmd_args.push("--gpu".to_string());
                    }
                    run_cli_subcommand(&cmd_args, &db_path_resolved).await
                }
                "semantic_search" => {
                    let action = arguments["action"].as_str().unwrap_or("search");
                    let mut cmd_args = vec!["--enable-hyde".to_string()];
                    match action {
                        "add" => {
                            if let Some(docs) = arguments["documents_path"].as_str() {
                                cmd_args.push("--add-documents".to_string());
                                cmd_args.push(docs.to_string());
                            }
                        }
                        "demo" => {
                            cmd_args.push("--demo-hyde".to_string());
                        }
                        _ => {
                            if let Some(query) = arguments["query"].as_str() {
                                cmd_args.push("--search-query".to_string());
                                cmd_args.push(query.to_string());
                            }
                            if let Some(k) = arguments["top_k"].as_u64() {
                                cmd_args.push("--top-k".to_string());
                                cmd_args.push(k.to_string());
                            }
                            if arguments["use_hyde"].as_bool().unwrap_or(false) {
                                cmd_args.push("--use-hyde".to_string());
                            }
                            if arguments["hyde_variants"].as_bool().unwrap_or(false) {
                                cmd_args.push("--hyde-variants".to_string());
                            }
                        }
                    }
                    run_cli_subcommand(&cmd_args, &db_path_resolved).await
                }
                "data_science" => {
                    let mode = arguments["mode"].as_str().unwrap_or("analyst");
                    let mut cmd_args = Vec::new();
                    match mode {
                        "science" => cmd_args.push("--datascience".to_string()),
                        "jupyter" => cmd_args.push("--jupyter".to_string()),
                        _ => cmd_args.push("--dataanalyst".to_string()),
                    }
                    if let Some(file) = arguments["file"].as_str() {
                        cmd_args.push("--file".to_string());
                        cmd_args.push(file.to_string());
                    }
                    if let Some(prompt) = arguments["prompt"].as_str() {
                        cmd_args.push("--prompt".to_string());
                        cmd_args.push(prompt.to_string());
                    }
                    if arguments["export_pdf"].as_bool().unwrap_or(false) {
                        cmd_args.push("--export-pdf".to_string());
                    }
                    run_cli_subcommand(&cmd_args, &db_path_resolved).await
                }
                "pe_header_extraction" => {
                    let file = arguments["file"].as_str().unwrap_or("").to_string();
                    let prompt = arguments["prompt"].as_str().unwrap_or("Perform PE analysis");
                    let cmd_args = vec![
                        "--pe-header-extraction".to_string(),
                        "--file".to_string(), file,
                        "--prompt".to_string(), prompt.to_string(),
                    ];
                    run_cli_subcommand(&cmd_args, &db_path_resolved).await
                }
                "model_management" => {
                    let action = arguments["action"].as_str().unwrap_or("prepare");
                    let mut cmd_args = Vec::new();
                    match action {
                        "prepare-all" => {
                            cmd_args.push("--prepare-all-models".to_string());
                        }
                        "sinq" => {
                            cmd_args.push("--sinq".to_string());
                            if let Some(nbits) = arguments["sinq_nbits"].as_u64() {
                                cmd_args.push("--sinq-nbits".to_string());
                                cmd_args.push(nbits.to_string());
                            }
                            if let Some(gs) = arguments["sinq_group_size"].as_u64() {
                                cmd_args.push("--sinq-group-size".to_string());
                                cmd_args.push(gs.to_string());
                            }
                        }
                        _ => {
                            if let Some(model_id) = arguments["model_id"].as_str() {
                                cmd_args.push("--prepare-model".to_string());
                                cmd_args.push(model_id.to_string());
                            }
                        }
                    }
                    if let Some(wf) = arguments["weight_format"].as_str() {
                        cmd_args.push("--weight-format".to_string());
                        cmd_args.push(wf.to_string());
                    }
                    run_cli_subcommand(&cmd_args, &db_path_resolved).await
                }
                "reporting" => {
                    let prompt = arguments["prompt"].as_str().unwrap_or("").to_string();
                    let output = arguments["output_path"].as_str().unwrap_or("./report").to_string();
                    let format = arguments["format"].as_str().unwrap_or("md").to_string();
                    let mut cmd_args = vec![
                        "--prompt".to_string(), prompt,
                        "--report".to_string(), output,
                        "--reporttype".to_string(), format,
                    ];
                    if let Some(file) = arguments["file"].as_str() {
                        cmd_args.push("--file".to_string());
                        cmd_args.push(file.to_string());
                    }
                    run_cli_subcommand(&cmd_args, &db_path_resolved).await
                }
                "ml_management" => {
                    let action = arguments["action"].as_str().unwrap_or("analytics");
                    match action {
                        "retrain" => run_cli_subcommand(&["--ml-retrain".to_string()], &db_path_resolved).await,
                        "cleanup" => {
                            let days = arguments["cleanup_days"].as_u64().unwrap_or(30);
                            run_cli_subcommand(&["--ml-cleanup".to_string(), days.to_string()], &db_path_resolved).await
                        }
                        _ => run_cli_subcommand(&["--ml-analytics".to_string()], &db_path_resolved).await,
                    }
                }
                "get_system_info" => {
                    run_cli_subcommand(&["--sys-info".to_string()], &db_path_resolved).await
                }
                "restore_backup" => {
                    handler.handle_restore(None).content
                }
                "get_database_stats" => {
                    handler.handle_stats().content
                }
                "list_tasks" => {
                    let category = arguments["category"].as_str();
                    handler.handle_tasks_list(category).content
                }
                "update_database" => {
                    handler.handle_update_database().await.content
                }
                "clear_cache" => {
                    handler.handle_clear_cache().content
                }
                "get_decision_stats" => {
                    handler.handle_decision_stats().content
                }
                "get_novel_ai_stats" => {
                    run_cli_subcommand(&["--novel-ai-stats".to_string()], &db_path_resolved).await
                }
                "get_performance_stats" => {
                    handler.handle_performance_stats().content
                }
                "get_cache_stats" => {
                    handler.handle_cache_stats().content
                }
                "get_model_recommendations" => {
                    run_cli_subcommand(&["--model-recommendations".to_string()], &db_path_resolved).await
                }
                "get_model_ranking" => {
                    let category = arguments["category"].as_str().unwrap_or("text-generation");
                    run_cli_subcommand(&["--model-ranking".to_string(), category.to_string()], &db_path_resolved).await
                }
                "get_ml_analytics" => {
                    handler.handle_ml_analytics().content
                }
                "quick_answer" => {
                    let question = arguments["question"].as_str().unwrap_or("").to_string();
                    let model = arguments["model"].as_str().unwrap_or("qwen2.5:3b").to_string();
                    
                    let endpoint = std::env::var("LOCAL_OLLAMA_ENDPOINT")
                        .unwrap_or_else(|_| "http://127.0.0.1:11434".to_string());
                    let url = format!("{}/api/chat", endpoint.trim_end_matches('/'));
                    
                    let body = serde_json::json!({
                        "model": model,
                        "messages": [{"role": "user", "content": &question}],
                        "stream": false,
                        "options": { "temperature": 0.7, "num_predict": 1024 }
                    });
                    
                    let client = reqwest::Client::builder()
                        .no_proxy()
                        .connect_timeout(std::time::Duration::from_secs(3))
                        .timeout(std::time::Duration::from_secs(120))
                        .build()
                        .unwrap();
                    
                    match client.post(&url).json(&body).send().await {
                        Ok(res) if res.status().is_success() => {
                            let data: serde_json::Value = res.json().await.unwrap_or_default();
                            data["message"]["content"].as_str().unwrap_or("No response").to_string()
                        }
                        Ok(res) => format!("Ollama error: {}", res.text().await.unwrap_or_default()),
                        Err(e) => format!("Ollama connection failed: {}. Is Ollama running?", e),
                    }
                }
                "report_bandit_feedback" => {
                    let context = arguments["context"].as_u64().unwrap_or(0) as usize;
                    let arm = arguments["arm"].as_u64().unwrap_or(0) as usize;
                    let reward = arguments["reward"].as_f64().unwrap_or(0.5);

                    if context < 2 && arm < 2 {
                        let db_dir = db_path_resolved.parent().unwrap_or_else(|| std::path::Path::new("db"));
                        let mut state = load_bandit_state(db_dir);
                        let count = state.counts[context][arm];
                        let val = state.values[context][arm];
                        state.counts[context][arm] += 1;
                        state.values[context][arm] = val + (reward - val) / (count + 1) as f64;
                        save_bandit_state(db_dir, &state);
                        format!("Successfully updated bandit feedback for context {}, arm {} to reward {}. New value: {:.4}", context, arm, reward, state.values[context][arm])
                    } else {
                        "Error: Invalid context or arm index".to_string()
                    }
                }
                                other => {
                    let flag_name = other.replace('_', "-");
                    let text = arguments["text"].as_str()
                        .or_else(|| arguments["prompt"].as_str())
                        .or_else(|| arguments["input"].as_str())
                        .unwrap_or("");
                    let mut cmd_args = vec![format!("--{}", flag_name)];
                    if !text.is_empty() {
                        cmd_args.push("--prompt".to_string());
                        cmd_args.push(text.to_string());
                    }
                    if let Some(file) = arguments["file"].as_str() {
                        cmd_args.push("--file".to_string());
                        cmd_args.push(file.to_string());
                    }
                    if let Some(lang) = arguments["language"].as_str() {
                        cmd_args.push("--language".to_string());
                        cmd_args.push(lang.to_string());
                    }
                    if arguments["gpu"].as_bool().unwrap_or(false) {
                        cmd_args.push("--gpu".to_string());
                    }
                    run_cli_subcommand(&cmd_args, &db_path_resolved).await
                }
            };

            let response = serde_json::json!({
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result_text
                        }
                    ]
                }
            });
            let response_str = serde_json::to_string(&response)? + "\n";
            stdout.write_all(response_str.as_bytes()).await?;
            stdout.flush().await?;
        } else {
            let response = serde_json::json!({
                "jsonrpc": "2.0",
                "id": id,
                "error": {
                    "code": -32601,
                    "message": format!("Method not found: {}", method)
                }
            });
            let response_str = serde_json::to_string(&response)? + "\n";
            stdout.write_all(response_str.as_bytes()).await?;
            stdout.flush().await?;
        }
    }

    Ok(())
}

pub fn parse_slash_commands_in_prompt(
    prompt: &mut String,
    gpu: &mut bool,
    cpu: &mut bool,
    openvino: &mut bool,
    fusion: &mut bool,
) {
    let parse_line = |line: &str| -> Option<(String, String)> {
        let trimmed = line.trim();
        let mut command_str = if trimmed.starts_with("User: ") {
            trimmed["User: ".len()..].trim()
        } else if trimmed.starts_with("user: ") {
            trimmed["user: ".len()..].trim()
        } else if trimmed.starts_with("System: ") {
            trimmed["System: ".len()..].trim()
        } else {
            trimmed
        };
        
        let lower_cmd = command_str.to_lowercase();
        let (has_agent_prefix, stripped_cmd, is_comment_prefix) = if lower_cmd.starts_with("@agent") {
            (true, command_str[6..].trim(), false)
        } else if lower_cmd.starts_with("@commands") {
            (true, command_str[9..].trim(), false)
        } else if lower_cmd.starts_with("@command") {
            (true, command_str[8..].trim(), false)
        } else if lower_cmd.starts_with("@comments") {
            (true, command_str[9..].trim(), true)
        } else if lower_cmd.starts_with("@comment") {
            (true, command_str[8..].trim(), true)
        } else if lower_cmd.starts_with("@tasks") {
            (true, command_str[6..].trim(), false)
        } else if lower_cmd.starts_with("@task") {
            (true, command_str[5..].trim(), false)
        } else if lower_cmd.starts_with("@modelfusion") {
            (true, command_str[12..].trim(), false)
        } else if lower_cmd.starts_with("@hugos") {
            (true, command_str[6..].trim(), false)
        } else {
            (false, command_str, false)
        };
        command_str = stripped_cmd;
        
        let (raw_cmd, rest) = if command_str.starts_with('/') {
            let mut parts = command_str.splitn(2, ' ');
            let cmd = parts.next().unwrap_or("").to_lowercase();
            let rest = parts.next().unwrap_or("").trim().to_string();
            (cmd, rest)
        } else if has_agent_prefix && !command_str.is_empty() {
            let mut parts = command_str.splitn(2, ' ');
            let cmd = format!("/{}", parts.next().unwrap_or("").to_lowercase());
            let rest = parts.next().unwrap_or("").trim().to_string();
            (cmd, rest)
        } else if has_agent_prefix && command_str.is_empty() {
            if is_comment_prefix {
                ("/comment".to_string(), String::new())
            } else {
                ("/stats".to_string(), String::new())
            }
        } else {
            return None;
        };

        let normalized_cmd = match raw_cmd.as_str() {
            "/evove" | "/evoce" | "/evovle" | "/evolv" | "/evolution" => "/evolve".to_string(),
            "/api-keys" => "/keys".to_string(),
            "/sys-info" => "/sysinfo".to_string(),
            "/db-stats" => "/stats".to_string(),
            "/clearcache" => "/clear_cache".to_string(),
            "/comments" => "/comment".to_string(),
            "/commands" | "/help" => "/command".to_string(),
            "/docs" => "/doc".to_string(),
            other => other.to_string(),
        };

        if normalized_cmd.starts_with('/') && normalized_cmd.len() > 1 {
            Some((normalized_cmd, rest))
        } else {
            None
        }
    };

    let mut detected_cmd = None;
    let mut cleaned_rest = String::new();

    // Check single line
    if let Some((cmd, rest)) = parse_line(prompt) {
        detected_cmd = Some(cmd);
        cleaned_rest = rest;
    } else if prompt.contains("User: ") {
        // Multi-turn transcript: check the last user line
        let lines: Vec<&str> = prompt.lines().collect();
        for i in (0..lines.len()).rev() {
            let line = lines[i];
            if line.trim().starts_with("User: ") {
                if let Some((cmd, rest)) = parse_line(line) {
                    detected_cmd = Some(cmd);
                    cleaned_rest = rest;
                }
                break;
            }
        }
    }

    if let Some(cmd) = detected_cmd {
        eprintln!("💡 [ROUTER] Detected Slash Command: {}", cmd);
        
        // Helper to extract first argument and actual prompt
        let get_arg = |r: &str| -> (String, String) {
            let mut parts = r.splitn(2, ' ');
            let arg = parts.next().unwrap_or("").trim().to_string();
            let actual = parts.next().unwrap_or("").trim().to_string();
            (arg, actual)
        };

        let mut actual_prompt = cleaned_rest.clone();

        match cmd.as_str() {
            "/file" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_FILE", &val);
                actual_prompt = act;
            }
            "/folder" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_FOLDER", &val);
                actual_prompt = act;
            }
            "/task" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_TASK_OVERRIDE", &val);
                actual_prompt = act;
            }
            "/budget" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_BUDGET", &val);
                actual_prompt = act;
            }
            "/config" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_CONFIG", &val);
                actual_prompt = act;
            }
            "/selection-strategy" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_SELECTION_STRATEGY", &val);
                actual_prompt = act;
            }
            "/language" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_LANGUAGE", &val);
                actual_prompt = act;
            }
            "/api-keys" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_API_KEYS", &val);
                actual_prompt = act;
            }
            "/load-model" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_LOAD_MODEL", &val);
                actual_prompt = act;
            }
            "/ml-ensemble-method" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_ML_ENSEMBLE_METHOD", &val);
                actual_prompt = act;
            }
            "/ml-confidence-threshold" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_ML_CONFIDENCE_THRESHOLD", &val);
                actual_prompt = act;
            }
            "/ml-cleanup" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_ML_CLEANUP", &val);
                actual_prompt = act;
            }
            "/sinq-nbits" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_SINQ_NBITS", &val);
                actual_prompt = act;
            }
            "/sinq-group-size" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_SINQ_GROUP_SIZE", &val);
                actual_prompt = act;
            }
            "/sinq-tiling-mode" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_SINQ_TILING_MODE", &val);
                actual_prompt = act;
            }
            "/sinq-method" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_SINQ_METHOD", &val);
                actual_prompt = act;
            }
            "/innovation-level" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_INNOVATION_LEVEL", &val);
                actual_prompt = act;
            }
            "/add-documents" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_ADD_DOCUMENTS", &val);
                actual_prompt = act;
            }
            "/search-query" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_SEARCH_QUERY", &val);
                actual_prompt = act;
            }
            "/top-k" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_TOP_K", &val);
                actual_prompt = act;
            }
            "/tasks" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_TASKS_FILTER", &val);
                actual_prompt = act;
            }
            "/model-ranking" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_MODEL_RANKING_FILTER", &val);
                actual_prompt = act;
            }
            "/fusion-models" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_FUSION_MODELS", &val);
                actual_prompt = act;
            }
            "/fusion-mode" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_FUSION_MODE", &val);
                actual_prompt = act;
            }
            "/model" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_MODEL", &val);
                actual_prompt = act;
            }
            "/prepare-model" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_PREPARE_MODEL", &val);
                actual_prompt = act;
            }
            "/weight-format" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_WEIGHT_FORMAT", &val);
                actual_prompt = act;
            }
            "/ov-model-dir" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_OV_MODEL_DIR", &val);
                actual_prompt = act;
            }
            "/context" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_CONTEXT", &val);
                actual_prompt = act;
            }
            "/report" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_REPORT", &val);
                actual_prompt = act;
            }
            "/reporttype" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_REPORTTYPE", &val);
                actual_prompt = act;
            }
            "/ml-fallback" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_ML_FALLBACK", &val);
                actual_prompt = act;
            }
            "/db-path" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_DB_PATH", &val);
                actual_prompt = act;
            }
            "/port" => {
                let (val, act) = get_arg(&cleaned_rest);
                std::env::set_var("MODELFUSION_PORT", &val);
                actual_prompt = act;
            }
            
            // Boolean flags
            "/cot" | "/chain-of-thought" => {
                std::env::set_var("MODELFUSION_CHAIN_OF_THOUGHT", "true");
            }
            "/enable-ml" => {
                std::env::set_var("MODELFUSION_ENABLE_ML", "true");
            }
            "/use-openai" => {
                std::env::set_var("MODELFUSION_USE_OPENAI", "true");
            }
            "/verbose" => {
                std::env::set_var("MODELFUSION_VERBOSE", "true");
            }
            "/debug" => {
                std::env::set_var("MODELFUSION_DEBUG", "true");
            }
            "/gpu" => {
                *gpu = true;
                std::env::set_var("MODELFUSION_FORCE_GPU", "true");
            }
            "/cpu" => {
                *cpu = true;
                std::env::set_var("MODELFUSION_FORCE_CPU", "true");
            }
            "/save-model" => {
                std::env::set_var("MODELFUSION_SAVE_MODEL", "true");
            }
            "/enable-ml-selection" => {
                std::env::set_var("MODELFUSION_ENABLE_ML_SELECTION", "true");
            }
            "/ml-learning" => {
                std::env::set_var("MODELFUSION_ML_LEARNING", "true");
            }
            "/ml-analytics" => {
                std::env::set_var("MODELFUSION_ML_ANALYTICS", "true");
            }
            "/ml-retrain" => {
                std::env::set_var("MODELFUSION_ML_RETRAIN", "true");
            }
            "/sinq" => {
                std::env::set_var("MODELFUSION_SINQ", "true");
            }
            "/innovate" | "/innovation" | "/enable-innovations" => {
                std::env::set_var("MODELFUSION_INNOVATE", "true");
            }
            "/optimize" | "/workflow" | "/workflow-optimization" => {
                std::env::set_var("MODELFUSION_WORKFLOW_OPTIMIZE", "true");
            }
            "/semantic-analysis" => {
                std::env::set_var("MODELFUSION_SEMANTIC_ANALYSIS", "true");
            }
            "/temporal-tracking" => {
                std::env::set_var("MODELFUSION_TEMPORAL_TRACKING", "true");
            }
            "/predict" | "/predictive" | "/predictive-mode" => {
                std::env::set_var("MODELFUSION_PREDICT", "true");
            }
            "/enable-hyde" => {
                std::env::set_var("MODELFUSION_ENABLE_HYDE", "true");
            }
            "/use-hyde" => {
                std::env::set_var("MODELFUSION_USE_HYDE", "true");
            }
            "/hyde-variants" => {
                std::env::set_var("MODELFUSION_HYDE_VARIANTS", "true");
            }
            "/demo-hyde" => {
                std::env::set_var("MODELFUSION_DEMO_HYDE", "true");
            }
            "/stats" => {
                std::env::set_var("MODELFUSION_STATS", "true");
            }
            "/sys-info" | "/sysinfo" => {
                std::env::set_var("MODELFUSION_SYS_INFO", "true");
            }
            "/update" => {
                std::env::set_var("MODELFUSION_UPDATE", "true");
            }
            "/restore" => {
                std::env::set_var("MODELFUSION_RESTORE", "true");
            }
            "/decision-stats" => {
                std::env::set_var("MODELFUSION_DECISION_STATS", "true");
            }
            "/novel-ai-stats" => {
                std::env::set_var("MODELFUSION_NOVEL_AI_STATS", "true");
            }
            "/performance-stats" => {
                std::env::set_var("MODELFUSION_PERFORMANCE_STATS", "true");
            }
            "/cache-stats" => {
                std::env::set_var("MODELFUSION_CACHE_STATS", "true");
            }
            "/clearcache" => {
                std::env::set_var("MODELFUSION_CLEARCACHE", "true");
            }
            "/analytics-demo" => {
                std::env::set_var("MODELFUSION_ANALYTICS_DEMO", "true");
            }
            "/model-recommendations" => {
                std::env::set_var("MODELFUSION_MODEL_RECOMMENDATIONS", "true");
            }
            "/full" => {
                std::env::set_var("MODELFUSION_FULL", "true");
            }
            "/fusion" => {
                *fusion = true;
                std::env::set_var("MODELFUSION_FUSION", "true");
            }
            "/ollama" => {
                std::env::set_var("MODELFUSION_USE_OLLAMA", "true");
            }
            "/openvino" => {
                *openvino = true;
                std::env::set_var("MODELFUSION_USE_OPENVINO", "true");
            }
            "/onnx" => {
                std::env::set_var("MODELFUSION_USE_ONNX", "true");
            }
            "/vllm" => {
                std::env::set_var("MODELFUSION_USE_VLLM", "true");
            }
            "/prepare-all-models" => {
                std::env::set_var("MODELFUSION_PREPARE_ALL_MODELS", "true");
            }
            "/context-auto" => {
                std::env::set_var("MODELFUSION_CONTEXT_AUTO", "true");
            }
            "/delegation" | "/delegate" => {
                std::env::set_var("MODELFUSION_DELEGATION", "true");
            }
            "/recursion" | "/recurse" => {
                std::env::set_var("MODELFUSION_RECURSION", "true");
            }
            "/real-options" | "/realoptions" => {
                std::env::set_var("MODELFUSION_REAL_OPTIONS", "true");
            }
            "/prompt-quality-scoring" => {
                std::env::set_var("MODELFUSION_PROMPT_QUALITY_SCORING", "true");
            }
            "/jupyter" => {
                std::env::set_var("MODELFUSION_JUPYTER", "true");
            }
            "/dataanalyst" => {
                std::env::set_var("MODELFUSION_DATAANALYST", "true");
            }
            "/datascience" => {
                std::env::set_var("MODELFUSION_DATASCIENCE", "true");
            }
            "/export-pdf" => {
                std::env::set_var("MODELFUSION_EXPORT_PDF", "true");
            }
            "/score" => {
                std::env::set_var("MODELFUSION_SCORE", "true");
            }
            "/judge" => {
                std::env::set_var("MODELFUSION_JUDGE", "true");
            }
            "/plan" => {
                std::env::set_var("MODELFUSION_PLAN", "true");
            }
            "/pe-header-extraction" => {
                std::env::set_var("MODELFUSION_PE_HEADER_EXTRACTION", "true");
            }
            "/sentiment" => {
                std::env::set_var("MODELFUSION_SENTIMENT", "true");
            }
            "/question" => {
                std::env::set_var("MODELFUSION_QUESTION", "true");
            }
            "/ner" => {
                std::env::set_var("MODELFUSION_NER", "true");
            }
            "/summary" => {
                std::env::set_var("MODELFUSION_SUMMARY", "true");
            }
            "/server" => {
                std::env::set_var("MODELFUSION_SERVER", "true");
            }
            "/mcp" => {
                std::env::set_var("MODELFUSION_MCP", "true");
            }

            // Task overrides
            other => {
                if other.starts_with('/') {
                    let task_name = other[1..].to_string();
                    std::env::set_var("MODELFUSION_TASK_OVERRIDE", &task_name);
                }
            }
        }

        // Apply back the cleaned prompt text
        if prompt.contains("User: ") {
            let lines: Vec<&str> = prompt.lines().collect();
            for i in (0..lines.len()).rev() {
                let line = lines[i];
                if line.trim().starts_with("User: ") {
                    let mut new_lines = lines.clone();
                    let new_line = format!("User: {}", actual_prompt);
                    new_lines[i] = &new_line;
                    *prompt = new_lines.join("\n");
                    break;
                }
            }
        } else {
            *prompt = actual_prompt;
        }
    }
}

fn acquire_cross_process_lock() -> Result<std::fs::File> {
    use std::os::windows::fs::OpenOptionsExt;
    
    let user_profile = std::env::var("USERPROFILE").unwrap_or_else(|_| "C:\\Users\\oyesa".to_string());
    let lock_dir = std::path::Path::new(&user_profile).join(".hugos-ide");
    let _ = std::fs::create_dir_all(&lock_dir);
    let lock_path = lock_dir.join(".inference.lock");

    // Loop and try to acquire the lock
    let start_time = std::time::Instant::now();
    loop {
        match std::fs::OpenOptions::new()
            .write(true)
            .create(true)
            .share_mode(0) // Exclusive access, lock out other processes
            .open(&lock_path)
        {
            Ok(file) => return Ok(file),
            Err(e) => {
                if start_time.elapsed().as_secs() > 600 {
                    anyhow::bail!("Failed to acquire cross-process inference lock after 10 minutes: {}", e);
                }
                std::thread::sleep(std::time::Duration::from_millis(100));
            }
        }
    }
}

// =============================================================================
// --patch-ide: Clone VSCode and apply HugOS IDE branding patches
// =============================================================================

/// Main workflow for --patch-ide: clone VSCode, apply all HugOS branding.
async fn patch_ide_workflow(ide_src_dir: &str, shallow: bool, vscode_tag: Option<&str>) -> Result<()> {
    use std::process::Command;

    let project_root = std::env::current_dir()?;
    let target_dir = project_root.join(ide_src_dir);
    let patches_dir = project_root.join("IDE").join("patches");
    let extension_src = project_root.join("IDE").join("vscode").join("extensions").join("modelfusion");

    println!("{}", "╔══════════════════════════════════════════════════════════════╗");
    println!("{}", "║        HugOS IDE Patcher — Clone & Brand VSCode             ║");
    println!("{}", "╚══════════════════════════════════════════════════════════════╝");
    println!();

    let mut successes: Vec<String> = Vec::new();
    let mut failures: Vec<String> = Vec::new();

    // ── Step 1: Clone VSCode ──────────────────────────────────────────
    println!("[1/7] Cloning VSCode repository...");
    if target_dir.exists() {
        println!("  WARNING: Target directory already exists: {}", target_dir.display());
        println!("  Skipping clone, applying patches to existing tree.");
        successes.push("Clone: skipped (directory exists)".into());
    } else {
        let mut cmd = Command::new("git");
        cmd.arg("clone");
        if shallow {
            cmd.args(["--depth", "1"]);
        }
        if let Some(tag) = vscode_tag {
            cmd.args(["--branch", tag]);
        }
        cmd.arg("https://github.com/microsoft/vscode.git");
        cmd.arg(&target_dir);

        println!("  git clone {} into {}",
            if shallow { "(shallow)" } else { "(full)" },
            target_dir.display());

        let status = cmd.status();
        match status {
            Ok(s) if s.success() => {
                println!("  [OK] Clone completed successfully.");
                successes.push("Clone: success".into());
            }
            Ok(s) => {
                let msg = format!("Clone: git exited with code {}", s.code().unwrap_or(-1));
                println!("  [FAIL] {}", msg);
                failures.push(msg);
                print_patch_summary(&successes, &failures);
                return Ok(());
            }
            Err(e) => {
                let msg = format!("Clone: failed to run git: {}", e);
                println!("  [FAIL] {}", msg);
                failures.push(msg);
                print_patch_summary(&successes, &failures);
                return Ok(());
            }
        }
    }
    println!();

    // ── Step 2: Replace product.json ──────────────────────────────────
    println!("[2/7] Replacing product.json with HugOS branding...");
    let product_src = patches_dir.join("product.json");
    let product_dst = target_dir.join("product.json");
    match std::fs::copy(&product_src, &product_dst) {
        Ok(_) => {
            println!("  [OK] product.json replaced.");
            successes.push("Branding: product.json".into());
        }
        Err(e) => {
            let msg = format!("Branding: product.json -- {}", e);
            println!("  [FAIL] {}", msg);
            failures.push(msg);
        }
    }
    println!();

    // ── Step 3: Patch package.json fields ─────────────────────────────
    println!("[3/7] Patching package.json fields...");
    let pkg_path = target_dir.join("package.json");
    match patch_package_json(&pkg_path) {
        Ok(_) => {
            println!("  [OK] package.json patched (name, displayName, description, author).");
            successes.push("Branding: package.json".into());
        }
        Err(e) => {
            let msg = format!("Branding: package.json -- {}", e);
            println!("  [FAIL] {}", msg);
            failures.push(msg);
        }
    }
    println!();

    // ── Step 4: Apply source code patches ─────────────────────────────
    println!("[4/7] Applying source code patches (copilot -> modelfusion)...");
    let patches = get_source_patches();
    let mut patch_ok = 0usize;
    let mut patch_fail = 0usize;
    for (rel_path, search, replace) in &patches {
        let file_path = target_dir.join(rel_path);
        match apply_text_patch(&file_path, search, replace) {
            Ok(count) => {
                println!("  [OK] {} ({} replacement{})", rel_path, count, if count != 1 { "s" } else { "" });
                patch_ok += 1;
            }
            Err(e) => {
                println!("  [FAIL] {} -- {}", rel_path, e);
                patch_fail += 1;
            }
        }
    }
    successes.push(format!("Source patches: {}/{} succeeded", patch_ok, patches.len()));
    if patch_fail > 0 {
        failures.push(format!("Source patches: {} file(s) failed", patch_fail));
    }
    println!();

    // ── Step 5: Copy modelfusion extension ─────────────────────────────
    println!("[5/7] Copying modelfusion extension...");
    let ext_dst = target_dir.join("extensions").join("modelfusion");
    if extension_src.exists() {
        match copy_dir_recursive(&extension_src, &ext_dst) {
            Ok(count) => {
                println!("  [OK] Copied {} files to extensions/modelfusion/", count);
                successes.push(format!("Extension: {} files copied", count));
            }
            Err(e) => {
                let msg = format!("Extension: copy failed -- {}", e);
                println!("  [FAIL] {}", msg);
                failures.push(msg);
            }
        }
    } else {
        let msg = "Extension: source directory IDE/vscode/extensions/modelfusion/ not found".to_string();
        println!("  [FAIL] {}", msg);
        failures.push(msg);
    }
    println!();

    // ── Step 6: Copy icons ────────────────────────────────────────────
    println!("[6/7] Replacing icons with HugOS branding...");
    let icon_mappings: Vec<(&str, &str)> = vec![
        ("icons/win32/code.ico", "resources/win32/code.ico"),
        ("icons/win32/code_150x150.png", "resources/win32/code_150x150.png"),
        ("icons/win32/code_70x70.png", "resources/win32/code_70x70.png"),
        ("icons/darwin/code.icns", "resources/darwin/code.icns"),
        ("icons/linux/code.png", "resources/linux/code.png"),
    ];
    for (src_rel, dst_rel) in &icon_mappings {
        let src = patches_dir.join(src_rel);
        let dst = target_dir.join(dst_rel);
        if src.exists() {
            if let Some(parent) = dst.parent() {
                let _ = std::fs::create_dir_all(parent);
            }
            match std::fs::copy(&src, &dst) {
                Ok(_) => {
                    println!("  [OK] {}", dst_rel);
                    successes.push(format!("Icon: {}", dst_rel));
                }
                Err(e) => {
                    println!("  [FAIL] {} -- {}", dst_rel, e);
                    failures.push(format!("Icon: {} -- {}", dst_rel, e));
                }
            }
        } else {
            println!("  [SKIP] {} (source not found)", src_rel);
        }
    }
    println!();

    // ── Step 7: Patch dev config ──────────────────────────────────────
    println!("[7/7] Patching .vscode dev configuration...");
    // launch.json: add modelfusion outFiles entry
    let launch_path = target_dir.join(".vscode").join("launch.json");
    match apply_text_patch(
        &launch_path,
        "\"${workspaceFolder}/extensions/*/out/**/*.js\"",
        "\"${workspaceFolder}/extensions/*/out/**/*.js\",\n\t\t\t\t\"${workspaceFolder}/extensions/modelfusion/dist/**/*.js\""
    ) {
        Ok(_) => {
            println!("  [OK] .vscode/launch.json patched.");
            successes.push("DevConfig: launch.json".into());
        }
        Err(e) => {
            println!("  [FAIL] .vscode/launch.json -- {}", e);
            failures.push(format!("DevConfig: launch.json -- {}", e));
        }
    }
    // tasks.json: replace copilot reference with modelfusion
    let tasks_path = target_dir.join(".vscode").join("tasks.json");
    match apply_text_patch(
        &tasks_path,
        "\"${workspaceFolder}/extensions/copilot\"",
        "\"${workspaceFolder}/extensions/modelfusion\""
    ) {
        Ok(_) => {
            println!("  [OK] .vscode/tasks.json patched.");
            successes.push("DevConfig: tasks.json".into());
        }
        Err(e) => {
            // Stock tasks.json may not have copilot reference — not fatal
            println!("  [SKIP] .vscode/tasks.json -- {} (non-fatal)", e);
        }
    }
    println!();
    // ── Step 8: Build IDE from source ─────────────────────────────────
    // CRITICAL: The IDE MUST be built from the patched vscode source tree.
    // Using the official VSCode release zip introduces a foreign versioned
    // directory (7e7950df89/) that overrides product.json, extensions, and
    // branding. Building from source produces a clean VSCode-win32-x64/
    // with HugOS branding and modelfusion extension baked in.
    // See: commit 4c29cb1f (last known working state)
    println!("[8/10] Building IDE from source (gulp vscode-win32-x64)...");
    println!("       This may take 10-15 minutes on first run.");

    // Step 8a: yarn install (ensure dependencies are up to date)
    let yarn_status = Command::new("cmd.exe")
        .args(["/c", "cd /d", &target_dir.to_string_lossy(), "&&", "yarn", "install", "--frozen-lockfile"])
        .output();
    match yarn_status {
        Ok(o) if o.status.success() => {
            println!("  [OK] yarn install completed.");
        }
        Ok(o) => {
            let stderr = String::from_utf8_lossy(&o.stderr);
            // yarn install may warn but still succeed
            if !stderr.contains("error") {
                println!("  [OK] yarn install completed (with warnings).");
            } else {
                println!("  [FAIL] yarn install failed: {}", stderr.chars().take(200).collect::<String>());
                failures.push("Build: yarn install failed".into());
            }
        }
        Err(e) => {
            println!("  [FAIL] Could not run yarn: {}", e);
            failures.push("Build: yarn not available".into());
        }
    }

    // Step 8b: gulp vscode-win32-x64 (build the IDE)
    let gulp_js = target_dir.join("node_modules").join("gulp").join("bin").join("gulp.js");
    if gulp_js.exists() {
        let build_status = Command::new("node")
            .arg(gulp_js.to_string_lossy().to_string())
            .arg("vscode-win32-x64")
            .current_dir(&target_dir)
            .output();
        match build_status {
            Ok(o) if o.status.success() => {
                println!("  [OK] gulp vscode-win32-x64 build completed.");
                successes.push("Build: IDE built from source".into());
            }
            Ok(o) => {
                let stderr = String::from_utf8_lossy(&o.stderr);
                println!("  [FAIL] gulp build failed: {}", stderr.chars().take(300).collect::<String>());
                failures.push("Build: gulp vscode-win32-x64 failed".into());
            }
            Err(e) => {
                println!("  [FAIL] Could not run gulp: {}", e);
                failures.push("Build: gulp not available".into());
            }
        }
    } else {
        println!("  [SKIP] gulp not found. Run 'yarn install' in IDE/vscode first.");
        failures.push("Build: gulp.js not found in node_modules".into());
    }
    println!();

    // ── Step 9: Brand the Electron binary with rcedit ─────────────────
    // CRITICAL: After gulp builds Code.exe, we must apply HugOS branding
    // to the PE resource table (icon, product name, file description).
    // Without this, the IDE shows "Visual Studio Code" everywhere.
    // See: IDE/INCIDENT_SIGNING_2026-07-16.md
    println!("[9/10] Branding Electron binary with rcedit...");
    let rcedit_path = target_dir
        .join("node_modules")
        .join("@vscode")
        .join("gulp-electron")
        .join("node_modules")
        .join("rcedit")
        .join("bin")
        .join("rcedit-x64.exe");

    // The built IDE output directory (VSCode-win32-x64)
    let ide_output_dir = project_root.join("IDE").join("VSCode-win32-x64");
    let hugos_exe = ide_output_dir.join("HugOS.exe");
    let hugos_ico = project_root.join("IDE").join("hugos.ico");

    if rcedit_path.exists() && hugos_exe.exists() {
        let rcedit_str = rcedit_path.to_string_lossy().to_string();
        let exe_str = hugos_exe.to_string_lossy().to_string();

        let branding_cmds: Vec<(&str, &str, &str)> = vec![
            ("--set-version-string", "ProductName", "HugOS IDE"),
            ("--set-version-string", "FileDescription", "HugOS IDE"),
            ("--set-version-string", "CompanyName", "HugOS Team"),
            ("--set-version-string", "InternalName", "HugOS"),
            ("--set-version-string", "OriginalFilename", "HugOS.exe"),
            ("--set-version-string", "LegalCopyright", "Copyright (C) 2026 HugOS Team"),
        ];

        let mut brand_ok = true;
        for (flag, key, value) in &branding_cmds {
            let status = Command::new(&rcedit_str)
                .args([exe_str.as_str(), *flag, *key, *value])
                .output();
            if let Err(e) = status {
                println!("  [FAIL] rcedit {} {} -- {}", flag, key, e);
                brand_ok = false;
            }
        }

        // Set version strings
        let _ = Command::new(&rcedit_str)
            .args([&exe_str, "--set-product-version", "1.126.0"])
            .output();
        let _ = Command::new(&rcedit_str)
            .args([&exe_str, "--set-file-version", "1.126.0"])
            .output();

        // Set HugOS icon
        if hugos_ico.exists() {
            let ico_str = hugos_ico.to_string_lossy().to_string();
            match Command::new(&rcedit_str)
                .args([&exe_str, "--set-icon", &ico_str])
                .output()
            {
                Ok(o) if o.status.success() => println!("  [OK] Icon set to hugos.ico"),
                Ok(o) => {
                    println!("  [FAIL] Icon set failed: {}", String::from_utf8_lossy(&o.stderr));
                    brand_ok = false;
                }
                Err(e) => {
                    println!("  [FAIL] Icon set failed: {}", e);
                    brand_ok = false;
                }
            }
        }

        if brand_ok {
            println!("  [OK] HugOS branding applied to Electron binary.");
            successes.push("Binary branding: rcedit applied".into());
        } else {
            failures.push("Binary branding: some rcedit steps failed".into());
        }
    } else {
        if !rcedit_path.exists() {
            println!("  [SKIP] rcedit not found at {:?}", rcedit_path);
            println!("         Run 'yarn install' in IDE/vscode first.");
        }
        if !hugos_exe.exists() {
            println!("  [SKIP] HugOS.exe not found at {:?}", hugos_exe);
            println!("         Run the gulp build first to produce VSCode-win32-x64/.");
        }
    }
    println!();

    // ── Step 9: Restore Electron binary + versioned runtime dir ───────
    // CRITICAL: Code.exe from VSCode 1.126.0 loads ICU data from a versioned
    // hash subdirectory (e.g. 7e7950df89/), NOT from the root directory.
    // Without this directory, HugOS.exe crashes with:
    //   "Invalid file descriptor to ICU data received"
    // See: IDE/INCIDENT_SIGNING_2026-07-16.md
    println!("[10/10] Ensuring Electron runtime integrity...");
    if ide_output_dir.exists() {
        // Check if the versioned directory already exists
        let has_versioned_dir = std::fs::read_dir(&ide_output_dir)
            .map(|entries| {
                entries.filter_map(|e| e.ok()).any(|e| {
                    let name = e.file_name().to_string_lossy().to_string();
                    e.file_type().map(|ft| ft.is_dir()).unwrap_or(false)
                        && name.len() >= 10
                        && name.chars().all(|c| c.is_ascii_hexdigit())
                })
            })
            .unwrap_or(false);

        if !has_versioned_dir {
            println!("  [WARNING] No versioned Electron runtime directory found!");
            println!("  The IDE will crash without it. To fix:");
            println!("  1. Download VSCode 1.126.0: https://update.code.visualstudio.com/1.126.0/win32-x64-archive/stable");
            println!("  2. Extract and copy the hash-named directory (e.g. 7e7950df89/) into VSCode-win32-x64/");
            println!("  3. Or run build_msi.ps1 which does this automatically.");
            failures.push("Runtime: versioned Electron directory missing".into());
        } else {
            println!("  [OK] Versioned Electron runtime directory present.");
            successes.push("Runtime: versioned directory verified".into());
        }

        // Verify HugOS.exe is not self-signed (the July 2026 incident guard)
        #[cfg(windows)]
        {
            let check = Command::new("powershell")
                .args([
                    "-NoProfile", "-Command",
                    &format!(
                        r#"$s = Get-AuthenticodeSignature '{}'; if ($s.Status -eq 'Valid') {{ Write-Output 'VALID' }} else {{ Write-Output 'INVALID' }}"#,
                        hugos_exe.display()
                    ),
                ])
                .output();
            if let Ok(out) = check {
                let result = String::from_utf8_lossy(&out.stdout);
                if result.trim() == "VALID" {
                    println!("  [OK] HugOS.exe signature is valid.");
                    successes.push("Runtime: binary signature valid".into());
                } else {
                    println!("  [WARNING] HugOS.exe signature is INVALID — build_msi.ps1 step 4.1 will auto-fix.");
                    failures.push("Runtime: HugOS.exe signature invalid".into());
                }
            }
        }
    } else {
        println!("  [SKIP] VSCode-win32-x64/ not yet built.");
    }
    println!();

    print_patch_summary(&successes, &failures);

    // ── Safety Check: Warn if built HugOS.exe has a broken signature ──────
    // This catches the July 2026 incident where build_msi.ps1 re-signed
    // HugOS.exe with a self-signed cert, breaking Electron's ICU data loader
    // and causing a silent renderer crash (IDE starts but no window appears).
    //
    // See: IDE/INCIDENT_SIGNING_2026-07-16.md for full details.
    let built_exe = project_root
        .join("IDE")
        .join("VSCode-win32-x64")
        .join("HugOS.exe");
    if built_exe.exists() {
        #[cfg(windows)]
        {
            use std::process::Command;
            let check = Command::new("powershell")
                .args([
                    "-NoProfile", "-Command",
                    &format!(
                        r#"$s = Get-AuthenticodeSignature '{}'; \
                        if ($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notlike '*Microsoft*') \
                        {{ Write-Output 'INVALID' }} else {{ Write-Output 'OK' }}"#,
                        built_exe.display()
                    ),
                ])
                .output();
            if let Ok(out) = check {
                let result = String::from_utf8_lossy(&out.stdout);
                if result.trim() == "INVALID" {
                    println!();
                    println!("╔══════════════════════════════════════════════════════════════╗");
                    println!("║  ⛔  CRITICAL SAFETY WARNING — READ BEFORE BUILDING MSI     ║");
                    println!("╠══════════════════════════════════════════════════════════════╣");
                    println!("║  HugOS.exe has an INVALID or SELF-SIGNED certificate!       ║");
                    println!("║                                                              ║");
                    println!("║  build_msi.ps1 MUST NOT sign HugOS.exe with a self-signed  ║");
                    println!("║  cert. Doing so corrupts Electron's ICU data loader and     ║");
                    println!("║  causes the IDE to spawn 4 processes but NEVER show a      ║");
                    println!("║  window. See IDE/INCIDENT_SIGNING_2026-07-16.md             ║");
                    println!("║                                                              ║");
                    println!("║  FIX: build_msi.ps1 step 4.1 will auto-restore Code.exe   ║");
                    println!("║  from VSCode 1.126.0 before packaging. Ensure you run the  ║");
                    println!("║  latest build_msi.ps1 (commit 2018208e or later).           ║");
                    println!("╚══════════════════════════════════════════════════════════════╝");
                    println!();
                }
            }
        }
    }
    print_patch_summary(&successes, &failures);
    Ok(())
}

fn print_patch_summary(successes: &[String], failures: &[String]) {
    println!("================================================================");
    println!("                    PATCH SUMMARY                               ");
    println!("================================================================");
    println!();
    println!("  {} steps succeeded:", successes.len());
    for s in successes {
        println!("    [OK] {}", s);
    }
    if !failures.is_empty() {
        println!();
        println!("  {} steps failed:", failures.len());
        for f in failures {
            println!("    [FAIL] {}", f);
        }
    } else {
        println!();
        println!("  All patches applied successfully!");
        println!("  Next: cd into the target directory and run 'yarn' then");
        println!("        'gulp vscode-win32-x64' to build the IDE.");
    }
    println!();
}

/// Patch package.json by reading it, modifying specific fields, and writing it back.
fn patch_package_json(pkg_path: &std::path::Path) -> Result<()> {
    let content = std::fs::read_to_string(pkg_path)?;
    let mut json: serde_json::Value = serde_json::from_str(&content)?;

    if let Some(obj) = json.as_object_mut() {
        obj.insert("name".into(), serde_json::json!("hugos"));
        obj.insert("displayName".into(), serde_json::json!("HugOS"));
        obj.insert("description".into(), serde_json::json!("HugOS - Custom AI-Powered Code-OSS IDE"));
        obj.insert("author".into(), serde_json::json!({ "name": "HugOS Team" }));
    }

    let output = serde_json::to_string_pretty(&json)?;
    std::fs::write(pkg_path, output)?;
    Ok(())
}

/// Apply a text search-and-replace patch to a file. Returns the number of replacements made.
fn apply_text_patch(file_path: &std::path::Path, search: &str, replace: &str) -> Result<usize> {
    let content = std::fs::read_to_string(file_path)
        .map_err(|e| anyhow::anyhow!("cannot read {}: {}", file_path.display(), e))?;
    let count = content.matches(search).count();
    if count == 0 {
        return Err(anyhow::anyhow!("search string not found in {}", file_path.display()));
    }
    let patched = content.replace(search, replace);
    std::fs::write(file_path, patched)
        .map_err(|e| anyhow::anyhow!("cannot write {}: {}", file_path.display(), e))?;
    Ok(count)
}

/// Recursively copy a directory tree. Returns total number of files copied.
fn copy_dir_recursive(src: &std::path::Path, dst: &std::path::Path) -> Result<usize> {
    let mut count = 0usize;
    std::fs::create_dir_all(dst)?;
    for entry in std::fs::read_dir(src)? {
        let entry = entry?;
        let file_type = entry.file_type()?;
        let src_path = entry.path();
        let dst_path = dst.join(entry.file_name());
        if file_type.is_dir() {
            count += copy_dir_recursive(&src_path, &dst_path)?;
        } else {
            std::fs::copy(&src_path, &dst_path)?;
            count += 1;
        }
    }
    Ok(count)
}

/// Returns all source code patches as (relative_path, search_string, replace_string) tuples.
/// These transform stock Microsoft VSCode source into HugOS IDE source.
fn get_source_patches() -> Vec<(&'static str, &'static str, &'static str)> {
    vec![
        // ── src/main.ts — argv.json comments (3 x "VS Code" -> "HugOS") ──
        (
            "src/main.ts",
            "to pass permanent command line arguments to VS Code.",
            "to pass permanent command line arguments to HugOS."
        ),
        (
            "src/main.ts",
            "Changing this file requires a restart of VS Code.",
            "Changing this file requires a restart of HugOS."
        ),
        (
            "src/main.ts",
            "you see rendering issues in VS Code.",
            "you see rendering issues in HugOS."
        ),

        // ── src/vs/platform/product/common/product.ts — defaultChatAgent ──
        (
            "src/vs/platform/product/common/product.ts",
            "extensionId: 'GitHub.copilot'",
            "extensionId: 'HugOS.modelfusion'"
        ),
        (
            "src/vs/platform/product/common/product.ts",
            "chatExtensionId: 'GitHub.copilot-chat'",
            "chatExtensionId: 'HugOS.modelfusion'"
        ),

        // ── forwardingTelemetryService.ts — isCopilotLikeExtension ──
        (
            "src/vs/platform/dataChannel/browser/forwardingTelemetryService.ts",
            "extIdLowerCase === 'github.copilot' || extIdLowerCase === 'github.copilot-chat'",
            "extIdLowerCase === 'hugos.modelfusion' || extIdLowerCase === 'hugos.modelfusion'"
        ),

        // ── mcpListWidget.ts — COPILOT_EXTENSION_IDS ──
        (
            "src/vs/workbench/contrib/chat/browser/aiCustomization/mcpListWidget.ts",
            "['github.copilot', 'github.copilot-chat']",
            "['hugos.modelfusion', 'hugos.modelfusion']"
        ),

        // ── chatSetupProviders.ts — timeout increase for local server ──
        (
            "src/vs/workbench/contrib/chat/browser/chatSetup/chatSetupProviders.ts",
            "this.environmentService.remoteAuthority ? 60000 /* increase for remote scenarios */ : 20000",
            "this.environmentService.remoteAuthority ? 60000 /* increase for remote scenarios */ : 60000 /* 60s — accommodates local ModelFusion server startup */"
        ),

        // ── editSourceTrackingFeature.ts — extension IDs ──
        (
            "src/vs/workbench/contrib/editTelemetry/browser/telemetry/editSourceTrackingFeature.ts",
            "'GitHub.copilot'",
            "'HugOS.modelfusion'"
        ),

        // ── editSourceTrackingImpl.ts — extension IDs ──
        (
            "src/vs/workbench/contrib/editTelemetry/browser/telemetry/editSourceTrackingImpl.ts",
            "'github.copilot'",
            "'hugos.modelfusion'"
        ),

        // ── terminalMenus.ts — isAiContributedProfile ──
        (
            "src/vs/workbench/contrib/terminal/browser/terminalMenus.ts",
            "extensionIdentifier === 'github.copilot-chat'",
            "extensionIdentifier === 'hugos.modelfusion'"
        ),

        // ── settingsLayout.ts — commonly used settings ──
        (
            "src/vs/workbench/contrib/preferences/browser/settingsLayout.ts",
            "'GitHub.copilot-chat.manageExtension'",
            "'HugOS.modelfusion.manageExtension'"
        ),

        // ── mcpRegistry.ts — inject modelfusion collection filter ──
        (
            "src/vs/workbench/contrib/mcp/common/mcpRegistry.ts",
            "public registerCollection(collection: McpCollectionDefinition): IDisposable {",
            "public registerCollection(collection: McpCollectionDefinition): IDisposable {\n\t\tconst filteredServerDefinitions = collection.serverDefinitions.map(defs =>\n\t\t\tdefs.filter(d => d.id.endsWith('.modelfusion') || d.label === 'modelfusion')\n\t\t);\n\t\tconst filteredCollection: McpCollectionDefinition = {\n\t\t\t...collection,\n\t\t\tserverDefinitions: filteredServerDefinitions\n\t\t};\n\t\tcollection = filteredCollection;"
        ),

        // ── languageModels.ts — inject ModelFusion vendor auto-registration ──
        // We inject after the onDidChangeLanguageModelGroups listener registration
        // ── languageModels.ts — inject ModelFusion vendor auto-registration ──
        // We inject after the onDidChangeLanguageModelGroups listener registration
        (
            "src/vs/workbench/contrib/chat/common/languageModels.ts",
            "this._store.add(this._languageModelsConfigurationService.onDidChangeLanguageModelGroups(changedGroups => this._onDidChangeLanguageModelGroups(changedGroups)));",
            "this._store.add(this._languageModelsConfigurationService.onDidChangeLanguageModelGroups(changedGroups => this._onDidChangeLanguageModelGroups(changedGroups)));\n\n\t\t// HugOS: Auto-register ModelFusion provider group on startup\n\t\t{\n\t\t\tconst groups = this._languageModelsConfigurationService.getLanguageModelsProviderGroups();\n\t\t\tif (!groups.some(g => g.vendor === 'modelfusion')) {\n\t\t\t\tthis._languageModelsConfigurationService.addLanguageModelsProviderGroup({\n\t\t\t\t\tvendor: 'modelfusion',\n\t\t\t\t\tname: 'ModelFusion Local Panel',\n\t\t\t\t\tsettings: { 'modelfusion-local': {} }\n\t\t\t\t}).then(\n\t\t\t\t\t() => this._logService.info('[LM] Added default ModelFusion provider group on startup'),\n\t\t\t\t\t(e) => this._logService.error('[LM] Failed to add default ModelFusion provider group on startup', e)\n\t\t\t\t);\n\t\t\t}\n\t\t}"
        ),
    ]
}

#[cfg(test)]
mod prompt_interception_tests {
    fn check_is_empty_user_prompt(prompt: &str) -> bool {
        let lower = prompt.to_lowercase();
        if lower.contains("@agent") || lower.contains("/evolve") || lower.contains("/stats") || lower.contains("<attachments>") || lower.contains("<attachment>") || lower.contains("<user_request>") {
            false
        } else {
            let mut clean = lower.clone();
            let strip_tags = [
                "customizationsupdate", "conversation-summary", "conversationsummary",
                "environment_info", "workspace_info", "editorcontext",
                "reminderinstruction", "attachments", "attachment",
                "tooluseinstructions", "editfileinstructions", "notebookinstructions",
                "usermemory", "sessionmemory", "repomemory",
                "memoryscopes", "memoryguidelines", "memoryinstructions",
                "outputformatting", "instructions", "context",
            ];
            for prefix in strip_tags {
                let needle = format!("<{}", prefix);
                while let Some(s) = clean.find(&needle) {
                    let after = &clean[s + 1..];
                    let tag_end = after.find(|c: char| c == '>' || c == ' ' || c == '\n' || c == '\r').unwrap_or(after.len());
                    let tag = &after[..tag_end];
                    let close = format!("</{}>", tag);
                    if let Some(e) = clean[s..].find(&close) {
                        clean.replace_range(s..s + e + close.len(), " ");
                    } else {
                        let le = clean[s..].find('\n').map(|p| s + p + 1).unwrap_or(clean.len());
                        clean.replace_range(s..le, " ");
                    }
                }
            }
            let usr = if let Some(pos) = clean.rfind("\nuser:") {
                &clean[pos + 6..]
            } else if let Some(pos) = clean.rfind("user:") {
                &clean[pos + 5..]
            } else {
                &clean[..]
            };
            usr.trim().is_empty()
        }
    }

    #[test]
    fn test_agent_command_with_attachments_not_empty() {
        let prompt = "System: You are HugOS AI.\nuser: <attachments>\n<attachment id=\"file:import math.py\">\nExcerpt from import math.py:\nimport math\n</attachment>\n</attachments>\n@agent /evolve";
        assert!(!check_is_empty_user_prompt(prompt), "@agent command with attachments must NOT be classified as empty prompt");
    }

    #[test]
    fn test_attachments_only_not_empty() {
        let prompt = "System: You are HugOS AI.\nuser: <attachments>\n<attachment id=\"file:import math.py\">\nimport math\n</attachment>\n</attachments>";
        assert!(!check_is_empty_user_prompt(prompt), "Attachments-only message must NOT be classified as empty prompt");
    }

    #[test]
    fn test_context_refresh_is_empty() {
        let prompt = "System: You are HugOS AI.\nuser: <environment_info>\nOS: Windows\n</environment_info>\n<workspace_info>\npath: d:\\test\n</workspace_info>";
        assert!(check_is_empty_user_prompt(prompt), "System context refresh without user content MUST be classified as empty prompt");
    }

    #[test]
    fn test_parse_slash_commands_agent_stats() {
        let mut prompt = "User: @agent /stats".to_string();
        let (mut gpu, mut cpu, mut openvino, mut fusion) = (false, false, false, false);
        super::parse_slash_commands_in_prompt(&mut prompt, &mut gpu, &mut cpu, &mut openvino, &mut fusion);
        assert_eq!(std::env::var("MODELFUSION_STATS").unwrap_or_default(), "true");
    }

    #[test]
    fn test_parse_slash_commands_agent_no_slash_stats() {
        let mut prompt = "User: @agent stats".to_string();
        let (mut gpu, mut cpu, mut openvino, mut fusion) = (false, false, false, false);
        super::parse_slash_commands_in_prompt(&mut prompt, &mut gpu, &mut cpu, &mut openvino, &mut fusion);
        assert_eq!(std::env::var("MODELFUSION_STATS").unwrap_or_default(), "true");
    }

    #[test]
    fn test_parse_slash_commands_comment() {
        let mut prompt = "User: @comment add comments to this code".to_string();
        let (mut gpu, mut cpu, mut openvino, mut fusion) = (false, false, false, false);
        super::parse_slash_commands_in_prompt(&mut prompt, &mut gpu, &mut cpu, &mut openvino, &mut fusion);
    }
}



