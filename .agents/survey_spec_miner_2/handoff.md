# Handoff Report: Backend & IPC Specification Mining

**Agent ID:** `survey_spec_miner_2` (Backend & IPC Spec Miner)  
**Parent Agent:** `orchestrator_1` / Caller `b359a14e-cb9c-45f2-8e1e-6bb6dc7ed242`  
**Date:** 2026-08-31T19:56:45Z  
**Handoff Type:** Hard (Task Complete)

---

## 1. Observation

1. **Rust Server Daemon & HTTP Endpoints (`crates/cli/src/main.rs:2250-3635`)**:
   - `run_server` binds to `127.0.0.1:5000` via Tokio `TcpListener`.
   - Core endpoint `/orchestrate` handles model routing, budget checking, and GPU/CPU flags.
   - OpenAI translation endpoint `/v1/chat/completions` translates chat messages into internal `/orchestrate` format with automated downsampling on VRAM < 10GB (`crates/cli/src/main.rs:2356-2359`).
   - Server-side fast interception at lines 2520-2950 intercepts chat history compaction and 35+ slash commands in <1ms without LLM inference overhead.
   - Additional REST endpoints: `/stats`, `/sys-info`, `/tasks`, `/decision-stats`, `/novel-ai-stats`, `/performance-stats`, `/cache-stats`, `/model-recommendations`, `/model-ranking`, `/clearcache`, `/update`, `/pe-header-extraction`, `/ml-analytics`, `/analyze-file`, `/analyze-folder`, `/report-bandit-feedback` (`crates/cli/src/main.rs:3539-3615`).
   - Connection management: `tokio::io::split` with client disconnect listener detecting socket drop (`crates/cli/src/main.rs:2440-2446`), keep-alive spaces sent every 5s on chunked transfer.

2. **MCP Stdio Server Protocol (`crates/cli/src/main.rs:3894-4400`)**:
   - Protocol version: `2024-11-05` JSON-RPC 2.0 over stdin/stdout.
   - 35+ tools exposed including `execute`, `quick_answer`, `orchestrate`, `analyze_file`, `analyze_folder`, `nlp_task`, `security_analysis`, `code_task`, `domain_task`, `multimodal_task`, `semantic_search`, `data_science`, `pe_header_extraction`, `model_management`, `reporting`, `ml_management`, and 14 system stat tools.
   - Extension integration: `ModelFusionMcpContrib` in `IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionMcp.contribution.ts` registers `vscode.McpStdioServerDefinition('ModelFusion', cliPath, ['--mcp', '--db-path', dbPath])`.

3. **OpenEvolve Evolutionary Engine (`src/openevolve/`)**:
   - Controller (`openevolve/controller.py`): `OpenEvolve` orchestrates prompt sampling, LLM generation, evaluation, novelty filtering, and database updates.
   - Database (`openevolve/database.py`): MAP-Elites multi-dimensional feature grid (`archive_size`, `feature_bins`, `feature_dimensions`), island population structure (`num_islands`, `island_feature_maps`, `migration_interval`), and absolute best program tracking.
   - Evolution Tracing (`openevolve/evolution_trace.py`): Logs parent-child transitions, code diffs, prompts, responses, and metric improvements to `.jsonl`, `.json`, or `.hdf5`.
   - Process Parallelism (`openevolve/process_parallel.py`): Multi-process worker pool with graceful signal shutdown.

4. **AVO (Autonomous Evolution) Framework (`IDE/vscode/extensions/copilot/avo/`)**:
   - Implements paper arXiv:2603.24517 (*Agentic Variation Operators*).
   - Core types (`types.py`): Score (`correct`, `metrics`, `primary`), LineageEntry (`version`, `commit`, `score`, `summary`), StepRecord (`step`, `accepted`, `score`, `best_primary`, `rejected_patch`).
   - Strict gate: `if not correct: primary = 0.0` (`types.py:85-86`).
   - Evolution Loop (`loop.py`): Continuous variation loop with step budget (`max_steps`), time budget (`time_budget_s`), and stagnation monitoring (`stagnation_window`).
   - Supervisor Intervention (`loop.py:174-191`): Meta-agent intervention when search stalls for $\ge$ stagnation steps.
   - ModelFusion Agent Backend (`agents/modelfusion.py`): Calls `http://127.0.0.1:5000/orchestrate` and executes file alterations via XML `<bash>` and `<replace>` tags.

