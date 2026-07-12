---
name: sinq
description: Enable SINQ quantization
---
# SINQ Quantization

Enables Stochastic Integer Quantization (SINQ) for model compression.

## Usage
- Quantizes model weights to INT4/INT8 with minimal accuracy loss
- Uses stochastic rounding to preserve model quality during compression
- Reduces memory footprint and accelerates inference on CPU
- Supports calibration with custom datasets for task-specific tuning
