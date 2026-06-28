# ModelFusion CLI Reference Manual

This document provides a comprehensive reference of all command-line interface (CLI) capabilities, subcommands, and flags available in ModelFusion (`cli.exe` or `cargo run --package cli`).

> [!IMPORTANT]
> **Functional Architecture:** In ModelFusion, **all flags function as commands/functions**. The CLI parser maps each flag directly to an underlying handler function in the execution engine. Specifying a flag acts as an instruction to execute that specific capability function rather than just setting configuration state.

---

## 📖 Table of Contents
- [1. Global Configuration Flags](#1-global-configuration-flags)
- [2. Machine Learning (ML) Selection Flags](#2-machine-learning-ml-selection-flags)
- [3. SINQ Quantization Flags](#3-sinq-quantization-flags)
- [4. Innovation Engine Flags](#4-innovation-engine-flags)
- [5. HyDE Search & RAG Flags](#5-hyde-search--rag-flags)
- [6. Orchestration & System Commands](#6-orchestration--system-commands)
- [7. Execution Backends](#7-execution-backends)
- [8. Data Science & Analytics Workflows](#8-data-science--analytics-workflows)
- [9. Response Evaluation & Planning](#9-response-evaluation--planning)
- [10. PE Binary Analysis](#10-pe-binary-analysis)
- [11. Task-Specific Model Routing Flags](#11-task-specific-model-routing-flags)
- [12. CLI Usage Examples](#12-cli-usage-examples)

---

## 1. Global Configuration Flags

These flags control the general runtime behavior, debugging levels, and execution budgets.

| Flag | Argument Type | Default Value | Description |
|:---|:---:|:---:|:---|
| `--file <PATH>` | `String` | None | Path to a local file for analysis or processing. |
| `--folder <PATH>` | `String` | None | Path to a local folder for batch code reviews or analysis. |
| `--prompt <STRING>` | `String` | None | The input prompt or instruction for the LLM task. |
| `--task <TASK>` | `String` | None | Force a specific Hugging Face task class (e.g. `text-generation`). |
| `--budget <LIMIT>` | `f64` | `10.0` | Cost budget limit in USD for paid LLM execution. |
| `--chain-of-thought` | None (Flag) | Off | Enable chain-of-thought reasoning before returning final responses. |
| `--config <PATH>` | `String` | None | Path to a custom ModelFusion JSON config override file. |
| `--enable-ml` | None (Flag) | Off | Enable general ML optimizations across features. |
| `--use-openai` | None (Flag) | Off | Force routing tasks to commercial OpenAI APIs instead of local open-weights models. |
| `--verbose` | None (Flag) | Off | Enable verbose console logging and trace outputs. |
| `--debug` | None (Flag) | Off | Enable raw debug dumps, timing metrics, and stacktraces. |
| `--selection-strategy` | `String` | `multi_objective` | Strategy for ranking models (`multi_objective`, `popularity`, `freshness`, etc.). |
| `--language <LANG>` | `String` | `en` | Set the target locale or processing language. |
| `--gpu` | None (Flag) | Off | Force GPU/CUDA execution. Skips CPU fallback check. |
| `--cpu` | None (Flag) | Off | Force CPU-only execution. Disables CUDA/Vulkan checks. |
| `--api-keys <PATH>` | `String` | None | Path to a JSON file containing API keys for cloud providers. |
| `--save-model` | None (Flag) | Off | Save trained local ML selection metadata to disk. |
| `--load-model <PATH>` | `String` | None | Load previously trained ML selection model weights. |

---

## 2. Machine Learning (ML) Selection Flags

ModelFusion contains an adaptive ML-based model selector that learns from run histories.

| Flag | Argument Type | Default Value | Description |
|:---|:---:|:---:|:---|
| `--enable-ml-selection` | None (Flag) | Off | Enable the ML routing classifier to select the top model instead of heuristics. |
| `--ml-learning` | None (Flag) | Off | Enable reinforcement learning from prompt success rates. |
| `--ml-ensemble-method` | `String` | `weighted_voting` | Ensemble voting technique: `weighted_voting`, `majority`, or `rank_averaging`. |
| `--ml-confidence-threshold`| `f64` | `0.6` | Minimum confidence score needed to accept an ML classification. |
| `--ml-analytics` | None (Flag) | Off | Show detailed ML selection training and query metrics. |
| `--ml-retrain` | None (Flag) | Off | Force retraining of the local model selector from historical database entries. |
| `--ml-cleanup <DAYS>` | `u32` | None | Delete ML training log entries older than the specified number of days. |
| `--ml-fallback <bool>` | `true/false` | `true` | Fallback to heuristics if the ML router confidence drops below threshold. |

---

## 3. SINQ Quantization Flags

ModelFusion features SINQ (Structured Innovation Network Quantization) to optimize memory load.

| Flag | Argument Type | Default Value | Description |
|:---|:---:|:---:|:---|
| `--sinq` | None (Flag) | Off | Enable SINQ weight-quantization on model weights during conversion. |
| `--sinq-nbits <BITS>` | `u32` | `4` | Target bit-width for SINQ weight quantization (e.g. `4` for INT4). |
| `--sinq-group-size <N>` | `u32` | `64` | Group size for quantized weights scales computation. |
| `--sinq-tiling-mode <MODE>` | `String` | `1D` | Weight matrix tiling layout (`1D` or `2D`). |
| `--sinq-method <METHOD>` | `String` | `sinq` | Quantization algorithm type to apply (`sinq`, `rtn`, `awq`). |

---

## 4. Innovation Engine Flags

These flags control the complex background synthesis engines of ModelFusion.

| Flag | Argument Type | Default Value | Description |
|:---|:---:|:---:|:---|
| `--enable-innovations` | None (Flag) | Off | Activate all integrated ModelFusion innovation features. |
| `--workflow-optimization`| None (Flag) | Off | Enable adaptive agentic workflow pipeline optimizations. |
| `--semantic-analysis` | None (Flag) | Off | Run deep semantic text checks on source files or prompts. |
| `--temporal-tracking` | None (Flag) | Off | Enable version-control/timeline tracking of file revisions. |
| `--predictive-mode` | None (Flag) | Off | Run predictive models to guess user intent or next tasks. |
| `--innovation-level <N>` | `u32` | `2` | Set severity / depth of innovation system passes (`1` to `5`). |

---

## 5. HyDE Search & RAG Flags

ModelFusion implements HyDE (Hypothetical Document Embeddings) to expand search recall.

| Flag | Argument Type | Default Value | Description |
|:---|:---:|:---:|:---|
| `--enable-hyde` | None (Flag) | Off | Enable HyDE RAG search. Generates hypothetical documents to search embeddings. |
| `--use-hyde` | None (Flag) | Off | Refine questions interactively before executing vector search. |
| `--hyde-variants` | None (Flag) | Off | Generate multiple hypothetical documents to expand search breadth. |
| `--add-documents <PATH>` | `String` | None | Index text files/directories into the local vector database. |
| `--search-query <QUERY>` | `String` | None | Query the vector database semantically and print results. |
| `--top-k <N>` | `u32` | `5` | Number of matching documents to fetch from the database. |
| `--demo-hyde` | None (Flag) | Off | Run a diagnostic RAG demo showing how HyDE retrieves document context. |

---

## 6. Orchestration & System Commands

Commands to fetch, check, and monitor system databases and cache files.

| Flag | Argument Type | Default Value | Description |
|:---|:---:|:---:|:---|
| `--stats` | None (Flag) | Off | Output database statistics (number of models, tasks, and file sizes). |
| `--tasks [<FILTER>]` | `String` | None | List all supported HuggingFace tasks. Filterable by `audio`, `image`, or `text`. |
| `--update` | None (Flag) | Off | Fetch the latest open-weights catalog directly from HuggingFace Hub. |
| `--restore` | None (Flag) | Off | Revert configurations and SQLite DB to the latest clean backup. |
| `--decision-stats` | None (Flag) | Off | Print router routing logs and selection accuracy statistics. |
| `--novel-ai-stats` | None (Flag) | Off | Print statistics for advanced AI models currently indexed. |
| `--performance-stats` | None (Flag) | Off | Print latency, token generation speed, and system load stats. |
| `--cache-stats` | None (Flag) | Off | Display model weight cache directories and disk usage. |
| `--clearcache` | None (Flag) | Off | Wipe all downloaded models and converted intermediates. |
| `--analytics-demo` | None (Flag) | Off | Run advanced visualization of the local HuggingFace catalog. |
| `--model-ranking [<TASK>]`| `String` | None | Output the ranked model list for a specific task classification. |
| `--model-recommendations` | None (Flag) | Off | Recommend model backends matching local CPU/GPU specifications. |
| `--full` | None (Flag) | Off | Force comprehensive, deep assessment mode across all features. |
| `--db-path <PATH>` | `String` | `models.db` | Custom path to the Hugging Face metadata SQLite database. |
| `--server` | None (Flag) | Off | Launch ModelFusion as an HTTP API REST server. |
| `--port <N>` | `u16` | `5000` | Port to run the HTTP API server on. |
| `--mcp` | None (Flag) | Off | Run ModelFusion as an MCP (Model Context Protocol) server. |

---

## 7. Execution Backends

ModelFusion orchestrates multiple inference runtimes depending on task parameters.

| Flag | Argument Type | Default Value | Description |
|:---|:---:|:---:|:---|
| `--fusion` | None (Flag) | Off | Enable multi-model consensus deliberation pipeline. |
| `--fusion-models <N>` | `usize` | `10` | Size of the consensus panel (how many models run in parallel). |
| `--fusion-mode <MODE>` | `String` | `multi-model` | Panel setup: `multi-model` (different models) or `multi-sample` (one model, N temp variations). |
| `--ollama` | None (Flag) | Off | Run inference using a local Ollama daemon rather than HuggingFace. |
| `--openvino` | None (Flag) | Off | Run inference on Intel hardware using OpenVINO optimization. |
| `--vllm` | None (Flag) | Off | Run high-throughput inference using vLLM (Linux GPU-only). |
| `--prepare-model <NAME>` | `String` | None | Pre-convert a Hugging Face PyTorch model into OpenVINO IR format. |
| `--prepare-all-models` | None (Flag) | Off | Download and convert all eligible model registry templates to OpenVINO. |
| `--weight-format <FMT>` | `String` | `int8` | OpenVINO quantization compression: `fp16`, `int8`, or `int4`. |
| `--ov-model-dir <DIR>` | `String` | `ov_models` | Directory path containing converted OpenVINO IR models. |

---

## 8. Data Science & Analytics Workflows

Dedicated workflows for tabulating data and automating scientific workloads.

| Flag | Argument Type | Default Value | Description |
|:---|:---:|:---:|:---|
| `--jupyter` | None (Flag) | Off | Launch a local Jupyter Server populated with ModelFusion libraries. |
| `--dataanalyst` | None (Flag) | Off | Run the CSV/Excel Data Analyst workflow (cleans data, extracts patterns). |
| `--datascience` | None (Flag) | Off | Run the full predictive modeling and science workflow. |
| `--export-pdf` | None (Flag) | Off | Save telemetry and workflow charts into a PDF document. |

---

## 9. Response Evaluation & Planning

These options control response quality grading.

| Flag | Argument Type | Default Value | Description |
|:---|:---:|:---:|:---|
| `--score` | None (Flag) | Off | Evaluate response quality using metric token overlays. |
| `--judge` | None (Flag) | Off | Run LLM-as-a-Judge comparison on outputs to grade correctness. |
| `--plan` | None (Flag) | Off | Run an agent planner to execute multiple subtasks sequentially. |

---

## 10. PE Binary Analysis

Low-level static PE analyzer.

| Flag | Argument Type | Default Value | Description |
|:---|:---:|:---:|:---|
| `--pe-header-extraction` | None (Flag) | Off | Parse PE files (DLL, EXE) to audit sections, imports, and entropy. |

---

## 11. Task-Specific Model Routing Flags

These flags force task-level classification and route prompts to specialized Hugging Face categories.

### 📝 Text Capabilities
- `--text-classification` — Classifies text segments (e.g. sentiment).
- `--token-classification` — NER/POS tags per token.
- `--question-answering` — Extractive question answering.
- `--text-generation` — Causal language generation.
- `--summarization` — Conditional summarization.
- `--translation` — Translate between languages.
- `--fill-mask` — Masked language modeling (predict blank tokens).
- `--text2text-generation` — Sequence-to-sequence conversion.
- `--language-detection` — Detect string locale.
- `--grammar-correction` — Correct syntax and errors.
- `--paraphrase-generation` — Rephrase sentences.
- `--causal-language-modeling` — Standard autoregressive text.
- `--zero-shot-classification` — Classify text without labels.
- `--feature-extraction` — Convert text to dense vectors.
- `--sentence-similarity` — Compute distance between two embeddings.
- `--anonymization` — Scrape PII.
- `--coreference-resolution` — Resolve pronouns.
- `--spam-detection` — Detect spam.
- `--pii-detection` — Scan for sensitive identity leaks.

### 🛡️ Cyber-Security Tasks
- `--malware-text-detection` — Detect malware indicator scripts in text.
- `--phishing-detection` — Audit emails for social engineering cues.
- `--hate-speech-detection` — Scan for toxicity.
- `--cyberbullying-detection` — Detect harassment patterns.
- `--fake-news-detection` — Fact-check text content.

### ⚖️ Legal & Financial Tasks
- `--legal-judgment-classification` — Classify case filings.
- `--contract-clause-classification` — Audit business agreements.
- `--case-outcome-prediction` — Predict judgment outcomes.
- `--financial-ner` — Tag financial assets and companies.
- `--legal-ner` — Tag laws, statutes, and citations.
- `--biomedical-ner` — Tag medical terminology.
- `--chemical-reaction-ner` — Tag chemical reagents.
- `--financial-sentiment-analysis` — Classify market sentiment (bullish/bearish).

### 🔍 Advanced Academic / Evaluative Tasks
- `--scientific-abstract-summarization` — Condense research papers.
- `--emotion-detection` — Tag human mood in texts.
- `--sarcasm-detection` — Detect irony.
- `--stance-detection` — Detect user argument stance.
- `--bias-detection` — Scan text for demographic bias.
- `--hallucination-detection` — Audit model responses for grounding.
- `--reading-level-assessment` — Assess grade/reading readability level.
- `--generation-groundedness` — Score facts in generated output.
- `--citation-intent-classification` — Identify why a source was cited.

### 💻 Code Analysis Tasks
- `--code-vulnerability-detection` — Audit source code for CVEs.
- `--code-summary-generation` — Document classes/methods.
- `--code-clone-detection` — Scan for code duplication.

### 🖼️ Vision Capabilities
- `--image-classification` — Tag images.
- `--object-detection` — Draw bounding boxes around items.
- `--image-segmentation` — Segment images into mask zones.
- `--visual-question-answering` — Query images with text prompts.
- `--document-question-answering` — Extracted text queries on PDF scans.
- `--zero-shot-image-classification` — Tag images without labels.
- `--depth-estimation` — Map 3D depth maps.
- `--image-feature-extraction` — Image embedding vectors.

### 🔊 Audio & Video Capabilities
- `--automatic-speech-recognition` — Transcript audio (ASR/Whisper).
- `--audio-classification` — Tag sounds (e.g. music genre).
- `--voice-activity-detection` — Split audio on voice frames.
- `--emotion-recognition` — Grade voice frequency tone.
- `--video-classification` — Categorize action loops.
- `--text-to-speech` — Generate audio.
- `--text-to-image` — Generate images.
- `--image-super-resolution` — Upscale images.

### 📊 Structured Tasks
- `--table-question-answering` — Run queries directly on CSV/SQL tables.
- `--feature-ranking` — Run statistics on feature relevance.

---

## 12. CLI Usage Examples

### Running Multi-Model Deliberation via Ollama
Loads the top 10 models for `text-generation`, executes them in sequence, evaluates consensus, and writes the output:
```bash
cli.exe --fusion --ollama --context-auto --prompt "How does Raft consensus handle log compaction?"
```

### Running Fast Multi-Sample Deliberation
Loads only one selected high-end model and queries it 5 times with different temperature seeds for consensus synthesis:
```bash
cli.exe --fusion --ollama --fusion-models 5 --fusion-mode multi-sample --prompt "Fix this Rust borrow-checker bug: ..."
```

### OpenVINO Optimized CPU Batch Conversion
Pre-converts verified models to CPU INT4 models for offline execution:
```bash
cli.exe --update --prepare-all-models --weight-format int4 --ov-model-dir ov_models
```

### Run PE Malware Audit with AI Planning
Extracts binary headers from an executable and routes telemetry to a planning agent for vulnerability assessment:
```bash
cli.exe --pe-header-extraction --plan --file "target/release/cli.exe"
```

### Running ModelFusion as a REST API backend
Serves model selection queries on port `8080`:
```bash
cli.exe --server --port 8080
```
