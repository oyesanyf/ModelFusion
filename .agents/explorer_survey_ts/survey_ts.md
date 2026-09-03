# ModelFusion TypeScript & IDE Extension Safety & Architectural Survey

**Survey Target**: TypeScript & IDE Extension Subsystem (`IDE/`, `src/`, extensions, webviews, IPC streaming, participants)  
**Surveyor**: TypeScript & IDE Extension Explorer (`explorer_survey_ts`)  
**Audit Date**: September 1, 2026  
**Status**: Comprehensive Survey Completed  

---

## Executive Summary

This report delivers a comprehensive code review, safety audit, resource lifecycle analysis, concurrency evaluation, error resilience assessment, and architectural mapping of all TypeScript and JavaScript modules in the ModelFusion / HugOS codebase.

### Overall Subsystem Assessment:
- **Architectural Design**: Exceptional modular design integrating a native Activity Bar Webview Dashboard (`DashboardViewProvider`), real-time 60fps asynchronous IPC streaming (`EventStreamService`), multi-agent team preset management (`TeamPresetManager`), virtual document diff provider (`OpenEvolveContentProvider`), atomic workspace patch applier (`CandidateApplier`), and language model backend orchestrator (`ModelFusionLMProvider`).
- **Critical Vulnerabilities & Bugs Found**:
  1. **[CRITICAL] Runtime Crash on Backend Process Exit**: `modelFusionProvider.ts:269` invokes non-existent method `this._spawnPersistentServer()` inside an unexpected exit handler, throwing `TypeError` in a timer callback.
  2. **[CRITICAL] Runtime ReferenceError in Built-in Evolution**: `modelFusionProvider.ts:1553` references undeclared variable `ollamaModel` inside `_runBuiltinEvolve()`, causing runtime crashes on non-Python evolution runs.
  3. **[HIGH] Synchronous Event-Loop Blocking Call**: `modelManagerPanel.ts:74` executes `child_process.execSync('ollama list')` directly on the extension host main thread, blocking editor typing and UI responsiveness for up to 10 seconds.
  4. **[HIGH] Undisposed MCP Definition Provider Registration**: `modelFusionMcp.contribution.ts:106` registers `lm.registerMcpServerDefinitionProvider` without adding it to `this._register(...)` or a disposal lifecycle, leaking on deactivation.
  5. **[HIGH] Leaked Global Workspace Event Listeners**: `modelFusionProvider.ts:110, 115, 142` registers `onDidChangeTextDocument`, `onDidChangeConfiguration`, and `registerCommand` without storing or registering disposables.

---

## 1. Codebase Inventory & Module Map