5. **VS Code Extension & Webview Provider (`IDE/vscode/extensions/copilot/src/`)**:
   - `ModelFusionLMProvider` (`modelFusionProvider.ts`): Spawns and manages `cli.exe --server --port 5000`, single-instance socket check on port 5000 (`lines 173-196`), inflight promise coalescing (`lines 49-53`), and AVO runner subprocess spawning (`lines 1201-1356`).
   - `InlineDiffManager` (`evolve/inlineDiff.ts`): Cursor-style inline diff view showing additions (green) and deletions (red) with Accept/Reject shortcuts (`Ctrl+Shift+Y`, `Ctrl+Shift+N`).
   - `ModelManagerPanel` (`modelManagerPanel.ts`): Webview panel implementation with dark-themed UI for configuring Ollama, OpenVINO, and Transformers.

---

## 2. Logic Chain

1. **Backend Integration**: The ModelFusion backend already supports all necessary endpoints (`/orchestrate`, `/v1/chat/completions`, `/stats`, `/tasks`, `/decision-stats`, etc.) and MCP tools. Therefore, the Multi-Agent Teams and Evolution Dashboard does not require reinventing server protocols; it can directly query the existing port 5000 API server.
2. **Evolutionary Studio Architecture (R2)**: Both OpenEvolve and AVO provide programmatic APIs and event models (scores, step trajectories, lineages, AST features, candidate diffs). A unified execution controller wrapping `openevolve.api` and `avo.cli` allows the IDE Dashboard to launch, pause, resume, and stop evolutionary runs while extracting candidate code patches for the diff viewer.
3. **High-Speed IPC & 60fps UI (R3)**: During active evolutionary search and multi-agent reasoning, high-frequency token events and evaluation metrics can flood the VS Code Extension Host. Implementing an asynchronous ring buffer with a 16.6ms (60Hz) throttled batch dispatcher ensures the Extension Host and Webview UI remain completely fluid and non-blocking during heavy inference.

---

## 3. Caveats

- **External Hardware Dependencies**: Local GPU inference depends on NVIDIA drivers (`nvidia-smi`) and Ollama daemon (`localhost:11434`). On CPU-only machines, inference falls back to OpenVINO or HuggingFace Serverless API.
- **Subprocess Isolation**: Long-running AVO runs spawn external Python processes (`python -m avo.cli`); killing runs requires terminating child process trees cleanly (`taskkill /T /F` on Windows) to prevent orphaned worker processes.

---

## 4. Conclusion

1. ModelFusion backend infrastructure is robust, featuring hardware-aware LLM routing, fast-interception slash command routing, multi-model consensus fusion, MCP tools, and native OpenEvolve / AVO evolutionary search runners.
2. The specifications in `analysis.md` establish clear data contracts and protocols for:
   - **R2 (OpenEvolve & AVO Studio)**: State machine execution controls (`launch`, `pause`, `resume`, `stop`), real-time fitness schemas, candidate diff structures, and one-click editor application.
   - **R3 (Real-Time IPC & Event Streaming)**: 60fps decoupled ring buffer architecture with frame-synchronized batching and Web Worker offloading.

---

## 5. Verification Method

To independently verify the discoveries and backend interfaces:
1. **Server Endpoint Verification**:
   - Run `cargo test` in `crates/cli` or start `target/release/cli.exe --server --port 5000` and send a test POST request to `http://127.0.0.1:5000/stats`.
2. **OpenEvolve Verification**:
   - Inspect `src/openevolve/openevolve/api.py` and run `python -m openevolve.cli --help` to confirm CLI parameters and configuration flags.
3. **AVO Verification**:
   - Inspect `IDE/vscode/extensions/copilot/avo/src/avo/loop.py` and `types.py` to confirm the lineage and scoring contracts.
4. **Specification Document Inspection**:
   - View `D:\harfile\ModelFusion\.agents\survey_spec_miner_2\analysis.md` for complete feature mappings, edge case matrices, and TypeScript schemas.
