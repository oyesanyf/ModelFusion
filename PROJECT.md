# Project: Hugging Face Trending & Following Feed Integration & Resilient Release Synchronization

## Architecture
- **Stage 0 Feed Ingestion (`crates/core`, `crates/cli`, `crates/db`)**:
  - Live query to Hugging Face Trending API (`/api/trending?type=model&limit=100`, `/api/models?sort=trendingScore`) and 9 high-signal research orgs (`RecursiveSI`, `Qwen`, `deepseek-ai`, `google`, `meta-llama`, `mistralai`, `microsoft`, `allenai`, `nvidia`).
  - Idempotent SQLite `ALTER TABLE` migration adding `trending_score`, `feed_source`, `bandit_pulls`, and `bandit_reward` to `hf_models.db`.
  - Automatic task mapping across all 45+ Hugging Face tasks and 19 Browser categories.
- **Multi-Objective Pareto & UCB1 Bandit Selector (`crates/model_selection`)**:
  - Unified multi-objective scoring formula:
    $$S(\text{model}) = w_1 \cdot Q_{\text{task}} + w_2 \cdot \log_{10}(1 + \text{Downloads}) + w_3 \cdot V_{\text{trending}} + w_4 \cdot B_{\text{following}} + \alpha \sqrt{\frac{2 \ln N}{\max(1, n_i)}} - P_{\text{memory}}$$
  - Dynamic hardware sizing via `SystemMemory::detect_live()` (`free_ram_gb`, `free_vram_mb`).
  - Unblocked default active status for Recursive Flint (`flint:latest` / `RecursiveSI/flint`), Block Goose (`goose`), and RAPTOR (`raptor`) ($P_{\text{memory}} = 0.0$).
- **Multi-Client Discovery & UI Directives (`crates/cli`, `browser/ui`, `IDE/vscode/extensions/copilot`)**:
  - Master CLI: `--trending`, `--trending-models`, `--update --trending`, `GET /api/trending/models`, `POST /api/trending/sync`.
  - HugOS Browser: `@agent trending-models`, `/trending`, `#sidebar-trending-models`, `#tool_trending_models` under `Utilities & System` strictly A-Z sorted, clean headerless canvas with 9-action `.msg-action-bar`, long-form 8192-token responses.
  - HugOS IDE: commands & directives across all 5 distribution locations, direct inline file-writer with active editor/workspace auto-save.
  - Port 5000..5010 failover: verified with `service === "modelfusion"` on `/health`.
- **Distribution, Parity & Signing Pipeline**:
  - 18-way cryptographic CLI binary parity (`cli.exe`, `clibrowser.exe`, `cliide.exe`, `climcp.exe`).
  - Zero-touch environment variable invariance.
  - WiX MSI packaging (`HugOS.msi`, `HugOS_Browser.msi`), Authenticode digital signing with DigiCert timestamp, Microsoft WDSI submission, and GitHub release synchronization.

---

