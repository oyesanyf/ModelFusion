//! Universal Command Help & Sample Usage Engine for ModelFusion Master CLI.
//!
//! Provides rich, interactive terminal cards, parameter syntax, CLI flags,
//! and runnable copyable examples across all 15 categories, 107 tools, and 50+ models.

/// Checks if a string is a command help trigger token.
pub fn is_help_token(s: &str) -> bool {
    let lower = s.to_lowercase();
    let clean = lower
        .trim_start_matches('-')
        .trim_start_matches('/')
        .trim_start_matches('?');
    lower == "help"
        || lower == "--help"
        || lower == "-h"
        || lower == "/?"
        || lower == "?"
        || lower == "halp"
        || lower == "hlp"
        || lower == "helo"
        || clean == "help"
        || clean == "halp"
        || clean == "hlp"
        || clean == "helo"
}

/// Detects conversational queries containing "help" that should not trigger command help.
pub fn is_conversational_prompt(tokens: &[String]) -> bool {
    let text = tokens.iter().map(|s| s.to_lowercase()).collect::<Vec<_>>().join(" ");
    let conversational_starters = [
        "help me write",
        "help me code",
        "help me create",
        "help me generate",
        "help me fix",
        "help me debug",
        "help me find",
        "help me search",
        "help me solve",
        "help me understand",
        "help me build",
        "help me implement",
        "help me explain",
        "help me review",
        "help me draft",
        "help me calculate",
        "can you help",
        "please help me",
        "could you help",
    ];
    for starter in &conversational_starters {
        if text.contains(starter) {
            return true;
        }
    }
    false
}

/// Identifies if a string is a known tool, model, or category name.
pub fn is_known_tool_or_model(name: &str) -> bool {
    let clean = name
        .trim_start_matches('@')
        .trim_start_matches('/')
        .trim_start_matches('-')
        .to_lowercase();
    let keywords = [
        "classify", "zero-shot", "topic", "bart", "deberta", "distilbart", "longformer",
        "security", "graph-index", "graph", "vuln-scan", "secret-scan", "pii-scan",
        "code-translate", "dockerfile", "api-docs", "sast",
        "computer-use", "computer_use", "ui-tars", "screen-grounding", "desktop-click",
        "desktop-type", "desktop-scroll", "shopping", "ticket-booking", "exam-solver",
        "map-directions", "som", "markers",
        "acdso", "dataanalyst", "timeseries", "predict", "datascience", "decision",
        "finance", "finbert", "chronos", "fingpt", "llama-fin", "patchtst",
        "vision", "vqa", "object-detection", "image-classification", "video", "image",
        "florence-2", "llava", "yolov10", "flux",
        "pe", "pe_binary", "entropy", "strings", "packer-detect",
        "legal", "cuad", "cuad-bert", "saul-7b", "legal-bert", "legal-longformer",
        "law-chat", "law-llm", "lawma", "pile-of-law",
        "agent", "boost", "grill-me", "goal", "plan", "cot", "agentic-loop", "reflection", "decompose",
        "science", "esm2", "esmfold", "esm3", "chemberta", "molformer", "evo", "prithvi", "climax", "galactica",
        "sentiment", "moderation", "distilbert-sst2", "twitter-roberta", "go-emotions",
        "distilbert-emotion", "toxic-bert", "text-moderation",
        "utilities", "sys-info", "sysinfo", "update", "updatedb", "active-model",
        "fusion-status", "db-check", "db-vacuum", "db-rebuild", "db-prune", "audit-menus", "benchmark",
        "audio", "asr", "tts", "whisper", "kokoro", "piper",
        "web", "search", "arxiv", "wiki", "browser", "summarize",
        "writing", "humanize", "watermark", "translate", "style-transfer", "outline",
    ];
    keywords.iter().any(|&k| clean == k || clean.starts_with(k))
}

pub struct CategoryInfo {
    pub menu_index: u32,
    pub id: &'static str,
    pub icon: &'static str,
    pub title: &'static str,
    pub subtitle: &'static str,
    pub overview: &'static str,
    pub engines: &'static [(&'static str, &'static str)],
    pub directives: &'static [(&'static str, &'static str)],
    pub examples: &'static [&'static str],
}

pub struct ToolCard {
    pub id: &'static str,
    pub name: &'static str,
    pub category: &'static str,
    pub menu_index: u32,
    pub icon: &'static str,
    pub architecture: &'static str,
    pub purpose: &'static str,
    pub input_format: &'static str,
    pub options: &'static [(&'static str, &'static str)],
    pub directives: &'static [(&'static str, &'static str)],
    pub examples: &'static [&'static str],
    pub related: &'static [&'static str],
}

pub struct ModelCard {
    pub id: &'static str,
    pub name: &'static str,
    pub category: &'static str,
    pub menu_index: u32,
    pub icon: &'static str,
    pub author: &'static str,
    pub architecture: &'static str,
    pub purpose: &'static str,
    pub input_format: &'static str,
    pub sample_input: &'static str,
    pub options: &'static [(&'static str, &'static str)],
    pub directives: &'static [(&'static str, &'static str)],
    pub examples: &'static [&'static str],
    pub related: &'static [&'static str],
}

