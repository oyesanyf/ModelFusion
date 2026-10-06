# Project Rules & User Preferences

## Mandatory Completion Rule: Always Commit, Push & Update Release Artifacts
Whenever any task, code edit, bug fix, calibration, or enhancement is done:
1. **Recompile Release Binaries**: `cargo build --release --bin cli`.
2. **Mirror Parity**: Run `python scripts/mirror_all.py` to keep all 12 binary/asset locations in identical parity.
3. **Rebuild & Sign MSI**: Run `powershell -ExecutionPolicy Bypass -File .\IDE\build_msi.ps1`.
4. **Submit to Microsoft Security Intelligence (WDSI) Every Build**:
   - Command: `python scripts/submit_to_wdsi.py --all --no-launch`
   - Every time code is recompiled, binaries mirrored, or MSIs packaged, submit all Authenticode-signed release targets (`cli.exe`, `clibrowser.exe`, `cliide.exe`, `climcp.exe`, `HugOS.msi`, `HugOS_Browser.msi`) to Microsoft Security Intelligence (`https://www.microsoft.com/en-us/wdsi/filesubmission?persona=SoftwareDeveloper`).
   - Ensures SmartScreen whitelisting, Windows Defender reputation scoring, and false positive suppression.
   - Automatically updates `IDE/reports/wdsi_submissions.json` with SHA-256 hashes, file sizes, and digital certificate thumbprints.
5. **Git Commit & Push**: Stage all changes (`git add -A`), commit with descriptive message, and push to `https://github.com/oyesanyf/ModelFusion.git`.
6. **Update Remote GitHub Releases**: Upload the latest `HugOS.msi` and `cli.exe` to the versioned release tag (e.g. `v1.0.0-beta.219`) and clobber update the rolling release `v1.0.0-beta`.
7. **Parity Check**: Verify 100% parity between local working directory, git remote `origin/main`, Git LFS, and GitHub release assets.

## Git Push Guardrails
- **Restricted Remotes:** NEVER run `git push` inside `IDE/vscode` or target any Microsoft/upstream third-party remote.
- **Canonical Repository:** ALL code pushes must strictly target `https://github.com/oyesanyf/ModelFusion.git`.

## Execution Blueprints (Flash Engine Constraints)
- **Trigger:** Applies ONLY when running high-speed/Flash models (e.g., Gemini Flash variants).
- **Exclusion:** Full-scale reasoning engines and simple/trivial single-line queries proceed normally without blueprints.

---

### Blueprint 1: Sandbox & Verify (Coding & Architecture)
1. **SANDBOX:** State implementation plan, required crates/dependencies, and 3 specific edge cases (e.g., Rust OOM/memory safety, TS disposable leaks, async deadlocks).
2. **VERIFY:** Detail how the design explicitly handles each identified edge case.
3. **OUTPUT:** Final code implementation with strict typing and error handling.

### Blueprint 2: Deconstruct & Solve (Math & Logic)
1. **EXTRACT:** List all raw data, variables, and constraints from the prompt.
2. **RULE:** State the exact formula or logic rule required.
3. **WORK:** Show step-by-step transformations.
4. **ANSWER:** Conclude with the final computed result (do not state the answer in the first line).

### Blueprint 3: Self-Correction (Debugging & Error Logs)
1. **TRACE:** Follow execution flow line-by-line to the point of failure.
2. **ISOLATE:** State the exact cause of the crash or syntax error.
3. **REFACTOR:** Provide the fixed code block highlighting the patch.

### Blueprint 4: Retrieve & Struct (Q&A & Technical Research)
1. **RETRIEVE:** Cite specific context sources, files, logs, or external docs referenced.
2. **CONTEXT:** Summarize key verified facts and remaining open variables.
3. **ANSWER:** Present a concise, scannable response using bullet points or tables.

