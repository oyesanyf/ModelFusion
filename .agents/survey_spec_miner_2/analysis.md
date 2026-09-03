# ModelFusion Backend, Runner, and Real-Time IPC Specification

**Document Version:** 1.0.0  
**Author:** Backend & IPC Spec Miner (`survey_spec_miner_2`)  
**Target Requirements:** R1 (Multi-Agent Dashboard), R2 (OpenEvolve & AVO Studio), R3 (Real-Time IPC & Event Streaming Architecture)  
**Date:** 2026-08-31  

---

## 1. Executive Summary

This specification provides the comprehensive discovery, data schemas, API contracts, execution control protocols, and real-time IPC architecture for integrating the **HugOS IDE Multi-Agent Teams, OpenEvolve, and AVO (Autonomous Evolution) Dashboard** with the **ModelFusion** backend engine.

ModelFusion operates as a hybrid architecture consisting of:
1. **Rust Core Daemon (`cli.exe`)**: High-performance multi-threaded HTTP server (port 5000) and MCP Stdio JSON-RPC server with hardware-aware resource query (CPU, GPU VRAM, RAM), adaptive concurrency semaphores, fast-path interception (<1ms), LLM routing, and multi-model consensus fusion panel.
2. **OpenEvolve Python Engine (`src/openevolve/`)**: High-level evolutionary optimization library implementing MAP-Elites feature grids, island-based population dynamics, novelty rejection sampling, cascaded evaluation pipelines, and JSONL/HDF5 evolution tracing.
3. **AVO (Agentic Variation Operators) Runner (`IDE/vscode/extensions/copilot/avo/`)**: Continuous autonomous search engine (arXiv:2603.24517) executing iterative prompt-based mutations, fitness evaluations against ground-truth benchmarks, supervisor interventions on search stagnation, and Git-backed lineage tracking ($P_t = \{(x_i, f(x_i))\}$).
4. **VS Code Extension Layer (`copilot/dist/extension.js`)**: TypeScript client provider bridging VS Code chat participants (`@agent`), slash commands (`/evolve`, `/stats`, `/security`), inline diff managers (green/red gutter decorations with Accept/Reject shortcuts), and Webview panels (`ModelManagerPanel`).

---

