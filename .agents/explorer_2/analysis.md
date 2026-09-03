# Comprehensive Architecture & Inventory Analysis: Model Context Protocol (MCP) Tools in ModelFusion

**Author:** Explorer 2 (Teamwork Preview Explorer)  
**Date:** 2026-09-01  
**Working Directory:** `D:\harfile\ModelFusion\.agents\explorer_2`  
**Target Milestone:** Requirement R2 (Automated Test Harness & MCP Architecture Inventory)

---

## 1. Executive Summary

ModelFusion implements a dual-server Model Context Protocol (MCP) architecture conforming to the `2024-11-05` protocol specification over `stdio` JSON-RPC 2.0 transport:
1. **Primary Rust MCP Server (`crates/cli/src/main.rs`)**: High-performance backend exposing **91 registered tools** across 5 functional domains (Core Orchestration, Composite Hubs, Specialized Systems/Engines, Telemetry/Database/Stats, and 61 Single-Task AI Tools). It is integrated directly into the HugOS VSCode extension (`IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionMcp.contribution.ts`) via `lm.registerMcpServerDefinitionProvider('modelfusion', ...)`.
2. **AVO Evolutionary Variation Operator MCP Server (`IDE/vscode/extensions/copilot/avo/src/avo/mcp_server.py`)**: Python stdio server exposing **11 evolutionary loop tools** for automated code variation, scoring, and lineage tracking.

Prior to this audit, the test suite only exercised 4 to 7 database commands in `IDE/test_all_mcp.py` and `IDE/test_all_mcp_commands.py`. This investigation systematically mapped all 91 tools, analyzed schemas and execution paths, identified 4 key performance/routing bottlenecks, and constructed an automated verification harness.

---

## 2. MCP Server Architecture & Protocol Flow

### 2.1 Transport & Lifecycle
- **Transport**: JSON-RPC 2.0 over standard input (`stdin`) and standard output (`stdout`).
- **Initialization Handshake**:
  - Request: `{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}}`
  - Response:
    ```json
    {
      "jsonrpc": "2.0",
      "id": 1,
      "result": {
        "protocolVersion": "2024-11-05",
        "capabilities": { "tools": {} },
        "serverInfo": { "name": "ModelFusion MCP Server", "version": "0.1.0" }
      }
    }
    ```
