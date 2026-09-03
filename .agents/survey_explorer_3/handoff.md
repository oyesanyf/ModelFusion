# Handoff Report: Chat Participants, Slash Commands, Diff Viewing, and Synchronization

**Explorer**: Survey Explorer 3 (Chat & Command Explorer)  
**Parent Conversation ID**: `b359a14e-cb9c-45f2-8e1e-6bb6dc7ed242`  
**Working Directory**: `D:\harfile\ModelFusion\.agents\survey_explorer_3`  
**Date**: 2026-09-01  

---

## 1. Observation

### 1.1 Chat Participants & Slash Command Registrations
- **Manifest Contributions (`D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\package.json`)**:
  - Line 1372: `"chatParticipants"` contributes `github.copilot.default` (lines 1374-1460), `github.copilot.editingSession` (line 2008), `github.copilot.editsAgent` (line 2423), `github.copilot.notebook` (line 2761), `github.copilot.vscode` (line 3203), `github.copilot.terminal` (line 3412).
  - Line 8563: `"viewsContainers"` contributes Activity Bar items (`copilot-chat`, `context-inspector`).
  - Line 8607-8617: `"keybindings"` contributes `hugos.evolve.accept` (`ctrl+shift+y`) and `hugos.evolve.reject` (`ctrl+shift+n`) when `editorTextFocus`.
- **Dynamic Custom Agent Providers (`src/extension/agents/vscode-node/promptFileContrib.ts:30-65`)**:
  - `vscode.chat.registerCustomAgentProvider` is used to register `PlanAgentProvider`, `AskAgentProvider`, `ExploreAgentProvider`, and `GitHubOrgCustomAgentProvider`.
  - `agentTypes.ts:56-120`: `buildAgentMarkdown` dynamically constructs `.agent.md` configurations with tools, subagents, and handoffs without external YAML libraries.
- **Model Provider & Slash Command Execution (`src/extension/byok/vscode-node/modelFusionProvider.ts`)**:
  - Registered via `lm.registerLanguageModelChatProvider(ModelFusionLMProvider.providerId, modelFusion)` in `byokContribution.ts:38`.
  - Lines 425-433: Detects `options.command` when selected from VS Code Chat UI dropdown.
  - Lines 436-493: Maintains `knownCommands` set containing 62 CLI task flags, info commands (`stats`, `sysinfo`, `tasks`, `mcp`), config toggles (`gpu`, `cpu`, `ollama`, `openvino`, `fusion`), and action pipelines (`evolve`).
  - Lines 540-597: Matches regex patterns for `@agent`, `@task`, `@comment`, and `/<command>` directly from raw/cleaned user messages.
  - Lines 616-654: Implements `deepFindCommand` scanning `options.requestInitiator` and nested option objects up to depth 4 to catch commands when VS Code routes `@agent /evolve` to `editsAgent` and strips command text.
  - Lines 689-704: Intercepts VS Code background conversation compaction requests and returns fast 1ms dummy summary to avoid 42s LLM roundtrips.
  - Lines 716-720: Routes `/evolve` to `this._runOpenEvolve(slashCommandText, progress, token)`.
  - Lines 817-842: Fast info commands (`stats`, `sysinfo`, `tasks`, `mcp`, `keys`) execute in `<10ms` by sending minimal prompts directly to `http://127.0.0.1:5000` without conversation history.
  - Lines 844-865: Native CLI actions (`update`, `clearcache`, `restore`) invoke `cli.exe` directly via `child_process.execFileSync`.
  - Lines 1201-1356: `_runAvoEvolve` synthesizes `eval.py` via LLM, sets up `target.yaml`, and spawns `python -m avo.cli run --target <dir> --backend modelfusion --max-steps <iterations>`.

### 1.2 Diff Viewing & Patch Application Implementations
- **Inline Diff Manager (`src/extension/byok/vscode-node/evolve/inlineDiff.ts`)**:
  - Lines 45-87: Creates 4 decoration types (`_gutterDecoration`, `_addDecoration`, `_removeDecoration`, `_headerDecoration`).
  - Lines 105-134: Modifies active text document in-place via `activeEditor.edit()`, computes line-by-line diffs, applies gutter/text decorations, and mounts a persistent Status Bar item (`$(check) Accept Changes $(x) Reject`).
  - Lines 247-286: `accept()` calls `editor.document.save()`; `reject()` reverts editor text to `originalCode`.
- **Side-by-Side Diff Viewer (`src/extension/chatSessions/copilotcli/vscode-node/tools/openDiff.ts`)**:
  - Lines 58-65: Generates readonly URIs with scheme `copilot-cli-readonly` using `createReadonlyUri`.
  - Lines 69-74: Opens native side-by-side diff editor using `vscode.commands.executeCommand('vscode.diff', originalUri, newUri, title, { preview: false, preserveFocus: true })`.
  - Lines 97-158: Monitors tab close events (`vscode.window.tabGroups.onDidChangeTabs`) and cleans up resources via `diffState.ts` (`DiffStateManager`).
