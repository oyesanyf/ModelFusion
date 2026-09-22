# HugOS IDE — Build & Feature Documentation

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Build Guide (Step-by-Step)](#build-guide-step-by-step)
  - [Upstream VS Code Rebase Pipeline (--patch-ide)](#upstream-vs-code-rebase-pipeline---patch-ide)
- [Chat Slash Commands & @agent Directives Reference](#chat-slash-commands--agent-directives-reference)
  - [Autocomplete & Interactive Discovery](#autocomplete--interactive-discovery)
  - [Category 1: Code Optimization & Evolution](#category-1-code-optimization--evolution)
  - [Category 2: Code Quality, Security & Auditing](#category-2-code-quality-security--auditing)
  - [Category 3: Multi-Model Consensus & Deliberation](#category-3-multi-model-consensus--deliberation)
  - [Category 4: Hardware Acceleration & Engine Control](#category-4-hardware-acceleration--engine-control)
  - [Category 5: Data Science, Notebooks & Binary Analysis](#category-5-data-science-notebooks--binary-analysis)
  - [Category 6: Live Web Research & Model Hub Sync](#category-6-live-web-research--model-hub-sync)
  - [Category 7: NLP & Analysis Directives](#category-7-nlp--analysis-directives)
  - [Category 8: System Introspection & Diagnostics](#category-8-system-introspection--diagnostics)
  - [@agent Directives Parity](#agent-directives-parity)
- [Inline Code Apply (Accept / Reject)](#inline-code-apply)
- [OpenEvolve Code Evolution](#openevolve-code-evolution)
- [Complete 83-Setting IDE Reference](#complete-83-setting-ide-reference)
  - [1. Fusion & Consensus Settings](#1-fusion--consensus-settings)
  - [2. Local Engines & Hardware Settings](#2-local-engines--hardware-settings)
  - [3. Cloud API Keys Settings](#3-cloud-api-keys-settings)
  - [4. Code Evolution Settings](#4-code-evolution-settings)
  - [5. SINQ Quantization Settings](#5-sinq-quantization-settings)
  - [6. Machine Learning & Intelligence Settings](#6-machine-learning--intelligence-settings)
  - [7. Advanced Reasoning & RAG Settings](#7-advanced-reasoning--rag-settings)
  - [8. Diagnostics & Watcher Settings](#8-diagnostics--watcher-settings)
  - [Chat & Model Routing Configurations](#chat--model-routing-configurations)
- [End-to-End Walkthrough Tutorials](#end-to-end-walkthrough-tutorials)
  - [Tutorial 1: Iterative Code Evolution with /evolve and Inline Diff](#tutorial-1-iterative-code-evolution-with-evolve-and-inline-diff)
  - [Tutorial 2: Multi-Model Consensus Deliberation with /fusion on Architecture](#tutorial-2-multi-model-consensus-deliberation-with-fusion-on-architecture)
  - [Tutorial 3: Automated Security Audit & Hardening with /security](#tutorial-3-automated-security-audit--hardening-with-security)
  - [Tutorial 4: Live Model Hub Updates & Local Auto-Provisioning with /update](#tutorial-4-live-model-hub-updates--local-auto-provisioning-with-update)
- [MSI Packaging](#msi-packaging)
- [Key Patches Applied to VS Code](#key-patches-applied-to-vs-code)

---

## Architecture Overview

HugOS IDE is a custom fork of VS Code (Code-OSS) with an integrated compound AI execution engine called **ModelFusion**. Built for native local-first execution, HugOS runs 100% offline out-of-the-box without requiring cloud subscriptions or mandatory external accounts, while offering optional hybrid routing when user API keys are provided.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          HugOS IDE (Electron)                          │
│  ┌───────────────────────┐          ┌───────────────────────────────┐  │
│  │  HugOS Chat Panel     │          │  Editor + Inline Diff         │  │
│  │  (Panel / Inline Chat)│          │  ✅ Accept (Ctrl+Shift+Y)     │  │
│  │  - Slash Commands     │          │  ❌ Reject (Ctrl+Shift+N)     │  │
│  │  - @agent Directives  │          │  Green / Red Gutter Markers   │  │
│  └───────────┬───────────┘          └───────────────▲───────────────┘  │
│              │                                      │                  │
│  ┌───────────▼──────────────────────────────────────┴───────────────┐  │
│  │  ModelFusion Extension (copilot/dist/extension.js)               │  │
│  │  - ModelFusionLMProvider (language model abstraction)            │  │
│  │  - InlineDiffManager (interactive decorations & keybindings)     │  │
│  │  - Slash & @agent Command Parser (extractKnownCmd / normCmd)     │  │
│  │  - Background Catalog Watcher (_runDatabaseUpdate)               │  │
│  └───────────┬──────────────────────────────────────────────────────┘  │
│              │ HTTP :5000 / JSON-RPC Stdio                             │
│  ┌───────────▼──────────────────────────────────────────────────────┐  │
│  │  cli.exe (Rust ModelFusion Master CLI & Server)                  │  │
│  │  - Dynamic Memory Sizer (evaluates live available RAM & VRAM)    │  │
│  │  - Multi-Model Fusion Orchestrator (multi_objective engine)      │  │
│  │  - Task Detection & Classification (45+ Hugging Face tasks)      │  │
│  │  - SQLite Catalog (hf_models.db, 2M+ registry & top workhorses)  │  │
│  └───────────┬───────────────────────────┬──────────────────────────┘  │
│              │                           │                             │
│  ┌───────────▼──────────┐   ┌────────────▼──────────┐   ┌───────────▼┐ │
│  │  Ollama Engine       │   │  OpenVINO / ONNX      │   │ Hybrid API │ │
│  │  (Default Local LLM) │   │  (CPU / iGPU / NPU)   │   │ (Optional) │ │
│  │  qwen2.5:7b / 14b    │   │  INT4/INT8 Quantized  │   │ OpenAI/Anth│ │
│  └──────────────────────┘   └───────────────────────┘   └────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **VS Code fork** | `IDE/vscode/` | Source-built Code-OSS fork with HugOS branding and vendor whitelist bypasses |
| **ModelFusion Extension** | `IDE/vscode/extensions/copilot/` | Chat integration, 71+ slash/@agent commands, inline diff, settings provider |
| **Rust Master CLI** | `crates/cli/` | API server (`--server`), model orchestration, catalog crawler (`--updatedb`), fast hub sync (`--update`) |
| **Database Catalog** | `IDE/db/hf_models.db` | High-speed SQLite repository catalog covering all 45 Hugging Face tasks |
| **Packaging Pipeline** | `IDE/build_msi.ps1` | Automated WiX Toolset installer compiler with Authenticode digital signing |

---

## Build Guide (Step-by-Step)

### Prerequisites

- **Node.js** v20+ (v24 recommended)
- **Python** 3.10+ (for build scripts and evaluation pipelines)
- **Rust** (stable toolchain with `cargo`)
- **Ollama** (for local LLM inference)
- **Windows SDK** (for `signtool.exe`)
- **WiX Toolset v4+** (for Windows Installer `.msi` compilation)
- **Git LFS** (Git Large File Storage for binary assets)

### Step 1: Clone the Repository

Make sure Git LFS is installed and initialized so all large binary assets (including `IDE/HugOS.msi`) are pulled down:

```bash
# Ensure Git LFS is initialized
git lfs install

# Clone repository
git clone https://github.com/oyesanyf/ModelFusion.git
cd ModelFusion

# Verify MSI installer or pull LFS files if needed
git lfs pull
```

### Step 2: Build the Rust CLI

```bash
cargo build --release --bin cli
# Output: target/release/cli.exe
```

This compiles `target/release/cli.exe` — the authoritative ModelFusion Master CLI that handles hardware detection, local LLM orchestration, and SQLite database ingestion.

### Step 3: Maintain 4-Way Binary Parity

Mirror the compiled binary across all distribution targets:

```powershell
Copy-Item target/release/cli.exe IDE/bin/cli.exe -Force
Copy-Item target/release/cli.exe IDE/VSCode-win32-x64/bin/cli.exe -Force
if (Test-Path "$env:LOCALAPPDATA\HugOS IDEin") {
    Copy-Item target/release/cli.exe "$env:LOCALAPPDATA\HugOS IDEin\cli.exe" -Force
}
```

### Step 4: Build the VS Code Fork & Upstream Rebase Automation

When working with an existing checkout of the VS Code fork (`IDE/vscode/`), compiling the distribution build is done using `yarn` and `gulp`:

```bash
cd IDE/vscode

# Install dependencies
yarn install

# Build the VS Code fork for Windows x64
npx gulp vscode-win32-x64
```

This produces `IDE/VSCode-win32-x64/` — the source-built IDE with HugOS branding from `product.json` (`applicationName: "hugos"`).

> [!IMPORTANT]
> The source build produces `HugOS.exe` natively. Never rename `Code.exe` to `HugOS.exe`.

---

### Upstream VS Code Rebase Pipeline (`--patch-ide`)

When upgrading or rebasing HugOS onto a newer upstream Microsoft VS Code release tag (e.g., rebasing onto `1.126.0`), ModelFusion provides the fully automated `--patch-ide` engine in the Master CLI (`crates/cli/src/main.rs`).

#### Architectural Purpose: Upstream Maintenance Tool, NOT Daily Packaging
- **Heavy Toolchain Requirement**: `--patch-ide` automates the entire clone, patch, dependency restoration, and source compilation sequence. It requires complete C++ and Node build chains (`yarn`, `gulp`, `node-gyp`, Visual Studio C++ Build Tools, Python) and takes ~10–15 minutes.
- **Daily Packaging Separation**: Day-to-day packaging does **not** invoke `--patch-ide`. Instead, developers run `powershell -ExecutionPolicy Bypass -File .\IDE\build_msi.ps1`, which operates directly on the pre-compiled `IDE/VSCode-win32-x64` tree to sync `cli.exe`, auto-increment build numbers, sign binaries with DigiCert timestamping, and generate `HugOS.msi`.
- **When to Use**: Run `--patch-ide` strictly when tracking or rebasing against a new upstream release tag from Microsoft.

#### The 10-Step Automated Workflow

The pipeline executes the following 10 steps sequentially:

1. **Clone VS Code Repository**: Clones `https://github.com/microsoft/vscode.git` into `--ide-src-dir` (default: `IDE/src`). Supports `--shallow` (`--depth 1`) and `--vscode-tag <tag>` (e.g. `1.126.0`). If the target directory already exists, cloning is skipped and patches are applied to the existing tree.
2. **Replace `product.json`**: Replaces `product.json` with HugOS branding from `IDE/patches/product.json`, setting `applicationName: "hugos"`, `nameShort: "HugOS"`, `nameLong: "HugOS IDE"`, and unlocking required API proposal whitelists.
3. **Patch `package.json`**: Modifies package manifest metadata (`name: "hugos"`, `displayName: "HugOS"`, `description: "HugOS - Custom AI-Powered Code-OSS IDE"`, `author: { "name": "HugOS Team" }`).
4. **Source Code Patches (Copilot -> ModelFusion)**: Systematically updates 8+ TypeScript files in `src/` to decouple proprietary Copilot endpoints and connect directly to ModelFusion:
   - `src/main.ts` (CLI argument comments)
   - `src/vs/platform/product/common/product.ts` (`defaultChatAgent` extension IDs)
   - `src/vs/platform/dataChannel/browser/forwardingTelemetryService.ts` (`isCopilotLikeExtension`)
   - `src/vs/workbench/contrib/chat/browser/aiCustomization/mcpListWidget.ts` (`COPILOT_EXTENSION_IDS`)
   - `src/vs/workbench/contrib/chat/browser/chatSetup/chatSetupProviders.ts` (timeout increased from 20s to 60s for local ModelFusion server)
   - `src/vs/workbench/contrib/editTelemetry/browser/telemetry/editSourceTrackingFeature.ts` & `editSourceTrackingImpl.ts`
   - `src/vs/workbench/contrib/terminal/browser/terminalMenus.ts`
   - `src/vs/workbench/contrib/preferences/browser/settingsLayout.ts`
   - `src/vs/workbench/contrib/mcp/common/mcpRegistry.ts` (injects ModelFusion collection filter)
   - `src/vs/workbench/contrib/chat/common/languageModels.ts` (auto-registers ModelFusion provider group on startup)
5. **Copy ModelFusion Extension**: Recursively copies `IDE/vscode/extensions/modelfusion` into `extensions/modelfusion/`.
6. **Copy HugOS Icon Artwork**: Copies official platform icons to `resources/win32/code.ico`, `code_150x150.png`, `code_70x70.png`, `resources/darwin/code.icns`, and `resources/linux/code.png`.
7. **Patch Dev Configuration**: Injects ModelFusion dist paths into `.vscode/launch.json` and updates `.vscode/tasks.json`.
8. **Build from Source (`gulp vscode-win32-x64`)**: Runs `yarn install --frozen-lockfile` and invokes `gulp vscode-win32-x64` to build the full distribution tree in `IDE/VSCode-win32-x64/`.
9. **Brand Electron Binary (`rcedit.exe`)**: Uses `rcedit-x64.exe` to update the PE resource headers of `HugOS.exe` (ProductName, FileDescription, CompanyName, icon, and version `1.126.0`).
10. **Runtime Integrity Check**: Validates the versioned Electron ICU runtime directory (e.g. `7e7950df89/`) to prevent ICU descriptor crashes (`IDE/INCIDENT_SIGNING_2026-07-16.md`) and verifies Authenticode signatures.

#### Command Syntax & Examples

```bash
# Standard shallow rebase onto upstream release tag 1.126.0
cli.exe --patch-ide --shallow --vscode-tag 1.126.0

# Clone and patch into a custom staging workspace
cli.exe --patch-ide --ide-src-dir "IDE/src_rebase" --shallow --vscode-tag 1.126.0
```

---

### Step 5: Build the ModelFusion Copilot Extension

```bash
cd IDE/vscode/extensions/copilot
npm run build
```

This compiles the TypeScript ModelFusion provider into `dist/extension.js`. Key source files:

| File | Purpose |
|------|---------|
| `byokContribution.ts` | Registers `ModelFusionLMProvider` with the chat framework |
| `modelFusionProvider.ts` | Core provider: slash command parsing, inline diff lifecycle, hardware orchestration |
| `evolve/inlineDiff.ts` | Cursor-style Accept/Reject diff decorations and keyboard handler |

### Step 6: Install & Verify Ollama

```bash
# Ensure Ollama is installed and running
ollama --version

# Pull default workhorse model (auto-provisioned by /update)
ollama pull qwen2.5:7b
```

### Step 7: Build & Digitally Sign the MSI Installer

```powershell
cd IDE
powershell -ExecutionPolicy Bypass -File build_msi.ps1
```

This packaging pipeline:
1. Verifies `VSCode-win32-x64/` exists.
2. Copies `target/release/cli.exe` into `IDE/bin/` and `VSCode-win32-x64/bin/`.
3. Auto-increments the build version in `IDE/build_number.txt` and `IDE/HugOS.wxs`.
4. Digitally signs all `.exe` and `.dll` files using `hugos-signing-cert.pfx` and timestamping via DigiCert.
5. Compiles the MSI with WiX Toolset v4+ (`dotnet tool run wix build`).
6. Digitally signs the final `IDE/HugOS.msi`.

---

## Chat Slash Commands & @agent Directives Reference

HugOS IDE features a unified, highly resilient command routing parser in `dist/extension.js`. Any command can be entered either as a traditional slash command (e.g. `/evolve`) or as an agent directive (e.g. `@agent evolve`).

### Autocomplete & Interactive Discovery

- **Slash Autocomplete (`/`)**: Typing `/` in the HugOS Chat input instantly displays an interactive dropdown listing available commands, descriptions, and argument hints.
- **Agent Autocomplete (`@agent `)**: Typing `@agent ` followed by the first letter of any command surfaces matching directives with full parity.
- **Resilient Matching**: The HugOS input parser automatically strips prompt wrappers, markdown envelopes, and natural language greetings. For example, typing `search the internet for ...` or `live web search for ...` automatically dispatches `/research` or `/search`.

---

### Category 1: Code Optimization & Evolution

Commands for multi-pass iterative code optimization, refactoring, performance hot-path profiling, and automated test generation.

| Command | Aliases | Arguments / Options | Description |
|:---|:---|:---|:---|
| `/evolve` | `/evolution`, `/avo`, `/evolv`, `/evovle`, `/evove`, `/evoce` | `-n <N>`, `--iterations <N>`, `--strategy <auto\|openevolve\|builtin>`, `--focus <area>` | Runs multi-pass iterative code evolution cycling through bug fixes, performance, error handling, clean refactoring, security hardening, and deep language optimizations. Auto-displays inline diff with Accept/Reject. |
| `/refactor` | — | `[instructions]` | Restructures code for modularity, clean architecture, SOLID adherence, and improved readability without modifying functional behavior. |
| `/optimize` | `/workflow-optimization` | `--focus <cpu\|memory\|io>`, `--level <1-5>` | Analyzes hot paths, memory allocations, cache locality, and algorithmic time complexity ($O(N)$ reductions). |
| `/fix` | — | `[diagnostic error message]` | Automatically diagnoses and resolves compiler errors, type mismatches, null-pointer exceptions, and runtime panics in active file. |
| `/review` | `/audit` | `--severity <low\|medium\|high\|critical>` | Performs deep code review identifying architectural anti-patterns, performance pitfalls, and maintenance liabilities. |
| `/tests` | — | `--framework <pytest\|jest\|cargo\|vitest>`, `--coverage` | Synthesizes comprehensive unit tests, edge-case assertions, regression suites, and integration mock fixtures. |
| `/explain` | — | `--level <beginner\|intermediate\|expert>` | Generates clear, step-by-step technical explanations of complex algorithms, concurrency flows, and data structures. |
| `/generate` | — | `<specification>` | Generates idiomatic boilerplate, API controllers, interface implementations, or service classes from text specifications. |

#### Real-World Chat Prompt Examples

```text
/evolve --iterations 5
Evolve the open file to eliminate quadratic allocations in the hot parsing loop and ensure zero-copy deserialization.
```

```text
/refactor
Refactor this monolithic transaction processing function into an event-driven handler using the Strategy pattern with dependency injection.
```

```text
/optimize --focus memory
Analyze this Rust vector buffer and convert allocations to smallvec or pooled buffers to prevent GC/allocator thrashing.
```

```text
/tests --framework pytest --coverage
Generate comprehensive unit tests for this JWT authentication middleware, including expired tokens, malformed signatures, and clock skew edge cases.
```

---

### Category 2: Code Quality, Security & Auditing

Static analysis, CVE vulnerability scanning, MITRE ATT&CK threat modeling, compliance checks, and automated docstring generation.

| Command | Aliases | Arguments / Options | Description |
|:---|:---|:---|:---|
| `/security` | `/code-vulnerability-detection`, `/codevulnerabilitydetection` | `--framework <cve\|owasp\|mitre>`, `--deep` | Runs ATLAS security audit and static taint analysis, scanning for OWASP Top 10 vulnerabilities, CWE violations, injection vectors, and hardcoded secrets. |
| `/comment` | `/comments`, `/doc`, `/docs` | `--style <jsdoc\|rustdoc\|google\|doxygen>` | Generates high-quality, comprehensive docstrings, parameter specifications, error/exception annotations, and inline code comments. |
| `/pii-detection` | — | `--sanitize`, `--strict` | Scans files and prompts for Personally Identifiable Information (PII), email addresses, IP addresses, private keys, and API tokens. |
| `/malware-text-detection` | — | `--deep-scan` | Analyzes scripts, shell commands, and macro files for suspicious system calls, obfuscated payloads, and malicious signatures. |
| `/phishing-detection` | — | — | Analyzes email templates, outbound notifications, and web links for deceptive patterns, domain spoofing, and social engineering cues. |
| `/code-clone-detection` | — | `--threshold <0.1-1.0>` | Detects exact and semantic duplicate code fragments across the workspace to eliminate redundant maintenance overhead. |
| `/code-summary-generation` | — | `--format <markdown\|json>` | Produces structured architectural summaries detailing file responsibilities, exported symbols, and dependency graphs. |
| `/anonymization` | — | `--mask <redact\|hash>` | Sanitizes codebases, log dumps, and test fixtures by redacting proprietary secrets, hostnames, and credentials. |

#### Real-World Chat Prompt Examples

```text
/security --deep
Audit this Express router endpoint for SQL injection, prototype pollution, missing rate limits, and timing attack vulnerabilities.
```

```text
/comment --style rustdoc
Add comprehensive documentation to all public structs, traits, and methods in this module, including # Errors, # Panics, and # Examples sections.
```

```text
/pii-detection --sanitize
Scan this customer onboarding payload fixture for HIPAA/GDPR violations and replace sensitive identifiers with deterministic synthetic mocks.
```

---

### Category 3: Multi-Model Consensus & Deliberation

Compound multi-model inference pipelines where multiple local models run concurrently or sequentially, cross-evaluating results for superior accuracy.

| Command | Aliases | Arguments / Options | Description |
|:---|:---|:---|:---|
| `/fusion` | — | `on` / `off` | Toggles ModelFusion multi-model deliberation panel. Evaluates candidate models, performs consensus voting, and synthesizes the optimal combined answer. |
| `/fusion-models` | — | `<N>` (e.g. `0`, `3`, `5`) | Configures the number of models in the fusion panel. Setting `0` activates Auto mode (dynamic scaling based on live available RAM/VRAM). |
| `/fusion-mode` | — | `multi-model` \| `multi-sample` | Sets deliberation mode: `multi-model` (queries N distinct models) or `multi-sample` (queries top model across N temperature seeds). |
| `/selection-strategy` | — | `multi_objective` \| `weighted_voting` \| `cost_efficient` \| `fastest` | Selects algorithm used by the Master CLI to rank and pick candidate models from SQLite. |
| `/judge` | — | `on` / `off` | Activates LLM-as-a-Judge cross-evaluation. A supervisor model critiques and grades candidate outputs on correctness, reasoning, and adherence. |
| `/score` | — | `on` / `off` | Calculates and displays multidimensional confidence, clarity, and precision scores for generated responses. |
| `/plan` | — | `[goal]` | Directs the model to emit a structured, multi-step execution plan prior to executing code modifications or refactors. |
| `/cot` | — | `on` / `off` | Enables Chain-of-Thought scratchpad reasoning, forcing the model to articulate internal deductions before outputting answers. |
| `/full` | — | — | Enables full-depth compound deliberation: simultaneously activates planning, chain-of-thought, fusion deliberation, and judge scoring. |

#### Real-World Chat Prompt Examples

```text
/fusion
Compare implementing a distributed task worker with Redis Streams vs RabbitMQ vs Apache Kafka for an order-processing pipeline handling 50k ops/sec.
```

```text
/fusion-models 0
@agent fusion Compare SQLite WAL mode with PostgreSQL for local client caching in an Electron desktop application.
```

```text
/plan
Create a migration plan to upgrade this Next.js 13 project to Next.js 15 App Router with React Server Components, addressing breaking changes.
```

```text
/judge
/cot
Solve this concurrent synchronization deadlock between our database connection pool and worker background threads.
```

---

### Category 4: Hardware Acceleration & Engine Control

Low-level hardware target steering, model size budget allocation, backend engine switching, and quantization controls.

| Command | Aliases | Arguments / Options | Description |
|:---|:---|:---|:---|
| `/gpu` | — | — | Forces model execution to target discrete GPU hardware (NVIDIA CUDA / Intel Arc / AMD ROCm). Skips CPU fallback. |
| `/cpu` | — | — | Forces CPU-only execution utilizing vectorized instruction sets (AVX-512, AMX, AVX2). |
| `/ollama` | — | — | Selects the local Ollama daemon (`http://127.0.0.1:11434`) as the active inference engine. |
| `/openvino` | — | — | Selects Intel OpenVINO runtime for optimized CPU/iGPU INT4/INT8 inference. |
| `/onnx` | — | — | Selects ONNX Runtime execution provider for cross-platform model graph evaluation. |
| `/vllm` | — | — | Routes inference to vLLM high-throughput engine (Linux environments). |
| `/model` | — | `<name>` (e.g. `qwen2.5:14b`) | Explicitly overrides the active model, bypassing automatic heuristic selection. |
| `/budget` | — | `<N>` (e.g. `1.5`, `7`, `14`, `32`) | Sets the parameter budget cap in billions of parameters ($P \le N	ext{B}$) based on hardware capacity. |
| `/sinq` | — | `on` / `off` | Enables Structured Innovation Network Quantization for ultra-low memory model footprint. |
| `/sinq-nbits` | — | `4` \| `8` | Configures SINQ quantization target bit-width (4-bit INT4 or 8-bit INT8). |
| `/sinq-group-size`| — | `64` \| `128` | Sets quantization weight block group size for scale calculations. |
| `/sinq-tiling-mode`| — | `auto` \| `1D` \| `2D` | Configures memory matrix tiling layout for quantization acceleration. |
| `/weight-format` | — | `int4` \| `int8` \| `fp16` | Sets OpenVINO model weight compression format for model conversion. |
| `/ov-model-dir` | — | `<path>` | Sets local cache directory for storing downloaded or converted OpenVINO IR models. |
| `/port` | — | `<port>` (default: `5000`) | Sets the local HTTP API port used by the Master CLI server (`cli.exe --server`). |

#### Real-World Chat Prompt Examples

```text
/ollama
/model qwen2.5:14b
Write a high-throughput async WebSocket server in Rust using tokio and tokio-tungstenite.
```

```text
/openvino
/gpu
Run inference on our local Intel Arc GPU using the OpenVINO INT4 quantized model cache.
```

```text
/budget 7
Select and run the best local model that fits strictly within a 7-billion parameter memory budget.
```

---

### Category 5: Data Science, Notebooks & Binary Analysis

Workflows for data analysts, CSV/Parquet manipulation, Jupyter interactive computing, and native Windows PE binary inspection.

| Command | Aliases | Arguments / Options | Description |
|:---|:---|:---|:---|
| `/jupyter` | — | `[file.ipynb]` | Activates interactive Jupyter Notebook mode, enabling code cell execution, dataframe inspection, and plot generation. |
| `/dataanalyst` | — | `[dataset.csv]` | Activates Data Analyst mode: parses CSV/Excel data, computes descriptive statistics, and detects missing values or anomalies. |
| `/datascience` | `/data-science` | `[dataset.csv]` | Initiates automated data science pipeline: feature engineering, train-test splitting, and baseline model training. |
| `/table-question-answering` | — | `<query>` | Performs natural language question answering directly over tabular datasets (CSV, Parquet, SQLite). |
| `/feature-ranking` | — | `--target <column>` | Computes feature importance rankings, correlation coefficients, and mutual information scores for predictive features. |
| `/pe-header-extraction` | `/peheaderextraction` | `[file.exe]` | Parses Windows Portable Executable (PE) binaries: inspects DOS/NT headers, Section headers, Import Address Tables (IAT), and entropy. |

#### Real-World Chat Prompt Examples

```text
/dataanalyst
Analyze this customer_churn.csv file: calculate monthly churn rate, identify correlations with customer support ticket counts, and recommend features.
```

```text
/jupyter
Create a Jupyter notebook implementing a time-series forecasting model using Prophet and XGBoost on this hourly_traffic.csv dataset.
```

```text
/pe-header-extraction target/release/cli.exe
Extract PE header sections, compute entropy across all .text and .rdata sections, and list all imported Windows API DLLs.
```

---

### Category 6: Live Web Research & Model Hub Sync

Real-time internet web search, documentation scraping, model hub synchronization, and Retrieval-Augmented Generation (RAG).

| Command | Aliases | Arguments / Options | Description |
|:---|:---|:---|:---|
| `/research` | `/reseach` | `<topic or query>` | Conducts live web research: fetches documentation, extracts key technical facts, summarizes architectural recommendations, and provides source URLs. |
| `/search` | — | `<query>` | Fast search query executing real-time web retrieval for current library versions, breaking API changes, or syntax lookups. |
| `/update` | — | `--db-path <path>` | **Fast Curated Engine**: Syncs the top ~6,500 production workhorse models across all 45 tasks and dynamically auto-provisions the matching local Ollama model. |
| `/updatedb` | `/update-db` | `--max-models <N>`, `--db-path <path>` | **Full Registry Crawler**: Continuously crawls all 2M+ models on Hugging Face Hub via cursor pagination (`limit=1000`, 1,000 models/sec) into SQLite. |
| `/enable-hyde` | `/use-hyde` | — | Activates Hypothetical Document Embeddings (HyDE) to expand query recall in dense vector search. |
| `/hyde-variants` | — | `<N>` (default: `3`) | Generates multiple synthetic document variations to broaden vector search context retrieval. |
| `/search-query` | — | `<query>` | Executes dense semantic vector search over indexed local workspace files. |
| `/add-documents` | — | `<path>` | Indexes specified files or folders into the local vector database for RAG querying. |
| `/demo-hyde` | — | — | Runs a diagnostic RAG walkthrough demonstrating HyDE query expansion and document retrieval. |

#### Real-World Chat Prompt Examples

```text
/research
Search the web for the latest breaking changes and migration guide between Pydantic v1 and Pydantic v2.
```

```text
/search
What is the exact function signature and required features for tokio::net::TcpListener in tokio 1.40+?
```

```text
/update
Refresh our local ModelFusion database with the latest curated Hugging Face models and verify local Ollama model provisioning.
```

```text
/updatedb --max-models 50000
Run the full registry crawler to index the next 50,000 Hugging Face models into IDE/db/hf_models.db.
```

---

### Category 7: NLP & Analysis Directives

Specialized directives covering all natural language processing tasks, multimodal analysis, and evaluation benchmarks across the 45 Hugging Face task domains.

| Command | Aliases | Arguments / Options | Description |
|:---|:---|:---|:---|
| `/sentiment` | — | `[text]` | Evaluates text sentiment: returns positive/neutral/negative classification with fine-grained emotional breakdown. |
| `/financial-sentiment-analysis` | — | `[earnings text]` | Classifies financial texts and earnings call transcripts into bullish, bearish, or neutral market signals. |
| `/ner` | — | `[text]` | Extracts Named Entities: persons, organizations, geographical locations, dates, and monetary values. |
| `/financial-ner` | — | `[financial news]` | Specialized entity extraction for stock tickers, equity classes, currency symbols, and corporate mergers. |
| `/legal-ner` | — | `[brief or filing]` | Extracts legal citations, constitutional amendments, judicial precedents, and statutory sections. |
| `/biomedical-ner` | — | `[clinical notes]` | Extracts biomedical entities: medications, dosages, clinical diagnoses, anatomical sites, and gene symbols. |
| `/chemical-reaction-ner` | — | `[paper excerpt]` | Extracts chemical compounds, reagents, catalysts, temperatures, and yields from chemistry literature. |
| `/summary` | `/summarization` | `--length <short\|medium\|long>` | Condenses long-form technical documents, RFCs, or code files into concise structured bullet points. |
| `/scientific-abstract-summarization` | — | `[abstract]` | Summarizes academic papers into Core Problem, Methodology, Key Findings, and Benchmark Results. |
| `/question` | `/question-answering` | `<question>` | Performs context-grounded extractive question answering against open documents or context buffers. |
| `/semantic-analysis` | — | `[text or code]` | Computes semantic similarity matrices, clustering related concepts and verifying thematic consistency. |
| `/zero-shot-classification` | — | `--labels <list>` | Classifies input text into arbitrary user-provided candidate labels without task-specific training. |
| `/translation` | — | `--target <lang>` | Translates text or code comments across 100+ natural languages while preserving technical terminology. |
| `/grammar-correction` | — | `[text]` | Corrects grammatical errors, punctuation, awkward phrasing, and stylistic inconsistencies in technical writing. |
| `/paraphrase-generation` | — | `[text]` | Rewrites sentences and paragraphs with varying tone and vocabulary while strictly maintaining semantic meaning. |
| `/hallucination-detection`| — | `[claim + source]` | Audits generated text against reference source context to verify factual grounding and flag hallucinations. |
| `/generation-groundedness`| — | — | Computes groundedness score measuring what percentage of claims are directly supported by workspace files. |
| `/reading-level-assessment`| — | — | Evaluates text readability scores (Flesch-Kincaid Grade Level, Gunning Fog Index, SMOG index). |
| `/legal-judgment-classification` | — | `[filing]` | Classifies legal holdings and court decisions into affirmed, reversed, remanded, or dismissed categories. |
| `/contract-clause-classification` | — | `[contract]` | Audits legal agreements, extracting indemnity clauses, limitation of liability, non-compete, and confidentiality terms. |
| `/case-outcome-prediction` | — | `[facts of case]` | Analyzes precedent patterns to predict litigation risk and probable settlement outcome distributions. |
| `/automatic-speech-recognition` | — | `[audio_file]` | Transcribes audio recordings (WAV, MP3, M4A) using Whisper speech recognition pipelines. |
| `/text-to-speech` | — | `[text]` | Synthesizes natural-sounding speech audio from input text. |
| `/image-classification` | — | `[image]` | Classifies input images, identifying objects, scenes, and visual elements. |
| `/visual-question-answering` | — | `[image] <question>` | Answers natural language questions regarding uploaded architectural diagrams, UI mockups, or photos. |
| `/document-question-answering` | — | `[pdf_image] <query>` | Extracts structured information and answers queries from scanned invoices, receipts, and PDF charts. |
| `/depth-estimation` | — | `[image]` | Generates monocular depth map representations from 2D images. |

#### Real-World Chat Prompt Examples

```text
/contract-clause-classification
Analyze this master_services_agreement.pdf: extract all limitation of liability clauses, IP assignment terms, and governing law clauses.
```

```text
/financial-sentiment-analysis
Evaluate this quarterly earnings release excerpt and classify sentiment regarding guidance and cloud revenue growth.
```

```text
/hallucination-detection
Check whether the claims made in this generated summary are 100% grounded in the referenced system design RFC.
```

---

### Category 8: System Introspection & Diagnostics

Live telemetry, hardware discovery metrics, task registry inspection, cache maintenance, and PDF reporting.

| Command | Aliases | Arguments / Options | Description |
|:---|:---|:---|:---|
| `/sysinfo` | `/sys-info` | — | Displays real-time hardware discovery telemetry: CPU cores, available physical RAM, GPU VRAM, and dynamic budget sizing. |
| `/stats` | `/statsd` | — | Displays database and runtime statistics: total cached models, indexed tasks, and token generation speed. |
| `/decision-stats` | `/decisionstats` | — | Dumps model selection router logs detailing why specific models were selected for recent queries. |
| `/performance-stats` | `/performancestats` | — | Displays end-to-end latency percentiles (p50, p95, p99), token throughput, and execution duration. |
| `/cache-stats` | `/cachestats` | — | Displays disk usage breakdown for cached models, OpenVINO IR files, and embeddings. |
| `/novel-ai-stats` | `/novelaistats` | — | Summarizes statistics for novel architectures, compound pipelines, and active quantization formats. |
| `/commands` | `/command`, `/help` | — | Renders the complete interactive list of supported chat slash commands and @agent directives. |
| `/tasks` | — | `[audio\|image\|text]` | Lists all 45+ Hugging Face task domains supported by the ModelFusion task classifier. |
| `/active-model` | `/active-models`, `/current-model`, `/current-models`, `/ide-model`, `/models-in-use` | — | Reports the currently active model, execution backend (Ollama/OpenVINO), device, and temperature settings. |
| `/version` | `/v` | — | Displays current version strings for HugOS IDE, ModelFusion Master CLI, and active engine runtimes. |
| `/keys` | `/api-keys` | — | Inspects configured cloud API keys, reporting `[LOADED]` or `[DISABLED]` status for OpenAI, Anthropic, Gemini, and Hugging Face. |
| `/clearcache` | — | — | Flushes temporary inference caches, compiled model graphs, and scratch token embeddings to reclaim disk space. |
| `/export-pdf` | `/exportpdf` | `[output_filename]` | Compiles the active conversation, telemetry charts, and code diffs into a publication-ready PDF document. |
| `/verbose` | — | `on` / `off` | Toggles detailed execution logging in the ModelFusion server output channel. |
| `/debug` | — | `on` / `off` | Toggles low-level diagnostic dumps, raw JSON payloads, and stacktraces for bug reporting. |

#### Real-World Chat Prompt Examples

```text
/sysinfo
```

```text
/active-model
```

```text
/stats
```

```text
/keys
```

```text
/export-pdf system_architecture_review.pdf
```

---

### @agent Directives Parity

HugOS IDE implements complete 1:1 functional parity between slash commands (`/<command>`) and agent directives (`@agent <command>`). The core parser normalizes both forms identically:

```
┌─────────────────────────────────┐
│ User Input in HugOS Chat Panel  │
├─────────────────────────────────┤
│  /update                        │ ──┐
│  @agent update                  │ ──┼──► [extractKnownCmd] ──► /update
│  @modelfusion update            │ ──┘
└─────────────────────────────────┘
```

Any command and argument combination works interchangeably:

| Slash Command Invocation | Equivalent @agent Directive Invocation | Action Performed |
|:---|:---|:---|
| `/evolve -n 5` | `@agent evolve -n 5` | Runs 5 evolution passes with inline diff |
| `/update` | `@agent update` | Runs Fast Curated Engine sync and model provisioning |
| `/fusion` | `@agent fusion` | Activates multi-model consensus deliberation |
| `/sysinfo` | `@agent sysinfo` | Displays live CPU, RAM, and GPU hardware metrics |
| `/security` | `@agent security` | Performs static vulnerability audit on active code |
| `/budget 14` | `@agent budget 14` | Caps model selection budget at 14B parameters |
| `/model qwen2.5:14b` | `@agent model qwen2.5:14b` | Explicitly pins active local model |
| `/research Next.js 15` | `@agent research Next.js 15` | Runs live internet web research |
| `/export-pdf report.pdf` | `@agent export-pdf report.pdf` | Compiles chat report to PDF document |

---

## Inline Code Apply

**Every code response** emitted by HugOS Chat automatically triggers an interactive inline diff with Accept / Reject controls directly within your active editor.

```
┌──────────────────────────────────────────────────────────────────┐
│ Active Editor (Rust / TypeScript / Python)                       │
├──────────────────────────────────────────────────────────────────┤
│  Banner:  ✅ Accept (Ctrl+Shift+Y)  ·  ❌ Reject (Ctrl+Shift+N)   │
├──────────────────────────────────────────────────────────────────┤
│   1   fn calculate_hash(data: &[u8]) -> u64 {                    │
│   2 🔴-   let mut hasher = std::collections::hash_map::DefaultH.. │
│   2 🟢+   let mut hasher = ahash::AHasher::default();             │
│   3       hasher.write(data);                                    │
│   4       hasher.finish()                                        │
│   5   }                                                          │
└──────────────────────────────────────────────────────────────────┘
```

### Visual Indicators

- 🟢 **Green Gutter & Highlight**: Newly inserted or modified code lines.
- 🔴 **Red Gutter & Strikethrough**: Removed or replaced code lines.
- 🔵 **Blue Boundary Overview**: Identifies the perimeter of modified code blocks.
- **Top Notification Banner**: "✅ Accept (Ctrl+Shift+Y) · ❌ Reject (Ctrl+Shift+N)".
- **Status Bar Indicator**: Quick clickable buttons to finalize or revert edits.

### Keyboard Shortcuts

| Shortcut | Action | Description |
|:---|:---|:---|
| `Ctrl+Shift+Y` | **Accept Changes** | Merges the candidate changes into your active buffer and saves the file to disk. |
| `Ctrl+Shift+N` | **Reject Changes** | Reverts the active editor buffer to its original pre-prompt state, discarding the candidate. |

---

## OpenEvolve Code Evolution

`/evolve` (or `@agent evolve`) invokes the OpenEvolve compound optimization engine, performing sequential evolutionary refinement passes over your active code.

```
┌─────────────────┐     ┌────────────────────────────────────────────────────────┐
│  Your Code File │────►│  OpenEvolve Iterative Refinement Pipeline              │
│ (Active Editor) │     │  Iter 1: 🐛 Fix Bugs & Logical Errors                  │
└─────────────────┘     │  Iter 2: ⚡ Optimize Performance & Allocations         │
                        │  Iter 3: 🛡️ Add Error Handling & Boundary Checks      │
                        │  Iter 4: 🏗️ Refactor for Clean Architecture            │
                        │  Iter 5: 🔒 Security Hardening & Taint Sanitization    │
                        └──────────────────────────┬─────────────────────────────┘
                                                   │
                                        ┌──────────▼──────────┐
                                        │  Final Evolved Code │
                                        │  + Inline Diff UI   │
                                        │  Accept / Reject    │
                                        └─────────────────────┘
```

### Execution Modes

1. **Python Pipeline (`.py` files)**: When `openevolve` is available, HugOS generates a targeted test harness (`evaluator.py`) and executes evolutionary genetic search against test metrics.
2. **Built-in Iterative Engine (All Languages)**: Operates natively across Rust, TypeScript, C++, Go, Python, Java, and C#, cycling through 8 specialized focus areas:
   - Pass 1: 🐛 **Bug fixes** — Type errors, null pointers, off-by-one errors, logic flaws.
   - Pass 2: ⚡ **Performance** — Algorithmic time complexity, vectorization, zero-copy memory.
   - Pass 3: 🛡️ **Error handling** — Result/Option propagation, input validation, invariant assertions.
   - Pass 4: 🏗️ **Refactoring** — Decoupling, DRY principles, SOLID design, idiomatic patterns.
   - Pass 5: 🔒 **Security hardening** — Memory safety, injection defense, timing attacks.
   - Pass 6: 📝 **Documentation** — Clean docstrings, architectural rationale, usage examples.
   - Pass 7: ✨ **Dead code removal** — Unused imports, orphaned branches, clean formatting.
   - Pass 8: 🚀 **Deep optimization** — Compiler intrinsics, cache alignment, concurrency pruning.

---

## Complete 83-Setting IDE Reference

HugOS IDE provides 83 granular settings accessible via **Settings** (`Ctrl+,` → search `hugos.modelfusion` or browse **HugOS ModelFusion**).

### 1. Fusion & Consensus Settings

| Setting ID | GUI Label | Type | Production Default | Description |
|:---|:---|:---:|:---:|:---|
| `hugos.modelfusion.fusion` | **Enable Fusion** | `boolean` | **`true`** | Enables multi-model consensus deliberation panel. Queries a panel of diverse models and synthesizes their collective findings into a unified, high-accuracy response. |
| `hugos.modelfusion.fusionModels` | **Fusion Models Count** | `integer` | **`0`** | Number of candidate models executed in the fusion panel. **`0` = Auto Dynamic Sizing**: automatically scales panel size based on runtime available RAM and VRAM. |
| `hugos.modelfusion.fusionMode` | **Fusion Execution Mode** | `string` | `"multi-model"` | Execution mode: `multi-model` (queries N distinct models from catalog) or `multi-sample` (queries the top model across N temperature variations). |
| `hugos.modelfusion.selectionStrategy` | **Model Selection Strategy** | `string` | `"multi_objective"` | Model ranking algorithm: `multi_objective` (balances speed, memory, and task accuracy), `weighted_voting`, `cost_efficient`, or `fastest`. |
| `hugos.modelfusion.scoreEnabled` | **Score Output Quality** | `boolean` | `false` | Computes multidimensional accuracy, relevance, and formatting quality scores for generated candidate answers. |
| `hugos.modelfusion.judgeEnabled` | **LLM-as-a-Judge** | `boolean` | `false` | Deploys an independent evaluator model to cross-examine and critique candidate responses before delivering the final answer. |

### 2. Local Engines & Hardware Settings

| Setting ID | GUI Label | Type | Production Default | Description |
|:---|:---|:---:|:---:|:---|
| `hugos.modelfusion.localBackend` | **Local Execution Backend** | `string` | **`"ollama"`** | Primary local inference backend runtime: `"ollama"`, `"openvino"`, or `"transformers"`. |
| `hugos.modelfusion.device` | **Hardware Device Target** | `string` | `"auto"` | Hardware compute device: `"auto"` (hardware auto-detect), `"gpu"` (force CUDA/Arc), or `"cpu"` (force CPU). |
| `hugos.modelfusion.budget` | **Parameter Budget (Billions)** | `number` | `1` | Max model parameter size in billions ($P \le N	ext{B}$). Dynamically auto-configured on launch based on available free memory. |
| `hugos.modelfusion.ollamaModel` | **Ollama Model Override** | `string` | `""` | Specific Ollama model tag override (e.g. `qwen2.5:7b`, `qwen2.5:14b`). Leave blank for dynamic auto-provisioning. |
| `hugos.modelfusion.ollamaModels` | **Managed Ollama Models** | `array` | `[]` | User-configured list of installed Ollama models with custom display names and runtime parameters. |
| `hugos.modelfusion.openvinoModel` | **OpenVINO Model Override** | `string` | `""` | Specific OpenVINO IR model identifier (e.g. `OpenVINO--Qwen2.5-1.5B-Instruct-int4-ov`). Leave blank for auto-selection. |
| `hugos.modelfusion.openvinoModels` | **Managed OpenVINO Models**| `array` | `[]` | User-managed list of local OpenVINO IR model directories and execution profiles. |
| `hugos.modelfusion.ovModelDir` | **OpenVINO Model Directory** | `string` | `""` | Filesystem directory for storing converted OpenVINO IR models (defaults to `IDE/ov_models`). |
| `hugos.modelfusion.getvino` | **Background OpenVINO Sync** | `boolean` | `false` | Enables 24-hour background cycle downloading pre-converted INT4 OpenVINO models from Hugging Face Hub. |
| `hugos.modelfusion.inferenceModel` | **Transformers Model Override**| `string` | `""` | Hugging Face model repository ID for remote or local transformers inference (e.g. `Qwen/Qwen2.5-7B-Instruct`). |
| `hugos.modelfusion.transformerModels` | **Managed Transformer Models**| `array` | `[]` | User-managed list of Hugging Face transformer models for local or cloud inference. |
| `hugos.modelfusion.port` | **API Server Port** | `number` | `5000` | Local HTTP REST port used for IPC communication between the IDE extension and `cli.exe --server`. |
| `hugos.modelfusion.reportPath` | **Telemetry Report Path** | `string` | `""` | Destination filesystem path for exporting telemetry logs and evaluation benchmark records. |
| `hugos.modelfusion.reportType` | **Telemetry Report Format** | `string` | `"json"` | File format for generated telemetry reports: `"json"`, `"csv"`, or `"pdf"`. |

### 3. Cloud API Keys Settings

| Setting ID | GUI Label | Type | Production Default | Description |
|:---|:---|:---:|:---:|:---|
| `hugos.modelfusion.openaiApiKey` | **OpenAI API Key** | `string` | `""` | API key for OpenAI GPT-4o models. Status: `[DISABLED]` when empty (100% private local execution), `[LOADED]` when set. |
| `hugos.modelfusion.anthropicApiKey` | **Anthropic API Key** | `string` | `""` | API key for Anthropic Claude 3.5 Sonnet. Status: `[DISABLED]` when empty, `[LOADED]` when set for hybrid routing. |
| `hugos.modelfusion.geminiApiKey` | **Google Gemini API Key** | `string` | `""` | API key for Google Gemini 1.5/2.0 Flash and Pro. Status: `[DISABLED]` when empty, `[LOADED]` when set. |
| `hugos.modelfusion.huggingfaceApiKey` | **Hugging Face Token** | `string` | `""` | Hugging Face User Access Token (`HF_TOKEN`) used to download gated models (e.g. LLaMA-3) and access Serverless APIs. |

### 4. Code Evolution Settings

| Setting ID | GUI Label | Type | Production Default | Description |
|:---|:---|:---:|:---:|:---|
| `hugos.modelfusion.openevolve.enabled` | **Enable OpenEvolve** | `boolean` | **`true`** | Enables the `/evolve` command and background code improvement agents in HugOS Chat. |
| `hugos.modelfusion.openevolve.iterations`| **Evolution Iterations** | `integer` | `5` | Default number of evolution cycles per `/evolve` run. Each pass focuses on a distinct optimization dimension. |
| `hugos.modelfusion.openevolve.strategy` | **Evolution Strategy** | `string` | `"auto"` | Engine selection: `"auto"` (selects Python OpenEvolve for `.py`, built-in for others), `"openevolve"`, or `"builtin"`. |
| `hugos.modelfusion.openevolve.autoApply`| **Auto-Apply Inline Diff** | `boolean` | **`true`** | Automatically opens the inline diff editor with Accept (`Ctrl+Shift+Y`) / Reject (`Ctrl+Shift+N`) upon completion. |
| `hugos.modelfusion.openevolve.showProgress`| **Show Evolution Progress**| `boolean` | **`true`** | Displays per-iteration status updates, diff metrics, and focus transitions in the chat stream. |
| `hugos.modelfusion.openevolve.focuses` | **Custom Focus Areas** | `array` | `[8 focuses]` | Ordered array of evolution goals (Bugs, Performance, Error handling, Clean code, Security, Docs, Polish, Optimization). |

### 5. SINQ Quantization Settings

| Setting ID | GUI Label | Type | Production Default | Description |
|:---|:---|:---:|:---:|:---|
| `hugos.modelfusion.sinq` | **Enable SINQ** | `boolean` | `false` | Enables Structured Innovation Network Quantization for aggressive weight compression during model loading. |
| `hugos.modelfusion.sinqNbits` | **SINQ Bit-Width** | `number` | `4` | Target quantization precision: `4` (INT4 - 75% memory reduction) or `8` (INT8 - 50% memory reduction). |
| `hugos.modelfusion.sinqGroupSize` | **SINQ Group Size** | `number` | `128` | Quantization block size (number of weight parameters sharing a single scale and zero-point offset). |
| `hugos.modelfusion.sinqTilingMode` | **SINQ Tiling Layout** | `string` | `"auto"` | Memory matrix tiling layout: `"auto"`, `"1D"`, or `"2D"` block tiling. |
| `hugos.modelfusion.sinqMethod` | **SINQ Algorithm** | `string` | `"default"` | Quantization methodology: `"default"`, `"sinq"`, `"rtn"` (Round-to-Nearest), or `"awq"` (Activation-aware). |
| `hugos.modelfusion.weightFormat` | **Target Weight Format** | `string` | `"default"` | Weight representation format: `"default"`, `"int4"`, `"int8"`, or `"fp16"`. |

### 6. Machine Learning & Intelligence Settings

| Setting ID | GUI Label | Type | Production Default | Description |
|:---|:---|:---:|:---:|:---|
| `hugos.modelfusion.enableML` | **Enable ML Model Router** | `boolean` | `false` | Activates adaptive machine learning model routing instead of static rule heuristics. |
| `hugos.modelfusion.mlLearning` | **Online Reinforcement Learning**| `boolean` | `false` | Continuously updates model recommendation weights based on user acceptance and execution success. |
| `hugos.modelfusion.mlFallback` | **Heuristic Fallback** | `boolean` | `false` | Falls back to rule-based heuristics if ML routing model confidence falls below the acceptance threshold. |
| `hugos.modelfusion.mlConfidenceThreshold`| **ML Confidence Threshold**| `number` | `0.5` | Minimum classification confidence required to accept an ML routing recommendation. |
| `hugos.modelfusion.mlEnsembleMethod` | **ML Ensemble Voting** | `string` | `"default"` | Ensemble voting technique: `"default"`, `"weighted_voting"`, or `"majority"`. |
| `hugos.modelfusion.mlCleanupDays` | **ML Telemetry Retention** | `number` | `7` | Retention threshold in days for historical ML routing logs before automatic database vacuuming. |
| `hugos.modelfusion.enableInnovations` | **Compound Innovations** | `boolean` | `false` | Globally enables experimental compound intelligence features across the runtime. |
| `hugos.modelfusion.innovationLevel` | **Innovation Severity** | `string` | `"medium"` | Depth of creative synthesis passes: `"low"`, `"medium"`, or `"high"`. |
| `hugos.modelfusion.topK` | **Top-K Retrieval** | `number` | `40` | Top-K sampling cutoff for model generation and vector context retrieval. |

### 7. Advanced Reasoning & RAG Settings

| Setting ID | GUI Label | Type | Production Default | Description |
|:---|:---|:---:|:---:|:---|
| `hugos.modelfusion.chainOfThought` | **Chain-of-Thought (CoT)** | `boolean` | `false` | Forces the model to emit a structured step-by-step reasoning scratchpad prior to finalizing answers. |
| `hugos.modelfusion.context` | **Static Custom Context** | `string` | `""` | User-defined system instructions or domain rules injected into all outgoing prompt payloads. |
| `hugos.modelfusion.contextAuto` | **Auto Context Generation** | `boolean` | `false` | Uses a local thinking model to summarize workspace context and prepend relevant project architecture notes. |
| `hugos.modelfusion.planEnabled` | **Pre-Execution Planning** | `boolean` | `false` | Enforces mandatory generation of a structured execution plan before executing complex coding changes. |
| `hugos.modelfusion.predictiveMode` | **Predictive Intent Engine** | `boolean` | `false` | Anticipates subsequent user actions and prepares background completions proactively. |
| `hugos.modelfusion.delegation` | **Subagent Delegation** | `boolean` | `false` | Enables autonomous decomposition of complex queries into parallel subagent execution tasks. |
| `hugos.modelfusion.recursion` | **Recursive Problem Solving** | `boolean` | `false` | Allows recursive prompt refinement loops until unit tests and lint verifications pass cleanly. |
| `hugos.modelfusion.realOptions` | **Real Options Decisioning** | `boolean` | `false` | Applies real options economic theory to evaluate architectural trade-offs under high uncertainty. |
| `hugos.modelfusion.promptQualityScoring`| **Prompt Quality Scoring** | `boolean` | `false` | Evaluates user prompts for ambiguity and missing context before dispatching to local models. |
| `hugos.modelfusion.semanticAnalysis` | **Deep Semantic Validation** | `boolean` | `false` | Performs vector semantic analysis across generated code to ensure semantic consistency with workspace patterns. |
| `hugos.modelfusion.temporalTracking` | **Temporal Code Tracking** | `boolean` | `false` | Tracks historical code mutations across time to understand developer intent and architectural drift. |
| `hugos.modelfusion.enableHyde` | **Enable HyDE RAG** | `boolean` | `false` | Activates Hypothetical Document Embeddings for vector search retrieval augmentation. |
| `hugos.modelfusion.useHyde` | **Interactive HyDE Refinement** | `boolean` | `false` | Refines hypothetical documents interactively with the user before performing vector searches. |
| `hugos.modelfusion.hydeVariants` | **HyDE Multiple Variants** | `boolean` | `false` | Generates 3-5 distinct hypothetical documents to broaden vector retrieval recall. |
| `hugos.modelfusion.fullMode` | **Full Compound Mode** | `boolean` | `false` | Enables full-depth execution: combines CoT, planning, multi-model consensus, and judge verification. |
| `hugos.modelfusion.workflowOptimization`| **Workflow Optimization** | `boolean` | `false` | Automatically optimizes agentic multi-step tool call sequences for minimum latency. |

### 8. Diagnostics & Watcher Settings

| Setting ID | GUI Label | Type | Production Default | Description |
|:---|:---|:---:|:---:|:---|
| `hugos.modelfusion.watcher.enabled` | **Enable Background Watcher**| `boolean` | **`true`** | Periodically checks for ModelFusion database updates and synchronizes catalog metadata. |
| `hugos.modelfusion.watcher.interval` | **Watcher Interval (Seconds)**| `integer` | `86400` | Background update frequency in seconds (default: 86,400 seconds = 24 hours). |
| `hugos.modelfusion.dbPath` | **Catalog Database Path** | `string` | `""` | Custom filesystem path for `hf_models.db`. Defaults to `IDE/db/hf_models.db` relative to the IDE bin folder. |
| `hugos.modelfusion.autoConfigCompleted`| **Auto-Config Completed** | `boolean` | `false` | Internal flag marking first-launch hardware discovery. Reset to `false` to re-run hardware detection. |
| `hugos.modelfusion.verbose` | **Verbose Output Logging** | `boolean` | `false` | Outputs detailed trace logs to the ModelFusion Server channel in the Output panel. |
| `hugos.modelfusion.debug` | **Debug Diagnostics** | `boolean` | `false` | Emits low-level IPC payloads, timing statistics, and memory allocations for bug diagnosis. |

### Chat & Model Routing Configurations

The remaining settings configuring HugOS IDE chat routing and multi-agent roles:

| Setting ID | Type | Default | Description |
|:---|:---:|:---:|:---|
| `chat.agent.enabled` | `boolean` | `true` | Enables the native HugOS chat assistant infrastructure. |
| `chat.utilityModel` | `string` | `"modelfusion/modelfusion-local"` | Directs general background chat utility tasks to the local ModelFusion engine. |
| `chat.utilitySmallModel` | `string` | `"modelfusion/modelfusion-local"` | Directs lightweight title/summary generation to local ModelFusion. |
| `github.copilot.enable` | `object` | `{"*": false}` | Disables proprietary cloud telemetry and vendor telemetry hooks. |
| `github.copilot.chat.inlineChat.enableThinking` | `boolean` | `false` | Enables local thinking model reasoning for inline editor prompts. |
| `github.copilot.chat.inlineChat.reasoningEffort` | `string` | `"low"` | Sets default thinking depth for inline editor interactions (`"low"`, `"medium"`, `"high"`). |
| `github.copilot.chat.executionSubagent.model` | `string` | `"gemini-3-flash"` | Configures model identity used when execution subagent delegation is active. |
| `github.copilot.chat.exploreAgent.enabled` | `boolean` | `true` | Enables codebase exploration subagent for repository mapping. |
| `github.copilot.chat.reviewAgent.enabled` | `boolean` | `true` | Enables automated code review subagent on git staging events. |
| `github.copilot.chat.imageUpload.enabled` | `boolean` | `true` | Enables image attachment and drag-and-drop support in chat prompts. |
| `github.copilot.chat.tools.viewImage.enabled` | `boolean` | `true` | Enables visual inspection tools for multimodal models. |
| `github.copilot.chat.workspace.enableCodeSearch` | `boolean` | `true` | Enables local workspace code search and vector indexing. |
| `github.copilot.chat.workspace.maxLocalIndexSize` | `number` | `100000` | Maximum character limit for local workspace symbol indices. |
| `github.copilot.chat.promptFileContextProvider.enabled` | `boolean` | `true` | Enables workspace context integration from `.prompt.md` files. |
| `github.copilot.chat.organizationInstructions.enabled` | `boolean` | `true` | Integrates instructions from `.github/copilot-instructions.md` and `AGENTS.md`. |
| `github.copilot.chat.setupTests.enabled` | `boolean` | `true` | Enables automated test scaffold generation for new repositories. |

---

## End-to-End Walkthrough Tutorials

### Tutorial 1: Iterative Code Evolution with /evolve and Inline Diff

**Scenario**: You have an unoptimized, bug-prone Rust memory cache (`src/cache.rs`) suffering from lock contention and unhandled boundary panics.

#### Step 1: Open Target File
Open `src/cache.rs` in the HugOS active editor buffer.

#### Step 2: Trigger Evolution
In the HugOS Chat panel, type:
```text
/evolve -n 5
Eliminate lock contention in this concurrent cache, replace Mutex with RwLock or lock-free DashMap, and add proper Option handling.
```
*(Alternatively: `@agent evolve --iterations 5`)*

#### Step 3: Monitor Live Iteration Passes
Watch real-time status updates stream in the chat:
- `Iteration 1/5 [Bugs]`: Identifies potential panic on missing key unwrap.
- `Iteration 2/5 [Performance]`: Substitutes `std::sync::Mutex` with `parking_lot::RwLock`.
- `Iteration 3/5 [Error Handling]`: Replaces panic branches with `Result<T, CacheError>`.
- `Iteration 4/5 [Refactor]`: Extracts generic storage backend with trait abstraction.
- `Iteration 5/5 [Security]`: Enforces maximum TTL expiration to prevent memory leaks.

#### Step 4: Inspect Inline Diff
The editor instantly presents cursor-style decorations:
- 🟢 **Green lines**: `parking_lot::RwLock` implementation and safe methods.
- 🔴 **Red lines**: Old contentious `Mutex` and dangerous unwrap statements.
- **Header Banner**: "✅ Accept (Ctrl+Shift+Y) · ❌ Reject (Ctrl+Shift+N)".

#### Step 5: Finalize
Press **`Ctrl+Shift+Y`** to accept all changes and save the file. If you wish to discard, press **`Ctrl+Shift+N`**.

---

### Tutorial 2: Multi-Model Consensus Deliberation with /fusion on Architecture

**Scenario**: Your engineering team is deciding between Event-Driven Architecture (Apache Kafka) vs Change-Data-Capture (Debezium + PostgreSQL) for real-time ledger auditing.

#### Step 1: Request Consensus Deliberation
In HugOS Chat, type:
```text
/fusion
/plan
/cot
Evaluate whether to implement audit logging via Kafka Event Sourcing or Debezium CDC for a financial transaction database handling 10,000 TPS.
```

#### Step 2: Model Execution & Independent Scoring
ModelFusion's Master CLI:
1. Detects live free RAM and dynamically provisions candidate models (e.g. `qwen2.5:14b`, `llama3.1:8b`, `deepseek-coder`).
2. Executes each model in parallel or sequential sandbox buffers.
3. Collects independent architectural analyses and scores each on operational complexity, schema evolution, and replay latency.

#### Step 3: Synthesis & LLM-as-a-Judge Review
The judge supervisor synthesizes the consensus:
- **Trade-off Matrix**: Clear comparison table covering TPS throughput, data consistency guarantees, operational overhead, and recovery time.
- **Recommended Verdict**: Specific recommendation tailored to your throughput and infrastructure constraints.

---

### Tutorial 3: Automated Security Audit & Hardening with /security

**Scenario**: You are preparing to deploy a new Node.js authentication microservice (`routes/auth.js`) handling user credentials and reset tokens.

#### Step 1: Run Security Audit
Open `routes/auth.js` and enter in chat:
```text
/security --deep
Perform a comprehensive OWASP Top 10 security audit and harden this authentication router.
```

#### Step 2: ATLAS Threat Analysis
ModelFusion performs static taint analysis and flags:
- **CWE-208 / Timing Attack**: `crypto.timingSafeEqual` missing on token comparisons.
- **CWE-307 / Brute Force**: Absence of rate-limiting middleware on `/login`.
- **CWE-798 / Hardcoded Secrets**: JWT secret fallback defaults to insecure string.

#### Step 3: Review Hardened Patch
ModelFusion presents the remediated code block with `argon2` password hashing, timing-safe equality checks, `express-rate-limit`, and validated environment variables.

#### Step 4: Apply Remediations
The inline diff renders automatically in the editor. Press **`Ctrl+Shift+Y`** to accept the security hardening.

---

### Tutorial 4: Live Model Hub Updates & Local Auto-Provisioning with /update

**Scenario**: You want to update your offline catalog with the latest top models from Hugging Face and ensure your local Ollama daemon has the best model provisioned for your hardware.

#### Step 1: Run Curated Update
In HugOS Chat, type:
```text
/update
```
*(Or in terminal: `cli.exe --update --db-path "IDE/db/hf_models.db"`)*

#### Step 2: Hardware Sizing & Ollama Discovery
The Master CLI:
1. Evaluates runtime available RAM (`res.free_ram_gb`) and free GPU VRAM (`res.free_vram_mb`).
2. Probes `http://127.0.0.1:11434/api/tags`. If absent, discovers or installs Ollama silently and adds it permanently to user `PATH`.
3. Selects the hardware-appropriate model tier:
   - Available RAM $\ge$ 48 GB $ightarrow$ `qwen2.5:32b`
   - Available RAM $\ge$ 24 GB $ightarrow$ `qwen2.5:14b`
   - Available RAM $\ge$ 12 GB $ightarrow$ `qwen2.5:7b`
   - Available RAM $\ge$ 6 GB $ightarrow$ `qwen2.5:3b`
   - Available RAM $<$ 6 GB $ightarrow$ `qwen2.5:1.5b`
4. Pulls the target model (`ollama pull qwen2.5:7b`) with live progress.

#### Step 3: Database Catalog Ingestion
Ingests top-downloaded workhorse models across all 45 tasks into `hf_models.db`.

#### Step 4: Verify Runtime State
In chat, run:
```text
/sysinfo
/active-model
```
Confirm your provisioned model is active, hardware acceleration is engaged, and the catalog is 100% up to date.

---

## MSI Packaging

### Packaging Pipeline

Run the PowerShell packaging automation from the `IDE/` directory:

```powershell
cd IDE
powershell -ExecutionPolicy Bypass -File build_msi.ps1
```

### Automation Flow

1. **Prerequisite Verification**: Checks for WiX Toolset v4+, .NET SDK, and the source-built `VSCode-win32-x64/` directory.
2. **Binary Parity Sync**: Copies release `cli.exe` into `IDE/bin/` and `VSCode-win32-x64/bin/`.
3. **Version Increment**: Increments build number in `IDE/build_number.txt` and updates `IDE/HugOS.wxs`.
4. **Authenticode Signing**: Signs all 127+ `.exe` and `.dll` files using `hugos-signing-cert.pfx` with SHA-256 and DigiCert timestamping.
5. **WiX Harvesting & Compilation**: Generates component manifest and builds MSI installer (`HugOS.msi`).
6. **Package Signing**: Signs the resulting `.msi` file.

### Installation Directory

- Default per-user install path: `%LOCALAPPDATA%\HugOS IDE\`
- CLI binary path: `%LOCALAPPDATA%\HugOS IDEin\cli.exe`
- Database path: `%LOCALAPPDATA%\HugOS IDE\db\hf_models.db`

---

## Key Patches Applied to VS Code

HugOS IDE applies systematic transformations to stock upstream Microsoft VS Code (Code-OSS) via the automated `cli.exe --patch-ide` pipeline:

### 1. Language Model Whitelist Bypass & Provider Auto-Registration
**File**: `src/vs/workbench/contrib/chat/common/languageModels.ts`
- Stripped hardcoded vendor whitelist that historically restricted default language models to Microsoft Copilot.
- Configured `isDefault: true` for the `modelfusion` vendor provider, enabling local offline models to serve as default chat engines.
- Injected startup auto-registration: checks `getLanguageModelsProviderGroups()`, and if `modelfusion` is absent, automatically registers the `ModelFusion Local Panel` provider group on workbench initialization.

### 2. MCP Registry Isolation & Server Filtering
**File**: `src/vs/workbench/contrib/mcp/common/mcpRegistry.ts`
- Injected dynamic server definition filtering into `registerCollection()`.
- Filters registered collections so that only servers ending in `.modelfusion` or labeled `modelfusion` are exposed to the IDE thinking agent.
- Prevents rogue or unverified third-party MCP servers from polluting the local orchestration context.

### 3. Chat Provider Timeout Accommodation
**File**: `src/vs/workbench/contrib/chat/browser/chatSetup/chatSetupProviders.ts`
- Replaced the default 20-second connection timeout with a 60-second window:
  ```typescript
  this.environmentService.remoteAuthority ? 60000 : 60000 /* 60s — accommodates local ModelFusion server startup */
  ```
- Accommodates cold-start hardware initialization for the local ModelFusion daemon and Ollama model weights.

### 4. Copilot Telemetry & Widget Decoupling (8+ TypeScript Files)
Systematically redirected Copilot telemetry hooks, settings menus, and editor widgets to ModelFusion:
- **`src/main.ts`**: Replaced `"VS Code"` with `"HugOS"` in persistent `argv.json` argument descriptions and rendering comments.
- **`src/vs/platform/product/common/product.ts`**: Replaced `defaultChatAgent` extension identifiers (`'GitHub.copilot'` -> `'HugOS.modelfusion'`, `'GitHub.copilot-chat'` -> `'HugOS.modelfusion'`).
- **`src/vs/platform/dataChannel/browser/forwardingTelemetryService.ts`**: Updated `isCopilotLikeExtension` check to match `hugos.modelfusion`.
- **`src/vs/workbench/contrib/chat/browser/aiCustomization/mcpListWidget.ts`**: Redirected `COPILOT_EXTENSION_IDS` array to `['hugos.modelfusion', 'hugos.modelfusion']`.
- **`src/vs/workbench/contrib/editTelemetry/browser/telemetry/editSourceTrackingFeature.ts` & `editSourceTrackingImpl.ts`**: Updated telemetry source tracking IDs from GitHub Copilot to HugOS ModelFusion.
- **`src/vs/workbench/contrib/terminal/browser/terminalMenus.ts`**: Replaced terminal AI profile contributor identifiers with `hugos.modelfusion`.
- **`src/vs/workbench/contrib/preferences/browser/settingsLayout.ts`**: Updated common settings shortcuts to point to `HugOS.modelfusion.manageExtension`.

### 5. Native Product Identity & Package Metadata
**Files**: `product.json` and `package.json`
- `product.json`: Configures `applicationName: "hugos"`, `nameShort: "HugOS"`, `nameLong: "HugOS IDE"`, and injects API proposal whitelists for language model providers.
- `package.json`: Replaced root manifest metadata (`name: "hugos"`, `displayName: "HugOS"`, `description: "HugOS - Custom AI-Powered Code-OSS IDE"`, `author: { "name": "HugOS Team" }`).

### 6. Built-in ModelFusion Extension Integration
**Destination**: `extensions/modelfusion/`
- Recursively copies `IDE/vscode/extensions/modelfusion` into the built-in extensions directory.
- Bakes the custom chat participant, inline diff manager, and slash/@agent parser directly into the distribution without requiring external marketplace downloads.

### 7. Custom Vector Artwork & Icons
**Destination**: `resources/`
- Replaces stock Code-OSS icons with official HugOS branding across all platforms:
  - Windows: `resources/win32/code.ico`, `code_150x150.png`, `code_70x70.png`
  - macOS: `resources/darwin/code.icns`
  - Linux: `resources/linux/code.png`

### 8. Developer Debugging Manifests
**Files**: `.vscode/launch.json` & `.vscode/tasks.json`
- `.vscode/launch.json`: Injects `${workspaceFolder}/extensions/modelfusion/dist/**/*.js` into `outFiles` for seamless source-level debugging of the ModelFusion extension.
- `.vscode/tasks.json`: Replaces references to `extensions/copilot` with `extensions/modelfusion`.

### 9. PE Binary Resource Branding via `rcedit.exe`
**Target**: `IDE/VSCode-win32-x64/HugOS.exe`
- Modifies the Portable Executable (PE) resource table of the compiled Electron binary using `rcedit-x64.exe`:
  - `ProductName` & `FileDescription`: `"HugOS IDE"`
  - `CompanyName`: `"HugOS Team"`
  - `InternalName`: `"HugOS"`
  - `OriginalFilename`: `"HugOS.exe"`
  - `LegalCopyright`: `"Copyright (C) 2026 HugOS Team"`
  - Product/File Version: `"1.126.0"`
  - Main Window & Explorer Icon: `IDE/hugos.ico`

### 10. Electron Runtime Integrity & Authenticode Signature Protection
**Target**: `IDE/VSCode-win32-x64/`
- **ICU Descriptor Guard**: Code.exe/HugOS.exe in Electron loads ICU internationalization data from a versioned hash subdirectory (e.g. `7e7950df89/`), NOT from the root folder. The pipeline verifies that this directory exists, preventing startup crashes with `Invalid file descriptor to ICU data received`.
- **Authenticode Signature Verification**: Verifies that the built executable has not been corrupted with an invalid self-signed certificate, enforcing the safety protections detailed in `IDE/INCIDENT_SIGNING_2026-07-16.md`.

