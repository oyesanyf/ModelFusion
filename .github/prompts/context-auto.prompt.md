---
name: context-auto
description: Auto-include relevant workspace context
---
# Auto-Context Inclusion

Automatically includes relevant workspace files and context in prompts.

## Usage
- Scans the workspace to identify files relevant to the current task
- Injects related source files, configs, and docs into the prompt context
- Uses semantic similarity to rank and select the most useful files
- Respects `.gitignore` and custom exclusion patterns