// -----------------------------------------------------------------------------
// Catalog of all 15 Menus / Categories
// -----------------------------------------------------------------------------
pub static CATEGORIES: &[CategoryInfo] = &[
    CategoryInfo {
        menu_index: 1,
        id: "classification",
        icon: "🏷️",
        title: "Classification & Taxonomy",
        subtitle: "Zero-Shot NLI, Logic Verification & Document Categorization",
        overview: "High-throughput local zero-shot classification, logic verification, and document taxonomy suite. Powered by Hugging Face foundation models fine-tuned on MultiNLI, FEVER, and financial disclosures.",
        engines: &[
            ("BART & DeBERTa NLI", "facebook/bart-large-mnli & cross-encoder/nli-deberta-v3-base"),
            ("DeBERTa FEVER & DistilBART", "deberta-v3-base-mnli-fever-anli & distilbart-mnli-12-3"),
            ("Longformer & FinBERT", "allenai/longformer-base-4096 & ProsusAI/finbert"),
        ],
        directives: &[
            ("@agent classify <model/labels> <text>", "Zero-shot classification assigning probabilities across candidate labels"),
            ("@agent zero-shot <text> --labels <l1,l2,...>", "Classify text into arbitrary candidate classes using NLI entailment"),
            ("@agent topic <text>", "Categorize long-form document into hierarchical subject themes"),
        ],
        examples: &[
            "@agent classify nli-deberta-v3-base \"The quarterly results exceeded all expectations\" candidate labels: technology, earnings, healthcare",
            "@agent zero-shot \"This product broke after two days\" --labels hardware, customer service, billing",
            "@agent topic longformer-base-4096 [Full text of research paper discussing quantum annealing algorithms]",
        ],
    },
    CategoryInfo {
        menu_index: 2,
        id: "code",
        icon: "💻",
        title: "Code & Security",
        subtitle: "Code Architecture, Security Forensics & Vulnerability Audit",
        overview: "Enterprise-grade local static application security testing (SAST), code architecture dependency graphing, memory safety review, secret leak detection, and polyglot transpilation. 100% offline with zero external API calls.",
        engines: &[
            ("Local Coder LLM", "Qwen2.5-Coder / DeepSeek-Coder"),
            ("Tree-Sitter AST Engine", "Native AST Grammar Parser"),
            ("OWASP Security Scanner", "Heuristic Rule Base"),
            ("Secret Leak Detector", "Regex & Shannon Entropy Scanner"),
        ],
        directives: &[
            ("@agent security <code/file>", "Comprehensive SAST security audit for buffer overflows, SQL injection, and memory safety"),
            ("@agent graph-index <path>", "Build full abstract syntax tree and call-graph architecture dependency map"),
            ("@agent vuln-scan <file>", "Deep vulnerability scan targeting memory corruption, use-after-free, and unsafe blocks"),
            ("@agent secret-scan <file/repo>", "Scan for leaked API keys, tokens, private certificates, and credentials"),
            ("@agent pii-scan <text/file>", "Discover leaked SSNs, credit cards, emails, and confidential identity data"),
            ("@agent code-translate to <lang>: <code>", "Polyglot AST-preserving code transpile across Rust, Python, Go, TypeScript, C++"),
            ("@agent dockerfile <path>", "Synthesize minimal attack-surface multi-stage production Dockerfiles"),
            ("@agent api-docs <code>", "Generate OpenAPI 3.0 / Swagger specs and markdown documentation directly from code"),
        ],
        examples: &[
            "@agent security fn authenticate(user: &str, pass: &str) -> bool { ... }",
            "@agent graph-index crates/cli/src",
            "@agent secret-scan config/settings.json",
            "@agent code-translate to Rust: function fib(n) { return n <= 1 ? n : fib(n-1) + fib(n-2); }",
        ],
    },
    CategoryInfo {
        menu_index: 3,
        id: "computer_use",
        icon: "🖱️",
        title: "Computer Use & OS Automation",
        subtitle: "Screen Grounding, VLM Desktop Agent & OS Automation",
        overview: "Autonomous Windows OS desktop control and GUI automation powered by Vision-Language Models (UI-TARS / Qwen2.5-VL), Set-of-Mark visual coordinate grounding, and native input dispatchers with sub-50ms preemption.",
        engines: &[
            ("UI-TARS 7B/72B", "Vision-Language GUI Agent (ByteDance)"),
            ("Set-of-Mark (SoM)", "Visual Coordinate Grounding Badge Overlay"),
            ("Native Windows Dispatcher", "Win32 SendInput / Job Object Instant Preemption"),
        ],
        directives: &[
            ("@agent computer-use <task>", "Launch end-to-end autonomous OS desktop agent to accomplish goal"),
            ("@agent ui-tars <goal>", "Dispatch UI-TARS action loop with sub-50ms preemption"),
            ("@agent screen-grounding", "Capture active screen, assign numbered Set-of-Mark bounding boxes to all controls"),
            ("@agent desktop-click <x,y>", "Simulate hardware mouse click at specified viewport or screen coordinate"),
            ("@agent desktop-type <text>", "Send verified keyboard strokes or hotkey sequences to active window"),
            ("@agent desktop-scroll <delta>", "Dispatch vertical or horizontal mouse wheel scroll event"),
            ("@agent shopping <item>", "Automate e-commerce navigation, price comparison, cart addition, and checkout flow"),
            ("@agent ticket-booking <details>", "Automate airline/train reservation forms and seat selection"),
            ("@agent exam-solver <question>", "Visual reasoning solver for complex multi-choice exam figures and diagrams"),
            ("@agent map-directions <route>", "Navigate GIS mapping web applications and compute optimal route waypoints"),
        ],
        examples: &[
            "@agent computer-use Open Notepad and write a project status report",
            "@agent screen-grounding",
            "@agent shopping Find best price for 32GB DDR5 SODIMM laptop RAM",
            "@agent ticket-booking Find one-way flight from JFK to LHR on November 15",
        ],
    },
    CategoryInfo {
        menu_index: 4,
        id: "tabular",
        icon: "📊",
        title: "Data & Spreadsheets (CSV/Excel)",
        subtitle: "Adaptive Contextual Data Science Optimization & Tabular AutoML",
        overview: "Adaptive Contextual Data Science Optimization (ACDSO), automated feature synthesis, statistical hypothesis testing, time-series forecasting, and machine learning model training on tabular data.",
        engines: &[
            ("ACDSO AutoML Pipeline", "Context-Aware Feature Engineering & Selection"),
            ("PatchTST / Chronos", "Time-Series Transformers for Trend Forecasting"),
            ("DuckDB / Polars", "In-Memory Vector Engine for Sub-Millisecond Aggregation"),
        ],
        directives: &[
            ("@agent acdso <file.csv>", "Run end-to-end ACDSO AutoML pipeline: automated data cleaning, profiling, and model training"),
            ("@agent dataanalyst <file.csv>", "Compute exploratory data analysis (EDA), kurtosis, skewness, and Pearson correlations"),
            ("@agent timeseries <file.csv>", "Multi-horizon univariate/multivariate time-series forecasting with confidence intervals"),
            ("@agent predict <target_col> on <file.csv>", "Train supervised classification or regression model to predict target column"),
            ("@agent datascience <file.csv>", "Full pipeline: data imputation, cross-validation, and feature importance ranking"),
            ("@agent decision <matrix>", "Multi-criteria decision analysis (MCDA) evaluating trade-offs across competing options"),
        ],
        examples: &[
            "@agent acdso dataset.csv",
            "@agent timeseries sales_history_2025.csv",
            "@agent dataanalyst customer_retention.csv",
            "@agent predict churn_status on telecom_users.csv",
        ],
    },
    CategoryInfo {
        menu_index: 5,
        id: "finance",
        icon: "💰",
        title: "Finance & Markets",
        subtitle: "Institutional Financial AI, Valuation, SEC Filings & Forecasting",
        overview: "9 specialized institutional financial foundation models for quantitative market analysis, SEC 10-K/10-Q filing dissection, ESG disclosures, sentiment extraction, and economic valuation without cloud leakage.",
        engines: &[
            ("Chronos-T5", "Amazon Science Zero-Shot Time-Series Forecasting"),
            ("FinBERT Suite", "ProsusAI Financial Sentiment, ESG & Managerial Tone"),
            ("FinGPT-Forecaster", "Multi-Source News, Filings & Directional Forecasting"),
            ("Llama-Fin & PatchTST", "DCF Valuation, WACC & High-Frequency Volatility"),
        ],
        directives: &[
            ("@agent finance chronos <data>", "Zero-shot probabilistic price and revenue time-series prediction"),
            ("@agent finance finbert <text>", "Extract institutional market sentiment score (-1.0 to +1.0)"),
            ("@agent finance finbert-esg <text>", "Audit corporate disclosures against SASB and TCFD ESG frameworks"),
            ("@agent finance finbert-tone <text>", "Evaluate executive management optimism vs hedging in earnings transcripts"),
            ("@agent finance fingpt <query>", "Multi-source stock movement and market forecast synthesis"),
            ("@agent finance llama-fin <data>", "Construct DCF valuation model and capital structure analysis"),
        ],
        examples: &[
            "@agent finance finbert Despite headwinds in supply chain, Q3 operating margins expanded by 180 basis points.",
            "@agent finance chronos 124.5, 126.2, 125.8, 128.4, 131.0, 129.5, 133.2",
            "@agent finance finbert-tone Management noted cautious optimism regarding European expansion.",
        ],
    },
    CategoryInfo {
        menu_index: 6,
        id: "vision",
        icon: "👁️",
        title: "Images & Vision",
        subtitle: "Computer Vision, Visual Grounding & Generative Synthesis",
        overview: "Local multi-modal computer vision suite for visual question answering (VQA), object detection, OCR, video comprehension, and generative image creation.",
        engines: &[
            ("LLaVA-1.6 / Qwen2.5-VL", "Multimodal Vision-Language Inspection & VQA"),
            ("YOLOv10 / DETR", "Real-Time Fine-Grained Object Detection"),
            ("Florence-2", "Dense Captioning, Visual Grounding & OCR"),
            ("FLUX.1-schnell / SDXL", "Latent Flow & Diffusion Photorealistic Synthesis"),
        ],
        directives: &[
            ("@agent vision <image> <prompt>", "Comprehensive visual inspection, reasoning, and scene understanding"),
            ("@agent vqa <image> <question>", "Visual question answering on technical diagrams, blueprints, and charts"),
            ("@agent object-detection <image>", "Identify and classify all visual objects with bounding box coordinates"),
            ("@agent image-classification <image>", "Categorize image into taxonomic hierarchies"),
            ("@agent image <prompt>", "Locally synthesize photorealistic or artistic images via FLUX.1 / SDXL diffusion"),
        ],
        examples: &[
            "@agent vision Describe the architecture diagram in the attached image",
            "@agent image A futuristic high-tech AI research workstation with glowing neural networks, 8k resolution",
            "@agent object-detection Identify all components on this printed circuit board",
        ],
    },
    CategoryInfo {
        menu_index: 7,
        id: "pe_binary",
        icon: "🛡️",
        title: "Inspect Windows Apps (.EXE / .DLL)",
        subtitle: "Windows Portable Executable (PECOFF) Static Binary Forensics",
        overview: "Static binary forensics of Windows x86, x64, and ARM64 PE files (.exe, .dll, .sys). Inspects DOS/NT headers, optional headers, ASLR/DEP/CFG security mitigations, import/export tables, and section entropy for packer detection.",
        engines: &[
            ("HugOS PECOFF Parser", "Native Rust Binary Header Deconstructor"),
            ("Shannon Entropy Scanner", "Statistical Byte Distribution for UPX / Packer Detection"),
            ("Authenticode Validator", "WinTrust PKCS#7 Digital Signature Verification"),
        ],
        directives: &[
            ("@agent pe <file.exe>", "Full static PE parsing: Architecture, Subsystem, ASLR/DEP/CFG, Sections, Imports"),
            ("@agent entropy <file>", "Calculate per-section Shannon entropy (0.0 to 8.0) to detect UPX, Themida, or encrypted payloads"),
            ("@agent strings <file>", "Extract ASCII/Unicode printable strings filtered for IPs, URLs, registry keys"),
            ("@agent packer-detect <file>", "Determine if binary is packed, obfuscated, or contains anti-debugging flags"),
        ],
        examples: &[
            "@agent pe C:\\Windows\\System32\\notepad.exe",
            "@agent entropy target/release/cli.exe",
            "@agent packer-detect suspicious_installer.exe",
        ],
    },
    CategoryInfo {
        menu_index: 8,
        id: "legal",
        icon: "⚖️",
        title: "Legal & Compliance",
        subtitle: "Legal Reasoning, Statutory Interpretation & Contract Understanding",
        overview: "8 specialized legal foundation models for contract clause extraction, indemnification analysis, statutory interpretation, judicial scholarship, and automated legal drafting with 100% attorney-client privilege protection.",
        engines: &[
            ("CUAD-BERT", "Clause-Level Extraction across 41 High-Risk Categories"),
            ("Saul-7B", "Mistral Architecture Leader in Statutory Reasoning & LegalBench"),
            ("Lawma-8B", "Contract Drafting, Clause Redlining & Statutory Reconciliation"),
            ("Legal-Longformer", "Deep Attention over Multi-Page Briefs & Agreements (4,096+ tokens)"),
        ],
        directives: &[
            ("@agent legal cuad-bert <contract>", "Extract all 41 high-risk legal clauses from agreements"),
            ("@agent legal saul-7b <statute/contract>", "In-depth legal reasoning, liability evaluation, and clause redlining"),
            ("@agent legal legal-bert <clause>", "Legal classification and semantic precedent matching"),
            ("@agent legal legal-longformer <brief>", "Long document legal analysis for multi-page judicial briefs"),
            ("@agent legal lawma <terms>", "Draft legally enforceable contractual covenants and clauses"),
        ],
        examples: &[
            "@agent legal cuad-bert Audit this Master Services Agreement for unilateral termination for convenience",
            "@agent legal saul-7b Analyze whether this non-compete clause is enforceable under California law",
            "@agent legal lawma Draft a mutual non-disclosure agreement with a 2-year survival term under New York law",
        ],
    },
    CategoryInfo {
        menu_index: 9,
        id: "agent",
        icon: "🧠",
        title: "Planning & Deep Thinking",
        subtitle: "Autonomous Planning, Deep Reasoning & Adversarial Verification",
        overview: "High-compute deliberation framework featuring Monte Carlo tree search, ReST-RL sub-50ms preemption, chain-of-thought verification, adversarial Grill Me interviews, and self-correcting task loops.",
        engines: &[
            ("HugOS ReST-RL Daemon", "Reinforcement Learning with Sub-50ms Preemption"),
            ("Deliberation Engine", "Qwen2.5-32B / DeepSeek-R1 Multi-Sample Reasoning"),
            ("Mutation Testing Gate", "Adversarial Code Certification (M_kill >= 0.5)"),
        ],
        directives: &[
            ("@agent boost <problem>", "Trigger deep multi-perspective reasoning deliberation with formal constraint checks"),
            ("@agent grill-me <plan>", "Adversarial requirements interview: AI interrogates user to uncover hidden edge cases"),
            ("@agent goal <autonomous_goal>", "Autonomous multi-turn agent execution loop until goal is mathematically verified"),
            ("@agent plan <architecture>", "Deconstruct complex specifications into structured, dependency-ordered milestones"),
            ("@agent cot <problem>", "Step-by-step chain-of-thought mathematical and algorithmic derivation"),
        ],
        examples: &[
            "@agent boost Design a lock-free multi-producer single-consumer ring buffer in Rust",
            "@agent grill-me I want to migrate our Postgres database to event-sourced Kafka architecture",
            "@agent plan Build a distributed Raft consensus cluster with heartbeat election timers",
        ],
    },
    CategoryInfo {
        menu_index: 10,
        id: "science",
        icon: "🔬",
        title: "Science & Discovery",
        subtitle: "Scientific Foundation Models (Biology, Chemistry, Climate & Literature)",
        overview: "20 scientific foundation models across Biology, Genomics, Chemistry, Materials Science, Climate, and Scientific Literature (ESM2, ChemBERTa, ClimaX, Prithvi, Galactica).",
        engines: &[
            ("ESM2 & ESMFold", "Protein Language Modeling & 3D Structure Folding"),
            ("ESM3 & Evo", "Generative Biology & Single-Nucleotide Genomic Modeling"),
            ("ChemBERTa & MoLFormer", "Molecular Property Prediction & Drug Screening"),
            ("Prithvi & Galactica", "Earth Observation Satellites & Scientific Paper Reasoning"),
        ],
        directives: &[
            ("@agent science esm2 <fasta>", "Protein residue contacts, evolutionary conservation, and variant prediction"),
            ("@agent science esmfold <fasta>", "Ultra-fast 3D protein structure folding and PDB coordinate output"),
            ("@agent science chemberta <smiles>", "Molecular property, solubility, and toxicity prediction"),
            ("@agent science molformer <smiles>", "High-throughput drug candidate binding affinity screening"),
            ("@agent science galactica <math/chem>", "Scientific literature reasoning and equation derivation"),
        ],
        examples: &[
            "@agent science chemberta CC(=O)OC1=CC=CC=C1C(=O)O",
            "@agent science molformer CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
            "@agent science galactica Derive the Navier-Stokes equations from the Boltzmann transport equation",
        ],
    },
    CategoryInfo {
        menu_index: 11,
        id: "sentiment",
        icon: "💖",
        title: "Sentiment & Content Moderation",
        subtitle: "Sentiment Analysis, Emotion Detection & Automated Content Moderation",
        overview: "Sentiment classification and moderation suite spanning multi-class sentiment, 28 fine-grained emotions, social media sentiment, and toxicity detection (RoBERTa, DistilBERT, Toxic-BERT, KoalaAI).",
        engines: &[
            ("RoBERTa & DistilBERT Emotion", "28-Nuanced Emotion Categories & Basic Sentiment"),
            ("DistilBERT SST-2 & Twitter-RoBERTa", "High-Speed Binary & Social Sentiment"),
            ("Toxic-BERT & KoalaAI", "Toxicity, Harassment, Hate Speech & Safety Violation Screening"),
        ],
        directives: &[
            ("@agent sentiment <text>", "Evaluate positive, negative, and emotional intensity with calibrated probabilities"),
            ("@agent moderation <text>", "Scan content for toxicity, harassment, obscenity, and safety violations"),
        ],
        examples: &[
            "@agent sentiment \"I absolutely love the new interface design! Outstanding work.\"",
            "@agent moderation \"Violent threat and abusive harassment statement\"",
        ],
    },
    CategoryInfo {
        menu_index: 12,
        id: "utilities",
        icon: "⚙️",
        title: "Utilities & System",
        subtitle: "System Telemetry, Hardware Sizing & Database Maintenance",
        overview: "Local system health monitoring, dynamic hardware RAM/VRAM resource calibration, SQLite FTS5 catalog ingestion, database integrity verification, and chat session lifecycle management.",
        engines: &[
            ("ModelFusion Master CLI", "Authoritative Rust Execution Engine (cli.exe)"),
            ("SQLite FTS5 Catalog", "Indexed Offline Database of 2M+ Models (hf_models.db)"),
            ("Dynamic Memory Calibrator", "Runtime Free RAM/VRAM Matrix (>=48GB -> 32B, >=24GB -> 14B, >=12GB -> 7B)"),
        ],
        directives: &[
            ("@agent sys-info", "Display live hardware telemetry: CPU name, cores, GPU, free VRAM, free RAM"),
            ("@agent update", "Fast curated update: indexes top ~6,500 production models across all 45 tasks"),
            ("@agent updatedb", "Full registry crawler: traverses all 2M+ models on Hugging Face Hub into SQLite"),
            ("@agent active-model", "Inspect currently loaded local Ollama model and context window"),
            ("@agent db-check", "Run low-level SQLite PRAGMA integrity checks"),
            ("@agent db-vacuum", "Reclaim disk space and defragment database storage pages"),
            ("@agent db-rebuild", "Drop and recreate the local model catalog database from scratch"),
            ("@agent db-prune", "Safely clear orphaned caches and temporary query buffers"),
            ("@agent audit-menus", "Programmatically click and audit all tool items across all 15 categories"),
        ],
        examples: &[
            "@agent sys-info",
            "@agent update",
            "@agent db-check",
            "@agent active-model",
        ],
    },
    CategoryInfo {
        menu_index: 13,
        id: "audio",
        icon: "🎙️",
        title: "Voice & Audio",
        subtitle: "Acoustic Transcription, Voice Synthesis & Sound Classification",
        overview: "Offline automatic speech recognition (ASR), neural text-to-speech (TTS), and acoustic event classification using Whisper, Piper, Kokoro, and Audio Spectrogram Transformers.",
        engines: &[
            ("OpenAI Whisper", "Multilingual Automatic Speech Recognition with Word Timestamps"),
            ("Piper / Kokoro TTS", "Real-Time Natural Voice Generation from Text"),
            ("Audio Spectrogram Transformer", "Acoustic Event & Sound Anomaly Detection"),
        ],
        directives: &[
            ("@agent asr <audio_file>", "Transcribe speech to text with precise timestamping and language detection"),
            ("@agent tts <text>", "Synthesize natural human-like voice audio from text"),
            ("@agent audio <sound_file>", "Classify environmental sounds, acoustic events, or musical genres"),
        ],
        examples: &[
            "@agent asr meeting_recording.mp3",
            "@agent tts Welcome to HugOS, your sovereign local AI environment.",
            "@agent audio pump_vibration_sample.wav",
        ],
    },
    CategoryInfo {
        menu_index: 14,
        id: "web",
        icon: "🌐",
        title: "Web Research & Automation",
        subtitle: "Grounded Live Search, arXiv Research & WikiSkill Distillation",
        overview: "Dual-source deep web and academic research engine, grounded citation synthesis, live Wikipedia knowledge distillation (WikiSkill), Set-of-Mark visual markers, and browser automation.",
        engines: &[
            ("Live Web Search Proxy", "Grounded Web Search with Source Footnotes"),
            ("arXiv API Engine", "Academic Literature Pipeline for Preprints & Citations"),
            ("WikiSkill Distillation", "Wikipedia REST Knowledge Synthesis"),
            ("Chrome DevTools Viewport", "CDP Automation Harness for Live DOM & Navigation"),
        ],
        directives: &[
            ("@agent search <query>", "Grounded web search with source footnotes and synthesized takeaways"),
            ("@agent arxiv <query>", "Search academic papers, preprints, and citation metadata on arXiv"),
            ("@agent wiki <topic>", "Distill Wikipedia article with key takeaways, deep sections, and cross-references"),
            ("@agent browser <url>", "Navigate internal HugOS browser viewport to specified web page"),
            ("@agent markers", "Inject numbered Set-of-Mark visual bounding markers onto web page controls"),
        ],
        examples: &[
            "@agent search latest quantum computing milestones 2026",
            "@agent arxiv mixture of agents speculative decoding",
            "@agent wiki CRISPR gene editing",
            "@agent browser https://en.wikipedia.org",
        ],
    },
    CategoryInfo {
        menu_index: 15,
        id: "writing",
        icon: "✍️",
        title: "Writing & Editing",
        subtitle: "Anti-AI Stylometry, Token Watermark Detection & Translation",
        overview: "Humanization of AI prose with anti-AI stylometry, statistical token watermark detection (Kirchenbauer et al.), multilingual neural translation, and outline pacing workspace.",
        engines: &[
            ("Anti-AI Stylometry Engine", "Entropy & Burstiness Optimizer for Natural Prose"),
            ("Dual Watermark Scanner", "Kirchenbauer Z-Score (Text) & Spatial LSB (Images)"),
            ("NLLB Multilingual Engine", "Neural Translation across 100+ Languages"),
            ("Outline Pacing Workspace", "Manuscript Architecture with Grounded Pacing Targets"),
        ],
        directives: &[
            ("@agent humanize <text/file>", "Rewrite AI-generated text into natural, varied human prose that bypasses AI detectors"),
            ("@agent watermark <text/file/image>", "Detect statistical token distribution watermarks (text) or spatial LSB artifacts (images)"),
            ("@agent translate to <language>: <text/file>", "High-fidelity multilingual translation with automatic language detection"),
            ("@agent style-transfer to <style>: <text>", "Shift voice and tone (conversational, academic, journalistic, executive)"),
            ("@agent outline <topic/book>", "Launch the Writing Outline & Chapter Pacing Workspace"),
        ],
        examples: &[
            "@agent humanize In today's digital era, artificial intelligence plays an indispensable role in modern society.",
            "@agent watermark Check this paragraph for synthetic AI green-list watermarking patterns.",
            "@agent translate to Spanish: Welcome to our local AI browser. All data stays on your machine.",
        ],
    },
];

