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
3. **Commit Code & Git LFS**:
   - Stage all source code changes, tests, and the updated `IDE/HugOS.msi` (tracked via Git LFS).
   - Commit with descriptive conventional commit messages.
   - Push to `origin/main` (or via branch and PR squash-merge).
4. **Update Remote GitHub Release Assets**:
   - Create or update the versioned release tag (`v1.0.0-beta.XX`) with the latest `HugOS.msi` and `target/release/cli.exe`.
   - Update the rolling release [`v1.0.0-beta`](https://github.com/oyesanyf/ModelFusion/releases/tag/v1.0.0-beta) with `--clobber`.
5. **Cryptographic & Git Parity**:
   - Maintain 100% parity between local working directory, git `main`, Git LFS, and remote GitHub release assets (SHA-256 hashes, file sizes, and timestamps).
6. **Disk Hygiene**:
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

### 1. 4-Way Cryptographic Binary Parity
Whenever `cli.exe` is recompiled, it MUST be mirrored across all 4 locations with identical SHA-256 hashes:
1. `d:\harfile\ModelFusion\target\release\cli.exe` (Authoritative build target)
2. `d:\harfile\ModelFusion\IDE\bin\cli.exe` (IDE packaging staging)
3. `d:\harfile\ModelFusion\IDE\VSCode-win32-x64\bin\cli.exe` (Packaged distribution directory)
4. `%LOCALAPPDATA%\HugOS IDE\bin\cli.exe` (Locally installed production IDE)

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

### 4. Ollama Lifecycle & System PATH Persistence
During `--update` or local engine startup (`ensure_ollama_running()`):
1. **Live Health Probe**: Probes `http://127.0.0.1:11434/api/tags`. If responding, proceeds immediately.
2. **Binary Discovery**: Resolves `ollama` via `PATH` and checks standard paths (`%LOCALAPPDATA%\Programs\Ollama`, `%PROGRAMFILES%\Ollama`, etc.).
3. **Silent Auto-Installation**: If absent, silently downloads `https://ollama.com/download/OllamaSetup.exe` and installs with `/SILENT /NORESTART`.
4. **Permanent PATH Persistence**:
   - Immediately injects the Ollama directory into the current process `PATH`.
   - Persists the directory into the Windows User Environment `Path` registry key via PowerShell `[Environment]::SetEnvironmentVariable('Path', ..., 'User')`.
5. **Daemon Launch & Polling**: Launches `ollama serve` in the background and polls until healthy.
6. **Live Model Provisioning**: Executes `ollama pull <model>` for the dynamically selected model tier.

### 5. Incremental Background Watcher & Interactive Chat Flow
- **Interactive Chat (`@agent update`)**: Dispatches the update command directly to the Master CLI, displaying live terminal progress to the user.
- **Incremental Background Watcher (`_startWatcher` / `_runDatabaseUpdate`)**:
  - Runs periodically in HugOS IDE to keep the multi-modal database and local models refreshed.
  - Spawns `cli.exe --update --db-path <dbPath>` at below-normal priority to protect interactive editing performance.
  - Pipes structured logs prefixed with `[Watcher]` to the `ModelFusion Server` output channel.

