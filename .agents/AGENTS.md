# Project Rules & User Preferences

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
- **Master CLI Source**: `crates/cli` in `d:\harfile\ModelFusion` compiles to `target/release/cli.exe`. HugOS IDE directly invokes this binary.
- **4-Way Binary Parity**: Always maintain identical SHA-256 hashes across `target/release/cli.exe`, `IDE/bin/cli.exe`, `IDE/VSCode-win32-x64/bin/cli.exe`, and `%LOCALAPPDATA%/HugOS IDE/bin/cli.exe`.
- **Database Update Commands (`--update` vs `--updatedb`)**:
  - `--update` (Fast Curated Engine): Ingests top ~6,500 production workhorse models across all 45 tasks and provisions optimal local Ollama hardware model. Used for daily runs, chat `@agent update`, and IDE background watcher. Syntax: `cli.exe --update --db-path "IDE/db/hf_models.db"`.
  - `--updatedb` (Full Registry Crawler): Cursor-paginated crawler that ingests ALL 2M+ models from Hugging Face Hub ("whether junk or not") in 1,000-model batches. Optional `--max-models <N>` caps total ingestion. Syntax: `cli.exe --updatedb --db-path "IDE/db/hf_models.db"`.
- **All Models & All Modalities**: The update pipeline covers all 45+ Hugging Face tasks (Vision, Audio, NLP, Multimodal, Tabular, RL, Legal, Security, etc.) for over 2 million models, not just coding models.
- **Runtime Available Memory Rule**: NEVER allocate models against total physical RAM. Always evaluate runtime free/available RAM (`res.free_ram_gb`) and free VRAM (`res.free_vram_mb`) to avoid OOM from concurrent workloads.
- **Ollama Engine Setup**: Must auto-detect, auto-install silently (`OllamaSetup.exe /SILENT /NORESTART`), persist Ollama path to Windows User PATH registry, start `ollama serve`, and pull the hardware-appropriate model.
- **Incremental Background Watcher**: `_runDatabaseUpdate()` periodically invokes `cli.exe --update --db-path <dbPath>` at below-normal priority with logs piped to the `ModelFusion Server` channel.
