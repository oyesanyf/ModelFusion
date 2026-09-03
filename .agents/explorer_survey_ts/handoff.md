# TypeScript & IDE Extension Safety Audit — Handoff Report

**Agent**: `explorer_survey_ts`  
**Recipient**: `parent` (`02870692-b65d-4b30-9bd8-8d719d3789f3`)  
**Workspace**: `d:/harfile/ModelFusion/.agents/explorer_survey_ts/`  
**Date**: 2026-09-01  
**Handoff Type**: Hard (Task Complete)  

---

## 1. Observation

Direct observations and code excerpts from audited TypeScript/JavaScript modules:

1. **Non-Existent Method Call on Process Exit in `modelFusionProvider.ts`**:
   - Location: `IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionProvider.ts:259-272`
   - Verbatim code:
     ```typescript
     this._serverProcess.on('exit', (code) => {
         const msg = `Server process exited with code ${code}`;
         this._logService.warn(`ModelFusionProvider: Persistent server exited with code ${code}`);
         this._outputChannel.appendLine(`[Server] ${msg}`);
         
         if (this._serverProcess) {
             this._outputChannel.appendLine(`[Server] Unexpected exit. Respawning in 3 seconds...`);
             this._serverProcess = undefined;
             setTimeout(() => {
                 this._spawnPersistentServer();
             }, 3000);
         }
     });
     ```
   - Inspection of `ModelFusionLMProvider` shows the server startup method is named `startServer()` at line 151. No method named `_spawnPersistentServer` is declared on the class or base classes.

2. **Undeclared Identifier in Built-in Evolution in `modelFusionProvider.ts`**:
   - Location: `IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionProvider.ts:1550-1554`
   - Verbatim code:
     ```typescript
     const improved = await this._sendOrchestrationRequest(
         prompt, 10.0, 'fastest', 'multi-model', 1,
         false, true, false, false, true, ollamaModel, token
     );
     ```
   - In `_runBuiltinEvolve()` (lines 1467-1600), `ollamaModel` is neither a method parameter, nor a local variable, nor a class property.

3. **Synchronous Execution Freezing Extension Host in `modelManagerPanel.ts`**:
   - Location: `IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelManagerPanel.ts:72-84`
   - Verbatim code:
     ```typescript
     private _detectOllamaModels() {
         try {
             const result = child_process.execSync('ollama list', { encoding: 'utf-8', timeout: 10000 });
             const lines = result.split('\n').filter(l => l.trim() && !l.startsWith('NAME'));
             ...
     ```
   - `child_process.execSync` executes synchronously on Node.js main thread in the extension host.

4. **Undisposed MCP Definition Provider in `modelFusionMcp.contribution.ts`**:
   - Location: `IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionMcp.contribution.ts:93-108`
   - Verbatim code:
     ```typescript
     export class ModelFusionMcpContrib extends Disposable {
         private disposable?: IDisposable;
         ...
         private _registerModelFusionMcpDefinitionProvider() {
             this.logService.trace('Registering ModelFusion MCP Definition Provider.');
             const provider = new ModelFusionMcpDefinitionProvider(this.logService);
             this.disposable = lm.registerMcpServerDefinitionProvider('modelfusion', provider);
         }
     }
     ```
   - The returned `IDisposable` is stored in a private field but not registered in `this._register(...)` or disposed on teardown.

5. **Leaked Workspace Event Listeners in `modelFusionProvider.ts`**:
   - Location: `IDE/vscode/extensions/copilot/src/extension/byok/vscode-node/modelFusionProvider.ts:110, 115, 142`
   - Verbatim code:
     ```typescript
     vscode.commands.registerCommand('hugos.modelfusion.openModelManager', () => { ... });
     vscode.workspace.onDidChangeTextDocument((e) => { ... });
     vscode.workspace.onDidChangeConfiguration((e) => { ... });
     ```
   - None of these are wrapped in `this._register(...)`.

6. **60fps Event Streaming and Webview Architecture in `eventStreamService.ts`**:
   - Location: `IDE/vscode/extensions/copilot/src/extension/dashboard/eventStreamService.ts:31-96, 254-319`
   - `AsyncRingBuffer` maintains a 4,096-capacity circular buffer with O(1) non-blocking enqueue and drop tracking.
   - `EventStreamService` batches drained events every 16ms (60fps) and dispatches via `webview.postMessage({ type: 'batchEvents', ... })`.

---

## 2. Logic Chain

