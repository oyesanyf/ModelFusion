#!/usr/bin/env python3
"""
Generate docs/CLI_REFERENCE.md with all 161 flags, numbered master table,
categorized sections, and concrete executable examples for every single flag.
"""

import json
import os
import sys

# Flag descriptions, valid values, and concrete executable examples for all 161 flags
FLAG_DETAILS = {
    # 1. Global Execution & Resource Flags (19 flags)
    "file": {
        "params": "Valid path to a readable file (.py, .rs, .csv, .json, .txt)",
        "example": "cli.exe --file \"crates/core/src/lib.rs\" --prompt \"Review this file for potential memory leaks\"",
        "desc": "Specify a local file path as target input for analysis, code review, or ingestion into the model context."
    },
    "folder": {
        "params": "Valid path to a readable directory",
        "example": "cli.exe --folder \"src/\" --prompt \"Generate an architectural overview of all Rust modules in this folder\"",
        "desc": "Specify a target directory for batch scanning, multi-file code review, or directory-level summarization."
    },
    "prompt": {
        "params": "Text string containing instructions, questions, or directives",
        "example": "cli.exe --prompt \"Explain the zero-VRAM graduated verification mechanism in HugOS\"",
        "desc": "Primary instruction or question passed to the dynamically selected local or remote model."
    },
    "task": {
        "params": "HuggingFace task name (e.g. text-generation, image-classification, summarization)",
        "example": "cli.exe --task text-generation --prompt \"Write a high-performance LRU cache in Rust\"",
        "desc": "Explicitly force routing to a specific Hugging Face task pipeline instead of automatic classification."
    },
    "budget": {
        "params": "Floating point monetary limit in USD (e.g. 5.0, 10.0, 25.5)",
        "example": "cli.exe --prompt \"Deep refactor of parsing pipeline\" --budget 2.5",
        "desc": "Sets a maximum monetary budget cap for commercial cloud LLM provider API consumption."
    },
    "chain-of-thought": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --prompt \"Solve the dining philosophers problem with deadlock avoidance\" --chain-of-thought",
        "desc": "Enforces step-by-step reasoning tokens prior to synthesizing final code and answers."
    },
    "config": {
        "params": "Path to a custom JSON configuration file",
        "example": "cli.exe --config \"config/production_overrides.json\" --active-model",
        "desc": "Overrides default engine configuration with settings from a specified JSON configuration file."
    },
    "enable-ml": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --prompt \"Classify cybersecurity incident logs\" --enable-ml",
        "desc": "Enables machine-learning enhancements across model routing, feature extraction, and heuristics."
    },
    "use-openai": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --prompt \"Summarize multi-tier architecture\" --use-openai",
        "desc": "Directs execution to OpenAI API endpoints (requires OPENAI_API_KEY) rather than local Ollama models."
    },
    "verbose": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --update --db-path \"IDE/db/hf_models.db\" --verbose",
        "desc": "Enables detailed informational console logs, pipeline transition notices, and execution progress."
    },
    "debug": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --rest-rl status --debug",
        "desc": "Outputs exhaustive low-level diagnostic traces, memory allocations, IPC messages, and raw errors."
    },
    "selection-strategy": {
        "params": "multi_objective, popularity, freshness, performance, size_optimized",
        "example": "cli.exe --task text-generation --selection-strategy popularity --prompt \"Generate REST client\"",
        "desc": "Specifies the Pareto optimization strategy used to score and rank candidate models from SQLite."
    },
    "language": {
        "params": "ISO 639-1 two-letter code (e.g. en, fr, de, es, zh, ja)",
        "example": "cli.exe --prompt \"Translate invoice summary\" --language fr",
        "desc": "Configures the target linguistic locale for model prompt templates, tokenizers, and responses."
    },
    "gpu": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --fusion --fusion-models 3 --gpu --prompt \"Synthesize microkernel design\"",
        "desc": "Forces GPU acceleration (CUDA, ROCm, Vulkan) and aborts if hardware acceleration is unavailable."
    },
    "cpu": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --fusion --cpu --prompt \"Parse CSV dataset and compute stats\"",
        "desc": "Forces CPU-only execution, disabling GPU kernel initialization and saving VRAM."
    },
    "api-keys": {
        "params": "Path to a JSON file containing provider API keys",
        "example": "cli.exe --api-keys \"credentials/keys.json\" --use-openai --prompt \"Run code analysis\"",
        "desc": "Loads provider credentials (HuggingFace, OpenAI, Anthropic) from a structured JSON file."
    },
    "sys-info": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --sys-info",
        "desc": "Detects and prints CPU, RAM, available memory, GPU model, VRAM, and storage resources in JSON format."
    },
    "save-model": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --enable-ml-selection --ml-retrain --save-model",
        "desc": "Serializes and persists the trained ML model selector weights and routing policy to disk."
    },
    "load-model": {
        "params": "Path to serialized ML model weights file",
        "example": "cli.exe --load-model \"models/custom_router.bin\" --enable-ml-selection",
        "desc": "Loads pre-trained model selection weights from disk for offline deterministic routing."
    },

    # 2. Machine Learning Model Selection (7 flags)
    "enable-ml-selection": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --enable-ml-selection --prompt \"Identify SQL injection vulnerabilities\"",
        "desc": "Enables the machine-learning classifier to pick optimal models based on task, prompt, and system resources."
    },
    "ml-learning": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --enable-ml-selection --ml-learning --prompt \"Refactor concurrent queue\"",
        "desc": "Activates online reinforcement learning to update selection weights based on execution success rates."
    },
    "ml-ensemble-method": {
        "params": "weighted_voting, majority_vote, stacking, average",
        "example": "cli.exe --enable-ml-selection --ml-ensemble-method weighted_voting",
        "desc": "Sets the ensemble aggregation algorithm for combining predictions across multiple ML meta-models."
    },
    "ml-confidence-threshold": {
        "params": "Float between 0.0 and 1.0 (e.g. 0.6, 0.75, 0.85)",
        "example": "cli.exe --enable-ml-selection --ml-confidence-threshold 0.75",
        "desc": "Minimum confidence required to accept ML model routing; lower scores trigger fallback heuristics."
    },
    "ml-analytics": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --ml-analytics",
        "desc": "Prints statistical reports of model routing decisions, classification accuracy, and confidence metrics."
    },
    "ml-retrain": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --ml-retrain --save-model",
        "desc": "Forces full retraining of the model selection routing classifiers using historical run records."
    },
    "ml-cleanup": {
        "params": "Integer number of days (e.g. 30, 60, 90)",
        "example": "cli.exe --ml-cleanup 30",
        "desc": "Purges historical ML execution telemetry and reward logs older than the specified retention days."
    },

    # 3. SINQ Quantization Engine (5 flags)
    "sinq": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --sinq --prompt \"Generate an AES-256 GCM encryption routine\"",
        "desc": "Enables SINQ (Sub-4-bit Integer Non-linear Quantization) for high-efficiency low-memory model inference."
    },
    "sinq-nbits": {
        "params": "Integer bit-width: 2, 3, 4, 8",
        "example": "cli.exe --sinq --sinq-nbits 4 --prompt \"Quantize and run code generation\"",
        "desc": "Specifies the target bit precision for SINQ weight quantization (default: 4)."
    },
    "sinq-group-size": {
        "params": "Integer power of 2: 32, 64, 128, 256",
        "example": "cli.exe --sinq --sinq-group-size 64",
        "desc": "Specifies the number of consecutive weight elements sharing quantization scale and zero-point parameters."
    },
    "sinq-tiling-mode": {
        "params": "1D, 2D, block, row",
        "example": "cli.exe --sinq --sinq-tiling-mode 1D",
        "desc": "Configures tensor tiling strategy for SINQ quantization matrix kernels."
    },
    "sinq-method": {
        "params": "sinq, dynamic, static, symmetric",
        "example": "cli.exe --sinq --sinq-method sinq",
        "desc": "Selects the mathematical quantization formulation (default: sinq)."
    },

    # 4. Innovation & Cognitive Systems (6 flags)
    "enable-innovations": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --enable-innovations --prompt \"Design an asynchronous multi-producer multi-consumer queue\"",
        "desc": "Activates all ModelFusion cognitive innovation modules including workflow optimization and predictive planning."
    },
    "workflow-optimization": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --workflow-optimization --folder \"crates/\" --prompt \"Audit compilation bottlenecks\"",
        "desc": "Applies cognitive pipeline restructuring to minimize latency and memory churn across subtasks."
    },
    "semantic-analysis": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --semantic-analysis --file \"crates/core/src/router.rs\"",
        "desc": "Performs deep semantic AST and intent analysis on codebases and input prompts."
    },
    "temporal-tracking": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --temporal-tracking --folder \"src/\"",
        "desc": "Tracks semantic modifications and architectural drift across code revisions over time."
    },
    "predictive-mode": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --predictive-mode --prompt \"Refactor state machine for high throughput\"",
        "desc": "Uses speculative ghost modeling to anticipate subsequent user commands and pre-cache inference results."
    },
    "innovation-level": {
        "params": "Integer: 1 (conservative), 2 (balanced), 3 (experimental)",
        "example": "cli.exe --enable-innovations --innovation-level 2",
        "desc": "Configures aggressiveness and heuristic exploration depth of innovation subsystems (default: 2)."
    },

    # 5. HyDE Search & Web Retrieval (9 flags)
    "enable-hyde": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --enable-hyde --search-query \"Zero-copy ring buffer in Rust\"",
        "desc": "Activates Hypothetical Document Embeddings (HyDE) for superior semantic document and code retrieval."
    },
    "use-hyde": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --use-hyde --prompt \"How does Windows Job Object termination provide sub-50ms preemption?\"",
        "desc": "Enables interactive HyDE query refinement and hypothetical response generation before searching."
    },
    "hyde-variants": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --enable-hyde --hyde-variants --search-query \"SIMD vectorization in AVX-512\"",
        "desc": "Generates multiple hypothetical answers across diverse temperature seeds to maximize embedding recall."
    },
    "add-documents": {
        "params": "Path to document, file, or directory",
        "example": "cli.exe --add-documents \"docs/architecture.md\"",
        "desc": "Ingests and indexes local files or Markdown docs into the HyDE vector embedding database."
    },
    "search-query": {
        "params": "Query string",
        "example": "cli.exe --search-query \"pareto optimal model selection algorithm\"",
        "desc": "Executes a semantic vector similarity search against indexed codebase and documentation chunks."
    },
    "research": {
        "params": "Research topic query string (alias: --reseach)",
        "example": "cli.exe --research \"Latest advances in GRPO and reasoning model distillation 2026\"",
        "desc": "Autonomous deep research agent performing multi-hop search, recursive web scraping, and reasoning synthesis."
    },
    "search": {
        "params": "Search query string (alias: --serarch)",
        "example": "cli.exe --search \"Rust tokio broadcast channel lag handling\"",
        "desc": "Performs real-time web search and fast extractive summarization using open-weight local models."
    },
    "top-k": {
        "params": "Integer number of results (e.g. 3, 5, 10, 20)",
        "example": "cli.exe --search-query \"memory safety invariants\" --top-k 5",
        "desc": "Specifies the number of top-ranking search results or document passages to return (default: 5)."
    },
    "demo-hyde": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --demo-hyde",
        "desc": "Runs an interactive end-to-end demonstration of HyDE hypothetical vector generation and retrieval."
    },

    # 6. System & Orchestration Commands (41 flags)
    "active-model": {
        "params": "Boolean switch (no value, aliases: --active-models, --current-model, --current-models, --ide-model, --ide-models, --models-in-use)",
        "example": "cli.exe --active-model --db-path \"IDE/db/hf_models.db\"",
        "desc": "Inspects and displays all active models across Ollama VRAM/RAM runtime, SQLite task models, and OpenVINO cache."
    },
    "stats": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --stats --db-path \"IDE/db/hf_models.db\"",
        "desc": "Displays global catalog statistics, model counts per Hugging Face task, and database health metrics."
    },
    "tasks": {
        "params": "Optional task filter string: audio, image, text, code, all",
        "example": "cli.exe --tasks vision",
        "desc": "Lists all 45+ supported Hugging Face task types and their currently registered models."
    },
    "update": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --update --db-path \"IDE/db/hf_models.db\"",
        "desc": "Fast curated update: indexes top ~6,500 production workhorse models and provisions matching Ollama model."
    },
    "updatedb": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --updatedb --db-path \"IDE/db/hf_models.db\"",
        "desc": "Full registry crawler: ingests all 2M+ models from Hugging Face Hub via cursor pagination (1,000/batch)."
    },
    "max-models": {
        "params": "Positive integer (e.g. 10000, 50000, 100000)",
        "example": "cli.exe --updatedb --max-models 50000 --db-path \"IDE/db/hf_models.db\"",
        "desc": "Caps the total number of models ingested from Hugging Face Hub during a --updatedb crawl run."
    },
    "restore": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --restore",
        "desc": "Restores ModelFusion configuration and SQLite catalog databases from verified recovery backups."
    },
    "decision-stats": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --decision-stats",
        "desc": "Displays historical statistics on Pareto model routing decisions, execution latencies, and fallback events."
    },
    "novel-ai-stats": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --novel-ai-stats",
        "desc": "Displays operational telemetry and metrics for novel AI components (SINQ, HyDE, predictive reasoning)."
    },
    "performance-stats": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --performance-stats",
        "desc": "Outputs hardware utilization, inference throughput (tokens/second), memory footprint, and queue delays."
    },
    "cache-stats": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --cache-stats",
        "desc": "Displays cache hit ratios, storage utilization, and eviction counters for prompt and IR caches."
    },
    "clearcache": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --clearcache",
        "desc": "Evicts all transient cache stores, prompt response buffers, and downloaded temporary model weights."
    },
    "analytics-demo": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --analytics-demo",
        "desc": "Executes a synthetic benchmark demonstrating multi-criteria model ranking and Pareto frontier visualization."
    },
    "model-ranking": {
        "params": "Optional task name (e.g. text-generation, code-vulnerability-detection)",
        "example": "cli.exe --model-ranking text-generation",
        "desc": "Computes and displays Pareto-ranked scorecards for models registered under the specified task."
    },
    "model-recommendations": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --model-recommendations",
        "desc": "Generates hardware-tailored model recommendations based on current CPU, GPU VRAM, and RAM availability."
    },
    "full": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --full --prompt \"Exhaustive verification of cryptographic primitives\"",
        "desc": "Enables comprehensive multi-stage analysis, activating cross-model validation and deep auditing."
    },
    "fusion": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --fusion --fusion-models 3 --prompt \"Formulate optimal distributed consensus protocol\"",
        "desc": "Executes prompt across a panel of models simultaneously and arbitrates responses into a synthesized consensus."
    },
    "fusion-models": {
        "params": "Integer count (0 = dynamic based on RAM/VRAM, or 2, 3, 5)",
        "example": "cli.exe --fusion --fusion-models 3 --prompt \"Design zero-trust authentication service\"",
        "desc": "Specifies the number of models in the fusion arbitration panel (default: 0 = dynamic auto-sizing)."
    },
    "fusion-mode": {
        "params": "multi-model (N different models), multi-sample (1 model, N temperature samples)",
        "example": "cli.exe --fusion --fusion-mode multi-sample --prompt \"Review code for race conditions\"",
        "desc": "Execution topology for Model Fusion: 'multi-model' (diverse models) or 'multi-sample' (fast local sampling)."
    },
    "ollama": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --ollama --prompt \"Explain RAII in modern C++\"",
        "desc": "Routes inference execution directly through local Ollama daemon rather than Python transformers."
    },
    "openvino": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --openvino --prompt \"Optimize matrix multiplication kernel\"",
        "desc": "Uses Intel OpenVINO runtime for AVX-512 / AMX accelerated CPU inference."
    },
    "onnx": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --onnx --prompt \"Run classification on feature vector\"",
        "desc": "Uses ONNX Runtime cross-platform inference engine for quantized and exported models."
    },
    "vllm": {
        "params": "Boolean switch (no value, Linux only)",
        "example": "cli.exe --vllm --prompt \"High-throughput batch code summarization\"",
        "desc": "Uses vLLM PagedAttention inference engine for ultra-high throughput GPU serving."
    },
    "model": {
        "params": "Valid HuggingFace or Ollama model tag (e.g. qwen2.5:14b, deepseek-ai/DeepSeek-R1)",
        "example": "cli.exe --model \"qwen2.5:14b\" --prompt \"Refactor threadpool scheduler\"",
        "desc": "Overrides Pareto routing heuristics and forces execution using a specific model identifier."
    },
    "prepare-model": {
        "params": "Hugging Face model repository ID",
        "example": "cli.exe --prepare-model \"Qwen/Qwen2.5-Coder-7B\" --weight-format int8",
        "desc": "Pre-converts and quantizes a Hugging Face model into OpenVINO Intermediate Representation (IR)."
    },
    "prepare-all-models": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --prepare-all-models --weight-format int8",
        "desc": "Batch converts all eligible top-tier models in the catalog database to OpenVINO IR format."
    },
    "weight-format": {
        "params": "fp16, int8, int4",
        "example": "cli.exe --prepare-model \"Qwen/Qwen2.5-7B\" --weight-format int4",
        "desc": "Specifies weight precision for OpenVINO Intermediate Representation exports (default: int8)."
    },
    "ov-model-dir": {
        "params": "Directory path",
        "example": "cli.exe --openvino --ov-model-dir \"D:/models/openvino_cache\"",
        "desc": "Directory where compiled OpenVINO IR models (.xml / .bin) are stored and cached (default: ov_models)."
    },
    "context-auto": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --context-auto --prompt \"Implement distributed rate limiter\"",
        "desc": "Automatically generates background domain context using a thinking model (e.g. DeepSeek-R1) prior to answering."
    },
    "context": {
        "params": "Text string or file path containing background context",
        "example": "cli.exe --context \"Target OS: Windows 11 64-bit, Kernel: NT 10.0\" --prompt \"Generate IPC pipe setup\"",
        "desc": "Injects explicit contextual background information into the system prompt."
    },
    "report": {
        "params": "File path or directory destination",
        "example": "cli.exe --datascience --file \"data/telemetry.csv\" --report \"reports/quarterly_audit.md\"",
        "desc": "Specifies file path or directory destination where generated analysis reports should be saved."
    },
    "reporttype": {
        "params": "pdf, text, json, md, word",
        "example": "cli.exe --datascience --file \"data/sales.csv\" --report \"reports/summary.pdf\" --reporttype pdf",
        "desc": "Format of the generated report document (default: md)."
    },
    "delegation": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --delegation --prompt \"Perform vulnerability audit and synthesize remediation patch\"",
        "desc": "Uses hierarchical delegation pattern to route individual subtasks to specialized domain models."
    },
    "recursion": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --recursion --prompt \"Design complete operating system memory manager\"",
        "desc": "Enables recursive task decomposition to break complex multifaceted prompts into atomic solvable subtasks."
    },
    "getvino": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --getvino --getvino-interval 24",
        "desc": "Launches background synchronization daemon to periodically pull pre-optimized OpenVINO IR models."
    },
    "getvino-interval": {
        "params": "Integer hours (e.g. 12, 24, 48)",
        "example": "cli.exe --getvino --getvino-interval 12",
        "desc": "Interval in hours between background OpenVINO model synchronization cycles (default: 24)."
    },
    "rest-rl": {
        "params": "Optional action arguments: status, start, stop, enqueue <task> (alias: --rl)",
        "example": "cli.exe --rest-rl status",
        "desc": "Controls and inspects the HugOS ReST-RL / GRPO background reinforcement learning daemon."
    },
    "real-options": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --real-options --task text-generation --prompt \"Generate high-reliability payment handler\"",
        "desc": "Applies financial real options valuation to maintain hot standby backup models during critical tasks."
    },
    "prompt-quality-scoring": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --prompt-quality-scoring --prompt \"Refactor database pool\"",
        "desc": "Evaluates clarity, specificity, and completeness of input prompts and suggests automated optimizations."
    },
    "ml-fallback": {
        "params": "true, false",
        "example": "cli.exe --ml-fallback true --enable-ml-selection",
        "desc": "Enables automated heuristic fallback when ML selection confidence falls below minimum threshold (default: true)."
    },
    "jupyter": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --jupyter",
        "desc": "Spawns or connects to an interactive Jupyter notebook server for data exploration and visualization."
    },

    # 7. Data Science & Tabular Workflows (3 flags)
    "dataanalyst": {
        "params": "Boolean switch (aliases: --data-analyst, --datanalyst)",
        "example": "cli.exe --dataanalyst --file \"data/q3_metrics.csv\" --prompt \"Analyze customer churn correlates\"",
        "desc": "Launches the automated Data Analyst pipeline: parses CSV/Excel, performs statistical profiling, and summarizes trends."
    },
    "datascience": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --datascience --file \"data/transactions.csv\" --report \"reports/fraud_analysis.md\"",
        "desc": "Runs the comprehensive Data Science workflow: data cleaning, feature engineering, correlation analysis, and predictive modeling."
    },
    "export-pdf": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --datascience --file \"data/telemetry.csv\" --export-pdf --report \"reports/metrics.pdf\"",
        "desc": "Renders analysis reports, statistical tables, and visualizations directly into a formatted PDF document."
    },

    # 8. Response Evaluation & Planning (3 flags)
    "score": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --score --prompt \"Write a lock-free ring buffer in Rust\"",
        "desc": "Calculates multi-dimensional quality metrics (coherence, accuracy, safety, code validity) on generated output."
    },
    "judge": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --judge --prompt \"Evaluate concurrent hash map implementations for race conditions\"",
        "desc": "Invokes an independent LLM-as-a-Judge model to critically review, score, and certify model outputs."
    },
    "plan": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --plan --prompt \"Migrate monolithic web service to asynchronous actor architecture\"",
        "desc": "Synthesizes a structured multi-phase execution blueprint with verification gates prior to generating code."
    },

    # 9. Binary & PE Executable Analysis (1 flag)
    "pe-header-extraction": {
        "params": "Boolean switch (requires --file <EXE/DLL>)",
        "example": "cli.exe --pe-header-extraction --file \"target/release/cli.exe\"",
        "desc": "Extracts PE header structures, section tables, imported DLLs, export symbols, and digital signatures from Windows binaries."
    },

    # 10. Multi-Modal Task Routing Flags (62 flags)
    "text-classification": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --text-classification --prompt \"Analyze user feedback for sentiment polarity: Excellent product!\"",
        "desc": "Routes prompt to top-ranked text classification models for categorizing unstructured text into target classes."
    },
    "token-classification": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --token-classification --prompt \"Extract entity tokens from: Satya Nadella visited Microsoft Dublin\"",
        "desc": "Routes prompt to token classification models for token-level labelling (NER, POS tagging, grammatical syntax)."
    },
    "question-answering": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --question-answering --context \"ModelFusion uses SQLite for offline cataloging.\" --prompt \"Where does ModelFusion store models?\"",
        "desc": "Extracts precise answers to queries given explicit reference context passages."
    },
    "text-generation": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --text-generation --prompt \"Synthesize an architectural summary of modern microkernels\"",
        "desc": "Standard autoregressive text generation for reasoning, creative writing, and documentation."
    },
    "summarization": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --summarization --file \"RFC-9110.txt\" --prompt \"Provide a 3-bullet executive summary\"",
        "desc": "Distills long-form technical reports, transcripts, and documents into concise summaries."
    },
    "translation": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --translation --language de --prompt \"High-performance software systems require rigorous profiling.\"",
        "desc": "Translates text across languages preserving technical terminology and semantic intent."
    },
    "fill-mask": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --fill-mask --prompt \"The capital of France is [MASK].\"",
        "desc": "Predicts masked tokens within sentences using bidirectional masked language models (e.g. BERT/RoBERTa)."
    },
    "text2text-generation": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --text2text-generation --prompt \"Rewrite this function signature to use async/await syntax: fn fetch() -> Result<Data>;\"",
        "desc": "Performs arbitrary sequence-to-sequence text transformation and structured rewriting."
    },
    "language-detection": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --language-detection --prompt \"Bonjour tout le monde, comment allez-vous aujourd'hui?\"",
        "desc": "Identifies the primary natural language of input passages with associated confidence scores."
    },
    "grammar-correction": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --grammar-correction --prompt \"They is going to the store yesterday.\"",
        "desc": "Detects grammatical, syntactic, and spelling errors and provides corrected text."
    },
    "paraphrase-generation": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --paraphrase-generation --prompt \"Optimizing throughput requires eliminating contention on shared locks.\"",
        "desc": "Rephrases sentences into alternative expressions while preserving core semantics."
    },
    "causal-language-modeling": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --causal-language-modeling --prompt \"In distributed computing, the CAP theorem states that\"",
        "desc": "Raw autoregressive next-token continuation modeling without instruction fine-tuning templates."
    },
    "zero-shot-classification": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --zero-shot-classification --prompt \"The server latency spiked to 450ms during flash sale\" --context \"billing, infrastructure, security\"",
        "desc": "Classifies text into dynamic arbitrary categories without requiring task-specific training data."
    },
    "feature-extraction": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --feature-extraction --prompt \"Embed this semantic concept into vector space\"",
        "desc": "Outputs dense multidimensional mathematical vector embeddings for downstream similarity and clustering."
    },
    "sentence-similarity": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --sentence-similarity --prompt \"Rust memory safety\" --context \"C++ RAII lifetime semantics\"",
        "desc": "Computes cosine similarity between sentence embeddings to determine semantic equivalence."
    },
    "anonymization": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --anonymization --prompt \"Patient John Doe, SSN 000-12-3456, visited Dr. Smith at Boston Clinic.\"",
        "desc": "Redacts or obfuscates personally identifiable information (PII) from text."
    },
    "coreference-resolution": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --coreference-resolution --prompt \"Alice told Bob she would review his pull request once it passed CI.\"",
        "desc": "Resolves referring expressions and pronouns to their corresponding entity antecedents."
    },
    "spam-detection": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --spam-detection --prompt \"Congratulations! You have won a $1,000 gift card. Click here to claim.\"",
        "desc": "Classifies incoming email, chat, or form submissions as legitimate or unsolicited spam."
    },
    "malware-text-detection": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --malware-text-detection --prompt \"powershell.exe -enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoAZQBjAHQAIABOAGUAdAAuAFcAZQBiAEMAbABpAGUAbgB0ACkALgBEAG8AdwBuAGwAbwBhAGQAUwB0AHIAaQBuAGcAKAApAA==\"",
        "desc": "Analyzes scripts, command strings, and payloads for indicators of malicious code execution."
    },
    "phishing-detection": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --phishing-detection --prompt \"Urgent: Your bank account has been locked. Verify credentials immediately at http://secure-bank-login.xyz\"",
        "desc": "Scans communication text and URLs for social engineering patterns and credential harvesting indicators."
    },
    "pii-detection": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --pii-detection --file \"logs/access.log\"",
        "desc": "Identifies sensitive personal information (credit cards, social security numbers, phone numbers, addresses)."
    },
    "hate-speech-detection": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --hate-speech-detection --prompt \"Audit this user comment for safety compliance: ...\"",
        "desc": "Detects toxic language, hate speech, and derogatory slurs for moderation compliance."
    },
    "cyberbullying-detection": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --cyberbullying-detection --prompt \"Analyze chat transcript for harassment: ...\"",
        "desc": "Identifies targeted harassment, bullying, and intimidation patterns in social interactions."
    },
    "fake-news-detection": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --fake-news-detection --prompt \"Breaking: Moon discovered to be made of green cheese according to NASA\"",
        "desc": "Evaluates news claims against factual verification patterns to identify misinformation."
    },
    "legal-judgment-classification": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --legal-judgment-classification --file \"briefs/motion_to_dismiss.txt\"",
        "desc": "Classifies judicial opinions, motions, and court rulings by legal domain and judicial outcome."
    },
    "contract-clause-classification": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --contract-clause-classification --prompt \"Either party may terminate this agreement upon 30 days written notice.\"",
        "desc": "Identifies contract clause types (Indemnification, Termination, Confidentiality, Governing Law)."
    },
    "case-outcome-prediction": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --case-outcome-prediction --file \"cases/brief_summary.txt\"",
        "desc": "Analyzes litigation filings to estimate probable case outcomes based on legal precedents."
    },
    "financial-ner": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --financial-ner --prompt \"Goldman Sachs reported Q2 net revenues of $12.73 billion, up 17% year-over-year.\"",
        "desc": "Extracts financial entities (ticker symbols, revenue metrics, institutions, currencies) from reports."
    },
    "legal-ner": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --legal-ner --prompt \"Under 17 U.S.C. § 107, the defendant asserts a fair use affirmative defense.\"",
        "desc": "Identifies legal citations, statutory codes, case names, and jurisdictional entities."
    },
    "biomedical-ner": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --biomedical-ner --prompt \"Metformin administration reduced HbA1c levels in type 2 diabetes mellitus patients.\"",
        "desc": "Extracts biomedical entities (genes, proteins, diseases, drug compounds, dosages) from scientific papers."
    },
    "chemical-reaction-ner": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --chemical-reaction-ner --prompt \"Benzene reacts with nitric acid in the presence of sulfuric acid to form nitrobenzene.\"",
        "desc": "Extracts chemical reagents, catalysts, reaction conditions, and products from chemistry literature."
    },
    "financial-sentiment-analysis": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --financial-sentiment-analysis --prompt \"Operating margins expanded 140 basis points despite macroeconomic headwinds.\"",
        "desc": "Classifies investor sentiment (bullish, bearish, neutral) from financial news and 10-K filings."
    },
    "scientific-abstract-summarization": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --scientific-abstract-summarization --file \"papers/quantum_computing.txt\"",
        "desc": "Distills dense academic papers into structured problem-method-result research summaries."
    },
    "emotion-detection": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --emotion-detection --prompt \"I am completely overwhelmed by how supportive the team has been!\"",
        "desc": "Detects nuanced emotional states (joy, frustration, anger, surprise, sadness) in conversational text."
    },
    "sarcasm-detection": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --sarcasm-detection --prompt \"Oh fantastic, another mandatory unskippable meeting on a Friday afternoon.\"",
        "desc": "Identifies ironic and sarcastic linguistic markers where intended meaning differs from literal text."
    },
    "stance-detection": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --stance-detection --prompt \"Nuclear energy is indispensable for decarbonizing the global power grid.\" --context \"Clean Energy Policy\"",
        "desc": "Determines whether an author is in favor of, against, or neutral toward a given target topic."
    },
    "bias-detection": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --bias-detection --prompt \"Audit this editorial for political or demographic framing bias: ...\"",
        "desc": "Identifies cognitive, gender, political, or demographic biases in articles and datasets."
    },
    "hallucination-detection": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --hallucination-detection --context \"The Eiffel Tower was completed in 1889.\" --prompt \"The Eiffel Tower was built by Napoleon in 1804.\"",
        "desc": "Detects ungrounded assertions or factual inconsistencies between generated responses and reference premises."
    },
    "reading-level-assessment": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --reading-level-assessment --file \"docs/getting_started.md\"",
        "desc": "Calculates reading comprehension levels (Flesch-Kincaid, Lexile) to assess documentation accessibility."
    },
    "generation-groundedness": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --generation-groundedness --context \"docs/spec.txt\" --prompt \"Does the generated implementation conform to specification?\"",
        "desc": "Evaluates whether model assertions are strictly supported by provided source materials."
    },
    "citation-intent-classification": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --citation-intent-classification --prompt \"Our method builds directly upon the architecture introduced by Vaswani et al. (2017).\"",
        "desc": "Classifies the purpose of academic citations (background, methodology, comparison, critique)."
    },
    "code-vulnerability-detection": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --code-vulnerability-detection --file \"crates/core/src/parser.rs\"",
        "desc": "Scans source code for security vulnerabilities, buffer overflows, integer wraps, and memory safety flaws."
    },
    "code-summary-generation": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --code-summary-generation --file \"crates/cli/src/main.rs\"",
        "desc": "Synthesizes concise technical docstrings and architectural summaries from complex functions and classes."
    },
    "code-clone-detection": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --code-clone-detection --folder \"src/\"",
        "desc": "Identifies duplicate, near-duplicate, and copy-pasted code fragments across a repository."
    },
    "image-classification": {
        "params": "Boolean switch (requires --file <IMAGE>)",
        "example": "cli.exe --image-classification --file \"assets/icon.png\"",
        "desc": "Routes image files to vision classification models to identify primary subjects and visual categories."
    },
    "object-detection": {
        "params": "Boolean switch (requires --file <IMAGE>)",
        "example": "cli.exe --object-detection --file \"assets/screenshot.png\"",
        "desc": "Locates and bounds distinct objects (buttons, windows, icons) within an input image."
    },
    "image-segmentation": {
        "params": "Boolean switch (requires --file <IMAGE>)",
        "example": "cli.exe --image-segmentation --file \"assets/diagram.png\"",
        "desc": "Segments images at pixel-level resolution to isolate foreground objects from background canvas."
    },
    "visual-question-answering": {
        "params": "Boolean switch (requires --file <IMAGE>)",
        "example": "cli.exe --visual-question-answering --file \"assets/chart.png\" --prompt \"What is the value of Q3 revenue shown in the bar chart?\"",
        "desc": "Answers natural language questions about the visual content of an uploaded image or diagram."
    },
    "document-question-answering": {
        "params": "Boolean switch (requires --file <PDF/IMAGE>)",
        "example": "cli.exe --document-question-answering --file \"invoices/inv_2026.pdf\" --prompt \"What is the total due and payment date?\"",
        "desc": "Extracts answers directly from scanned documents, structured PDF forms, and invoices."
    },
    "zero-shot-image-classification": {
        "params": "Boolean switch (requires --file <IMAGE>)",
        "example": "cli.exe --zero-shot-image-classification --file \"assets/device.jpg\" --context \"laptop, tablet, desktop, smartphone\"",
        "desc": "Classifies images into arbitrary candidate categories using multi-modal vision-language models (CLIP)."
    },
    "depth-estimation": {
        "params": "Boolean switch (requires --file <IMAGE>)",
        "example": "cli.exe --depth-estimation --file \"assets/scene.jpg\"",
        "desc": "Computes monocular depth maps predicting distance from camera for each pixel in an image."
    },
    "image-feature-extraction": {
        "params": "Boolean switch (requires --file <IMAGE>)",
        "example": "cli.exe --image-feature-extraction --file \"assets/logo.png\"",
        "desc": "Extracts high-dimensional visual embedding vectors for image retrieval and similarity matching."
    },
    "automatic-speech-recognition": {
        "params": "Boolean switch (requires --file <AUDIO>)",
        "example": "cli.exe --automatic-speech-recognition --file \"recordings/standup.wav\"",
        "desc": "Transcribes spoken audio into timestamped text transcripts using state-of-the-art ASR models (Whisper)."
    },
    "audio-classification": {
        "params": "Boolean switch (requires --file <AUDIO>)",
        "example": "cli.exe --audio-classification --file \"telemetry/engine_sound.wav\"",
        "desc": "Classifies audio files by acoustic event, musical genre, or environmental sound category."
    },
    "voice-activity-detection": {
        "params": "Boolean switch (requires --file <AUDIO>)",
        "example": "cli.exe --voice-activity-detection --file \"audio/meeting.mp3\"",
        "desc": "Detects presence of human speech vs silence or background noise in audio streams."
    },
    "emotion-recognition": {
        "params": "Boolean switch (requires --file <AUDIO>)",
        "example": "cli.exe --emotion-recognition --file \"support/call_sample.wav\"",
        "desc": "Detects vocal emotion and caller stress levels from audio pitch, tone, and prosody."
    },
    "video-classification": {
        "params": "Boolean switch (requires --file <VIDEO>)",
        "example": "cli.exe --video-classification --file \"media/demo.mp4\"",
        "desc": "Classifies video clips into activity, genre, or scene categories using temporal-spatial models."
    },
    "text-to-speech": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --text-to-speech --prompt \"Build 148 compilation complete. All 161 CLI flags verified.\"",
        "desc": "Synthesizes natural-sounding speech audio from text input using neural vocoders."
    },
    "text-to-image": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --text-to-image --prompt \"Futuristic AI operating system terminal in glowing amber cyberpunk aesthetic\"",
        "desc": "Generates high-resolution images from text descriptions using latent diffusion models."
    },
    "image-super-resolution": {
        "params": "Boolean switch (requires --file <IMAGE>)",
        "example": "cli.exe --image-super-resolution --file \"assets/low_res_badge.png\"",
        "desc": "Upscales low-resolution images using neural super-resolution to enhance clarity and detail."
    },
    "table-question-answering": {
        "params": "Boolean switch (requires --file <CSV/XLSX>)",
        "example": "cli.exe --table-question-answering --file \"data/benchmarks.csv\" --prompt \"Which model achieved the highest throughput?\"",
        "desc": "Answers natural language queries by executing relational reasoning directly over tabular datasets."
    },
    "feature-ranking": {
        "params": "Boolean switch (requires --file <CSV>)",
        "example": "cli.exe --feature-ranking --file \"data/training_set.csv\" --prompt \"Target: churn\"",
        "desc": "Ranks input dataset features by predictive importance, information gain, and variance."
    },

    # 11. Server & Database Commands (5 flags)
    "db-path": {
        "params": "Path to SQLite database file",
        "example": "cli.exe --db-path \"IDE/db/hf_models.db\" --stats",
        "desc": "Specifies custom SQLite database path for ModelFusion catalog, models, and embeddings."
    },
    "server": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --server --port 5000 --db-path \"IDE/db/hf_models.db\"",
        "desc": "Launches the ModelFusion HTTP REST API server for external IDE and headless automation access."
    },
    "enable-slash-commands": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --enable-slash-commands --prompt \"/datascience data/sales.csv\"",
        "desc": "Enables parsing of interactive IDE slash commands (/datascience, /search, /jupyter, /evolve) from raw prompts."
    },
    "port": {
        "params": "Valid TCP port number: 1024 - 65535 (default: 5000)",
        "example": "cli.exe --server --port 8080",
        "desc": "Specifies the TCP port on which the ModelFusion HTTP API server listens (default: 5000)."
    },
    "mcp": {
        "params": "Boolean switch (no value)",
        "example": "cli.exe --mcp --db-path \"IDE/db/hf_models.db\"",
        "desc": "Runs ModelFusion as a Model Context Protocol (MCP) server communicating over standard input/output (stdio)."
    }
}