| Module Path | Size / Lines | Primary Role | Key Classes / Exports |
|---|---|---|---|
| `IDE/vscode/extensions/copilot/src/extension/dashboard/dashboardContribution.ts` | 193 lines (5.9 KB) | Central dashboard extension contribution & command registration | `DashboardContribution` |
| `IDE/vscode/extensions/copilot/src/extension/dashboard/dashboardViewProvider.ts` | 236 lines (6.6 KB) | Activity Bar WebviewView & Editor Panel Webview Provider | `DashboardViewProvider` |
| `IDE/vscode/extensions/copilot/src/extension/dashboard/evolutionStateManager.ts` | 448 lines (13.3 KB) | Reactive state store for evolutionary search runs, candidates, thoughts, metrics | `EvolutionStateManager` |
| `IDE/vscode/extensions/copilot/src/extension/dashboard/teamPresetManager.ts` | 358 lines (10.9 KB) | Multi-agent team preset registry, role allocation, token tracking | `TeamPresetManager` |
| `IDE/vscode/extensions/copilot/src/extension/dashboard/eventStreamService.ts` | 400 lines (10.3 KB) | 60fps Async Ring Buffer, Webview IPC event streaming, backend polling | `EventStreamService`, `AsyncRingBuffer` |
| `IDE/vscode/extensions/copilot/src/extension/dashboard/candidateApplier.ts` | 256 lines (7.6 KB) | Native side-by-side diff launcher, atomic `WorkspaceEdit` applier, rollback history | `CandidateApplier` |
| `IDE/vscode/extensions/copilot/src/extension/dashboard/candidateContentProvider.ts` | 89 lines (3.2 KB) | Virtual `hugos-candidate://` TextDocumentContentProvider | `OpenEvolveContentProvider` |
| `IDE/vscode/extensions/copilot/src/extension/dashboard/dashboardHtml.ts` | 1,522 lines (44.6 KB) | Dark-theme native HTML/CSS/JS frontend UI, SVG graphs, agent tree, candidate diff viewer | `getDashboardHtml()` |
| `IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionProvider.ts` | 2,690 lines (119.2 KB) | Core ModelFusion LM Provider, process lifecycle, `/orchestrate` HTTP client, slash command router | `ModelFusionLMProvider` |
| `IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionMcp.contribution.ts` | 109 lines (3.9 KB) | VS Code Stdio MCP Server Provider for `cli.exe --mcp` | `ModelFusionMcpContrib` |
| `IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/byokContribution.ts` | 97 lines (5.1 KB) | Unconditionally registers `ModelFusionLMProvider` with VS Code LM API | `BYOKContrib` |
| `IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelManagerPanel.ts` | 686 lines (18.3 KB) | Model Manager Webview for Ollama, OpenVINO, and Transformer models | `ModelManagerPanel` |
| `IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/evolve/inlineDiff.ts` | 317 lines (10.8 KB) | Cursor-style inline Accept/Reject decorations and status bar controls | `InlineDiffManager` |
| `IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/evolve/evolveEngine.ts` | 473 lines (16.8 KB) | Evolution file generator, prompt builder, candidate response cleaner | `cleanModelResponse`, `EvolveFiles` |
| `IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/evolve/fallbackEvaluator.ts` | 260 lines (9.1 KB) | Dynamic Python test evaluator generator for evolutionary search | `generateFallbackEvaluator` |
| `IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/security/securityAudit.ts` | 395 lines (15.1 KB) | `/security` code scanning, taint analysis prompt generator, auto-fix driver | `SecurityAuditor` |
| `IDE/vscode/extensions/copilot/src/extension/dashboard/test/dashboardM1M2.spec.ts` | 268 lines (9.9 KB) | Vitest specification for TeamPresetManager, EvolutionStateManager, RingBuffer | Test Suite |
| `IDE/vscode/extensions/copilot/src/extension/dashboard/test/dashboardM3M4M5.spec.ts` | 254 lines (10.8 KB) | Vitest specification for CandidateProvider, CandidateApplier, ThoughtStream | Test Suite |
| `IDE/vscode/extensions/copilot/test/modelFusion/dashboardM1M2.test.ts` | 268 lines (10.3 KB) | Mocha integration test suite for Dashboard M1 & M2 | Test Suite |
| `IDE/test_e2e_suite.mjs` | 51 lines (2.0 KB) | Node.js standalone 19-feature 4-tier E2E test runner | Test Runner |
| `tests/e2e/test_e2e_harness.mjs` | 402 lines (14.3 KB) | E2E contract emulator, JSON-RPC 2.0 client, sanitization validator | Test Harness |

---

## 2. Deep Dive: Resource Lifecycle & Leak Audit

### 2.1 vscode.Disposable Usage & Registration
- **Finding TS-RL-1 [HIGH]**: In `modelFusionMcp.contribution.ts:106`:
  ```typescript
  // File: IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionMcp.contribution.ts:106
  this.disposable = lm.registerMcpServerDefinitionProvider('modelfusion', provider);
  ```
  `this.disposable` is assigned to a private property but is never passed to `this._register(...)` and `ModelFusionMcpContrib` does not implement a `dispose()` method to dispose it.
  - **Risk**: The MCP definition provider remains permanently registered in VS Code's internal registry even when the contribution or extension is deactivated.
  - **Remediation**:
    ```typescript
    this._register(lm.registerMcpServerDefinitionProvider('modelfusion', provider));
    ```