## 2. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Server Endpoints | `/orchestrate` (HTTP POST) | Full ModelFusion orchestration pipeline: task detection, model selection, execution, and multi-model fusion | JSON: `{ prompt, budget, selection_strategy, fusion_mode, fusion_models, gpu, cpu, openvino, ollama, model, options }` | HTTP 200 chunked JSON `{ "content": string }` | 503 if fast pool closed; 400 invalid JSON; fallbacks on LLM router failure | `crates/cli/src/main.rs:2373` |
| 2 | Server Endpoints | `/v1/chat/completions` | OpenAI-compatible translation endpoint converting OpenAI chat messages into `/orchestrate` requests with VRAM-aware downsampling | JSON: OpenAI messages schema `{ model, messages: [{ role, content }] }` | HTTP 200 chunked JSON with standard response payload | 400 Bad Request if malformed JSON; auto downsamples >10B models if VRAM < 10GB | `crates/cli/src/main.rs:2334` |
| 3 | Fast Interception | Sub-millisecond Command Interception | Server-side regex/tag parser intercepting chat compaction and 35+ slash commands without LLM overhead (<1ms) | Parsed prompt tokens from `@agent` or `/command` | Direct markdown summary / system telemetry JSON | Fallback to standard orchestration if unrecognized | `crates/cli/src/main.rs:2520-3050` |
| 4 | Server Endpoints | `/stats`, `/sys-info`, `/tasks` | Telemetry endpoints querying database models, tasks categorization, and hardware resources (CPU, RAM, GPU, Disk) | HTTP POST with optional `{ "category": "all" }` | Formatted markdown/JSON specs of system & DB state | Returns error string wrapped in JSON response | `crates/cli/src/main.rs:3539-3548` |
| 5 | Server Endpoints | `/decision-stats`, `/performance-stats`, `/cache-stats` | AI decision tracking, model latency benchmarks, and cache memory inspection | HTTP POST `{}` | Performance metrics, cache hit counts, decision distributions | Error message string in response JSON | `crates/cli/src/main.rs:3549-3560` |
| 6 | Server Endpoints | `/model-ranking`, `/model-recommendations` | Task-specific model ranking based on multi-objective benchmark scores | JSON `{ "category": string }` | Ranked list of models with latency, accuracy, and memory ratings | Default fallback to `text-generation` category | `crates/cli/src/main.rs:3561-3567` |
| 7 | Server Endpoints | `/report-bandit-feedback` | Multi-armed bandit reinforcement learning feedback loop updating reward state | JSON `{ "context": int (0=Simple, 1=Complex), "arm": int (0=Single, 1=Fusion), "reward": float }` | Feedback status string with updated expected reward value | Returns `"Error: Invalid context or arm index"` | `crates/cli/src/main.rs:3599-3615` |
| 8 | MCP Server | MCP Stdio Protocol Server | Model Context Protocol v2024-11-05 implementation over stdin/stdout exposing 35+ tools | JSON-RPC 2.0 requests (`initialize`, `tools/list`, `tools/call`) | JSON-RPC 2.0 tool results & capability manifests | Standard JSON-RPC error response objects | `crates/cli/src/main.rs:3894-4400` |
| 9 | MCP Server | Universal CLI Tool (`execute`) | MCP tool allowing execution of arbitrary ModelFusion CLI flag configurations | JSON-RPC `{ "name": "execute", "arguments": { "args": string[] } }` | Command stdout/stderr packaged into MCP tool result | Exit code error captured in result text | `crates/cli/src/main.rs:3941-3954` |
| 10 | MCP Server | Fast Direct QA Tool (`quick_answer`) | MCP tool calling local Ollama directly, bypassing heavy orchestration for 2-3s answers | JSON-RPC `{ "name": "quick_answer", "arguments": { "question": string, "model": string } }` | Plain text answer string | Ollama connection error fallback | `crates/cli/src/main.rs:3956-3966` |
| 11 | Multi-Model Engine | Multi-Model Consensus Fusion Panel | Runs panel of $N$ models (batched by VRAM availability), submits answers to LLM Judge, synthesizes consensus | Prompt + candidate model configs | Synthesized final response; structured JSON judge analysis | Minority override rule if minority answer has superior code evidence | `crates/core/src/fusion_engine/` |
| 12 | OpenEvolve Core | MAP-Elites Evolutionary Database | High-dimensional feature archive & island populations preserving elite diverse candidates | Program objects with code, metrics, and AST features | Multi-island database archive, best program tracking | Fallbacks to numeric averages if `combined_score` missing | `src/openevolve/openevolve/database.py` |
| 13 | OpenEvolve Core | Evolution Tracing (`EvolutionTracer`) | Logs state-action-reward evolution transitions, code diffs, prompts, and metric improvements | Parent/child program pairs, evaluation metrics | Buffered `.jsonl`, `.jsonl.gz`, or `.json` trace files | Buffer auto-flushes on close; handles disk write errors | `src/openevolve/openevolve/evolution_trace.py` |
| 14 | OpenEvolve Core | Process Parallel Controller | Async multi-process worker pool for concurrent candidate generation and sandboxed evaluation | Config, initial program, evaluator script | Real-time evaluated programs pushed into database | Signal handlers for graceful SIGINT/SIGTERM shutdown | `src/openevolve/openevolve/process_parallel.py` |
| 15 | OpenEvolve Core | High-Level Python API | Library interface (`run_evolution`, `evolve_function`, `evolve_code`) | Source code string/file + evaluator callable/file | `EvolutionResult(best_program, best_score, best_code, metrics)` | Raises `ValueError` if no LLMs configured | `src/openevolve/openevolve/api.py` |
| 16 | AVO Engine | Autonomous Evolution Loop (`loop.py`) | Multi-step continuous evolution runner executing variation operators against benchmarks | `RunConfig(max_steps, time_budget_s, stagnation_window, backend)` | `LoopResult(steps, accepted, best_primary, stopped_because)` | Traps SIGINT for clean 1-step drain; records rejections | `IDE/.../avo/src/avo/loop.py` |
| 17 | AVO Engine | Mathematical Lineage & Correctness Gate | Lineage tracking $P_t = \{(x_i, f(x_i))\}$ with strict gate: `if not correct: primary = 0.0` | Target `eval.py` output JSON: `{ correct, metrics, primary, error }` | `Score`, `LineageEntry`, `StepRecord` trajectory | Invalid JSON or failed evaluation scores 0.0 | `IDE/.../avo/src/avo/types.py` |
| 18 | AVO Engine | Supervisor Intervention Operator | Automatic meta-prompting of supervisor agent when search stalls for $\ge$ stagnation window | Trajectory tail, lineage entries, knowledge base index | Markdown supervisor steering note passed to variation agent | Supervisor failure falls back to default variation prompt | `IDE/.../avo/src/avo/loop.py:174` |
| 19 | AVO Engine | ModelFusion Agent Backend | AVO variation agent driver communicating with ModelFusion `/orchestrate` | Prompt + sandboxed work directory | Code changes executed via `<bash>` and `<replace>` XML tags | Iteration limit (120) & timeout protection (900s) | `IDE/.../avo/src/avo/agents/modelfusion.py` |
| 20 | Extension Host | `ModelFusionLMProvider` | VS Code Chat Provider managing local server lifecycle, slash commands, and requests | User chat requests from Chat Panel / `@agent` | Streamed LanguageModelResponsePart chunks to UI | Socket timeout (600s), inflight request coalescing, CLI spawn fallback | `copilot/src/.../modelFusionProvider.ts` |
| 21 | Extension Host | AVO Runner Execution Bridge | Dynamic evaluator generation via LLM followed by spawning `python -m avo.cli` subprocess | Open editor buffer code + user focuses | Streamed progress reporting to chat and inline diff trigger | Subprocess kill on `CancellationToken` | `copilot/src/.../modelFusionProvider.ts:1201` |
| 22 | Extension Host | Inline Diff Decorator (`InlineDiffManager`) | Cursor-style inline diff view showing additions (green) and deletions (red) with Accept/Reject | Original code vs evolved code string | Editor text decorations and keyboard command bindings | Reverts cleanly on cancellation or rejection | `copilot/src/.../evolve/inlineDiff.ts` |
| 23 | Webview | Model Manager Panel (`ModelManagerPanel`) | Responsive dark-theme Webview for configuring Ollama, OpenVINO, and Transformer models | Extension URI and VS Code configuration | HTML/CSS/JS interactive settings GUI with auto Ollama detection | Webview error handling via postMessage | `copilot/src/.../modelManagerPanel.ts` |