// -----------------------------------------------------------------------------
// Catalog of Specific Foundation Model Cards
// -----------------------------------------------------------------------------
pub static MODEL_CARDS: &[ModelCard] = &[
    ModelCard {
        id: "deberta-v3",
        name: "DeBERTa-v3 Natural Language Inference Suite",
        category: "classification",
        menu_index: 1,
        icon: "🔀",
        author: "Microsoft Research / Moritz Laurer (cross-encoder/nli-deberta-v3-base)",
        architecture: "DeBERTa-v3 with Disentangled Attention and Enhanced Masked Language Modeling",
        purpose: "Built on DeBERTa-v3 and trained on MNLI, FEVER, and ANLI, offering significantly higher precision and sharper semantic boundary detection than older BART checkpoints. Resilient to complex sentence structures and subtle negations in zero-shot classification.",
        input_format: "Premise text and hypothesis or candidate labels.",
        sample_input: "Although the drug demonstrated efficacy in vitro, clinical trials failed to reproduce statistically significant improvements.",
        options: &[
            ("--labels <l1, l2, ...>", "Target candidate classification labels to evaluate against premise"),
            ("--threshold <0.0-1.0>", "Softmax/sigmoid entailment confidence cutoff threshold (default: 0.5)"),
            ("--multi-label", "Allow multiple candidate labels to be entailed simultaneously"),
        ],
        directives: &[
            ("@agent classify nli-deberta-v3-base <text>", "High-precision cross-encoder zero-shot classification"),
            ("@agent classify deberta-v3-base-mnli-fever-anli <text>", "Fact verification and adversarial NLI entailment scoring"),
        ],
        examples: &[
            "@agent classify nli-deberta-v3-base \"The quarterly results beat expectations\" candidate labels: earnings, tech, health",
            "@agent classify nli-deberta-v3-base The server never crashed despite the denial of service attempt candidate labels: resilient, vulnerable, crashed",
            "@agent classify deberta-v3-base-mnli-fever-anli Climate models predict warming trends across the Arctic candidate labels: climate change, fictional narrative",
            "cli.exe --tool-help \"classify nli-deberta-v3-base\"",
        ],
        related: &["bart-large-mnli", "distilbart-mnli", "longformer-base-4096"],
    },
    ModelCard {
        id: "bart-large-mnli",
        name: "BART-Large MNLI Zero-Shot Classifier",
        category: "classification",
        menu_index: 1,
        icon: "🎯",
        author: "Meta AI / Hugging Face (facebook/bart-large-mnli)",
        architecture: "BART Encoder-Decoder (407M params) fine-tuned on MultiNLI",
        purpose: "The standard benchmark for zero-shot text classification, fine-tuned on MultiNLI to determine whether a given premise text entails, contradicts, or remains neutral toward arbitrary candidate labels formulated as hypotheses.",
        input_format: "Text to classify followed by candidate labels (or --labels label1, label2, ...).",
        sample_input: "Apple unveiled its latest M4 workstation processor with unified memory architecture. candidate labels: technology, sports, culinary, politics",
        options: &[
            ("--labels <l1, l2, ...>", "Comma-separated candidate labels to score against premise"),
            ("--multi-label", "Allow multiple candidate labels to be true simultaneously"),
        ],
        directives: &[
            ("@agent classify bart-large-mnli <text> candidate labels: <l1, l2>", "Zero-shot classification ranking candidate labels with softmax entailment probabilities"),
            ("@agent zero-shot <text> --labels <l1, l2>", "Evaluate candidate hypotheses with multi-class inference"),
        ],
        examples: &[
            "@agent classify bart-large-mnli The central bank raised interest rates by 25 basis points candidate labels: finance, weather, sports",
            "@agent zero-shot \"The package arrived damaged and two days late\" --labels shipping issue, billing inquiry, technical support",
            "cli.exe --tool-help bart-large-mnli",
        ],
        related: &["deberta-v3", "distilbart-mnli", "longformer"],
    },
    ModelCard {
        id: "distilbart-mnli",
        name: "DistilBART MNLI High-Throughput Classifier",
        category: "classification",
        menu_index: 1,
        icon: "⚡",
        author: "Valhalla / Hugging Face Community (valhalla/distilbart-mnli-12-3)",
        architecture: "DistilBART-12-3 (Distilled BART student with 60% fewer parameters)",
        purpose: "A distilled, lightweight alternative designed for high-throughput zero-shot classification where inference speed and memory footprint are the primary constraints. Retains over 90% of full BART-Large MNLI accuracy at 2.5x inference speed.",
        input_format: "Text passage and candidate classification categories.",
        sample_input: "The database connection pool reached maximum capacity and threw connection timeout exceptions.",
        options: &[
            ("--labels <l1, l2, ...>", "Candidate categories"),
            ("--threshold <0.0-1.0>", "Confidence cutoff threshold"),
        ],
        directives: &[
            ("@agent classify distilbart-mnli-12-3 <text>", "Ultra-low latency zero-shot classification for edge and streaming pipelines"),
        ],
        examples: &[
            "@agent classify distilbart-mnli-12-3 Connection pool timeout on node 4 candidate labels: database error, network failure, user error",
            "cli.exe --tool-help distilbart-mnli",
        ],
        related: &["bart-large-mnli", "distilbert-sst2"],
    },
    ModelCard {
        id: "saul-7b",
        name: "Saul-7B Legal Reasoning Foundation Model",
        category: "legal",
        menu_index: 8,
        icon: "⚖️",
        author: "Equall / Mistral Architecture (Equall/Saul-7B-Instruct)",
        architecture: "Mistral-7B Architecture fine-tuned on LegalBench and 30B+ legal tokens",
        purpose: "State-of-the-art open legal LLM leading LegalBench benchmarks for statutory interpretation, contract clause analysis, compliance review, and legal scholarship. Provides in-depth legal reasoning with 100% offline data sovereignty.",
        input_format: "Contract agreements, statutory clauses, judicial filings, or legal questions.",
        sample_input: "Analyze whether this non-compete clause with a 24-month duration across all 50 states is enforceable under California law.",
        options: &[
            ("--jurisdiction <state/country>", "Applicable legal jurisdiction (e.g. California, Delaware, New York, UK, EU)"),
            ("--detail <summary|full>", "Level of analytical depth and statutory citations"),
        ],
        directives: &[
            ("@agent legal saul-7b <statute/contract>", "Comprehensive statutory analysis, enforceability review, and liability assessment"),
            ("@agent legal saul-7b redline <clause>", "Suggest legally enforceable alternative contract language"),
        ],
        examples: &[
            "@agent legal saul-7b Analyze enforceability of non-compete clause under California Business and Professions Code 16600",
            "@agent legal saul-7b redline Limitation of liability clause to cap damages at 12 months fees",
            "cli.exe --tool-help \"legal saul-7b\"",
        ],
        related: &["cuad-bert", "lawma-8b", "legal-longformer", "legal-bert"],
    },
    ModelCard {
        id: "cuad-bert",
        name: "CUAD-BERT Contract Understanding & Clause Extractor",
        category: "legal",
        menu_index: 8,
        icon: "📜",
        author: "The Atticus Project (TheAtticusProject/cuad-bert-base)",
        architecture: "BERT-Base fine-tuned on the Contract Understanding Atticus Dataset (CUAD)",
        purpose: "Specialized clause extraction model trained across 510 commercial contracts to extract 41 critical high-risk legal clauses (indemnification, limitation of liability, non-compete, change of control, governing law, termination for convenience).",
        input_format: "Full commercial contracts (.docx, .pdf, or plain text).",
        sample_input: "Audit attached Master Services Agreement for unilateral termination rights and non-standard indemnification covenants.",
        options: &[
            ("--clauses <all|liability|termination>", "Filter specific clause types to inspect"),
            ("--threshold <0.0-1.0>", "Probability confidence threshold for clause detection"),
        ],
        directives: &[
            ("@agent legal cuad-bert <contract>", "Extract and catalog all 41 high-risk contract clauses with start/end byte offsets"),
        ],
        examples: &[
            "@agent legal cuad-bert Audit this Master Services Agreement for limitation of liability caps",
            "@agent legal cuad-bert Check if this NDA contains an IP assignment covenant",
            "cli.exe --tool-help cuad-bert",
        ],
        related: &["saul-7b", "legal-longformer", "lawma-8b"],
    },
    ModelCard {
        id: "distilbert-emotion",
        name: "DistilBERT 6-Emotion Classifier",
        category: "sentiment",
        menu_index: 11,
        icon: "💖",
        author: "Bhadresh Psavani (bhadresh-psavani/distilbert-base-uncased-emotion)",
        architecture: "DistilBERT-Base fine-tuned on the Emotion dataset",
        purpose: "High-speed conversational emotion recognition predicting 6 foundational emotional states: Joy, Sadness, Anger, Fear, Love, and Surprise with calibrated probability distributions.",
        input_format: "Customer feedback, social media posts, chat transcripts, or user reviews.",
        sample_input: "I can't believe how smoothly the upgrade process went! Truly impressed with the engineering quality.",
        options: &[
            ("--threshold <0.0-1.0>", "Confidence cutoff threshold (default: 0.4)"),
            ("--format <json|table>", "Output formatting style"),
        ],
        directives: &[
            ("@agent sentiment distilbert-base-uncased-emotion <text>", "Predict fine-grained emotion distribution with softmax scores"),
        ],
        examples: &[
            "@agent sentiment distilbert-base-uncased-emotion \"I am thrilled by the performance improvements in the new release!\"",
            "@agent sentiment distilbert-base-uncased-emotion \"I've been waiting for three days with zero response from support.\"",
            "cli.exe --tool-help \"sentiment distilbert-base-uncased-emotion\"",
        ],
        related: &["go-emotions", "distilbert-sst2", "twitter-roberta", "toxic-bert"],
    },
    ModelCard {
        id: "chemberta",
        name: "ChemBERTa Molecular Property Transformer",
        category: "science",
        menu_index: 10,
        icon: "🧪",
        author: "DeepChem (DeepChem/ChemBERTa-77M-MTR)",
        architecture: "RoBERTa Architecture pre-trained on 77M+ SMILES chemical strings",
        purpose: "Molecular representation and property prediction transformer. Evaluates chemical SMILES notations to predict aqueous solubility, blood-brain barrier permeability (BBBP), clinical toxicity, and binding affinities for drug discovery.",
        input_format: "SMILES or SELFIES chemical strings.",
        sample_input: "CC(=O)OC1=CC=CC=C1C(=O)O (Aspirin / Acetylsalicylic acid)",
        options: &[
            ("--property <solubility|toxicity|bbbp>", "Target chemical property to predict"),
        ],
        directives: &[
            ("@agent science chemberta <smiles>", "Predict molecular properties, solubility, and toxicity from SMILES representation"),
        ],
        examples: &[
            "@agent science chemberta CC(=O)OC1=CC=CC=C1C(=O)O",
            "@agent science chemberta CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
            "cli.exe --tool-help chemberta",
        ],
        related: &["molformer", "esm2", "esmfold", "galactica"],
    },
    ModelCard {
        id: "esm2",
        name: "ESM2 Evolutionary Scale Protein Language Model",
        category: "science",
        menu_index: 10,
        icon: "🧬",
        author: "Meta AI / Fundamental AI Research (facebook/esm2_t33_650M_UR50D)",
        architecture: "Transformer with Rotary Position Embeddings trained on UniRef50 (650M params)",
        purpose: "State-of-the-art biological foundation model understanding protein evolution, residue contact maps, mutation fitness effects, and secondary structure from amino acid sequences.",
        input_format: "FASTA amino acid sequence strings.",
        sample_input: "MSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDATYGKLTLKFICTTGKLPVPWPTLVTTFSYGVQCFSRYPDHMKQHDFFKSAMPEGYVQERTIFFKDDGNYKTRAEVKFEGDTLVNRIELKGIDFKEDGNILGHKLEYNYNSHNVYIMADKQKNGIKVNFKIRHNIEDGSVQLADHYQQNTPIGDGPVLLPDNHYLSTQSALSKDPNEKRDHMVLLEFVTAAGITHGMDELYK",
        options: &[
            ("--contacts", "Predict residue-residue contact map"),
            ("--mutation <pos,orig,mut>", "Predict fitness effect of specific amino acid substitution"),
        ],
        directives: &[
            ("@agent science esm2 <fasta>", "Extract protein residue embeddings and evolutionary conservation scores"),
            ("@agent science esmfold <fasta>", "Fold sequence into 3D atomic coordinates (PDB file output)"),
        ],
        examples: &[
            "@agent science esm2 MSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDATYGKLTLKFICTTGKLPVPWPTLVTTFSYGVQCFSRYPDHMKQHDFFKSAMPEGYVQERTIFFKDDGNYKTRAEVKFEGDTLVNRIELKGIDFKEDGNILGHKLEYNYNSHNVYIMADKQKNGIKVNFKIRHNIEDGSVQLADHYQQNTPIGDGPVLLPDNHYLSTQSALSKDPNEKRDHMVLLEFVTAAGITHGMDELYK",
            "cli.exe --tool-help esm2",
        ],
        related: &["esmfold", "esm3", "chemberta", "molformer"],
    },
];

