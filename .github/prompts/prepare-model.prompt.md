---
name: prepare-model
description: Convert model to OpenVINO IR format
---
# Prepare Model for OpenVINO

Converts ML models to OpenVINO Intermediate Representation (IR) format for optimized inference.

## Usage
- Converts PyTorch, TensorFlow, and ONNX models to OpenVINO IR
- Applies graph optimizations: layer fusion, constant folding, quantization
- Targets Intel CPUs, GPUs, and VPUs for hardware-accelerated inference
- Validates converted model accuracy against the original
