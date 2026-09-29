# 🔌 ModelFusion Universal MCP Server

The **ModelFusion Model Context Protocol (MCP) Server** is a high-performance, local AI integration bridge that exposes ModelFusion's entire compound intelligence ecosystem—**103 specialized tools**, ACDSO Pareto AutoML, 45+ multi-modal tasks, PE binary forensics, and ReST-RL autonomous reasoning—over standard JSON-RPC 2.0 stdio (`protocolVersion: "2024-11-05"`).

Connecting ModelFusion as an MCP server equips any frontier desktop AI environment (**Claude Desktop**, **Cursor**, **Google Antigravity**, **VS Code**, or **Zed**) with local offline capabilities, zero cloud API fees, and direct access to 2M+ open-weight models.

---

## 🌟 Why ModelFusion MCP?

* **100% Free & Offline-First**: No OpenAI/Anthropic/Gemini cloud credits or API keys required. Runs entirely on local Ollama, OpenVINO, and ONNX runtimes.
* **Dynamic Hardware Sizing**: Automatically discovers CPU cores, available runtime RAM, and free VRAM to allocate the ideal model tier (`qwen2.5:32b`, `14b`, `7b`, `3b`, `1.5b`).
* **Universal Multi-Modal Mesh**: Solves 45+ Hugging Face tasks across Vision (detection, OCR, segmentation, depth), Audio (Whisper ASR, TTS, VAD), NLP, Code, and Tabular AutoML.
* **103 Standardized MCP Tools**: Complete coverage of code review, security audits, PE forensics, Pareto AutoML, and universal CLI execution (`execute`).
* **Instant Compatibility**: Drops directly into `claude_desktop_config.json`, `cursor_mcp.json`, and `antigravity_mcp.json`.

---

## 📁 Folder Structure

```text
mcp/
├── README.md                      # This primary MCP manual
├── modelfusion_mcp.json           # Canonical MCP manifest and capability specifications
├── tools_reference.md             # Exhaustive reference for all 103 tools (schemas & examples)
├── configs/
│   ├── claude_desktop_config.json # Claude Desktop configuration snippet
│   ├── cursor_mcp.json            # Cursor IDE MCP configuration snippet
│   ├── antigravity_mcp.json       # Google Antigravity / AGY MCP snippet
│   ├── vscode_continue_config.json# VS Code Continue / Roo-Code configuration
│   └── zed_settings.json          # Zed Editor context server configuration
├── scripts/
│   ├── run_mcp.bat                # Windows batch launcher (resolves binary automatically)
│   ├── run_mcp.ps1                # PowerShell launcher with environment checks
│   └── run_mcp.sh                 # Unix/Linux/macOS bash launcher
└── client/
    └── test_mcp_connection.py     # Automated JSON-RPC test client (verifies handshake & tools)
```

---

## ⚡ Quick Start: 30-Second Verification

Before configuring desktop clients, you can verify your local ModelFusion MCP Server in one command:

```powershell
# Run the automated MCP verification client
python mcp\client\test_mcp_connection.py
```

Expected output:
```text
[*] Testing ModelFusion MCP Server via: target\release\cli.exe
 -> Sending 'initialize' request...
 <- Received initialize response: Server='ModelFusion MCP Server', Version='0.1.0'
 -> Sending 'tools/list' request...
 <- Successfully discovered 103 ModelFusion MCP tools:
    - execute: Execute the ModelFusion CLI with ANY combination of flags...
    - quick_answer: Fast direct answer for general knowledge questions...
    - orchestrate: Run the full ModelFusion orchestration pipeline...
    - analyze_file: Analyze, review, or process a specific file...
    ... and 91 more tools.

 -> Calling tool 'get_system_info'...
 <- Successfully received tool response (1 content blocks)
[SUCCESS] ModelFusion MCP Stdio Server is 100% operational and compliant with MCP 2024-11-05 spec!
```

---

## 🔌 Client Connection Guides

### 1. Claude Desktop

