# HugOS IDE — Custom AI-Powered Code-OSS Fork

HugOS is an advanced, open-weights compound intelligence IDE built upon the open-source core of VS Code (Code - OSS). 

Unlike standard editors that rely on proprietary cloud APIs, HugOS is built from the ground up for native local orchestration, running ModelFusion as a built-in, un-uninstallable Model Context Protocol (MCP) server.

![HugOS System Dashboard](./hugos_system_dashboard.png)

---

## 🏗️ Architecture & Integration

HugOS disables and strips out all proprietary and paid model registries (such as OpenAI, Anthropic, and Gemini) and strictly restricts the MCP registry to **only allow the ModelFusion local MCP server**. All other MCP server registrations are dynamically filtered out at the core workbench registry layer.

### Integration Flow
```mermaid
graph TD
    User[User in HugOS Chat] -->|Natural Language Query| Agent[HugOS Chat Agent / Thinking Model]
    Agent -->|Intelligent Tool Selection| Host[HugOS Native MCP Host]
    Host -->|JSON-RPC over Stdio| Server[ModelFusion MCP Server / cli.exe]
    
    subgraph ModelFusion Local Daemon
        Server -->|1. Intent Analysis| Detector[Intelligent Task Detector]
        Server -->|2. Model Select| Selector[Enhanced Model Selector]
        Server -->|3. Local Run| Exec[OpenVINO / Transformers / Ollama]
        DB[(hf_models.db)] <--> Selector
    end

    Exec -->|Result Content| Server
    Server -->|JSON-RPC Output| Host
    Host -->|Rendered Content| Agent
    Agent -->|Final Answer| User
```

---

## 🛠️ Setup & Installation Instructions