# The 13 Developer / Build / Legacy flags for Appendix
APPENDIX_FLAGS = {
    "sentiment": {
        "name": "--sentiment",
        "type": "bool",
        "default": "false",
        "desc": "Legacy alias for --text-classification. Analyzes text sentiment.",
        "example": "cli.exe --sentiment --prompt \"The update succeeded without any issues!\""
    },
    "question": {
        "name": "--question",
        "type": "bool",
        "default": "false",
        "desc": "Legacy alias for --question-answering. Runs question answering mode.",
        "example": "cli.exe --question --context \"Build 148 is released.\" --prompt \"What build is released?\""
    },
    "ner": {
        "name": "--ner",
        "type": "bool",
        "default": "false",
        "desc": "Legacy alias for --token-classification. Runs named entity recognition.",
        "example": "cli.exe --ner --prompt \"Sundar Pichai announced Google Antigravity in Mountain View.\""
    },
    "summary": {
        "name": "--summary",
        "type": "bool",
        "default": "false",
        "desc": "Legacy alias for --summarization. Runs text summarization.",
        "example": "cli.exe --summary --file \"docs/README.md\""
    },
    "patch-ide": {
        "name": "--patch-ide",
        "type": "bool",
        "default": "false",
        "desc": "Clones upstream VSCode from GitHub and applies HugOS IDE branding, telemetry rewiring, and updater patches.",
        "example": "cli.exe --patch-ide --ide-src-dir \"IDE/src\" --shallow"
    },
    "ide-src-dir": {
        "name": "--ide-src-dir <IDE_SRC_DIR>",
        "type": "String",
        "default": "IDE/src",
        "desc": "Target directory where VSCode source code is cloned and patched.",
        "example": "cli.exe --patch-ide --ide-src-dir \"IDE/src\""
    },
    "shallow": {
        "name": "--shallow",
        "type": "bool",
        "default": "false",
        "desc": "Executes git clone with --depth 1 during IDE source patching for accelerated downloads.",
        "example": "cli.exe --patch-ide --shallow"
    },
    "vscode-tag": {
        "name": "--vscode-tag <VSCODE_TAG>",
        "type": "Option<String>",
        "default": "None",
        "desc": "Specifies a particular VSCode git tag to checkout and patch (e.g. '1.96.0').",
        "example": "cli.exe --patch-ide --vscode-tag \"1.96.0\""
    },
    "graph-index": {
        "name": "--graph-index",
        "type": "bool",
        "default": "false",
        "desc": "Extracts codebase AST symbols, functions, calls, and type hierarchies into SQLite knowledge graph.",
        "example": "cli.exe --graph-index --workspace \".\""
    },
    "graph-query": {
        "name": "--graph-query <GRAPH_QUERY>",
        "type": "Option<String>",
        "default": "None",
        "desc": "Executes semantic code queries against the indexed codebase AST knowledge graph.",
        "example": "cli.exe --graph-query \"parse_args_struct\" --workspace \".\""
    },
    "workspace": {
        "name": "--workspace <WORKSPACE>",
        "type": "Option<String>",
        "default": "None",
        "desc": "Sets target workspace directory for knowledge graph AST indexing and query resolution.",
        "example": "cli.exe --graph-index --workspace \"d:/harfile/ModelFusion\""
    },
    "query-type": {
        "name": "--query-type <QUERY_TYPE>",
        "type": "String",
        "default": "all",
        "desc": "Knowledge graph query filter: all, symbol, calls, callees, callers, impls, refs, search.",
        "example": "cli.exe --graph-query \"Args\" --query-type symbol"
    },
    "force": {
        "name": "--force",
        "type": "bool",
        "default": "false",
        "desc": "Forces complete re-indexing of all workspace files into AST knowledge graph ignoring cache.",
        "example": "cli.exe --graph-index --force --workspace \".\""
    }
}

