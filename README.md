<p align="center">
  <img src="assets/logo.png" alt="ModelFusion Logo" width="220px" style="border-radius: 12px; box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.35);" />
</p>

<h1 align="center">ModelFusion</h1>

<p align="center">
  <strong>Open-Weight Compound Intelligence Through Retrieval-Augmented Consensus Deliberation</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Rust-1.70+-000000?style=for-the-badge&logo=rust&logoColor=white" alt="Rust Version" />
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite Version" />
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge" alt="License" />
  <img src="https://img.shields.io/badge/Hugging%20Face-2M%2B%20Models-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black" alt="HuggingFace Models" />
</p>

---

ModelFusion is an open-weight compound intelligence system designed to achieve frontier-class reasoning and technical capability at a fraction of the cost of commercial proprietary APIs. By combining retrieval-augmented generation (RAG), dynamic task-based model selection, multi-model consensus deliberation, and structured synthesis, ModelFusion bridges the gap between local open-weights execution and closed frontier models.

---

## 🌀 System Architecture

```mermaid
graph TD
    A[User Prompt / Task] --> B[Intelligent Task Detector]
    B -->|Classifies Task Tag| C[Enhanced Model Selector]
    D[(SQLite Model DB: 2M+ Models)] -->|Ranks & Filters| C
    C -->|Selects Top 10 Models| E[Step 1: Concurrent Panel Generation]
    E --> F[Step 2: LLM-as-a-Judge Evaluation]
    F --> G[Step 3: Synthesis & Final Writing]
    G --> H[Synthesized Final Answer]
```

### 1. The Hugging Face Model Database (2M+ Models)
ModelFusion leverages a local SQLite database (`hf_models.db`) indexing **over 2 million model entries** fetched directly from the Hugging Face Hub. 
*   For each model, it stores metadata including downloads, likes, model sizes, licensing, freshness, and capability metrics.
*   This allows local model routing to be fully grounded in actual Hugging Face ecosystem statistics rather than hardcoded heuristics.

### 2. Intelligent Routing & Classification
When a user submits a prompt, ModelFusion automatically routes it to the optimal models:
*   **Intelligent Task Detector**: Classifies the prompt's task type (e.g., `text-generation`, `question-answering`, `text-classification`, `summarization`, `translation`) by analyzing syntactic and semantic features.
*   **Enhanced Model Selector**: Performs a multi-objective optimization query over the 2M+ models database, normalizing downloads, popularity, model size, license openness, and performance metrics. It dynamically retrieves the **top 10 candidate models** matching the task classification to form the consensus panel.

### 3. Multi-Model Consensus Deliberation (`--fusion`)
When `--fusion` is active, the engine coordinates a three-step deliberation pipeline:
1.  **Concurrent Panel Execution**: Dispatches the prompt in parallel to the top 10 selected candidate models (served locally via Ollama or HF Serverless).
2.  **LLM-as-a-Judge Evaluation**: A high-capability reasoning model evaluates the 10 candidate responses, highlighting points of consensus, identifying factual contradictions, and extracting unique insights.
3.  **Synthesis & Writing**: A final writer model synthesizes the judge's analysis and the panel's consensus into a comprehensive, highly accurate response.

---

## 📁 Workspace Crate Structure

ModelFusion is built on a highly modular Rust and Python workspace:

*   [crates/analysis/](file:///D:/harfile/ModelFusion/crates/analysis) — PE header parser, high-entropy packed binary audits, and malware indicator scanning.
*   [crates/cli/](file:///D:/harfile/ModelFusion/crates/cli) — Main CLI package wrapper for orchestration execution.
*   [crates/core/](file:///D:/harfile/ModelFusion/crates/core) — Core system engine, asynchronous task execution, and orchestration pipelines.
*   [crates/db/](file:///D:/harfile/ModelFusion/crates/db) — Hugging Face SQLite DB indexing, query constraints, and self-healing db check loops.
*   [crates/model_selection/](file:///D:/harfile/ModelFusion/crates/model_selection) — Multi-objective model selection logic and score weight managers.
*   [crates/monitoring/](file:///D:/harfile/ModelFusion/crates/monitoring) — Decision metrics tracker and adaptive thresholds.
*   [crates/security/](file:///D:/harfile/ModelFusion/crates/security) — MITRE ATLAS threat detector scanning.
*   [crates/task_detection/](file:///D:/harfile/ModelFusion/crates/task_detection) — Syntax-based task routing and classifier keywords.
*   [crates/utils/](file:///D:/harfile/ModelFusion/crates/utils) — Rate limiters and directory managers.

---

## 📄 Scientific Publication: "Beyond Model Scale"

Our research paper, *"Beyond Model Scale: Open-Weight Compound Intelligence Through Retrieval-Augmented Consensus Deliberation"*, evaluates ModelFusion using the rigorous **DRACO Evaluation Suite** (25 technical tasks across Software Engineering, Cryptography, Security, and Distributed Systems).

### Related Work & OpenRouter Fusion
OpenRouter recently introduced "Fusion," a tool designed to synthesize outputs from a panel of multiple AI models to surpass individual frontier models on complex deep research tasks.
*   **Mechanism**: Submitted prompts are dispatched in parallel to participant models (equipped with web search/fetch) before a judge model compiles points of consensus and contradictions into a final response.
*   **Draco Benchmark Validation**: In evaluations, a fused combination of Fable 5 and GPT-5.5 scored **69.0%**, outperforming Fable 5's standalone score of 65.3%. A budget panel consisting of Gemini 3 Flash, Kimi K2.6, and DeepSeek V4 Pro scored **64.7%**, beating standalone models like GPT-5.5 and Claude Opus 4.8 at half the operational cost.

### Overall Benchmark Metrics (DRACO Suite with 95% Confidence Intervals)

| Configuration | Mean Score | Std Dev ($\sigma$) | 95% Confidence Interval | API Operating Cost | Local Infra Cost | Profile |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **Fusion panel only** | 26.47% | 32.55% | [14.0%, 39.6%] | \$0.00000 | \$0.10639 | Compound Open-Weights |
| **Gemma-4-E2B alone** | 38.73% | 29.91% | [27.4%, 49.3%] | \$0.00000 | \$0.00095 | Single Open-Weights |
| **Gemma-4-E2B + Context** | 47.20% | 37.70% | [32.8%, 62.0%] | \$0.00000 | \$0.00129 | Single Open-Weights |
| **Qwen2.5-7B alone** | 70.27% | 38.25% | [55.2%, 83.3%] | \$0.00000 | \$0.00299 | Single Open-Weights |
| **ModelFusion (Fusion + Context)** | **80.30%** | **28.80%** | **[69.1%, 90.8%]** | **\$0.00000** | **\$0.07760** | **Compound Open-Weights** |
| **gpt-4o alone** | 83.60% | 28.41% | [71.6%, 93.6%] | \$0.24908 | \$0.00000 | Commercial Cloud API |
| **gpt-5.5 alone** | 91.60% | 24.44% | [81.6%, 100.0%] | \$1.68826 | \$0.00000 | Commercial Cloud API |
| **gpt-5.5 + Context** | 98.40% | 8.00% | [95.2%, 100.0%] | \$1.41766 | \$0.00000 | Commercial Cloud API |

---

## 🔬 Component Ablation Analysis

The ablation study shows that retrieval and consensus do not behave as simple independent add-ons.

```
Base model (Gemma-4-E2B)    [38.73%]
       |
       +--> Add Context Only  [47.20%] (Gains: +8.47 points)
       |
       +--> Add Fusion Only   [26.47%] (Loss: -12.26 points)
       |
       +--> ModelFusion (Full) [80.30%] (Synergy Gain: +41.57 points)
```

> [!IMPORTANT]
> **The Deliberation / Retrieval Synergy (Interaction Effect)**
> Consensus deliberation without grounding performs worse than a standalone base model (**26.47% vs. 38.73%**). Without source context, multi-model panels merely amplify assumptions. However, when grounded with RAG context, ModelFusion scores **80.30%** (a **+53.83%** absolute jump). This demonstrates a strong **nonlinear interaction effect** where retrieval and deliberation become highly synergistic.

---

## 💰 Operational Cost Analysis

ModelFusion trades commercial API charges for a predictable local infrastructure cost. 
*   **Infrastructure Efficiency**: ModelFusion costs **\$0.07760** and achieves **80.30%** accuracy, while GPT-4o costs **\$0.24908** and achieves **83.60%**.
*   **Resource Tradeoff**: ModelFusion reaches **96.1%** of GPT-4o's measured score while reducing run cost by **68.8%** relative to GPT-4o.
*   **Cost-per-Value Performance**: Compared to GPT-5.5 + Context, ModelFusion achieves **81.6%** of its accuracy at **~15x better cost efficiency** (1034.8 score-per-dollar vs 69.4 score-per-dollar).

---

## 📊 Sub-Domain and Task-Level Behavior

ModelFusion's average score evaluated across 20 technical sub-domains demonstrates strong technical capabilities:

| Sub-Domain / Task | Average Score (%) | Description |
|:---|:---:|:---|
| **Vector Databases** | 100.0% | Embedding search indexes & similarity scoring. |
| **System Architecture** | 100.0% | Distributed design and service modularization. |
| **Network Protocols** | 100.0% | Low-level transport layer handshake logic. |
| **AI Threat Detection** | 100.0% | Adversarial prompt and jailbreak scanning. |
| **Network Security** | 100.0% | TLS handshake parameters & threat analysis. |
| **Deep Learning** | 100.0% | Neural network layer parameter backpropagation. |
| **Language Runtimes** | 100.0% | Garbage collection mechanisms and JIT compilers. |
| **Computer Architecture**| 100.0% | CPU instruction caches and register states. |
| **Computer Security** | 100.0% | Vulnerability exploits and defense frameworks. |
| **Cryptography** | 100.0% | Encryption keys and secure key exchanges. |
| **Database Internals** | 100.0% | WAL logs, index queries, and transaction isolation. |
| **Software Engineering** | 75.0% | Object-oriented systems and concurrency bugs. |
| **Deep Learning Optimization**| 75.0% | Kernel optimizations and mixed precision. |
| **Web Security** | 66.7% | CORS, CSRF, and SQL Injection vector auditing. |
| **Distributed Systems** | 66.7% | Raft consensus logs and replica syncs. |
| **Blockchain Security** | 60.0% | Smart contract vulnerabilities. |
| **Concurrency** | 60.0% | Deadlock detection and locking mechanisms. |
| **Operating Systems** | 50.0% | Thread schedulers, page faults, and virtual memory. |
| **Cloud Infrastructure** | 37.5% | Kubernetes configurations and orchestration. |

### Limitations & Heatmap Insights
*   **Task 21 Miss**: The task-level heatmap exposes where the compound system succeeds and fails. While ModelFusion improves many weak cases, Task 21 (focusing on distributed storage sync) remains a complete miss, demonstrating that consensus still relies on high-quality retrieval and correct evidence use.

---

## 🚀 Getting Started

### Prerequisites
*   Rust 1.70+ and Cargo
*   Python 3.10+ with `transformers`, `torch`, and `accelerate` installed
*   (Optional) [Ollama](https://ollama.com/) for local model serving

### Running the CLI

**Basic fusion query** (10 panel models by default, runs locally via `transformers`):
```powershell
cargo run --release --package cli -- --fusion --prompt "Design a high-concurrency connection pool in Rust."
```

**With auto-generated context** (uses DeepSeek-R1-Distill-Qwen-1.5B to generate background context):
```powershell
cargo run --release --package cli -- --fusion --context-auto --prompt "What is a deadlock and how can it be prevented?"
```

**With custom context guidance**:
```powershell
cargo run --release --package cli -- --fusion --context "Focus on Rust async patterns" --prompt "Compare tokio vs async-std"
```

**Custom panel size** (e.g., 3 models instead of the default 10):
```powershell
cargo run --release --package cli -- --fusion --fusion-models 3 --context-auto --prompt "Explain CAP theorem"
```

**Using Ollama** (runs models via local Ollama instead of Python transformers):
```powershell
cargo run --release --package cli -- --fusion --ollama --context-auto --prompt "What is a deadlock?"
```

### Fusion CLI Flags Reference

| Flag | Default | Description |
|:---|:---:|:---|
| `--fusion` | off | Enable multi-model consensus deliberation pipeline |
| `--fusion-models <N>` | `10` | Number of models (or temperature samples) to run in the panel |
| `--fusion-mode <MODE>` | `multi-model` | Execution mode: `multi-model` (N different models) or `multi-sample` (1 model, N temperature samples — much faster locally) |
| `--ollama` | off | Use local Ollama for model execution (auto-starts `ollama serve` if not running) |
| `--openvino` | off | Use OpenVINO for optimized CPU inference (requires: `pip install -U openvino`) |
| `--context-auto` | off | Auto-generate background context via DeepSeek-R1-Distill-Qwen-1.5B |
| `--context <STRING>` | none | Provide custom context guidance for context generation |
| `--report <PATH>` | none | Save the final fusion report to a file or directory |

### Execution Backends

ModelFusion supports three local execution backends. If no backend flag is specified, it defaults to Python `transformers`:

| Backend | Flag | Precision | 7B Model Memory | Best For |
|:---|:---:|:---:|:---:|:---|
| **Ollama** | `--ollama` | Q4_0 | ~5.0 GB | GPU inference via Vulkan/CUDA, fastest for repeated runs |
| **OpenVINO** | `--openvino` | FP32→IR | ~4.2 GB | Optimized CPU inference (Intel/AMD), 2-3× faster than transformers |
| **Transformers** | *(default)* | FP16 | ~16.8 GB | Direct HuggingFace model loading, widest compatibility |

### Fusion Execution Modes

| Mode | Flag | What It Does | Speed | Best For |
|:---|:---:|:---|:---:|:---|
| **Multi-Model** | `--fusion-mode multi-model` | Runs N different models, each providing a unique perspective | Slower (N model loads) | Maximum diversity and quality |
| **Multi-Sample** | `--fusion-mode multi-sample` | Loads 1 best model, samples N times with varied temperatures (T=0.3→1.1) | **5-10× faster** | Fast local execution with good diversity |

### Dynamic Resource Management

ModelFusion dynamically adapts to your hardware at runtime:

* **Memory Detection**: Scans available RAM (via PowerShell) and GPU VRAM (via `nvidia-smi`) on every run.
* **Model Filtering**: Only selects models that fit within 70% of available memory. If fewer than N models fit, the panel is **automatically reduced** with a clear warning.
* **GPU Routing**: Small models (≤ VRAM budget) run on 🎮 GPU; larger models fall back to 💻 CPU (RAM).
* **Sequential Execution**: Ollama and OpenVINO backends run models one at a time to avoid OOM crashes. Transformers can batch based on memory budget.
* **Runtime Fallback**: If a model fails during execution (OOM, timeout, API error), the system automatically substitutes the next-best model from a pre-built fallback pool and **logs the failure reason**.
* **Ollama Auto-Start**: If `--ollama` is specified but Ollama is not running, ModelFusion automatically starts `ollama serve` and waits up to 30 seconds for it to be ready.

> [!NOTE]
> ModelFusion's local SQLite database indexes **over 2 million open-weight models** across **56 task types** from the Hugging Face Hub. When `--fusion` is active, the system dynamically selects the best-fit models for your specific task from this entire catalog, filtered by your hardware's available memory and GPU capacity — giving every user access to a massive pool of open-weight intelligence regardless of their hardware.

### Usage Examples

**Fast local fusion** (1 model, 10 temperature samples via Ollama — recommended for most local setups):
```powershell
cli.exe --fusion --ollama --fusion-mode multi-sample --context-auto --prompt "Design a high-concurrency connection pool in Rust."
```

**Quality fusion** (10 different models via Ollama):
```powershell
cli.exe --fusion --ollama --context-auto --prompt "What is a deadlock and how can it be prevented?"
```

**OpenVINO optimized CPU** (no GPU needed):
```powershell
cli.exe --fusion --openvino --fusion-mode multi-sample --prompt "Explain CAP theorem"
```

**Custom panel size** (e.g., 5 models):
```powershell
cli.exe --fusion --ollama --fusion-models 5 --context-auto --prompt "Compare tokio vs async-std"
```

**Default transformers backend** (FP16, widest compatibility):
```powershell
cli.exe --fusion --context-auto --prompt "What are the tradeoffs of microservices?"
```

### Pre-installing Ollama Models
To pre-install the models commonly selected by the `--fusion --ollama` panel:
```powershell
ollama pull qwen2.5:7b
ollama pull qwen2.5:3b
ollama pull qwen2.5:1.5b
ollama pull llama3.1
ollama pull llama3.2:1b
ollama pull deepseek-r1:1.5b
```

### Running the Draco Benchmark
To execute the DRACO evaluation benchmark offline with strict verification (no simulated fallbacks) and compute confidence intervals across 1,000 bootstrap replicates:
```powershell
python canned_benchmark/draco_evaluator.py --no-fallback --bootstraps 1000
```

---

## 📄 References & Citation
For more information, please consult the complete research paper: 
*   Draft PDF: `Beyond Model Scale: Open-Weight Compound Intelligence Through Retrieval-Augmented Consensus Deliberation`
*   OpenRouter announcement: [Fusion Announcement](https://openrouter.ai/blog/announcements/fusion-beats-frontier/)