- **Finding TS-RL-2 [HIGH]**: In `modelFusionProvider.ts:110, 115, 142`:
  ```typescript
  // File: IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionProvider.ts
  vscode.commands.registerCommand('hugos.modelfusion.openModelManager', ...); // line 110
  vscode.workspace.onDidChangeTextDocument((e) => { ... });                   // line 115
  vscode.workspace.onDidChangeConfiguration((e) => { ... });                  // line 142
  ```
  None of these three subscriptions are wrapped with `this._register(...)`.
  - **Risk**: Memory leak of document edit listeners and configuration change listeners across extension life cycle. The document listener additionally schedules unmanaged timers (`setTimeout(..., 300)`).
  - **Remediation**: Wrap all three registrations in `this._register(...)`.

- **Finding TS-RL-3 [MEDIUM]**: In `modelFusionProvider.ts:67, 103`:
  ```typescript
  // File: IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionProvider.ts:67, 103
  private readonly _inlineDiff = new InlineDiffManager();
  ...
  this._inlineDiff.registerCommands();
  ```
  The disposables returned by `_inlineDiff.registerCommands()` (`vscode.Disposable[]`) and `this._inlineDiff` itself (which holds 4 `TextEditorDecorationType` instances) are never registered with `this._register(...)` or disposed in `disposeServer()`.
  - **Risk**: Leaks VS Code editor decoration types and command registrations.

- **Finding TS-RL-4 [MEDIUM]**: In `modelFusionProvider.ts:1792-1799`:
  ```typescript
  // File: IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionProvider.ts:1792
  const cancelReg = token?.onCancellationRequested(() => {
      this._logService.info('ModelFusionProvider: HTTP request cancelled. Aborting.');
      req.destroy();
      this._inflightMap.delete(promptText);
      resolve('[Request cancelled]');
  });
  ```
  `cancelReg` (`vscode.Disposable`) is never disposed on normal completion (`res.on('end')`, `req.on('error')`, `req.on('timeout')`).
  - **Risk**: For long-lived cancellation tokens, listener closures accumulate on the token.
  - **Remediation**: Call `cancelReg?.dispose()` in the `end`, `error`, `timeout`, and `finally` handlers.

- **Finding TS-RL-5 [LOW]**: In `modelFusionProvider.ts:1687`:
  ```typescript
  // File: IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionProvider.ts:1687
  const tokenSource = new vscode.CancellationTokenSource();
  ```
  `tokenSource` is never disposed after the evolutionary search call completes.
  - **Remediation**: Wrap in `try ... finally { tokenSource.dispose(); }`.

### 2.2 Map & Set Collection Retention
- **Finding TS-RL-6 [LOW]**: In `evolutionStateManager.ts:98, 347`:
  `_candidates = new Map<string, CandidateInfo>()` stores candidate patches without an upper size bound or LRU eviction, unlike `_metricsHistory` (capped at 5,000) and `_thoughts` (capped at 1,000).
  - **Risk**: Continuous evolutionary runs generating tens of thousands of candidate code snapshots could steadily grow memory until `resetState()` is invoked.
  - **Remediation**: Add a cap (e.g. 2,000 candidates) with eviction of oldest non-applied candidates.

- **Finding TS-RL-7 [VERIFIED CLEAN]**: In `eventStreamService.ts:110, 242-244`:
  `_webviews = new Set<vscode.Webview>()` properly returns a disposable that deletes the webview upon disposal:
  ```typescript
  return toDisposable(() => { this._webviews.delete(webview); });
  ```
  `dashboardViewProvider.ts:108-122` tracks `_webviewDisposables = new Map<vscode.Webview, IDisposable>()` and cleans up on `onDidDispose`.

