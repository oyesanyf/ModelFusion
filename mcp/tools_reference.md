# ModelFusion MCP Server • Tools Reference Manual

The **ModelFusion Model Context Protocol (MCP) Server** exposes **103 specialized tools** over standard JSON-RPC 2.0 stdio (`protocolVersion: "2024-11-05"`). These tools connect frontier desktop assistants (Claude Desktop, Cursor, Google Antigravity, VS Code, Zed) to ModelFusion's local multi-modal engine, ACDSO Pareto AutoML, ReST-RL preemption, and 2M+ model catalog.

---

## 📑 Table of Contents
1. [Core Orchestration & Universal Execution](#1-core-orchestration--universal-execution)
2. [File & Project Intelligence](#2-file--project-intelligence)
3. [Natural Language Processing (NLP)](#3-natural-language-processing-nlp)
4. [CyberSecurity & Binary Forensics](#4-cybersecurity--binary-forensics)
5. [Domain-Specific Reasoning (Legal, Financial, Biomedical)](#5-domain-specific-reasoning)
6. [Multi-Modal Vision, Audio & Video](#6-multi-modal-vision-audio--video)
7. [Semantic Search, Web & arXiv Scientific Grounding](#7-semantic-search-web--arxiv-scientific-grounding)
8. [ACDSO AutoML & Data Science](#8-acdso-automl--data-science)
9. [Model Lifecycle, Quantization & Bandits](#9-model-lifecycle-quantization--bandits)
10. [System Telemetry, Hardware & Health](#10-system-telemetry-hardware--health)

---

## 1. Core Orchestration & Universal Execution

### `execute`
* **Description**: Execute the ModelFusion Master CLI with **ANY** combination of flags. This is the universal escape-hatch tool when no specialized tool fits.
* **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "args": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Array of CLI arguments, e.g. ['--prompt', 'explain memory safety', '--gpu', '--ollama']"
      }
    },
    "required": ["args"]
  }
  ```
* **Supported CLI Flags**: `--prompt <text>`, `--file <path>`, `--folder <path>`, `--task <name>`, `--budget <float>`, `--chain-of-thought`, `--gpu`, `--cpu`, `--ollama`, `--openvino`, `--onnx`, `--vllm`, `--model <id>`, `--fusion`, `--fusion-models <N>`, `--fusion-mode <multi-model|multi-sample>`, `--selection-strategy <strategy>`, `--delegation`, `--recursion`, `--score`, `--judge`, `--plan`, `--enable-ml`, `--acdso`, `--rest-rl`.
* **Example Call**:
  ```json
  {
    "name": "execute",
    "arguments": {
      "args": ["--prompt", "Compare Rust Arc vs Rc pointers", "--budget", "7"]
    }
  }
  ```

---

### `quick_answer`
* **Description**: Fast direct answer for general knowledge, factual lookup, definitions, and translations. Queries local Ollama directly, bypassing orchestration for sub-2-second response latency.
* **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "question": { "type": "string", "description": "The question to answer" },
      "model": {
        "type": "string",
        "description": "Ollama model tag (default: qwen2.5:3b). Options: qwen2.5:0.5b, qwen2.5:1.5b, qwen2.5:3b, qwen2.5:7b, deepseek-r1:1.5b"
      }
    },
    "required": ["question"]
  }
  ```

---

### `orchestrate`
* **Description**: Full ModelFusion compound intelligence pipeline: Task Auto-Detection $\rightarrow$ Hardware-Sized Model Selection $\rightarrow$ Multi-Model Deliberation $\rightarrow$ Response Synthesis.
* **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "prompt": { "type": "string", "description": "Prompt or task description" },
      "budget": { "type": "number", "description": "Model parameter budget in billions (1, 3, 7, 14, 32)" },
      "selection_strategy": { "type": "string", "description": "Strategy: multi_objective, latency, accuracy, cost, performance" },
      "task_override": { "type": "string", "description": "Explicit task override (text-generation, summarization, etc.)" },
      "gpu": { "type": "boolean" },
      "cpu": { "type": "boolean" },
      "fusion": { "type": "boolean", "description": "Enable multi-model consensus deliberation" },
      "chain_of_thought": { "type": "boolean", "description": "Enable step-by-step reasoning" },
      "delegation": { "type": "boolean", "description": "Enable multi-agent task routing" },
      "recursion": { "type": "boolean", "description": "Enable recursive task decomposition" }
    },
    "required": ["prompt"]
  }
  ```

---

## 2. File & Project Intelligence

### `analyze_file`
* **Description**: Deep inspection and analysis of a single file. Supports code quality audits, vulnerability detection, documentation generation, and structural summarization.
* **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "file": { "type": "string", "description": "Absolute filesystem path to the file" },
      "prompt": { "type": "string", "description": "Analysis instructions" },
      "budget": { "type": "number", "description": "Max model size in billions" },
      "gpu": { "type": "boolean" },
      "full": { "type": "boolean", "description": "Enable comprehensive analysis mode" }
    },
    "required": ["file", "prompt"]
  }
  ```

---

### `analyze_folder`
* **Description**: Project-wide scanning and architectural analysis. Scans dependencies, file hierarchy, cyclic imports, architectural drift, and security hotspots.
* **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "folder": { "type": "string", "description": "Absolute filesystem path to the directory" },
      "prompt": { "type": "string", "description": "Project-wide analysis instructions" },
      "budget": { "type": "number" },
      "gpu": { "type": "boolean" },
      "full": { "type": "boolean" }
    },
    "required": ["folder", "prompt"]
  }
  ```

---

### `code_task`
* **Description**: Code-specific specialized AI pipeline: vulnerability detection, summary generation, clone detection, and LLM-as-a-Judge code scoring.
* **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "task": {
        "type": "string",
        "description": "Task: code-vulnerability-detection, code-summary-generation, code-clone-detection, text-generation"
      },
      "text": { "type": "string", "description": "Source code snippet or description" },
      "file": { "type": "string", "description": "Optional file path" },
      "plan": { "type": "boolean", "description": "Enable AI planning phase" },
      "judge": { "type": "boolean", "description": "Enable LLM-as-a-Judge evaluation" },
      "score": { "type": "boolean", "description": "Enable output scoring" },
      "gpu": { "type": "boolean" }
    },
    "required": ["task", "text"]
  }
  ```

---

## 3. Natural Language Processing (NLP)

### `nlp_task`
* **Description**: Executes 20+ specialized NLP tasks using optimized local models.
* **Supported Tasks**:
  - `sentiment-analysis`, `text-classification`, `summarization`, `translation`, `question-answering`
  - `ner` (Named Entity Recognition), `emotion-detection`, `sarcasm-detection`, `paraphrase-generation`
  - `grammar-correction`, `language-detection`, `reading-level-assessment`, `anonymization`
  - `coreference-resolution`, `fill-mask`, `feature-extraction`, `sentence-similarity`, `zero-shot-classification`
  - `stance-detection`, `bias-detection`
* **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "task": { "type": "string", "description": "NLP task name" },
      "text": { "type": "string", "description": "Input text to process" },
      "language": { "type": "string", "description": "Target language (default: en)" },
      "gpu": { "type": "boolean" }
    },
    "required": ["task", "text"]
  }
  ```

---

## 4. CyberSecurity & Binary Forensics

### `security_analysis`
* **Description**: Security auditing and threat detection across text, communications, and code.
* **Supported Tasks**:
  - `spam-detection`, `malware-text-detection`, `phishing-detection`, `pii-detection`
  - `hate-speech-detection`, `cyberbullying-detection`, `fake-news-detection`
  - `hallucination-detection`, `generation-groundedness`, `code-vulnerability-detection`
* **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "task": { "type": "string", "description": "Security task name" },
      "text": { "type": "string", "description": "Text or code to analyze" },
      "file": { "type": "string", "description": "Optional file path to scan" },
      "gpu": { "type": "boolean" }
    },
    "required": ["task", "text"]
  }
  ```

---

### `pe_header_extraction`
* **Description**: Static forensics and header inspection on Windows Portable Executables (`.exe`, `.dll`, `.sys`). Parses DOS header, COFF header, optional headers, section table, virtual sizes, subsystem type, and machine architecture.
* **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "file": { "type": "string", "description": "Absolute path to the PE binary" },
      "prompt": { "type": "string", "description": "Forensic instructions (default: 'Perform PE analysis')" }
    },
    "required": ["file"]
  }
  ```

---

## 5. Domain-Specific Reasoning

### `domain_task`
* **Description**: Specialized domain models trained for legal, financial, scientific, and biomedical tasks.
* **Supported Tasks**:
  - **Legal**: `legal-judgment-classification`, `contract-clause-classification`, `case-outcome-prediction`, `legal-ner`
  - **Finance**: `financial-sentiment-analysis`, `financial-ner`
  - **Biomedical & Science**: `biomedical-ner`, `chemical-reaction-ner`, `scientific-abstract-summarization`, `citation-intent-classification`
  - **Structured Data**: `table-question-answering`, `feature-ranking`
* **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "task": { "type": "string", "description": "Domain task name" },
      "text": { "type": "string", "description": "Text to analyze" },
      "gpu": { "type": "boolean" }
    },
    "required": ["task", "text"]
  }
  ```