---

## 3. Edge Cases Discovered

| # | Feature | Input / Condition | Observed Behavior |
|---|---------|-------------------|-------------------|
| 1 | `/orchestrate` | Client disconnects or cancels request mid-inference | Rust server splits socket (`tokio::io::split`); parallel `client_disconnect` future detects EOF (0 bytes read) and terminates inference task immediately to free inference permit. |
| 2 | `/orchestrate` | Fast inference pool exhausted | Returns HTTP 503 Service Unavailable with `{"error":"Fast inference pool closed"}` immediately. |
| 3 | `/orchestrate` | Massive prompt length (>5,000 or >15,000 characters) | Extension client dynamically scales down budget ($0.7\times$ or $0.4\times$) to prevent GPU VRAM out-of-memory errors on large KV caches. |
| 4 | `/orchestrate` | Long inference run exceeding standard HTTP timeouts | Rust server sends keep-alive whitespace chunks every 5s over chunked transfer-encoding; client strips leading whitespace before parsing final JSON. |
| 5 | `/orchestrate` (compaction) | Prompt contains VS Code history compaction preamble | Fast interception matches text in <1ms and returns pre-formatted static summary, completely bypassing LLM inference. |
| 6 | `/v1/chat/completions` | Client requests 14B or 32B model on hardware with <10GB VRAM | Server queries `nvidia-smi` / WMI; detects low VRAM and auto-downsamples model request to `qwen2.5:7b` to guarantee GPU execution. |
| 7 | `/report-bandit-feedback` | `context >= 2` or `arm >= 2` | Returns literal string `"Error: Invalid context or arm index"`. |
| 8 | OpenEvolve Evaluator | Evaluator returns metrics without `combined_score` | Computes arithmetic mean of all numeric metric fields and logs a warning advising explicit `combined_score`. |
| 9 | OpenEvolve Evaluator | Cascade evaluation enabled but evaluator lacks `evaluate_stage1` | Auto-detects absence of stage functions from AST/source scan and disables cascade evaluation to prevent crash. |
| 10 | OpenEvolve Parallel | Non-serializable callable or lambda provided as evaluator | Extracts source code via AST / bracket-aware parser and generates standalone Python file wrapper to allow IPC across worker processes. |
| 11 | AVO Scoring | Candidate passes benchmarks with high throughput but fails correctness test | Strict gate: `primary` is forced to `0.0`, candidate is rejected, and failure note is recorded in lineage trajectory. |
| 12 | AVO Search | Search stagnates (no new best score for $\ge$ `stagnation_window` steps) | Evolution loop temporarily halts variation operator, constructs supervisor context from knowledge base and trajectory tail, invokes Supervisor Agent for architectural redirect, and reverts any file modifications made by the supervisor. |
| 13 | Extension Server Spawn | Port 5000 already bound by another IDE instance or background process | Extension tests port via `net.createServer().listen(5000)`: detects `EADDRINUSE`, skips spawning new process, and reuses existing running server. |
| 14 | Extension Server Spawn | Server crashes or exits unexpectedly | Exit handler detects non-disposed state, logs message to Output Channel, and automatically respawns `cli.exe` after a 3-second delay. |
| 15 | ModelFusion Agent | Tool command in XML `<replace>` specifies path outside workspace directory | Path resolution detects directory traversal attempt (`relative_to` fails) and returns `"Error: Path is outside workspace"`. |

