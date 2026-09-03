## 2026-08-31T20:05:40Z
You are a Studio Diff & Chat Sync Worker (teamwork_preview_worker) for Milestones M3, M4, and M5 of the HugOS Multi-Agent Teams, OpenEvolve, and AVO Dashboard implementation.

Working Directory (Metadata): D:\harfile\ModelFusion\.agents\worker_m3_m4_m5
Codebase Directory: D:\harfile\ModelFusion\IDE\vscode\extensions\copilot
Original Request Path: D:\harfile\ModelFusion\.agents\ORIGINAL_REQUEST.md
Project Plan Path: D:\harfile\ModelFusion\PROJECT.md
Test Infra Path: D:\harfile\ModelFusion\TEST_INFRA.md
Test Ready Path: D:\harfile\ModelFusion\TEST_READY.md

Your Mission:
1. Implement Milestone M3 (Teams Panel & Thought Streams enhancements), M4 (OpenEvolve & AVO Studio, Virtual Candidate Content Provider, Side-by-Side Diff Viewer, Atomic WorkspaceEdit Patch Apply), and M5 (Chat & Slash Command Bidirectional Synchronization):
   - Implement `src/extension/dashboard/candidateContentProvider.ts`:
     - Implements `vscode.TextDocumentContentProvider` for scheme `hugos-candidate`.
     - Resolves candidate code from `EvolutionStateManager` candidate cache.
     - Registers scheme `hugos-candidate` with `vscode.workspace.registerTextDocumentContentProvider`.
   - Implement `src/extension/dashboard/candidateApplier.ts`:
     - Native side-by-side diff launcher using `vscode.commands.executeCommand('vscode.diff', baselineUri, candidateUri, title)`.
     - Atomic `WorkspaceEdit` patch applier applying candidate code directly to workspace files with auto-save.
     - Snapshotting / backup mechanism enabling atomic rollback (`rollbackCandidatePatch`).
   - Connect OpenEvolve & AVO Execution Engine:
     - Connect `DashboardViewProvider` and `EvolutionStateManager` launch/stop/pause/resume triggers to actual `modelFusionProvider.ts` evolution pipelines (`_runOpenEvolve`, `_runAvoEvolve`) or runner services.
   - Implement Milestone M5 (Chat & Slash Command Synchronization):
     - Update `src/extension/byok/vscode-node/modelFusionProvider.ts` to bridge with `evolutionStateManager` and `eventStreamService`.
     - When `/evolve` or `@agent` is executed in the chat panel, emit lifecycle events, thoughts, and metrics to `EvolutionStateManager` and `EventStreamService` so the dashboard reflects progress live.
     - When the dashboard launches evolution or switches presets, sync active config/preset with `ModelFusionLMProvider`.
   - Register new providers, commands, and contributions in `src/extension/dashboard/dashboardContribution.ts` and `package.json` if needed.
2. Verify:
   - Build extension: `node .esbuild.mts --dev` in `D:\harfile\ModelFusion\IDE\vscode\extensions\copilot`.
   - Run unit tests: `npx.cmd vitest run src/extension/dashboard/test/`.
   - Run master E2E test suite: `node D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\test\dashboard\run_all_tests.mjs`.
3. Deliverables:
   - Complete, genuine, strictly-typed implementation of all components.
   - Write your handoff report to `D:\harfile\ModelFusion\.agents\worker_m3_m4_m5\handoff.md` including test results and build logs.
   - Send completion message via send_message to parent.