### 2.3 Singleton Instance Lifecycle
- **Finding TS-RL-8 [LOW]**: In `teamPresetManager.ts:52`, `eventStreamService.ts:100`, and `candidateContentProvider.ts:16`:
  These classes set static `_instance = this` in constructor, but unlike `EvolutionStateManager` and `CandidateApplier`, they do not reset `_instance = undefined` in their `dispose()` overrides.

---

## 3. Deep Dive: Concurrency & Async UI Audit

### 3.1 Synchronous vs Asynchronous Execution
- **Finding TS-CU-1 [HIGH]**: In `modelManagerPanel.ts:74`:
  ```typescript
  // File: IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelManagerPanel.ts:74
  const result = child_process.execSync('ollama list', { encoding: 'utf-8', timeout: 10000 });
  ```
  `execSync` synchronously halts the Node.js event loop of the extension host process.
  - **Impact**: Freezes all editor interactions, typing, completions, and language server requests for up to 10 seconds if Ollama is slow or unresponsive.
  - **Remediation**: Replace with async `child_process.exec('ollama list', ...)` and await the result.

### 3.2 60fps Event Streaming & Async Ring Buffer
- **Finding TS-CU-2 [EXEMPLARY]**: In `eventStreamService.ts:31-96, 254-319`:
  - `AsyncRingBuffer<T>` implements a fixed-size (4,096 items) circular buffer.
  - Push is O(1) non-blocking. When capacity is reached, it overwrites the oldest unconsumed event and increments `_droppedCount` without blocking the producer.
  - Drain is O(N) array slice.
  - `_dispatchTimer` runs at ~16ms (60fps), draining all queued events into a single batched IPC message (`batchEvents`).
  - Webview updates do not overwhelm the IPC channel or block UI rendering.

### 3.3 HTTP Polling & Socket Timeout Management
- **Finding TS-CU-3 [EXEMPLARY]**: In `eventStreamService.ts:323-378`:
  `_pollBackendStats()` uses `http.get('http://127.0.0.1:5000/stats', { timeout: 800 }, ...)` with explicit `req.on('timeout', () => req.destroy())` and `req.on('error', ...)`.
  - Non-blocking execution prevents UI stalls when the backend server is offline or restarting.

### 3.4 Request Coalescing & Promise Safety
- **Finding TS-CU-4 [EXEMPLARY]**: In `modelFusionProvider.ts:1100-1114`:
  `_inflightMap` deduplicates concurrent identical requests by storing the active `Promise<string>` and deleting it in `.finally()`.

---

## 4. Deep Dive: Error Handling & Resilience Audit

### 4.1 Critical Runtime Bugs
- **Finding TS-EH-1 [CRITICAL]**: In `modelFusionProvider.ts:269`:
  ```typescript
  // File: IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionProvider.ts:259-272
  this._serverProcess.on('exit', (code) => {
      const msg = `Server process exited with code ${code}`;
      this._logService.warn(`ModelFusionProvider: Persistent server exited with code ${code}`);
      this._outputChannel.appendLine(`[Server] ${msg}`);
      
      // If _serverProcess is still truthy, it wasn't deliberately disposed
      if (this._serverProcess) {
          this._outputChannel.appendLine(`[Server] Unexpected exit. Respawning in 3 seconds...`);
          this._serverProcess = undefined;
          setTimeout(() => {
              this._spawnPersistentServer(); // BUG: METHOD DOES NOT EXIST!
          }, 3000);
      }
  });
  ```
  The method is declared as `private async startServer()` at line 151. `this._spawnPersistentServer` does not exist on `ModelFusionLMProvider`.
  - **Impact**: When the backend server crashes or is killed externally, the auto-respawn timer throws `TypeError: this._spawnPersistentServer is not a function`, failing to revive the server.
  - **Remediation**: Change line 269 to `this.startServer();`.

