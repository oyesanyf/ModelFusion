# HugOS IDE — Build & Feature Documentation

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Build Guide (Step-by-Step)](#build-guide-step-by-step)
- [Chat Slash Commands](#chat-slash-commands)
- [Inline Code Apply (Accept / Reject)](#inline-code-apply)
- [OpenEvolve Code Evolution](#openevolve-code-evolution)
- [ModelFusion Settings](#modelfusion-settings)
- [MSI Packaging](#msi-packaging)

---

## Architecture Overview

HugOS IDE is a custom fork of VS Code with an integrated AI-powered code assistant called **ModelFusion**. It runs entirely locally — no cloud login required.

```
┌─────────────────────────────────────────────────────┐
│                   HugOS IDE (Electron)               │
│  ┌─────────────┐  ┌──────────────────────────────┐  │
│  │  Chat Panel  │  │  Editor + Inline Diff        │  │
│  │  (Copilot    │  │  ✅ Accept / ❌ Reject       │  │
│  │   framework) │  │  Green/Red gutter markers    │  │
│  └──────┬───────┘  └──────────────────────────────┘  │
│         │                                            │
│  ┌──────▼──────────────────────────────────────────┐ │
│  │  ModelFusion Extension (copilot/dist/extension.js)│
│  │  - ModelFusionLMProvider (language model)        │ │
│  │  - InlineDiffManager (accept/reject UI)         │ │
│  │  - Slash command handler (/evolve, /security)   │ │
│  └──────┬──────────────────────────────────────────┘ │
│         │ HTTP :5000                                  │
│  ┌──────▼──────────────────────────────────────────┐ │
│  │  cli.exe (Rust API Server)                       │ │
│  │  - /orchestrate endpoint                         │ │
│  │  - Multi-model selection (multi_objective)       │ │
│  │  - Semaphore-based concurrency control           │ │
│  └──────┬──────────────────────────────────────────┘ │
│         │                                            │
│  ┌──────▼─────────┐  ┌────────────────────────────┐ │
│  │  Ollama (LLM)  │  │  OpenVINO (optional)       │ │
│  │  qwen2.5:7b    │  │  HuggingFace models        │ │
│  └────────────────┘  └────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **VS Code fork** | `IDE/vscode/` | Custom-branded Code-OSS with ModelFusion patches |
| **Copilot extension** | `IDE/vscode/extensions/copilot/` | Chat integration, slash commands, inline diff |
| **Rust CLI** | `crates/cli/` | API server, model orchestration, GPU detection |
| **Patches** | `IDE/patches/` | Brand assets, product.json, icons |
| **MSI builder** | `IDE/build_msi.ps1` | Windows installer packaging |

---

## Build Guide (Step-by-Step)

### Prerequisites

- **Node.js** v20+ (v24 recommended)
- **Python** 3.10+ (for build scripts)
- **Rust** (stable, for cli.exe)
- **Ollama** (for local LLM inference)
- **Windows SDK** (for signtool.exe)
- **WiX Toolset v4+** (for MSI packaging)
- **Git LFS** (large file storage for binary assets)

### Step 1: Clone the Repository

```bash
git clone https://github.com/oyesanyf/ModelFusion.git
cd ModelFusion
git submodule update --init --recursive
```

### Step 2: Build the Rust CLI

```bash
cargo build --release
# Output: target/release/cli.exe
```

This produces `cli.exe` — the local API server that handles model orchestration.

### Step 3: Set Up the VS Code Fork

```bash
cd IDE/vscode

# Install dependencies
yarn install

# Build the VS Code fork for Windows x64
npx gulp vscode-win32-x64
```

This produces `IDE/VSCode-win32-x64/` — the source-built IDE with HugOS branding from `product.json` (`applicationName: "hugos"`).

> **IMPORTANT**: The source build produces `HugOS.exe` natively. Never rename `Code.exe` to `HugOS.exe`.

### Step 4: Build the Copilot Extension

```bash
cd IDE/vscode/extensions/copilot
npm run build
```

This compiles the TypeScript ModelFusion provider into `dist/extension.js` (~18 MB). Key source files:

| File | Purpose |
|------|---------|
| `byokContribution.ts` | Registers ModelFusionLMProvider with the chat framework |
| `modelFusionProvider.ts` | Core provider: slash commands, inline diff, model orchestration |
| `evolve/inlineDiff.ts` | Cursor-style Accept/Reject diff decorations |

### Step 5: Copy CLI into the Build

```bash
# From the ModelFusion root:
cp target/release/cli.exe IDE/VSCode-win32-x64/bin/cli.exe
```

### Step 6: Install Ollama

```bash
# Download and install Ollama from https://ollama.ai
ollama pull qwen2.5:7b
```

### Step 7: Build the MSI Installer

```powershell
cd IDE
powershell -ExecutionPolicy Bypass -File build_msi.ps1
```

This:
1. Verifies `VSCode-win32-x64/` exists (source build output)
2. Copies `cli.exe` into the packaging directory
3. Signs all `.exe` and `.dll` files with a self-signed certificate
4. Generates a WiX manifest (`HugOS.wxs`)
5. Compiles the MSI with `dotnet tool run wix build`
6. Signs the final MSI

Output: `IDE/HugOS.msi`

### Step 8: Launch

```bash
# From source build:
IDE/VSCode-win32-x64/HugOS.exe

# Or install the MSI and launch from Start Menu
```

---

## Chat Slash Commands

Type these in the HugOS chat panel. All commands are processed locally.

### Core Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/evolve` | Iterative code evolution using OpenEvolve engine | `/evolve` (with a file open) |
| `/evolve --iterations 10` | Set iteration count | `/evolve -n 10` |
| `/security` | Run ATLAS security analysis and threat detection | `/security` |
| `/stats` | Display inference statistics and metrics | `/stats` |

### Model Selection Commands

| Command | Description |
|---------|-------------|
| `/ollama` | Force Ollama backend for inference |
| `/openvino` | Use Intel OpenVINO optimized inference |
| `/gpu` | Force GPU-accelerated inference |
| `/cpu` | Force CPU-only inference |
| `/model <name>` | Select a specific model (e.g., `/model Qwen/Qwen2.5-7B-Instruct`) |
| `/budget <N>` | Set execution cost/time budget (e.g., `/budget 1.5`) |

### Multi-Model Commands

| Command | Description |
|---------|-------------|
| `/fusion` | Enable multi-model fusion for higher quality |
| `/cot` | Enable chain-of-thought reasoning |
| `/score` | Score and evaluate response quality |
| `/judge` | Use LLM-as-judge evaluation |
| `/plan` | Generate execution plan before running |

### Data Science Commands

| Command | Description |
|---------|-------------|
| `/jupyter` | Launch Jupyter notebook mode |
| `/dataanalyst` | Activate data analyst mode for CSV/Excel |
| `/datascience` | Enable data science pipeline with ML training |
| `/predict` | Predictive mode for proactive suggestions |

### Analysis Commands

| Command | Description |
|---------|-------------|
| `/sentiment` | Run sentiment analysis on text |
| `/ner` | Named entity recognition extraction |
| `/summary` | Generate concise summary of text or code |
| `/question` | Run question-answering on context |
| `/semantic-analysis` | Deep semantic analysis |
| `/pe-header-extraction` | Extract and analyze PE headers from executables |

### Utility Commands

| Command | Description |
|---------|-------------|
| `/context <text>` | Add custom context to the prompt |
| `/context-auto` | Auto-include relevant workspace context |
| `/verbose` | Enable verbose output with detailed logs |
| `/debug` | Enable debug mode with diagnostics |
| `/update` | Update model database from HuggingFace |
| `/clearcache` | Clear inference and model cache |
| `/export-pdf` | Export response as PDF report |
| `/model-recommendations` | Get AI-powered model recommendations |

---

## Inline Code Apply

**Every code response** from the chat triggers an inline diff with Accept / Reject:

### How It Works

1. You ask the chat to modify code (e.g., "add error handling to this function")
2. The model responds with a code block
3. The code is **applied as an unsaved edit** to your active editor
4. **Visual indicators** appear:
   - 🟢 **Green gutter** — added/changed lines
   - 🔴 **Red gutter** — removed lines
   - 🔵 **Blue border** — overview of all changes
   - **Header banner** — "✅ Accept (Ctrl+Shift+Y) · ❌ Reject (Ctrl+Shift+N)"
5. A **notification toast** and **status bar item** also offer Accept/Reject

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+Y` | **Accept** changes (saves the file) |
| `Ctrl+Shift+N` | **Reject** changes (reverts to original) |

### Behavior

- Only one pending edit at a time — new code replaces the previous pending edit
- Empty/new files also get inline diff — you can Accept/Reject proposed initial content
- The best matching code block is selected when the response contains multiple blocks

---

## OpenEvolve Code Evolution

`/evolve` is an iterative code improvement engine that makes multiple passes over your code.

### How It Works

```
┌──────────────────┐     ┌──────────────────┐
│  Your Code File  │────►│  LLM Generates   │
│  (active editor) │     │  Evaluator.py    │
└──────────────────┘     └────────┬─────────┘
                                  │
                         ┌────────▼─────────┐
                         │  OpenEvolve      │
                         │  Iterates N times│
                         │  (Python engine) │
                         └────────┬─────────┘
                                  │
                         ┌────────▼─────────┐
                         │  Evolved Code    │
                         │  + Inline Diff   │
                         │  Accept / Reject │
                         └──────────────────┘
```

### Two Modes

#### 1. OpenEvolve Python Pipeline (for `.py` files)
When OpenEvolve is installed, `/evolve` on Python files:
1. **Step 1**: Uses the LLM to auto-generate an `evaluator.py` (test harness)
2. **Step 2**: Spawns `python -m openevolve.cli <program.py> <evaluator.py> --iterations N`
3. **Step 3**: Shows the evolved code as an inline diff

Requires: `pip install openevolve` or `openevolve-run.py` in the project.

#### 2. Built-in Iterative Engine (all languages)
When OpenEvolve is not available, `/evolve` uses a built-in engine:

Each iteration focuses on a different aspect:
1. 🐛 **Bug fixes** — null pointers, type errors, logic errors
2. ⚡ **Performance** — reduce complexity, efficient data structures
3. 🛡️ **Error handling** — input validation, edge cases
4. 🏗️ **Refactoring** — clean code, SOLID principles
5. 🔒 **Security** — injection risks, sanitization
6. 📝 **Documentation** — comments, structure, formatting
7. ✨ **Polish** — imports, dead code removal
8. 🚀 **Deep optimization** — hot paths, allocations

After all iterations, the best evolved code is shown as an inline diff.

### Settings

Configure in **Settings → HugOS → ModelFusion → OpenEvolve**:

| Setting | Default | Description |
|---------|---------|-------------|
| `hugos.modelfusion.openevolve.enabled` | `true` | Enable/disable /evolve |
| `hugos.modelfusion.openevolve.iterations` | `5` | Number of evolution iterations |
| `hugos.modelfusion.openevolve.strategy` | `auto` | `auto`, `openevolve`, or `builtin` |
| `hugos.modelfusion.openevolve.autoApply` | `true` | Auto-apply best result to editor |
| `hugos.modelfusion.openevolve.showProgress` | `true` | Show iteration progress in chat |
| `hugos.modelfusion.openevolve.focuses` | `[]` | Custom focus areas (overrides defaults) |

### Usage Examples

```
/evolve                    # Evolve with default 5 iterations
/evolve --iterations 10    # Evolve with 10 iterations
/evolve -n 3               # Short form for 3 iterations
```

---

## ModelFusion Settings

Access via **File → Preferences → Settings → HugOS → ModelFusion**

### General

| Setting | Default | Description |
|---------|---------|-------------|
| `hugos.modelfusion.localBackend` | `ollama` | Backend: `ollama`, `openvino`, or `transformers` |
| `hugos.modelfusion.device` | `auto` | Device: `auto`, `gpu`, or `cpu` |
| `hugos.modelfusion.budget` | `1.0` | Execution cost/time budget (1-10) |
| `hugos.modelfusion.fusion` | `false` | Enable multi-model fusion |
| `hugos.modelfusion.fusionModels` | `3` | Number of models for fusion |
| `hugos.modelfusion.selectionStrategy` | `multi_objective` | Model selection strategy |
| `hugos.modelfusion.fusionMode` | `multi-model` | Fusion mode |

### Model Overrides

| Setting | Default | Description |
|---------|---------|-------------|
| `hugos.modelfusion.ollamaModel` | `""` | Specific Ollama model name (blank = auto) |
| `hugos.modelfusion.openvinoModel` | `""` | Specific OpenVINO model path |
| `hugos.modelfusion.inferenceModel` | `""` | Specific Transformers model |

---

## MSI Packaging

### Build Process

```powershell
# From IDE/ directory:
powershell -ExecutionPolicy Bypass -File build_msi.ps1
```

### What the Script Does

1. **Verifies** `VSCode-win32-x64/` exists (source build output)
2. **Copies** `cli.exe` from `target/release/` into `VSCode-win32-x64/bin/`
3. **Creates** a self-signed code signing certificate (`hugos-signing-cert.pfx`)
4. **Signs** all 126+ `.exe` and `.dll` files in the packaging directory
5. **Generates** WiX source manifest (`HugOS.wxs`) with all files enumerated
6. **Compiles** MSI using WiX Toolset v4+ (`dotnet tool run wix build`)
7. **Signs** the final `HugOS.msi`

### Install Location

The MSI installs to: `C:\Users\<user>\AppData\Local\HugOS IDE\`

### Required Runtime

- **Ollama** must be installed and running for chat to work
- Pull a model: `ollama pull qwen2.5:7b`

---

## Key Patches Applied to VS Code

These patches differentiate HugOS IDE from stock VS Code:

### 1. Workbench: Vendor Whitelist Fix (`52e286f9`)
**File**: `src/vs/workbench/contrib/chat/common/languageModels.ts`
- Removed vendor whitelist that only allowed `copilot` provider
- Set `isDefault: true` for `modelfusion` vendor when no `copilot` vendor present
- Enables local models to work as the default chat model

### 2. Extension Host: Default Model Vendor (`extensionHostProcess.js`)
- `getDefaultLanguageModel()` accepts `modelfusion` vendor alongside `copilot`
- Without this, chat always shows "Language model unavailable"

### 3. ModelFusion Provider: Default Location Flag
**File**: `extensions/copilot/src/extension/byok/vscode-node/modelFusionProvider.ts`
- Added `isDefaultForLocation: { panel: true, inline: true, terminal: true }`
- Required by `getDefaultLanguageModel()` to recognize the model

### 4. Branding
**File**: `product.json`
- `applicationName: "hugos"`
- `nameShort: "HugOS"`
- `nameLong: "HugOS IDE"`
- Custom icons in `resources/win32/`, `resources/darwin/`, `resources/linux/`
