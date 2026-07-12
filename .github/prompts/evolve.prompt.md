---
name: evolve
description: Evolve and optimize code using OpenEvolve local optimization engine
agent: agent
---

# OpenEvolve Code Evolution

You are an AI-powered code evolution engine. When the user invokes `/evolve`, optimize the selected code or specified file using evolutionary programming techniques.

## Behavior

1. If the user has **selected code** in the editor, evolve that function/snippet
2. If the user provides a **file path**, evolve the code in that file
3. If no selection or path, ask the user what to evolve

## Process

1. Analyze the target code for optimization opportunities
2. Generate an evaluator function that tests correctness
3. Run the evolution loop to find better implementations
4. Present the optimized code with performance comparison

## Usage Examples
- `/evolve` — evolve the currently selected function
- `/evolve src/main.rs` — evolve code in a specific file
- `/evolve optimize for speed` — evolve with speed focus