def generate_cli_reference():
    with open('scripts/all_parsed_flags.json', 'r', encoding='utf-8') as f:
        all_flags = json.load(f)

    excluded_names = set(APPENDIX_FLAGS.keys())
    agent_directives = {'btw', 'goal', 'schedule', 'browser', 'grill-me', 'teamwork-preview', 'learn', 'boost', 'generative-ui', 'no-fusion'}
    primary_161 = [f for f in all_flags if f['long_name'] not in excluded_names and f['long_name'] not in agent_directives]

    assert len(primary_161) == 161, f"Expected 161 primary flags, got {len(primary_161)}"

    lines = []
    lines.append("# ModelFusion Master CLI Reference Manual (All 161 Flags)")
    lines.append("")
    lines.append("This document is the exhaustive, authoritative reference for the **ModelFusion Master CLI** (`cli.exe` or `cargo run --release --bin cli`).")
    lines.append("Every single one of the **161 production CLI flags** is documented below with its argument type, default value, functional category, behavioral explanation, and a **concrete executable command example**.")
    lines.append("")
    lines.append("> [!IMPORTANT]")
    lines.append("> **Functional Architecture: Flags as Executable Commands**  ")
    lines.append("> In ModelFusion, flags function directly as executable capability functions. The CLI parser maps each flag directly to an underlying handler function in the execution engine. Specifying a flag instructs the engine to invoke that capability rather than merely toggling state.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📖 Table of Contents")
    lines.append("- [Master Summary Table (All 161 Flags)](#-master-summary-table-all-161-flags)")
    lines.append("- [1. Global Execution & Resource Flags (#1 - #19)](#1-global-execution--resource-flags)")
    lines.append("- [2. Machine Learning Model Selection (#20 - #26)](#2-machine-learning-model-selection)")
    lines.append("- [3. SINQ Quantization Engine (#27 - #31)](#3-sinq-quantization-engine)")
    lines.append("- [4. Innovation & Cognitive Systems (#32 - #37)](#4-innovation--cognitive-systems)")
    lines.append("- [5. HyDE Search & Web Retrieval (#38 - #46)](#5-hyde-search--web-retrieval)")
    lines.append("- [6. System & Orchestration Commands (#47 - #87)](#6-system--orchestration-commands)")
    lines.append("- [7. Data Science & Tabular Workflows (#88 - #90)](#7-data-science--tabular-workflows)")
    lines.append("- [8. Response Evaluation & Planning (#91 - #93)](#8-response-evaluation--planning)")
    lines.append("- [9. Binary & PE Executable Analysis (#94)](#9-binary--pe-executable-analysis)")
    lines.append("- [10. Multi-Modal Task Routing Flags (#95 - #156)](#10-multi-modal-task-routing-flags)")
    lines.append("- [11. Server & Database Commands (#157 - #161)](#11-server--database-commands)")
    lines.append("- [Appendix: Developer Tooling, Source Patching & Legacy Aliases](#appendix-developer-tooling-source-patching--legacy-aliases)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📋 Master Summary Table (All 161 Flags)")
    lines.append("")
    lines.append("| # | Flag & Aliases | Type | Default | Category | Description |")
    lines.append("|:---:|:---|:---:|:---:|:---|:---|")

    # Build Master Table
    for idx, f in enumerate(primary_161, 1):
        field_name = f['field_name']
        flag_str = f"`{f['flag']}`"
        
        # Display argument signature
        if f['field_type'] == 'Option<String>':
            flag_str = f"`{f['flag']} <{f['long_name'].upper()}>`"
        elif f['field_type'] in ['u16', 'u32', 'u64', 'f64', 'usize']:
            flag_str = f"`{f['flag']} <VALUE>`"
        elif f['field_type'] == 'String':
            flag_str = f"`{f['flag']} <{f['long_name'].upper()}>`"
        elif 'Option<Vec<String>>' in f['field_type']:
            flag_str = f"`{f['flag']} [<ACTION>...]`"

        if f['aliases']:
            alias_str = ", ".join([f"`{a}`" for a in f['aliases']])
            flag_str += f"<br><small>Aliases: {alias_str}</small>"

        t_clean = f['field_type'].replace('Option<', '').replace('>', '')
        def_clean = str(f['default_val']) if f['default_val'] is not None else "None"
        if f['field_type'] == 'bool' and f['default_val'] is None:
            def_clean = "false"

        cat = f['clean_category']
        desc = FLAG_DETAILS.get(f['long_name'], {}).get('desc', f['help_text'])
        if not desc:
            desc = f['help_text'] if f['help_text'] else f"Execute {f['long_name']} capability."

        lines.append(f"| {idx} | {flag_str} | `{t_clean}` | `{def_clean}` | {cat} | {desc} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Detailed Categorized Sections
    # Group by clean category
    cats_order = [
        ("1. Global Execution & Resource Flags", "Global Execution & Resource Flags"),
        ("2. Machine Learning Model Selection", "Machine Learning Model Selection"),
        ("3. SINQ Quantization Engine", "SINQ Quantization Engine"),
        ("4. Innovation & Cognitive Systems", "Innovation & Cognitive Systems"),
        ("5. HyDE Search & Web Retrieval", "HyDE Search & Web Retrieval"),
        ("6. System & Orchestration Commands", "System & Orchestration Commands"),
        ("7. Data Science & Tabular Workflows", "Data Science & Tabular Workflows"),
        ("8. Response Evaluation & Planning", "Response Evaluation & Planning"),
        ("9. Binary & PE Executable Analysis", "Binary & PE Executable Analysis"),
        ("10. Multi-Modal Task Routing Flags", "Multi-Modal Task Routing Flags"),
        ("11. Server & Database Commands", "Server & Database Commands"),
    ]

    global_flag_idx = 1
    for sec_title, cat_name in cats_order:
        cat_flags = [f for f in primary_161 if f['clean_category'] == cat_name]
        start_idx = global_flag_idx
        end_idx = global_flag_idx + len(cat_flags) - 1
        lines.append(f"## {sec_title} (#{start_idx} - #{end_idx})")
        lines.append("")
        lines.append(f"This section details the **{len(cat_flags)} flags** belonging to **{cat_name}**.")
        lines.append("")

        for f in cat_flags:
            long_name = f['long_name']
            detail = FLAG_DETAILS.get(long_name, {})
            desc = detail.get('desc', f['help_text'] or f"Executes {long_name} task.")
            params = detail.get('params', f"Type: {f['field_type']}")
            example = detail.get('example', f"cli.exe --{long_name}")
            t_clean = f['field_type'].replace('Option<', '').replace('>', '')
            def_val = str(f['default_val']) if f['default_val'] is not None else ("false" if f['field_type'] == 'bool' else "None")

            lines.append(f"### #{global_flag_idx}. `{f['flag']}`")
            lines.append(f"- **Category:** {cat_name}")
            lines.append(f"- **Argument Type:** `{t_clean}`")
            lines.append(f"- **Default Value:** `{def_val}`")
            if f['aliases']:
                lines.append(f"- **Aliases:** {', '.join([f'`{a}`' for a in f['aliases']])}")
            lines.append(f"- **Accepted Parameters:** {params}")
            lines.append(f"- **Description:** {desc}")
            lines.append("")
            lines.append("```powershell")
            lines.append(f"# Example for #{global_flag_idx}: {f['flag']}")
            lines.append(example)
            lines.append("```")
            lines.append("")
            global_flag_idx += 1

        lines.append("---")
        lines.append("")

    # Section 12: Universal Agent Directives
    lines.append("## 12. Universal Agent Directives & Slash Commands")
    lines.append("")
    lines.append("HugOS IDE and ModelFusion integrate **10 universal compound agent directives** matching full Antigravity operating system capabilities:")
    lines.append("")
    lines.append("| Command | Flag | Argument Type | Description | Executable Example |")
    lines.append("|:---|:---|:---:|:---|:---|")
    lines.append("| `/btw` | `--btw <QUESTION>` | `String` | Quick side questions in isolated context without polluting main thread | `cli.exe --btw \"What is RAII in modern C++?\"` |")
    lines.append("| `/goal` | `--goal <OBJECTIVE>` | `String` | Autonomous goal-seeking loop enqueued to ReST-RL daemon | `cli.exe --goal \"Optimize AST parser and run verification\"` |")
    lines.append("| `/schedule` | `--schedule <DIRECTIVE>` | `String` | Background timer and recurring cron execution schedules | `cli.exe --schedule \"cron '*/5 * * * *' health check\"` |")
    lines.append("| `/browser` | `--browser <URL/QUERY>` | `String` | Web research agent with live page scraping and synthesis | `cli.exe --browser \"https://huggingface.co/models\"` |")
    lines.append("| `/plan` | `--plan` | `bool` | Rigorous architectural blueprint with invariant & verification matrix | `cli.exe --plan --prompt \"Design lock-free queue\"` |")
    lines.append("| `/grill-me` | `--grill-me` | `bool` | Lead Architect Socratic interview to align on design decisions | `cli.exe --grill-me --prompt \"Refactoring IPC pipeline\"` |")
    lines.append("| `/teamwork-preview` | `--teamwork-preview` | `bool` | Multi-agent collaborative topology with Mermaid sequence diagrams | `cli.exe --teamwork-preview` |")
    lines.append("| `/learn` | `--learn <RULE>` | `String` | Captures and persists reusable engineering rules into `.hugos/rules/` | `cli.exe --learn \"Always check free RAM before allocating models\"` |")
    lines.append("| `/boost` | `--boost` | `bool` | High-compute multi-sample consensus deliberation over top models | `cli.exe --boost --prompt \"Solve dining philosophers\"` |")
    lines.append("| `/generative_ui` | `--generative-ui <SPEC>` | `String` | Generates self-contained interactive HTML/Tailwind widgets | `cli.exe --generative-ui \"GPU VRAM telemetry widget\"` |")
    lines.append("")
    lines.append("---")
    lines.append("")
    # Appendix for 13 Developer / Build / Legacy flags
    lines.append("## Appendix: Developer Tooling, Source Patching & Legacy Aliases")
    lines.append("")
    lines.append("ModelFusion contains **13 supplementary internal and legacy flags** used for source code patching, IDE build pipelines, legacy compatibility, and AST code graph operations.")
    lines.append("")
    lines.append("| # | Flag | Type | Default | Description | Example |")
    lines.append("|:---:|:---|:---:|:---:|:---|:---|")
    
    app_idx = 162
    for k, v in APPENDIX_FLAGS.items():
        lines.append(f"| {app_idx} | `{v['name']}` | `{v['type']}` | `{v['default']}` | {v['desc']} | `{v['example']}` |")
        app_idx += 1

    lines.append("")
    for k, v in APPENDIX_FLAGS.items():
        lines.append(f"### `{v['name']}`")
        lines.append(f"- **Description:** {v['desc']}")
        lines.append(f"- **Type:** `{v['type']}` | **Default:** `{v['default']}`")
        lines.append("")
        lines.append("```powershell")
        lines.append(v['example'])
        lines.append("```")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Positional Arguments")
    lines.append("")
    lines.append("### `query` (Prompt Query Fallback)")
    lines.append("- **Type:** `Option<String>`")
    lines.append("- **Description:** Any trailing positional string passed without a flag is automatically captured as the prompt query directive.")
    lines.append("```powershell")
    lines.append("cli.exe \"Explain the Pareto frontier model selection algorithm\"")
    lines.append("```")

    doc_content = "\n".join(lines)
    with open("docs/CLI_REFERENCE.md", "w", encoding="utf-8") as f:
        f.write(doc_content)
    print(f"Successfully generated docs/CLI_REFERENCE.md ({len(lines)} lines, {len(doc_content)} bytes)")

if __name__ == '__main__':
    generate_cli_reference()