// -----------------------------------------------------------------------------
// Catalog of Specific Tool Cards
// -----------------------------------------------------------------------------
pub static TOOL_CARDS: &[ToolCard] = &[
    ToolCard {
        id: "classify",
        name: "Zero-Shot Cross-Encoder NLI Classifier",
        category: "classification",
        menu_index: 1,
        icon: "🏷️",
        architecture: "DeBERTa-v3 / BART-Large MNLI Natural Language Inference",
        purpose: "Perform high-precision zero-shot classification and multi-label premise-hypothesis entailment scoring without requiring fine-tuning.",
        input_format: "Text passage followed by candidate labels (e.g. \"Text\" candidate labels: label1, label2, ... or --labels l1, l2).",
        options: &[
            ("--labels <l1, l2, ...>", "Comma-separated candidate labels to score against premise"),
            ("--multi-label", "Allow multiple labels to be true simultaneously (sigmoid scoring)"),
            ("--threshold <0.0-1.0>", "Confidence threshold cutoff (default: 0.5)"),
        ],
        directives: &[
            ("@agent classify <model> \"<text>\" candidate labels: <l1, l2>", "Zero-shot classification ranking candidate labels"),
            ("@agent classify nli-deberta-v3-base \"<text>\" candidate labels: <l1, l2>", "High-precision DeBERTa-v3 NLI zero-shot classification"),
        ],
        examples: &[
            "@agent classify nli-deberta-v3-base \"The quarterly results beat expectations\" candidate labels: earnings, tech, health",
            "@agent classify nli-deberta-v3-base \"This product broke immediately\" candidate labels: hardware, billing, support",
            "@agent classify bart-large-mnli The central bank raised interest rates candidate labels: finance, weather, sports",
            "cli.exe --tool-help classify",
        ],
        related: &["zero-shot", "topic", "deberta-v3", "bart-large-mnli"],
    },
    ToolCard {
        id: "zero-shot",
        name: "Zero-Shot NLI Entailment Evaluator",
        category: "classification",
        menu_index: 1,
        icon: "🎯",
        architecture: "Natural Language Inference Cross-Encoder",
        purpose: "Classify arbitrary passages into dynamic candidate classes using NLI entailment probabilities.",
        input_format: "Text passage with --labels <label1, label2, ...>",
        options: &[
            ("--labels <l1, l2, ...>", "Candidate classes to test as hypotheses"),
        ],
        directives: &[
            ("@agent zero-shot \"<text>\" --labels <l1, l2>", "Evaluate candidate hypotheses with multi-class inference"),
        ],
        examples: &[
            "@agent zero-shot \"This product broke after two days\" --labels hardware, customer service, billing",
            "@agent zero-shot \"The server never crashed despite the DDoS attempt\" --labels resilient, vulnerable, crashed",
            "cli.exe --tool-help zero-shot",
        ],
        related: &["classify", "topic", "deberta-v3"],
    },
    ToolCard {
        id: "topic",
        name: "Longformer Document Topic Categorizer",
        category: "classification",
        menu_index: 1,
        icon: "📜",
        architecture: "Longformer-Base-4096 (Local + Global Dilated Attention)",
        purpose: "Classify lengthy multi-page documents, PDFs, or RFCs up to 4,096 tokens into hierarchical subject taxonomies.",
        input_format: "Multi-page document text or file path.",
        options: &[
            ("--file <path>", "Path to text, PDF, or markdown document"),
        ],
        directives: &[
            ("@agent topic longformer-base-4096 <document_content>", "Classify full document without truncation"),
        ],
        examples: &[
            "@agent topic longformer-base-4096 [Full text of research paper discussing quantum annealing algorithms]",
            "cli.exe --tool-help topic",
        ],
        related: &["classify", "longformer-base-4096"],
    },
    ToolCard {
        id: "security",
        name: "Static Application Security Testing (SAST)",
        category: "code",
        menu_index: 2,
        icon: "🛡️",
        architecture: "Tree-Sitter AST & OWASP Heuristic Engine",
        purpose: "Deep static vulnerability discovery auditing source code against OWASP Top 10 vulnerabilities (buffer overflows, SQL injection, use-after-free, unsafe blocks).",
        input_format: "Source code file path or inline code block.",
        options: &[
            ("--file <path>", "Path to source code file (.rs, .py, .ts, .go, .c, .cpp)"),
            ("--severity <high|all>", "Filter vulnerabilities by minimum severity"),
        ],
        directives: &[
            ("@agent security <code/file>", "Full SAST security audit for buffer overflows, memory safety, and injections"),
        ],
        examples: &[
            "@agent security fn authenticate(user: &str, pass: &str) -> bool { ... }",
            "@agent security --file crates/cli/src/main.rs",
            "cli.exe --tool-help security",
        ],
        related: &["vuln-scan", "secret-scan", "pii-scan", "graph-index"],
    },
    ToolCard {
        id: "graph-index",
        name: "Code Architecture Dependency Graph Indexer",
        category: "code",
        menu_index: 2,
        icon: "🕸️",
        architecture: "Tree-Sitter AST & Call-Graph Engine",
        purpose: "Build full abstract syntax tree and call-graph architecture dependency maps across polyglot repositories.",
        input_format: "Path to project folder or module directory.",
        options: &[
            ("--depth <N>", "Maximum call-graph traversal depth"),
            ("--format <json|dot|mermaid>", "Output graph visualization format"),
        ],
        directives: &[
            ("@agent graph-index <directory>", "Parse directory and index symbol call-graphs and dependencies"),
        ],
        examples: &[
            "@agent graph-index crates/cli/src",
            "@agent graph-index browser/ui",
            "cli.exe --tool-help graph-index",
        ],
        related: &["security", "api-docs"],
    },
    ToolCard {
        id: "vuln-scan",
        name: "Deep Memory & Logic Vulnerability Scanner",
        category: "code",
        menu_index: 2,
        icon: "🔍",
        architecture: "Tree-Sitter Grammar & Memory Safety Analyzer",
        purpose: "Targeted static audit checking for memory corruption, use-after-free, unvalidated input sanitization, and unsafe pointers.",
        input_format: "File path or code snippet.",
        options: &[
            ("--file <path>", "Target code file"),
        ],
        directives: &[
            ("@agent vuln-scan <file>", "Audit file for memory safety and logic exploits"),
        ],
        examples: &[
            "@agent vuln-scan src/network/parser.c",
            "cli.exe --tool-help vuln-scan",
        ],
        related: &["security", "secret-scan"],
    },
    ToolCard {
        id: "secret-scan",
        name: "Secret & Credential Leak Scanner",
        category: "code",
        menu_index: 2,
        icon: "🔑",
        architecture: "Regex Pattern & Shannon Entropy Scanner",
        purpose: "Discover committed API keys, tokens, RSA private keys, passwords, and connection strings before pushing code.",
        input_format: "File path, repository directory, or configuration file.",
        options: &[
            ("--file <path>", "File to inspect for secrets"),
            ("--repo <path>", "Scan entire repository recursively"),
        ],
        directives: &[
            ("@agent secret-scan <file/repo>", "Scan for leaked API tokens, certificates, and secrets"),
        ],
        examples: &[
            "@agent secret-scan config/settings.json",
            "@agent secret-scan --repo .",
            "cli.exe --tool-help secret-scan",
        ],
        related: &["pii-scan", "security"],
    },
    ToolCard {
        id: "pii-scan",
        name: "Confidential Personally Identifiable Information (PII) Scanner",
        category: "code",
        menu_index: 2,
        icon: "🕵️",
        architecture: "Heuristic Pattern & Luhn Algorithm Validator",
        purpose: "Discover leaked SSNs, credit card numbers, email addresses, phone numbers, and identity data in source code and databases.",
        input_format: "Text passage, dataset, or file path.",
        options: &[
            ("--file <path>", "Path to data file or log file"),
        ],
        directives: &[
            ("@agent pii-scan <text/file>", "Scan content for leaked private customer identity data"),
        ],
        examples: &[
            "@agent pii-scan logs/customer_dump.csv",
            "cli.exe --tool-help pii-scan",
        ],
        related: &["secret-scan", "security"],
    },
    ToolCard {
        id: "code-translate",
        name: "Polyglot AST-Preserving Code Transpiler",
        category: "code",
        menu_index: 2,
        icon: "🔄",
        architecture: "AST Parser & Local Coder LLM",
        purpose: "Transpile code across Rust, Python, Go, TypeScript, C++, and C# while preserving semantic types and error handling.",
        input_format: "Source language code with target language directive.",
        options: &[
            ("--to <lang>", "Target programming language (e.g. Rust, Python, Go, TypeScript, C++)"),
        ],
        directives: &[
            ("@agent code-translate to <lang>: <code>", "Translate code snippet to target language"),
        ],
        examples: &[
            "@agent code-translate to Rust: function fib(n) { return n <= 1 ? n : fib(n-1) + fib(n-2); }",
            "@agent code-translate to Go: def fetch_records(limit: int) -> list: ...",
            "cli.exe --tool-help code-translate",
        ],
        related: &["security", "api-docs", "dockerfile"],
    },
    ToolCard {
        id: "dockerfile",
        name: "Minimal Multi-Stage Dockerfile Synthesizer",
        category: "code",
        menu_index: 2,
        icon: "🐳",
        architecture: "Container Hardening Engine",
        purpose: "Synthesize minimal attack-surface, multi-stage production Dockerfiles with non-root security baselines.",
        input_format: "Path to project root or description of application stack.",
        options: &[
            ("--base <alpine|distroless|debian>", "Target base image style"),
        ],
        directives: &[
            ("@agent dockerfile <path>", "Generate hardened multi-stage Dockerfile"),
        ],
        examples: &[
            "@agent dockerfile crates/cli",
            "cli.exe --tool-help dockerfile",
        ],
        related: &["security", "api-docs"],
    },
    ToolCard {
        id: "api-docs",
        name: "OpenAPI Specification & Documentation Generator",
        category: "code",
        menu_index: 2,
        icon: "📑",
        architecture: "AST Symbol Extractor & Doc Synthesizer",
        purpose: "Generate OpenAPI 3.0 specs, Swagger JSON, and markdown documentation directly from backend route definitions.",
        input_format: "Backend router file or source directory.",
        options: &[
            ("--format <openapi|markdown>", "Output documentation format"),
        ],
        directives: &[
            ("@agent api-docs <code>", "Synthesize OpenAPI 3.0 specification from endpoints"),
        ],
        examples: &[
            "@agent api-docs src/routes/user.rs",
            "cli.exe --tool-help api-docs",
        ],
        related: &["graph-index", "code-translate"],
    },
    ToolCard {
        id: "computer-use",
        name: "Autonomous Computer Use & OS Navigation",
        category: "computer_use",
        menu_index: 3,
        icon: "🖱️",
        architecture: "UI-TARS Multimodal Perception-Action Loop (ByteDance)",
        purpose: "Autonomous OS desktop control and GUI automation via visual grounding, mouse clicks, keyboard typing, and window navigation.",
        input_format: "Natural language goal describing desktop task.",
        options: &[
            ("--goal <task>", "Autonomous desktop task description"),
            ("--max-steps <N>", "Maximum sequential action steps (default: 25)"),
        ],
        directives: &[
            ("@agent computer-use <task>", "Execute autonomous desktop control loop until task completes"),
            ("cli.exe --computer-use \"<task>\"", "Launch direct CLI desktop control execution"),
        ],
        examples: &[
            "@agent computer-use Open Notepad and write a project status report",
            "@agent computer-use Open browser, navigate to github.com, and check notifications",
            "cli.exe --computer-use \"Open Calculator and compute 128 * 64\"",
            "cli.exe --tool-help computer-use",
        ],
        related: &["ui-tars", "screen-grounding", "desktop-click", "desktop-type", "desktop-scroll"],
    },
    ToolCard {
        id: "ui-tars",
        name: "UI-TARS Multimodal Perception-Action Loop",
        category: "computer_use",
        menu_index: 3,
        icon: "🤖",
        architecture: "UI-TARS 7B/72B Vision-Language GUI Agent",
        purpose: "End-to-end desktop perception, reasoning, and OS action sequence generation with sub-50ms preemption.",
        input_format: "Natural language goal or interactive GUI task.",
        options: &[
            ("--temperature <0.0-1.0>", "Action sampling temperature"),
        ],
        directives: &[
            ("@agent ui-tars <goal>", "Execute UI-TARS action loop with sub-50ms preemption"),
        ],
        examples: &[
            "@agent ui-tars Navigate to Settings and toggle dark mode",
            "cli.exe --tool-help ui-tars",
        ],
        related: &["computer-use", "screen-grounding"],
    },
    ToolCard {
        id: "screen-grounding",
        name: "Screen Perception & Element Grounding",
        category: "computer_use",
        menu_index: 3,
        icon: "🎯",
        architecture: "Set-of-Mark (SoM) Visual Coordinate Grounding",
        purpose: "Capture desktop screen and assign numbered Set-of-Mark bounding badges to all interactive controls, buttons, and inputs.",
        input_format: "Viewport or full desktop screen.",
        options: &[
            ("--monitor <N>", "Target display monitor index (0, 1, 2)"),
        ],
        directives: &[
            ("@agent screen-grounding", "Perceive active screen and ground interactive UI elements"),
        ],
        examples: &[
            "@agent screen-grounding",
            "cli.exe --tool-help screen-grounding",
        ],
        related: &["computer-use", "som", "desktop-click"],
    },
    ToolCard {
        id: "desktop-click",
        name: "Hardware Mouse Click Simulator",
        category: "computer_use",
        menu_index: 3,
        icon: "👆",
        architecture: "Win32 SendInput Event Dispatcher",
        purpose: "Simulate hardware mouse click at specified viewport or screen coordinate [x, y].",
        input_format: "Screen coordinates x, y (e.g. 450, 320).",
        options: &[
            ("--button <left|right|middle>", "Mouse button to click (default: left)"),
            ("--double", "Execute double-click"),
        ],
        directives: &[
            ("@agent desktop-click <x,y>", "Simulate hardware mouse click at coordinates"),
        ],
        examples: &[
            "@agent desktop-click 450, 320",
            "@agent desktop-click 1920, 1080",
            "cli.exe --tool-help desktop-click",
        ],
        related: &["desktop-type", "desktop-scroll", "computer-use"],
    },
    ToolCard {
        id: "desktop-type",
        name: "Hardware Keyboard Typing Simulator",
        category: "computer_use",
        menu_index: 3,
        icon: "⌨️",
        architecture: "Win32 SendInput Keyboard Dispatcher",
        purpose: "Send verified keystrokes, text strings, or hotkey combinations to the active window.",
        input_format: "Text string to type or hotkey sequence (e.g. ctrl+s).",
        options: &[
            ("--delay-ms <N>", "Inter-keystroke delay in milliseconds (default: 15)"),
        ],
        directives: &[
            ("@agent desktop-type <text>", "Send keyboard strokes or hotkeys to active window"),
        ],
        examples: &[
            "@agent desktop-type \"git status\"",
            "@agent desktop-type ctrl+shift+p",
            "cli.exe --tool-help desktop-type",
        ],
        related: &["desktop-click", "desktop-scroll", "computer-use"],
    },
    ToolCard {
        id: "desktop-scroll",
        name: "Mouse Wheel Scroll Dispatcher",
        category: "computer_use",
        menu_index: 3,
        icon: "📜",
        architecture: "Win32 SendInput Mouse Wheel Dispatcher",
        purpose: "Dispatch vertical or horizontal mouse wheel scroll event on active window.",
        input_format: "Scroll delta integer (positive = scroll down, negative = scroll up).",
        options: &[
            ("--horizontal", "Perform horizontal scroll instead of vertical"),
        ],
        directives: &[
            ("@agent desktop-scroll <delta>", "Dispatch mouse wheel scroll"),
        ],
        examples: &[
            "@agent desktop-scroll 300",
            "@agent desktop-scroll -500",
            "cli.exe --tool-help desktop-scroll",
        ],
        related: &["desktop-click", "desktop-type", "computer-use"],
    },
    ToolCard {
        id: "shopping",
        name: "E-Commerce Shopping Assistant",
        category: "computer_use",
        menu_index: 3,
        icon: "🛒",
        architecture: "UI-TARS & E-Commerce Grounding Engine",
        purpose: "Automate e-commerce product search, price comparison, specification extraction, and cart checkout with safety gate.",
        input_format: "Product name or search parameters.",
        options: &[
            ("--max-price <USD>", "Price ceiling threshold"),
        ],
        directives: &[
            ("@agent shopping <item>", "Discover products and compare prices with e-commerce safety gate"),
        ],
        examples: &[
            "@agent shopping Find best price for 32GB DDR5 SODIMM laptop RAM",
            "@agent shopping Ergonomic mechanical split keyboard under $150",
            "cli.exe --tool-help shopping",
        ],
        related: &["computer-use", "ticket-booking"],
    },
    ToolCard {
        id: "ticket-booking",
        name: "Flight & Event Ticket Booking Assistant",
        category: "computer_use",
        menu_index: 3,
        icon: "✈️",
        architecture: "Travel Route Grounding & Booking Gate",
        purpose: "Automate airline, rail, or event reservation search, schedule comparison, and seat selection with confirmation gate.",
        input_format: "Origin, destination, dates, and passenger details.",
        options: &[
            ("--tier <Economy|Business>", "Preferred seating tier"),
        ],
        directives: &[
            ("@agent ticket-booking <details>", "Search and ground ticket options with booking safety gate"),
        ],
        examples: &[
            "@agent ticket-booking Find one-way flight from JFK to LHR on November 15",
            "@agent ticket-booking Train tickets from Paris to Zurich next Monday morning",
            "cli.exe --tool-help ticket-booking",
        ],
        related: &["shopping", "map-directions", "computer-use"],
    },
    ToolCard {
        id: "exam-solver",
        name: "Visual Exam & Quiz Solver",
        category: "computer_use",
        menu_index: 3,
        icon: "📝",
        architecture: "Multimodal Question Grounding & HITL Gate",
        purpose: "Inspect active web page and solve multi-choice exam questions, figures, and charts with human-in-the-loop validation.",
        input_format: "Exam web URL or active page questions.",
        options: &[
            ("--auto-advance", "Automatically advance to next question after confirmation"),
        ],
        directives: &[
            ("@agent exam-solver <url/exam>", "Inspect active page and solve exam questions with HITL validation"),
        ],
        examples: &[
            "@agent exam-solver Inspect and solve questions on active page",
            "@agent exam-solver https://tests.com/sample-exam",
            "cli.exe --tool-help exam-solver",
        ],
        related: &["computer-use", "vqa"],
    },
    ToolCard {
        id: "map-directions",
        name: "GIS Map Directions & Route Planner",
        category: "computer_use",
        menu_index: 3,
        icon: "🗺️",
        architecture: "GIS Navigation & Waypoint Calculator",
        purpose: "Compute turn-by-turn map directions, transit routes, and travel time across mapping applications.",
        input_format: "Origin and destination locations.",
        options: &[
            ("--mode <driving|transit|walking>", "Travel modality"),
        ],
        directives: &[
            ("@agent map-directions <route>", "Compute turn-by-turn map directions and transit routes"),
        ],
        examples: &[
            "@agent map-directions Directions from Times Square to Central Park Zoo",
            "@agent map-directions Fastest route from SFO to San Jose Downtown during rush hour",
            "cli.exe --tool-help map-directions",
        ],
        related: &["ticket-booking", "computer-use"],
    },
    ToolCard {
        id: "acdso",
        name: "Adaptive Contextual Data Science Optimization (ACDSO)",
        category: "tabular",
        menu_index: 4,
        icon: "📊",
        architecture: "ACDSO Automated Feature Synthesis & Model Selection",
        purpose: "End-to-end automated data cleaning, profiling, feature selection, and supervised model training on tabular data.",
        input_format: "CSV (.csv), TSV (.tsv), Excel (.xlsx), or Parquet (.parquet) files.",
        options: &[
            ("--file <path>", "Dataset file path"),
            ("--target <col>", "Target column name for supervised prediction"),
        ],
        directives: &[
            ("@agent acdso <file.csv>", "Run end-to-end ACDSO AutoML pipeline on tabular dataset"),
            ("cli.exe --acdso --file <path>", "Execute ACDSO via CLI"),
        ],
        examples: &[
            "@agent acdso dataset.csv",
            "@agent acdso sales_2025.csv --target revenue",
            "cli.exe --acdso --file data/housing.csv",
            "cli.exe --tool-help acdso",
        ],
        related: &["dataanalyst", "timeseries", "predict", "datascience"],
    },
    ToolCard {
        id: "dataanalyst",
        name: "Exploratory Data Analysis (EDA) Profiler",
        category: "tabular",
        menu_index: 4,
        icon: "📈",
        architecture: "DuckDB & Polars High-Throughput Statistics",
        purpose: "Compute distribution statistics, kurtosis, skewness, missing values, and Pearson correlation matrices.",
        input_format: "Dataset file path or tabular text.",
        options: &[
            ("--file <path>", "Dataset file to analyze"),
        ],
        directives: &[
            ("@agent dataanalyst <file.csv>", "Compute comprehensive exploratory data analysis"),
        ],
        examples: &[
            "@agent dataanalyst customer_retention.csv",
            "cli.exe --tool-help dataanalyst",
        ],
        related: &["acdso", "timeseries", "predict"],
    },
    ToolCard {
        id: "timeseries",
        name: "Multi-Horizon Time-Series Forecaster",
        category: "tabular",
        menu_index: 4,
        icon: "⏳",
        architecture: "PatchTST & Chronos Time-Series Transformers",
        purpose: "Probabilistic univariate and multivariate time-series trend forecasting with confidence intervals.",
        input_format: "CSV file containing timestamped numerical series.",
        options: &[
            ("--horizon <N>", "Number of future periods to forecast (default: 30)"),
        ],
        directives: &[
            ("@agent timeseries <file.csv>", "Multi-horizon time-series forecasting with confidence intervals"),
        ],
        examples: &[
            "@agent timeseries sales_history_2025.csv",
            "@agent timeseries --horizon 60 quarterly_revenue.csv",
            "cli.exe --tool-help timeseries",
        ],
        related: &["acdso", "dataanalyst", "predict"],
    },
    ToolCard {
        id: "predict",
        name: "Supervised Tabular Prediction Trainer",
        category: "tabular",
        menu_index: 4,
        icon: "🔮",
        architecture: "Gradient Boosting & Tabular Neural Nets",
        purpose: "Train supervised classification or regression model to predict target column.",
        input_format: "Target column name and dataset file path.",
        options: &[
            ("--metric <accuracy|f1|rmse>", "Evaluation metric for cross-validation"),
        ],
        directives: &[
            ("@agent predict <target_col> on <file.csv>", "Train model and evaluate predictive performance"),
        ],
        examples: &[
            "@agent predict churn_status on telecom_users.csv",
            "@agent predict price on real_estate_listings.csv",
            "cli.exe --tool-help predict",
        ],
        related: &["acdso", "dataanalyst", "timeseries"],
    },
    ToolCard {
        id: "datascience",
        name: "Comprehensive Data Science Pipeline",
        category: "tabular",
        menu_index: 4,
        icon: "🧪",
        architecture: "Full ML Pipeline (Imputation, Encoding, Ranking)",
        purpose: "Execute full data science workflow: missing value imputation, categorical encoding, cross-validation, and feature importance.",
        input_format: "Dataset file path.",
        options: &[
            ("--file <path>", "Dataset file"),
        ],
        directives: &[
            ("@agent datascience <file.csv>", "Run end-to-end data science optimization workflow"),
        ],
        examples: &[
            "@agent datascience credit_scoring.csv",
            "cli.exe --tool-help datascience",
        ],
        related: &["acdso", "predict"],
    },
    ToolCard {
        id: "decision",
        name: "Multi-Criteria Decision Analysis & Hybrid Router",
        category: "tabular",
        menu_index: 4,
        icon: "⚖️",
        architecture: "Strands Decider 2B & Cloudflare Clef-Flash Edge Router",
        purpose: "Dual-engine System 1 decision-making and routing across competing choices with Bayesian calibration and HITL safety gate.",
        input_format: "Decision query followed by choices (e.g. \"query\" --choices \"A, B, C\").",
        options: &[
            ("--choices <A, B, ...>", "Comma-separated list of candidate options"),
            ("--decision-mode <hybrid|strands|clef|fast>", "Execution engine mode (default: hybrid)"),
        ],
        directives: &[
            ("@agent decision <query> --choices <A, B>", "Evaluate choices with calibrated probabilities"),
            ("cli.exe --decision \"<query>\" --choices \"A, B\"", "CLI decision routing execution"),
        ],
        examples: &[
            "@agent decision \"Should we migrate our cache from Redis to Dragonfly?\" --choices \"Migrate to Dragonfly, Keep Redis, Evaluate KeyDB\"",
            "cli.exe --decision \"Route incoming request\" --choices \"CodeEngine, SearchEngine, VisionEngine\"",
            "cli.exe --tool-help decision",
        ],
        related: &["acdso", "boost"],
    },
    ToolCard {
        id: "sys-info",
        name: "Hardware Telemetry & Memory Sizing Inspector",
        category: "utilities",
        menu_index: 12,
        icon: "💻",
        architecture: "Native Windows WMI / SysInfo Engine",
        purpose: "Display live hardware specifications: CPU model, cores, GPU name, runtime available/free RAM, and certified model tier.",
        input_format: "None (zero arguments).",
        options: &[
            ("--json", "Emit telemetry in JSON format"),
        ],
        directives: &[
            ("@agent sys-info", "Display live hardware specifications and memory sizing"),
            ("cli.exe --sys-info", "Output system hardware JSON telemetry"),
        ],
        examples: &[
            "@agent sys-info",
            "cli.exe --sys-info",
            "cli.exe --tool-help sys-info",
        ],
        related: &["update", "updatedb", "active-model"],
    },
    ToolCard {
        id: "update",
        name: "Fast Curated Model Catalog Updater",
        category: "utilities",
        menu_index: 12,
        icon: "🔄",
        architecture: "Curated Hub Ingestion & Dynamic Sizing Matrix",
        purpose: "Ingest top ~6,500 production workhorse models across all 45 tasks and provision matching Ollama model based on runtime free memory.",
        input_format: "Optional --db-path.",
        options: &[
            ("--db-path <path>", "Target SQLite database file (default: IDE/db/hf_models.db)"),
        ],
        directives: &[
            ("@agent update", "Run fast curated update and provision matching Ollama hardware tier"),
            ("cli.exe --update", "Master CLI curated catalog ingestion"),
        ],
        examples: &[
            "@agent update",
            "cli.exe --update --db-path \"IDE/db/hf_models.db\"",
            "cli.exe --tool-help update",
        ],
        related: &["updatedb", "sys-info", "active-model"],
    },
    ToolCard {
        id: "updatedb",
        name: "Full Hugging Face Registry Crawler (All 2M+ Models)",
        category: "utilities",
        menu_index: 12,
        icon: "🌐",
        architecture: "Cursor Pagination HTTP Ingestion (~1,000 models/sec)",
        purpose: "Continuously traverse the entire Hugging Face Hub via cursor pagination, committing 1,000 models per transaction into local SQLite.",
        input_format: "Optional --max-models cap and --db-path.",
        options: &[
            ("--max-models <N>", "Cap total number of models to crawl (e.g. 50000)"),
            ("--db-path <path>", "Target SQLite database path"),
        ],
        directives: &[
            ("@agent updatedb", "Crawl all 2M+ Hugging Face models into local catalog"),
            ("cli.exe --updatedb --max-models 50000", "Crawl first 50,000 models into SQLite"),
        ],
        examples: &[
            "@agent updatedb",
            "cli.exe --updatedb --max-models 50000 --db-path \"IDE/db/hf_models.db\"",
            "cli.exe --tool-help updatedb",
        ],
        related: &["update", "db-check", "db-rebuild"],
    },
    ToolCard {
        id: "active-model",
        name: "Active Local Model Inspector",
        category: "utilities",
        menu_index: 12,
        icon: "🧠",
        architecture: "Ollama Daemon API Probe",
        purpose: "Inspect currently loaded local model, parameters, context window, quantization level, and VRAM memory footprint.",
        input_format: "None.",
        options: &[],
        directives: &[
            ("@agent active-model", "Inspect currently loaded local model and context window"),
        ],
        examples: &[
            "@agent active-model",
            "cli.exe --active-model",
            "cli.exe --tool-help active-model",
        ],
        related: &["sys-info", "update"],
    },
    ToolCard {
        id: "audit-menus",
        name: "Comprehensive Menus & Tools Auditor",
        category: "utilities",
        menu_index: 12,
        icon: "🧪",
        architecture: "Automated Tool Test & Verification Suite",
        purpose: "Programmatically audit and verify all 107 tool definitions across all 15 categories for syntax integrity and schema parity.",
        input_format: "None.",
        options: &[],
        directives: &[
            ("@agent audit-menus", "Audit all tool items across all 15 categories"),
        ],
        examples: &[
            "@agent audit-menus",
            "cli.exe --tool-help audit-menus",
        ],
        related: &["sys-info", "db-check"],
    },
    ToolCard {
        id: "db-check",
        name: "SQLite Database Integrity Verifier",
        category: "utilities",
        menu_index: 12,
        icon: "🩺",
        architecture: "SQLite PRAGMA Integrity & FTS5 Index Checker",
        purpose: "Run low-level SQLite PRAGMA integrity checks, foreign key verification, and FTS5 full-text index validation.",
        input_format: "Optional --db-path.",
        options: &[
            ("--db-path <path>", "Target SQLite database file"),
        ],
        directives: &[
            ("@agent db-check", "Run low-level SQLite PRAGMA integrity checks"),
            ("cli.exe --db-check", "Execute database integrity audit"),
        ],
        examples: &[
            "@agent db-check",
            "cli.exe --db-check",
            "cli.exe --tool-help db-check",
        ],
        related: &["db-vacuum", "db-rebuild", "db-prune"],
    },
    ToolCard {
        id: "db-vacuum",
        name: "SQLite Database Vacuum & Page Defragmenter",
        category: "utilities",
        menu_index: 12,
        icon: "🧹",
        architecture: "SQLite VACUUM Engine",
        purpose: "Reclaim unallocated disk space, defragment SQLite storage pages, and shrink hf_models.db file size.",
        input_format: "Optional --db-path.",
        options: &[
            ("--db-path <path>", "Target database file"),
        ],
        directives: &[
            ("@agent db-vacuum", "Reclaim disk space and defragment database storage pages"),
            ("cli.exe --db-vacuum", "Execute vacuum maintenance"),
        ],
        examples: &[
            "@agent db-vacuum",
            "cli.exe --db-vacuum",
            "cli.exe --tool-help db-vacuum",
        ],
        related: &["db-check", "db-prune", "db-rebuild"],
    },
    ToolCard {
        id: "db-rebuild",
        name: "SQLite Catalog Database Rebuilder",
        category: "utilities",
        menu_index: 12,
        icon: "🏗️",
        architecture: "Schema Migration & Table Initializer",
        purpose: "Drop and recreate local model catalog tables, triggers, and FTS5 virtual tables from scratch.",
        input_format: "Optional --db-path.",
        options: &[
            ("--db-path <path>", "Database path to rebuild"),
        ],
        directives: &[
            ("@agent db-rebuild", "Drop and recreate the local model catalog database from scratch"),
            ("cli.exe --db-rebuild", "Execute complete catalog rebuild"),
        ],
        examples: &[
            "@agent db-rebuild",
            "cli.exe --db-rebuild",
            "cli.exe --tool-help db-rebuild",
        ],
        related: &["db-check", "db-vacuum", "update"],
    },
    ToolCard {
        id: "db-prune",
        name: "Temporary Buffer & Cache Pruner",
        category: "utilities",
        menu_index: 12,
        icon: "✂️",
        architecture: "Cache Cleaner & Storage Reclaimer",
        purpose: "Safely clear orphaned search caches, temporary query buffers, and scratch files from disk.",
        input_format: "None.",
        options: &[],
        directives: &[
            ("@agent db-prune", "Safely clear orphaned caches and temporary query buffers"),
            ("cli.exe --db-prune", "Execute prune via Master CLI"),
        ],
        examples: &[
            "@agent db-prune",
            "cli.exe --db-prune",
            "cli.exe --tool-help db-prune",
        ],
        related: &["db-vacuum", "db-check"],
    },
    ToolCard {
        id: "som",
        name: "Set-of-Mark (SoM) Visual Coordinate Markers",
        category: "computer_use",
        menu_index: 3,
        icon: "🎯",
        architecture: "Set-of-Mark Visual Coordinate Grounding",
        purpose: "Inject numbered visual bounding badges onto active desktop controls or browser web elements.",
        input_format: "Active viewport or window.",
        options: &[],
        directives: &[
            ("@agent markers", "Inject numbered Set-of-Mark visual bounding markers onto web page controls"),
            ("cli.exe som", "CLI Set-of-Mark invocation"),
        ],
        examples: &[
            "@agent markers",
            "cli.exe som",
            "cli.exe --tool-help som",
        ],
        related: &["screen-grounding", "computer-use"],
    },
    ToolCard {
        id: "humanize",
        name: "Anti-AI Stylometry Prose Humanizer",
        category: "writing",
        menu_index: 15,
        icon: "✍️",
        architecture: "Entropy & Burstiness Stylometry Optimizer",
        purpose: "Rewrite robotic AI drafts into natural, varied human prose that bypasses AI detectors while preserving meaning.",
        input_format: "AI-generated text or file path.",
        options: &[
            ("--file <path>", "File containing text to humanize"),
        ],
        directives: &[
            ("@agent humanize <text>", "Rewrite passage into natural, fluid human prose"),
            ("cli.exe --humanize \"<text>\"", "CLI humanizer execution"),
        ],
        examples: &[
            "@agent humanize In today's digital era, artificial intelligence plays an indispensable role in modern society.",
            "cli.exe --humanize \"The multifaceted approach revolutionized the digital landscape.\"",
            "cli.exe --tool-help humanize",
        ],
        related: &["watermark", "translate", "outline"],
    },
    ToolCard {
        id: "watermark",
        name: "Statistical Token & Spatial Watermark Detector",
        category: "writing",
        menu_index: 15,
        icon: "🔍",
        architecture: "Kirchenbauer Z-Score & Spatial LSB Entropy Scanner",
        purpose: "Detect statistical token distribution green-list watermarks (text) and chi-square LSB entropy anomalies (images).",
        input_format: "Text passage, document file path, or image file path.",
        options: &[
            ("--file <path>", "Path to text or image file"),
        ],
        directives: &[
            ("@agent watermark <text/file>", "Detect AI watermark or steganographic anomaly"),
            ("cli.exe --watermark \"<text>\"", "CLI watermark detector"),
        ],
        examples: &[
            "@agent watermark Check this paragraph for synthetic AI green-list watermarking patterns.",
            "cli.exe --watermark --file sample_text.txt",
            "cli.exe --tool-help watermark",
        ],
        related: &["humanize", "translate"],
    },
    ToolCard {
        id: "translate",
        name: "Neural Multilingual Translator",
        category: "writing",
        menu_index: 15,
        icon: "🌐",
        architecture: "NLLB-200 / SeamlessM4T Neural Translator",
        purpose: "Translate natural language text or documents into target language across 100+ supported languages.",
        input_format: "Text or file with target language specification.",
        options: &[
            ("--to <lang>", "Target language (default: English)"),
            ("--file <path>", "Path to document file to translate"),
        ],
        directives: &[
            ("@agent translate to <lang>: <text>", "Translate text into target language"),
            ("cli.exe --translate \"<text>\" --to Spanish", "CLI translation execution"),
        ],
        examples: &[
            "@agent translate to Spanish: Welcome to our local AI browser. All data stays on your machine.",
            "cli.exe --translate \"Hello world\" --to French",
            "cli.exe --tool-help translate",
        ],
        related: &["humanize", "code-translate"],
    },
    ToolCard {
        id: "boost",
        name: "Deep Reasoning Deliberation & Verification",
        category: "agent",
        menu_index: 9,
        icon: "🚀",
        architecture: "Monte Carlo Deliberation & Formal Verification",
        purpose: "Trigger deep multi-perspective reasoning deliberation with formal constraint checks on complex challenges.",
        input_format: "Complex problem statement, architectural specification, or algorithmic puzzle.",
        options: &[],
        directives: &[
            ("@agent boost <problem>", "Trigger deep reasoning deliberation"),
            ("cli.exe --boost \"<problem>\"", "CLI deep deliberation execution"),
        ],
        examples: &[
            "@agent boost Design a lock-free multi-producer single-consumer ring buffer in Rust",
            "cli.exe --boost \"Prove that square root of 2 is irrational\"",
            "cli.exe --tool-help boost",
        ],
        related: &["grill-me", "plan", "cot", "goal"],
    },
    ToolCard {
        id: "grill-me",
        name: "Adversarial Requirements Interviewer",
        category: "agent",
        menu_index: 9,
        icon: "🔥",
        architecture: "Adversarial Edge-Case Discovery Agent",
        purpose: "AI conducts rigorous multi-turn interview, interrogating user specifications to uncover hidden assumptions and edge cases.",
        input_format: "Project proposal or architecture outline.",
        options: &[],
        directives: &[
            ("@agent grill-me <plan>", "Adversarial interview stress-testing proposal"),
        ],
        examples: &[
            "@agent grill-me I want to migrate our Postgres transactional database to an event-sourced architecture on Apache Kafka",
            "cli.exe --tool-help grill-me",
        ],
        related: &["boost", "plan", "goal"],
    },
    ToolCard {
        id: "plan",
        name: "Milestone Decomposer & Architecture Planner",
        category: "agent",
        menu_index: 9,
        icon: "📋",
        architecture: "Hierarchical Task Network (HTN) Planner",
        purpose: "Deconstruct complex specifications into structured, dependency-ordered milestones and verified test criteria.",
        input_format: "High-level goal or system architecture vision.",
        options: &[],
        directives: &[
            ("@agent plan <architecture>", "Deconstruct specification into structured milestones"),
        ],
        examples: &[
            "@agent plan Build a distributed Raft consensus cluster with heartbeat election timers",
            "cli.exe --tool-help plan",
        ],
        related: &["boost", "grill-me", "goal"],
    },
];

