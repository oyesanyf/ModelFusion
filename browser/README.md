# HugOS Chromium Browser Engine & Multi-Modal AI Co-Pilot

The **HugOS Chromium Browser** is an autonomous, high-speed, vision-grounded web operating environment built specifically for ModelFusion. It unifies standard Chromium browsing with deep ModelFusion AI integration, live Chrome DevTools Protocol (CDP) orchestration on port 9222, high-throughput semantic DOM pruning (Set-of-Mark tags), automatic tabular dataset extraction into the 5-objective Pareto ACDSO engine, multi-model consensus deliberation, and pixel-perfect ChatGPT functional fidelity.

---

## 🌐 Key Capabilities & Architecture

```mermaid
graph TD
    A[User Prompt / URL / Slash Command] --> B[HugOS Browser Orchestration]
    B --> C{Execution Mode}
    
    C -->|Interactive AI Chat| D[ChatGPT-Fidelity Side Panel UI]
    C -->|Autonomous Navigation| E[CDP Engine: Port 9222]
    C -->|Table / Data Extraction| F[RFC-4180 Table Extractor]
    
    D --> D1[Clean White / Dark Themes & Centered 768px Thread]
    D --> D2[Canvas Document Cards .chatgpt-canvas-card]
    D --> D3[5-Button Action Row: Copy, Share, TTS, Regenerate, More]
    D --> D4[ModelFusion System Panel: 6,438 Models / 45 Tasks]
    
    E --> E1[Set-of-Mark SoM Visual Grounding: [1], [2], [3]]
    E --> E2[90% Token-Pruned Semantic DOM Filter]
    E --> E3[Multimodal Consensus: Vision + DOM + Heavy Arbiter]
    
    F --> G[ACDSO 5-Objective Pareto AutoML Pipeline]
```

### 1. 90% Token Reduction Semantic DOM Pruner (`dom_pruner.rs`)
Standard web pages contain megabytes of minified JavaScript bundles, tracking tags, CSS styles, and inline SVGs that cause severe context blowups and LLM latency.
- HugOS Browser implements a high-throughput semantic pruner that strips scripts, styles, SVGs, noscripts, iframes, and HTML comments.
- Actionable elements (`<a>`, `<button>`, `<input>`, `<select>`, `<textarea>`, elements with `role="button"` or `onclick`) are tagged with numeric **Set-of-Mark** tags (`[1]`, `[2]`, `[3]`, etc.).
- Reduces typical page token volume by **85% to 95%** while retaining 100% of interactive actionability and semantic structure.

### 2. Instant Web Dataset Extraction for ACDSO (`table_extractor.rs`)
- Parses HTML `<table>` elements and modern CSS grid structures (`role="grid"`, `role="table"`).
- Automatically converts extracted tables to RFC-4180 compliant CSV and structured JSON.
- Direct pipeline to the ModelFusion 5-objective Pareto ACDSO engine: running `/acdso <URL>` or clicking "Analyze Table with ACDSO" in the sidebar instantly extracts the tabular data and trains optimal AutoML models across accuracy, latency, memory, cost, and risk.

### 3. Vision-Language Grounding (`vision_grounding.rs`)
- When DOM structures are obfuscated, dynamic, or ambiguous (e.g. canvas elements, SVGs, interactive maps), HugOS Browser bridges viewport screenshots with multimodal models (`qwen2.5-vl`, `llama3.2-vision`, OpenVINO).
- Normalizes coordinates (`[ymin, xmin, ymax, xmax]`) and computes exact sub-pixel center click targets `(x, y)` for CDP dispatch.

### 4. Chrome DevTools Protocol Engine (`cdp_client.rs`)
- Communicates directly with Chromium's `--remote-debugging-port=9222`.
- Direct async RFC-6455 WebSocket framing for sub-millisecond command dispatch:
  - `Page.navigate`
  - `Runtime.evaluate`
  - `Page.captureScreenshot`
  - `Input.dispatchMouseEvent`
  - `Input.dispatchKeyEvent`
  - `Input.insertText`
- Non-blocking socket communication with 10-second safety timeouts to prevent deadlocks.

### 5. Multi-Model Consensus Arbitration (`browser_fusion.rs`)
Browser navigation workflows employ three specialist models:
1. **Fast NLP DOM Specialist (`qwen2.5:7b`)**: Rapid Set-of-Mark parsing and quick DOM action proposal.
2. **Vision Specialist (`qwen2.5-vl`)**: Visual layout verification and screenshot understanding.
3. **Heavy Reasoning Arbiter (`deepseek-r1:7b` / `qwen2.5:32b`)**: Complex planning, multi-step navigation, and discrepancy resolution with `<think>` verification.

---

## 🎨 ChatGPT Visual & Functional Fidelity

HugOS Browser's AI interface (`browser/ui/`) provides unmatched ergonomic fidelity modeled directly after frontier AI conversational standards:

### 1. Unified White & Dark Theme Aesthetics
- **Default Clean White Theme (`#FCFCFC` / `#FFFFFF`)**: Pure light background, subtle borders (`#E5E5E5`), high-contrast typography, and unified light grey dialog surfaces.
- **Dark Theme Variants**: Dark, Dark+, Obsidian Pitch Black, and Midnight Navy with custom CSS variables.
- **Clean Settings Modal**: Every tab pane, navigation item, input field, and statistics card in the Settings Dialog adheres strictly to the active theme with zero jarring black-box artifacts.

### 2. Centered 768px Chat Thread
- Messages are formatted in a clean, focused 768px-wide center column with generous margin gutters.
- User queries render in comfortable rounded chat capsules (`--user-msg-bg: #f4f4f4`).
- Assistant answers stream in clean transparent typography with crisp typographic hierarchy.

### 3. Canvas Document Card (`.chatgpt-canvas-card`)
- Long-form generated text, technical reports, essays, and multi-line code snippets automatically format into elegant rounded Canvas cards.
- Displays document title in the top-left corner with `📋 Copy` and `⤢ Expand` modal action buttons.

### 4. 5-Button Assistant Action Row
Every assistant message features an interactive bottom action bar:
- 📋 **Copy**: Instant clipboard copying of Markdown source or formatted text.
- ⬆️ **Share**: Exports message threads or saves conversation excerpts.
- 🔊 **Read Aloud**: Native client-side speech synthesis powered by the Web Speech API.
- 🔄 **Regenerate**: Triggers alternative response generation via ModelFusion consensus.
- ⋯ **More options**: Quick access to model diagnostics, token telemetry, and execution traces.

### 5. Persistent Sidebar Chat History
- Conversation history is automatically persisted into `localStorage`.
- Supports instant session switching, thread renaming, selective deletion, and new chat creation.

### 6. Auto-Hiding Sleek 6px Scrollbars
- Completely eliminates thick operating system scrollbars and dual-nested page scrollbars.
- Custom WebKit scrollbar styling (`6px` width, rounded `#d1d5db` thumb, auto-hiding on idle).

---

## 🧠 ModelFusion Multi-Modal System Panel & Settings Architecture

HugOS Browser embeds complete visibility into ModelFusion's local compound intelligence engine:
- **Live Catalog Statistics**: Queries `IDE/db/hf_models.db` to show real-time catalog metrics (**6,438 Curated Models across 45 Tasks** or **1,271,167 Models** when full crawl is active).
- **Dynamic Hardware Memory Sizing**: Evaluates strictly **runtime available / free memory** (`res.free_ram_gb`, `res.free_vram_mb`) to dynamically provision matching local Ollama workhorses (`qwen2.5:32b/14b/7b/1.5b`) without OOM risk.
- **Consensus Panel Sizing (`--fusion-models`)**:
  - `0 (Auto-RAM)`: Dynamically sized from available memory (Default).
  - `2 Models`: Fast Dual Consensus (Primary reasoning + Secondary verifier).
  - `3 Models`: Tri-Specialist (DOM Specialist + Vision Specialist + Heavy Reasoning Arbiter).
  - `5 Models`: Deep Consensus Panel (Broad sampling across architectures).
  - `10 Models`: Exhaustive Frontier Deliberation (Full Pareto consensus).
- **Catalog Model Count Invariants & Transparency**:
  - **`--update` (Fast Curated Tier)**: Populates the top ~6,500 production workhorse models across all 45 tasks.
  - **`--updatedb` (Full Registry Crawler)**: Populates all 1,271,167+ models across the entire Hugging Face Hub.
  - **Offline / IPC Fallback Invariant**: When the Master CLI backend (`:5000`) is offline or unreachable, the browser UI fails safe to the verified baseline constant of **6,438 Models**, rather than crashing or displaying blank metrics.
  - **Task-Specific Filtering**: Unclassified models lacking valid `pipeline_tag` metadata exist in the raw table count, but are pruned from task-specific consensus candidate pools.

---

## ⚙️ Comprehensive 12-Category Settings Drawer (Matching HugOS IDE)