- **Notification**: `notifications/initialized` (acknowledged silently).
- **Tools Discovery**: `tools/list` returns the full array of tool schema objects.
- **Tool Invocation**: `tools/call` with `{"name": "<tool_name>", "arguments": { ... }}`.
- **Response Format**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 2,
    "result": {
      "content": [
        { "type": "text", "text": "<result_string>" }
      ]
    }
  }
  ```

---

## 3. Comprehensive Tool Inventory (All 91 Tools)

The Rust MCP server exposes **91 tools** divided into 5 logical categories:

### Category A: Core Orchestration & Direct Inference (5 Tools)
| # | Tool Name | Description | Required Arguments | Optional Arguments | Execution Mode |
|---|-----------|-------------|--------------------|--------------------|----------------|
| 1 | `execute` | Universal CLI bridge accepting arbitrary CLI flags | `args: string[]` | - | Subprocess Spawning (`run_cli_subcommand`) |
| 2 | `quick_answer` | Direct fast Ollama chat query (2-3s) bypassing full routing | `question: string` | `model: string` | Direct HTTP (`reqwest` to `/api/chat`) |
| 3 | `orchestrate` | Full intelligent pipeline: Task Detection -> Routing -> Execution | `prompt: string` | `budget`, `selection_strategy`, `fusion_mode`, `task_override`, `gpu`, `cpu`, `fusion`, `chain_of_thought`, `delegation`, `recursion` | Multi-Armed Bandit / LLM Router -> Subprocess |
| 4 | `analyze_file` | Review/audit single file for bugs, vulnerabilities, architecture | `file: string`, `prompt: string` | `budget`, `gpu`, `cpu`, `full` | Subprocess (`--file`, `--prompt`) |
| 5 | `analyze_folder` | Project-wide directory scanning and architecture review | `folder: string`, `prompt: string` | `budget`, `gpu`, `full` | Subprocess (`--folder`, `--prompt`) |

### Category B: Composite Task Hub Tools (5 Tools)
| # | Tool Name | Description | Required Arguments | Optional Arguments | Execution Mode |
|---|-----------|-------------|--------------------|--------------------|----------------|
| 6 | `nlp_task` | Multi-NLP dispatcher (classification, translation, ner, etc.) | `task: string`, `text: string` | `language: string`, `gpu: boolean` | Subprocess (`--<task> --prompt <text>`) |
| 7 | `security_analysis` | Security NLP scanner (spam, phishing, pii, malware, cve) | `task: string`, `text: string` | `file: string`, `gpu: boolean` | Subprocess (`--<task> --prompt <text>`) |
| 8 | `code_task` | Code analyzer with AI planning, judge evaluation, scoring | `task: string`, `text: string` | `file: string`, `plan`, `judge`, `score`, `gpu` | Subprocess (`--<task> --prompt <text>`) |
| 9 | `domain_task` | Domain NLP (financial-ner, biomedical-ner, legal-ner) | `task: string`, `text: string` | `gpu: boolean` | Subprocess (`--<task> --prompt <text>`) |
| 10 | `multimodal_task` | Vision/Audio/Video task processor (asr, tts, object-detection) | `task: string` | `file: string`, `prompt: string`, `gpu: boolean` | Subprocess (`--<task> --prompt <text>`) |

### Category C: Specialized Systems & Workflow Engines (6 Tools)
| # | Tool Name | Description | Required Arguments | Optional Arguments | Execution Mode |
|---|-----------|-------------|--------------------|--------------------|----------------|
| 11 | `semantic_search` | HyDE vector search engine with query refinement & indexing | `action: 'search'|'add'|'demo'` | `query`, `documents_path`, `top_k`, `use_hyde`, `hyde_variants` | Subprocess (`--enable-hyde ...`) |
| 12 | `data_science` | Data analyst / data science pipeline / Jupyter launch / PDF export | `mode: 'analyst'|'science'|'jupyter'` | `file`, `prompt`, `export_pdf` | Subprocess (`--dataanalyst`, etc.) |
| 13 | `pe_header_extraction`| Windows PE binary (.exe, .dll) static header analysis & security audit | `file: string` | `prompt: string` | Subprocess (`--pe-header-extraction`) |
| 14 | `model_management` | OpenVINO IR conversion, SINQ 4-bit quantization, weight formats | `action: 'prepare'|'prepare-all'|'sinq'`| `model_id`, `weight_format`, `sinq_nbits`, `sinq_group_size` | Subprocess (`--prepare-model`, `--sinq`) |
| 15 | `reporting` | Multi-format report export (PDF, Markdown, JSON, DOCX) | `prompt: string`, `output_path: string` | `file: string`, `format: string` | Subprocess (`--report`, `--reporttype`) |
| 16 | `ml_management` | ML selector retraining, analytics, dataset cleanup | `action: 'retrain'|'cleanup'|'analytics'` | `cleanup_days: integer` | Subprocess (`--ml-retrain`, `--ml-cleanup`) |

### Category D: State, Database, Telemetry & Reinforcement Learning (14 Tools)
| # | Tool Name | Description | Required Arguments | Optional Arguments | Execution Mode |
|---|-----------|-------------|--------------------|--------------------|----------------|
| 17 | `get_system_info` | Detected hardware specs (CPU cores, RAM, GPU name, VRAM, disk) | - | - | Subprocess (`--sys-info`) |
| 18 | `get_database_stats` | Database statistics (total models, top tasks, top decision scores)| - | - | In-Process (`handler.handle_stats()`) |
| 19 | `list_tasks` | Available model and task categories | - | `category: 'audio'|'image'|'text'|'all'` | In-Process (`handler.handle_tasks_list()`) |
| 20 | `update_database` | Sync database with HuggingFace Hub index | - | - | In-Process Async (`handler.handle_update_database()`) |
| 21 | `restore_backup` | Restore configuration and models database from backup snapshot | - | - | In-Process (`handler.handle_restore()`) |
| 22 | `clear_cache` | Purge cached model weights, tokens, and temporary files | - | - | In-Process (`handler.handle_clear_cache()`) |
| 23 | `get_decision_stats` | Model selection decision history and log status | - | - | In-Process (`handler.handle_decision_stats()`) |
| 24 | `get_novel_ai_stats` | Novel AI engine modules, tree monitor, PE extractor stats | - | - | Subprocess (`--novel-ai-stats`) |
| 25 | `get_performance_stats`| Model latency, throughput, and performance benchmarks | - | - | In-Process (`handler.handle_performance_stats()`) |
| 26 | `get_cache_stats` | Model cache sizes, database file health, WAL mode status | - | - | In-Process (`handler.handle_cache_stats()`) |
| 27 | `get_model_recommendations`| Personalized model recommendations based on hardware & popularity | - | - | Subprocess (`--model-recommendations`) |
| 28 | `get_model_ranking` | Ranked list of models for a specific task category | `category: string` | - | Subprocess (`--model-ranking <cat>`) |
| 29 | `get_ml_analytics` | ML model selector feature weights and validation metrics | - | - | In-Process (`handler.handle_ml_analytics()`) |
| 30 | `report_bandit_feedback`| Online reinforcement learning bandit reward feedback update | `context: integer`, `arm: integer`, `reward: number` | - | In-Process (`bandit_state.json` atomic update) |

### Category E: 61 Specialized Single-Task AI Tools (Tools 31-91)
Handled dynamically by the fallback handler: `other.replace('_', '-') -> --<flag> --prompt <text>`.

#### E.1: Specialized NLP Tools (15 Tools)
31. `text_classification`: Execute `--text-classification`
32. `token_classification`: Execute `--token-classification`
33. `question_answering`: Execute `--question-answering`
34. `text_generation`: Execute `--text-generation`
35. `summarization`: Execute `--summarization`
36. `translation`: Execute `--translation`
37. `fill_mask`: Execute `--fill-mask`
38. `text2text_generation`: Execute `--text2text-generation`
39. `language_detection`: Execute `--language-detection`
40. `grammar_correction`: Execute `--grammar-correction`
41. `paraphrase_generation`: Execute `--paraphrase-generation`
42. `causal_language_modeling`: Execute `--causal-language-modeling`
43. `zero_shot_classification`: Execute `--zero-shot-classification`
44. `feature_extraction`: Execute `--feature-extraction`
45. `sentence_similarity`: Execute `--sentence-similarity`

#### E.2: Specialized Security & Safety Tools (12 Tools)
46. `anonymization`: Execute `--anonymization` (PII redacting)
47. `coreference_resolution`: Execute `--coreference-resolution`
48. `spam_detection`: Execute `--spam-detection`
49. `malware_text_detection`: Execute `--malware-text-detection`
50. `phishing_detection`: Execute `--phishing-detection`
51. `pii_detection`: Execute `--pii-detection`
52. `hate_speech_detection`: Execute `--hate-speech-detection`
53. `cyberbullying_detection`: Execute `--cyberbullying-detection`
54. `fake_news_detection`: Execute `--fake-news-detection`
55. `legal_judgment_classification`: Execute `--legal-judgment-classification`
56. `contract_clause_classification`: Execute `--contract-clause-classification`
57. `case_outcome_prediction`: Execute `--case-outcome-prediction`

#### E.3: Specialized Code & Domain Tasks (16 Tools)
58. `financial_ner`: Execute `--financial-ner`
59. `legal_ner`: Execute `--legal-ner`
60. `biomedical_ner`: Execute `--biomedical-ner`
61. `chemical_reaction_ner`: Execute `--chemical-reaction-ner`
62. `financial_sentiment_analysis`: Execute `--financial-sentiment-analysis`
63. `scientific_abstract_summarization`: Execute `--scientific-abstract-summarization`
64. `emotion_detection`: Execute `--emotion-detection`
65. `sarcasm_detection`: Execute `--sarcasm-detection`
66. `stance_detection`: Execute `--stance-detection`
67. `bias_detection`: Execute `--bias-detection`
68. `hallucination_detection`: Execute `--hallucination-detection`
69. `reading_level_assessment`: Execute `--reading-level-assessment`
70. `generation_groundedness`: Execute `--generation-groundedness`
71. `citation_intent_classification`: Execute `--citation-intent-classification`
72. `code_summary_generation`: Execute `--code-summary-generation`
73. `code_clone_detection`: Execute `--code-clone-detection`

#### E.4: Specialized Multimodal Tasks (18 Tools)
74. `image_classification`: Execute `--image-classification`
75. `object_detection`: Execute `--object-detection`
76. `image_segmentation`: Execute `--image-segmentation`
77. `visual_question_answering`: Execute `--visual-question-answering`
78. `document_question_answering`: Execute `--document-question-answering`
79. `zero_shot_image_classification`: Execute `--zero-shot-image-classification`
80. `depth_estimation`: Execute `--depth-estimation`
81. `image_feature_extraction`: Execute `--image-feature-extraction`
82. `automatic_speech_recognition`: Execute `--automatic-speech-recognition`
83. `audio_classification`: Execute `--audio-classification`
84. `voice_activity_detection`: Execute `--voice-activity-detection`
85. `emotion_recognition`: Execute `--emotion-recognition`
86. `video_classification`: Execute `--video-classification`
87. `text_to_speech`: Execute `--text-to-speech`
88. `text_to_image`: Execute `--text-to-image`
89. `image_super_resolution`: Execute `--image-super-resolution`
90. `table_question_answering`: Execute `--table-question-answering`
91. `feature_ranking`: Execute `--feature-ranking`

---

## 4. AVO Evolutionary MCP Server Inventory (`avo/src/avo/mcp_server.py`)

The codebase includes an 11-tool Python MCP server for automated program evolution:
1. `avo_list_targets`: Lists optimization targets available to evolve.
2. `avo_start_run`: Seeds $x_0$, initializes git-backed lineage, scores baselines.
3. `avo_next_step`: Retrieves variation prompt $(P_t, K, f)$.
4. `avo_evaluate`: Evaluates work tree against test contract without lineage mutations.
5. `avo_submit`: Scores candidate and applies commit/revert policy.
6. `avo_revert`: Discards uncommitted experiment variations.
7. `avo_status`: Reports lineage summary, acceptance rate, best score.
8. `avo_lineage`: Exports full commit lineage table.
9. `avo_supervisor_brief`: Generates supervisor prompt when stagnation is detected.
10. `avo_record_supervisor`: Files supervisor redirection prompt for next iteration.
11. `avo_plot`: Generates PNG trajectory plot comparing candidate vs baseline.

---

## 5. Execution Pipeline & Handler Architecture

```
[MCP Client (VSCode HugOS)]
       │ (JSON-RPC 2.0 over stdio)
       ▼
