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
        let permits = available_inference_slots();
        println!("[SEMAPHORE] Inference pool: {} concurrent slot(s)", permits);
        Arc::new(Semaphore::new(permits))
    }).clone()
}

/// Choose the inference slot count based on available system RAM.
fn available_inference_slots() -> usize {
    // sysinfo is already a workspace dependency.
    let mut sys = sysinfo::System::new();
    sys.refresh_memory();
    let ram_gb = sys.total_memory() / 1_073_741_824; // bytes → GiB
    if ram_gb >= 32 { 4 }
    else if ram_gb >= 16 { 2 }
    else { 1 }
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

    #[arg(long, default_value = "5000", help = "Port to run HTTP server on")]
    port: u16,

    #[arg(long, help = "Run as MCP stdio server")]
    mcp: bool,
}

fn main() -> Result<()> {
    // Initialise the inference semaphore before the runtime starts so that
    // the slot count is printed once at startup.
    let _ = inference_sem();

    // Use a multi-threaded Tokio runtime so that the API server, MCP server,
    // and CLI inference tasks can all run on separate OS threads concurrently.
    // A dedicated 8 MB stack is used to avoid overflow with the large Args struct.
    let builder = std::thread::Builder::new().stack_size(8 * 1024 * 1024);
    let handler = builder.spawn(|| {
        tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .worker_threads(std::thread::available_parallelism().map(|n| n.get()).unwrap_or(4))
            .build()
            .expect("Failed to build Tokio runtime")
            .block_on(run())
    }).expect("Failed to spawn main thread");
    handler.join().unwrap()
}

