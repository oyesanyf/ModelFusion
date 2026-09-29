# ModelFusion MCP Server • Tools Reference Manual

The **ModelFusion Model Context Protocol (MCP) Server** exposes **173 specialized tools** over standard JSON-RPC 2.0 stdio (`protocolVersion: "2024-11-05"`). These tools connect frontier desktop assistants (Claude Desktop, Cursor, Google Antigravity, VS Code, Zed) to ModelFusion's local multi-modal engine, ACDSO Pareto AutoML, ReST-RL preemption, and 2M+ model catalog.

---

## 📑 Table of Contents
1. [Core Orchestration (3 Tools)](#1-core-orchestration)
2. [Code Intelligence (21 Tools)](#2-code-intelligence)
3. [Autonomous Browser & Research (11 Tools)](#3-autonomous-browser--research)
4. [Autonomous Agents & Reasoning (15 Tools)](#4-autonomous-agents--reasoning)
5. [NLP & Linguistics (30 Tools)](#5-nlp--linguistics)
6. [Computer Vision (25 Tools)](#6-computer-vision)
7. [Audio & Speech (15 Tools)](#7-audio--speech)
8. [Multi-Modal & Domain Sciences (16 Tools)](#8-multi-modal--domain-sciences)
9. [ACDSO AutoML & Tabular Data (15 Tools)](#9-acdso-automl--tabular-data)
10. [CyberSecurity & Binary Forensics (16 Tools)](#10-cybersecurity--binary-forensics)
11. [System Telemetry & Lifecycle (6 Tools)](#11-system-telemetry--lifecycle)

---

## 1. Core Orchestration

### `execute`
* **Label**: Universal CLI Execute 🖥️
* **Category**: Core Orchestration
* **Description**: Execute ModelFusion CLI with ANY combination of flags
* **CLI Equivalent**: `cli.exe`
* **Input Schema**:
  ```json
  {
    "properties": {
      "args": {
        "description": "Array of CLI arguments (e.g. ['--prompt', 'explain recursion', '--gpu'])",
        "items": {
          "type": "string"
        },
        "type": "array"
      }
    },
    "required": [
      "args"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "execute",
      "arguments": {
        "args": [
          "--prompt",
          "sample argument"
        ]
      }
    }
  }
  ```

---

### `quick_answer`
* **Label**: Quick Answer ⚡
* **Category**: Core Orchestration
* **Description**: Fast direct answer for general knowledge questions (non-coding) via Ollama in 2-3s
* **CLI Equivalent**: `@agent quick`
* **Input Schema**:
  ```json
  {
    "properties": {
      "model": {
        "description": "Ollama model (default: qwen2.5:3b)",
        "type": "string"
      },
      "question": {
        "description": "The question to answer",
        "type": "string"
      }
    },
    "required": [
      "question"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "quick_answer",
      "arguments": {
        "question": "sample_value"
      }
    }
  }
  ```

---

### `orchestrate`
* **Label**: Full Orchestrator 🎼
* **Category**: Core Orchestration
* **Description**: Full pipeline: task detection → model selection → multi-model deliberation → execution
* **CLI Equivalent**: `@agent orchestrate`
* **Input Schema**:
  ```json
  {
    "properties": {
      "budget": {
        "description": "Model parameter budget in billions",
        "type": "number"
      },
      "cpu": {
        "type": "boolean"
      },
      "fusion": {
        "description": "Enable multi-model consensus",
        "type": "boolean"
      },
      "gpu": {
        "type": "boolean"
      },
      "prompt": {
        "description": "Task prompt or instruction",
        "type": "string"
      },
      "selection_strategy": {
        "description": "Selection strategy",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "orchestrate",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

## 2. Code Intelligence

### `analyze_file`
* **Label**: Analyze File 📄
* **Category**: Code Intelligence
* **Description**: Analyze, review, or process a specific file with ModelFusion
* **CLI Equivalent**: `@agent file`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Absolute path to file",
        "type": "string"
      },
      "prompt": {
        "description": "Instructions or questions about file",
        "type": "string"
      }
    },
    "required": [
      "file",
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "analyze_file",
      "arguments": {
        "file": "src/main.rs",
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `analyze_folder`
* **Label**: Analyze Folder 📁
* **Category**: Code Intelligence
* **Description**: Analyze, audit, or review an entire directory/project
* **CLI Equivalent**: `@agent folder`
* **Input Schema**:
  ```json
  {
    "properties": {
      "folder": {
        "description": "Absolute path to folder",
        "type": "string"
      },
      "prompt": {
        "description": "Instructions or review goals",
        "type": "string"
      }
    },
    "required": [
      "folder",
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 5,
    "method": "tools/call",
    "params": {
      "name": "analyze_folder",
      "arguments": {
        "folder": "sample_value",
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `code`
* **Label**: Code Intelligence 💻
* **Category**: Code Intelligence
* **Description**: Code generation, vulnerability scanning & refactoring
* **CLI Equivalent**: `@agent code`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Code Intelligence",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 103,
    "method": "tools/call",
    "params": {
      "name": "code",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `code_gen`
* **Label**: Code Generation ⚡
* **Category**: Code Intelligence
* **Description**: Multi-language function and module synthesis
* **CLI Equivalent**: `@agent code-gen`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Code Generation",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 104,
    "method": "tools/call",
    "params": {
      "name": "code_gen",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `infill`
* **Label**: Code Infilling 🧩
* **Category**: Code Intelligence
* **Description**: Fill-in-the-middle code completion from context
* **CLI Equivalent**: `@agent infill`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Code Infilling",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 105,
    "method": "tools/call",
    "params": {
      "name": "infill",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `code_review`
* **Label**: Code Review 🧐
* **Category**: Code Intelligence
* **Description**: Automated code review for maintainability & bugs
* **CLI Equivalent**: `@agent code-review`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Code Review",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 106,
    "method": "tools/call",
    "params": {
      "name": "code_review",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `refactor`
* **Label**: Code Refactoring 🔨
* **Category**: Code Intelligence
* **Description**: Restructure code without altering functional behavior
* **CLI Equivalent**: `@agent refactor`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Code Refactoring",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 107,
    "method": "tools/call",
    "params": {
      "name": "refactor",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `test_gen`
* **Label**: Unit Test Gen 🧪
* **Category**: Code Intelligence
* **Description**: Generate high-coverage unit tests and assertions
* **CLI Equivalent**: `@agent test-gen`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Unit Test Gen",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 108,
    "method": "tools/call",
    "params": {
      "name": "test_gen",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `graph_index`
* **Label**: Code Graph Index 🕸️
* **Category**: Code Intelligence
* **Description**: Extract AST relationships & call graphs
* **CLI Equivalent**: `@agent graph-index`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Code Graph Index",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 109,
    "method": "tools/call",
    "params": {
      "name": "graph_index",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `ast_parse`
* **Label**: AST Tree Parse 🌲
* **Category**: Code Intelligence
* **Description**: Parse source into concrete syntax trees and tokens
* **CLI Equivalent**: `@agent ast-parse`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for AST Tree Parse",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 111,
    "method": "tools/call",
    "params": {
      "name": "ast_parse",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `docstring`
* **Label**: Docstring Gen 📝
* **Category**: Code Intelligence
* **Description**: Synthesize Google/Sphinx/Rustdoc documentation comments
* **CLI Equivalent**: `@agent docstring`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Docstring Gen",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 112,
    "method": "tools/call",
    "params": {
      "name": "docstring",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `type_infer`
* **Label**: Type Inference 🏷️
* **Category**: Code Intelligence
* **Description**: Infer strong static types for dynamic languages
* **CLI Equivalent**: `@agent type-infer`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Type Inference",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 113,
    "method": "tools/call",
    "params": {
      "name": "type_infer",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `sql`
* **Label**: SQL Generator 🗄️
* **Category**: Code Intelligence
* **Description**: Translate natural language queries into optimized SQL
* **CLI Equivalent**: `@agent sql`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for SQL Generator",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 114,
    "method": "tools/call",
    "params": {
      "name": "sql",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `regex`
* **Label**: Regex Builder 🔍
* **Category**: Code Intelligence
* **Description**: Construct and explain complex regular expressions
* **CLI Equivalent**: `@agent regex`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Regex Builder",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 115,
    "method": "tools/call",
    "params": {
      "name": "regex",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `git_commit`
* **Label**: Git Commit Message 📦
* **Category**: Code Intelligence
* **Description**: Generate Conventional Commit messages from diffs
* **CLI Equivalent**: `@agent git-commit`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Git Commit Message",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 116,
    "method": "tools/call",
    "params": {
      "name": "git_commit",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `lint_fix`
* **Label**: Automated Lint Fix 🪛
* **Category**: Code Intelligence
* **Description**: Auto-repair linting, formatting, and stylistic warnings
* **CLI Equivalent**: `@agent lint-fix`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Automated Lint Fix",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 117,
    "method": "tools/call",
    "params": {
      "name": "lint_fix",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `perf_audit`
* **Label**: Performance Profiler ⏱️
* **Category**: Code Intelligence
* **Description**: Algorithmic complexity Big-O analysis and bottlenecks
* **CLI Equivalent**: `@agent perf-audit`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Performance Profiler",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 118,
    "method": "tools/call",
    "params": {
      "name": "perf_audit",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `deps`
* **Label**: Dependency Analysis 📦
* **Category**: Code Intelligence
* **Description**: Detect obsolete or vulnerable third-party dependencies
* **CLI Equivalent**: `@agent deps`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Dependency Analysis",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 119,
    "method": "tools/call",
    "params": {
      "name": "deps",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `api_docs`
* **Label**: API Doc Generator 📚
* **Category**: Code Intelligence
* **Description**: Generate OpenAPI / Swagger specifications from code
* **CLI Equivalent**: `@agent api-docs`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for API Doc Generator",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 120,
    "method": "tools/call",
    "params": {
      "name": "api_docs",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `code_translate`
* **Label**: Code Translation 🔀
* **Category**: Code Intelligence
* **Description**: Transpile code between Python, Rust, TS, Go, C++
* **CLI Equivalent**: `@agent code-translate`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Code Translation",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 121,
    "method": "tools/call",
    "params": {
      "name": "code_translate",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `dockerfile`
* **Label**: Dockerfile Gen 🐳
* **Category**: Code Intelligence
* **Description**: Generate multi-stage secure container Dockerfiles
* **CLI Equivalent**: `@agent dockerfile`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Dockerfile Gen",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 122,
    "method": "tools/call",
    "params": {
      "name": "dockerfile",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

## 3. Autonomous Browser & Research

### `browser`
* **Label**: Browser Automation 🌐
* **Category**: Autonomous Browser & Research
* **Description**: Navigate, interact, and automate web workflows
* **CLI Equivalent**: `@agent browser`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Browser Automation",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 6,
    "method": "tools/call",
    "params": {
      "name": "browser",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `browser_deep_research`
* **Label**: Deep Research 🔍
* **Category**: Autonomous Browser & Research
* **Description**: Autonomous multi-step web research & synthesis
* **CLI Equivalent**: `@agent browser deep research on`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Deep Research",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 8,
    "method": "tools/call",
    "params": {
      "name": "browser_deep_research",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `arxiv`
* **Label**: arXiv Papers 📚
* **Category**: Autonomous Browser & Research
* **Description**: Direct search of arXiv scientific preprints and research papers
* **CLI Equivalent**: `@agent arxiv`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for arXiv Papers",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 9,
    "method": "tools/call",
    "params": {
      "name": "arxiv",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `markers`
* **Label**: Visual Element Markers 🎯
* **Category**: Autonomous Browser & Research
* **Description**: Numeric visual element grounding with 90% token reduction
* **CLI Equivalent**: `@agent markers`
* **Input Schema**:
  ```json
  {
    "properties": {},
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 10,
    "method": "tools/call",
    "params": {
      "name": "markers",
      "arguments": {}
    }
  }
  ```

---

### `som`
* **Label**: Visual Element Markers 🎯
* **Category**: Autonomous Browser & Research
* **Description**: Numeric visual element grounding with 90% token reduction
* **CLI Equivalent**: `@agent markers`
* **Input Schema**:
  ```json
  {
    "properties": {},
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 11,
    "method": "tools/call",
    "params": {
      "name": "som",
      "arguments": {}
    }
  }
  ```

---

### `summarize`
* **Label**: Summarize Page 📑
* **Category**: Autonomous Browser & Research
* **Description**: Extract and summarize active web page content
* **CLI Equivalent**: `@agent summarize`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Summarize Page",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 12,
    "method": "tools/call",
    "params": {
      "name": "summarize",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `search`
* **Label**: Web Search Grounding 🔎
* **Category**: Autonomous Browser & Research
* **Description**: Live web search grounding with verified citations
* **CLI Equivalent**: `@agent search`
* **Input Schema**:
  ```json
  {
    "properties": {
      "query": {
        "description": "Search query",
        "type": "string"
      }
    },
    "required": [
      "query"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 13,
    "method": "tools/call",
    "params": {
      "name": "search",
      "arguments": {
        "query": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `web_agent`
* **Label**: Web Search Agent 🌐
* **Category**: Autonomous Browser & Research
* **Description**: Search internet, build inverted index, and correlate results with LLM
* **CLI Equivalent**: `@agent web-agent`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Web Search Agent",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 14,
    "method": "tools/call",
    "params": {
      "name": "web_agent",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `search_index`
* **Label**: Search Index 📑
* **Category**: Autonomous Browser & Research
* **Description**: Build and query in-memory inverted search index over web data
* **CLI Equivalent**: `@agent search-index`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Search Index",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 15,
    "method": "tools/call",
    "params": {
      "name": "search_index",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `browser_navigate`
* **Label**: Browser Navigate 🧭
* **Category**: Autonomous Browser & Research
* **Description**: Direct viewport navigation to specific URL
* **CLI Equivalent**: `@agent browser navigate`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Browser Navigate",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 16,
    "method": "tools/call",
    "params": {
      "name": "browser_navigate",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `browser_extract`
* **Label**: DOM Extraction 📋
* **Category**: Autonomous Browser & Research
* **Description**: Extract structured clean text and interactive nodes from DOM
* **CLI Equivalent**: `@agent browser extract`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for DOM Extraction",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 17,
    "method": "tools/call",
    "params": {
      "name": "browser_extract",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

## 4. Autonomous Agents & Reasoning

### `goal`
* **Label**: Autonomous Goal 🎯
* **Category**: Autonomous Agents & Reasoning
* **Description**: Multi-turn autonomous goal-directed agent loop
* **CLI Equivalent**: `@agent goal`
* **Input Schema**:
  ```json
  {
    "properties": {
      "goal": {
        "description": "High-level goal description",
        "type": "string"
      }
    },
    "required": [
      "goal"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 154,
    "method": "tools/call",
    "params": {
      "name": "goal",
      "arguments": {
        "goal": "sample_value"
      }
    }
  }
  ```

---

### `plan`
* **Label**: Planning Engine 📋
* **Category**: Autonomous Agents & Reasoning
* **Description**: Deconstruct complex tasks into executable steps
* **CLI Equivalent**: `@agent plan`
* **Input Schema**:
  ```json
  {
    "properties": {
      "task": {
        "description": "Task description to plan",
        "type": "string"
      }
    },
    "required": [
      "task"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 155,
    "method": "tools/call",
    "params": {
      "name": "plan",
      "arguments": {
        "task": "text-generation"
      }
    }
  }
  ```

---

### `grill_me`
* **Label**: Grill Me Mode 🔥
* **Category**: Autonomous Agents & Reasoning
* **Description**: Adversarial requirements interview & stress-testing
* **CLI Equivalent**: `@agent grill-me`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Grill Me Mode",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 156,
    "method": "tools/call",
    "params": {
      "name": "grill_me",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `boost`
* **Label**: Reasoning Boost 🚀
* **Category**: Autonomous Agents & Reasoning
* **Description**: Deep multi-perspective reasoning & rigorous verification
* **CLI Equivalent**: `@agent boost`
* **Input Schema**:
  ```json
  {
    "properties": {
      "prompt": {
        "description": "Complex prompt or query",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 157,
    "method": "tools/call",
    "params": {
      "name": "boost",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `agentic_loop`
* **Label**: Agentic Loop 🔄
* **Category**: Autonomous Agents & Reasoning
* **Description**: Recursive auto-chaining for up to 256k tokens
* **CLI Equivalent**: `@agent agentic-loop`
* **Input Schema**:
  ```json
  {
    "properties": {
      "prompt": {
        "description": "Prompt for large generation",
        "type": "string"
      },
      "target_tokens": {
        "description": "Target token budget (up to 262144)",
        "type": "integer"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 158,
    "method": "tools/call",
    "params": {
      "name": "agentic_loop",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `explain`
* **Label**: Explain Concept 💡
* **Category**: Autonomous Agents & Reasoning
* **Description**: Step-by-step reasoning and deep conceptual explanation
* **CLI Equivalent**: `@agent explain`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Explain Concept",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 159,
    "method": "tools/call",
    "params": {
      "name": "explain",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `cot`
* **Label**: Chain-of-Thought 🧠
* **Category**: Autonomous Agents & Reasoning
* **Description**: Explicit chain-of-thought derivation with evidence checks
* **CLI Equivalent**: `@agent cot`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Chain-of-Thought",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 160,
    "method": "tools/call",
    "params": {
      "name": "cot",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `critic`
* **Label**: Self-Critique 🧐
* **Category**: Autonomous Agents & Reasoning
* **Description**: Adversarially evaluate draft solutions for edge case flaws
* **CLI Equivalent**: `@agent critic`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Self-Critique",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 161,
    "method": "tools/call",
    "params": {
      "name": "critic",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `synthesize`
* **Label**: Synthesis Engine 🪢
* **Category**: Autonomous Agents & Reasoning
* **Description**: Synthesize multiple divergent viewpoints into one consensus
* **CLI Equivalent**: `@agent synthesize`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Synthesis Engine",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 162,
    "method": "tools/call",
    "params": {
      "name": "synthesize",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `decompose`
* **Label**: Decomposition 🧩
* **Category**: Autonomous Agents & Reasoning
* **Description**: Break massive requirements into atomic subtasks
* **CLI Equivalent**: `@agent decompose`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Decomposition",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 163,
    "method": "tools/call",
    "params": {
      "name": "decompose",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `delegate`
* **Label**: Subagent Delegate 🤝
* **Category**: Autonomous Agents & Reasoning
* **Description**: Dispatch specialized micro-tasks to background subagents
* **CLI Equivalent**: `@agent delegate`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Subagent Delegate",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 164,
    "method": "tools/call",
    "params": {
      "name": "delegate",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `verify`
* **Label**: Step Verification ✅
* **Category**: Autonomous Agents & Reasoning
* **Description**: Formal verification of outputs against input constraints
* **CLI Equivalent**: `@agent verify`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Step Verification",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 165,
    "method": "tools/call",
    "params": {
      "name": "verify",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `backtrack`
* **Label**: Backtrack Rollback ↩️
* **Category**: Autonomous Agents & Reasoning
* **Description**: Rollback erroneous reasoning branches to previous valid state
* **CLI Equivalent**: `@agent backtrack`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Backtrack Rollback",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 166,
    "method": "tools/call",
    "params": {
      "name": "backtrack",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `reflection`
* **Label**: Error Reflection 🪞
* **Category**: Autonomous Agents & Reasoning
* **Description**: Analyze execution failure traces and synthesize self-corrections
* **CLI Equivalent**: `@agent reflection`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Error Reflection",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 167,
    "method": "tools/call",
    "params": {
      "name": "reflection",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `adversarial`
* **Label**: Adversarial Test ⚔️
* **Category**: Autonomous Agents & Reasoning
* **Description**: Subject assumptions and architecture to worst-case stresses
* **CLI Equivalent**: `@agent adversarial`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Adversarial Test",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 168,
    "method": "tools/call",
    "params": {
      "name": "adversarial",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

## 5. NLP & Linguistics

### `nlp`
* **Label**: NLP Pipeline 📝
* **Category**: NLP & Linguistics
* **Description**: Sentiment, NER, translation, and text classification
* **CLI Equivalent**: `@agent nlp`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for NLP Pipeline",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 73,
    "method": "tools/call",
    "params": {
      "name": "nlp",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `text_generation`
* **Label**: Text Generation ✍️
* **Category**: NLP & Linguistics
* **Description**: Open-ended causal text completion and synthesis
* **CLI Equivalent**: `@agent text-generation`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Text Generation",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 74,
    "method": "tools/call",
    "params": {
      "name": "text_generation",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `text2text`
* **Label**: Text-to-Text 🔄
* **Category**: NLP & Linguistics
* **Description**: Seq2Seq transformation, rewriting, and standardization
* **CLI Equivalent**: `@agent text2text`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Text-to-Text",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 75,
    "method": "tools/call",
    "params": {
      "name": "text2text",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `translation`
* **Label**: Translation 🌐
* **Category**: NLP & Linguistics
* **Description**: Neural machine translation across 200+ languages
* **CLI Equivalent**: `@agent translation`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Translation",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 76,
    "method": "tools/call",
    "params": {
      "name": "translation",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `question_answering`
* **Label**: Question Answering 💬
* **Category**: NLP & Linguistics
* **Description**: Extractive and generative reading comprehension
* **CLI Equivalent**: `@agent question-answering`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Question Answering",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 77,
    "method": "tools/call",
    "params": {
      "name": "question_answering",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `table_qa`
* **Label**: Table QA 📊
* **Category**: NLP & Linguistics
* **Description**: Direct natural language querying over tabular structures
* **CLI Equivalent**: `@agent table-qa`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Table QA",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 78,
    "method": "tools/call",
    "params": {
      "name": "table_qa",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `zero_shot`
* **Label**: Zero-Shot Text 🎯
* **Category**: NLP & Linguistics
* **Description**: Categorize text into arbitrary candidate label sets
* **CLI Equivalent**: `@agent zero-shot`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Zero-Shot Text",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 79,
    "method": "tools/call",
    "params": {
      "name": "zero_shot",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `text_classification`
* **Label**: Text Classify 🏷️
* **Category**: NLP & Linguistics
* **Description**: Fine-tuned intent, category, and sentiment labels
* **CLI Equivalent**: `@agent text-classification`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Text Classify",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 80,
    "method": "tools/call",
    "params": {
      "name": "text_classification",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `token_classification`
* **Label**: Token Classify 🔠
* **Category**: NLP & Linguistics
* **Description**: Token-level entity, POS tag, and boundary classification
* **CLI Equivalent**: `@agent token-classification`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Token Classify",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 81,
    "method": "tools/call",
    "params": {
      "name": "token_classification",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `sentence_similarity`
* **Label**: Sentence Similarity 🔗
* **Category**: NLP & Linguistics
* **Description**: Bi-encoder semantic similarity scoring and ranking
* **CLI Equivalent**: `@agent sentence-similarity`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Sentence Similarity",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 82,
    "method": "tools/call",
    "params": {
      "name": "sentence_similarity",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `conversational`
* **Label**: Chat Assistant 🗣️
* **Category**: NLP & Linguistics
* **Description**: Multi-turn persona-grounded conversational agent
* **CLI Equivalent**: `@agent conversational`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Chat Assistant",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 83,
    "method": "tools/call",
    "params": {
      "name": "conversational",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `fill_mask`
* **Label**: Masked LM Fill 🎭
* **Category**: NLP & Linguistics
* **Description**: Predict masked tokens via bidirectional context
* **CLI Equivalent**: `@agent fill-mask`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Masked LM Fill",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 84,
    "method": "tools/call",
    "params": {
      "name": "fill_mask",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `multiple_choice`
* **Label**: Multiple Choice 🔘
* **Category**: NLP & Linguistics
* **Description**: Select most plausible completion from candidate options
* **CLI Equivalent**: `@agent multiple-choice`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Multiple Choice",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 85,
    "method": "tools/call",
    "params": {
      "name": "multiple_choice",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `sentiment`
* **Label**: Sentiment Analysis ❤️
* **Category**: NLP & Linguistics
* **Description**: Positive, negative, neutral, and emotional intensity
* **CLI Equivalent**: `@agent sentiment`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Sentiment Analysis",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 86,
    "method": "tools/call",
    "params": {
      "name": "sentiment",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `summarize_text`
* **Label**: Text Summarize 📜
* **Category**: NLP & Linguistics
* **Description**: Abstractive and extractive multi-paragraph summarization
* **CLI Equivalent**: `@agent summarize-text`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Text Summarize",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 87,
    "method": "tools/call",
    "params": {
      "name": "summarize_text",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `grammar`
* **Label**: Grammar Check ✍️
* **Category**: NLP & Linguistics
* **Description**: Orthographic, syntactic, and stylistic error correction
* **CLI Equivalent**: `@agent grammar`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Grammar Check",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 88,
    "method": "tools/call",
    "params": {
      "name": "grammar",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `paraphrase`
* **Label**: Paraphraser 🔁
* **Category**: NLP & Linguistics
* **Description**: Alternative phrasing preserving core semantic intent
* **CLI Equivalent**: `@agent paraphrase`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Paraphraser",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 89,
    "method": "tools/call",
    "params": {
      "name": "paraphrase",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `ner`
* **Label**: Named Entity Rec 🏷️
* **Category**: NLP & Linguistics
* **Description**: Extract names, locations, dates, and organizations
* **CLI Equivalent**: `@agent ner`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Named Entity Rec",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 90,
    "method": "tools/call",
    "params": {
      "name": "ner",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `keywords`
* **Label**: Keyword Extractor 🔑
* **Category**: NLP & Linguistics
* **Description**: KeyBERT and TF-IDF keyphrase significance extraction
* **CLI Equivalent**: `@agent keywords`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Keyword Extractor",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 91,
    "method": "tools/call",
    "params": {
      "name": "keywords",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `semantic_search`
* **Label**: Semantic Search 🔎
* **Category**: NLP & Linguistics
* **Description**: Dense vector retrieval over embedded corpus documents
* **CLI Equivalent**: `@agent semantic-search`
* **Input Schema**:
  ```json
  {
    "properties": {
      "action": {
        "description": "'search' to query, 'add' to index documents, 'demo' to run demo",
        "type": "string"
      },
      "documents_path": {
        "description": "Path to documents to add (for 'add' action)",
        "type": "string"
      },
      "hyde_variants": {
        "description": "Generate multiple HyDE variants",
        "type": "boolean"
      },
      "query": {
        "description": "Search query (for 'search' action)",
        "type": "string"
      },
      "top_k": {
        "description": "Number of results (default: 5)",
        "type": "integer"
      },
      "use_hyde": {
        "description": "Use interactive HyDE refinement",
        "type": "boolean"
      }
    },
    "required": [
      "action"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 92,
    "method": "tools/call",
    "params": {
      "name": "semantic_search",
      "arguments": {
        "action": "sample_value"
      }
    }
  }
  ```

---

### `hallucination_eval`
* **Label**: Hallucination Check 🛡️
* **Category**: NLP & Linguistics
* **Description**: Cross-reference text claims against source ground truth
* **CLI Equivalent**: `@agent hallucination-eval`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Hallucination Check",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 93,
    "method": "tools/call",
    "params": {
      "name": "hallucination_eval",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `prompt_expand`
* **Label**: Prompt Expander 🪄
* **Category**: NLP & Linguistics
* **Description**: Enrich sparse prompts with context and constraints
* **CLI Equivalent**: `@agent prompt-expand`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Prompt Expander",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 94,
    "method": "tools/call",
    "params": {
      "name": "prompt_expand",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `chain_of_thought`
* **Label**: Chain-of-Thought 🧠
* **Category**: NLP & Linguistics
* **Description**: Step-by-step rationalized deductive derivation
* **CLI Equivalent**: `@agent chain-of-thought`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Chain-of-Thought",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 95,
    "method": "tools/call",
    "params": {
      "name": "chain_of_thought",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `toxicity`
* **Label**: Toxicity Detection ⚠️
* **Category**: NLP & Linguistics
* **Description**: Identify profanity, harassment, hate speech, and threats
* **CLI Equivalent**: `@agent toxicity`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Toxicity Detection",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 96,
    "method": "tools/call",
    "params": {
      "name": "toxicity",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `intent`
* **Label**: Intent Recognition 🎯
* **Category**: NLP & Linguistics
* **Description**: Identify actionable user objective and routing class
* **CLI Equivalent**: `@agent intent`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Intent Recognition",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 97,
    "method": "tools/call",
    "params": {
      "name": "intent",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `relation_extract`
* **Label**: Relation Extraction 🕸️
* **Category**: NLP & Linguistics
* **Description**: Extract subject-predicate-object knowledge triples
* **CLI Equivalent**: `@agent relation-extract`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Relation Extraction",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 98,
    "method": "tools/call",
    "params": {
      "name": "relation_extract",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `topic_model`
* **Label**: Topic Modeling 🗂️
* **Category**: NLP & Linguistics
* **Description**: Unsupervised discovery of semantic themes across docs
* **CLI Equivalent**: `@agent topic-model`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Topic Modeling",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 99,
    "method": "tools/call",
    "params": {
      "name": "topic_model",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `simplify`
* **Label**: Text Simplifier 💡
* **Category**: NLP & Linguistics
* **Description**: Convert dense academic jargon into plain English
* **CLI Equivalent**: `@agent simplify`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Text Simplifier",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 100,
    "method": "tools/call",
    "params": {
      "name": "simplify",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `lang_detect`
* **Label**: Language Detection 🔤
* **Category**: NLP & Linguistics
* **Description**: Determine ISO language code from raw text snippet
* **CLI Equivalent**: `@agent lang-detect`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Language Detection",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 101,
    "method": "tools/call",
    "params": {
      "name": "lang_detect",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `citation`
* **Label**: Citation Generator 📖
* **Category**: NLP & Linguistics
* **Description**: Generate BibTeX, APA, IEEE, and Chicago references
* **CLI Equivalent**: `@agent citation`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Citation Generator",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 102,
    "method": "tools/call",
    "params": {
      "name": "citation",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

## 6. Computer Vision

### `vision`
* **Label**: Vision Analysis 👁️
* **Category**: Computer Vision
* **Description**: Object detection, OCR, and visual Q&A
* **CLI Equivalent**: `@agent vision`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Vision Analysis",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 33,
    "method": "tools/call",
    "params": {
      "name": "vision",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `image_classification`
* **Label**: Image Classify 🏷️
* **Category**: Computer Vision
* **Description**: Zero-shot vision classification across open models
* **CLI Equivalent**: `@agent image-classification`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Image Classify",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 34,
    "method": "tools/call",
    "params": {
      "name": "image_classification",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `object_detection`
* **Label**: Object Detection 📦
* **Category**: Computer Vision
* **Description**: Visual bounding boxes and multi-target detection
* **CLI Equivalent**: `@agent object-detection`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Object Detection",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 35,
    "method": "tools/call",
    "params": {
      "name": "object_detection",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `vqa`
* **Label**: Visual QA ❓
* **Category**: Computer Vision
* **Description**: Direct Q&A on attached images & visual assets
* **CLI Equivalent**: `@agent vqa`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Visual QA",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 36,
    "method": "tools/call",
    "params": {
      "name": "vqa",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `image_segmentation`
* **Label**: Image Segment ✂️
* **Category**: Computer Vision
* **Description**: Semantic and instance pixel-level segmentation masks
* **CLI Equivalent**: `@agent image-segmentation`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Image Segment",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 37,
    "method": "tools/call",
    "params": {
      "name": "image_segmentation",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `text_to_image`
* **Label**: Text to Image 🎨
* **Category**: Computer Vision
* **Description**: High-fidelity diffusion image generation from prompt
* **CLI Equivalent**: `@agent text-to-image`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Text to Image",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 38,
    "method": "tools/call",
    "params": {
      "name": "text_to_image",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `image_to_text`
* **Label**: Image Captioning 📝
* **Category**: Computer Vision
* **Description**: Dense visual captioning and narrative extraction
* **CLI Equivalent**: `@agent image-to-text`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Image Captioning",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 39,
    "method": "tools/call",
    "params": {
      "name": "image_to_text",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `image_to_image`
* **Label**: Image to Image 🖼️
* **Category**: Computer Vision
* **Description**: Style transfer, super-resolution, and image refinement
* **CLI Equivalent**: `@agent image-to-image`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Image to Image",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 40,
    "method": "tools/call",
    "params": {
      "name": "image_to_image",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `depth_estimation`
* **Label**: Depth Estimation 📏
* **Category**: Computer Vision
* **Description**: Monocular 3D depth map and surface normal estimation
* **CLI Equivalent**: `@agent depth-estimation`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Depth Estimation",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 41,
    "method": "tools/call",
    "params": {
      "name": "depth_estimation",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `doc_vqa`
* **Label**: Document VQA 📄
* **Category**: Computer Vision
* **Description**: Visual document understanding on invoices, receipts & forms
* **CLI Equivalent**: `@agent doc-vqa`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Document VQA",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 42,
    "method": "tools/call",
    "params": {
      "name": "doc_vqa",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `zero_shot_image`
* **Label**: Zero-Shot Image 🎯
* **Category**: Computer Vision
* **Description**: Open-vocabulary image classification without fine-tuning
* **CLI Equivalent**: `@agent zero-shot-image`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Zero-Shot Image",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 43,
    "method": "tools/call",
    "params": {
      "name": "zero_shot_image",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `zero_shot_detect`
* **Label**: Zero-Shot Detect 🔍
* **Category**: Computer Vision
* **Description**: Open-vocabulary bounding box object localization
* **CLI Equivalent**: `@agent zero-shot-detect`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Zero-Shot Detect",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 44,
    "method": "tools/call",
    "params": {
      "name": "zero_shot_detect",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `mask_generation`
* **Label**: Mask Generation 🎭
* **Category**: Computer Vision
* **Description**: Segment Anything (SAM) promptable foreground masks
* **CLI Equivalent**: `@agent mask-generation`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Mask Generation",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 45,
    "method": "tools/call",
    "params": {
      "name": "mask_generation",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `keypoint_detection`
* **Label**: Keypoint Detect 📍
* **Category**: Computer Vision
* **Description**: Human pose, facial landmarks, and skeletal joint tracking
* **CLI Equivalent**: `@agent keypoint-detection`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Keypoint Detect",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 46,
    "method": "tools/call",
    "params": {
      "name": "keypoint_detection",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `video_classification`
* **Label**: Video Classify 🎬
* **Category**: Computer Vision
* **Description**: Action recognition, temporal scene cuts, and video tags
* **CLI Equivalent**: `@agent video-classification`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Video Classify",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 47,
    "method": "tools/call",
    "params": {
      "name": "video_classification",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `text_to_video`
* **Label**: Text to Video 📹
* **Category**: Computer Vision
* **Description**: Temporal video sequence generation from text description
* **CLI Equivalent**: `@agent text-to-video`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Text to Video",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 48,
    "method": "tools/call",
    "params": {
      "name": "text_to_video",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `unconditional_image`
* **Label**: Image Synthesis ✨
* **Category**: Computer Vision
* **Description**: Unconditional generative synthesis from learned priors
* **CLI Equivalent**: `@agent unconditional-image`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Image Synthesis",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 49,
    "method": "tools/call",
    "params": {
      "name": "unconditional_image",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `ocr`
* **Label**: OCR Text Extract 🔤
* **Category**: Computer Vision
* **Description**: Multi-language printed and handwritten optical text reading
* **CLI Equivalent**: `@agent ocr`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for OCR Text Extract",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 50,
    "method": "tools/call",
    "params": {
      "name": "ocr",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `face_detection`
* **Label**: Face Detection 👤
* **Category**: Computer Vision
* **Description**: Facial bounding boxes, expression, and demographic cues
* **CLI Equivalent**: `@agent face-detection`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Face Detection",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 51,
    "method": "tools/call",
    "params": {
      "name": "face_detection",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `image_enhance`
* **Label**: Image Super-Res 🌟
* **Category**: Computer Vision
* **Description**: Denoising, deblurring, and 4x AI resolution upscaling
* **CLI Equivalent**: `@agent image-enhance`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Image Super-Res",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 52,
    "method": "tools/call",
    "params": {
      "name": "image_enhance",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `inpainting`
* **Label**: Image Inpainting 🖌️
* **Category**: Computer Vision
* **Description**: Masked area reconstruction and contextual object removal
* **CLI Equivalent**: `@agent inpainting`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Image Inpainting",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 53,
    "method": "tools/call",
    "params": {
      "name": "inpainting",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `image_similarity`
* **Label**: Visual Similarity 🪞
* **Category**: Computer Vision
* **Description**: CLIP embedding cosine similarity between images
* **CLI Equivalent**: `@agent image-similarity`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Visual Similarity",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 54,
    "method": "tools/call",
    "params": {
      "name": "image_similarity",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `nsfw_detect`
* **Label**: NSFW Filter 🛡️
* **Category**: Computer Vision
* **Description**: Safety filtering, sensitive content, and moderation check
* **CLI Equivalent**: `@agent nsfw-detect`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for NSFW Filter",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 55,
    "method": "tools/call",
    "params": {
      "name": "nsfw_detect",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `scene_understanding`
* **Label**: Scene Parsing 🏞️
* **Category**: Computer Vision
* **Description**: Indoor/outdoor holistic scene topology and spatial parsing
* **CLI Equivalent**: `@agent scene-understanding`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Scene Parsing",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 56,
    "method": "tools/call",
    "params": {
      "name": "scene_understanding",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `color_palette`
* **Label**: Palette Extraction 🎨
* **Category**: Computer Vision
* **Description**: Dominant hexadecimal color palette and visual harmony
* **CLI Equivalent**: `@agent color-palette`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Palette Extraction",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 57,
    "method": "tools/call",
    "params": {
      "name": "color_palette",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

## 7. Audio & Speech

### `asr`
* **Label**: Speech-to-Text 🎙️
* **Category**: Audio & Speech
* **Description**: Automatic speech recognition via Whisper models
* **CLI Equivalent**: `@agent asr`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Speech-to-Text",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 58,
    "method": "tools/call",
    "params": {
      "name": "asr",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `tts`
* **Label**: Text-to-Speech 🔊
* **Category**: Audio & Speech
* **Description**: Text synthesis into natural audible speech
* **CLI Equivalent**: `@agent tts`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Text-to-Speech",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 59,
    "method": "tools/call",
    "params": {
      "name": "tts",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `audio`
* **Label**: Audio Classify 🎵
* **Category**: Audio & Speech
* **Description**: Sound event detection & voice activity analysis
* **CLI Equivalent**: `@agent audio`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Audio Classify",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 60,
    "method": "tools/call",
    "params": {
      "name": "audio",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `vad`
* **Label**: Voice Activity 🗣️
* **Category**: Audio & Speech
* **Description**: Real-time speech vs silence endpoint segmentation
* **CLI Equivalent**: `@agent vad`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Voice Activity",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 61,
    "method": "tools/call",
    "params": {
      "name": "vad",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `audio_to_audio`
* **Label**: Audio Denoise 🎚️
* **Category**: Audio & Speech
* **Description**: Background noise cancellation and voice isolation
* **CLI Equivalent**: `@agent audio-to-audio`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Audio Denoise",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 62,
    "method": "tools/call",
    "params": {
      "name": "audio_to_audio",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `text_to_audio`
* **Label**: Text to Sound 🎶
* **Category**: Audio & Speech
* **Description**: Synthesize custom sound effects and acoustic ambiances
* **CLI Equivalent**: `@agent text-to-audio`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Text to Sound",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 63,
    "method": "tools/call",
    "params": {
      "name": "text_to_audio",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `speaker_diarization`
* **Label**: Speaker Diarization 👥
* **Category**: Audio & Speech
* **Description**: Who spoke when: multi-speaker segmentation & clustering
* **CLI Equivalent**: `@agent speaker-diarization`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Speaker Diarization",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 64,
    "method": "tools/call",
    "params": {
      "name": "speaker_diarization",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `speaker_id`
* **Label**: Speaker ID 🆔
* **Category**: Audio & Speech
* **Description**: Voiceprint embedding verification and speaker matching
* **CLI Equivalent**: `@agent speaker-id`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Speaker ID",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 65,
    "method": "tools/call",
    "params": {
      "name": "speaker_id",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `music_gen`
* **Label**: Music Generation 🎼
* **Category**: Audio & Speech
* **Description**: Instrumental and polyphonic music generation from prompts
* **CLI Equivalent**: `@agent music-gen`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Music Generation",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 66,
    "method": "tools/call",
    "params": {
      "name": "music_gen",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `sound_event`
* **Label**: Sound Event Detect 🔔
* **Category**: Audio & Speech
* **Description**: Identify siren, glass break, baby cry, and environmental cues
* **CLI Equivalent**: `@agent sound-event`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Sound Event Detect",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 67,
    "method": "tools/call",
    "params": {
      "name": "sound_event",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `speech_enhance`
* **Label**: Speech Enhance 🎧
* **Category**: Audio & Speech
* **Description**: Spectral restoration and vocal clarity enhancement
* **CLI Equivalent**: `@agent speech-enhance`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Speech Enhance",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 68,
    "method": "tools/call",
    "params": {
      "name": "speech_enhance",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `source_separation`
* **Label**: Audio Separation ✂️
* **Category**: Audio & Speech
* **Description**: Stems splitting: vocals, drums, bass, and instruments
* **CLI Equivalent**: `@agent source-separation`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Audio Separation",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 69,
    "method": "tools/call",
    "params": {
      "name": "source_separation",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `voice_emotion`
* **Label**: Voice Emotion 😊
* **Category**: Audio & Speech
* **Description**: Prosodic speech emotion and affective state recognition
* **CLI Equivalent**: `@agent voice-emotion`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Voice Emotion",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 70,
    "method": "tools/call",
    "params": {
      "name": "voice_emotion",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `audio_lang_id`
* **Label**: Spoken Language ID 🌍
* **Category**: Audio & Speech
* **Description**: Identify spoken language across 100+ global dialects
* **CLI Equivalent**: `@agent audio-lang-id`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Spoken Language ID",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 71,
    "method": "tools/call",
    "params": {
      "name": "audio_lang_id",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `tempo`
* **Label**: Tempo & BPM ⏱️
* **Category**: Audio & Speech
* **Description**: Rhythm tracking, beat onset, and BPM tempo estimation
* **CLI Equivalent**: `@agent tempo`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Tempo & BPM",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 72,
    "method": "tools/call",
    "params": {
      "name": "tempo",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

## 8. Multi-Modal & Domain Sciences

### `video`
* **Label**: Video Analysis 🎬
* **Category**: Multi-Modal & Domain Sciences
* **Description**: Process video streams, extract keyframes, classify actions & video QA
* **CLI Equivalent**: `@agent video`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Video Analysis",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 7,
    "method": "tools/call",
    "params": {
      "name": "video",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `medical`
* **Label**: Medical Analysis 🏥
* **Category**: Multi-Modal & Domain Sciences
* **Description**: Clinical notes analysis, biomedical research summarization
* **CLI Equivalent**: `@agent medical`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Medical Analysis",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 139,
    "method": "tools/call",
    "params": {
      "name": "medical",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `legal`
* **Label**: Legal Review ⚖️
* **Category**: Multi-Modal & Domain Sciences
* **Description**: Contract clause analysis, indemnification and liability audit
* **CLI Equivalent**: `@agent legal`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Legal Review",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 140,
    "method": "tools/call",
    "params": {
      "name": "legal",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `finance`
* **Label**: Financial Analysis 💰
* **Category**: Multi-Modal & Domain Sciences
* **Description**: Balance sheet parsing, earnings call sentiment & ratios
* **CLI Equivalent**: `@agent finance`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Financial Analysis",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 141,
    "method": "tools/call",
    "params": {
      "name": "finance",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `robotics`
* **Label**: Robotics Kinematics 🤖
* **Category**: Multi-Modal & Domain Sciences
* **Description**: Inverse kinematics, trajectory planning, and actuator dynamics
* **CLI Equivalent**: `@agent robotics`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Robotics Kinematics",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 142,
    "method": "tools/call",
    "params": {
      "name": "robotics",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `rl`
* **Label**: Reinforcement Learning 🎮
* **Category**: Multi-Modal & Domain Sciences
* **Description**: Markov decision processes, Q-learning, and policy gradients
* **CLI Equivalent**: `@agent rl`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Reinforcement Learning",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 143,
    "method": "tools/call",
    "params": {
      "name": "rl",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `graph_ml`
* **Label**: Graph ML 🕸️
* **Category**: Multi-Modal & Domain Sciences
* **Description**: Node classification and link prediction on knowledge graphs
* **CLI Equivalent**: `@agent graph-ml`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Graph ML",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 144,
    "method": "tools/call",
    "params": {
      "name": "graph_ml",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `chemistry`
* **Label**: Molecular Chemistry 🧪
* **Category**: Multi-Modal & Domain Sciences
* **Description**: SMILES molecular representation and reaction properties
* **CLI Equivalent**: `@agent chemistry`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Molecular Chemistry",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 145,
    "method": "tools/call",
    "params": {
      "name": "chemistry",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `climate`
* **Label**: Climate Science 🌍
* **Category**: Multi-Modal & Domain Sciences
* **Description**: Atmospheric sensor modeling and weather trend forecasting
* **CLI Equivalent**: `@agent climate`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Climate Science",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 146,
    "method": "tools/call",
    "params": {
      "name": "climate",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `patent`
* **Label**: Patent Prior Art 📜
* **Category**: Multi-Modal & Domain Sciences
* **Description**: Cross-reference claims and patent infringement discovery
* **CLI Equivalent**: `@agent patent`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Patent Prior Art",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 147,
    "method": "tools/call",
    "params": {
      "name": "patent",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `tab_domain`
* **Label**: Domain Tabular 📑
* **Category**: Multi-Modal & Domain Sciences
* **Description**: Healthcare and financial domain-specific tabular modeling
* **CLI Equivalent**: `@agent tab-domain`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Domain Tabular",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 148,
    "method": "tools/call",
    "params": {
      "name": "tab_domain",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `fusion`
* **Label**: Multimodal Fusion 🧠
* **Category**: Multi-Modal & Domain Sciences
* **Description**: Cross-modal late fusion combining vision, text, and data
* **CLI Equivalent**: `@agent fusion`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Multimodal Fusion",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 149,
    "method": "tools/call",
    "params": {
      "name": "fusion",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `av_align`
* **Label**: Audio-Visual Grounding 🎬
* **Category**: Multi-Modal & Domain Sciences
* **Description**: Align audio spectrogram events with visual video frames
* **CLI Equivalent**: `@agent av-align`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Audio-Visual Grounding",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 150,
    "method": "tools/call",
    "params": {
      "name": "av_align",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `physics`
* **Label**: Physics Modeling ⚛️
* **Category**: Multi-Modal & Domain Sciences
* **Description**: Hamiltonian and classical Newtonian mechanics simulations
* **CLI Equivalent**: `@agent physics`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Physics Modeling",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 151,
    "method": "tools/call",
    "params": {
      "name": "physics",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `bioinformatics`
* **Label**: Bioinformatics 🧬
* **Category**: Multi-Modal & Domain Sciences
* **Description**: DNA sequence alignment and protein folding predictions
* **CLI Equivalent**: `@agent bioinformatics`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Bioinformatics",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 152,
    "method": "tools/call",
    "params": {
      "name": "bioinformatics",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `geospatial`
* **Label**: GIS Geospatial 🗺️
* **Category**: Multi-Modal & Domain Sciences
* **Description**: Geohash coordinate queries and satellite imagery analytics
* **CLI Equivalent**: `@agent geospatial`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for GIS Geospatial",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 153,
    "method": "tools/call",
    "params": {
      "name": "geospatial",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

## 9. ACDSO AutoML & Tabular Data

### `acdso`
* **Label**: ACDSO AutoML 📊
* **Category**: ACDSO AutoML & Tabular Data
* **Description**: 5-objective Pareto causal AutoML on datasets
* **CLI Equivalent**: `@agent acdso`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for ACDSO AutoML",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 18,
    "method": "tools/call",
    "params": {
      "name": "acdso",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `datascience`
* **Label**: Data Science 📈
* **Category**: ACDSO AutoML & Tabular Data
* **Description**: Full data science workflow and pipeline
* **CLI Equivalent**: `@agent datascience`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Data Science",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 19,
    "method": "tools/call",
    "params": {
      "name": "datascience",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `dataanalyst`
* **Label**: Data Analyst 🔬
* **Category**: ACDSO AutoML & Tabular Data
* **Description**: Exploratory data analysis & statistical profiling
* **CLI Equivalent**: `@agent dataanalyst`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Data Analyst",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 20,
    "method": "tools/call",
    "params": {
      "name": "dataanalyst",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `timeseries`
* **Label**: Time-Series ⏳
* **Category**: ACDSO AutoML & Tabular Data
* **Description**: Time-series forecasting with Pareto horizon
* **CLI Equivalent**: `@agent timeseries`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Time-Series",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 21,
    "method": "tools/call",
    "params": {
      "name": "timeseries",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `predict`
* **Label**: AutoML Predict 🎯
* **Category**: ACDSO AutoML & Tabular Data
* **Description**: Target variable inference on tabular models
* **CLI Equivalent**: `@agent predict`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for AutoML Predict",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 22,
    "method": "tools/call",
    "params": {
      "name": "predict",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `decision`
* **Label**: Decision Engine ⚖️
* **Category**: ACDSO AutoML & Tabular Data
* **Description**: Prescriptive decision optimization & counterfactuals
* **CLI Equivalent**: `@agent decision`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Decision Engine",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 23,
    "method": "tools/call",
    "params": {
      "name": "decision",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `tabular_classification`
* **Label**: Tabular Classify 🏷️
* **Category**: ACDSO AutoML & Tabular Data
* **Description**: Gradient-boosted decision trees and ensemble classifiers
* **CLI Equivalent**: `@agent tabular-classification`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Tabular Classify",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 24,
    "method": "tools/call",
    "params": {
      "name": "tabular_classification",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `tabular_regression`
* **Label**: Tabular Regress 📉
* **Category**: ACDSO AutoML & Tabular Data
* **Description**: Continuous target estimation and causal effect regression
* **CLI Equivalent**: `@agent tabular-regression`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Tabular Regress",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 25,
    "method": "tools/call",
    "params": {
      "name": "tabular_regression",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `feature_engineering`
* **Label**: Feature Engineer ⚙️
* **Category**: ACDSO AutoML & Tabular Data
* **Description**: Automated polynomial, categorical, and interaction features
* **CLI Equivalent**: `@agent feature-engineering`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Feature Engineer",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 26,
    "method": "tools/call",
    "params": {
      "name": "feature_engineering",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `data_clean`
* **Label**: Dataset Cleaner 🧹
* **Category**: ACDSO AutoML & Tabular Data
* **Description**: Imputation, outlier removal, and schema validation
* **CLI Equivalent**: `@agent data-clean`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Dataset Cleaner",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 27,
    "method": "tools/call",
    "params": {
      "name": "data_clean",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `correlation_matrix`
* **Label**: Correlation Matrix 🔢
* **Category**: ACDSO AutoML & Tabular Data
* **Description**: Pearson, Spearman, and mutual information correlation
* **CLI Equivalent**: `@agent correlation`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Correlation Matrix",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 28,
    "method": "tools/call",
    "params": {
      "name": "correlation_matrix",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `anomaly_detection`
* **Label**: Anomaly Detection 🚨
* **Category**: ACDSO AutoML & Tabular Data
* **Description**: Isolation Forest and Local Outlier Factor anomaly scoring
* **CLI Equivalent**: `@agent anomaly-detection`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Anomaly Detection",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 29,
    "method": "tools/call",
    "params": {
      "name": "anomaly_detection",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `pareto_frontier`
* **Label**: Pareto Optimizer 📐
* **Category**: ACDSO AutoML & Tabular Data
* **Description**: Multi-objective trade-off surface computation
* **CLI Equivalent**: `@agent pareto`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Pareto Optimizer",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 30,
    "method": "tools/call",
    "params": {
      "name": "pareto_frontier",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `clustering`
* **Label**: Data Clustering 🫧
* **Category**: ACDSO AutoML & Tabular Data
* **Description**: K-Means, HDBSCAN, and spectral clustering partitions
* **CLI Equivalent**: `@agent clustering`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Data Clustering",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 31,
    "method": "tools/call",
    "params": {
      "name": "clustering",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

### `model_interpretability`
* **Label**: SHAP Interpretability 💡
* **Category**: ACDSO AutoML & Tabular Data
* **Description**: Shapley additive explanations and feature importance
* **CLI Equivalent**: `@agent shap-explain`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for SHAP Interpretability",
        "type": "string"
      }
    },
    "required": [
      "prompt"
    ],
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 32,
    "method": "tools/call",
    "params": {
      "name": "model_interpretability",
      "arguments": {
        "prompt": "Sample analysis instruction"
      }
    }
  }
  ```

---

## 10. CyberSecurity & Binary Forensics

### `security`
* **Label**: Security Analysis 🛡️
* **Category**: CyberSecurity & Binary Forensics
* **Description**: Malware, phishing, PII, and exploit detection
* **CLI Equivalent**: `@agent security`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Security Analysis",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 123,
    "method": "tools/call",
    "params": {
      "name": "security",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

### `pe`
* **Label**: PE Header Forensics 🔬
* **Category**: CyberSecurity & Binary Forensics
* **Description**: Extract PE headers and binary forensics from .exe/.dll
* **CLI Equivalent**: `@agent pe`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for PE Header Forensics",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 124,
    "method": "tools/call",
    "params": {
      "name": "pe",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

### `vuln_scan`
* **Label**: Vulnerability Scan 🪲
* **Category**: CyberSecurity & Binary Forensics
* **Description**: Static analysis for buffer overflows, use-after-free, injection
* **CLI Equivalent**: `@agent vuln-scan`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Vulnerability Scan",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 125,
    "method": "tools/call",
    "params": {
      "name": "vuln_scan",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

### `malware_analysis`
* **Label**: Malware Analysis 🦠
* **Category**: CyberSecurity & Binary Forensics
* **Description**: Heuristic static malware indicators and evasion patterns
* **CLI Equivalent**: `@agent malware-analysis`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Malware Analysis",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 126,
    "method": "tools/call",
    "params": {
      "name": "malware_analysis",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

### `mem_forensics`
* **Label**: Memory Forensics 💾
* **Category**: CyberSecurity & Binary Forensics
* **Description**: Analyze core dumps, heap allocations, and stack frames
* **CLI Equivalent**: `@agent mem-forensics`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Memory Forensics",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 127,
    "method": "tools/call",
    "params": {
      "name": "mem_forensics",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

### `pii_scan`
* **Label**: PII Scanner 🔒
* **Category**: CyberSecurity & Binary Forensics
* **Description**: Discover SSNs, credit cards, emails, and confidential data
* **CLI Equivalent**: `@agent pii-scan`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for PII Scanner",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 128,
    "method": "tools/call",
    "params": {
      "name": "pii_scan",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

### `entropy`
* **Label**: Entropy Scan 📐
* **Category**: CyberSecurity & Binary Forensics
* **Description**: Compute Shannon entropy to detect packed or encrypted sections
* **CLI Equivalent**: `@agent entropy`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Entropy Scan",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 129,
    "method": "tools/call",
    "params": {
      "name": "entropy",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

### `strings`
* **Label**: Strings Extractor 🧵
* **Category**: CyberSecurity & Binary Forensics
* **Description**: Extract and filter printable ASCII and Unicode strings
* **CLI Equivalent**: `@agent strings`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Strings Extractor",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 130,
    "method": "tools/call",
    "params": {
      "name": "strings",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

### `exploit`
* **Label**: Exploit Analyzer 💥
* **Category**: CyberSecurity & Binary Forensics
* **Description**: Assess proof-of-concept exploits and remediation steps
* **CLI Equivalent**: `@agent exploit`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Exploit Analyzer",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 131,
    "method": "tools/call",
    "params": {
      "name": "exploit",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

### `decompile`
* **Label**: Decompilation 🧬
* **Category**: CyberSecurity & Binary Forensics
* **Description**: Explain disassembled assembly and high-level pseudocode
* **CLI Equivalent**: `@agent decompile`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Decompilation",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 132,
    "method": "tools/call",
    "params": {
      "name": "decompile",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

### `net_audit`
* **Label**: Network Traffic Audit 🌐
* **Category**: CyberSecurity & Binary Forensics
* **Description**: Inspect PCAP captures and suspicious beaconing traffic
* **CLI Equivalent**: `@agent net-audit`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Network Traffic Audit",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 133,
    "method": "tools/call",
    "params": {
      "name": "net_audit",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

### `yara`
* **Label**: YARA Rule Gen 📜
* **Category**: CyberSecurity & Binary Forensics
* **Description**: Synthesize YARA detection rules for indicators of compromise
* **CLI Equivalent**: `@agent yara`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for YARA Rule Gen",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 134,
    "method": "tools/call",
    "params": {
      "name": "yara",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

### `tls_inspect`
* **Label**: TLS Inspector 🔐
* **Category**: CyberSecurity & Binary Forensics
* **Description**: Verify certificates, cipher suites, and handshake health
* **CLI Equivalent**: `@agent tls-inspect`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for TLS Inspector",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 135,
    "method": "tools/call",
    "params": {
      "name": "tls_inspect",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

### `owasp`
* **Label**: OWASP Audit 🛡️
* **Category**: CyberSecurity & Binary Forensics
* **Description**: Comprehensive audit against OWASP Top 10 vulnerabilities
* **CLI Equivalent**: `@agent owasp`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for OWASP Audit",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 136,
    "method": "tools/call",
    "params": {
      "name": "owasp",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

### `packer_detect`
* **Label**: Packer Detector 📦
* **Category**: CyberSecurity & Binary Forensics
* **Description**: Detect UPX, Themida, VMProtect, and known binary packers
* **CLI Equivalent**: `@agent packer-detect`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Packer Detector",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 137,
    "method": "tools/call",
    "params": {
      "name": "packer_detect",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

### `secret_scan`
* **Label**: Secret Leak Scan 🔑
* **Category**: CyberSecurity & Binary Forensics
* **Description**: Identify committed API tokens, private keys, and passwords
* **CLI Equivalent**: `@agent secret-scan`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Secret Leak Scan",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 138,
    "method": "tools/call",
    "params": {
      "name": "secret_scan",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

## 11. System Telemetry & Lifecycle

### `rest_rl`
* **Label**: ReST-RL Daemon ⚡
* **Category**: System Telemetry & Lifecycle
* **Description**: Sub-8ms Windows Job Object RL repair engine
* **CLI Equivalent**: `@agent rest-rl status`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for ReST-RL Daemon",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 110,
    "method": "tools/call",
    "params": {
      "name": "rest_rl",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

### `update`
* **Label**: Update Catalog ⚡
* **Category**: System Telemetry & Lifecycle
* **Description**: Fast curated update (~6,500 models & dynamic Ollama sizing)
* **CLI Equivalent**: `@agent update`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Update Catalog",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 169,
    "method": "tools/call",
    "params": {
      "name": "update",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

### `updatedb`
* **Label**: Full Registry Crawler 🚀
* **Category**: System Telemetry & Lifecycle
* **Description**: Crawl all 2M+ models from Hugging Face Hub
* **CLI Equivalent**: `@agent updatedb`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Full Registry Crawler",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 170,
    "method": "tools/call",
    "params": {
      "name": "updatedb",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

### `active_model`
* **Label**: Active Model 🤖
* **Category**: System Telemetry & Lifecycle
* **Description**: Inspect currently loaded Ollama model & memory
* **CLI Equivalent**: `@agent active-model`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for Active Model",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 171,
    "method": "tools/call",
    "params": {
      "name": "active_model",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

### `sys_info`
* **Label**: System Info 🖥️
* **Category**: System Telemetry & Lifecycle
* **Description**: Hardware resources, runtime RAM/VRAM, and active models
* **CLI Equivalent**: `@agent sys-info`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for System Info",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 172,
    "method": "tools/call",
    "params": {
      "name": "sys_info",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---

### `fusion_status`
* **Label**: ModelFusion Status 🧠
* **Category**: System Telemetry & Lifecycle
* **Description**: Multi-modal catalog count and consensus telemetry
* **CLI Equivalent**: `@agent fusion-status`
* **Input Schema**:
  ```json
  {
    "properties": {
      "file": {
        "description": "Optional file path or target dataset",
        "type": "string"
      },
      "gpu": {
        "description": "Enable GPU acceleration",
        "type": "boolean"
      },
      "prompt": {
        "description": "Input text or instructions for ModelFusion Status",
        "type": "string"
      }
    },
    "type": "object"
  }
  ```
* **Example Call**:
  ```json
  {
    "jsonrpc": "2.0",
    "id": 173,
    "method": "tools/call",
    "params": {
      "name": "fusion_status",
      "arguments": {
        "file": "sample",
        "gpu": true
      }
    }
  }
  ```

---
