# HugOS IDE & ModelFusion Integration Manual

HugOS IDE categorizes task queries by modality (text, security, legal, domain, image, and audio) and features native local multimodal processing directly through its Python execution pipeline, completely bypassing the need for any external container manager or Ollama installation.

---

## 🌀 Local Multimodal Processing

### How it Works:
1. **IDE Capture**: The editor's chat UI allows dragging and dropping images, voice notes, or documents. Binary parts are serialized to base64 and wrapped in custom tags (e.g. `[IMAGE:base64_data]` or `[AUDIO:base64_data]`) inside the text prompt.
2. **Extraction**: The Python execution scripts (`run_model_transformers.py`) parse these tags, strip them from the prompt, and decode the base64 strings back into their raw media representations.
3. **Modality Breakdown**:
   * **Images (PNG, JPEG, WebP)**: Local models (e.g. `Qwen2-VL` or `Phi-3-vision`) are loaded via HuggingFace's `AutoProcessor` and `AutoModelForVision2Seq` to perform image classification, visual question answering, or layout analysis.
   * **Voice & Audio (WAV, MP3, M4A)**: Local audio processing is handled via HuggingFace's automatic speech recognition pipelines (e.g. executing `Whisper` models) to natively transcribe and analyze audio clips.
   * **PDFs & Documents (Text & Layout)**: For standard text PDFs, the text layer is extracted and routed as context. For scanned or visual PDFs (containing diagrams/tables), pages are converted to images in Python to perform visual reasoning.

### Required Setup & Dependencies:
To enable native local multimodal execution on your machine, install the required Python packages:
```bash
pip install torch transformers accelerate pillow soundfile librosa pypdf
```
> [!NOTE]
> If a HuggingFace API token is supplied in settings, multimodal requests will optionally route to Hugging Face's serverless endpoints in the cloud; otherwise, the local Python scripts run the execution locally.

---

## 🤖 Intent Classification & Decision Routing

HugOS features a hybrid task detector in `detector.rs` combining exact regex keyword patterns and a Term-Frequency Vector Space Model (VSM).

### 1. Prompt Embedding and VSM Classification
* **Tokenizer & Stop-Word Filter**: The prompt text is cleaned, lower-cased, and stripped of non-alphanumeric noise. Common English stop-words (e.g. *the*, *is*, *a*) are removed.
* **TF Vector Space Embedding**: The remaining tokens are parsed into a normalized term frequency vector (`TermVector`).
* **Cosine Similarity Matching**: The prompt vector is compared against mutable category centroids representing standard tasks (e.g. translation, code-analysis, summarization).
* **Hybrid Scoring**: The final score combines keyword matches (40%) and VSM similarity (60%).

### 2. Online Feedback & Drift Prevention
To adapt to the developer's vocabulary, the IDE supports feedback corrections via `register_feedback(prompt, corrected_task)`:
* **Centroid Shift**: Shifty task centroids are updated using an Exponential Moving Average (EMA) with a learning rate (\(\alpha = 0.15\)).
* **L2 Unit Normalization**: After each update, the centroid vector is re-normalized to a unit length of 1.0.
* **Pruning Threshold**: Any term weight falling below 0.01 is pruned.

This mathematical cleanup prevents feature inflation and guarantees category definitions do not drift over time.

---

## 💻 CLI Command Line Interface Flags (`cli.exe`)

The ModelFusion binary `cli.exe` (located in the IDE `bin` directory) supports command-line flags. Please note the differences between flags that are active inside the IDE and those that are only for standalone CLI use:

> [!IMPORTANT]
> **Functional Architecture:** In ModelFusion, **all flags function as executable commands/functions**. The CLI parser maps each flag directly to an underlying handler function in the execution engine. Specifying a flag acts as an instruction to execute that specific capability function rather than just setting configuration state.

### Supported CLI Flags in the IDE
* `--server`: Starts the persistent HTTP API server that the IDE connects to.
* `--port <port>`: Configures the HTTP port for the server (the IDE extension expects this to be `5000`).
* `--db-path <path>`: Sets the SQLite database path (resolved relative to the IDE installation directory).
* `--mcp`: Runs ModelFusion as an MCP stdio server.
* `--update`: Runs the background Hugging Face Hub sync process.
* `--orchestrate "<prompt>"`: Command-line fallback used by the IDE to fetch routing decisions and run models if the API server is unreachable.
* `--openvino`: Forces local inference to run using OpenVINO.
* `--gpu`: Requests CUDA/GPU execution for local transformers.
* `--cpu`: Forces CPU fallback for local transformers.

### 📡 Database Synchronization Telemetry Logging (`--update`)
When running database sync operations (via the `--update` flag or the `update_database` MCP tool), the console outputs paginated telemetry feedback. It requests models in batches of 1,000 using cursor-based pagination and upserts them into the SQLite database.

**Progress Log Output Structure:**
```text
📥 Fetching page 50 (url: https://huggingface.co/api/models?limit=1000&full=false&cursor=eyIkb3IiOlt7InRyZW5kaW5nU2NvcmUiOjAsIl9pZCI6eyIkZ3QiOiI2MjkwNDkzNTQ3ZDVkNDkzN2E2ODQ1NzYifX0seyJ0cmVuZGluZ1Njb3JlIjp7IiRsdCI6MH19LHsidHJlbmRpbmdTY29yZSI6bnVsbH1dfQ%3D%3D)...
🏗️  Updating database with 1000 fetched models from page 50...
✨ Page 50 completed. Total upserted models: 50000
📥 Fetching page 51 (url: https://huggingface.co/api/models?limit=1000&full=false&cursor=eyIkb3IiOlt7InRyZW5kaW5nU2NvcmUiOjAsIl9pZCI6eyIkZ3QiOiI2Mjk3Y2Q3YjlkM2RlN2IzMmZjZjE3ZjEifX0seyJ0cmVuZGluZ1Njb3JlIjp7IiRsdCI6MH19LHsidHJlbmRpbmdTY29yZSI6bnVsbH1dfQ%3D%3D)...
🏗️  Updating database with 1000 fetched models from page 51...
✨ Page 51 completed. Total upserted models: 51000
```

### Deactivated or Unsupported CLI Flags in HugOS IDE
* `--use-openai`: **Disabled / Stripped in the IDE core**. HugOS strictly forbids and blocks connections to proprietary registries (OpenAI, Anthropic, Gemini) to guarantee local privacy.
* `--vllm`: **Linux-only**. Cannot be used on Windows IDE installations.
* `--config` / `--api-keys`: Managed automatically by the HugOS extension and user settings; manually overriding these via CLI flags is unsupported inside the IDE environment.
* `--save-model` / `--load-model` / `--ml-retrain`: CLI-only tools for developer experimentation; these will not work inside the IDE's read-only production environment.

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
