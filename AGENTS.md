# ModelFusion / HugOS IDE Rules & Persistent Instructions

## Core Rule: Always Rebuild, Sign, and Synchronize the MSI Installer
Whenever code changes, bug fixes, or enhancements are made to ModelFusion or HugOS IDE:
1. **Recompile Release Binaries**:
   - Recompile the release CLI: `cargo build --release --bin cli`.
   - Verify `target/release/cli.exe` functionality and `--sys-info`.
2. **Rebuild & Sign MSI Package**:
   - Run the packaging pipeline: `powershell -ExecutionPolicy Bypass -File .\IDE\build_msi.ps1`.
   - Verify the build number auto-increments in `IDE/build_number.txt` and `IDE/HugOS.wxs`.
   - Ensure all binaries, DLLs, and the final `IDE/HugOS.msi` are digitally signed with `hugos-signing-cert.pfx` and timestamped via DigiCert.
3. **Submit to Microsoft Security Intelligence (WDSI) Every Build**:
   - Command: `python scripts/submit_to_wdsi.py --all --no-launch`
   - Every time code is recompiled, binaries mirrored, or MSIs packaged, submit all Authenticode-signed release targets (`cli.exe`, `clibrowser.exe`, `cliide.exe`, `climcp.exe`, `HugOS.msi`, `HugOS_Browser.msi`) to Microsoft Security Intelligence (`https://www.microsoft.com/en-us/wdsi/filesubmission?persona=SoftwareDeveloper`).
   - Ensures SmartScreen whitelisting, Windows Defender reputation scoring, and false positive suppression.
   - Automatically updates `IDE/reports/wdsi_submissions.json` with SHA-256 hashes, file sizes, and digital certificate thumbprints.
4. **Commit Code & Git LFS**:
   - Stage all source code changes, tests, and the updated `IDE/HugOS.msi` (tracked via Git LFS).
   - Commit with descriptive conventional commit messages.
   - Push to `origin/main` (or via branch and PR squash-merge).