---

## 6. Multi-Modal Vision, Audio & Video

### `multimodal_task`
* **Description**: Universal multi-modal inference across images, audio waveforms, and video streams.
* **Supported Modalities**:
  - **Vision**: `image-classification`, `object-detection`, `image-segmentation`, `visual-question-answering` (`vqa`), `doc-vqa`, `zero-shot-image-classification`, `depth-estimation`, `image-super-resolution`, `text-to-image`
  - **Audio**: `automatic-speech-recognition` (`asr`), `text-to-speech` (`tts`), `audio-classification`, `voice-activity-detection` (`vad`), `emotion-recognition`
  - **Video**: `video-classification`, `action-recognition`, `keyframe-extraction`
* **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "task": { "type": "string", "description": "Multimodal task name" },
      "file": { "type": "string", "description": "Path to image, audio, or video file" },
      "prompt": { "type": "string", "description": "Prompt or visual question" },
      "gpu": { "type": "boolean" }
    },
    "required": ["task"]
  }
  ```

---

## 7. Semantic Search, Web & arXiv Scientific Grounding

### `semantic_search`
* **Description**: In-memory dense retrieval with **HyDE** (Hypothetical Document Embeddings). Embeds documents, generates hypothetical answers to expand query semantics, and computes cosine similarity ranking.
* **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "action": { "type": "string", "description": "'search' to query, 'add' to index documents, 'demo' for benchmark" },
      "query": { "type": "string", "description": "Search query" },
      "documents_path": { "type": "string", "description": "Path to documents to index" },
      "top_k": { "type": "integer", "description": "Number of top results (default: 5)" },
      "use_hyde": { "type": "boolean", "description": "Enable interactive HyDE hypothetical expansion" },
      "hyde_variants": { "type": "boolean", "description": "Generate multiple HyDE variants" }
    },
    "required": ["action"]
  }
  ```

