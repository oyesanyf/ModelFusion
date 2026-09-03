## 2026-09-01T00:58:46Z
You are a Dashboard UI & IPC Core Worker (teamwork_preview_worker) for Milestones M1 & M2 of the HugOS Multi-Agent Teams, OpenEvolve, and AVO Dashboard implementation.

Working Directory (Metadata): D:\harfile\ModelFusion\.agents\worker_m1_m2
Codebase Directory: D:\harfile\ModelFusion\IDE\vscode\extensions\copilot
Original Request Path: D:\harfile\ModelFusion\.agents\ORIGINAL_REQUEST.md
Project Plan Path: D:\harfile\ModelFusion\PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Mission:
1. Implement Milestone M1 (Activity Bar & Core Webview Framework) & M2 (Real-Time IPC & Event Stream Engine) in `D:\harfile\ModelFusion\IDE\vscode\extensions\copilot`:
   - `package.json`: Add view container `hugos-dashboard-container` to `viewsContainers.activitybar` with icon and title "HugOS Studio"; register view `hugos.dashboardView` under `contributes.views`.
   - Implement `src/extension/dashboard/dashboardViewProvider.ts`: `WebviewViewProvider` and Webview Panel manager with full lifecycle management, state retention, and bidirectional `postMessage` messaging.
   - Implement `src/extension/dashboard/dashboardHtml.ts`: Responsive, dark glassmorphism theme HTML/CSS/JS template containing:
     - Header with title, backend status indicator, and preset quick-selector.
     - Multi-Agent Teams section (hierarchy tree, agent status cards, live thought stream logs).
     - OpenEvolve & AVO Studio section (run controls, generation metrics, SVG/Canvas 60fps fitness score graphs, candidate comparison cards).
     - IPC & event telemetry log panel.
   - Implement `src/extension/dashboard/eventStreamService.ts`: Decoupled asynchronous ring buffer with 16.6ms (60fps) frame-throttled batch dispatcher broadcasting to active webviews.
   - Implement `src/extension/dashboard/evolutionStateManager.ts`: Centralized state machine (IDLE, RUNNING, PAUSED, COMPLETED, STOPPED) managing active run state, metrics history, candidate cache, and agent thoughts.
   - Implement `src/extension/dashboard/teamPresetManager.ts`: Presets ("Architect-Worker Swarm", "AVO Optimizer", "Local Sandbox", "Security Auditor") and role configs (Lead Architect Pro, Worker Flash, AVO Agent, Evaluator).
   - Hook into extension activation in `src/extension/extension/vscode-node/contributions.ts` and register commands (`hugos.dashboard.open`, `hugos.dashboard.refresh`, `hugos.dashboard.resetState`).
2. Run build / compile check (`npm run compile` or `node .esbuild.mts --dev`) to verify clean compilation.
3. Deliverables:
   - Implement source code files.
   - Write your handoff report to `D:\harfile\ModelFusion\.agents\worker_m1_m2\handoff.md` with build command outputs and verification details.
   - Send completion message via send_message to parent.