// -----------------------------------------------------------------------------
// Card Formatting Helpers
// -----------------------------------------------------------------------------

fn build_header_box(icon: &str, title: &str) -> String {
    let inner_len = 76;
    let title_line = format!("{} {}", icon, title);
    let padded_title = if title_line.len() > inner_len - 4 {
        title_line[..inner_len - 4].to_string()
    } else {
        title_line
    };
    let spaces = inner_len - 2 - padded_title.len();
    let border = "═".repeat(inner_len);

    format!(
        "╔{}╗\n║  {}{:width$}║\n╚{}╝\n",
        border,
        padded_title,
        "",
        border,
        width = spaces
    )
}

fn format_model_card(card: &ModelCard) -> String {
    let mut out = String::new();
    out.push_str(&build_header_box(card.icon, &format!("MODEL CARD: {}", card.name)));

    out.push_str(&format!("📂 Subsystem & Category:\n   Menu {}: {}\n\n", card.menu_index, card.category.to_uppercase()));
    out.push_str(&format!("🏗️ Architecture & Engine:\n   {}\n   Provider: {}\n\n", card.architecture, card.author));
    out.push_str(&format!("📋 Purpose & Capabilities:\n   {}\n\n", card.purpose));
    out.push_str(&format!("📥 Input Format & Requirements:\n   {}\n   Sample Input: {}\n\n", card.input_format, card.sample_input));

    if !card.options.is_empty() {
        out.push_str("⚙️ Command Options & CLI Flags:\n");
        for (flag, desc) in card.options {
            out.push_str(&format!("   {:<28} {}\n", flag, desc));
        }
        out.push('\n');
    }

    if !card.directives.is_empty() {
        out.push_str("💬 Agent Directives:\n");
        for (cmd, desc) in card.directives {
            out.push_str(&format!("   • {:<35} ({})\n", cmd, desc));
        }
        out.push('\n');
    }

    if !card.examples.is_empty() {
        out.push_str("🚀 Runnable Sample Usage Examples:\n");
        for ex in card.examples {
            out.push_str(&format!("   • {}\n", ex));
        }
        out.push('\n');
    }

    if !card.related.is_empty() {
        out.push_str(&format!("🔗 Related Models & Tools: {}\n", card.related.join(", ")));
    }

    out
}