---

## 4. Requirement R2 Specification: OpenEvolve & AVO Evolutionary Search Studio

### 4.1 Execution Control Architecture

The evolutionary engine requires a robust, non-blocking execution lifecycle that allows interactive monitoring, live parameter adjustments, and clean process control.

```
                  ┌──────────────────────┐
                  │         IDLE         │
                  └──────────┬───────────┘
                             │ launch(target, config)
                  ┌──────────▼───────────┐
                  │     INITIALIZING     │
                  └──────────┬───────────┘
                             │ initial eval complete
                  ┌──────────▼───────────┐
                  │    RUNNING (LOOP)    ├──────────┐
                  └────┬────────────▲────┘          │ pause()
          step done    │            │ resume()      │
          new step     │  ┌─────────┴─────────┐     │
                       │  │       PAUSED      │◄────┘
                       │  └───────────────────┘
                       │
                       │ stop() / max_steps reached / target_score met
                  ┌────▼─────────────────┐
                  │ COMPLETED / STOPPED  │
                  └──────────────────────┘
```

#### Execution Control Commands (Extension Host ↔ Backend Runner)

1. **`evolution.launch`**:
   - **Payload**:
     ```json
     {
       "runId": "evo_run_20260831_195500",
       "engine": "openevolve" | "avo" | "builtin",
       "targetFile": "d:/harfile/ModelFusion/src/core.py",
       "evaluatorPath": "d:/harfile/ModelFusion/tests/eval_core.py",
       "config": {
         "maxSteps": 50,
         "timeBudgetSeconds": 3600,
         "stagnationWindow": 5,
         "model": "qwen2.5:7b",
         "backend": "modelfusion",
         "numIslands": 4,
         "migrationInterval": 10,
         "customFocuses": ["latency", "memory_safety"]
       }
     }
     ```
2. **`evolution.pause`**:
   - Suspends the variation/evaluation loop immediately after completing the in-flight step.
   - Preserves worker process pool and current database/lineage state in memory.
3. **`evolution.resume`**:
   - Resumes the iteration loop from the last committed step index.
4. **`evolution.stop`**:
   - Gracefully drains the current iteration, closes trace buffers, exports best candidate to disk, and terminates worker child processes.
   - Optional `force: true` sends immediate SIGKILL / `taskkill.exe /F /T /PID`.