1. **Premise from Observation 1**: When Node.js executes `this._serverProcess.on('exit')` upon an unexpected child process crash, it triggers `setTimeout(..., 3000)`. When the timer elapses, calling `this._spawnPersistentServer()` triggers `TypeError: this._spawnPersistentServer is not a function`.
   - **Deduction**: The auto-recovery mechanism fails to respawn the server and produces an unhandled timer exception. Replacing `this._spawnPersistentServer()` with `this.startServer()` restores recovery.

2. **Premise from Observation 2**: JavaScript/TypeScript runtime evaluation of `_runBuiltinEvolve()` encounters identifier `ollamaModel`. Because `ollamaModel` is not in scope, JavaScript throws `ReferenceError: ollamaModel is not defined`.
   - **Deduction**: All non-Python evolutionary search invocations (`/evolve`) crash immediately at iteration 1. Defining `const ollamaModel = ...` from settings resolves the crash.

3. **Premise from Observation 3**: The VS Code Extension Host runs as a single-threaded Node.js process managing all active extensions, autocomplete providers, language servers, and document sync.
   - **Deduction**: Calling `child_process.execSync('ollama list', { timeout: 10000 })` halts the entire event loop until Ollama finishes or 10s expires, causing editor typing freezes. Replacing with async `child_process.exec` ensures non-blocking UI behavior.

4. **Premise from Observation 4 & 5**: VS Code contributions extend `Disposable` and rely on `this._register(...)` so that when an extension is reloaded, deactivated, or tested, all registered providers and listeners are cleanly unregistered.
   - **Deduction**: Missing `this._register(...)` calls leave lingering event subscriptions and MCP providers in the VS Code host, causing resource retention leaks and duplicate handlers across reloads.

5. **Premise from Observation 6**: The 60fps frame dispatcher and `AsyncRingBuffer` decouple high-frequency model events (thoughts, fitness steps, candidates) from webview DOM rendering.
   - **Deduction**: High-throughput evolutionary search runs do not saturate VS Code IPC channels or block UI responsiveness.

---

## 3. Caveats

- **Scope Boundary**: This audit exclusively examined the TypeScript and JavaScript codebase (`IDE/vscode/extensions/copilot/src/`, `IDE/patches/`, `IDE/test_e2e_suite.mjs`, `tests/e2e/`). Rust crates (`crates/`) and Python scripts (`src/scripts/`, `avo/`) were audited in parallel by the respective language explorers.
- **Runtime Environment**: Static analysis was performed directly on source code and test files without running live GUI instances of VS Code.

---

## 4. Conclusion

The TypeScript and IDE Extension subsystem of ModelFusion / HugOS is architecturally mature and well-structured, featuring clean separation of concerns, 60fps asynchronous IPC event streaming, and native VS Code diff/patch integration.

To bring the subsystem to 100% production safety:
1. **Apply Critical Bug Fixes**:
   - Fix `this._spawnPersistentServer()` → `this.startServer()` in `modelFusionProvider.ts:269`.
   - Declare `ollamaModel` in `_runBuiltinEvolve()` in `modelFusionProvider.ts:1485`.
2. **Apply Concurrency Fix**:
   - Convert `execSync` to async `child_process.exec` in `modelManagerPanel.ts:74`.
3. **Apply Resource Cleanup Fixes**:
   - Register MCP definition provider in `modelFusionMcp.contribution.ts:106`.
   - Register `onDidChangeTextDocument`, `onDidChangeConfiguration`, and `registerCommand` in `modelFusionProvider.ts:110, 115, 142`.
   - Dispose `_inlineDiff` and cancellation token subscriptions.

All findings and diff patches are fully documented in `d:/harfile/ModelFusion/.agents/explorer_survey_ts/survey_ts.md`.

---

## 5. Verification Method

To independently verify these findings:

1. **Verify Line Locations & Issues**:
   - `modelFusionProvider.ts:269`: Inspect `this._spawnPersistentServer()`. Verify `startServer()` at line 151.
   - `modelFusionProvider.ts:1553`: Inspect `ollamaModel` usage inside `_runBuiltinEvolve()`. Check parameter list (line 1467) and local declarations.
   - `modelManagerPanel.ts:74`: Inspect `child_process.execSync('ollama list', ...)` inside `_detectOllamaModels()`.
   - `modelFusionMcp.contribution.ts:106`: Inspect `this.disposable = lm.registerMcpServerDefinitionProvider(...)`.

2. **Run TypeScript Test Suites**:
   - Run Vitest specifications:
     `npx vitest run IDE/vscode/extensions/copilot/src/extension/dashboard/test/dashboardM1M2.spec.ts`
     `npx vitest run IDE/vscode/extensions/copilot/src/extension/dashboard/test/dashboardM3M4M5.spec.ts`
   - Run E2E test harness:
     `node IDE/test_e2e_suite.mjs`
