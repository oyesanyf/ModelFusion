---
name: wikiskill
description: Operate WikiSkill workflows that compile task experience into persistent knowledge for skill evolution, and perform deep Wikipedia knowledge distillation, hierarchical section retrieval, cross-reference linking, and verified citation grounding.
---

# WikiSkill Knowledge & Skill Evolution Engine

Help the user improve recurring agent tasks through persistent experience compilation, and distill structured Wikipedia domain knowledge with full section retrieval, cross-reference linking, and citation grounding.

## 1. Core Principles & 3-Layer Architecture

WikiSkill operates across three distinct persistence layers (arXiv:2608.27454):

| Layer | What It Retains | Purpose |
|---|---|---|
| **Raw Experience** | Task inputs, tool calls, model outputs, verification logs, and human feedback | Ephemeral execution history, failure modes, and tracebacks |
| **Persistent Knowledge Wiki** | Sourced patterns, factual encyclopedic distillations, section outlines, cross-references, and counterexamples | Enduring, reusable knowledge base compiled across multiple agent runs |
| **Operational Skills** | Concrete procedural instructions (`SKILL.md`) executed by the agent | Practical rules, guardrails, and executable skills |

## 2. Roles in the Evolution Loop

1. **Wiki Maintainer**: Consolidates user feedback, test execution results, and encyclopedic facts into structured, citation-grounded wiki articles. Retains original user feedback words while connecting them to generalized patterns.
2. **Skill Proposer**: Translates learned patterns and section outlines into candidate agent instructions and guardrails.
3. **Independent Evaluator (Validation Gate)**: Evaluates candidate skills against baseline executions on validation tasks. A candidate is adopted ONLY when empirical performance strictly improves (ties and regressions retain the incumbent).

## 3. Wikipedia Knowledge Distillation Pipeline

When invoked via `@agent wiki <topic>` or `/wiki <topic>`:
- **Search & Disambiguation**: Queries Wikipedia's authoritative search API to identify primary article targets and related concepts, with direct lookup fallback.
- **Lead Summary Extraction**: Retrieves concise, factual lead summaries free of wiki markup or formatting artifacts.
- **Deep Section Retrieval**: Extracts complete hierarchical Table of Contents (TOC) with levels, headings, and anchors, enabling precise sub-topic navigation (following redirects automatically via `&redirects=1`).
- **Cross-Reference Linking**: Identifies related internal encyclopedic concepts and wikilinks to form a domain knowledge graph.
- **Citation Grounding**: Extracts external citations, research preprints, DOIs, and primary sources to verify claims inline using numbered references (`[1]`, `[2]`).

## 4. Invocation & CLI Directives

- **Chat Commands**:
  - `@agent wiki <topic>` — Distill Wikipedia knowledge with summary, section hierarchy, cross-references, and citations.
  - `/wiki <topic>` — Slash command equivalent with 1:1 functional parity.
  - `/wiki feedback <note>` — Record execution feedback and lessons into the persistent workspace wiki.
  - `/wiki status` — Display current 3-layer architecture status, active skill versions, and evaluation gates.
- **Master CLI Execution**:
  - `cli.exe --wiki "<topic>"`
  - `cli.exe --wiki feedback "<lesson learned>"`
  - `cli.exe --wiki status`
  - `cli.exe /wiki "<topic>"`
  - `cli.exe @agent wiki "<topic>"`
- **HTTP Server Endpoint**:
  - `GET /api/wiki?q=<topic>&action=distill`
  - `GET /api/wiki?q=<topic>&action=search`
  - `GET /api/wiki?q=<topic>&action=sections`
  - `GET /api/wiki?q=<topic>&action=article`
- **MCP Tool**:
  - `wiki` in ModelFusion Master MCP Catalog (`category: "web"`).

