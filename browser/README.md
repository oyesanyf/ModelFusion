# HugOS Chromium Browser Engine & Multi-Modal AI Co-Pilot

The **HugOS Chromium Browser** is an autonomous, high-speed, vision-grounded web operating environment built for ModelFusion. It combines standard Chromium browsing with deep ModelFusion AI integration, live Chrome DevTools Protocol (CDP) orchestration, semantic DOM pruning (Set-of-Mark tags), automatic tabular dataset extraction into the 5-objective Pareto ACDSO engine, and multi-model consensus arbitration.

---

## Key Capabilities & Architecture

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

## Directory Structure

```
browser/
├── bin/
│   └── cli.exe                 # Authoritative ModelFusion Master CLI binary
├── config/
│   └── default_preferences.json# Dark theme, telemetry disabled, ModelFusion endpoint
├── db/
│   └── hf_models.db            # Hardlink/copy of SQLite multi-modal model catalog
├── extension/                  # Manifest V3 HugOS Browser AI Assistant
│   ├── manifest.json           # Extension manifest with sidePanel, debugger, activeTab
│   ├── content.js              # Set-of-Mark visual bounding box injector & DOM parser
│   ├── background.js           # Background service worker managing CDP & ModelFusion IPC
│   ├── sidepanel.html          # Full AI chat sidebar matching HugOS IDE dark theme
│   ├── sidepanel.js            # Chat interactions, slash commands, and tool streaming
│   └── styles.css              # Dark-mode styling matching HugOS IDE
├── Chromium-win32-x64/
│   └── hugos-browser.bat       # Launcher script with remote debugging & extension loading
├── build_number.txt            # Package auto-increment build tracking
├── build_browser.ps1           # WiX MSI automated packaging and digital signing script
└── README.md                   # Technical documentation
```

---

## Master CLI Commands

```powershell
# Launch interactive HugOS Browser with AI side panel
cli.exe --browser

# Execute autonomous goal-directed web task
cli.exe --browser-task "Navigate to Hugging Face, search for top TTS models, and report their download counts"

# Instant semantic table and dataset extraction from URL
cli.exe --browser-extract "https://en.wikipedia.org/wiki/Comparison_of_deep_learning_software"

# Specify custom remote debugging port
cli.exe --browser --browser-port 9223

# Interactive Slash Commands in HugOS Chat:
/browser https://huggingface.co/models
/acdso https://en.wikipedia.org/wiki/List_of_countries_by_GDP_(nominal)
@agent browser find the highest rated local embedding models
```

---

## Packaging & MSI Distribution

To compile, verify, digitally sign, and build the HugOS Browser MSI installer:
```powershell
powershell -ExecutionPolicy Bypass -File .\browser\build_browser.ps1
```
This increments `browser/build_number.txt`, digitally signs all binaries using `IDE/hugos-signing-cert.pfx`, generates the WiX manifest `browser/HugOS_Browser.wxs`, and builds `browser/HugOS_Browser.msi`.
