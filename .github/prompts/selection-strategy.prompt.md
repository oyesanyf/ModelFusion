---
name: selection-strategy
description: Set model selection strategy
---
# Model Selection Strategy

Configures the model selection strategy for inference routing.

## Usage
- Choose from strategies: accuracy-first, speed-first, balanced, or cost-optimized
- Set priority weights for latency, quality, and resource usage
- Define fallback order when preferred models are unavailable
- Applies strategy globally or per-task-type with overrides