## Feature Inventory

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | SQLite Schema Evolution & Non-Destructive Migration | Add `trending_score: f64`, `feed_source: String`, `bandit_pulls: i64`, `bandit_reward: f64` to `models` table via idempotent `ALTER TABLE` migration | M1 | ORIGINAL_REQUEST §R1 |
| F2 | ModelMetrics Extended Persistence | Persist and deserialize trending, feed source, and bandit fields in `crates/db/src/models.rs` | M1 | ORIGINAL_REQUEST §R1 |
| F3 | Stage 0 Trending & Following Feed Ingestion | Live HTTP queries for public trending models and 9 followed research orgs inserted into `--update` and `--updatedb` | M1 | ORIGINAL_REQUEST §R1 |
| F4 | Pipeline Tag Task & Browser Category Mapping | Map all ingested models by `pipeline_tag` across 45+ Hugging Face tasks and 19 browser categories | M1 | ORIGINAL_REQUEST §R1 |
| F5 | Pareto Velocity & UCB1 Bandit Scoring | Incorporate $V_{\text{trending}}$, $B_{\text{following}}$, and $\alpha \sqrt{\frac{2\ln N}{\max(1, n_i)}}$ into `EnhancedModelSelector` and Pareto candidate objectives | M2 | ORIGINAL_REQUEST §R2 |
| F6 | Live Runtime Available Memory Invariant | Enforce `SystemMemory::detect_live()` (`free_ram_gb`, `free_vram_mb`) to apply $P_{\text{memory}}$ preventing OOM | M2 | ORIGINAL_REQUEST §R2 |
| F7 | Recursive Flint + Block Goose + RAPTOR Default Stack | Ensure Flint, Goose, and RAPTOR are never blocked, default active for Coding/Fusion ($P_{\text{memory}} = 0.0$), fixing `test_flint_dual_gate_law` | M2 | ORIGINAL_REQUEST §R2 |
| F8 | Master CLI Trending Flags & HTTP Endpoints | Support `--trending`, `--trending-models`, `--update --trending`, `GET /api/trending/models`, `POST /api/trending/sync` | M3 | ORIGINAL_REQUEST §R3 |
| F9 | Port 5000..5010 Resilient Failover | Discover active server port across ports 5000..5010 verifying `data.service === "modelfusion"` on `/health` | M3 | ORIGINAL_REQUEST §R3 |
| F10 | HugOS Browser Trending Discovery & A-Z Alphabetical Order | Add `@agent trending-models`, `/trending`, `#sidebar-trending-models`, `#tool_trending_models` in `Utilities & System` strictly A-Z sorted | M3 | ORIGINAL_REQUEST §R3 |
| F11 | Clean Canvas & Long-Form Response Stream | Headerless assistant canvas, preserved 9-action `.msg-action-bar`, and 8192-token long-form response generation | M3 | ORIGINAL_REQUEST §R3 |
| F12 | HugOS IDE Commands, Directives & 5-Location Mirroring | Support `/trending`, `@agent trending-models`, `/raptor`, `/goose`, `/flint` synced across all 5 IDE extension locations | M3 | ORIGINAL_REQUEST §R3 |
| F13 | IDE Inline File-Writer & Auto-Save | Extract `<userRequest>` to top of prompt, generate compilable code, and write directly to active editor/workspace files | M3 | ORIGINAL_REQUEST §R3 |
| F14 | Comprehensive E2E Test Suite | Create and verify `tests/test_hf_trending_and_following_feed.js`, verify `test_goose_19_categories_and_longform_canvas.js`, `test_flint_coding_fusion.js`, `test_alphabetical_menu.py`, `test_browser_menu_accordion_and_tool_count.js` | M3 | ORIGINAL_REQUEST §AC |
| F15 | 18-Way Cryptographic Binary Parity | Mirror release `cli.exe` across all 18 locations with identical SHA-256 hashes via `scripts/mirror_all.py` | M4 | Persistent Rules & R4 |
| F16 | Zero-Touch Environment Verification | Verify zero registry modifications in `HKCU\Environment` via `tests/test_no_env_variable_tampering.py` | M4 | Persistent Rules & R4 |
| F17 | WiX MSI Packaging & Authenticode Signing | Rebuild and sign `IDE/HugOS.msi` and `browser/HugOS_Browser.msi` with DigiCert timestamp | M4 | Persistent Rules & R4 |
| F18 | Microsoft WDSI Submissions & GitHub Release Sync | Submit all 6 targets to WDSI, commit/push to `origin/main`, and upload release assets | M4 | Persistent Rules & R4 |

---

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Stage 0 Trending & Following Activity Ingestion | F1, F2, F3, F4: `crates/db/src/schema.rs`, `models.rs`, migration logic, `crates/core/src/task_handler.rs` Stage 0 ingestion, task/category mapping, unit tests | None | **DONE** (`cargo test -p db` 7/7 pass, 16-thread race & conflict merge verified) |
| M2 | Multi-Objective Pareto + Contextual Bandit Velocity Scoring | F5, F6, F7: `crates/model_selection/src/lib.rs`, `pareto.rs`, `memory.rs`, UCB1 exploration, live memory rule, Flint/Goose/RAPTOR unblocked law & test fix | M1 | **DONE** (`cargo test -p model_selection` 38/38 pass, `cargo test -p db -p model_selection` 45/45 pass, gate passed) |
| M3 | Discovery Directives, Frontend/IDE Integration & E2E Testing | F8, F9, F10, F11, F12, F13, F14: CLI flags/endpoints, Browser UI A-Z ordering, IDE commands across 5 locations, inline file writer, `test_hf_trending_and_following_feed.js` | M1, M2 | **DONE** (CLI flags/endpoints, Browser UI A-Z menu & canvas, IDE commands across 5 locations, inline file writer, E2E test suites verified) |
| M4 | 18-Way Parity, WiX Packaging, WDSI Submissions & Release Sync | F15, F16, F17, F18: Release CLI compilation, 18-way mirror parity, zero-touch verification, MSI build/signing, WDSI submission, GitHub release sync | M1, M2, M3 | **DONE** (18-way parity 18/18 verified, zero-touch env verified, MSI build 415 Authenticode-signed, 6 WDSI targets submitted, release assets synced) |