---

## 8. ACDSO AutoML & Data Science

### `data_science`
* **Description**: Automated causal data science on tabular datasets (`.csv`, `.tsv`, `.xlsx`). Computes 5-objective Pareto causal AutoML, feature importance, correlation matrices, and generates Jupyter notebooks or PDF executive summaries.
* **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "mode": { "type": "string", "description": "'analyst' for exploratory profiling, 'science' for full AutoML, 'jupyter' to launch notebook" },
      "file": { "type": "string", "description": "Path to CSV or Excel dataset" },
      "prompt": { "type": "string", "description": "Analysis objective or target column instructions" },
      "export_pdf": { "type": "boolean", "description": "Export comprehensive PDF report" }
    },
    "required": ["mode"]
  }
  ```

---

## 9. Model Lifecycle, Quantization & Bandits

### `model_management`
* **Description**: Converts Hugging Face PyTorch/Safetensors weights into OpenVINO IR formats with FP16, INT8, or INT4 SINQ quantization.
* **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "action": { "type": "string", "description": "'prepare' to convert, 'prepare-all' to batch convert, 'sinq' to quantize" },
      "model_id": { "type": "string", "description": "Hugging Face model repository ID" },
      "weight_format": { "type": "string", "description": "fp16, int8, or int4 (default: int8)" },
      "sinq_nbits": { "type": "integer", "description": "SINQ bit-width (default: 4)" },
      "sinq_group_size": { "type": "integer", "description": "SINQ group size (default: 64)" }
    },
    "required": ["action"]
  }
  ```

---

### `report_bandit_feedback`
* **Description**: Submits reinforcement learning feedback (reward) to the contextual bandit router to dynamically improve model selection weights over time.
* **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "context": { "type": "integer", "description": "Context ID (0=Simple query, 1=Complex/Coding)" },
      "arm": { "type": "integer", "description": "Arm ID (0=Single model, 1=Consensus Fusion)" },
      "reward": { "type": "number", "description": "Reward score (1.0=success/good, 0.0=poor)" }
    },
    "required": ["context", "arm", "reward"]
  }
  ```

---

## 10. System Telemetry, Hardware & Health

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `get_system_info` | `{}` | Returns CPU name, logical core count, total RAM, runtime free RAM, GPU device name, total VRAM, and runtime free VRAM. |
| `get_database_stats` | `{}` | Returns total models ingested, task category distribution, and SQLite database file size. |
| `list_tasks` | `{"category": "audio|image|text|all"}` | Lists supported tasks and top recommended models for a specific modality. |
| `get_performance_stats` | `{}` | Returns inference latency benchmarks, token-per-second throughput, and hardware profile. |
| `get_decision_stats` | `{}` | Returns historical model selection decisions, confidence scores, and selection strategies. |
| `get_cache_stats` | `{}` | Returns model cache directory size, OpenVINO IR cache status, and weight footprint. |
| `clear_cache` | `{}` | Clears ephemeral model weights and temp files. |
| `update_database` | `{}` | Triggers fast curated update (~6,500 models across all 45 tasks) into SQLite. |
| `restore_backup` | `{}` | Restores configuration and SQLite catalog from backup points. |
