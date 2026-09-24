# ModelFusion Master CLI Reference Manual (All 161 Flags)

This document is the exhaustive, authoritative reference for the **ModelFusion Master CLI** (`cli.exe` or `cargo run --release --bin cli`).
Every single one of the **161 production CLI flags** is documented below with its argument type, default value, functional category, behavioral explanation, and a **concrete executable command example**.

> [!IMPORTANT]
> **Functional Architecture: Flags as Executable Commands**  
> In ModelFusion, flags function directly as executable capability functions. The CLI parser maps each flag directly to an underlying handler function in the execution engine. Specifying a flag instructs the engine to invoke that capability rather than merely toggling state.

---

## 📖 Table of Contents
- [Master Summary Table (All 161 Flags)](#-master-summary-table-all-161-flags)
- [1. Global Execution & Resource Flags (#1 - #19)](#1-global-execution--resource-flags)
- [2. Machine Learning Model Selection (#20 - #26)](#2-machine-learning-model-selection)
- [3. SINQ Quantization Engine (#27 - #31)](#3-sinq-quantization-engine)
- [4. Innovation & Cognitive Systems (#32 - #37)](#4-innovation--cognitive-systems)
- [5. HyDE Search & Web Retrieval (#38 - #46)](#5-hyde-search--web-retrieval)
- [6. System & Orchestration Commands (#47 - #87)](#6-system--orchestration-commands)
- [7. Data Science & Tabular Workflows (#88 - #90)](#7-data-science--tabular-workflows)
- [8. Response Evaluation & Planning (#91 - #93)](#8-response-evaluation--planning)
- [9. Binary & PE Executable Analysis (#94)](#9-binary--pe-executable-analysis)
- [10. Multi-Modal Task Routing Flags (#95 - #156)](#10-multi-modal-task-routing-flags)
- [11. Server & Database Commands (#157 - #161)](#11-server--database-commands)
- [Appendix: Developer Tooling, Source Patching & Legacy Aliases](#appendix-developer-tooling-source-patching--legacy-aliases)

---

## 📋 Master Summary Table (All 161 Flags)

| # | Flag & Aliases | Type | Default | Category | Description |
|:---:|:---|:---:|:---:|:---|:---|
| 1 | `--file <FILE>` | `String` | `None` | Global Execution & Resource Flags | Specify a local file path as target input for analysis, code review, or ingestion into the model context. |
| 2 | `--folder <FOLDER>` | `String` | `None` | Global Execution & Resource Flags | Specify a target directory for batch scanning, multi-file code review, or directory-level summarization. |
| 3 | `--prompt <PROMPT>` | `String` | `None` | Global Execution & Resource Flags | Primary instruction or question passed to the dynamically selected local or remote model. |
| 4 | `--task <TASK>` | `String` | `None` | Global Execution & Resource Flags | Explicitly force routing to a specific Hugging Face task pipeline instead of automatic classification. |
| 5 | `--budget <VALUE>` | `f64` | `10.0` | Global Execution & Resource Flags | Sets a maximum monetary budget cap for commercial cloud LLM provider API consumption. |
| 6 | `--chain-of-thought` | `bool` | `false` | Global Execution & Resource Flags | Enforces step-by-step reasoning tokens prior to synthesizing final code and answers. |
| 7 | `--config <CONFIG>` | `String` | `None` | Global Execution & Resource Flags | Overrides default engine configuration with settings from a specified JSON configuration file. |
| 8 | `--enable-ml` | `bool` | `false` | Global Execution & Resource Flags | Enables machine-learning enhancements across model routing, feature extraction, and heuristics. |
| 9 | `--use-openai` | `bool` | `false` | Global Execution & Resource Flags | Directs execution to OpenAI API endpoints (requires OPENAI_API_KEY) rather than local Ollama models. |
| 10 | `--verbose` | `bool` | `false` | Global Execution & Resource Flags | Enables detailed informational console logs, pipeline transition notices, and execution progress. |
| 11 | `--debug` | `bool` | `false` | Global Execution & Resource Flags | Outputs exhaustive low-level diagnostic traces, memory allocations, IPC messages, and raw errors. |
| 12 | `--selection-strategy <SELECTION-STRATEGY>` | `String` | `multi_objective` | Global Execution & Resource Flags | Specifies the Pareto optimization strategy used to score and rank candidate models from SQLite. |
| 13 | `--language <LANGUAGE>` | `String` | `en` | Global Execution & Resource Flags | Configures the target linguistic locale for model prompt templates, tokenizers, and responses. |
| 14 | `--gpu` | `bool` | `false` | Global Execution & Resource Flags | Forces GPU acceleration (CUDA, ROCm, Vulkan) and aborts if hardware acceleration is unavailable. |
| 15 | `--cpu` | `bool` | `false` | Global Execution & Resource Flags | Forces CPU-only execution, disabling GPU kernel initialization and saving VRAM. |
| 16 | `--api-keys <API-KEYS>` | `String` | `None` | Global Execution & Resource Flags | Loads provider credentials (HuggingFace, OpenAI, Anthropic) from a structured JSON file. |
| 17 | `--sys-info` | `bool` | `false` | Global Execution & Resource Flags | Detects and prints CPU, RAM, available memory, GPU model, VRAM, and storage resources in JSON format. |
| 18 | `--save-model` | `bool` | `false` | Global Execution & Resource Flags | Serializes and persists the trained ML model selector weights and routing policy to disk. |
| 19 | `--load-model <LOAD-MODEL>` | `String` | `None` | Global Execution & Resource Flags | Loads pre-trained model selection weights from disk for offline deterministic routing. |
| 20 | `--enable-ml-selection` | `bool` | `false` | Machine Learning Model Selection | Enables the machine-learning classifier to pick optimal models based on task, prompt, and system resources. |
| 21 | `--ml-learning` | `bool` | `false` | Machine Learning Model Selection | Activates online reinforcement learning to update selection weights based on execution success rates. |
| 22 | `--ml-ensemble-method <ML-ENSEMBLE-METHOD>` | `String` | `weighted_voting` | Machine Learning Model Selection | Sets the ensemble aggregation algorithm for combining predictions across multiple ML meta-models. |
| 23 | `--ml-confidence-threshold <VALUE>` | `f64` | `0.6` | Machine Learning Model Selection | Minimum confidence required to accept ML model routing; lower scores trigger fallback heuristics. |
| 24 | `--ml-analytics` | `bool` | `false` | Machine Learning Model Selection | Prints statistical reports of model routing decisions, classification accuracy, and confidence metrics. |
| 25 | `--ml-retrain` | `bool` | `false` | Machine Learning Model Selection | Forces full retraining of the model selection routing classifiers using historical run records. |
| 26 | `--ml-cleanup` | `u32` | `None` | Machine Learning Model Selection | Purges historical ML execution telemetry and reward logs older than the specified retention days. |
| 27 | `--sinq` | `bool` | `false` | SINQ Quantization Engine | Enables SINQ (Sub-4-bit Integer Non-linear Quantization) for high-efficiency low-memory model inference. |
| 28 | `--sinq-nbits <VALUE>` | `u32` | `4` | SINQ Quantization Engine | Specifies the target bit precision for SINQ weight quantization (default: 4). |
| 29 | `--sinq-group-size <VALUE>` | `u32` | `64` | SINQ Quantization Engine | Specifies the number of consecutive weight elements sharing quantization scale and zero-point parameters. |
| 30 | `--sinq-tiling-mode <SINQ-TILING-MODE>` | `String` | `1D` | SINQ Quantization Engine | Configures tensor tiling strategy for SINQ quantization matrix kernels. |
| 31 | `--sinq-method <SINQ-METHOD>` | `String` | `sinq` | SINQ Quantization Engine | Selects the mathematical quantization formulation (default: sinq). |
| 32 | `--enable-innovations` | `bool` | `false` | Innovation & Cognitive Systems | Activates all ModelFusion cognitive innovation modules including workflow optimization and predictive planning. |
| 33 | `--workflow-optimization` | `bool` | `false` | Innovation & Cognitive Systems | Applies cognitive pipeline restructuring to minimize latency and memory churn across subtasks. |
| 34 | `--semantic-analysis` | `bool` | `false` | Innovation & Cognitive Systems | Performs deep semantic AST and intent analysis on codebases and input prompts. |
| 35 | `--temporal-tracking` | `bool` | `false` | Innovation & Cognitive Systems | Tracks semantic modifications and architectural drift across code revisions over time. |
| 36 | `--predictive-mode` | `bool` | `false` | Innovation & Cognitive Systems | Uses speculative ghost modeling to anticipate subsequent user commands and pre-cache inference results. |
| 37 | `--innovation-level <VALUE>` | `u32` | `2` | Innovation & Cognitive Systems | Configures aggressiveness and heuristic exploration depth of innovation subsystems (default: 2). |
| 38 | `--enable-hyde` | `bool` | `false` | HyDE Search & Web Retrieval | Activates Hypothetical Document Embeddings (HyDE) for superior semantic document and code retrieval. |
| 39 | `--use-hyde` | `bool` | `false` | HyDE Search & Web Retrieval | Enables interactive HyDE query refinement and hypothetical response generation before searching. |
| 40 | `--hyde-variants` | `bool` | `false` | HyDE Search & Web Retrieval | Generates multiple hypothetical answers across diverse temperature seeds to maximize embedding recall. |
| 41 | `--add-documents <ADD-DOCUMENTS>` | `String` | `None` | HyDE Search & Web Retrieval | Ingests and indexes local files or Markdown docs into the HyDE vector embedding database. |
| 42 | `--search-query <SEARCH-QUERY>` | `String` | `None` | HyDE Search & Web Retrieval | Executes a semantic vector similarity search against indexed codebase and documentation chunks. |
| 43 | `--research <RESEARCH>`<br><small>Aliases: `--reseach`</small> | `String` | `None` | HyDE Search & Web Retrieval | Autonomous deep research agent performing multi-hop search, recursive web scraping, and reasoning synthesis. |
| 44 | `--search <SEARCH>`<br><small>Aliases: `--serarch`</small> | `String` | `None` | HyDE Search & Web Retrieval | Performs real-time web search and fast extractive summarization using open-weight local models. |
| 45 | `--top-k <VALUE>` | `u32` | `5` | HyDE Search & Web Retrieval | Specifies the number of top-ranking search results or document passages to return (default: 5). |
| 46 | `--demo-hyde` | `bool` | `false` | HyDE Search & Web Retrieval | Runs an interactive end-to-end demonstration of HyDE hypothetical vector generation and retrieval. |
| 47 | `--active-model`<br><small>Aliases: `--active-models`, `--current-model`, `--current-models`, `--ide-model`, `--ide-models`, `--models-in-use`</small> | `bool` | `false` | System & Orchestration Commands | Inspects and displays all active models across Ollama VRAM/RAM runtime, SQLite task models, and OpenVINO cache. |
| 48 | `--stats` | `bool` | `false` | System & Orchestration Commands | Displays global catalog statistics, model counts per Hugging Face task, and database health metrics. |
| 49 | `--tasks <TASKS>` | `String` | `None` | System & Orchestration Commands | Lists all 45+ supported Hugging Face task types and their currently registered models. |
| 50 | `--update` | `bool` | `false` | System & Orchestration Commands | Fast curated update: indexes top ~6,500 production workhorse models and provisions matching Ollama model. |
| 51 | `--updatedb` | `bool` | `false` | System & Orchestration Commands | Full registry crawler: ingests all 2M+ models from Hugging Face Hub via cursor pagination (1,000/batch). |
| 52 | `--max-models` | `usize` | `None` | System & Orchestration Commands | Caps the total number of models ingested from Hugging Face Hub during a --updatedb crawl run. |
| 53 | `--restore` | `bool` | `false` | System & Orchestration Commands | Restores ModelFusion configuration and SQLite catalog databases from verified recovery backups. |
| 54 | `--decision-stats` | `bool` | `false` | System & Orchestration Commands | Displays historical statistics on Pareto model routing decisions, execution latencies, and fallback events. |
| 55 | `--novel-ai-stats` | `bool` | `false` | System & Orchestration Commands | Displays operational telemetry and metrics for novel AI components (SINQ, HyDE, predictive reasoning). |
| 56 | `--performance-stats` | `bool` | `false` | System & Orchestration Commands | Outputs hardware utilization, inference throughput (tokens/second), memory footprint, and queue delays. |
| 57 | `--cache-stats` | `bool` | `false` | System & Orchestration Commands | Displays cache hit ratios, storage utilization, and eviction counters for prompt and IR caches. |
| 58 | `--clearcache` | `bool` | `false` | System & Orchestration Commands | Evicts all transient cache stores, prompt response buffers, and downloaded temporary model weights. |
| 59 | `--analytics-demo` | `bool` | `false` | System & Orchestration Commands | Executes a synthetic benchmark demonstrating multi-criteria model ranking and Pareto frontier visualization. |
| 60 | `--model-ranking <MODEL-RANKING>` | `String` | `None` | System & Orchestration Commands | Computes and displays Pareto-ranked scorecards for models registered under the specified task. |
| 61 | `--model-recommendations` | `bool` | `false` | System & Orchestration Commands | Generates hardware-tailored model recommendations based on current CPU, GPU VRAM, and RAM availability. |
| 62 | `--full` | `bool` | `false` | System & Orchestration Commands | Enables comprehensive multi-stage analysis, activating cross-model validation and deep auditing. |
| 63 | `--fusion` | `bool` | `false` | System & Orchestration Commands | Executes prompt across a panel of models simultaneously and arbitrates responses into a synthesized consensus. |
| 64 | `--fusion-models <VALUE>` | `usize` | `0` | System & Orchestration Commands | Specifies the number of models in the fusion arbitration panel (default: 0 = dynamic auto-sizing). |
| 65 | `--fusion-mode <FUSION-MODE>` | `String` | `multi-model` | System & Orchestration Commands | Execution topology for Model Fusion: 'multi-model' (diverse models) or 'multi-sample' (fast local sampling). |
| 66 | `--ollama` | `bool` | `false` | System & Orchestration Commands | Routes inference execution directly through local Ollama daemon rather than Python transformers. |
| 67 | `--openvino` | `bool` | `false` | System & Orchestration Commands | Uses Intel OpenVINO runtime for AVX-512 / AMX accelerated CPU inference. |
| 68 | `--onnx` | `bool` | `false` | System & Orchestration Commands | Uses ONNX Runtime cross-platform inference engine for quantized and exported models. |
| 69 | `--vllm` | `bool` | `false` | System & Orchestration Commands | Uses vLLM PagedAttention inference engine for ultra-high throughput GPU serving. |
| 70 | `--model <MODEL>` | `String` | `None` | System & Orchestration Commands | Overrides Pareto routing heuristics and forces execution using a specific model identifier. |
| 71 | `--prepare-model <PREPARE-MODEL>` | `String` | `None` | System & Orchestration Commands | Pre-converts and quantizes a Hugging Face model into OpenVINO Intermediate Representation (IR). |
| 72 | `--prepare-all-models` | `bool` | `false` | System & Orchestration Commands | Batch converts all eligible top-tier models in the catalog database to OpenVINO IR format. |
| 73 | `--weight-format <WEIGHT-FORMAT>` | `String` | `int8` | System & Orchestration Commands | Specifies weight precision for OpenVINO Intermediate Representation exports (default: int8). |
| 74 | `--ov-model-dir <OV-MODEL-DIR>` | `String` | `ov_models` | System & Orchestration Commands | Directory where compiled OpenVINO IR models (.xml / .bin) are stored and cached (default: ov_models). |
| 75 | `--context-auto` | `bool` | `false` | System & Orchestration Commands | Automatically generates background domain context using a thinking model (e.g. DeepSeek-R1) prior to answering. |
| 76 | `--context <CONTEXT>` | `String` | `None` | System & Orchestration Commands | Injects explicit contextual background information into the system prompt. |
| 77 | `--report <REPORT>` | `String` | `None` | System & Orchestration Commands | Specifies file path or directory destination where generated analysis reports should be saved. |
| 78 | `--reporttype <REPORTTYPE>` | `String` | `md` | System & Orchestration Commands | Format of the generated report document (default: md). |
| 79 | `--delegation` | `bool` | `false` | System & Orchestration Commands | Uses hierarchical delegation pattern to route individual subtasks to specialized domain models. |
| 80 | `--recursion` | `bool` | `false` | System & Orchestration Commands | Enables recursive task decomposition to break complex multifaceted prompts into atomic solvable subtasks. |
| 81 | `--getvino` | `bool` | `false` | System & Orchestration Commands | Launches background synchronization daemon to periodically pull pre-optimized OpenVINO IR models. |
| 82 | `--getvino-interval <VALUE>` | `u64` | `24` | System & Orchestration Commands | Interval in hours between background OpenVINO model synchronization cycles (default: 24). |
| 83 | `--rest-rl [<ACTION>...]`<br><small>Aliases: `--rl`</small> | `Vec<String` | `None` | System & Orchestration Commands | Controls and inspects the HugOS ReST-RL / GRPO background reinforcement learning daemon. |
| 84 | `--real-options` | `bool` | `false` | System & Orchestration Commands | Applies financial real options valuation to maintain hot standby backup models during critical tasks. |
| 85 | `--prompt-quality-scoring` | `bool` | `false` | System & Orchestration Commands | Evaluates clarity, specificity, and completeness of input prompts and suggests automated optimizations. |
| 86 | `--ml-fallback` | `bool` | `true` | System & Orchestration Commands | Enables automated heuristic fallback when ML selection confidence falls below minimum threshold (default: true). |
| 87 | `--jupyter` | `bool` | `false` | System & Orchestration Commands | Spawns or connects to an interactive Jupyter notebook server for data exploration and visualization. |
| 88 | `--dataanalyst`<br><small>Aliases: `--data-analyst`, `--datanalyst`</small> | `bool` | `false` | Data Science & Tabular Workflows | Launches the automated Data Analyst pipeline: parses CSV/Excel, performs statistical profiling, and summarizes trends. |
| 89 | `--datascience` | `bool` | `false` | Data Science & Tabular Workflows | Runs the comprehensive Data Science workflow: data cleaning, feature engineering, correlation analysis, and predictive modeling. |
| 90 | `--export-pdf` | `bool` | `false` | Data Science & Tabular Workflows | Renders analysis reports, statistical tables, and visualizations directly into a formatted PDF document. |
| 91 | `--score` | `bool` | `false` | Response Evaluation & Planning | Calculates multi-dimensional quality metrics (coherence, accuracy, safety, code validity) on generated output. |
| 92 | `--judge` | `bool` | `false` | Response Evaluation & Planning | Invokes an independent LLM-as-a-Judge model to critically review, score, and certify model outputs. |
| 93 | `--plan` | `bool` | `false` | Response Evaluation & Planning | Synthesizes a structured multi-phase execution blueprint with verification gates prior to generating code. |
| 94 | `--pe-header-extraction` | `bool` | `false` | Binary & PE Executable Analysis | Extracts PE header structures, section tables, imported DLLs, export symbols, and digital signatures from Windows binaries. |
| 95 | `--text-classification` | `bool` | `false` | Multi-Modal Task Routing Flags | Routes prompt to top-ranked text classification models for categorizing unstructured text into target classes. |
| 96 | `--token-classification` | `bool` | `false` | Multi-Modal Task Routing Flags | Routes prompt to token classification models for token-level labelling (NER, POS tagging, grammatical syntax). |
| 97 | `--question-answering` | `bool` | `false` | Multi-Modal Task Routing Flags | Extracts precise answers to queries given explicit reference context passages. |
| 98 | `--text-generation` | `bool` | `false` | Multi-Modal Task Routing Flags | Standard autoregressive text generation for reasoning, creative writing, and documentation. |
| 99 | `--summarization` | `bool` | `false` | Multi-Modal Task Routing Flags | Distills long-form technical reports, transcripts, and documents into concise summaries. |
| 100 | `--translation` | `bool` | `false` | Multi-Modal Task Routing Flags | Translates text across languages preserving technical terminology and semantic intent. |
| 101 | `--fill-mask` | `bool` | `false` | Multi-Modal Task Routing Flags | Predicts masked tokens within sentences using bidirectional masked language models (e.g. BERT/RoBERTa). |
| 102 | `--text2text-generation` | `bool` | `false` | Multi-Modal Task Routing Flags | Performs arbitrary sequence-to-sequence text transformation and structured rewriting. |
| 103 | `--language-detection` | `bool` | `false` | Multi-Modal Task Routing Flags | Identifies the primary natural language of input passages with associated confidence scores. |
| 104 | `--grammar-correction` | `bool` | `false` | Multi-Modal Task Routing Flags | Detects grammatical, syntactic, and spelling errors and provides corrected text. |
| 105 | `--paraphrase-generation` | `bool` | `false` | Multi-Modal Task Routing Flags | Rephrases sentences into alternative expressions while preserving core semantics. |
| 106 | `--causal-language-modeling` | `bool` | `false` | Multi-Modal Task Routing Flags | Raw autoregressive next-token continuation modeling without instruction fine-tuning templates. |
| 107 | `--zero-shot-classification` | `bool` | `false` | Multi-Modal Task Routing Flags | Classifies text into dynamic arbitrary categories without requiring task-specific training data. |
| 108 | `--feature-extraction` | `bool` | `false` | Multi-Modal Task Routing Flags | Outputs dense multidimensional mathematical vector embeddings for downstream similarity and clustering. |
| 109 | `--sentence-similarity` | `bool` | `false` | Multi-Modal Task Routing Flags | Computes cosine similarity between sentence embeddings to determine semantic equivalence. |
| 110 | `--anonymization` | `bool` | `false` | Multi-Modal Task Routing Flags | Redacts or obfuscates personally identifiable information (PII) from text. |
| 111 | `--coreference-resolution` | `bool` | `false` | Multi-Modal Task Routing Flags | Resolves referring expressions and pronouns to their corresponding entity antecedents. |
| 112 | `--spam-detection` | `bool` | `false` | Multi-Modal Task Routing Flags | Classifies incoming email, chat, or form submissions as legitimate or unsolicited spam. |
| 113 | `--malware-text-detection` | `bool` | `false` | Multi-Modal Task Routing Flags | Analyzes scripts, command strings, and payloads for indicators of malicious code execution. |
| 114 | `--phishing-detection` | `bool` | `false` | Multi-Modal Task Routing Flags | Scans communication text and URLs for social engineering patterns and credential harvesting indicators. |
| 115 | `--pii-detection` | `bool` | `false` | Multi-Modal Task Routing Flags | Identifies sensitive personal information (credit cards, social security numbers, phone numbers, addresses). |
| 116 | `--hate-speech-detection` | `bool` | `false` | Multi-Modal Task Routing Flags | Detects toxic language, hate speech, and derogatory slurs for moderation compliance. |
| 117 | `--cyberbullying-detection` | `bool` | `false` | Multi-Modal Task Routing Flags | Identifies targeted harassment, bullying, and intimidation patterns in social interactions. |
| 118 | `--fake-news-detection` | `bool` | `false` | Multi-Modal Task Routing Flags | Evaluates news claims against factual verification patterns to identify misinformation. |
| 119 | `--legal-judgment-classification` | `bool` | `false` | Multi-Modal Task Routing Flags | Classifies judicial opinions, motions, and court rulings by legal domain and judicial outcome. |
| 120 | `--contract-clause-classification` | `bool` | `false` | Multi-Modal Task Routing Flags | Identifies contract clause types (Indemnification, Termination, Confidentiality, Governing Law). |
| 121 | `--case-outcome-prediction` | `bool` | `false` | Multi-Modal Task Routing Flags | Analyzes litigation filings to estimate probable case outcomes based on legal precedents. |
| 122 | `--financial-ner` | `bool` | `false` | Multi-Modal Task Routing Flags | Extracts financial entities (ticker symbols, revenue metrics, institutions, currencies) from reports. |
| 123 | `--legal-ner` | `bool` | `false` | Multi-Modal Task Routing Flags | Identifies legal citations, statutory codes, case names, and jurisdictional entities. |
| 124 | `--biomedical-ner` | `bool` | `false` | Multi-Modal Task Routing Flags | Extracts biomedical entities (genes, proteins, diseases, drug compounds, dosages) from scientific papers. |
| 125 | `--chemical-reaction-ner` | `bool` | `false` | Multi-Modal Task Routing Flags | Extracts chemical reagents, catalysts, reaction conditions, and products from chemistry literature. |
| 126 | `--financial-sentiment-analysis` | `bool` | `false` | Multi-Modal Task Routing Flags | Classifies investor sentiment (bullish, bearish, neutral) from financial news and 10-K filings. |
| 127 | `--scientific-abstract-summarization` | `bool` | `false` | Multi-Modal Task Routing Flags | Distills dense academic papers into structured problem-method-result research summaries. |
| 128 | `--emotion-detection` | `bool` | `false` | Multi-Modal Task Routing Flags | Detects nuanced emotional states (joy, frustration, anger, surprise, sadness) in conversational text. |
| 129 | `--sarcasm-detection` | `bool` | `false` | Multi-Modal Task Routing Flags | Identifies ironic and sarcastic linguistic markers where intended meaning differs from literal text. |
| 130 | `--stance-detection` | `bool` | `false` | Multi-Modal Task Routing Flags | Determines whether an author is in favor of, against, or neutral toward a given target topic. |
| 131 | `--bias-detection` | `bool` | `false` | Multi-Modal Task Routing Flags | Identifies cognitive, gender, political, or demographic biases in articles and datasets. |
| 132 | `--hallucination-detection` | `bool` | `false` | Multi-Modal Task Routing Flags | Detects ungrounded assertions or factual inconsistencies between generated responses and reference premises. |
| 133 | `--reading-level-assessment` | `bool` | `false` | Multi-Modal Task Routing Flags | Calculates reading comprehension levels (Flesch-Kincaid, Lexile) to assess documentation accessibility. |
| 134 | `--generation-groundedness` | `bool` | `false` | Multi-Modal Task Routing Flags | Evaluates whether model assertions are strictly supported by provided source materials. |
| 135 | `--citation-intent-classification` | `bool` | `false` | Multi-Modal Task Routing Flags | Classifies the purpose of academic citations (background, methodology, comparison, critique). |
| 136 | `--code-vulnerability-detection` | `bool` | `false` | Multi-Modal Task Routing Flags | Scans source code for security vulnerabilities, buffer overflows, integer wraps, and memory safety flaws. |
| 137 | `--code-summary-generation` | `bool` | `false` | Multi-Modal Task Routing Flags | Synthesizes concise technical docstrings and architectural summaries from complex functions and classes. |
| 138 | `--code-clone-detection` | `bool` | `false` | Multi-Modal Task Routing Flags | Identifies duplicate, near-duplicate, and copy-pasted code fragments across a repository. |
| 139 | `--image-classification` | `bool` | `false` | Multi-Modal Task Routing Flags | Routes image files to vision classification models to identify primary subjects and visual categories. |
| 140 | `--object-detection` | `bool` | `false` | Multi-Modal Task Routing Flags | Locates and bounds distinct objects (buttons, windows, icons) within an input image. |
| 141 | `--image-segmentation` | `bool` | `false` | Multi-Modal Task Routing Flags | Segments images at pixel-level resolution to isolate foreground objects from background canvas. |
| 142 | `--visual-question-answering` | `bool` | `false` | Multi-Modal Task Routing Flags | Answers natural language questions about the visual content of an uploaded image or diagram. |
| 143 | `--document-question-answering` | `bool` | `false` | Multi-Modal Task Routing Flags | Extracts answers directly from scanned documents, structured PDF forms, and invoices. |
| 144 | `--zero-shot-image-classification` | `bool` | `false` | Multi-Modal Task Routing Flags | Classifies images into arbitrary candidate categories using multi-modal vision-language models (CLIP). |
| 145 | `--depth-estimation` | `bool` | `false` | Multi-Modal Task Routing Flags | Computes monocular depth maps predicting distance from camera for each pixel in an image. |
| 146 | `--image-feature-extraction` | `bool` | `false` | Multi-Modal Task Routing Flags | Extracts high-dimensional visual embedding vectors for image retrieval and similarity matching. |
| 147 | `--automatic-speech-recognition` | `bool` | `false` | Multi-Modal Task Routing Flags | Transcribes spoken audio into timestamped text transcripts using state-of-the-art ASR models (Whisper). |
| 148 | `--audio-classification` | `bool` | `false` | Multi-Modal Task Routing Flags | Classifies audio files by acoustic event, musical genre, or environmental sound category. |
| 149 | `--voice-activity-detection` | `bool` | `false` | Multi-Modal Task Routing Flags | Detects presence of human speech vs silence or background noise in audio streams. |
| 150 | `--emotion-recognition` | `bool` | `false` | Multi-Modal Task Routing Flags | Detects vocal emotion and caller stress levels from audio pitch, tone, and prosody. |
| 151 | `--video-classification` | `bool` | `false` | Multi-Modal Task Routing Flags | Classifies video clips into activity, genre, or scene categories using temporal-spatial models. |
| 152 | `--text-to-speech` | `bool` | `false` | Multi-Modal Task Routing Flags | Synthesizes natural-sounding speech audio from text input using neural vocoders. |
| 153 | `--text-to-image` | `bool` | `false` | Multi-Modal Task Routing Flags | Generates high-resolution images from text descriptions using latent diffusion models. |
| 154 | `--image-super-resolution` | `bool` | `false` | Multi-Modal Task Routing Flags | Upscales low-resolution images using neural super-resolution to enhance clarity and detail. |
| 155 | `--table-question-answering` | `bool` | `false` | Multi-Modal Task Routing Flags | Answers natural language queries by executing relational reasoning directly over tabular datasets. |
| 156 | `--feature-ranking` | `bool` | `false` | Multi-Modal Task Routing Flags | Ranks input dataset features by predictive importance, information gain, and variance. |
| 157 | `--db-path <DB-PATH>` | `String` | `None` | Server & Database Commands | Specifies custom SQLite database path for ModelFusion catalog, models, and embeddings. |
| 158 | `--server` | `bool` | `false` | Server & Database Commands | Launches the ModelFusion HTTP REST API server for external IDE and headless automation access. |
| 159 | `--enable-slash-commands` | `bool` | `false` | Server & Database Commands | Enables parsing of interactive IDE slash commands (/datascience, /search, /jupyter, /evolve) from raw prompts. |
| 160 | `--port <VALUE>` | `u16` | `5000` | Server & Database Commands | Specifies the TCP port on which the ModelFusion HTTP API server listens (default: 5000). |
| 161 | `--mcp` | `bool` | `false` | Server & Database Commands | Runs ModelFusion as a Model Context Protocol (MCP) server communicating over standard input/output (stdio). |

---

## 1. Global Execution & Resource Flags (#1 - #19)

This section details the **19 flags** belonging to **Global Execution & Resource Flags**.

### #1. `--file`
- **Category:** Global Execution & Resource Flags
- **Argument Type:** `String`
- **Default Value:** `None`
- **Accepted Parameters:** Valid path to a readable file (.py, .rs, .csv, .json, .txt)
- **Description:** Specify a local file path as target input for analysis, code review, or ingestion into the model context.

```powershell
# Example for #1: --file
cli.exe --file "crates/core/src/lib.rs" --prompt "Review this file for potential memory leaks"
```

### #2. `--folder`
- **Category:** Global Execution & Resource Flags
- **Argument Type:** `String`
- **Default Value:** `None`
- **Accepted Parameters:** Valid path to a readable directory
- **Description:** Specify a target directory for batch scanning, multi-file code review, or directory-level summarization.

```powershell
# Example for #2: --folder
cli.exe --folder "src/" --prompt "Generate an architectural overview of all Rust modules in this folder"
```

### #3. `--prompt`
- **Category:** Global Execution & Resource Flags
- **Argument Type:** `String`
- **Default Value:** `None`
- **Accepted Parameters:** Text string containing instructions, questions, or directives
- **Description:** Primary instruction or question passed to the dynamically selected local or remote model.

```powershell
# Example for #3: --prompt
cli.exe --prompt "Explain the zero-VRAM graduated verification mechanism in HugOS"
```

### #4. `--task`
- **Category:** Global Execution & Resource Flags
- **Argument Type:** `String`
- **Default Value:** `None`
- **Accepted Parameters:** HuggingFace task name (e.g. text-generation, image-classification, summarization)
- **Description:** Explicitly force routing to a specific Hugging Face task pipeline instead of automatic classification.

```powershell
# Example for #4: --task
cli.exe --task text-generation --prompt "Write a high-performance LRU cache in Rust"
```

### #5. `--budget`
- **Category:** Global Execution & Resource Flags
- **Argument Type:** `f64`
- **Default Value:** `10.0`
- **Accepted Parameters:** Floating point monetary limit in USD (e.g. 5.0, 10.0, 25.5)
- **Description:** Sets a maximum monetary budget cap for commercial cloud LLM provider API consumption.

```powershell
# Example for #5: --budget
cli.exe --prompt "Deep refactor of parsing pipeline" --budget 2.5
```

### #6. `--chain-of-thought`
- **Category:** Global Execution & Resource Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Enforces step-by-step reasoning tokens prior to synthesizing final code and answers.

```powershell
# Example for #6: --chain-of-thought
cli.exe --prompt "Solve the dining philosophers problem with deadlock avoidance" --chain-of-thought
```

### #7. `--config`
- **Category:** Global Execution & Resource Flags
- **Argument Type:** `String`
- **Default Value:** `None`
- **Accepted Parameters:** Path to a custom JSON configuration file
- **Description:** Overrides default engine configuration with settings from a specified JSON configuration file.

```powershell
# Example for #7: --config
cli.exe --config "config/production_overrides.json" --active-model
```

### #8. `--enable-ml`
- **Category:** Global Execution & Resource Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Enables machine-learning enhancements across model routing, feature extraction, and heuristics.

```powershell
# Example for #8: --enable-ml
cli.exe --prompt "Classify cybersecurity incident logs" --enable-ml
```

### #9. `--use-openai`
- **Category:** Global Execution & Resource Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Directs execution to OpenAI API endpoints (requires OPENAI_API_KEY) rather than local Ollama models.

```powershell
# Example for #9: --use-openai
cli.exe --prompt "Summarize multi-tier architecture" --use-openai
```

### #10. `--verbose`
- **Category:** Global Execution & Resource Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Enables detailed informational console logs, pipeline transition notices, and execution progress.

```powershell
# Example for #10: --verbose
cli.exe --update --db-path "IDE/db/hf_models.db" --verbose
```

### #11. `--debug`
- **Category:** Global Execution & Resource Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Outputs exhaustive low-level diagnostic traces, memory allocations, IPC messages, and raw errors.

```powershell
# Example for #11: --debug
cli.exe --rest-rl status --debug
```

### #12. `--selection-strategy`
- **Category:** Global Execution & Resource Flags
- **Argument Type:** `String`
- **Default Value:** `multi_objective`
- **Accepted Parameters:** multi_objective, popularity, freshness, performance, size_optimized
- **Description:** Specifies the Pareto optimization strategy used to score and rank candidate models from SQLite.

```powershell
# Example for #12: --selection-strategy
cli.exe --task text-generation --selection-strategy popularity --prompt "Generate REST client"
```

### #13. `--language`
- **Category:** Global Execution & Resource Flags
- **Argument Type:** `String`
- **Default Value:** `en`
- **Accepted Parameters:** ISO 639-1 two-letter code (e.g. en, fr, de, es, zh, ja)
- **Description:** Configures the target linguistic locale for model prompt templates, tokenizers, and responses.

```powershell
# Example for #13: --language
cli.exe --prompt "Translate invoice summary" --language fr
```

### #14. `--gpu`
- **Category:** Global Execution & Resource Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Forces GPU acceleration (CUDA, ROCm, Vulkan) and aborts if hardware acceleration is unavailable.

```powershell
# Example for #14: --gpu
cli.exe --fusion --fusion-models 3 --gpu --prompt "Synthesize microkernel design"
```

### #15. `--cpu`
- **Category:** Global Execution & Resource Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Forces CPU-only execution, disabling GPU kernel initialization and saving VRAM.

```powershell
# Example for #15: --cpu
cli.exe --fusion --cpu --prompt "Parse CSV dataset and compute stats"
```

### #16. `--api-keys`
- **Category:** Global Execution & Resource Flags
- **Argument Type:** `String`
- **Default Value:** `None`
- **Accepted Parameters:** Path to a JSON file containing provider API keys
- **Description:** Loads provider credentials (HuggingFace, OpenAI, Anthropic) from a structured JSON file.

```powershell
# Example for #16: --api-keys
cli.exe --api-keys "credentials/keys.json" --use-openai --prompt "Run code analysis"
```

### #17. `--sys-info`
- **Category:** Global Execution & Resource Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Detects and prints CPU, RAM, available memory, GPU model, VRAM, and storage resources in JSON format.

```powershell
# Example for #17: --sys-info
cli.exe --sys-info
```

### #18. `--save-model`
- **Category:** Global Execution & Resource Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Serializes and persists the trained ML model selector weights and routing policy to disk.

```powershell
# Example for #18: --save-model
cli.exe --enable-ml-selection --ml-retrain --save-model
```

### #19. `--load-model`
- **Category:** Global Execution & Resource Flags
- **Argument Type:** `String`
- **Default Value:** `None`
- **Accepted Parameters:** Path to serialized ML model weights file
- **Description:** Loads pre-trained model selection weights from disk for offline deterministic routing.

```powershell
# Example for #19: --load-model
cli.exe --load-model "models/custom_router.bin" --enable-ml-selection
```

---

## 2. Machine Learning Model Selection (#20 - #26)

This section details the **7 flags** belonging to **Machine Learning Model Selection**.

### #20. `--enable-ml-selection`
- **Category:** Machine Learning Model Selection
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Enables the machine-learning classifier to pick optimal models based on task, prompt, and system resources.

```powershell
# Example for #20: --enable-ml-selection
cli.exe --enable-ml-selection --prompt "Identify SQL injection vulnerabilities"
```

### #21. `--ml-learning`
- **Category:** Machine Learning Model Selection
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Activates online reinforcement learning to update selection weights based on execution success rates.

```powershell
# Example for #21: --ml-learning
cli.exe --enable-ml-selection --ml-learning --prompt "Refactor concurrent queue"
```

### #22. `--ml-ensemble-method`
- **Category:** Machine Learning Model Selection
- **Argument Type:** `String`
- **Default Value:** `weighted_voting`
- **Accepted Parameters:** weighted_voting, majority_vote, stacking, average
- **Description:** Sets the ensemble aggregation algorithm for combining predictions across multiple ML meta-models.

```powershell
# Example for #22: --ml-ensemble-method
cli.exe --enable-ml-selection --ml-ensemble-method weighted_voting
```

### #23. `--ml-confidence-threshold`
- **Category:** Machine Learning Model Selection
- **Argument Type:** `f64`
- **Default Value:** `0.6`
- **Accepted Parameters:** Float between 0.0 and 1.0 (e.g. 0.6, 0.75, 0.85)
- **Description:** Minimum confidence required to accept ML model routing; lower scores trigger fallback heuristics.

```powershell
# Example for #23: --ml-confidence-threshold
cli.exe --enable-ml-selection --ml-confidence-threshold 0.75
```

### #24. `--ml-analytics`
- **Category:** Machine Learning Model Selection
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Prints statistical reports of model routing decisions, classification accuracy, and confidence metrics.

```powershell
# Example for #24: --ml-analytics
cli.exe --ml-analytics
```

### #25. `--ml-retrain`
- **Category:** Machine Learning Model Selection
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Forces full retraining of the model selection routing classifiers using historical run records.

```powershell
# Example for #25: --ml-retrain
cli.exe --ml-retrain --save-model
```

### #26. `--ml-cleanup`
- **Category:** Machine Learning Model Selection
- **Argument Type:** `u32`
- **Default Value:** `None`
- **Accepted Parameters:** Integer number of days (e.g. 30, 60, 90)
- **Description:** Purges historical ML execution telemetry and reward logs older than the specified retention days.

```powershell
# Example for #26: --ml-cleanup
cli.exe --ml-cleanup 30
```

---

## 3. SINQ Quantization Engine (#27 - #31)

This section details the **5 flags** belonging to **SINQ Quantization Engine**.

### #27. `--sinq`
- **Category:** SINQ Quantization Engine
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Enables SINQ (Sub-4-bit Integer Non-linear Quantization) for high-efficiency low-memory model inference.

```powershell
# Example for #27: --sinq
cli.exe --sinq --prompt "Generate an AES-256 GCM encryption routine"
```

### #28. `--sinq-nbits`
- **Category:** SINQ Quantization Engine
- **Argument Type:** `u32`
- **Default Value:** `4`
- **Accepted Parameters:** Integer bit-width: 2, 3, 4, 8
- **Description:** Specifies the target bit precision for SINQ weight quantization (default: 4).

```powershell
# Example for #28: --sinq-nbits
cli.exe --sinq --sinq-nbits 4 --prompt "Quantize and run code generation"
```

### #29. `--sinq-group-size`
- **Category:** SINQ Quantization Engine
- **Argument Type:** `u32`
- **Default Value:** `64`
- **Accepted Parameters:** Integer power of 2: 32, 64, 128, 256
- **Description:** Specifies the number of consecutive weight elements sharing quantization scale and zero-point parameters.

```powershell
# Example for #29: --sinq-group-size
cli.exe --sinq --sinq-group-size 64
```

### #30. `--sinq-tiling-mode`
- **Category:** SINQ Quantization Engine
- **Argument Type:** `String`
- **Default Value:** `1D`
- **Accepted Parameters:** 1D, 2D, block, row
- **Description:** Configures tensor tiling strategy for SINQ quantization matrix kernels.

```powershell
# Example for #30: --sinq-tiling-mode
cli.exe --sinq --sinq-tiling-mode 1D
```

### #31. `--sinq-method`
- **Category:** SINQ Quantization Engine
- **Argument Type:** `String`
- **Default Value:** `sinq`
- **Accepted Parameters:** sinq, dynamic, static, symmetric
- **Description:** Selects the mathematical quantization formulation (default: sinq).

```powershell
# Example for #31: --sinq-method
cli.exe --sinq --sinq-method sinq
```

---

## 4. Innovation & Cognitive Systems (#32 - #37)

This section details the **6 flags** belonging to **Innovation & Cognitive Systems**.

### #32. `--enable-innovations`
- **Category:** Innovation & Cognitive Systems
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Activates all ModelFusion cognitive innovation modules including workflow optimization and predictive planning.

```powershell
# Example for #32: --enable-innovations
cli.exe --enable-innovations --prompt "Design an asynchronous multi-producer multi-consumer queue"
```

### #33. `--workflow-optimization`
- **Category:** Innovation & Cognitive Systems
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Applies cognitive pipeline restructuring to minimize latency and memory churn across subtasks.

```powershell
# Example for #33: --workflow-optimization
cli.exe --workflow-optimization --folder "crates/" --prompt "Audit compilation bottlenecks"
```

### #34. `--semantic-analysis`
- **Category:** Innovation & Cognitive Systems
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Performs deep semantic AST and intent analysis on codebases and input prompts.

```powershell
# Example for #34: --semantic-analysis
cli.exe --semantic-analysis --file "crates/core/src/router.rs"
```

### #35. `--temporal-tracking`
- **Category:** Innovation & Cognitive Systems
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Tracks semantic modifications and architectural drift across code revisions over time.

```powershell
# Example for #35: --temporal-tracking
cli.exe --temporal-tracking --folder "src/"
```

### #36. `--predictive-mode`
- **Category:** Innovation & Cognitive Systems
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Uses speculative ghost modeling to anticipate subsequent user commands and pre-cache inference results.

```powershell
# Example for #36: --predictive-mode
cli.exe --predictive-mode --prompt "Refactor state machine for high throughput"
```

### #37. `--innovation-level`
- **Category:** Innovation & Cognitive Systems
- **Argument Type:** `u32`
- **Default Value:** `2`
- **Accepted Parameters:** Integer: 1 (conservative), 2 (balanced), 3 (experimental)
- **Description:** Configures aggressiveness and heuristic exploration depth of innovation subsystems (default: 2).

```powershell
# Example for #37: --innovation-level
cli.exe --enable-innovations --innovation-level 2
```

---

## 5. HyDE Search & Web Retrieval (#38 - #46)

This section details the **9 flags** belonging to **HyDE Search & Web Retrieval**.

### #38. `--enable-hyde`
- **Category:** HyDE Search & Web Retrieval
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Activates Hypothetical Document Embeddings (HyDE) for superior semantic document and code retrieval.

```powershell
# Example for #38: --enable-hyde
cli.exe --enable-hyde --search-query "Zero-copy ring buffer in Rust"
```

### #39. `--use-hyde`
- **Category:** HyDE Search & Web Retrieval
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Enables interactive HyDE query refinement and hypothetical response generation before searching.

```powershell
# Example for #39: --use-hyde
cli.exe --use-hyde --prompt "How does Windows Job Object termination provide sub-50ms preemption?"
```

### #40. `--hyde-variants`
- **Category:** HyDE Search & Web Retrieval
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Generates multiple hypothetical answers across diverse temperature seeds to maximize embedding recall.

```powershell
# Example for #40: --hyde-variants
cli.exe --enable-hyde --hyde-variants --search-query "SIMD vectorization in AVX-512"
```

### #41. `--add-documents`
- **Category:** HyDE Search & Web Retrieval
- **Argument Type:** `String`
- **Default Value:** `None`
- **Accepted Parameters:** Path to document, file, or directory
- **Description:** Ingests and indexes local files or Markdown docs into the HyDE vector embedding database.

```powershell
# Example for #41: --add-documents
cli.exe --add-documents "docs/architecture.md"
```

### #42. `--search-query`
- **Category:** HyDE Search & Web Retrieval
- **Argument Type:** `String`
- **Default Value:** `None`
- **Accepted Parameters:** Query string
- **Description:** Executes a semantic vector similarity search against indexed codebase and documentation chunks.

```powershell
# Example for #42: --search-query
cli.exe --search-query "pareto optimal model selection algorithm"
```

### #43. `--research`
- **Category:** HyDE Search & Web Retrieval
- **Argument Type:** `String`
- **Default Value:** `None`
- **Aliases:** `--reseach`
- **Accepted Parameters:** Research topic query string (alias: --reseach)
- **Description:** Autonomous deep research agent performing multi-hop search, recursive web scraping, and reasoning synthesis.

```powershell
# Example for #43: --research
cli.exe --research "Latest advances in GRPO and reasoning model distillation 2026"
```

### #44. `--search`
- **Category:** HyDE Search & Web Retrieval
- **Argument Type:** `String`
- **Default Value:** `None`
- **Aliases:** `--serarch`
- **Accepted Parameters:** Search query string (alias: --serarch)
- **Description:** Performs real-time web search and fast extractive summarization using open-weight local models.

```powershell
# Example for #44: --search
cli.exe --search "Rust tokio broadcast channel lag handling"
```

### #45. `--top-k`
- **Category:** HyDE Search & Web Retrieval
- **Argument Type:** `u32`
- **Default Value:** `5`
- **Accepted Parameters:** Integer number of results (e.g. 3, 5, 10, 20)
- **Description:** Specifies the number of top-ranking search results or document passages to return (default: 5).

```powershell
# Example for #45: --top-k
cli.exe --search-query "memory safety invariants" --top-k 5
```

### #46. `--demo-hyde`
- **Category:** HyDE Search & Web Retrieval
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Runs an interactive end-to-end demonstration of HyDE hypothetical vector generation and retrieval.

```powershell
# Example for #46: --demo-hyde
cli.exe --demo-hyde
```

---

## 6. System & Orchestration Commands (#47 - #87)

This section details the **41 flags** belonging to **System & Orchestration Commands**.

### #47. `--active-model`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Aliases:** `--active-models`, `--current-model`, `--current-models`, `--ide-model`, `--ide-models`, `--models-in-use`
- **Accepted Parameters:** Boolean switch (no value, aliases: --active-models, --current-model, --current-models, --ide-model, --ide-models, --models-in-use)
- **Description:** Inspects and displays all active models across Ollama VRAM/RAM runtime, SQLite task models, and OpenVINO cache.

```powershell
# Example for #47: --active-model
cli.exe --active-model --db-path "IDE/db/hf_models.db"
```

### #48. `--stats`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Displays global catalog statistics, model counts per Hugging Face task, and database health metrics.

```powershell
# Example for #48: --stats
cli.exe --stats --db-path "IDE/db/hf_models.db"
```

### #49. `--tasks`
- **Category:** System & Orchestration Commands
- **Argument Type:** `String`
- **Default Value:** `None`
- **Accepted Parameters:** Optional task filter string: audio, image, text, code, all
- **Description:** Lists all 45+ supported Hugging Face task types and their currently registered models.

```powershell
# Example for #49: --tasks
cli.exe --tasks vision
```

### #50. `--update`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Fast curated update: indexes top ~6,500 production workhorse models and provisions matching Ollama model.

```powershell
# Example for #50: --update
cli.exe --update --db-path "IDE/db/hf_models.db"
```

### #51. `--updatedb`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Full registry crawler: ingests all 2M+ models from Hugging Face Hub via cursor pagination (1,000/batch).

```powershell
# Example for #51: --updatedb
cli.exe --updatedb --db-path "IDE/db/hf_models.db"
```

### #52. `--max-models`
- **Category:** System & Orchestration Commands
- **Argument Type:** `usize`
- **Default Value:** `None`
- **Accepted Parameters:** Positive integer (e.g. 10000, 50000, 100000)
- **Description:** Caps the total number of models ingested from Hugging Face Hub during a --updatedb crawl run.

```powershell
# Example for #52: --max-models
cli.exe --updatedb --max-models 50000 --db-path "IDE/db/hf_models.db"
```

### #53. `--restore`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Restores ModelFusion configuration and SQLite catalog databases from verified recovery backups.

```powershell
# Example for #53: --restore
cli.exe --restore
```

### #54. `--decision-stats`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Displays historical statistics on Pareto model routing decisions, execution latencies, and fallback events.

```powershell
# Example for #54: --decision-stats
cli.exe --decision-stats
```

### #55. `--novel-ai-stats`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Displays operational telemetry and metrics for novel AI components (SINQ, HyDE, predictive reasoning).

```powershell
# Example for #55: --novel-ai-stats
cli.exe --novel-ai-stats
```

### #56. `--performance-stats`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Outputs hardware utilization, inference throughput (tokens/second), memory footprint, and queue delays.

```powershell
# Example for #56: --performance-stats
cli.exe --performance-stats
```

### #57. `--cache-stats`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Displays cache hit ratios, storage utilization, and eviction counters for prompt and IR caches.

```powershell
# Example for #57: --cache-stats
cli.exe --cache-stats
```

### #58. `--clearcache`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Evicts all transient cache stores, prompt response buffers, and downloaded temporary model weights.

```powershell
# Example for #58: --clearcache
cli.exe --clearcache
```

### #59. `--analytics-demo`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Executes a synthetic benchmark demonstrating multi-criteria model ranking and Pareto frontier visualization.

```powershell
# Example for #59: --analytics-demo
cli.exe --analytics-demo
```

### #60. `--model-ranking`
- **Category:** System & Orchestration Commands
- **Argument Type:** `String`
- **Default Value:** `None`
- **Accepted Parameters:** Optional task name (e.g. text-generation, code-vulnerability-detection)
- **Description:** Computes and displays Pareto-ranked scorecards for models registered under the specified task.

```powershell
# Example for #60: --model-ranking
cli.exe --model-ranking text-generation
```

### #61. `--model-recommendations`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Generates hardware-tailored model recommendations based on current CPU, GPU VRAM, and RAM availability.

```powershell
# Example for #61: --model-recommendations
cli.exe --model-recommendations
```

### #62. `--full`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Enables comprehensive multi-stage analysis, activating cross-model validation and deep auditing.

```powershell
# Example for #62: --full
cli.exe --full --prompt "Exhaustive verification of cryptographic primitives"
```

### #63. `--fusion`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Executes prompt across a panel of models simultaneously and arbitrates responses into a synthesized consensus.

```powershell
# Example for #63: --fusion
cli.exe --fusion --fusion-models 3 --prompt "Formulate optimal distributed consensus protocol"
```

### #64. `--fusion-models`
- **Category:** System & Orchestration Commands
- **Argument Type:** `usize`
- **Default Value:** `0`
- **Accepted Parameters:** Integer count (0 = dynamic based on RAM/VRAM, or 2, 3, 5)
- **Description:** Specifies the number of models in the fusion arbitration panel (default: 0 = dynamic auto-sizing).

```powershell
# Example for #64: --fusion-models
cli.exe --fusion --fusion-models 3 --prompt "Design zero-trust authentication service"
```

### #65. `--fusion-mode`
- **Category:** System & Orchestration Commands
- **Argument Type:** `String`
- **Default Value:** `multi-model`
- **Accepted Parameters:** multi-model (N different models), multi-sample (1 model, N temperature samples)
- **Description:** Execution topology for Model Fusion: 'multi-model' (diverse models) or 'multi-sample' (fast local sampling).

```powershell
# Example for #65: --fusion-mode
cli.exe --fusion --fusion-mode multi-sample --prompt "Review code for race conditions"
```

### #66. `--ollama`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Routes inference execution directly through local Ollama daemon rather than Python transformers.

```powershell
# Example for #66: --ollama
cli.exe --ollama --prompt "Explain RAII in modern C++"
```

### #67. `--openvino`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Uses Intel OpenVINO runtime for AVX-512 / AMX accelerated CPU inference.

```powershell
# Example for #67: --openvino
cli.exe --openvino --prompt "Optimize matrix multiplication kernel"
```

### #68. `--onnx`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Uses ONNX Runtime cross-platform inference engine for quantized and exported models.

```powershell
# Example for #68: --onnx
cli.exe --onnx --prompt "Run classification on feature vector"
```

### #69. `--vllm`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value, Linux only)
- **Description:** Uses vLLM PagedAttention inference engine for ultra-high throughput GPU serving.

```powershell
# Example for #69: --vllm
cli.exe --vllm --prompt "High-throughput batch code summarization"
```

### #70. `--model`
- **Category:** System & Orchestration Commands
- **Argument Type:** `String`
- **Default Value:** `None`
- **Accepted Parameters:** Valid HuggingFace or Ollama model tag (e.g. qwen2.5:14b, deepseek-ai/DeepSeek-R1)
- **Description:** Overrides Pareto routing heuristics and forces execution using a specific model identifier.

```powershell
# Example for #70: --model
cli.exe --model "qwen2.5:14b" --prompt "Refactor threadpool scheduler"
```

### #71. `--prepare-model`
- **Category:** System & Orchestration Commands
- **Argument Type:** `String`
- **Default Value:** `None`
- **Accepted Parameters:** Hugging Face model repository ID
- **Description:** Pre-converts and quantizes a Hugging Face model into OpenVINO Intermediate Representation (IR).

```powershell
# Example for #71: --prepare-model
cli.exe --prepare-model "Qwen/Qwen2.5-Coder-7B" --weight-format int8
```

### #72. `--prepare-all-models`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Batch converts all eligible top-tier models in the catalog database to OpenVINO IR format.

```powershell
# Example for #72: --prepare-all-models
cli.exe --prepare-all-models --weight-format int8
```

### #73. `--weight-format`
- **Category:** System & Orchestration Commands
- **Argument Type:** `String`
- **Default Value:** `int8`
- **Accepted Parameters:** fp16, int8, int4
- **Description:** Specifies weight precision for OpenVINO Intermediate Representation exports (default: int8).

```powershell
# Example for #73: --weight-format
cli.exe --prepare-model "Qwen/Qwen2.5-7B" --weight-format int4
```

### #74. `--ov-model-dir`
- **Category:** System & Orchestration Commands
- **Argument Type:** `String`
- **Default Value:** `ov_models`
- **Accepted Parameters:** Directory path
- **Description:** Directory where compiled OpenVINO IR models (.xml / .bin) are stored and cached (default: ov_models).

```powershell
# Example for #74: --ov-model-dir
cli.exe --openvino --ov-model-dir "D:/models/openvino_cache"
```

### #75. `--context-auto`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Automatically generates background domain context using a thinking model (e.g. DeepSeek-R1) prior to answering.

```powershell
# Example for #75: --context-auto
cli.exe --context-auto --prompt "Implement distributed rate limiter"
```

### #76. `--context`
- **Category:** System & Orchestration Commands
- **Argument Type:** `String`
- **Default Value:** `None`
- **Accepted Parameters:** Text string or file path containing background context
- **Description:** Injects explicit contextual background information into the system prompt.

```powershell
# Example for #76: --context
cli.exe --context "Target OS: Windows 11 64-bit, Kernel: NT 10.0" --prompt "Generate IPC pipe setup"
```

### #77. `--report`
- **Category:** System & Orchestration Commands
- **Argument Type:** `String`
- **Default Value:** `None`
- **Accepted Parameters:** File path or directory destination
- **Description:** Specifies file path or directory destination where generated analysis reports should be saved.

```powershell
# Example for #77: --report
cli.exe --datascience --file "data/telemetry.csv" --report "reports/quarterly_audit.md"
```

### #78. `--reporttype`
- **Category:** System & Orchestration Commands
- **Argument Type:** `String`
- **Default Value:** `md`
- **Accepted Parameters:** pdf, text, json, md, word
- **Description:** Format of the generated report document (default: md).

```powershell
# Example for #78: --reporttype
cli.exe --datascience --file "data/sales.csv" --report "reports/summary.pdf" --reporttype pdf
```

### #79. `--delegation`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Uses hierarchical delegation pattern to route individual subtasks to specialized domain models.

```powershell
# Example for #79: --delegation
cli.exe --delegation --prompt "Perform vulnerability audit and synthesize remediation patch"
```

### #80. `--recursion`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Enables recursive task decomposition to break complex multifaceted prompts into atomic solvable subtasks.

```powershell
# Example for #80: --recursion
cli.exe --recursion --prompt "Design complete operating system memory manager"
```

### #81. `--getvino`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Launches background synchronization daemon to periodically pull pre-optimized OpenVINO IR models.

```powershell
# Example for #81: --getvino
cli.exe --getvino --getvino-interval 24
```

### #82. `--getvino-interval`
- **Category:** System & Orchestration Commands
- **Argument Type:** `u64`
- **Default Value:** `24`
- **Accepted Parameters:** Integer hours (e.g. 12, 24, 48)
- **Description:** Interval in hours between background OpenVINO model synchronization cycles (default: 24).

```powershell
# Example for #82: --getvino-interval
cli.exe --getvino --getvino-interval 12
```

### #83. `--rest-rl`
- **Category:** System & Orchestration Commands
- **Argument Type:** `Vec<String`
- **Default Value:** `None`
- **Aliases:** `--rl`
- **Accepted Parameters:** Optional action arguments: status, start, stop, enqueue <task> (alias: --rl)
- **Description:** Controls and inspects the HugOS ReST-RL / GRPO background reinforcement learning daemon.

```powershell
# Example for #83: --rest-rl
cli.exe --rest-rl status
```

### #84. `--real-options`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Applies financial real options valuation to maintain hot standby backup models during critical tasks.

```powershell
# Example for #84: --real-options
cli.exe --real-options --task text-generation --prompt "Generate high-reliability payment handler"
```

### #85. `--prompt-quality-scoring`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Evaluates clarity, specificity, and completeness of input prompts and suggests automated optimizations.

```powershell
# Example for #85: --prompt-quality-scoring
cli.exe --prompt-quality-scoring --prompt "Refactor database pool"
```

### #86. `--ml-fallback`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `true`
- **Accepted Parameters:** true, false
- **Description:** Enables automated heuristic fallback when ML selection confidence falls below minimum threshold (default: true).

```powershell
# Example for #86: --ml-fallback
cli.exe --ml-fallback true --enable-ml-selection
```

### #87. `--jupyter`
- **Category:** System & Orchestration Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Spawns or connects to an interactive Jupyter notebook server for data exploration and visualization.

```powershell
# Example for #87: --jupyter
cli.exe --jupyter
```

---

## 7. Data Science & Tabular Workflows (#88 - #90)

This section details the **3 flags** belonging to **Data Science & Tabular Workflows**.

### #88. `--dataanalyst`
- **Category:** Data Science & Tabular Workflows
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Aliases:** `--data-analyst`, `--datanalyst`
- **Accepted Parameters:** Boolean switch (aliases: --data-analyst, --datanalyst)
- **Description:** Launches the automated Data Analyst pipeline: parses CSV/Excel, performs statistical profiling, and summarizes trends.

```powershell
# Example for #88: --dataanalyst
cli.exe --dataanalyst --file "data/q3_metrics.csv" --prompt "Analyze customer churn correlates"
```

### #89. `--datascience`
- **Category:** Data Science & Tabular Workflows
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Runs the comprehensive Data Science workflow: data cleaning, feature engineering, correlation analysis, and predictive modeling.

```powershell
# Example for #89: --datascience
cli.exe --datascience --file "data/transactions.csv" --report "reports/fraud_analysis.md"
```

### #90. `--export-pdf`
- **Category:** Data Science & Tabular Workflows
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Renders analysis reports, statistical tables, and visualizations directly into a formatted PDF document.

```powershell
# Example for #90: --export-pdf
cli.exe --datascience --file "data/telemetry.csv" --export-pdf --report "reports/metrics.pdf"
```

---

## 8. Response Evaluation & Planning (#91 - #93)

This section details the **3 flags** belonging to **Response Evaluation & Planning**.

### #91. `--score`
- **Category:** Response Evaluation & Planning
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Calculates multi-dimensional quality metrics (coherence, accuracy, safety, code validity) on generated output.

```powershell
# Example for #91: --score
cli.exe --score --prompt "Write a lock-free ring buffer in Rust"
```

### #92. `--judge`
- **Category:** Response Evaluation & Planning
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Invokes an independent LLM-as-a-Judge model to critically review, score, and certify model outputs.

```powershell
# Example for #92: --judge
cli.exe --judge --prompt "Evaluate concurrent hash map implementations for race conditions"
```

### #93. `--plan`
- **Category:** Response Evaluation & Planning
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Synthesizes a structured multi-phase execution blueprint with verification gates prior to generating code.

```powershell
# Example for #93: --plan
cli.exe --plan --prompt "Migrate monolithic web service to asynchronous actor architecture"
```

---

## 9. Binary & PE Executable Analysis (#94 - #94)

This section details the **1 flags** belonging to **Binary & PE Executable Analysis**.

### #94. `--pe-header-extraction`
- **Category:** Binary & PE Executable Analysis
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (requires --file <EXE/DLL>)
- **Description:** Extracts PE header structures, section tables, imported DLLs, export symbols, and digital signatures from Windows binaries.

```powershell
# Example for #94: --pe-header-extraction
cli.exe --pe-header-extraction --file "target/release/cli.exe"
```

---

## 10. Multi-Modal Task Routing Flags (#95 - #156)

This section details the **62 flags** belonging to **Multi-Modal Task Routing Flags**.

### #95. `--text-classification`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Routes prompt to top-ranked text classification models for categorizing unstructured text into target classes.

```powershell
# Example for #95: --text-classification
cli.exe --text-classification --prompt "Analyze user feedback for sentiment polarity: Excellent product!"
```

### #96. `--token-classification`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Routes prompt to token classification models for token-level labelling (NER, POS tagging, grammatical syntax).

```powershell
# Example for #96: --token-classification
cli.exe --token-classification --prompt "Extract entity tokens from: Satya Nadella visited Microsoft Dublin"
```

### #97. `--question-answering`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Extracts precise answers to queries given explicit reference context passages.

```powershell
# Example for #97: --question-answering
cli.exe --question-answering --context "ModelFusion uses SQLite for offline cataloging." --prompt "Where does ModelFusion store models?"
```

### #98. `--text-generation`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Standard autoregressive text generation for reasoning, creative writing, and documentation.

```powershell
# Example for #98: --text-generation
cli.exe --text-generation --prompt "Synthesize an architectural summary of modern microkernels"
```

### #99. `--summarization`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Distills long-form technical reports, transcripts, and documents into concise summaries.

```powershell
# Example for #99: --summarization
cli.exe --summarization --file "RFC-9110.txt" --prompt "Provide a 3-bullet executive summary"
```

### #100. `--translation`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Translates text across languages preserving technical terminology and semantic intent.

```powershell
# Example for #100: --translation
cli.exe --translation --language de --prompt "High-performance software systems require rigorous profiling."
```

### #101. `--fill-mask`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Predicts masked tokens within sentences using bidirectional masked language models (e.g. BERT/RoBERTa).

```powershell
# Example for #101: --fill-mask
cli.exe --fill-mask --prompt "The capital of France is [MASK]."
```

### #102. `--text2text-generation`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Performs arbitrary sequence-to-sequence text transformation and structured rewriting.

```powershell
# Example for #102: --text2text-generation
cli.exe --text2text-generation --prompt "Rewrite this function signature to use async/await syntax: fn fetch() -> Result<Data>;"
```

### #103. `--language-detection`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Identifies the primary natural language of input passages with associated confidence scores.

```powershell
# Example for #103: --language-detection
cli.exe --language-detection --prompt "Bonjour tout le monde, comment allez-vous aujourd'hui?"
```

### #104. `--grammar-correction`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Detects grammatical, syntactic, and spelling errors and provides corrected text.

```powershell
# Example for #104: --grammar-correction
cli.exe --grammar-correction --prompt "They is going to the store yesterday."
```

### #105. `--paraphrase-generation`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Rephrases sentences into alternative expressions while preserving core semantics.

```powershell
# Example for #105: --paraphrase-generation
cli.exe --paraphrase-generation --prompt "Optimizing throughput requires eliminating contention on shared locks."
```

### #106. `--causal-language-modeling`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Raw autoregressive next-token continuation modeling without instruction fine-tuning templates.

```powershell
# Example for #106: --causal-language-modeling
cli.exe --causal-language-modeling --prompt "In distributed computing, the CAP theorem states that"
```

### #107. `--zero-shot-classification`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Classifies text into dynamic arbitrary categories without requiring task-specific training data.

```powershell
# Example for #107: --zero-shot-classification
cli.exe --zero-shot-classification --prompt "The server latency spiked to 450ms during flash sale" --context "billing, infrastructure, security"
```

### #108. `--feature-extraction`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Outputs dense multidimensional mathematical vector embeddings for downstream similarity and clustering.

```powershell
# Example for #108: --feature-extraction
cli.exe --feature-extraction --prompt "Embed this semantic concept into vector space"
```

### #109. `--sentence-similarity`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Computes cosine similarity between sentence embeddings to determine semantic equivalence.

```powershell
# Example for #109: --sentence-similarity
cli.exe --sentence-similarity --prompt "Rust memory safety" --context "C++ RAII lifetime semantics"
```

### #110. `--anonymization`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Redacts or obfuscates personally identifiable information (PII) from text.

```powershell
# Example for #110: --anonymization
cli.exe --anonymization --prompt "Patient John Doe, SSN 000-12-3456, visited Dr. Smith at Boston Clinic."
```

### #111. `--coreference-resolution`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Resolves referring expressions and pronouns to their corresponding entity antecedents.

```powershell
# Example for #111: --coreference-resolution
cli.exe --coreference-resolution --prompt "Alice told Bob she would review his pull request once it passed CI."
```

### #112. `--spam-detection`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Classifies incoming email, chat, or form submissions as legitimate or unsolicited spam.

```powershell
# Example for #112: --spam-detection
cli.exe --spam-detection --prompt "Congratulations! You have won a $1,000 gift card. Click here to claim."
```

### #113. `--malware-text-detection`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Analyzes scripts, command strings, and payloads for indicators of malicious code execution.

```powershell
# Example for #113: --malware-text-detection
cli.exe --malware-text-detection --prompt "powershell.exe -enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoAZQBjAHQAIABOAGUAdAAuAFcAZQBiAEMAbABpAGUAbgB0ACkALgBEAG8AdwBuAGwAbwBhAGQAUwB0AHIAaQBuAGcAKAApAA=="
```

### #114. `--phishing-detection`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Scans communication text and URLs for social engineering patterns and credential harvesting indicators.

```powershell
# Example for #114: --phishing-detection
cli.exe --phishing-detection --prompt "Urgent: Your bank account has been locked. Verify credentials immediately at http://secure-bank-login.xyz"
```

### #115. `--pii-detection`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Identifies sensitive personal information (credit cards, social security numbers, phone numbers, addresses).

```powershell
# Example for #115: --pii-detection
cli.exe --pii-detection --file "logs/access.log"
```

### #116. `--hate-speech-detection`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Detects toxic language, hate speech, and derogatory slurs for moderation compliance.

```powershell
# Example for #116: --hate-speech-detection
cli.exe --hate-speech-detection --prompt "Audit this user comment for safety compliance: ..."
```

### #117. `--cyberbullying-detection`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Identifies targeted harassment, bullying, and intimidation patterns in social interactions.

```powershell
# Example for #117: --cyberbullying-detection
cli.exe --cyberbullying-detection --prompt "Analyze chat transcript for harassment: ..."
```

### #118. `--fake-news-detection`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Evaluates news claims against factual verification patterns to identify misinformation.

```powershell
# Example for #118: --fake-news-detection
cli.exe --fake-news-detection --prompt "Breaking: Moon discovered to be made of green cheese according to NASA"
```

### #119. `--legal-judgment-classification`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Classifies judicial opinions, motions, and court rulings by legal domain and judicial outcome.

```powershell
# Example for #119: --legal-judgment-classification
cli.exe --legal-judgment-classification --file "briefs/motion_to_dismiss.txt"
```

### #120. `--contract-clause-classification`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Identifies contract clause types (Indemnification, Termination, Confidentiality, Governing Law).

```powershell
# Example for #120: --contract-clause-classification
cli.exe --contract-clause-classification --prompt "Either party may terminate this agreement upon 30 days written notice."
```

### #121. `--case-outcome-prediction`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Analyzes litigation filings to estimate probable case outcomes based on legal precedents.

```powershell
# Example for #121: --case-outcome-prediction
cli.exe --case-outcome-prediction --file "cases/brief_summary.txt"
```

### #122. `--financial-ner`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Extracts financial entities (ticker symbols, revenue metrics, institutions, currencies) from reports.

```powershell
# Example for #122: --financial-ner
cli.exe --financial-ner --prompt "Goldman Sachs reported Q2 net revenues of $12.73 billion, up 17% year-over-year."
```

### #123. `--legal-ner`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Identifies legal citations, statutory codes, case names, and jurisdictional entities.

```powershell
# Example for #123: --legal-ner
cli.exe --legal-ner --prompt "Under 17 U.S.C. § 107, the defendant asserts a fair use affirmative defense."
```

### #124. `--biomedical-ner`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Extracts biomedical entities (genes, proteins, diseases, drug compounds, dosages) from scientific papers.

```powershell
# Example for #124: --biomedical-ner
cli.exe --biomedical-ner --prompt "Metformin administration reduced HbA1c levels in type 2 diabetes mellitus patients."
```

### #125. `--chemical-reaction-ner`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Extracts chemical reagents, catalysts, reaction conditions, and products from chemistry literature.

```powershell
# Example for #125: --chemical-reaction-ner
cli.exe --chemical-reaction-ner --prompt "Benzene reacts with nitric acid in the presence of sulfuric acid to form nitrobenzene."
```

### #126. `--financial-sentiment-analysis`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Classifies investor sentiment (bullish, bearish, neutral) from financial news and 10-K filings.

```powershell
# Example for #126: --financial-sentiment-analysis
cli.exe --financial-sentiment-analysis --prompt "Operating margins expanded 140 basis points despite macroeconomic headwinds."
```

### #127. `--scientific-abstract-summarization`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Distills dense academic papers into structured problem-method-result research summaries.

```powershell
# Example for #127: --scientific-abstract-summarization
cli.exe --scientific-abstract-summarization --file "papers/quantum_computing.txt"
```

### #128. `--emotion-detection`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Detects nuanced emotional states (joy, frustration, anger, surprise, sadness) in conversational text.

```powershell
# Example for #128: --emotion-detection
cli.exe --emotion-detection --prompt "I am completely overwhelmed by how supportive the team has been!"
```

### #129. `--sarcasm-detection`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Identifies ironic and sarcastic linguistic markers where intended meaning differs from literal text.

```powershell
# Example for #129: --sarcasm-detection
cli.exe --sarcasm-detection --prompt "Oh fantastic, another mandatory unskippable meeting on a Friday afternoon."
```

### #130. `--stance-detection`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Determines whether an author is in favor of, against, or neutral toward a given target topic.

```powershell
# Example for #130: --stance-detection
cli.exe --stance-detection --prompt "Nuclear energy is indispensable for decarbonizing the global power grid." --context "Clean Energy Policy"
```

### #131. `--bias-detection`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Identifies cognitive, gender, political, or demographic biases in articles and datasets.

```powershell
# Example for #131: --bias-detection
cli.exe --bias-detection --prompt "Audit this editorial for political or demographic framing bias: ..."
```

### #132. `--hallucination-detection`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Detects ungrounded assertions or factual inconsistencies between generated responses and reference premises.

```powershell
# Example for #132: --hallucination-detection
cli.exe --hallucination-detection --context "The Eiffel Tower was completed in 1889." --prompt "The Eiffel Tower was built by Napoleon in 1804."
```

### #133. `--reading-level-assessment`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Calculates reading comprehension levels (Flesch-Kincaid, Lexile) to assess documentation accessibility.

```powershell
# Example for #133: --reading-level-assessment
cli.exe --reading-level-assessment --file "docs/getting_started.md"
```

### #134. `--generation-groundedness`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Evaluates whether model assertions are strictly supported by provided source materials.

```powershell
# Example for #134: --generation-groundedness
cli.exe --generation-groundedness --context "docs/spec.txt" --prompt "Does the generated implementation conform to specification?"
```

### #135. `--citation-intent-classification`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Classifies the purpose of academic citations (background, methodology, comparison, critique).

```powershell
# Example for #135: --citation-intent-classification
cli.exe --citation-intent-classification --prompt "Our method builds directly upon the architecture introduced by Vaswani et al. (2017)."
```

### #136. `--code-vulnerability-detection`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Scans source code for security vulnerabilities, buffer overflows, integer wraps, and memory safety flaws.

```powershell
# Example for #136: --code-vulnerability-detection
cli.exe --code-vulnerability-detection --file "crates/core/src/parser.rs"
```

### #137. `--code-summary-generation`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Synthesizes concise technical docstrings and architectural summaries from complex functions and classes.

```powershell
# Example for #137: --code-summary-generation
cli.exe --code-summary-generation --file "crates/cli/src/main.rs"
```

### #138. `--code-clone-detection`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Identifies duplicate, near-duplicate, and copy-pasted code fragments across a repository.

```powershell
# Example for #138: --code-clone-detection
cli.exe --code-clone-detection --folder "src/"
```

### #139. `--image-classification`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (requires --file <IMAGE>)
- **Description:** Routes image files to vision classification models to identify primary subjects and visual categories.

```powershell
# Example for #139: --image-classification
cli.exe --image-classification --file "assets/icon.png"
```

### #140. `--object-detection`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (requires --file <IMAGE>)
- **Description:** Locates and bounds distinct objects (buttons, windows, icons) within an input image.

```powershell
# Example for #140: --object-detection
cli.exe --object-detection --file "assets/screenshot.png"
```

### #141. `--image-segmentation`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (requires --file <IMAGE>)
- **Description:** Segments images at pixel-level resolution to isolate foreground objects from background canvas.

```powershell
# Example for #141: --image-segmentation
cli.exe --image-segmentation --file "assets/diagram.png"
```

### #142. `--visual-question-answering`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (requires --file <IMAGE>)
- **Description:** Answers natural language questions about the visual content of an uploaded image or diagram.

```powershell
# Example for #142: --visual-question-answering
cli.exe --visual-question-answering --file "assets/chart.png" --prompt "What is the value of Q3 revenue shown in the bar chart?"
```

### #143. `--document-question-answering`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (requires --file <PDF/IMAGE>)
- **Description:** Extracts answers directly from scanned documents, structured PDF forms, and invoices.

```powershell
# Example for #143: --document-question-answering
cli.exe --document-question-answering --file "invoices/inv_2026.pdf" --prompt "What is the total due and payment date?"
```

### #144. `--zero-shot-image-classification`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (requires --file <IMAGE>)
- **Description:** Classifies images into arbitrary candidate categories using multi-modal vision-language models (CLIP).

```powershell
# Example for #144: --zero-shot-image-classification
cli.exe --zero-shot-image-classification --file "assets/device.jpg" --context "laptop, tablet, desktop, smartphone"
```

### #145. `--depth-estimation`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (requires --file <IMAGE>)
- **Description:** Computes monocular depth maps predicting distance from camera for each pixel in an image.

```powershell
# Example for #145: --depth-estimation
cli.exe --depth-estimation --file "assets/scene.jpg"
```

### #146. `--image-feature-extraction`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (requires --file <IMAGE>)
- **Description:** Extracts high-dimensional visual embedding vectors for image retrieval and similarity matching.

```powershell
# Example for #146: --image-feature-extraction
cli.exe --image-feature-extraction --file "assets/logo.png"
```

### #147. `--automatic-speech-recognition`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (requires --file <AUDIO>)
- **Description:** Transcribes spoken audio into timestamped text transcripts using state-of-the-art ASR models (Whisper).

```powershell
# Example for #147: --automatic-speech-recognition
cli.exe --automatic-speech-recognition --file "recordings/standup.wav"
```

### #148. `--audio-classification`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (requires --file <AUDIO>)
- **Description:** Classifies audio files by acoustic event, musical genre, or environmental sound category.

```powershell
# Example for #148: --audio-classification
cli.exe --audio-classification --file "telemetry/engine_sound.wav"
```

### #149. `--voice-activity-detection`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (requires --file <AUDIO>)
- **Description:** Detects presence of human speech vs silence or background noise in audio streams.

```powershell
# Example for #149: --voice-activity-detection
cli.exe --voice-activity-detection --file "audio/meeting.mp3"
```

### #150. `--emotion-recognition`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (requires --file <AUDIO>)
- **Description:** Detects vocal emotion and caller stress levels from audio pitch, tone, and prosody.

```powershell
# Example for #150: --emotion-recognition
cli.exe --emotion-recognition --file "support/call_sample.wav"
```

### #151. `--video-classification`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (requires --file <VIDEO>)
- **Description:** Classifies video clips into activity, genre, or scene categories using temporal-spatial models.

```powershell
# Example for #151: --video-classification
cli.exe --video-classification --file "media/demo.mp4"
```

### #152. `--text-to-speech`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Synthesizes natural-sounding speech audio from text input using neural vocoders.

```powershell
# Example for #152: --text-to-speech
cli.exe --text-to-speech --prompt "Build 148 compilation complete. All 161 CLI flags verified."
```

### #153. `--text-to-image`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Generates high-resolution images from text descriptions using latent diffusion models.

```powershell
# Example for #153: --text-to-image
cli.exe --text-to-image --prompt "Futuristic AI operating system terminal in glowing amber cyberpunk aesthetic"
```

### #154. `--image-super-resolution`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (requires --file <IMAGE>)
- **Description:** Upscales low-resolution images using neural super-resolution to enhance clarity and detail.

```powershell
# Example for #154: --image-super-resolution
cli.exe --image-super-resolution --file "assets/low_res_badge.png"
```

### #155. `--table-question-answering`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (requires --file <CSV/XLSX>)
- **Description:** Answers natural language queries by executing relational reasoning directly over tabular datasets.

```powershell
# Example for #155: --table-question-answering
cli.exe --table-question-answering --file "data/benchmarks.csv" --prompt "Which model achieved the highest throughput?"
```

### #156. `--feature-ranking`
- **Category:** Multi-Modal Task Routing Flags
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (requires --file <CSV>)
- **Description:** Ranks input dataset features by predictive importance, information gain, and variance.

```powershell
# Example for #156: --feature-ranking
cli.exe --feature-ranking --file "data/training_set.csv" --prompt "Target: churn"
```

---

## 11. Server & Database Commands (#157 - #161)

This section details the **5 flags** belonging to **Server & Database Commands**.

### #157. `--db-path`
- **Category:** Server & Database Commands
- **Argument Type:** `String`
- **Default Value:** `None`
- **Accepted Parameters:** Path to SQLite database file
- **Description:** Specifies custom SQLite database path for ModelFusion catalog, models, and embeddings.

```powershell
# Example for #157: --db-path
cli.exe --db-path "IDE/db/hf_models.db" --stats
```

### #158. `--server`
- **Category:** Server & Database Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Launches the ModelFusion HTTP REST API server for external IDE and headless automation access.

```powershell
# Example for #158: --server
cli.exe --server --port 5000 --db-path "IDE/db/hf_models.db"
```

### #159. `--enable-slash-commands`
- **Category:** Server & Database Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Enables parsing of interactive IDE slash commands (/datascience, /search, /jupyter, /evolve) from raw prompts.

```powershell
# Example for #159: --enable-slash-commands
cli.exe --enable-slash-commands --prompt "/datascience data/sales.csv"
```

### #160. `--port`
- **Category:** Server & Database Commands
- **Argument Type:** `u16`
- **Default Value:** `5000`
- **Accepted Parameters:** Valid TCP port number: 1024 - 65535 (default: 5000)
- **Description:** Specifies the TCP port on which the ModelFusion HTTP API server listens (default: 5000).

```powershell
# Example for #160: --port
cli.exe --server --port 8080
```

### #161. `--mcp`
- **Category:** Server & Database Commands
- **Argument Type:** `bool`
- **Default Value:** `false`
- **Accepted Parameters:** Boolean switch (no value)
- **Description:** Runs ModelFusion as a Model Context Protocol (MCP) server communicating over standard input/output (stdio).

```powershell
# Example for #161: --mcp
cli.exe --mcp --db-path "IDE/db/hf_models.db"
```

---

## 12. Universal Agent Directives & Slash Commands

HugOS IDE and ModelFusion integrate **10 universal compound agent directives** matching full Antigravity operating system capabilities:

| Command | Flag | Argument Type | Description | Executable Example |
|:---|:---|:---:|:---|:---|
| `/btw` | `--btw <QUESTION>` | `String` | Quick side questions in isolated context without polluting main thread | `cli.exe --btw "What is RAII in modern C++?"` |
| `/goal` | `--goal <OBJECTIVE>` | `String` | Autonomous goal-seeking loop enqueued to ReST-RL daemon | `cli.exe --goal "Optimize AST parser and run verification"` |
| `/schedule` | `--schedule <DIRECTIVE>` | `String` | Background timer and recurring cron execution schedules | `cli.exe --schedule "cron '*/5 * * * *' health check"` |
| `/browser` | `--browser <URL/QUERY>` | `String` | Web research agent with live page scraping and synthesis | `cli.exe --browser "https://huggingface.co/models"` |
| `/plan` | `--plan` | `bool` | Rigorous architectural blueprint with invariant & verification matrix | `cli.exe --plan --prompt "Design lock-free queue"` |
| `/grill-me` | `--grill-me` | `bool` | Lead Architect Socratic interview to align on design decisions | `cli.exe --grill-me --prompt "Refactoring IPC pipeline"` |
| `/teamwork-preview` | `--teamwork-preview` | `bool` | Multi-agent collaborative topology with Mermaid sequence diagrams | `cli.exe --teamwork-preview` |
| `/learn` | `--learn <RULE>` | `String` | Captures and persists reusable engineering rules into `.hugos/rules/` | `cli.exe --learn "Always check free RAM before allocating models"` |
| `/boost` | `--boost` | `bool` | High-compute multi-sample consensus deliberation over top models | `cli.exe --boost --prompt "Solve dining philosophers"` |
| `/generative_ui` | `--generative-ui <SPEC>` | `String` | Generates self-contained interactive HTML/Tailwind widgets | `cli.exe --generative-ui "GPU VRAM telemetry widget"` |

---

## Appendix: Developer Tooling, Source Patching & Legacy Aliases

ModelFusion contains **13 supplementary internal and legacy flags** used for source code patching, IDE build pipelines, legacy compatibility, and AST code graph operations.

| # | Flag | Type | Default | Description | Example |
|:---:|:---|:---:|:---:|:---|:---|
| 162 | `--sentiment` | `bool` | `false` | Legacy alias for --text-classification. Analyzes text sentiment. | `cli.exe --sentiment --prompt "The update succeeded without any issues!"` |
| 163 | `--question` | `bool` | `false` | Legacy alias for --question-answering. Runs question answering mode. | `cli.exe --question --context "Build 148 is released." --prompt "What build is released?"` |
| 164 | `--ner` | `bool` | `false` | Legacy alias for --token-classification. Runs named entity recognition. | `cli.exe --ner --prompt "Sundar Pichai announced Google Antigravity in Mountain View."` |
| 165 | `--summary` | `bool` | `false` | Legacy alias for --summarization. Runs text summarization. | `cli.exe --summary --file "docs/README.md"` |
| 166 | `--patch-ide` | `bool` | `false` | Clones upstream VSCode from GitHub and applies HugOS IDE branding, telemetry rewiring, and updater patches. | `cli.exe --patch-ide --ide-src-dir "IDE/src" --shallow` |
| 167 | `--ide-src-dir <IDE_SRC_DIR>` | `String` | `IDE/src` | Target directory where VSCode source code is cloned and patched. | `cli.exe --patch-ide --ide-src-dir "IDE/src"` |
| 168 | `--shallow` | `bool` | `false` | Executes git clone with --depth 1 during IDE source patching for accelerated downloads. | `cli.exe --patch-ide --shallow` |
| 169 | `--vscode-tag <VSCODE_TAG>` | `Option<String>` | `None` | Specifies a particular VSCode git tag to checkout and patch (e.g. '1.96.0'). | `cli.exe --patch-ide --vscode-tag "1.96.0"` |
| 170 | `--graph-index` | `bool` | `false` | Extracts codebase AST symbols, functions, calls, and type hierarchies into SQLite knowledge graph. | `cli.exe --graph-index --workspace "."` |
| 171 | `--graph-query <GRAPH_QUERY>` | `Option<String>` | `None` | Executes semantic code queries against the indexed codebase AST knowledge graph. | `cli.exe --graph-query "parse_args_struct" --workspace "."` |
| 172 | `--workspace <WORKSPACE>` | `Option<String>` | `None` | Sets target workspace directory for knowledge graph AST indexing and query resolution. | `cli.exe --graph-index --workspace "d:/harfile/ModelFusion"` |
| 173 | `--query-type <QUERY_TYPE>` | `String` | `all` | Knowledge graph query filter: all, symbol, calls, callees, callers, impls, refs, search. | `cli.exe --graph-query "Args" --query-type symbol` |
| 174 | `--force` | `bool` | `false` | Forces complete re-indexing of all workspace files into AST knowledge graph ignoring cache. | `cli.exe --graph-index --force --workspace "."` |

### `--sentiment`
- **Description:** Legacy alias for --text-classification. Analyzes text sentiment.
- **Type:** `bool` | **Default:** `false`

```powershell
cli.exe --sentiment --prompt "The update succeeded without any issues!"
```

### `--question`
- **Description:** Legacy alias for --question-answering. Runs question answering mode.
- **Type:** `bool` | **Default:** `false`

```powershell
cli.exe --question --context "Build 148 is released." --prompt "What build is released?"
```

### `--ner`
- **Description:** Legacy alias for --token-classification. Runs named entity recognition.
- **Type:** `bool` | **Default:** `false`

```powershell
cli.exe --ner --prompt "Sundar Pichai announced Google Antigravity in Mountain View."
```

### `--summary`
- **Description:** Legacy alias for --summarization. Runs text summarization.
- **Type:** `bool` | **Default:** `false`

```powershell
cli.exe --summary --file "docs/README.md"
```

### `--patch-ide`
- **Description:** Clones upstream VSCode from GitHub and applies HugOS IDE branding, telemetry rewiring, and updater patches.
- **Type:** `bool` | **Default:** `false`

```powershell
cli.exe --patch-ide --ide-src-dir "IDE/src" --shallow
```

### `--ide-src-dir <IDE_SRC_DIR>`
- **Description:** Target directory where VSCode source code is cloned and patched.
- **Type:** `String` | **Default:** `IDE/src`

```powershell
cli.exe --patch-ide --ide-src-dir "IDE/src"
```

### `--shallow`
- **Description:** Executes git clone with --depth 1 during IDE source patching for accelerated downloads.
- **Type:** `bool` | **Default:** `false`

```powershell
cli.exe --patch-ide --shallow
```

### `--vscode-tag <VSCODE_TAG>`
- **Description:** Specifies a particular VSCode git tag to checkout and patch (e.g. '1.96.0').
- **Type:** `Option<String>` | **Default:** `None`

```powershell
cli.exe --patch-ide --vscode-tag "1.96.0"
```

### `--graph-index`
- **Description:** Extracts codebase AST symbols, functions, calls, and type hierarchies into SQLite knowledge graph.
- **Type:** `bool` | **Default:** `false`

```powershell
cli.exe --graph-index --workspace "."
```

### `--graph-query <GRAPH_QUERY>`
- **Description:** Executes semantic code queries against the indexed codebase AST knowledge graph.
- **Type:** `Option<String>` | **Default:** `None`

```powershell
cli.exe --graph-query "parse_args_struct" --workspace "."
```

### `--workspace <WORKSPACE>`
- **Description:** Sets target workspace directory for knowledge graph AST indexing and query resolution.
- **Type:** `Option<String>` | **Default:** `None`

```powershell
cli.exe --graph-index --workspace "d:/harfile/ModelFusion"
```

### `--query-type <QUERY_TYPE>`
- **Description:** Knowledge graph query filter: all, symbol, calls, callees, callers, impls, refs, search.
- **Type:** `String` | **Default:** `all`

```powershell
cli.exe --graph-query "Args" --query-type symbol
```

### `--force`
- **Description:** Forces complete re-indexing of all workspace files into AST knowledge graph ignoring cache.
- **Type:** `bool` | **Default:** `false`

```powershell
cli.exe --graph-index --force --workspace "."
```

---

## Positional Arguments

### `query` (Prompt Query Fallback)
- **Type:** `Option<String>`
- **Description:** Any trailing positional string passed without a flag is automatically captured as the prompt query directive.
```powershell
cli.exe "Explain the Pareto frontier model selection algorithm"
```