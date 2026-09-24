#!/usr/bin/env python3
"""
Update README.md with the prominent 'CLI Reference & Capabilities (All 161 Flags)' section.
"""

import sys

def update_readme():
    with open('README.md', 'r', encoding='utf-8') as f:
        content = f.read()

    # Update doc link at the top
    old_link = "*   [CLI Reference Manual](docs/CLI_REFERENCE.md) — Comprehensive guide for all 159+ commands, subcommands, and flags."
    new_link = "*   [CLI Reference Manual (All 161 Flags)](docs/CLI_REFERENCE.md) — Exhaustive master table, parameter options, and executable examples for all 161 CLI flags."
    if old_link in content:
        content = content.replace(old_link, new_link)
        print("Updated top CLI Reference Manual link.")

    # Check if section already exists
    if "## 💻 CLI Reference & Capabilities (All 161 Flags)" in content:
        print("Section already exists in README.md. Skipping insertion.")
        return

    section = """## 💻 CLI Reference & Capabilities (All 161 Flags)

ModelFusion's Master CLI (`cli.exe`) is the single authoritative execution engine powering both standalone terminal workflows and the embedded HugOS IDE runtime. In accordance with ModelFusion's command architecture, **all 161 CLI flags function as direct executable capability directives** rather than passive configuration options.

> [!TIP]
> **Complete Authoritative Documentation**: For the full numbered master table (#1 to #161), detailed parameter specifications, and concrete executable examples for every single flag, see the dedicated [**docs/CLI_REFERENCE.md**](docs/CLI_REFERENCE.md).

### Functional Category Matrix (All 161 Production Flags)

| # | Category | Flag Range | Total | Core Capabilities & Key Directives | Concrete Execution Example |
|:---:|:---|:---:|:---:|:---|:---|
| **1** | **Global Execution & Resource Flags** | `#1 – #19` | 19 | Hardware targeting (`--gpu`, `--cpu`), prompt inputs (`--file`, `--prompt`), budget limits (`--budget`), execution trace | `cli.exe --prompt "Design lock-free queue" --gpu` |
| **2** | **Machine Learning Model Selection** | `#20 – #26` | 7 | Adaptive Pareto routing, online RL feedback (`--ml-learning`), meta-ensembles, confidence thresholds | `cli.exe --enable-ml-selection --ml-analytics` |
| **3** | **SINQ Quantization Engine** | `#27 – #31` | 5 | Sub-4-bit integer non-linear weight quantization, bit-width (`--sinq-nbits`), grouping, tiling modes | `cli.exe --sinq --sinq-nbits 4 --prompt "..."` |
| **4** | **Innovation & Cognitive Systems** | `#32 – #37` | 6 | Workflow optimization, semantic AST tracking, predictive reasoning, cognitive innovation levels | `cli.exe --enable-innovations --innovation-level 2` |
| **5** | **HyDE Search & Web Retrieval** | `#38 – #46` | 9 | Hypothetical document embeddings, live web search agent (`--search`), autonomous deep research (`--research`) | `cli.exe --research "Latest GRPO RL advances"` |
| **6** | **System & Orchestration Commands** | `#47 – #87` | 41 | Model Fusion deliberation (`--fusion`), Ollama/OpenVINO/ONNX/vLLM backends, `--update` vs `--updatedb`, ReST-RL | `cli.exe --active-model --db-path "IDE/db/hf_models.db"` |
| **7** | **Data Science & Tabular Workflows** | `#88 – #90` | 3 | Automated tabular profiling (`--dataanalyst`), full ML pipeline (`--datascience`), formatted PDF report export | `cli.exe --datascience --file "data.csv" --export-pdf` |
| **8** | **Response Evaluation & Planning** | `#91 – #93` | 3 | Multi-metric response scoring (`--score`), LLM-as-a-Judge certification (`--judge`), strategic blueprints (`--plan`) | `cli.exe --judge --score --prompt "..."` |
| **9** | **Binary & PE Executable Analysis** | `#94` | 1 | Windows PE executable header inspection, import/export symbol tables, digital Authenticode signatures | `cli.exe --pe-header-extraction --file "cli.exe"` |
| **10** | **Multi-Modal Task Routing Flags** | `#95 – #156` | 62 | All 45+ Hugging Face tasks spanning Vision, Audio, NLP, Code, Document QA, Tabular, and Domain pipelines | `cli.exe --text-generation --prompt "..."` |
| **11** | **Server & Database Commands** | `#157 – #161` | 5 | Custom SQLite database path (`--db-path`), HTTP REST server (`--server`, `--port`), MCP stdio protocol (`--mcp`) | `cli.exe --server --port 5000 --db-path "IDE/db/hf_models.db"` |

---

### Core Execution Invariants

1. **Dual Database Ingestion Pipelines**:
   - **`--update` (Fast Curated Engine)**: Ingests top ~6,500 production workhorse models across all 45 tasks and provisions matching Ollama model.
   - **`--updatedb` (Full Registry Crawler)**: Traverses all 2,000,000+ models on Hugging Face Hub using cursor pagination (1,000 models/commit).
2. **Dynamic Runtime Available Memory Law**:
   - Never size or allocate models based on total physical RAM. Always evaluate runtime free/available RAM (`res.free_ram_gb`) and free VRAM (`res.free_vram_mb`) to prevent OOM termination.
3. **4-Way Cryptographic Parity**:
   - `cli.exe` is kept byte-identical across `target/release/cli.exe`, `IDE/bin/cli.exe`, `IDE/VSCode-win32-x64/bin/cli.exe`, and `%LOCALAPPDATA%\\HugOS IDE\\bin\\cli.exe`.

For complete documentation of all flags, see [**docs/CLI_REFERENCE.md**](docs/CLI_REFERENCE.md).

---

"""

    target_marker = "## 🖥️ HugOS IDE"
    if target_marker not in content:
        raise ValueError("Could not find marker '## 🖥️ HugOS IDE' in README.md")

    content = content.replace(target_marker, section + target_marker)
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully inserted 'CLI Reference & Capabilities (All 161 Flags)' into README.md")

if __name__ == '__main__':
    update_readme()