fn format_tool_card(card: &ToolCard) -> String {
    let mut out = String::new();
    out.push_str(&build_header_box(card.icon, &format!("TOOL CARD: {}", card.name)));

    out.push_str(&format!("📂 Subsystem & Category:\n   Menu {}: {}\n\n", card.menu_index, card.category.to_uppercase()));
    out.push_str(&format!("🏗️ Architecture & Engine:\n   {}\n\n", card.architecture));
    out.push_str(&format!("📋 Purpose & Capabilities:\n   {}\n\n", card.purpose));
    out.push_str(&format!("📥 Input Format & Requirements:\n   {}\n\n", card.input_format));

    if !card.options.is_empty() {
        out.push_str("⚙️ Command Options & CLI Flags:\n");
        for (flag, desc) in card.options {
            out.push_str(&format!("   {:<28} {}\n", flag, desc));
        }
        out.push('\n');
    }

    if !card.directives.is_empty() {
        out.push_str("💬 Agent Directives:\n");
        for (cmd, desc) in card.directives {
            out.push_str(&format!("   • {:<35} ({})\n", cmd, desc));
        }
        out.push('\n');
    }

    if !card.examples.is_empty() {
        out.push_str("🚀 Runnable Sample Usage Examples:\n");
        for ex in card.examples {
            out.push_str(&format!("   • {}\n", ex));
        }
        out.push('\n');
    }

    if !card.related.is_empty() {
        out.push_str(&format!("🔗 Related Tools & Models: {}\n", card.related.join(", ")));
    }

    out
}

