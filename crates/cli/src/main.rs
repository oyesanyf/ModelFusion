//! CLI Entry Point for ModelFusion.

use anyhow::Result;
use clap::Parser;
use modelfusion_core::{ComprehensiveTaskHandler, HuggingFaceOrchestrator};
use model_selection::SelectionStrategy;
use std::collections::HashMap;
use chrono;

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

    #[arg(long, help = "Use OpenVINO for optimized CPU inference (requires: pip install -U openvino optimum-intel)")]
    openvino: bool,

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
}

#[tokio::main]
async fn main() -> Result<()> {
    // Load .env variables
    dotenv::dotenv().ok();

    let args = Args::parse();

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
    print_ensemble_info(&args.selection_strategy);

    // Initialize the comprehensive task handler
    let handler = ComprehensiveTaskHandler::new(None)?;
    handler.ensure_database_exists()?;

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

    if args.pe_header_extraction {
        let file_path = args.file.as_deref().unwrap_or("test.exe");
        let prompt = args.prompt.as_deref().unwrap_or("Perform PE analysis");
        handler.handle_pe_analysis(file_path, prompt);
        return Ok(());
    }

    // ---------------------------------------------------------
    // Orchestration Flow
    // ---------------------------------------------------------
    if args.prompt.is_some() || args.folder.is_some() {
        let mut final_prompt = args.prompt.clone().unwrap_or_else(|| {
            "Review the code in this folder, identify any bugs, vulnerabilities, or optimization opportunities, and suggest improvements.".to_string()
        });

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

        let is_fusion_needed = args.fusion || modelfusion_core::fusion_engine::classify_prompt(&final_prompt);

        if is_fusion_needed {
            println!("[FUSION] Model Fusion is active (explicitly requested or dynamically classified).");
            std::env::set_var("MODELFUSION_NO_SIMULATION", "true");
            if args.ollama {
                // Ensure Ollama is running — auto-start if needed
                println!("🦙 [FUSION] Ensuring Ollama is running...");
                match model_selection::memory::ensure_ollama_running() {
                    Ok(()) => {
                        println!("✅ [FUSION] Ollama is ready.");
                        std::env::set_var("MODELFUSION_USE_OLLAMA", "true");
                    }
                    Err(e) => {
                        return Err(anyhow::anyhow!("❌ [FUSION] {}", e));
                    }
                }
            } else if args.openvino {
                // Verify OpenVINO Python package is installed
                println!("🔷 [FUSION] Checking OpenVINO installation...");
                let check = std::process::Command::new("python")
                    .args(["-c", "import openvino; print('OK')"])
                    .output();
                match check {
                    Ok(out) if out.status.success() => {
                        println!("✅ [FUSION] OpenVINO is installed.");
                        std::env::set_var("MODELFUSION_USE_OPENVINO", "true");
                        println!("🔷 [FUSION] Using OpenVINO for optimized CPU inference.");
                    }
                    _ => {
                        return Err(anyhow::anyhow!(
                            "❌ [FUSION] OpenVINO not installed.\n\n  Install with: pip install -U openvino\n\n  This provides optimized CPU inference, 2-3× faster than transformers."
                        ));
                    }
                }
            } else {
                std::env::set_var("MODELFUSION_USE_TRANSFORMERS", "true");
                println!("🐍 [FUSION] Using local Python transformers for model execution.");
            }

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
                }
                Err(e) => {
                    println!("\n[ERROR] Orchestration Failed (via Model Fusion)!\n");
                    println!("Error: {}", e);
                }
            }
            return Ok(());
        }

        let orchestrator = HuggingFaceOrchestrator::new(db_path, args.budget, args.enable_ml, args.verbose);

        let options = HashMap::new();
        let res = orchestrator
            .process_task(
                &final_prompt,
                task_override.as_deref(),
                None,
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
        } else {
            println!("\n[ERROR] Orchestration Failed!\n");
            if let Some(err) = res.error_message {
                println!("Error: {}", err);
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

/// Convert content to DOCX (represented as RTF bytes for compatibility)
fn generate_minimal_docx(content: &str) -> Vec<u8> {
    generate_minimal_rtf(content).into_bytes()
}
