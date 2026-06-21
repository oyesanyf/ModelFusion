# Custom AI-Powered IDE Project (Code-OSS Fork)

This folder contains the codebase and configuration for building our custom AI-powered IDE based on VS Code (Code - OSS).

## 🚀 High-Level Roadmap & Architecture

### 1. Core Repository Setup
* **Clone/Fork:** Core engine from the `microsoft/vscode` GitHub repository.
* **Dependencies:** Manage dependencies using Yarn (v1).
* **Local Compilation:** Execute `yarn watch` to compile the codebase and run it using `./scripts/code.sh` (Unix) or `.\scripts\code.bat` (Windows).

### 2. Branding & UI Customization
* **Branding:** Modify `product.json` to change the application name, publisher, themes, and branding assets.
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

## 🛠️ Next Steps

1. **Setup Initial Build Scripts:** Script files to automate repository cloning, dependency installation, and local compilation.
2. **Design AI Context Architecture:** Formulate the architecture for code parsing, embedding generation, and LLM communication.
