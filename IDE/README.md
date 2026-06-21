# Aether IDE — Custom AI-Powered Code-OSS Fork

Aether is an open-weights compound intelligence IDE built upon the open-source core of VS Code (Code - OSS).

## 🚀 High-Level Roadmap & Architecture

### 1. Core Repository Setup
* **Repository:** Custom fork of the `microsoft/vscode` repository.
* **Dependencies:** Managed via Yarn (v1).
* **Local Compilation:** Execute `yarn watch` to compile the codebase and run it using `./scripts/code.sh` (Unix) or `.\scripts\code.bat` (Windows).

### 2. Branding & UI Customization
* **Branding:** Modify `product.json` to change the application name to "Aether", publisher, and branding assets.
* **Package Config:** Update `package.json` to manage custom builds.
* **Workbench UI:** Edit components in `src/vs/workbench` to inject custom sidebars, AI panels, or inline ghost-text.

### 3. AI Engine Integration
* **Monaco Editor API:** Hook into `src/vs/editor` to access editor state, line tokens, and cursors.
* **Vector Indexing:** Parse codebases into vector embeddings (using Chroma/Qdrant) for project-wide semantic context.
* **API Middleware:** Connect to LLM backends (OpenAI, Anthropic, or local Ollama).

### 4. Marketplace Alternative
* **Registry:** Configure `product.json` to point the extensions gallery to the Open VSX Registry:
  ```json
  "extensionsGallery": {
    "serviceUrl": "https://open-vsx.org",
    "itemUrl": "https://open-vsx.org"
  }
  ```

---

## 📁 Project Directory Structure
* `setup_aether.ps1` — Automation script to clone VS Code, install dependencies, apply branding, and initialize compilation.
* `README.md` — Project roadmap and instructions.