### 1. Production Installation via MSI
HugOS IDE packages all system files, local configuration, and a **prepopulated SQLite database** inside the `HugOS.msi` installer.
* **Installer Path:** Go to [HugOS.msi](file:///d:/harfile/ModelFusion/IDE/HugOS.msi) and double-click the file to start the installation wizard.
* **Clean Reinstallation:** If you are updating an existing installation or experiencing file locks, choose the **Remove** option on the installation screen to cleanly uninstall the old files first, and then run `HugOS.msi` again.

### 2. Resolving File Locks
If the installation or update freezes, verify that no old instances are running in the background. Run this PowerShell command to kill hung editor processes:
```powershell
Stop-Process -Name HugOS -Force
```

### 3. Local Directory Locations
* **Installation folder:** `C:\Program Files\HugOS IDE`
* **Prepopulated database:** `C:\Program Files\HugOS IDE\db\hf_models.db` (Wix automatically deploys this 478 MB database containing 200,000+ Hugging Face models so you don't have to populate the database from scratch).
* **Developer Build executable:** [HugOS.exe](file:///d:/harfile/ModelFusion/IDE/VSCode-win32-x64/HugOS.exe) (directly runnable as a portable application).

### 4. GitHub Account Login Setup
To enable cloning, pushing, pulling, and querying private repositories on GitHub:
1. Click the **Accounts** icon (the profile silhouette in the bottom-left corner of the status bar).
2. Click **Sign in to GitHub** and follow the browser authorization prompts.

---

## 💾 System & Hardware Requirements

HugOS features a pure-Rust hardware detection system powered by the `sysinfo` crate and `nvidia-smi` to prevent Out-Of-Memory (OOM) crashes and select models optimal for your device.

### 1. Detected Hardware Metrics
* **System RAM:** Captured using pure-Rust `sysinfo::System`.
* **CPU Physical Cores:** Captured using pure-Rust physical core count.
* **GPU VRAM:** Queries free/total memory using `nvidia-smi`.

### 2. Minimum vs. Adequate Hardware Specs
The routing layer calculates hardware suitability boundaries based on parameter count ($P$ in billions) and active backend runtime (Transformers, Ollama, OpenVINO):

| Model Size | Backend | Minimum Specs (Required) | Adequate Specs (Recommended) |
| :--- | :--- | :--- | :--- |
| **$P \le 3\text{B}$** | OpenVINO / Ollama | 4 GB RAM, 2 CPU Cores | 6 GB RAM, 4 CPU Cores, GPU preferred |
| **$3\text{B} < P \le 8\text{B}$** | OpenVINO / Ollama | 8 GB RAM, 4 CPU Cores | 12 GB RAM, 6 CPU Cores, GPU preferred |
| **$P > 8\text{B}$** | OpenVINO / Ollama | 16 GB RAM, 6 CPU Cores | 24 GB RAM, 8 CPU Cores, GPU preferred |
| **Any Size** | Transformers (FP16) | $VRAM \ge P \times 2.4\text{ GB}$ | $VRAM \ge P \times 3.0\text{ GB}$ |

### 3. Budget & Scoring Modifiers
* **Safety Factor:** The system applies a 70% safety margin buffer on available resources when computing CPU and GPU budgets.
* **Suitability Modifiers:**
  * **Inadequate:** If the system does not meet the minimum RAM or Core counts required, the candidate model is **completely filtered out** (failsafe).
  * **Adequate:** If the system meets the adequate recommendation, the candidate receives a **`+0.15` score boost** (promoting faster performance).
  * **Minimum:** If the system only meets the minimum specifications but not adequate, the candidate receives a **`-0.20` score penalty**.

---

## 🎛️ Local Inference Backends (OpenVINO, vLLM, Ollama)

ModelFusion supports multiple high-performance execution backends depending on your hardware:

* **OpenVINO (Optimized CPU/iGPU/GPU):** 
  * Designed for cross-platform hardware acceleration on Intel/AMD CPUs, integrated GPUs (iGPUs), and discrete graphics.
  * Active when the `--openvino` flag or `MODELFUSION_USE_OPENVINO` environment variable is set.
  * *Conversion Flow:* It looks for cached models in `ov_models/`. If not found, it downloads pre-converted INT4 models from the OpenVINO HuggingFace registry. If a custom model is requested, it attempts manual conversion via `optimum-intel` or direct `ov.convert_model()`.
* **vLLM (Linux-only High-Throughput GPU):**
  * High-performance LLM execution framework optimized for NVIDIA GPUs using PagedAttention.
  * Only supported on **Linux** environments; falls back to Ollama or OpenVINO on Windows.
  * Active when the `MODELFUSION_USE_VLLM` environment variable is set.
* **Ollama (Local LLM Daemon):**
  * Seamless fallback or primary local runner that connects to a running Ollama server instance (default: `http://localhost:11434`).
  * Maps HuggingFace model IDs to Ollama-specific library equivalents (e.g. `Qwen2.5-Coder` -> `qwen2.5-coder`).

---

## 📸 Multimodal Task Processing (Images, Voice & PDFs)

HugOS categorizes task queries by modality: `text`, `security`, `legal`, `domain`, `image`, and `audio`. The IDE features **native local multimodal processing** directly through its Python execution pipeline, completely bypassing the need for any external container manager or Ollama installation.

### How it Works:
* **IDE Capture:** The editor's chat UI allows dragging and dropping images, voice notes, or documents. Binary parts are serialized to base64 and wrapped in custom tags (e.g. `[IMAGE:base64_data]` or `[AUDIO:base64_data]`) inside the text prompt.
* **Extraction:** The Python execution scripts (`run_model_transformers.py`) parse these tags, strip them from the prompt, and decode the base64 strings back into their raw media representations.

### Modality Breakdown:
1. **Images (PNG, JPEG, WebP):** 
   * Local models (e.g. `Qwen2-VL` or `Phi-3-vision`) are loaded via HuggingFace's `AutoProcessor` and `AutoModelForVision2Seq` to perform image classification, visual question answering, or layout analysis.
2. **Voice & Audio (WAV, MP3, M4A):** 
   * Local audio processing is handled via HuggingFace's automatic speech recognition pipelines (e.g. executing Whisper models) to natively transcribe and analyze audio clips.
3. **PDFs & Documents (Text & Layout):** 
   * For standard text PDFs, the text layer is extracted and routed as context. For scanned or visual PDFs (containing diagrams/tables), pages are converted to images in Python to perform visual reasoning.

### Required Setup & Dependencies:
To enable native local multimodal execution on your machine, install the required Python packages:
```bash
pip install torch transformers accelerate pillow soundfile librosa pypdf
```
*(If a HuggingFace API token is supplied in settings, multimodal requests will optionally route to Hugging Face's serverless endpoints in the cloud; otherwise, the local Python scripts run the execution locally).*

---

## 🤖 Intent Classification & Decision Routing

HugOS features a hybrid task detector in [detector.rs](file:///d:/harfile/ModelFusion/crates/task_detection/src/detector.rs) combining exact regex keyword patterns and a Term-Frequency Vector Space Model (VSM).

### 1. Prompt Embedding and VSM Classification
1. **Tokenizer & Stop-Word Filter:** The prompt text is cleaned, lower-cased, and stripped of non-alphanumeric noise. Common English stop-words (e.g. `the`, `is`, `a`) are removed.
2. **TF Vector Space Embedding:** The remaining tokens are parsed into a normalized term frequency vector (`TermVector`).
3. **Cosine Similarity Matching:** The prompt vector is compared against mutable category centroids representing standard tasks (e.g. `translation`, `code-analysis`, `summarization`).
4. **Hybrid Scoring:** The final score combines keyword matches ($40\%$) and VSM similarity ($60\%$).

### 2. Online Feedback & Drift Prevention
To adapt to the developer's vocabulary, the IDE supports feedback corrections via `register_feedback(prompt, corrected_task)`:
* **Centroid Shift:** Shifty task centroids are updated using an Exponential Moving Average (EMA) with a learning rate ($\alpha = 0.15$).
* **L2 Unit Normalization:** After each update, the centroid vector is re-normalized to a unit length of `1.0`.
* **Pruning Threshold:** Any term weight falling below `0.01` is pruned.
* *This mathematical cleanup prevents feature inflation and guarantees category definitions do not drift over time.*

---

## 💻 CLI Command Line Interface Flags (`cli.exe`)

The ModelFusion binary `cli.exe` (located in the IDE `bin` directory) supports command-line flags. **Please note the differences between flags that are active inside the IDE and those that are only for standalone CLI use:**

### Supported CLI Flags in the IDE
* **`--server`**: Starts the persistent HTTP API server that the IDE connects to.
* **`--port <port>`**: Configures the HTTP port for the server (the IDE extension expects this to be `5000`).
* **`--db-path <path>`**: Sets the SQLite database path (resolved relative to the IDE installation directory).
* **`--mcp`**: Runs ModelFusion as an MCP stdio server.
* **`--update`**: Runs the background Hugging Face Hub sync process.
* **`--orchestrate "<prompt>"`**: Command-line fallback used by the IDE to fetch routing decisions and run models if the API server is unreachable.
* **`--openvino`**: Forces local inference to run using OpenVINO.
* **`--gpu`**: Requests CUDA/GPU execution for local transformers.
* **`--cpu`**: Forces CPU fallback for local transformers.

### Deactivated or Unsupported CLI Flags in HugOS IDE
* **`--use-openai`**: **Disabled / Stripped** in the IDE core. HugOS strictly forbids and blocks connections to proprietary registries (OpenAI, Anthropic, Gemini) to guarantee local privacy.
* **`--vllm`**: **Linux-only.** Cannot be used on Windows IDE installations.
* **`--config` / `--api-keys`**: Managed automatically by the HugOS extension and user settings; manually overriding these via CLI flags is unsupported inside the IDE environment.
* **`--save-model` / `--load-model` / `--ml-retrain`**: CLI-only tools for developer experimentation; these will not work inside the IDE's read-only production environment.

---

## 🛠️ ModelFusion MCP Stdio Server Tools

The ModelFusion MCP server registers the following native tools, which the editor's thinking model calls automatically:

### 1. `orchestrate`
* **Description**: Runs local model selection and orchestration for general text-based queries.
* **Parameters**: `prompt` (string, required), `budget` (number), `selection_strategy` (string), `fusion_mode` (string), `task_override` (string), `gpu` (boolean), `cpu` (boolean).

### 2. `analyze_file`
* **Description**: Evaluates and refines code or logs for a specific file path, feeding the file's content as context into the local LLM.
* **Parameters**: `file` (string, required), `prompt` (string, required), `budget` (number), `gpu` (boolean), `cpu` (boolean).

### 3. `analyze_folder`
* **Description**: Scans a folder to list files and analyze directory context for architectural review.
* **Parameters**: `folder` (string, required), `prompt` (string, required), `budget` (number).

### 4. `pe_header_extraction`
* **Description**: Extract PE structures, sections, imports, and detect malware signatures in Windows executables.
* **Parameters**: `file` (string, required), `prompt` (string).

### 5. `get_database_stats`
* **Description**: Inspects `hf_models.db` to show the number of cached, categorized, and indexed models.
* **Parameters**: None.

### 6. `list_tasks`
* **Description**: Returns all supported Hugging Face model tasks categorized by modality.
* **Parameters**: `category` (string).

### 7. `update_database`
* **Description**: Updates the local SQLite models database with the latest open-weights metadata.
* **Parameters**: None.

### 8. `clear_cache`
* **Description**: Empties the local download cache to free disk space.
* **Parameters**: None.

### 9. `get_decision_stats`
* **Description**: Retrieves history logs detailing which models were chosen for past prompts.
* **Parameters**: None.

### 10. `report_bandit_feedback`
* **Description**: Submits thumbs-up/down or numeric feedback to train the Multi-Armed Bandit context router.
* **Parameters**: `context` (integer, required), `arm` (integer, required), `reward` (number, required).