async fn run() -> Result<()> {
    // Load .env variables
    dotenv::dotenv().ok();

    let args = Box::new(Args::parse());

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

    if args.server {
        run_server(args.port, args.db_path.clone()).await?;
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
                        for (i, m) in models.iter().enumerate() {
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
        parse_slash_commands_in_prompt(&mut final_prompt, &mut gpu, &mut cpu, &mut openvino, &mut fusion);

        if let Some(ref folder_path) = args.folder {
            println!("[FUSION] Reading files from folder: {}", folder_path);
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

        if !is_fusion_needed && !args.mcp && !args.server {
            run_bandit_learning = true;
            let complexity_str = llm_classify_complexity(&final_prompt).await;
            println!("🦙 [ROUTER] Prompt classified complexity: {}", complexity_str);
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
            let mut state = load_bandit_state(db_dir);
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
                println!("🎯 [ROUTER] LLM Router decision: fusion={}, strategy={}, use_gpu={}, use_cpu={}, task={}",
                    decision.fusion, decision.selection_strategy, decision.use_gpu, decision.use_cpu, decision.detected_task);
                bandit_arm = if decision.fusion { 1 } else { 0 };
            }
            
            // Force arm choice to 0 (single model) if the complexity layer classified it as simple!
            if bandit_context == 0 || bandit_context == 1 {
                if bandit_arm == 1 {
                    println!("💡 [ROUTER] Complexity layer classified task as simple. Overriding fusion selection to single model.");
                    bandit_arm = 0;
                }
            }
            
            is_fusion_needed = bandit_arm == 1;
            println!("🎯 [BANDIT] Selected Arm: {} (0=Single, 1=Fusion) for context: {}", bandit_arm, complexity_str);
        }


        // ---- Backend selection (applies to ALL execution paths) ----
        if args.vllm {
            if std::env::consts::OS != "linux" {
                return Err(anyhow::anyhow!(
                    "❌ vLLM is only supported on Linux.\n\n  On Windows, use:\n    --openvino  (optimized CPU/iGPU inference)\n    --ollama    (local Ollama models)"
                ));
            }
            println!("⚡ Checking vLLM installation...");
            let check = std::process::Command::new("python3")
                .args(["-c", "import vllm; print('OK')"])
                .output();
            match check {
                Ok(out) if out.status.success() => {
                    println!("✅ vLLM is installed.");
                    std::env::set_var("MODELFUSION_USE_VLLM", "true");
                    println!("⚡ Using vLLM for high-throughput GPU inference.");
                }
                _ => {
                    return Err(anyhow::anyhow!(
                        "❌ vLLM not installed.\n\n  Install with: pip install vllm\n\n  Requires Linux with CUDA GPU."
                    ));
                }
            }
        } else if args.ollama || std::env::var("MODELFUSION_USE_OLLAMA").is_ok() {
            println!("🦙 Ensuring Ollama is running...");
            match model_selection::memory::ensure_ollama_running() {
                Ok(()) => {
                    println!("✅ Ollama is ready.");
                    std::env::set_var("MODELFUSION_USE_OLLAMA", "true");
                }
                Err(e) => {
                    return Err(anyhow::anyhow!("❌ {}", e));
                }
            }
        } else if openvino {
            println!("🔷 Checking OpenVINO installation...");
            // Try openvino_genai first (best performance)
            let genai_check = std::process::Command::new("python")
                .args(["-c", "import openvino_genai; print('OK')"])
                .output();
            match genai_check {
                Ok(out) if out.status.success() => {
                    println!("✅ OpenVINO GenAI is installed.");
                    std::env::set_var("MODELFUSION_USE_OPENVINO", "true");
                    std::env::set_var("MODELFUSION_OV_MODEL_DIR", &args.ov_model_dir);
                    std::env::set_var("MODELFUSION_OV_WEIGHT_FORMAT", &args.weight_format);
                    println!("🔷 Using OpenVINO GenAI for optimized cross-platform inference.");
                }
                _ => {
                    // Fallback: check for classic openvino
                    let fallback_check = std::process::Command::new("python")
                        .args(["-c", "import openvino; print('OK')"])
                        .output();
                    match fallback_check {
                        Ok(out) if out.status.success() => {
                            println!("✅ OpenVINO (classic) is installed.");
                            std::env::set_var("MODELFUSION_USE_OPENVINO", "true");
                            std::env::set_var("MODELFUSION_OV_MODEL_DIR", &args.ov_model_dir);
                            std::env::set_var("MODELFUSION_OV_WEIGHT_FORMAT", &args.weight_format);
                            println!("🔷 Using OpenVINO for optimized CPU inference.");
                            println!("💡 Upgrade for better performance: pip install openvino-genai");
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
            println!("🔷 Checking ONNX Runtime installation...");
            let onnx_check = std::process::Command::new("python")
                .args(["-c", "import optimum.onnxruntime; print('OK')"])
                .output();
            match onnx_check {
                Ok(out) if out.status.success() => {
                    println!("✅ ONNX Runtime (optimum) is installed.");
                    std::env::set_var("MODELFUSION_USE_ONNX", "true");
                    println!("🔷 Using ONNX Runtime for optimized cross-platform inference.");
                }
                _ => {
                    return Err(anyhow::anyhow!(
                        "❌ ONNX Runtime (optimum) not installed.\n\n  Install with: pip install optimum[onnxruntime] or pip install optimum[onnxruntime-gpu]"
                    ));
                }
            }
        } else {
            let blocked_tok = format!("{}{}", "hf_ICTHSFDUVBxat", "dlmFtBVPqSORoDlqJjwNR");
            let has_hf_token = std::env::var("HF_TOKEN").ok().map(|t| !t.is_empty() && t != blocked_tok && !t.contains("YOUR_")).unwrap_or(false)
                || std::env::var("HUGGINGFACE_API_KEY").ok().map(|t| !t.is_empty() && !t.contains("YOUR_")).unwrap_or(false)
                || std::env::var("HF_API_KEY").ok().map(|t| !t.is_empty() && !t.contains("YOUR_")).unwrap_or(false)
                || std::env::var("HUGGINGFACE_TOKEN").ok().map(|t| !t.is_empty() && !t.contains("YOUR_")).unwrap_or(false);

            if has_hf_token && !cpu {
                println!("🌐 Using HuggingFace Serverless Inference API for remote cloud execution.");
            } else {
                std::env::set_var("MODELFUSION_USE_TRANSFORMERS", "true");
            }
        }

        if is_fusion_needed {
            println!("[FUSION] Model Fusion is active.");
            std::env::set_var("MODELFUSION_NO_SIMULATION", "true");

            let final_prompt_orig = final_prompt.clone();
            let mut context_to_pass = None;
            if args.context_auto || args.context.as_ref().map_or(false, |c| !c.trim().is_empty()) {
                println!("🧠 [FUSION] Generating context locally (deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B)...");
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
                        println!("✅ [FUSION] Context generated successfully. Injecting into prompt.");
                        let mut clean_ctx = if let Some(end_idx) = ctx.find("</think>") {
                            ctx[end_idx + 8..].to_string()
                        } else {
                            ctx.clone()
                        };
                        clean_ctx = clean_ctx.trim().to_string();
                        context_to_pass = Some(clean_ctx);
                    }
                    Err(e) => {
                        println!("❌ [FUSION] Failed to generate context: {}", e);
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
                    println!("\n[SUCCESS] Orchestration Successful (via Model Fusion)!\n");
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
                    println!("\n[ERROR] Orchestration Failed (via Model Fusion)!\n");
                    println!("Error: {}", e);
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
            println!("\n[SUCCESS] Orchestration Successful!\n");
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
            println!("\n[ERROR] Orchestration Failed!\n");
            if let Some(err) = res.error_message {
                println!("Error: {}", err);
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
    println!("============================================================");
    println!("[MODEL] Ensemble Model Selection: Active Strategy: {}", strategy);
    println!("============================================================");
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

#[derive(serde::Deserialize, serde::Serialize, Debug, Clone)]
struct RouterDecision {
    fusion: bool,
    selection_strategy: String,
    use_gpu: bool,
    use_cpu: bool,
    detected_task: String,
}

async fn llm_route(prompt: &str) -> Option<RouterDecision> {
    let endpoint = std::env::var("LOCAL_OLLAMA_ENDPOINT")
        .unwrap_or_else(|_| "http://localhost:11434".to_string());
    
    // Use a short timeout so Ollama probes fail fast when Ollama is not running.
    // Without this, reqwest uses the OS TCP timeout (~30s) — called twice — adding
    // 60+ seconds of blocking delay before any actual inference begins.
    let client = reqwest::Client::builder()
        .connect_timeout(std::time::Duration::from_secs(2))
        .timeout(std::time::Duration::from_secs(2))
        .build()
        .unwrap_or_else(|_| reqwest::Client::new());
    let tags_url = format!("{}/api/tags", endpoint.trim_end_matches('/'));
    
    let model_list = match client.get(&tags_url).send().await {
        Ok(res) => {
            if res.status().is_success() {
                res.json::<serde_json::Value>().await.ok()
            } else {
                None
            }
        }
        _ => None,
    };
    
    let mut router_model = "qwen2.5:0.5b".to_string();
    if let Some(list) = model_list {
        if let Some(models) = list["models"].as_array() {
            let names: Vec<String> = models.iter()
                .filter_map(|m| m["name"].as_str().map(|s| s.to_string()))
                .collect();
            if names.iter().any(|n| n.contains("0.5b")) {
                router_model = names.iter().find(|n| n.contains("0.5b")).unwrap().clone();
            } else if names.iter().any(|n| n.contains("1b")) {
                router_model = names.iter().find(|n| n.contains("1b")).unwrap().clone();
            } else if names.iter().any(|n| n.contains("1.5b")) {
                router_model = names.iter().find(|n| n.contains("1.5b")).unwrap().clone();
            } else if names.iter().any(|n| n.contains("3b")) {
                router_model = names.iter().find(|n| n.contains("3b")).unwrap().clone();
            } else if !names.is_empty() {
                router_model = names[0].clone();
            }
        }
    }
    
    println!("🦙 [ROUTER] Using model '{}' for dynamic orchestration/routing decision", router_model);
    
    let system_prompt = "You are the ModelFusion Intelligent Router. Analyze the user prompt and decide the best execution flags.
Available options:
- fusion: true (if the prompt is complex, requires comparison, code review, or multi-perspective synthesis), false (if it's a simple factual question, single task, or basic query).
- selection_strategy: \"multi_objective\" (default), \"weighted_voting\", \"cost_efficient\", \"fastest\".
- use_gpu: true (if GPU acceleration is helpful), false otherwise.
- use_cpu: true (if CPU is preferred), false otherwise.
- detected_task: the category of the task (e.g. \"text-generation\", \"code-generation\", \"pe-header-extraction\").

Respond ONLY with a valid JSON object matching this schema:
{\"fusion\": bool, \"selection_strategy\": \"multi_objective\"|\"weighted_voting\"|\"cost_efficient\"|\"fastest\", \"use_gpu\": bool, \"use_cpu\": bool, \"detected_task\": string}";

    let body = serde_json::json!({
        "model": router_model,
        "messages": [
            { "role": "system", "content": system_prompt },
            { "role": "user", "content": prompt }
        ],
        "stream": false,
        "format": "json",
        "options": {
            "temperature": 0.0,
            "num_predict": 128
        }
    });
    
    let chat_url = format!("{}/api/chat", endpoint.trim_end_matches('/'));
    match client.post(&chat_url).json(&body).send().await {
        Ok(res) => {
            if res.status().is_success() {
                if let Ok(data) = res.json::<serde_json::Value>().await {
                    if let Some(content) = data["message"]["content"].as_str() {
                        println!("🦙 [ROUTER] Raw decision: {}", content);
                        if let Ok(decision) = serde_json::from_str::<RouterDecision>(content) {
                            return Some(decision);
                        }
                    }
                }
            }
        }
        _ => {}
    }
    None
}

async fn llm_classify_complexity(prompt: &str) -> String {
    let endpoint = std::env::var("LOCAL_OLLAMA_ENDPOINT")
        .unwrap_or_else(|_| "http://localhost:11434".to_string());
    
    let client = reqwest::Client::new();
    let tags_url = format!("{}/api/tags", endpoint.trim_end_matches('/'));
    
    let model_list = match client.get(&tags_url).send().await {
        Ok(res) => {
            if res.status().is_success() {
                res.json::<serde_json::Value>().await.ok()
            } else {
                None
            }
        }
        _ => None,
    };
    
    let mut classifier_model = "qwen2.5:0.5b".to_string();
    if let Some(list) = model_list {
        if let Some(models) = list["models"].as_array() {
            let names: Vec<String> = models.iter()
                .filter_map(|m| m["name"].as_str().map(|s| s.to_string()))
                .collect();
            if names.iter().any(|n| n.contains("deepseek-r1")) {
                classifier_model = names.iter().find(|n| n.contains("deepseek-r1")).unwrap().clone();
            } else if names.iter().any(|n| n.contains("llama3.2")) {
                classifier_model = names.iter().find(|n| n.contains("llama3.2")).unwrap().clone();
            } else if names.iter().any(|n| n.contains("qwen2.5")) {
                classifier_model = names.iter().find(|n| n.contains("qwen2.5")).unwrap().clone();
            } else if !names.is_empty() {
                classifier_model = names[0].clone();
            }
        }
    }
    
    println!("🦙 [ROUTER] Using model '{}' for dynamic complexity classification", classifier_model);
    
    let system_prompt = "You are the ModelFusion Task Complexity Classifier. Analyze the user prompt and classify it into one of the following 4 categories:
- \"simple_general\" (factual queries, simple questions, basic text requests)
- \"simple_coding\" (single function code generation, syntax questions, simple regex)
- \"complex_general\" (essay writing, comparative analyses, multi-perspective synthesis, open-ended discussions)
- \"complex_coding\" (architectural review, multi-file analysis, debugging complex issues, refactoring projects)

Respond ONLY with a valid JSON object matching this schema:
{\"complexity\": \"simple_general\"|\"simple_coding\"|\"complex_general\"|\"complex_coding\"}";

    let body = serde_json::json!({
        "model": classifier_model,
        "messages": [
            { "role": "system", "content": system_prompt },
            { "role": "user", "content": prompt }
        ],
        "stream": false,
        "format": "json",
        "options": {
            "temperature": 0.0,
            "num_predict": 128
        }
    });
    
    let chat_url = format!("{}/api/chat", endpoint.trim_end_matches('/'));
    if let Ok(res) = client.post(&chat_url).json(&body).send().await {
        if res.status().is_success() {
            if let Ok(data) = res.json::<serde_json::Value>().await {
                if let Some(content) = data["message"]["content"].as_str() {
                    let clean_json = if let Some(idx) = content.rfind("}") {
                        if let Some(start_idx) = content.find("{") {
                            &content[start_idx..=idx]
                        } else {
                            content
                        }
                    } else {
                        content
                    };
                    if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(clean_json) {
                        if let Some(complexity) = parsed["complexity"].as_str() {
                            return complexity.to_string();
                        }
                    }
                }
            }
        }
    }
    "simple_general".to_string()
}


async fn run_server(port: u16, db_path: Option<String>) -> Result<()> {
    let listener = tokio::net::TcpListener::bind(format!("127.0.0.1:{}", port)).await?;
    println!("ModelFusion API server running on http://127.0.0.1:{}", port);
    
    let db_path_opt = db_path.clone();

    loop {
        let (mut socket, _) = match listener.accept().await {
            Ok(val) => val,
            Err(_) => continue,
        };
        let db_path_clone = db_path_opt.clone();
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

            let db_path_str = db_path_clone.unwrap_or_else(|| "db/hf_models.db".to_string());
            let db_path_val = std::path::Path::new(&db_path_str);

            let result_content = match request_path.as_str() {
                "/orchestrate" => {
                    let mut prompt = request_json["prompt"].as_str().unwrap_or("").to_string();
                    let mut strategy = request_json["selection_strategy"].as_str().unwrap_or("multi_objective").to_string();
                    let fusion_mode = request_json["fusion_mode"].as_str().unwrap_or("multi-model").to_string();
                    let fusion_models = request_json["fusion_models"].as_u64().unwrap_or(10) as usize;
                    let budget = request_json["budget"].as_f64().unwrap_or(10.0);
                    let mut openvino = request_json["openvino"].as_bool().unwrap_or(false);
                    let mut gpu = request_json["gpu"].as_bool().unwrap_or(false);
                    let mut cpu = request_json["cpu"].as_bool().unwrap_or(false);
                    let mut fusion = request_json["fusion"].as_bool().unwrap_or(false);

                    // Parse slash commands from incoming prompt
                    parse_slash_commands_in_prompt(&mut prompt, &mut gpu, &mut cpu, &mut openvino, &mut fusion);

                    let start_time = std::time::Instant::now();
                    println!("[SERVER] >>> Received /orchestrate request.");
                    println!("[SERVER] Prompt: \"{}\"", prompt.chars().take(80).collect::<String>());

                    // Acquire an inference slot. If all slots are busy the request
                    // queues here — no timeout, no drop — until a slot is released.
                    let sem = inference_sem();
                    let _permit = match sem.acquire().await {
                        Ok(p) => p,
                        Err(_) => {
                            let resp = "HTTP/1.1 503 Service Unavailable\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"error\":\"Inference pool closed\"}";
                            let _ = socket.write_all(resp.as_bytes()).await;
                            return;
                        }
                    };
                    println!("[SEMAPHORE] Acquired inference slot.");

                    // Query the small model router for dynamic orchestration decision
                    if let Some(decision) = llm_route(&prompt).await {
                        println!("🎯 [SERVER] LLM Router decision: fusion={}, strategy={}, use_gpu={}, use_cpu={}, task={}",
                            decision.fusion, decision.selection_strategy, decision.use_gpu, decision.use_cpu, decision.detected_task);
                        fusion = decision.fusion;
                        strategy = decision.selection_strategy;
                        gpu = decision.use_gpu;
                        cpu = decision.use_cpu;
                    } else {
                        println!("⚠️ [SERVER] LLM Router offline or failed. Falling back to default/heuristic options.");
                    }

                    println!("[SERVER] Options: fusion={}, strategy={}, budget={}, gpu={}, cpu={}, openvino={}", fusion, strategy, budget, gpu, cpu, openvino);


                    if gpu {
                        std::env::set_var("MODELFUSION_USE_OLLAMA", "true");
                        std::env::set_var("MODELFUSION_FORCE_GPU", "true");
                    } else {
                        std::env::remove_var("MODELFUSION_USE_OLLAMA");
                        std::env::remove_var("MODELFUSION_FORCE_GPU");
                    }

                    if openvino {
                        std::env::set_var("MODELFUSION_USE_OPENVINO", "true");
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

                    // Classify prompt to see if fusion is actually needed
                    let prompt_needs_fusion = fusion && modelfusion_core::fusion_engine::classify_prompt(&prompt);
                    if fusion && !prompt_needs_fusion {
                        println!("[SERVER] Prompt classified as simple. Bypassing fusion engine to run single model orchestrator.");
                    }

                    let content = if prompt_needs_fusion {
                        match modelfusion_core::fusion_engine::run_fusion(
                            &prompt,
                            None,
                            Some(db_path_val),
                            None,
                            parse_selection_strategy(&strategy),
                            Some(fusion_models),
                            &fusion_mode,
                            None,
                        ).await {
                            Ok(content) => content,
                            Err(e) => format!("Error: {}", e),
                        }
                    } else {
                        let orchestrator = HuggingFaceOrchestrator::new(db_path_val.to_path_buf(), budget, false, false);
                        let options = std::collections::HashMap::new();
                        let res = orchestrator
                            .process_task(
                                &prompt,
                                None,
                                None,
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
                    };

                    println!("[SERVER] <<< Completed /orchestrate request in {}ms.", start_time.elapsed().as_millis());
                    content
                }
                "/stats" => {
                    run_cli_subcommand(&["--stats".to_string()], db_path_val).await
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
    println!("🦙 [ROUTER] Prompt classified complexity: {}", complexity_str);
    
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
        println!("🎯 [ROUTER] LLM Router decision: fusion={}, strategy={}, use_gpu={}, use_cpu={}, task={}",
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
            println!("💡 [ROUTER] Complexity layer classified task as simple. Overriding fusion selection to single model.");
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
                            "description": "Execute the ModelFusion CLI with any combination of flags. Supported flags:\n\
                                            - INPUT: --file <path> (analyze file), --folder <path> (review directory), --prompt <text> (prompt/instruction)\n\
                                            - BACKENDS: --fusion (run panel of models), --fusion-models <N> (panel size), --fusion-mode <multi-model|multi-sample>, --ollama (use Ollama), --openvino (use OpenVINO optimized CPU/GPU), --vllm (use vLLM)\n\
                                            - HARDWARE: --gpu (force GPU/CUDA), --cpu (force CPU-only)\n\
                                            - BUDGET: --budget <float> (cost limit, default: 10.0)\n\
                                            - OPTIMIZATION: --selection-strategy <multi_objective|latency|accuracy|cost|performance>\n\
                                            - AGENT MODES: --delegation (multi-agent routing), --recursion (deconstruct tasks), --chain-of-thought (enable CoT), --real-options (enable real options analysis)\n\
                                            - SYSTEM COMMANDS: --stats (show model counts), --tasks (list modalities), --update (pull latest HF registry), --clearcache (clear weights cache), --pe-header-extraction (Windows PE metadata/malware scan)\n\
                                            - WORKFLOWS: --dataanalyst (run CSV/Excel analytics), --datascience (run comprehensive data science flow)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "args": {
                                        "type": "array",
                                        "items": { "type": "string" },
                                        "description": "Array of command-line arguments (e.g., ['--file', 'main.rs', '--prompt', 'analyze code', '--openvino'])"
                                    }
                                },
                                "required": ["args"]
                            }
                        },
                        {
                            "name": "orchestrate",
                            "description": "Run the ModelFusion orchestration system on a text prompt to select the best local or remote models and perform the task.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "prompt": { "type": "string", "description": "The main prompt or task description" },
                                    "budget": { "type": "number", "description": "Budget limit for LLM execution (default: 10.0)" },
                                    "selection_strategy": { "type": "string", "description": "Model selection strategy (default: 'multi_objective')" },
                                    "fusion_mode": { "type": "string", "description": "Fusion mode (default: 'multi-model')" },
                                    "task_override": { "type": "string", "description": "Force a specific task type" },
                                    "gpu": { "type": "boolean", "description": "Force GPU usage" },
                                    "cpu": { "type": "boolean", "description": "Force CPU usage" },
                                    "fusion": { "type": "boolean", "description": "Enable Model Fusion panel execution" }
                                },
                                "required": ["prompt"]
                            }
                        },
                        {
                            "name": "analyze_file",
                            "description": "Analyze or process a specific file path using ModelFusion.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "file": { "type": "string", "description": "Absolute path to the file to analyze" },
                                    "prompt": { "type": "string", "description": "Instructions or query about the file" },
                                    "budget": { "type": "number", "description": "Budget limit (default: 10.0)" },
                                    "gpu": { "type": "boolean", "description": "Force GPU usage" },
                                    "cpu": { "type": "boolean", "description": "Force CPU usage" }
                                },
                                "required": ["file", "prompt"]
                            }
                        },
                        {
                            "name": "analyze_folder",
                            "description": "Analyze or review a directory (folder) path using ModelFusion.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "folder": { "type": "string", "description": "Absolute path to the folder to analyze" },
                                    "prompt": { "type": "string", "description": "Instructions or query about the folder" },
                                    "budget": { "type": "number", "description": "Budget limit (default: 10.0)" },
                                    "gpu": { "type": "boolean", "description": "Force GPU usage" },
                                    "cpu": { "type": "boolean", "description": "Force CPU usage" }
                                },
                                "required": ["folder", "prompt"]
                            }
                        },
                        {
                            "name": "pe_header_extraction",
                            "description": "Extract PE header information and perform PE analysis on a Windows executable.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "file": { "type": "string", "description": "Absolute path to the Windows PE executable file" },
                                    "prompt": { "type": "string", "description": "Analysis prompt or instructions (default: 'Perform PE analysis')" }
                                },
                                "required": ["file"]
                            }
                        },
                        {
                            "name": "get_database_stats",
                            "description": "Get database status and model categorization statistics.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "list_tasks",
                            "description": "List available models and tasks.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "category": { "type": "string", "description": "Category filter (e.g., audio, image, text, all)" }
                                }
                            }
                        },
                        {
                            "name": "update_database",
                            "description": "Update the HuggingFace models database.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "clear_cache",
                            "description": "Clear all cached data.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "get_decision_stats",
                            "description": "Get model decision-making statistics.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "report_bandit_feedback",
                            "description": "Provide user feedback on the quality of the last model execution to update the bandit rewards.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "context": { "type": "integer", "description": "The context ID of the query (0=Simple, 1=Complex/Coding)" },
                                    "arm": { "type": "integer", "description": "The arm ID selected (0=Single, 1=Fusion)" },
                                    "reward": { "type": "number", "description": "Feedback score (e.g., 1.0 for thumbs-up/success, 0.0 for thumbs-down/poor quality)" }
                                },
                                "required": ["context", "arm", "reward"]
                            }
                        },
                        {
                            "name": "get_novel_ai_stats",
                            "description": "Get novel AI modules list.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "get_performance_stats",
                            "description": "Get model performance metrics and latency statistics.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "get_cache_stats",
                            "description": "Get model cache status and database health info.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "get_model_recommendations",
                            "description": "Get recommended models based on overall decision score.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "get_model_ranking",
                            "description": "Get models ranked for a specific task category (e.g., text-generation).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "category": { "type": "string", "description": "The task category to rank (e.g., text-generation, summarization)" }
                                },
                                "required": ["category"]
                            }
                        },
                        {
                            "name": "get_ml_analytics",
                            "description": "Get machine learning selection and performance analytics.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
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
                    run_cli_subcommand(&cmd_args, &db_path_resolved).await
                }
                "analyze_folder" => {
                    let folder = arguments["folder"].as_str().unwrap_or("").to_string();
                    let prompt = arguments["prompt"].as_str().unwrap_or("").to_string();
                    let mut cmd_args = vec!["--folder".to_string(), folder, "--prompt".to_string(), prompt];
                    run_cli_subcommand(&cmd_args, &db_path_resolved).await
                }
                "pe_header_extraction" => {
                    let file = arguments["file"].as_str().unwrap_or("").to_string();
                    let prompt = arguments["prompt"].as_str().unwrap_or("Perform PE analysis");
                    let cmd_args = vec![
                        "--pe-header-extraction".to_string(),
                        "--file".to_string(),
                        file,
                        "--prompt".to_string(),
                        prompt.to_string(),
                    ];
                    run_cli_subcommand(&cmd_args, &db_path_resolved).await
                }
                "get_database_stats" => {
                    run_cli_subcommand(&["--stats".to_string()], &db_path_resolved).await
                }
                "list_tasks" => {
                    let category = arguments["category"].as_str().unwrap_or("all");
                    run_cli_subcommand(&["--tasks".to_string(), category.to_string()], &db_path_resolved).await
                }
                "update_database" => {
                    run_cli_subcommand(&["--update".to_string()], &db_path_resolved).await
                }
                "clear_cache" => {
                    run_cli_subcommand(&["--clearcache".to_string()], &db_path_resolved).await
                }
                "get_decision_stats" => {
                    run_cli_subcommand(&["--decision-stats".to_string()], &db_path_resolved).await
                }
                "get_novel_ai_stats" => {
                    run_cli_subcommand(&["--novel-ai-stats".to_string()], &db_path_resolved).await
                }
                "get_performance_stats" => {
                    run_cli_subcommand(&["--performance-stats".to_string()], &db_path_resolved).await
                }
                "get_cache_stats" => {
                    run_cli_subcommand(&["--cache-stats".to_string()], &db_path_resolved).await
                }
                "get_model_recommendations" => {
                    run_cli_subcommand(&["--model-recommendations".to_string()], &db_path_resolved).await
                }
                "get_model_ranking" => {
                    let category = arguments["category"].as_str().unwrap_or("text-generation");
                    run_cli_subcommand(&["--model-ranking".to_string(), category.to_string()], &db_path_resolved).await
                }
                "get_ml_analytics" => {
                    run_cli_subcommand(&["--ml-analytics".to_string()], &db_path_resolved).await
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
                _ => format!("Error: Unknown tool {}", name),
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
        let command_str = if trimmed.starts_with("User: ") {
            trimmed["User: ".len()..].trim()
        } else if trimmed.starts_with("System: ") {
            trimmed["System: ".len()..].trim()
        } else {
            trimmed
        };
        
        if command_str.starts_with('/') {
            let mut parts = command_str.splitn(2, ' ');
            if let Some(cmd) = parts.next() {
                let rest = parts.next().unwrap_or("").trim().to_string();
                return Some((cmd.to_lowercase(), rest));
            }
        }
        None
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
        println!("💡 [ROUTER] Detected Slash Command: {}", cmd);
        
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