---

## Interface Contracts

### 1. Database Schema & Migration (`crates/db`)
- `ALTER TABLE models ADD COLUMN trending_score REAL DEFAULT 0.0;`
- `ALTER TABLE models ADD COLUMN feed_source TEXT DEFAULT 'standard_hub';`
- `ALTER TABLE models ADD COLUMN bandit_pulls INTEGER DEFAULT 0;`
- `ALTER TABLE models ADD COLUMN bandit_reward REAL DEFAULT 0.0;`
- Idempotency: `PRAGMA table_info(models)` inspected prior to executing `ALTER TABLE`.

### 2. Multi-Objective Scoring Equation (`crates/model_selection`)
- Formula:
  $$S(\text{model}) = 0.25 \cdot Q_{\text{task}} + 0.15 \cdot \log_{10}(1 + \text{Downloads}) + 0.25 \cdot V_{\text{trending}} + 0.15 \cdot B_{\text{following}} + 0.20 \sqrt{\frac{2 \ln N}{\max(1, n_i)}} - P_{\text{memory}}$$
- Memory penalty $P_{\text{memory}}$:
  $$P_{\text{memory}} = \max\left(0, \frac{\text{Required GB} - \text{Free RAM GB}}{\text{Free RAM GB}}\right) \times 10.0$$
- Unblocked law: For `flint:latest`, `RecursiveSI/flint`, `goose`, `raptor`: $P_{\text{memory}} = 0.0$.

### 3. Master CLI HTTP API (`crates/cli`)
- `GET /api/trending/models`
  - Response: `{ "status": "ok", "count": N, "models": [ { "id": "...", "trending_score": 0.85, "feed_source": "trending", "pipeline_tag": "text-generation", "task": "text-generation", "browser_category": "NLP & Language", "pareto_score": 0.92 } ] }`
- `POST /api/trending/sync`
  - Response: `{ "status": "ok", "synced": N, "duration_ms": M }`

### 4. Browser UI (`browser/ui/index.html` & `app.js`)
- Sidebar Nav: `<li id="sidebar-trending-models" class="sidebar-nav-item"><span class="sidebar-icon">🔥</span><span class="sidebar-label">Trending Models</span></li>`
- Tool Item in `Utilities & System`: `<button id="tool_trending_models" class="tool-item">Trending Hub Models</button>` (alphabetically between `Optimize Database` and `Update Top Models`).
- Directives: `@agent trending-models` and `/trending`.

### 5. IDE Extension (`IDE/vscode/extensions/copilot/`)
- Command: `hugos.modelfusion.trendingModels`
- Chat Directives: `/trending`, `@agent trending-models`, `/raptor`, `/goose`, `/flint`.
- Distribution Sync: All 5 locations mirrored with identical hash.

---

## Code Layout

- `crates/db/`: `src/schema.rs`, `src/models.rs`, `src/lib.rs` (owned by M1)
- `crates/core/`: `src/task_handler.rs`, `src/fusion_engine/` (owned by M1)
- `crates/model_selection/`: `src/lib.rs`, `src/pareto.rs`, `src/memory.rs` (owned by M2)
- `crates/cli/`: `src/main.rs` (owned by M3)
- `browser/ui/`: `index.html`, `app.js`, `styles.css` (owned by M3)
- `IDE/vscode/extensions/copilot/`: `package.json`, `dist/extension.js` (owned by M3)
- `tests/`: `test_hf_trending_and_following_feed.js`, `test_flint_coding_fusion.js`, etc. (owned by M3 / Test Writer)
- Packaging & Release: `scripts/mirror_all.py`, `scripts/verify_18_way_parity.py`, `IDE/build_msi.ps1`, `scripts/submit_to_wdsi.py` (owned by M4)