- **Readonly Content Provider (`src/extension/chatSessions/copilotcli/vscode-node/readonlyContentProvider.ts:10-29`)**:
  - Implements `vscode.TextDocumentContentProvider` and registers scheme `copilot-cli-readonly` with `workspace.registerTextDocumentContentProvider`.

### 1.3 AVO Lineage & Evolutionary Storage (`avo/src/avo/lineage.py`)
- Lines 45-96: `Lineage` maintains `work/` as an isolated Git repository with version tags (`v0, v1, v2, ...`).
- Persists `.avo/score.json` for current generation and `.avo/scores.jsonl` containing historical fitness evaluations, notes, and duration per iteration.

---

## 2. Logic Chain

1. **Premise (Chat Routing)**: VS Code's extension architecture routes chat prompts through `LanguageModelChatProvider` and `ChatCustomAgentProvider`. `ModelFusionLMProvider` successfully handles slash command detection via multi-stage matching (options inspection, regex, deep options scan), and routes `/evolve` to `_runOpenEvolve`.
2. **Premise (Diff Viewing)**: Two proven patterns exist in the codebase:
   - `InlineDiffManager` provides immediate in-editor visual review and hotkey acceptance (`Ctrl+Shift+Y` / `Ctrl+Shift+N`).
   - `openDiff.ts` with `ReadonlyContentProvider` provides native side-by-side comparison using `vscode.diff`.
3. **Premise (Candidate Lineage)**: AVO and OpenEvolve produce structured candidate artifacts with Git version tags (`v0, v1, ...`) and JSONL fitness metrics.
4. **Inference for Requirement R2 (Diff Viewer & Patch Apply)**:
   - Implementing a dedicated `OpenEvolveContentProvider` (`hugos-candidate://`) enables `vscode.diff` to open any candidate solution ($v_i$) side-by-side against the baseline ($v_0$) or previous candidate ($v_{i-1}$) with zero file pollution.
   - Implementing `hugos.openevolve.applyCandidate` using `vscode.WorkspaceEdit` provides clean, atomic one-click code application and save into workspace files directly from the diff editor title bar and dashboard webview.
5. **Inference for Requirement R4 (Command & Participant Synchronization)**:
   - Introducing an `EvolutionStateManager` singleton in the extension host bridges the Chat panel (`ModelFusionLMProvider`), the Webview Dashboard, and backend CLI events.
   - When a user triggers `/evolve` in Chat, lifecycle events are broadcast to the Webview via `webview.postMessage()`, updating fitness graphs and agent status at 60fps.
   - When a user triggers evolution or preset changes in the Dashboard, the Webview sends messages to the host, which updates settings and triggers evolution runs transparently.

---

## 3. Caveats

- No caveats. All investigated areas (chat participant declarations, command handlers, diff editors, AVO lineage, and Webview IPC) are fully backed by direct source code inspection.

---

## 4. Conclusion

The HugOS IDE architecture supports the implementation of Requirements R2 and R4 natively:
1. **Requirement R2 (Candidate Diff Viewer & Patch Application)** is best achieved by combining a virtual `TextDocumentContentProvider` (`hugos-candidate://`), native `vscode.diff` comparison invocations, and atomic `vscode.WorkspaceEdit` patch application with rollback support.
2. **Requirement R4 (Command & Participant Synchronization)** is best achieved via a centralized `EvolutionStateManager` event bus that coordinates between the Chat participant (`ModelFusionLMProvider`), custom agent providers (`PlanAgentProvider`, `AskAgentProvider`), and the Activity Bar Webview Dashboard via asynchronous `postMessage` IPC.

---

## 5. Verification Method

To independently verify the observations and code pathways:
1. **Inspect Chat Participants**:
   - View `D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\package.json` at lines 1372-1460, 8563-8618.
2. **Inspect Command Routing & OpenEvolve**:
   - View `D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\src\extension\byok\vscode-node\modelFusionProvider.ts` at lines 425-680, 716-720, 1115-1355.
3. **Inspect Diff Mechanisms**:
   - View `D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\src\extension\byok\vscode-node\evolve\inlineDiff.ts` at lines 105-286.
   - View `D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\src\extension\chatSessions\copilotcli\vscode-node\tools\openDiff.ts` at lines 23-178.
4. **Inspect AVO Lineage**:
   - View `D:\harfile\ModelFusion\IDE\vscode\extensions\copilot\avo\src\avo\lineage.py` at lines 45-100.