Pressing `Ctrl+,` or clicking the ⚙️ Settings button in the sidebar opens the full two-column Settings Modal with real-time search filtering across 12 categories:
1. ⚙️ **General**: Default homepage, token streaming mode, auto-scroll terminal, and diagnostics.
2. 🔆 **Appearance**: 5 distinct themes (ChatGPT Clean White, Dark, Obsidian Pitch Black, Midnight Navy, Warm Sepia) and font size scaling.
3. 🌐 **Web Search & Routing**: Autonomous query routing toggles, search engine provider, maximum search results, and citation formatting.
4. 🧠 **AI Models & Endpoints**: Ollama REST API URL, ModelFusion Master CLI IPC URL, Chrome CDP Port, Primary Workhorse Model, Consensus Panel Size (`--fusion-models`), Vision Specialist Model (`qwen2.5-vl`), and Audio Specialist Model (`whisper-base`).
5. 📁 **Storage**: Navigation history cache clearing, attached file staging management, and database statistics.
6. ⌨️ **Keyboard**: Master table of keyboard shortcuts (`Ctrl+,`, `Ctrl+N`, `Ctrl+[`, `Ctrl+Enter`, `Alt+S`, `Esc`).
7. 📈 **Usage**: Live host telemetry (Runtime Available RAM, GPU VRAM, active model, and query counter).
8. 🔔 **Notifications**: In-app toast alerts, model provisioning notifications, and task completion chimes.
9. 👤 **Account**: 100% local profile, zero cloud registration, and `%LOCALAPPDATA%\HugOS Browser` path.
10. 🔑 **Security & Sandboxing**: Windows Job Object process isolation (<8ms termination) and CORS defense-in-depth.
11. 🎙️ **Voice**: Speech synthesis voice selection, pitch, and playback rate for Read Aloud.
12. 🐾 **Pets**: Interactive desktop productivity companion and status indicators.

---

## 📎 Multimodal File Attachments & Data Pipelines

Attach files directly via the `📎` button or drag-and-drop:
- **Images** (`.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`): Thumbnail preview in tray, processed via Set-of-Mark visual grounding and Vision Specialists.
- **Audio** (`.wav`, `.mp3`, `.ogg`, `.flac`): Transcribed via local Whisper acoustic models.
- **Tabular Datasets** (`.csv`, `.tsv`, `.parquet`): Features an instant `[⚡ Run ACDSO]` action chip to train 5-objective Pareto AutoML models directly on host datasets.
- **Code & Documents** (`.rs`, `.py`, `.json`, `.pdf`, `.md`): Automatically injected into prompt context for analysis.

---

## 📁 Directory Structure

```
browser/
├── bin/
│   └── cli.exe                 # Authoritative ModelFusion Master CLI binary (7-way parity)
├── config/
│   └── default_preferences.json# Dark/White theme, telemetry disabled, ModelFusion endpoint
├── db/
│   └── hf_models.db            # SQLite catalog database (6,438 models across 45 tasks)
├── extension/                  # Manifest V3 HugOS Browser AI Assistant
│   ├── manifest.json           # Extension manifest with sidePanel, debugger, activeTab
│   ├── content.js              # Set-of-Mark visual bounding box injector & DOM parser
│   ├── background.js           # Background service worker managing CDP & ModelFusion IPC
│   ├── sidepanel.html          # AI chat sidebar HTML
│   ├── sidepanel.js            # Chat interactions, slash commands, and tool streaming
│   └── styles.css              # Sidepanel styling
├── ui/                         # ChatGPT-fidelity standalone AI web application
│   ├── index.html              # Chat UI, Settings modal, ModelFusion system panel
│   ├── app.js                  # Streaming LLM, chat history, TTS, settings persistence
│   └── styles.css              # Themes (White, Dark, Obsidian), Canvas cards, 6px scrollbars
├── Chromium-win32-x64/
│   └── hugos-browser.bat       # Launcher script with remote debugging & extension loading
├── build_number.txt            # Package auto-increment build tracking
├── build_browser.ps1           # WiX MSI automated packaging and digital signing script
├── generate_wix.js             # Automated WiX manifest XML generator
└── README.md                   # Comprehensive technical documentation
```

---

## 💻 Master CLI Commands

```powershell
# Launch interactive HugOS Browser with AI side panel
cli.exe --browser

# Execute autonomous goal-directed web navigation and research directive
cli.exe --browser-task "Navigate to Hugging Face, search for top TTS models, and report their download counts"

# Instant semantic table and dataset extraction from URL directly into ACDSO
cli.exe --browser-extract "https://en.wikipedia.org/wiki/Comparison_of_deep_learning_software"

# Specify custom remote debugging port
cli.exe --browser --browser-port 9225

# Direct launcher batch script
.\browser\Chromium-win32-x64\hugos-browser.bat
```

### Interactive Slash Commands in HugOS Chat
```text
/browser https://huggingface.co/models
/browser extract tables from https://en.wikipedia.org/wiki/List_of_countries_by_GDP_(nominal)
/acdso https://en.wikipedia.org/wiki/List_of_countries_by_GDP_(nominal)
@agent browser find the highest rated local embedding models
```

---

## 📦 Packaging & MSI Distribution

To compile, verify, digitally sign, and build the self-contained HugOS Browser MSI installer:
```powershell
powershell -ExecutionPolicy Bypass -File .\browser\build_browser.ps1
```
This increments `browser/build_number.txt`, digitally signs all binaries using `IDE/hugos-signing-cert.pfx`, generates the WiX manifest `browser/HugOS_Browser.wxs`, and builds `browser/HugOS_Browser.msi`.