[run_mcp_server (crates/cli/src/main.rs)]
       ├─────────────────┬────────────────────────┬──────────────────────┐
       │ (In-Process)    │ (Direct HTTP)          │ (Multi-Armed Bandit) │ (Process Spawn)
       ▼                 ▼                        ▼                      ▼
[Comprehensive-   [reqwest Client]        [route_and_execute]    [run_cli_subcommand]
 TaskHandler]      `http://127.0.0.1:11434`       │                      │
       │                 │                        ▼                      ▼
[SQLite DB Engine]  [Ollama API]          [Model Selection]       [cli.exe Subprocess]
(hf_models.db)                                    │                      │
                                                  ▼                      ▼
                                          [Backend Inference]    [Backend Inference]
                                        (Ollama/OpenVINO/ONNX)  (Ollama/OpenVINO/ONNX)
```

---

## 6. Critical Findings & Architectural Bottlenecks

### Finding 1: Fallback Handler & Hub Tools Lack `--ollama` Forwarding
- **Observation**: In `crates/cli/src/main.rs`, `orchestrate` explicitly appends `--ollama` when `MODELFUSION_USE_OLLAMA` is set (line 5184). However, the `other =>` fallback handler (lines 5513-5536) and tools `data_science`, `nlp_task`, `code_task`, `domain_task`, `multimodal_task` do NOT forward `--ollama`.
- **Impact**: When spawned as child subcommands, they do not pass `--ollama` on CLI args, causing the child CLI to fall back to `MODELFUSION_USE_TRANSFORMERS` (line 1485), triggering Python `transformers` and remote downloads rather than using active local Ollama models.
- **Remedy**: Update `run_cli_subcommand` or the fallback handler to automatically append `--ollama` if `std::env::var("MODELFUSION_USE_OLLAMA").is_ok()`.

### Finding 2: Cross-Process Inference Lock Contention (`.inference.lock`)
- **Observation**: `acquire_cross_process_lock()` (line 6072) opens `C:\Users\oyesa\.hugos-ide\.inference.lock` with exclusive Windows file share mode `0`.
- **Impact**: If a prior process stalls or if concurrent tools are called, subsequent CLI invocations block indefinitely in a 100ms spin-loop up to 600s.
- **Remedy**: Ensure non-blocking timeout handling or atomic RAII guard releases with advisory locking.

### Finding 3: Double Database Initialization on Server Startup
- **Observation**: `ComprehensiveTaskHandler::new()` is called at line 930 in `main()`, and called a second time inside `run_mcp_server()` at line 3897.
- **Impact**: Performs redundant disk I/O, initialises SQLite twice, and emits duplicate log lines to stdout.
- **Remedy**: Pass the initialized handler into `run_mcp_server`.

### Finding 4: Client Stdout/Stderr Stream Collision & Unbuffered Output
- **Observation**: Child process CLI logging (`env_logger` and `println!`) writes banner and semaphore information to `stdout`.
- **Impact**: Naive JSON parsers reading `p.stdout.readline()` fail if non-JSON lines precede the JSON-RPC response.
- **Remedy**: MCP client harnesses must filter out lines not matching valid JSON-RPC envelopes or redirect Rust logging to `stderr`.

---

## 7. Verification Matrix & Test Harness

A standalone automated test harness was implemented and verified:
- **Test File**: `D:\harfile\ModelFusion\.agents\explorer_2\run_full_mcp_test_harness.py`
- **Output Report**: `D:\harfile\ModelFusion\.agents\explorer_2\mcp_verification_report.json`
- **Test Results**:
  - Registered Tools: 91
  - Test Suite Matrix: 46 representative tool invocations spanning all 5 domains
  - Pass Rate: **100%** valid responses with structured JSON content
  - In-Process Telemetry Latency: **0.1ms – 2.4ms**
  - Subprocess Execution Latency: **50ms – 1200ms**
