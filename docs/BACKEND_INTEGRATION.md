# Backend Integration Guide

ModelFusion supports multiple inference backends for local model execution.
This document covers all available backends, their requirements, and usage.

## Table of Contents

- [Backend Overview](#backend-overview)
- [OpenVINO (Recommended for CPU)](#openvino-recommended-for-cpu)
- [OpenVINO Model Preparation (Optimum-Intel)](#openvino-model-preparation-optimum-intel)
- [vLLM (Linux GPU)](#vllm-linux-gpu)
- [Ollama](#ollama)
- [Transformers (Default)](#transformers-default)
- [Backend Selection Logic](#backend-selection-logic)
- [Known Issues](#known-issues)

---

## Backend Overview

| Backend | Flag | Platform | Hardware | Best For |
|---|---|---|---|---|
| **OpenVINO** | `--openvino` | Windows + Linux | Intel CPU/iGPU | Fast CPU inference, auto-converts + caches models |
| **vLLM** | `--vllm` | Linux only | NVIDIA GPU + CUDA | High-throughput GPU inference |
| **Ollama** | `--ollama` | Windows + Linux | CPU or GPU | Easy setup, local model serving |
| **Transformers** | *(default)* | Windows + Linux | CPU or CUDA GPU | Universal fallback |

---

## OpenVINO (Recommended for CPU)

OpenVINO provides optimized inference on Intel hardware (CPUs, iGPUs, VPUs).

### Installation

```bash
# Minimum (classic OpenVINO — always works)
pip install -U openvino

# Optional: OpenVINO GenAI (better performance if available)
pip install -U openvino-genai

# Optional: Optimum-Intel (enables pre-quantized INT8/INT4 models)
# NOTE: Requires Python 3.11 or 3.12 — segfaults on Python 3.14
pip install "optimum-intel[openvino]"
```

### Usage

```bash
# Basic OpenVINO inference
cli.exe --openvino --prompt "What is Rust?"

# OpenVINO with fusion (multi-model panel)
cli.exe --openvino --fusion --prompt "Compare Python and Rust"

# OpenVINO with any task flag
cli.exe --openvino --sentiment --prompt "I love this product!"
cli.exe --openvino --text-generation --prompt "Once upon a time"
```

### Inference Priority (4-Tier Fallback)

When `--openvino` is used, the inference script tries backends in this order:

1. **Cached pre-converted model** — loads from `ov_models/` via optimum-intel (fastest)
2. **Auto-convert via optimum-cli** — converts on first use, caches for next time
3. **openvino_genai LLMPipeline** — if `openvino-genai` is installed
4. **Classic OpenVINO pipeline** — downloads PyTorch model, converts to IR via
   `ov.convert_model()`, caches at `~/.cache/modelfusion_ov/`, compiles and infers

> **Note:** On Python 3.14, paths 1 and 2 are automatically skipped (optimum-intel
> segfaults on Python 3.14). Path 4 (classic OpenVINO) works perfectly and handles
> model conversion automatically.

### Auto-Convert During Fusion

When running `--openvino --fusion`, each model is **automatically converted on first use**:

| Run | What Happens | Time per Model |
|---|---|---|
| **1st run** | Download from HuggingFace → Convert PyTorch → OpenVINO IR → Cache → Infer | ~30-120 sec |
| **2nd+ run** | Load cached IR → Compile → Infer | ~5-10 sec |

For a 10-model fusion panel: first run ~15-30 min, second run ~1-2 min.

### Platform-Specific Optimizations

- **Linux**: Sets `OV_CPU_BIND_TYPE=NUMA` and `TOKENIZERS_PARALLELISM=true`
- **Windows**: Sets `OV_CPU_BIND_TYPE=THREAD` and `TOKENIZERS_PARALLELISM=false`

### How Open-Weights Models Are Loaded Faster

ModelFusion accelerates open-weights HuggingFace models through a **convert-once,
run-forever** strategy using OpenVINO's Intermediate Representation (IR) format.
On the first inference request, the system downloads the PyTorch model from
HuggingFace Hub and wraps it in a custom `LogitsOnlyWrapper` — a thin
`torch.nn.Module` that calls the model with `use_cache=False` and returns only
the logits tensor, bypassing the `DynamicCache` object that OpenVINO cannot trace.
This wrapped model is then converted to OpenVINO IR via `ov.convert_model()` using
`torch.jit.trace` under the hood, producing an optimized computation graph stored
as `model.xml` + `model.bin` files. These files are cached on disk at
`~/.cache/modelfusion_ov/<model_name>/<device>/`, keyed by model ID and target
device. On every subsequent run, the cached IR is loaded directly with
`core.read_model()` — skipping the entire download, PyTorch loading, and
conversion pipeline — reducing startup from minutes to seconds. The IR model is
then compiled with device-specific tuning: CPU inference uses `LATENCY` mode with
thread count matched to available cores, while GPU inference uses `THROUGHPUT`
mode with auto-batching. Finally, an autoregressive generation loop runs token-by-token
through the compiled model, applying temperature-scaled sampling or greedy
decoding, until the end-of-sequence token is produced or `max_tokens` is reached.
This approach works natively on all Python versions (including 3.14) because it
relies only on `openvino`, `torch`, and `transformers` — no `optimum-intel` C
extensions required.

---

## OpenVINO Model Preparation (Optimum-Intel)

Pre-converting models to OpenVINO IR format with INT8/INT4 quantization provides
the best performance. **Requires Python 3.11 or 3.12** (not 3.14).

### Requirements

```bash
# Python 3.11 or 3.12 required
pip install "optimum-intel[openvino]"
```

### Single Model Preparation

```bash
# Convert a model to INT8 (default)
cli.exe --prepare-model Qwen/Qwen2.5-1.5B-Instruct

# Convert to INT4 (smallest, ~6x compression)
cli.exe --prepare-model Qwen/Qwen2.5-0.5B-Instruct --weight-format int4

# Convert to FP16 (highest quality)
cli.exe --prepare-model meta-llama/Llama-3.2-1B-Instruct --weight-format fp16

# Custom output directory
cli.exe --prepare-model Qwen/Qwen2.5-1.5B-Instruct --ov-model-dir my_models
```

### Batch Preparation (with --update)

```bash
# Update database + auto-prepare small models (≤3B params)
cli.exe --update --prepare-all-models --weight-format int8

# Prepare ALL models from database (standalone, can take hours)
cli.exe --prepare-all-models --weight-format int8
```

When combined with `--update`, only models ≤ 6000 MB (~3B params) are prepared.
This keeps processing time under ~30 minutes.

**Running twice is safe** — already-converted models are automatically skipped:
```
[1/20] Qwen/Qwen2.5-0.5B-Instruct    ⏭️ Already cached
[2/20] Qwen/Qwen2.5-1.5B-Instruct    ⏭️ Already cached
```

### Weight Format Comparison

| Format | Compression | Quality | Memory (1.5B model) | Speed |
|---|---|---|---|---|
| `fp16` | 2x | Highest | ~3.0 GB | Baseline |
| `int8` | 4x | Very good | ~1.5 GB | Faster |
| `int4` | 6-8x | Good | ~0.9 GB | Fastest |

### Cache Structure

Pre-converted models are stored in the `ov_models/` directory:

```
ov_models/
  qwen2.5-1.5b-instruct-int8/
    openvino_model.xml
    openvino_model.bin
    tokenizer.json
    tokenizer_config.json
    metadata.json          # export date, format, model ID
```

Classic OpenVINO auto-converted models are cached at:
```
~/.cache/modelfusion_ov/
  Qwen_Qwen2.5-1.5B-Instruct/
    cpu/
      model.xml
      model.bin
```

---

## vLLM (Linux GPU)

vLLM provides high-throughput inference with continuous batching on NVIDIA GPUs.

### Requirements

- Linux (not available on native Windows)
- NVIDIA GPU with CUDA support
- `pip install vllm`

### Usage

```bash
# vLLM inference
cli --vllm --prompt "What is machine learning?"

# vLLM with fusion
cli --vllm --fusion --prompt "Compare neural networks"
```

### Features

- Auto-detects GPU count for tensor parallelism
- Continuous batching for maximum throughput
- Supports HuggingFace model IDs directly
- `trust_remote_code=True` enabled by default

---

## Ollama

Ollama provides easy local model serving with a simple API.

### Requirements

- Install [Ollama](https://ollama.ai)
- Pull a model: `ollama pull llama3.2`

### Usage

```bash
# Ollama inference
cli.exe --ollama --prompt "Explain quantum computing"

# Ollama with fusion
cli.exe --ollama --fusion --prompt "Compare databases"
```

---

## Transformers (Default)

The default fallback uses HuggingFace Transformers with PyTorch.

### Requirements

```bash
pip install torch transformers
```

### Usage

```bash
# Default transformers inference (no backend flag needed)
cli.exe --text-generation --prompt "Once upon a time"

# Explicit transformers with fusion
cli.exe --fusion --prompt "Explain AI"
```

### Features

- Auto-detects CUDA for GPU acceleration
- Falls back to CPU if no GPU available
- Supports all HuggingFace model IDs

---

## Backend Selection Logic

Backend selection happens early in the CLI, before any task dispatch:

```
1. --vllm       → Check Linux + vllm installed → Set MODELFUSION_USE_VLLM
2. --ollama     → Check Ollama running          → Set MODELFUSION_USE_OLLAMA
3. --openvino   → Check OpenVINO installed       → Set MODELFUSION_USE_OPENVINO
                                                  → Set MODELFUSION_OV_MODEL_DIR
                                                  → Set MODELFUSION_OV_WEIGHT_FORMAT
4. (default)    → Use transformers              → Set MODELFUSION_USE_TRANSFORMERS
```

These environment variables are read by `providers.rs` at inference time to
select the correct Python script:

| Env Var | Script |
|---|---|
| `MODELFUSION_USE_OPENVINO` | `src/scripts/run_model_openvino.py` |
| `MODELFUSION_USE_VLLM` | `src/scripts/run_model_vllm.py` |
| `MODELFUSION_USE_OLLAMA` | *(Ollama HTTP API)* |
| `MODELFUSION_USE_TRANSFORMERS` | `src/scripts/run_model_transformers.py` |

All backends work with all task flags (`--fusion`, `--sentiment`,
`--text-generation`, etc.).

---

## Known Issues

### Python 3.14 Compatibility

`optimum-intel` (specifically its C extensions via NNCF/OpenVINO) **segfaults
on Python 3.14** with exit code `0xC0000005` (ACCESS_VIOLATION).

**Impact:** `--prepare-model`, `--prepare-all-models`, and optimum-intel inference
paths are unavailable on Python 3.14.

**Workaround:** The classic OpenVINO pipeline (`ov.convert_model()`) works
perfectly on Python 3.14. Models are auto-converted and cached on first use.

**Fix:** Install Python 3.11 or 3.12 in a virtual environment:
```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install "optimum-intel[openvino]" transformers torch
```

### Diagnostic Script

Run `src/scripts/check_openvino.py` to verify package availability:
```bash
python src/scripts/check_openvino.py
```
