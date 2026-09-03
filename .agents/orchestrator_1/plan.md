# Execution Plan: HugOS IDE Multi-Agent Teams, OpenEvolve, and AVO Dashboard

## Objectives
Implement and rigorously verify:
1. Native Activity Bar & Multi-Agent Dashboard UI (Teams hierarchy, roles, thought streams, config presets).
2. OpenEvolve & AVO Evolutionary Search Studio (launch/pause/stop, live fitness graphs, candidate diff viewer, one-click patch apply).
3. Real-Time IPC & Event Streaming Architecture (non-blocking async IPC to ModelFusion /orchestrate, /evolve, AVO runners, MCP).
4. Command & Participant Synchronization (@agent, /evolve, slash commands bidirectional sync).

## Step-by-Step Plan
1. **Survey Phase**:
   - Dispatch 3 parallel subagents (Explorers / Spec Miner) to investigate `D:\harfile\ModelFusion\IDE` and `D:\harfile\ModelFusion` backend/API contracts.
   - Aggregate findings and build `PROJECT.md` (Architecture, Feature Inventory, Milestones, Interface Contracts, Code Layout).
2. **Dual-Track Decomposition**:
   - **Track A (E2E Testing Track)**: Build `TEST_INFRA.md`, generate Tier 1-4 tests (Feature, Boundary, Combinatorial, Real-World) publishing `TEST_READY.md`.
   - **Track B (Implementation Track)**: Implement core components across partitioned milestones:
     - M1: Activity Bar & Core Webview Framework
     - M2: Real-Time Non-Blocking IPC & Event Stream Engine
     - M3: Multi-Agent Teams Panel & Thought Streams
     - M4: OpenEvolve & AVO Studio (Controls, Metrics Graphs, Diff Viewer, Patch Applicator)
     - M5: Chat Participant & Slash Command Synchronization
3. **Verification, Adversarial Hardening & Audit**:
   - Run full E2E test suite.
   - Run Challenger adversarial tests (Tier 5).
   - Run Forensic Auditor integrity checks.
4. **Final Delivery**:
   - Generate summary report and notify parent agent.
