---
name: wikiskill
description: Operate WikiSkill workflows that compile task experience into persistent knowledge for skill evolution, and perform deep Wikipedia knowledge distillation, hierarchical section retrieval, cross-reference linking, and verified citation grounding.
---

# WikiSkill Knowledge & Skill Evolution Engine

Help the user improve recurring agent tasks through persistent experience compilation, and distill structured Wikipedia domain knowledge with full section retrieval, cross-reference linking, and citation grounding.

## 1. Core Principles

WikiSkill operates across three distinct persistence layers:

| Layer | What It Retains | Purpose |
|---|---|---|
| **Raw Experience** | Task inputs, tool calls, model outputs, verification logs, and human feedback | Ephemeral execution history and error tracebacks |
| **Persistent Knowledge Wiki** | Sourced patterns, factual encyclopedic distillations, section outlines, cross-references, and counterexamples | Enduring knowledge base compiled across runs |
| **Operational Skills** | Concrete procedural instructions (`SKILL.md`) executed by the agent | Practical rules and guardrails governing behavior |

## 2. Roles in the Evolution Loop

1. **Wiki Maintainer**: Consolidates user feedback, test execution results, and encyclopedic facts into structured, citation-grounded wiki articles.
2. **Skill Proposer**: Translates learned patterns and section outlines into candidate agent instructions and guardrails.
3. **Independent Evaluator**: Evaluates candidate skills against baseline executions on validation tasks, accepting changes only when empirical metrics improve without regressing prior constraints.

## 3. Wikipedia Knowledge Distillation Pipeline

When invoked via `@agent wiki <topic>` or `/wiki <topic>`:
- **Search & Disambiguation**: Queries Wikipedia's authoritative search API to identify primary article targets and related concepts.
- **Lead Summary Extraction**: Retrieves concise, factual lead summaries free of wiki markup or formatting artifacts.
- **Deep Section Retrieval**: Extracts complete hierarchical Table of Contents (TOC) with levels, headings, and anchors, enabling precise sub-topic navigation.
- **Cross-Reference Linking**: Identifies related internal encyclopedic concepts and wikilinks to form a domain knowledge graph.
- **Citation Grounding**: Extracts external citations, research preprints, DOIs, and primary sources to verify claims inline using numbered references (`[1]`, `[2]`).

## 4. Invocation & CLI Directives

- **Chat Commands**:
  - `@agent wiki <topic>` — Distill Wikipedia knowledge with summary, section hierarchy, cross-references, and citations.
  - `/wiki <topic>` — Slash command equivalent with 1:1 functional parity.
  - `@agent wikiskill <goal>` — Compile experience into persistent wiki knowledge.
- **Master CLI Execution**:
  - `cli.exe --wiki "<topic>"`
  - `cli.exe /wiki "<topic>"`
  - `cli.exe @agent wiki "<topic>"`
- **HTTP Server Endpoint**:
  - `GET /api/wiki?q=<topic>&action=distill`
  - `GET /api/wiki?q=<topic>&action=search`
  - `GET /api/wiki?q=<topic>&action=sections`
  - `GET /api/wiki?q=<topic>&action=article`
- **MCP Tool**:
  - `wiki` in ModelFusion Master MCP Catalog (`category: "web"`).