- **Finding TS-EH-2 [CRITICAL]**: In `modelFusionProvider.ts:1552-1553`:
  ```typescript
  // File: IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionProvider.ts:1550-1553
  const improved = await this._sendOrchestrationRequest(
      prompt, 10.0, 'fastest', 'multi-model', 1,
      false, true, false, false, true, ollamaModel, token // BUG: ollamaModel IS NOT DEFINED!
  );
  ```
  `_runBuiltinEvolve()` does not declare or extract `ollamaModel` from settings or parameters.
  - **Impact**: When `/evolve` is executed on any non-Python file (TypeScript, JavaScript, Rust, C++, etc.), the function immediately crashes with `ReferenceError: ollamaModel is not defined`.
  - **Remediation**: Add at line 1485:
    ```typescript
    const userConfig = vscode.workspace.getConfiguration('hugos.modelfusion');
    const ollamaModel = userConfig.get<string>('ollamaModel', 'qwen2.5:7b').trim() || 'qwen2.5:7b';
    ```

### 4.2 Webview Security & Content Sanitization
- **Finding TS-EH-3 [EXEMPLARY]**: In `dashboardHtml.ts:15, 1269, 1312, 1336`:
  - Strict CSP policy with random cryptographic nonces for script execution.
  - All dynamically formatted DOM elements utilize `escapeHtml()` to mitigate XSS risks from untrusted model outputs or file contents.

### 4.3 Virtual Document Traversal Defense
- **Finding TS-EH-4 [EXEMPLARY]**: In `candidateContentProvider.ts:54`:
  - Sanitizes URI path against directory traversal attempts (`..` segments).

---

## 5. Deep Dive: Architectural Layout & Integration Audit

### 5.1 Extension Host & Contribution Wiring
- `IDE/vscode/extensions/copilot/src/extension/extension/vscode-node/contributions.ts`:
  - Registers `DashboardContribution` (line 111)
  - Registers `ModelFusionMcpContrib` (line 106)
  - Registers `BYOKContrib` (line 110)
- `IDE/vscode/extensions/copilot/package.json`:
  - Declares all ModelFusion configuration schemas (`hugos.modelfusion.*`), commands, and tools.

### 5.2 Evolutionary Search & Multi-Agent Teams Architecture
1. **Activity Bar & Webview Panels**:
   - `hugos.dashboardView`: Sidebar webview in Activity Bar.
   - `hugos.dashboardPanel`: Full editor tab panel.
2. **Multi-Agent Presets**:
   - `architect_worker_swarm`: Lead Architect (Gemini 3.1 Pro) + Worker Alpha & Beta (Gemini 3.7 Flash) + Quality Gate Evaluator.
   - `avo_optimizer`: AVO Mutation Lead (Gemini 3.1 Pro) + MAP-Elites Evaluator + Fast Harness Runner.
   - `local_sandbox`: Local Lead Operator + Local Static Analyzer (GGUF).
   - `security_auditor`: Vulnerability Hunter (Gemini 3.1 Pro) + Forensic Diff Inspector + Policy Verifier.
3. **Diff & Patch System**:
   - Native side-by-side diffing via `vscode.diff` between `file://` baseline and `hugos-candidate://` virtual document.
   - Atomic workspace editing with automatic rollback backup history.

---

## 6. Actionable Findings & Severity Matrix

