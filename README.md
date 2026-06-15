# ModelFusion

ModelFusion is a modular, high-performance Rust port of the **HFOrchestra** AI task orchestration CLI. It evaluates and selects HuggingFace models dynamically from a local SQLite database, routes prompts to various LLM API providers, scans text for adversarial threat patterns, and analyzes Windows executables for malware indicators.

---

## 🏗️ Crate Architecture

The workspace is structured into several modular crates under the `crates/` directory:

```
d:\harfile\ModelFusion\
├── Cargo.toml            (Workspace Root)
├── .env.example          (Environment variables template)
├── config/               (JSON/CSV configuration files copied from Python)
├── db/                   (SQLite database location)
├── crates/
│   ├── cli/              (Main CLI binary - parses flags and handles dispatches)
│   ├── core/             (Named 'modelfusion_core' - houses LLM providers, orchestrator, and processor)
│   ├── db/               (SQLite database wrapper, schemas, and stats queries)
│   ├── task_detection/   (Keyword-based prompt task and language detection)
│   ├── model_selection/  (Multi-objective scorer and weighted ensemble selectors)
│   ├── analysis/         (PE executable parser using goblin and malware risk evaluator)
│   ├── security/         (ATLAS Threat Detector scanning for MITRE ATLAS adversarial TTPs)
│   ├── monitoring/       (Rolling session quality and adaptive threshold managers)
│   └── utils/            (Backups, folder scaffolding, and rate limiter utilities)
```

---

## ⚙️ Setup Instructions

### Prerequisites
- [Rust & Cargo](https://rustup.rs/) (Stable toolchain)
- SQLite (Bundled in the `db` crate dependency)

### Environment Variables
Copy `.env.example` to `.env` in the root folder and fill in your API credentials:
```bash
cp .env.example .env
```
Available environment keys:
- `OPENAI_API_KEY`: For OpenAI model calls (`gpt-3.5-turbo`, etc.)
- `ANTHROPIC_API_KEY`: For Anthropic model calls (`claude-3`, etc.)
- `GOOGLE_GEMINI_API_KEY`: For Google Gemini model calls
- `HF_TOKEN` / `HUGGINGFACE_API_KEY`: For HuggingFace Inference API calls

---

## 🚀 Usage Guide

### 1. Build the Workspace
Compile all crates in release or dev profile:
```bash
cargo build --workspace
```

### 2. Populate the Database
Initializes the database schema and downloads the top 100 model metadata records from the HuggingFace Hub REST API:
```bash
cargo run --bin cli -- --update
```

### 3. Display Database Statistics
Query database metrics, model counts by task/tag, and the highest-ranked models:
```bash
cargo run --bin cli -- --stats
```

### 4. Run Task Orchestration
Processes a prompt, automatically detects its task type, searches the database for the best model using multi-objective optimization, and executes the call:
```bash
cargo run --bin cli -- --prompt "translate this sentence to spanish"
```
You can also force a specific task or request OpenAI processing:
```bash
cargo run --bin cli -- --prompt "write a story about a rusty robot" --task text-generation --use-openai
```

### 5. Windows Portable Executable (PE) Analysis
Extracts DOS headers, File headers, Sections, and DLL imports from a binary executable to calculate a malware score and flag potential security risks:
```bash
cargo run --bin cli -- --pe-header-extraction --file target/debug/cli.exe
```

### 6. List Tasks
List available tasks, either as a general summary or filtered by category:
```bash
cargo run --bin cli -- --tasks
cargo run --bin cli -- --tasks text
```

### 7. Run Model Fusion
Model Fusion evaluates a prompt using a panel of 10 diverse models concurrently, parses their responses with a 32B judge model into structured JSON, and writes a final synthesized answer using a 32B writer model:
```bash
cargo run --bin cli -- --prompt "compare Python and Rust for high-performance CLI tools" --fusion
```

### 8. Review Code in a Folder
Recursively reads and aggregates all supported code/text files from a specified folder and passes them for analysis. You can specify a custom prompt or let it execute a default code review prompt:
```bash
cargo run --bin cli -- --folder crates/cli/src
```
Or run with Model Fusion for a comprehensive multi-model comparison:
```bash
cargo run --bin cli -- --folder crates/cli/src --fusion
```

### 9. CLI Command Line Help
To view all available command line arguments, flags, and options:
```bash
cargo run --bin cli -- --help
```

---

## 🛡️ Security & Innovations

- **Model Fusion Pipeline**: Dynamically queries a panel of 10 concurrent Hugging Face models using the new OpenAI-compatible router at `router.huggingface.co/v1`, handles `reasoning_content` for DeepSeek-R1 distilled models, and performs robust multi-stage analysis and synthesis.
- **MITRE ATLAS Threat Scanner**: Scans prompts against common adversarial patterns (like prompt injection, evasion of policies, and social engineering) using compiled regex tables.
- **Multi-Objective Model Scoring**: Norms downloads and likes, blends in model size efficiency, and checks licenses against a list of approved open-source licenses (`mit`, `apache-2.0`, etc.) to choose the best candidate.
- **Offline Provider Mocks**: If API keys are missing or requests fail, the orchestration system falls back gracefully to a mock answer format, allowing the system to run in offline/isolated environments without crashing.