fn format_category_section(cat: &CategoryInfo) -> String {
    let mut out = String::new();
    out.push_str(&build_header_box(cat.icon, &format!("MENU {}: {}", cat.menu_index, cat.title)));
    out.push_str(&format!("Subtitle: {}\n\n", cat.subtitle));
    out.push_str(&format!("📋 Overview:\n   {}\n\n", cat.overview));

    out.push_str("🏗️ Foundation Engines & Models:\n");
    for (name, spec) in cat.engines {
        out.push_str(&format!("   • {:<26} [{}]\n", name, spec));
    }
    out.push('\n');

    out.push_str("💬 Key Directives:\n");
    for (cmd, desc) in cat.directives {
        out.push_str(&format!("   • {:<35} {}\n", cmd, desc));
    }
    out.push('\n');

    out.push_str("🚀 Runnable Examples:\n");
    for ex in cat.examples {
        out.push_str(&format!("   • {}\n", ex));
    }
    out.push('\n');

    out
}

fn format_all_categories_index() -> String {
    let mut out = String::new();
    out.push_str(&build_header_box("📚", "MODELFUSION / HUGOS COMMAND HELP DIRECTORY"));
    out.push_str("Explore all 15 operational subsystems, 107 local tools, and 50+ models.\n");
    out.push_str("Run `@agent <cmd> help`, `@agent <cmd> --help`, or `cli.exe --tool-help <cmd>` for deep cards.\n\n");

    for cat in CATEGORIES {
        out.push_str(&format!("{} Menu {:>2}: {:<32} - {}\n", cat.icon, cat.menu_index, cat.title, cat.subtitle));
        for ex in cat.examples.iter().take(1) {
            out.push_str(&format!("   Sample: {}\n", ex));
        }
    }

    out.push_str("\n💡 Tip: Query any tool or model directly, e.g.:\n");
    out.push_str("   • cli.exe --tool-help \"classify nli-deberta-v3-base\"\n");
    out.push_str("   • cli.exe --tool-help computer-use\n");
    out.push_str("   • cli.exe --tool-help \"legal saul-7b\"\n");
    out.push_str("   • cli.exe --tool-help acdso\n");
    out.push_str("   • cli.exe --tool-help 1  (displays Menu 1 Classification & Taxonomy)\n");

    out
}