## Master CLI & Update Architecture (Persistent Memory)
- **18-Way Cryptographic Binary Parity across CLI, Browser, MCP & IDE**:
  Whenever `cli.exe` is recompiled, it MUST be mirrored with identical SHA-256 hashes across all 18 locations:
  1. `target/release/cli.exe` (Authoritative master CLI build target)
  2. `browser/bin/clibrowser.exe` (Authoritative dedicated binary for HugOS Browser)
  3. `target/release/clibrowser.exe` (Browser release staging binary)
  4. `%LOCALAPPDATA%/HugOS Browser/bin/clibrowser.exe` (Locally installed production browser binary)
  5. `browser/dist/win-unpacked/resources/bin/clibrowser.exe` (Unpacked browser distribution binary)
  6. `browser/bin/cli.exe` (Browser staging fallback binary)
  7. `%LOCALAPPDATA%/HugOS Browser/bin/cli.exe` (Browser installed fallback binary)
  8. `IDE/bin/cliide.exe` (Authoritative dedicated binary for HugOS IDE)
  9. `IDE/VSCode-win32-x64/bin/cliide.exe` (Packaged IDE distribution binary)
  10. `%LOCALAPPDATA%/HugOS IDE/bin/cliide.exe` (Locally installed production IDE binary)
  11. `IDE/bin/cli.exe` (IDE packaging staging fallback binary)
  12. `%LOCALAPPDATA%/HugOS IDE/bin/cli.exe` (IDE installed fallback binary)
  13. `target/release/climcp.exe` (Authoritative dedicated binary for HugOS MCP Server)
  14. `mcp/bin/climcp.exe` (MCP staging dedicated binary)
  15. `mcp/bin/cli.exe` (MCP staging fallback binary)
  16. `%LOCALAPPDATA%/HugOS MCP/bin/climcp.exe` (Locally installed production MCP binary)
  17. `%LOCALAPPDATA%/HugOS MCP/bin/cli.exe` (MCP installed fallback binary)
  18. `C:\Users\oyesanyf\AppData\Local\Programs\ModelFusion\cli.exe` (Root application distribution binary)
- **Component Binary Priority Laws**:
  - **Browser Execution Law**: HugOS Browser (`hugos-browser.bat`, `HugOS_Browser.wxs`) ALWAYS prioritizes `clibrowser.exe` first for all browser automation, OS grounding, server lifecycle, and UI-TARS loops, falling back to `cli.exe`.
  - **IDE Execution Law**: HugOS IDE (`_findCliBinary` in `IDE/vscode/extensions/copilot/dist/extension.js`) ALWAYS prioritizes `cliide.exe` first, falling back to `cli.exe`.
  - **MCP Execution Law**: Universal MCP Server launcher (`run_mcp.ps1`, `run_mcp.bat`, `run_mcp.sh`) discovers `climcp.exe` first (`target/release/climcp.exe`, `mcp/bin/climcp.exe`, `%LOCALAPPDATA%/HugOS MCP/bin/climcp.exe`), with fallback to `cliide.exe`, `clibrowser.exe`, or `cli.exe`.
- **Database Update Commands (`--update` vs `--updatedb`)**:
  - `--update` (Fast Curated Engine): Ingests top ~6,500 production workhorse models across all 45 tasks and provisions optimal local Ollama hardware model. Used for daily runs, chat `@agent update`, and IDE background watcher. Syntax: `cli.exe --update --db-path "IDE/db/hf_models.db"`.
  - `--updatedb` (Full Registry Crawler): Cursor-paginated crawler that ingests ALL 2M+ models from Hugging Face Hub ("whether junk or not") in 1,000-model batches. Optional `--max-models <N>` caps total ingestion. Syntax: `cli.exe --updatedb --db-path "IDE/db/hf_models.db"`.
- **All Models & All Modalities**: The update pipeline covers all 45+ Hugging Face tasks (Vision, Audio, NLP, Multimodal, Tabular, RL, Legal, Security, etc.) for over 2 million models, not just coding models.
- **Runtime Available Memory Rule**: NEVER allocate models against total physical RAM. Always evaluate runtime free/available RAM (`res.free_ram_gb`) and free VRAM (`res.free_vram_mb`) to avoid OOM from concurrent workloads.
- **Ollama Engine Setup & Zero Touch Law**: Must auto-detect, auto-install silently (`OllamaSetup.exe /SILENT /NORESTART`), inject Ollama directory into process-scoped `PATH` only, start `ollama serve`, and pull the hardware-appropriate model. NEVER modify Windows User (`HKCU\Environment`) or System registry environment variables under ANY circumstances.
- **WiX Installer Zero-Touch PATH Law**: NEVER use `<Environment Id="PATH" ...>` in WiX installers (`.wxs`). WiX's `Permanent="no"` translates into destructive MSI table flag `=-*PATH` which deletes the system or user PATH. HugOS IDE and HugOS Browser MUST strictly rely on application folder shortcuts, launcher scripts (`hugos-browser.bat`), and in-memory process PATH (`std::env::set_var`).
- **Incremental Background Watcher**: `_runDatabaseUpdate()` periodically invokes `cli.exe --update --db-path <dbPath>` at below-normal priority with logs piped to the `ModelFusion Server` channel.

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

