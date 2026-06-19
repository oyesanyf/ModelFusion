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

---

## Backend Overview

| Backend | Flag | Platform | Hardware | Best For |
|---|---|---|---|---|
| **OpenVINO** | `--openvino` | Windows + Linux | Intel CPU/iGPU | Fast CPU inference, INT8/INT4 quantization |
| **vLLM** | `--vllm` | Linux only | NVIDIA GPU + CUDA | High-throughput GPU inference |
| **Ollama** | `--ollama` | Windows + Linux | CPU or GPU | Easy setup, local model serving |
| **Transformers** | *(default)* | Windows + Linux | CPU or CUDA GPU | Universal fallback |

---

## OpenVINO (Recommended for CPU)

OpenVINO provides optimized inference on Intel hardware (CPUs, iGPUs, VPUs).

### Installation

```bash
# Option 1: OpenVINO GenAI (recommended, best performance)
pip install -U openvino-genai

# Option 2: Classic OpenVINO (fallback)
pip install -U openvino

# Option 3: Optimum-Intel (enables auto-convert + cache)
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

### Inference Priority

When `--openvino` is used, the inference script tries backends in this order:

1. **Cached pre-converted model** — loads from `ov_models/` (fastest, ~1-3 sec)
2. **Auto-convert via optimum-intel** — converts on first use, caches for next time
3. **openvino_genai LLMPipeline** — if `openvino-genai` is installed
4. **Classic OpenVINO pipeline** — manual PyTorch → ONNX → IR conversion (slowest)

### Platform-Specific Optimizations

- **Linux**: Sets `OV_CPU_BIND_TYPE=NUMA` and `TOKENIZERS_PARALLELISM=true`
- **Windows**: Sets `OV_CPU_BIND_TYPE=THREAD` and `TOKENIZERS_PARALLELISM=false`

---

## OpenVINO Model Preparation (Optimum-Intel)

Pre-converting models to OpenVINO IR format dramatically speeds up inference
by eliminating download + conversion overhead on every run.

### Requirements

```bash
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

### Batch Preparation

```bash
# Convert ALL models from database (can take hours for large databases)
cli.exe --prepare-all-models --weight-format int8

# Recommended: combine with --update to refresh DB + prepare small models
cli.exe --update --prepare-all-models --weight-format int8
```

When combined with `--update`, only models ≤ 6000 MB (~3B params) are prepared
to keep the process under ~30 minutes.

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
  llama-3.2-1b-instruct-int4/
    ...
```

Models are automatically discovered by name matching — no configuration needed.

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