#### Windows
Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "modelfusion": {
      "command": "cmd.exe",
      "args": [
        "/c",
        "d:\\harfile\\ModelFusion\\mcp\\scripts\\run_mcp.bat"
      ],
      "env": {
        "LOCAL_OLLAMA_ENDPOINT": "http://127.0.0.1:11434"
      }
    }
  }
}
```

#### macOS / Linux
Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "modelfusion": {
      "command": "/bin/bash",
      "args": [
        "/path/to/ModelFusion/mcp/scripts/run_mcp.sh"
      ]
    }
  }
}
```

---

### 2. Cursor IDE

In Cursor, navigate to **Settings** $\rightarrow$ **Features** $\rightarrow$ **MCP Servers** $\rightarrow$ **Add New MCP Server**:
* **Name**: `modelfusion`
* **Type**: `command`
* **Command**: `d:\harfile\ModelFusion\target\release\cli.exe --mcp --db-path d:\harfile\ModelFusion\IDE\db\hf_models.db`

Or paste into `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "modelfusion": {
      "command": "d:\\harfile\\ModelFusion\\target\\release\\cli.exe",
      "args": ["--mcp", "--db-path", "d:\\harfile\\ModelFusion\\IDE\\db\\hf_models.db"]
    }
  }
}
```

---

### 3. Google Antigravity / Gemini CLI

Add to your workspace or global Antigravity configuration (`antigravity_mcp.json` or `.gemini/settings.json`):

```json
{
  "mcpServers": {
    "modelfusion": {
      "command": "d:\\harfile\\ModelFusion\\mcp\\scripts\\run_mcp.bat",
      "args": [],
      "description": "ModelFusion Universal Compound Intelligence MCP Server",
      "enabled": true
    }
  }
}
```

---

### 4. VS Code (Continue / Roo-Code)

Add to `.continue/config.json`:

```json
{
  "experimental": {
    "modelContextProtocolServers": [
      {
        "transport": {
          "type": "stdio",
          "command": "d:\\harfile\\ModelFusion\\mcp\\scripts\\run_mcp.bat",
          "args": []
        }
      }
    ]
  }
}
```

---

### 5. Zed Editor

Add to `settings.json`:

```json
{
  "context_servers": {
    "modelfusion": {
      "command": {
        "path": "d:\\harfile\\ModelFusion\\mcp\\scripts\\run_mcp.bat",
        "args": []
      }
    }
  }
}
```

---

## 🛠️ Key Tools at a Glance

| Category | Primary Tools | Capabilities |
| :--- | :--- | :--- |
| **Core Execution** | `execute`, `orchestrate`, `quick_answer` | Run any CLI flag combination, full multi-model consensus deliberation, sub-2s direct Q&A. |
| **Code & Files** | `analyze_file`, `analyze_folder`, `code_task` | Vulnerability scanning, code review, architectural project auditing, LLM-as-a-Judge. |
| **NLP Tasks** | `nlp_task`, `translation`, `summarize` | 20+ specialized tasks (NER, sentiment, summarization, coreference, grammar). |
| **AutoML & Data** | `data_science`, `acdso`, `timeseries` | 5-objective Pareto causal AutoML, feature engineering, correlation matrices, notebook generation. |
| **Security & Forensics** | `security_analysis`, `pe_header_extraction` | Static Windows PE binary header forensics, phishing/spam/PII detection, code security. |
| **Multi-Modal AI** | `multimodal_task`, `vision`, `asr`, `tts` | Zero-shot image classification, object detection, Whisper ASR speech-to-text, text-to-speech. |
| **Dense Search** | `semantic_search`, `arxiv`, `search` | In-memory HyDE semantic search, live arXiv scientific paper retrieval, live web grounding. |
| **Telemetry** | `get_system_info`, `get_database_stats` | Real-time hardware telemetry (RAM, VRAM, GPU cores), SQLite model registry stats. |

👉 *For full parameter schemas, input options, and examples for every tool, see the [Exhaustive Tools Reference Manual](tools_reference.md).*

---

## 📜 License
Apache-2.0. Built with pride by the HugOS & ModelFusion Teams.