| ID | Location | Severity | Category | Summary & Impact |
|---|---|---|---|---|
| **TS-EH-1** | `modelFusionProvider.ts:269` | **CRITICAL** | Error Handling | `this._spawnPersistentServer()` does not exist; crash on unexpected server exit |
| **TS-EH-2** | `modelFusionProvider.ts:1553` | **CRITICAL** | Error Handling | `ollamaModel` is undeclared in `_runBuiltinEvolve()`; crashes on non-Python evolution |
| **TS-CU-1** | `modelManagerPanel.ts:74` | **HIGH** | Concurrency | `child_process.execSync('ollama list')` blocks extension host main thread for up to 10s |
| **TS-RL-1** | `modelFusionMcp.contribution.ts:106` | **HIGH** | Resource Leak | `lm.registerMcpServerDefinitionProvider` is not registered in disposables |
| **TS-RL-2** | `modelFusionProvider.ts:110,115,142` | **HIGH** | Resource Leak | Global event listeners (`onDidChangeTextDocument`, `onDidChangeConfiguration`) leaked |
| **TS-RL-3** | `modelFusionProvider.ts:67,103` | **MEDIUM** | Resource Leak | `InlineDiffManager` decoration types and commands never disposed |
| **TS-RL-4** | `modelFusionProvider.ts:1792` | **MEDIUM** | Resource Leak | `token.onCancellationRequested` disposable never cleaned up after HTTP response |
| **TS-RL-5** | `modelFusionProvider.ts:1687` | **LOW** | Resource Leak | `CancellationTokenSource` created without disposal |
| **TS-RL-6** | `evolutionStateManager.ts:98` | **LOW** | Memory Growth | Uncapped `_candidates` Map could grow during long sessions without reset |
| **TS-RL-7** | `teamPresetManager.ts:52` | **LOW** | Lifecycle | Singleton static `_instance` not cleared on `dispose()` |

---

## 7. Concrete Patch Proposals

### Patch 1: Fix Server Respawn & Undeclared Variable in `modelFusionProvider.ts`
```diff
--- a/IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionProvider.ts
+++ b/IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionProvider.ts
@@ -266,7 +266,7 @@
 					this._outputChannel.appendLine(`[Server] Unexpected exit. Respawning in 3 seconds...`);
 					this._serverProcess = undefined;
 					setTimeout(() => {
-						this._spawnPersistentServer();
+						this.startServer();
 					}, 3000);
 				}
@@ -1485,6 +1485,8 @@
 		let currentCode = originalCode;
 		let bestCode = originalCode;
 		let totalImprovements = 0;
+		const userConfig = vscode.workspace.getConfiguration('hugos.modelfusion');
+		const ollamaModel = userConfig.get<string>('ollamaModel', 'qwen2.5:7b').trim() || 'qwen2.5:7b';
```

### Patch 2: Fix Non-Blocking Model Detection in `modelManagerPanel.ts`
```diff
--- a/IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelManagerPanel.ts
+++ b/IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelManagerPanel.ts
@@ -72,8 +72,8 @@
 	private _detectOllamaModels() {
-		try {
-			const result = child_process.execSync('ollama list', { encoding: 'utf-8', timeout: 10000 });
+		child_process.exec('ollama list', { encoding: 'utf-8', timeout: 10000 }, (err, stdout) => {
+			if (err) {
+				this._panel.webview.postMessage({ type: 'ollamaDetected', models: [] });
+				return;
+			}
-			const lines = result.split('\n').filter(l => l.trim() && !l.startsWith('NAME'));
+			const lines = stdout.split('\n').filter(l => l.trim() && !l.startsWith('NAME'));
 			const models = lines.map(line => {
 				const parts = line.trim().split(/\s+/);
 				return parts[0] || '';
 			}).filter(Boolean);
 			this._panel.webview.postMessage({ type: 'ollamaDetected', models });
-		} catch {
-			this._panel.webview.postMessage({ type: 'ollamaDetected', models: [] });
-		}
+		});
 	}
```

### Patch 3: Fix Disposable Registration in `modelFusionMcp.contribution.ts`
```diff
--- a/IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionMcp.contribution.ts
+++ b/IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionMcp.contribution.ts
@@ -94,7 +94,6 @@
 export class ModelFusionMcpContrib extends Disposable {
-	private disposable?: IDisposable;
 
 	constructor(
@@ -106,3 +105,3 @@
 		const provider = new ModelFusionMcpDefinitionProvider(this.logService);
-		this.disposable = lm.registerMcpServerDefinitionProvider('modelfusion', provider);
+		this._register(lm.registerMcpServerDefinitionProvider('modelfusion', provider));
 	}
```