5. **Update Remote GitHub Release Assets**:
   - Create or update the versioned release tag (`v1.0.0-beta.XX`) with the latest `HugOS.msi` and `target/release/cli.exe`.
   - Update the rolling release [`v1.0.0-beta`](https://github.com/oyesanyf/ModelFusion/releases/tag/v1.0.0-beta) with `--clobber`.
6. **Cryptographic & Git Parity**:
   - Maintain 100% parity between local working directory, git `main`, Git LFS, and remote GitHub release assets (SHA-256 hashes, file sizes, and timestamps).
7. **Disk Hygiene**:
   - Run `git lfs prune --recent` before and after staging large installer files to preserve drive D: free space.

## Core Architecture: ModelFusion Master CLI & Universal Update Pipeline

The ModelFusion Master CLI (`crates/cli/src/main.rs`) is the single authoritative execution engine for hardware discovery, model selection, local AI lifecycle management, and catalog database ingestion. HugOS IDE does not implement an independent updating mechanism; it delegates directly to the Master CLI.

### Database Update Commands: `--update` vs `--updatedb`
ModelFusion provides two distinct, non-aliased update commands:
- **`--update` (Fast Curated Engine)**:
  - Ingests top ~6,500 production workhorse models across all 45 tasks.
  - Detects runtime available/free RAM and provisions matching Ollama model (e.g. `qwen2.5:32b`).
  - Designed for daily use, `@agent update` in chat, and IDE background watcher.
  - Syntax: `cli.exe --update --db-path "IDE/db/hf_models.db"`
- **`--updatedb` (Full Registry Crawler - All 2M+ Models)**:
  - Continuously traverses the entire Hugging Face Hub via cursor pagination (`limit=1000`, HTTP `Link: rel="next"`).
  - Ingests every model in the registry into SQLite ("whether junk or not").
  - Commits 1,000 models per transaction (~1,000 models/sec).
  - Syntax: `cli.exe --updatedb --db-path "IDE/db/hf_models.db"`
  - Optional cap: `--max-models <N>` (e.g. `--max-models 50000`).

### 1. 18-Way Cryptographic Binary Parity & Component Priority Laws
Whenever `cli.exe` is recompiled, it MUST be mirrored with identical SHA-256 hashes across all 18 distribution locations via `scripts/mirror_all.py`:
1. `d:\harfile\ModelFusion\target\release\cli.exe` (Authoritative master CLI build target)
2. `d:\harfile\ModelFusion\browser\bin\clibrowser.exe` (Authoritative dedicated binary for HugOS Browser)
3. `d:\harfile\ModelFusion\target\release\clibrowser.exe` (Browser release staging binary)
4. `%LOCALAPPDATA%\HugOS Browser\bin\clibrowser.exe` (Locally installed production browser binary)
5. `d:\harfile\ModelFusion\browser\dist\win-unpacked\resources\bin\clibrowser.exe` (Unpacked browser distribution binary)
6. `d:\harfile\ModelFusion\browser\bin\cli.exe` (Browser staging fallback binary)
7. `%LOCALAPPDATA%\HugOS Browser\bin\cli.exe` (Browser installed fallback binary)
8. `d:\harfile\ModelFusion\IDE\bin\cliide.exe` (Authoritative dedicated binary for HugOS IDE)
9. `d:\harfile\ModelFusion\IDE\VSCode-win32-x64\bin\cliide.exe` (Packaged IDE distribution binary)
10. `%LOCALAPPDATA%\HugOS IDE\bin\cliide.exe` (Locally installed production IDE binary)
11. `d:\harfile\ModelFusion\IDE\bin\cli.exe` (IDE packaging staging fallback binary)
12. `%LOCALAPPDATA%\HugOS IDE\bin\cli.exe` (IDE installed fallback binary)
13. `d:\harfile\ModelFusion\target\release\climcp.exe` (Authoritative dedicated binary for HugOS MCP Server)
14. `d:\harfile\ModelFusion\mcp\bin\climcp.exe` (MCP staging dedicated binary)
15. `d:\harfile\ModelFusion\mcp\bin\cli.exe` (MCP staging fallback binary)
16. `%LOCALAPPDATA%\HugOS MCP\bin\climcp.exe` (Locally installed production MCP binary)
17. `%LOCALAPPDATA%\HugOS MCP\bin\cli.exe` (MCP installed fallback binary)
18. `C:\Users\oyesanyf\AppData\Local\Programs\ModelFusion\cli.exe` (Root application distribution binary)

**Component Priority Laws**:
- **Browser Law**: `clibrowser.exe` is the primary execution binary for HugOS Browser (`hugos-browser.bat`, `HugOS_Browser.wxs`) for all OS automation, UI-TARS, and web browsing tasks, with fallback to `cli.exe`.
- **IDE Law**: `cliide.exe` is the primary execution binary for HugOS IDE (`_findCliBinary` in `copilot/dist/extension.js`), with fallback to `cli.exe`.
- **MCP Law**: Universal MCP Server launcher (`run_mcp.ps1`, `run_mcp.bat`, `run_mcp.sh`) discovers `climcp.exe` first (`target/release/climcp.exe`, `mcp/bin/climcp.exe`, `%LOCALAPPDATA%/HugOS MCP/bin/climcp.exe`), with fallback to `cliide.exe`, `clibrowser.exe`, or `cli.exe`.

### 2. Universal Multi-Modal Catalog (All 45+ Tasks & 2M+ Models)
- HugOS IDE is a universal multi-modal operating system, not solely a coding assistant.
- The update pipeline ingests top-downloaded and highest-utility models across ALL 45 Hugging Face tasks spanning:
  - **Vision**: Image classification, object detection, segmentation, image-to-text, depth estimation.
  - **Audio**: Speech recognition (ASR), text-to-speech (TTS), audio classification, voice activity detection.
  - **NLP & Conversational**: Text generation, chat, summarization, translation, question answering.
  - **Code & Reasoning**: Code generation, infilling, reasoning, instruction following.
  - **Domain & Multimodal**: VQA, document QA, tabular modeling, reinforcement learning, medical, legal, security analysis.
- Multi-tier ingestion populates the SQLite catalog (`hf_models.db`) to enable offline discovery and instant switching.

### 3. Dynamic Hardware Sizing: Available Runtime Memory Rule
- **CRITICAL LAW**: NEVER size or allocate models based on total installed physical RAM. Always evaluate **runtime available / free memory** (`res.free_ram_gb`, `res.free_vram_mb`).
- **Rationale**: Concurrent processes, system caches, or background workloads may occupy significant memory. Evaluating total RAM causes fatal OOM aborts.
- **Hardware-to-Model Dynamic Scaling Matrix**:
  - Available RAM >= 48 GB OR Free VRAM >= 24 GB -> `qwen2.5:32b`
  - Available RAM >= 24 GB OR Free VRAM >= 14 GB -> `qwen2.5:14b`
  - Available RAM >= 12 GB OR Free VRAM >= 4.5 GB -> `qwen2.5:7b`
  - Available RAM >= 6 GB OR Free VRAM >= 2 GB -> `qwen2.5:3b`
  - Available RAM < 6 GB OR Low-Budget Flag -> `qwen2.5:1.5b`

### 4. Ollama Lifecycle & In-Memory Process PATH Architecture
- **ZERO TOUCH OF WINDOWS ENVIRONMENT VARIABLES LAW**:
  *CRITICAL LAW: NEVER modify Windows User (`HKCU\Environment`) or System registry environment variables under ANY circumstances. All environment variables must strictly be process-scoped (`std::env::set_var`, `process.env`) or local `.env` configuration files. ModelFusion, HugOS IDE, and HugOS Browser must NEVER tamper with the user's personal Windows environment.*
- **WIX INSTALLER ZERO-TOUCH PATH LAW**:
  *CRITICAL LAW: NEVER use `<Environment Id="PATH" ...>` in WiX installers (`.wxs`). WiX's `Permanent="no"` translates into destructive MSI table flag `=-*PATH` which deletes the system or user PATH. HugOS IDE and HugOS Browser MUST strictly rely on application folder shortcuts, launcher scripts (`hugos-browser.bat`), and in-memory process PATH (`std::env::set_var`).*
During `--update` or local engine startup (`ensure_ollama_running()`):
1. **Live Health Probe**: Probes `http://127.0.0.1:11434/api/tags`. If responding, proceeds immediately.
2. **Binary Discovery**: Resolves `ollama` via `PATH` and checks standard paths (`%LOCALAPPDATA%\Programs\Ollama`, `%PROGRAMFILES%\Ollama`, etc.).
3. **Silent Auto-Installation**: If absent, silently downloads `https://ollama.com/download/OllamaSetup.exe` and installs with `/SILENT /NORESTART`.
4. **In-Memory Process PATH**:
   - Immediately injects the Ollama directory into the current process `std::env::set_var("PATH", ...)`.
   - Never writes to the registry or modifies Windows User environment variables.
5. **Daemon Launch & Polling**: Launches `ollama serve` in the background with `OLLAMA_ORIGINS=*` process environment and polls until healthy.
6. **Live Model Provisioning**: Executes `ollama pull <model>` for the dynamically selected model tier.

### 5. Incremental Background Watcher & Interactive Chat Flow
- **Interactive Chat (`@agent update`)**: Dispatches the update command directly to the Master CLI, displaying live terminal progress to the user.
- **Incremental Background Watcher (`_startWatcher` / `_runDatabaseUpdate`)**:
  - Runs periodically in HugOS IDE to keep the multi-modal database and local models refreshed.
  - Spawns `cli.exe --update --db-path <dbPath>` at below-normal priority to protect interactive editing performance.
  - Pipes structured logs prefixed with `[Watcher]` to the `ModelFusion Server` output channel.

### 6. ReST-RL Background Daemon Invariants & Zero-Impact Laws
- **Strict 40% VRAM Cap**: Never load independent secondary reward models (e.g. 8B Skywork) concurrently with policy models on systems with <24 GB VRAM. Sizing must rely on the 4-tier zero-VRAM graduated verification signal and unified single-model PRM/logprob scoring.
- **Dynamic Ollama Tag Parity**: Adapters must dynamically query `/api/tags` or use the Master CLI's dynamically pulled models (`qwen2.5:32b`, `qwen2.5:14b`, `qwen2.5:7b`, `qwen2.5:1.5b`). Never hardcode model tags with `-coder` suffixes that trigger silent HTTP 404 aborts. Prompts must always include `task.test_target` and error reflection tracebacks.
- **Sub-50ms Preemption Architecture**:
  - Test runners in `sandbox.py` must register subprocesses with a Windows Job Object (`CreateJobObjectW`) terminated via `TerminateJobObject(hJob, 1)` upon `ide/idle_stop` (<8ms cancellation).
  - LLM inference must use streaming SSE (`stream: true`) with token-level `is_paused()` yield checks (<25ms abortion).
- **Mutation Testing Gate**: Mutation testing ($K=5$ AST mutants) must act as an adversarial certification gate ($M_{kill} \ge 0.5 \implies R=1.0$), not a scalar multiplier that drops passing solutions below the IDE's 1.0 presentation threshold.

### 7. Universal Computer Use, UI-TARS, Exam Solver & Port 5000 Resilience Laws
- **All 10 Computer Use Tools Authorized & Maintained**:
  1. `@agent computer-use <goal>` (Autonomous Computer Use & Web Navigation)
  2. `@agent exam-solver <url/exam>` (Autonomous Exam & Quiz Solver)
  3. `@agent map-directions <route>` (Map Directions & Route Planning)
  4. `@agent desktop-click <coords>` (OS Mouse Click)
  5. `@agent desktop-type <text>` (OS Keyboard Typing & Hotkeys)
  6. `@agent desktop-scroll <delta>` (OS Window Scrolling)
  7. `@agent screen-grounding` (Perceive & Ground Screen Interactive Elements)
  8. `@agent shopping <item>` (Price Comparison & Shopping Assistant)
  9. `@agent ticket-booking <details>` (Flight & Event Ticket Booking)
  10. `@agent ui-tars <goal>` (Autonomous UI-TARS Perception-Action Loop)
  - Preprocessor in `crates/cli/src/main.rs` (`preprocess_cli_args`) MUST always recognize and format all 10 subcommands into `--computer-use` goals without throwing "unexpected argument" errors.
- **Search Engine & Navigation URL Typo Resiliency**:
  - Automatically fix URL typos (`ww.google.com`, `w.google.com`, `wwww.google.com`, `gogle.com`, `googl.com` -> `www.google.com`, `ww.bing.com` -> `www.bing.com`).
  - Extract search queries with typo tolerance (`seach for ...` -> search query `...`).
  - Automatically rewrite search engine home URLs when a search goal is detected (e.g. `google.com` + `seach for weather in lagos Nigeria` -> `https://www.google.com/search?q=weather%20in%20lagos%20Nigeria`).
  - Cleanly discard stale CLI error text in webview DOM to prevent UI-TARS from grounding on stale crashes.
- **Exam Solver & Same-Page Answering**:
  - `extractExamQuestions` must support both DOM structures (radio groups, tables, cards, checkmark images) and plain-text/HTML string fallback.
  - Automatically detect answer keys (e.g. tests.com `<input type="hidden" name="answerposn..." value="4">` -> Option D) and explanation rationales.
  - Render interactive Human-in-the-Loop (HITL) safety gate workspace (`buildHitlExamWorkspaceHtml`) with auto-solve, manual option selection, question pagination (`q=1` -> `q=2`, ...), and confirm/abort controls.
- **Server Port 5000 & Browser Zero-Crash Guarantee (`ERR_FAILED` Elimination)**:
  - Persistent background startup daemon (`ModelFusion_Server.vbs` in Windows Startup) ensures Master Server is always online on port 5000.
  - `run_hidden.vbs` must always sanitize quotes (`CleanQuote`) to prevent double-quote escaping.
  - `hugos-browser.bat` launcher must probe `http://127.0.0.1:5000/health`. If port 5000 is not responding, it MUST automatically fall back to `file:///` local UI protocol, never letting the browser crash into Chrome's `ERR_FAILED` dead-end page.
  - `browser/ui/app.js` must NEVER blindly force `window.location.replace('http://localhost:5000/index.html')` from `file:` protocol without verified 200 OK.

### 8. Hybrid Decision Model Engine (Strands Decider 2B + Cloudflare Clef/Clef-Flash)
- **Architecture**: Dual-engine System 1 decision-making combining AWS Strands Labs' Strands Decider 2B (local 1.9B pointer-head fast router, sub-15ms, zero VRAM) with Cloudflare Workers AI Clef / Clef-Flash (edge 9B dual-attention router, multimodal vision routing).
- **Ensemble Modes**:
  - `hybrid` (default): Fast local Strands Decider 2B pass; if confidence >= 0.75, routes immediately; if uncertainty is high or vision input is detected, invokes Cloudflare Clef-Flash with Bayesian calibration ($P_{\text{cal}} = \sigma(\alpha \cdot z)$) ensuring sum of probabilities = 1.0.
  - `strands`: Ultra-low latency local execution (<15ms) via Strands Decider 2B pointer network.
  - `clef`: Cloudflare Clef-Flash / Clef edge execution for multimodal queries.
  - `fast`: Dynamic heuristic rule-based routing fallback (<5ms).
- **Execution & Endpoints**:
  - CLI: `cli.exe --decision "<query>" --choices "A, B, C" [--decision-mode <mode>] [--decision-engine <engine>]`
  - Chat Agent: `@agent decision <query> --choices "A, B, C"`
  - HTTP Server (Port 5000): `/api/decision` (JSON evaluation) and `/api/decision/status` (engine health & status).
  - Human-in-the-Loop (HITL) Gate: When top choice confidence is <0.50 or high ambiguity is detected, returns `hitl_gate_triggered: true` with interactive confirmation.

