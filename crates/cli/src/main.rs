//! CLI Entry Point for ModelFusion.

use anyhow::Result;
use clap::Parser;
use modelfusion_core::{ComprehensiveTaskHandler, HuggingFaceOrchestrator};
use model_selection::SelectionStrategy;
use std::collections::HashMap;

#[derive(Parser, Debug)]
#[command(name = "modelfusion", version = "0.1.0", about = "ModelFusion - Advanced HuggingFace Model Orchestration System")]
struct Args {
    // ---------------------------------------------------------
    // Global Flags
    // ---------------------------------------------------------
    #[arg(long, help = "Path to file for analysis or processing")]
    file: Option<String>,

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

    // ---------------------------------------------------------
    // Data Science Flags
    // ---------------------------------------------------------
    #[arg(long, help = "Run the Data Analyst workflow on CSV/Excel")]
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
    if let Some(ref prompt) = args.prompt {
        let is_fusion_needed = args.fusion || modelfusion_core::fusion_engine::classify_prompt(prompt);

        if is_fusion_needed {
            println!("🤖 Model Fusion is active (explicitly requested or dynamically classified).");
            match modelfusion_core::fusion_engine::run_fusion(prompt).await {
                Ok(content) => {
                    println!("\n✨ Orchestration Successful (via Model Fusion)!\n");
                    println!("{}", content);
                }
                Err(e) => {
                    println!("\n❌ Orchestration Failed (via Model Fusion)!\n");
                    println!("Error: {}", e);
                }
            }
            return Ok(());
        }

        let db_path = handler.db_path.clone();
        let orchestrator = HuggingFaceOrchestrator::new(db_path, args.budget, args.enable_ml, args.verbose);

        let task_override = determine_task_override(&args);
        let selection_strategy = parse_selection_strategy(&args.selection_strategy);

        let options = HashMap::new();
        let res = orchestrator
            .process_task(
                &prompt,
                task_override.as_deref(),
                None,
                args.use_openai,
                args.file.as_deref(),
                selection_strategy,
                options,
            )
            .await;

        if res.success {
            println!("\n✨ Orchestration Successful!\n");
            println!("{}", res.content);
        } else {
            println!("\n❌ Orchestration Failed!\n");
            if let Some(err) = res.error_message {
                println!("Error: {}", err);
            }
        }
    } else {
        // Fallback display similar to Python's else clause
        println!("HFOrchestra - Advanced HuggingFace Model Orchestration System");
        println!("============================================================");
        println!("Available modules:");
        println!("  🔍 Model Discovery - Find and evaluate HuggingFace models");
        println!("  🛡️ Security - ATLAS threat detection and monitoring");
        println!("  📊 Performance - System monitoring and optimization");
        println!("  🔍 PE Analysis - Malware detection and binary analysis");
        println!("  🤖 Orchestration - Multi-provider LLM management");
        println!("  🧠 ML Model Selection - Machine learning-based intelligent selection");
        println!("  🔧 SINQ Quantization - Model quantization for memory efficiency");
        println!("\nUse --help for comprehensive usage information");
    }

    Ok(())
}

/// Print dynamic ensemble information banner as expected by main.py flow.
fn print_ensemble_info(strategy: &str) {
    println!("============================================================");
    println!("🤖 Ensemble Model Selection: Active Strategy: {}", strategy);
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