5. **`evolution.applyCandidate`**:
   - Applies the selected candidate's code diff directly to the active workspace editor using VS Code's `WorkspaceEdit` API and activates the `InlineDiffManager`.

---

### 4.2 Live Metrics & Fitness Graph Data Schemas

The dashboard requires streaming metrics representing population diversity, fitness convergence, token usage, and model selection.

#### Real-Time Telemetry Event Schema (`evolution.event`)

```typescript
export interface EvolutionTelemetryEvent {
  runId: string;
  timestamp: number; // Unix epoch ms
  type: 
    | 'run:started'
    | 'step:started'
    | 'agent:thought'
    | 'agent:tool'
    | 'evaluation:completed'
    | 'step:accepted'
    | 'step:rejected'
    | 'supervisor:invoked'
    | 'migration:occurred'
    | 'run:completed';
  payload: StepTelemetryPayload | RunSummaryPayload | SupervisorPayload;
}

export interface StepTelemetryPayload {
  step: number;
  generation: number;
  islandId?: number;
  candidateId: string;
  parentId?: string;
  
  // Model & Execution Metadata
  model: string;
  selectionStrategy: string;
  durationMs: number;
  tokens: {
    inputTokens: number;
    outputTokens: number;
    totalTokens: number;
    estimatedCostUsd: number;
  };

  // Fitness & Verification
  score: {
    correct: boolean;
    primary: number; // Normalized 0.0 - 1.0 or benchmark scalar
    metrics: Record<string, number>; // e.g. { "latency_ms": 12.4, "throughput": 850.0, "memory_mb": 42.0 }
    error?: string;
    notes?: string;
  };
  
  // Evolution Trajectory State
  accepted: boolean;
  bestPrimarySoFar: number;
  improvementDelta: Record<string, number>;
  summary: string;
  
  // Diff Representation
  codeDiff?: {
    patch: string; // Unified diff format
    linesAdded: number;
    linesRemoved: number;
    complexityScore: number;
  };
}
```

---

### 4.3 Candidate Patch Diff Viewer Specification

The Candidate Diff Viewer provides side-by-side and unified inspections of generated mutations with one-click workspace application.

#### Data Structure:
```typescript
export interface CandidateDiffEntry {
  candidateId: string;
  step: number;
  version?: number;
  timestamp: number;
  primaryScore: number;
  isBest: boolean;
  isAccepted: boolean;
  summary: string;
  filePath: string;
  originalContent: string;
  evolvedContent: string;
  unifiedDiff: string;
  changesDescription: string;
}
```

#### Application Workflow:
1. User clicks **"Inspect Diff"** on a graph node or lineage table entry.
2. Webview sends message `postMessage({ type: 'previewDiff', candidateId })` to Extension Host.
3. Extension Host invokes `vscode.commands.executeCommand('vscode.diff', originalUri, candidateVirtualUri, 'Original ↔ Candidate v' + step)`.
4. User clicks **"Apply to File"**:
   - Extension Host creates `vscode.WorkspaceEdit`, updates document, saves file, and triggers the `InlineDiffManager` for user verification.

---

## 5. Requirement R3 Specification: Real-Time IPC & Event Streaming Architecture (60fps UI)

### 5.1 Architecture Overview & IPC Strategy

To maintain **60 frames per second (16.6ms per frame)** UI responsiveness without freezing the VS Code Extension Host or blocking editor typing:

```
┌────────────────────────────────────────────────────────────────────────┐
│                          BACKEND RUNNERS                               │
│   (cli.exe / OpenEvolve / AVO Python / MCP Server)                     │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ Raw stdout/stderr / JSON-RPC / SSE
                                   │ (High frequency: 100 - 500 Hz)
┌──────────────────────────────────▼─────────────────────────────────────┐
│                    EXTENSION HOST STREAM ADAPTER                       │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ 1. Asynchronous Ring Buffer (Queue cap: 5,000 events)            │  │
│  │ 2. Throttled Frame Dispatcher (16.6ms / 60Hz tick window)        │  │
│  │ 3. Batch Aggregator (Combines multiple token thoughts & points)  │  │
│  └──────────────────────────────────┬───────────────────────────────┘  │
└─────────────────────────────────────┼──────────────────────────────────┘
                                      │ Throttled Batch postMessage
                                      │ (Max 60 messages/sec)
┌─────────────────────────────────────▼──────────────────────────────────┐
│                      HUGOS DASHBOARD WEBVIEW                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Webview Main Thread (DOM / React / Canvas UI)                    │  │
│  │  - requestAnimationFrame render scheduling                       │  │
│  │  - Canvas / WebGL hardware-accelerated fitness graph             │  │
│  ├──────────────────────────────────────────────────────────────────┤  │
│  │ Webview Web Worker (Offloaded Processing)                        │  │
│  │  - Unified Diff Parsing & syntax highlighting                   │  │
│  │  - Multi-island population clustering & PCA projection          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 5.2 Stream Throttling & Batching Protocol

1. **Extension Host Batch Dispatcher (`StreamThrottleDispatcher`)**:
   - Collects incoming telemetry events from child processes or HTTP sockets into a lightweight memory queue.
   - A timer fires every **16 milliseconds** (or synchronizes to next frame). If new events exist in the queue, all queued events are packaged into a single batch message:
     ```json
     {
       "type": "telemetry_batch",
       "batchSeq": 1042,
       "events": [
         { "type": "agent:thought", "text": "Analyzing AST nodes..." },
         { "type": "agent:thought", "text": " Testing edge cases..." },
         { "type": "evaluation:completed", "step": 14, "score": { "primary": 0.884 } }
       ]
     }
     ```
2. **Webview Hardware-Accelerated Chart Rendering**:
   - Use HTML5 `<canvas>` with 2D Context / OffscreenCanvas or lightweight WebGL line plotting (e.g. Chart.js with decimation or custom canvas renderer).
   - Fixed capacity rolling array (e.g., 2,000 data points) to prevent garbage collection spikes.
3. **Web Worker Offloading**:
   - Expensive computations (such as generating diff line matrices, formatting 100-line code diffs, or calculating statistical moving averages) are performed inside a dedicated Webview Web Worker (`worker.js`).
   - Results are posted to the Webview UI thread only when ready.

---

## 6. Multi-Agent Teams & Thought Streams Architecture

### 6.1 Team Hierarchy & Roles
ModelFusion Multi-Agent Teams feature defined roles:
- **Lead Architect**: Responsible for high-level decomposition, task typing, strategy selection (`multi_objective`, `accuracy`, `latency`, `cost`), and final consensus synthesis.
- **Worker Subagents**: Specialized agents performing focused code generation, security scanning, refactoring, PE header extraction, or unit test generation.
- **AVO Agent**: Autonomous mutation operator executing iterative trials against benchmark harnesses.
- **Judge / Critic**: Comparative evaluator scoring candidate answers, detecting blind spots, identifying disagreements, and checking risk flags.

### 6.2 Real-Time Thought Stream Protocol
During multi-agent reasoning, thought streams emitted by local models (e.g., `<think>...</think>` in DeepSeek/Qwen or internal reasoning traces) are streamed into the Dashboard thought stream panel:

```typescript
export interface AgentThoughtStreamEvent {
  runId: string;
  agentId: string;
  agentRole: 'Lead Architect' | 'Worker Subagent' | 'AVO Agent' | 'Judge Critic';
  model: string;
  step: number;
  chunk: string;
  isComplete: boolean;
  timestamp: number;
}
```

---

## 7. Verification & Implementation Roadmap

1. **Rust Backend (`crates/cli/src/main.rs`)**:
   - Endpoints `/orchestrate`, `/v1/chat/completions`, `/stats`, `/tasks`, `/decision-stats`, `/pe-header-extraction`, `/report-bandit-feedback` verified functional on port 5000.
2. **OpenEvolve & AVO Runners**:
   - Python entry points `openevolve.api` and `avo.cli` verified with standard schemas and file-based lineage/trace persistence.
3. **MCP Stdio Protocol**:
   - 35+ tools registered and tested over JSON-RPC 2.0.
4. **IPC Streaming**:
   - Recommended batching frame rate: 60Hz (16.6ms window) with Canvas-based graphing and Web Worker diff offloading to ensure seamless UI interaction without extension host blocking.