/// Formats a comprehensive tool or model help card based on user query string.
pub fn format_tool_help_card(query: &str) -> String {
    let trimmed = query.trim();
    if trimmed.is_empty() || trimmed.eq_ignore_ascii_case("all") || trimmed.eq_ignore_ascii_case("menu") || trimmed.eq_ignore_ascii_case("help") {
        return format_all_categories_index();
    }

    // Check if query is a numeric menu index 1..15
    if let Ok(num) = trimmed.parse::<u32>() {
        if let Some(cat) = CATEGORIES.iter().find(|c| c.menu_index == num) {
            return format_category_section(cat);
        }
    }

    let lower = trimmed.to_lowercase();
    let tokens: Vec<&str> = lower.split_whitespace().collect();

    // 1. Check exact or alias match in Specific Model Cards
    for card in MODEL_CARDS {
        let card_author_lower = card.author.to_lowercase();
        let card_name_lower = card.name.to_lowercase();
        if lower == card.id
            || lower.contains(card.id)
            || card_author_lower.contains(&lower)
            || card_name_lower.contains(&lower)
        {
            return format_model_card(card);
        }
        for token in &tokens {
            if *token == card.id
                || (card.id.contains(token) && token.len() >= 4)
                || (token.contains(card.id) && card.id.len() >= 4)
                || (token.len() >= 4 && card_author_lower.contains(token))
                || (token.len() >= 4 && card_name_lower.contains(token))
            {
                return format_model_card(card);
            }
        }
    }

    // 2. Check exact or alias match in Tool Cards
    for card in TOOL_CARDS {
        if lower == card.id || lower == card.name.to_lowercase() {
            return format_tool_card(card);
        }
        for token in &tokens {
            if *token == card.id {
                return format_tool_card(card);
            }
        }
    }

    // 3. Check partial multi-token match in Tool Cards
    for card in TOOL_CARDS {
        if lower.contains(card.id) || card.id.contains(&lower) {
            return format_tool_card(card);
        }
    }

    // 4. Check category keyword or title match
    for cat in CATEGORIES {
        let cat_title_lower = cat.title.to_lowercase();
        let cat_id = cat.id.to_lowercase();
        if lower == cat_id || cat_title_lower.contains(&lower) || lower.contains(&cat_id) {
            return format_category_section(cat);
        }
        for token in &tokens {
            if *token == cat_id || cat_title_lower.contains(token) && token.len() >= 4 {
                return format_category_section(cat);
            }
        }
    }

    // 5. Fallback card: Not found, show suggestions and full menu index
    let mut out = String::new();
    out.push_str(&build_header_box("ℹ️", &format!("NO EXACT CARD FOR: \"{}\"", trimmed)));
    out.push_str("Could not find an exact specialized card matching that query.\n\n");
    out.push_str("Available Popular Commands:\n");
    out.push_str("   • @agent classify nli-deberta-v3-base help\n");
    out.push_str("   • @agent computer-use --help\n");
    out.push_str("   • @agent legal saul-7b help\n");
    out.push_str("   • @agent acdso help\n");
    out.push_str("   • @agent sys-info help\n");
    out.push_str("   • @agent update help\n\n");
    out.push_str("Available Menus (1 to 15):\n");
    for cat in CATEGORIES {
        out.push_str(&format!("   Menu {:>2}: {} {}\n", cat.menu_index, cat.icon, cat.title));
    }
    out.push_str("\nType `@agent <cmd> help` or `cli.exe --tool-help <query>` to view detailed cards.\n");
    out
}
