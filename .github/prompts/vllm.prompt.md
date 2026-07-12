---
name: vllm
description: Use vLLM for high-throughput inference (Linux)
---
# vLLM High-Throughput Inference

Uses vLLM for high-throughput LLM inference on Linux systems.

## Usage
- Serves LLMs with PagedAttention for efficient memory management
- Supports continuous batching for maximum throughput
- Compatible with HuggingFace model hub and custom checkpoints
- Requires Linux with CUDA-capable GPU; not supported on Windows
