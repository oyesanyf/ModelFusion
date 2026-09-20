/**
 * HugOS IDE Client Shim (ide_client_shim.ts)
 * 
 * Client-side TypeScript module for HugOS / VSCode IDE integration:
 * 1. Hooks into editor input events: keystrokes, cursor navigation, window focus.
 * 2. Employs a 45-second debounce timer transitioning between ACTIVE and IDLE.
 * 3. Immediately triggers ACTIVE preemption on the first subsequent keystroke.
 * 4. Displays a subtle, non-blocking UI status bar item:
 *    "ReST-RL: Idle Optimization Running..." during background optimization.
 * 5. Notifies the developer via an in-editor Diff Viewer with Accept/Reject actions
 *    when a candidate patch successfully passes all tests (reward 1.0).
 */

import * as vscode from 'vscode';
import * as net from 'net';
import * as fs from 'fs';
import * as path from 'path';

export interface RpcResponse<T = any> {
  jsonrpc: string;
  id: number;
  result?: T;
  error?: {
    code: number;
    message: string;
  };
}

export interface ResolutionPayload {
  task_id: string;
  target_file: string;
  reward: number;
  candidate_code: string;
  original_code: string;
  diff_patch: string;
  passed: boolean;
}

/**
 * In-memory virtual document provider for ReST-RL diff previews (restrl-diff://).
 * Eliminates ephemeral file writes to disk and prevents race conditions with diff tabs.
 */
export class RestRlDiffContentProvider implements vscode.TextDocumentContentProvider {
  private _onDidChange = new vscode.EventEmitter<vscode.Uri>();
  public readonly onDidChange = this._onDidChange.event;
  private _docs = new Map<string, string>();

  public provideTextDocumentContent(uri: vscode.Uri): string {
    return this._docs.get(uri.toString()) || '';
  }

  public setContent(uri: vscode.Uri, content: string): void {
    this._docs.set(uri.toString(), content);
    this._onDidChange.fire(uri);
  }

  public deleteContent(uri: vscode.Uri): void {
    this._docs.delete(uri.toString());
  }
}

export class RestRLIdeShim implements vscode.Disposable {
  private _debounceTimer: NodeJS.Timeout | null = null;
  private _pollTimer: NodeJS.Timeout | null = null;
  private _isIdle: boolean = false;
  private _lastActivityTime: number = Date.now();
  private _statusBarItem: vscode.StatusBarItem;
  private _diffProvider: RestRlDiffContentProvider;
  private _disposables: vscode.Disposable[] = [];
  private _reqId: number = 0;

  // Connection settings
  private _tcpHost: string = '127.0.0.1';
  private _tcpPort: number = 45454;
  private _pipePath: string = '\\\\.\\pipe\\hugos_rest_rl_ipc';
  private _debounceSeconds: number = 45.0;

  constructor(private readonly _context: vscode.ExtensionContext) {
    // 1. Initialize Status Bar Item
    this._statusBarItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Right,
      100
    );
    this._statusBarItem.name = 'HugOS ReST-RL Status';
    this._statusBarItem.text = '$(zap) ReST-RL: Ready';
    this._statusBarItem.tooltip = 'ModelFusion ReST-RL Autonomous Optimization Subsystem';
    this._statusBarItem.show();
    this._disposables.push(this._statusBarItem);

    // 2. Initialize In-Memory Virtual Document Provider for restrl-diff://
    this._diffProvider = new RestRlDiffContentProvider();
    this._disposables.push(
      vscode.workspace.registerTextDocumentContentProvider('restrl-diff', this._diffProvider)
    );

    // 3. Register IDE User Activity Hooks
    this._registerEventHooks();

    // 4. Register Commands (Diff Review, Accept, Reject)
    this._registerCommands();

    // 5. Start 45-second debounce & resolution polling
    this._scheduleDebounce();
    this._startResolutionPolling();
  }

  /**
   * Disposes all timers, event hooks, and status bar elements.
   */
  public dispose(): void {
    if (this._debounceTimer) {
      clearTimeout(this._debounceTimer);
      this._debounceTimer = null;
    }
    if (this._pollTimer) {
      clearInterval(this._pollTimer);
      this._pollTimer = null;
    }
    this._disposables.forEach((d) => d.dispose());
  }

  /**
   * Hooks into editor keystrokes, selection changes, and window focus.
   */
  private _registerEventHooks(): void {
    // Text Document edits (keystrokes)
    this._disposables.push(
      vscode.workspace.onDidChangeTextDocument((e) => {
        if (e.contentChanges.length > 0) {
          this.onUserActivity('text_edit');
        }
      })
    );

    // Cursor navigation and selection changes
    this._disposables.push(
      vscode.window.onDidChangeTextEditorSelection(() => {
        this.onUserActivity('selection_change');
      })
    );

    // Active editor switch
    this._disposables.push(
      vscode.window.onDidChangeActiveTextEditor(() => {
        this.onUserActivity('editor_change');
      })
    );

    // Window focus change
    this._disposables.push(
      vscode.window.onDidChangeWindowState((state) => {
        if (state.focused) {
          this.onUserActivity('window_focused');
        }
      })
    );
  }

  /**
   * Registers Review, Accept, and Reject commands.
   */
  private _registerCommands(): void {
    this._disposables.push(
      vscode.commands.registerCommand(
        'modelfusion.rest_rl.reviewPatch',
        async (res: ResolutionPayload) => {
          await this._showDiffViewer(res);
        }
      )
    );

    this._disposables.push(
      vscode.commands.registerCommand(
        'modelfusion.rest_rl.acceptPatch',
        async (targetFile: string, candidateCode: string) => {
          try {
            const targetUri = vscode.Uri.file(targetFile);
            const doc = await vscode.workspace.openTextDocument(targetUri);
            const edit = new vscode.WorkspaceEdit();
            const fullRange = new vscode.Range(
              doc.positionAt(0),
              doc.positionAt(doc.getText().length)
            );
            edit.replace(targetUri, fullRange, candidateCode);
            const applied = await vscode.workspace.applyEdit(edit);
            if (applied) {
              await doc.save();
              vscode.window.showInformationMessage(
                `ReST-RL: Accepted patch for ${path.basename(targetFile)}`
              );
            } else {
              // Fallback to disk write if edit could not be applied
              await fs.promises.writeFile(targetFile, candidateCode, 'utf-8');
              vscode.window.showInformationMessage(
                `ReST-RL: Accepted patch for ${path.basename(targetFile)}`
              );
            }
          } catch (err: any) {
            vscode.window.showErrorMessage(
              `ReST-RL: Failed to apply patch: ${err.message}`
            );
          }
        }
      )
    );
  }

  /**
   * Handles user activity events with instant preemption back to ACTIVE.
   */
  public onUserActivity(reason: string = 'keystroke'): void {
    this._lastActivityTime = Date.now();

    if (this._isIdle) {
      this._isIdle = false;
      this._statusBarItem.text = '$(zap) ReST-RL: Ready';
      this._statusBarItem.tooltip = 'ModelFusion ReST-RL: Active editing mode';

      // Immediately notify daemon to PAUSE background rollouts
      this._callRpc('ide/idle_stop').catch(() => {});
    }

    // Reset 45-second debounce window
    this._scheduleDebounce();
  }

  /**
   * Schedules the 45-second debounce timer.
   */
  private _scheduleDebounce(): void {
    if (this._debounceTimer) {
      clearTimeout(this._debounceTimer);
    }

    this._debounceTimer = setTimeout(() => {
      this._onDebounceFired();
    }, this._debounceSeconds * 1000);
  }

  /**
   * Fired when the IDE has been idle for >= 45 seconds.
   */
  private async _onDebounceFired(): Promise<void> {
    const elapsed = (Date.now() - this._lastActivityTime) / 1000;
    if (elapsed >= this._debounceSeconds && !this._isIdle) {
      this._isIdle = true;
      this._statusBarItem.text = '$(sync~spin) ReST-RL: Idle Optimization Running...';
      this._statusBarItem.tooltip = 'ModelFusion ReST-RL: Autonomous reasoning in progress';

      try {
        await this._callRpc('ide/idle_start');
      } catch (err: any) {
        // Daemon might not be currently running
      }
    }
  }

  /**
   * Enqueues a failing test or code optimization task to the background daemon.
   */
  public async enqueueTask(
    taskId: string,
    targetFile: string,
    testTarget: string,
    instruction: string = ''
  ): Promise<any> {
    const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || '';
    return this._callRpc('agent/enqueue_task', {
      task_id: taskId,
      target_file: targetFile,
      test_target: testTarget,
      workspace_root: workspaceRoot,
      instruction: instruction,
    });
  }

  /**
   * Periodic polling for completed task resolutions.
   */
  private _startResolutionPolling(): void {
    this._pollTimer = setInterval(async () => {
      try {
        const resp = await this._callRpc('agent/poll_resolutions');
        const resolutions: ResolutionPayload[] = resp?.resolutions || [];
        for (const res of resolutions) {
          if (res.passed || res.reward >= 1.0) {
            this._promptResolutionReview(res);
          }
        }
      } catch {
        // Silently ignore connection blips
      }
    }, 2500);
  }

  /**
   * Displays non-intrusive notification prompting developer with Diff Viewer.
   */
  private async _promptResolutionReview(res: ResolutionPayload): Promise<void> {
    const filename = path.basename(res.target_file);
    const action = await vscode.window.showInformationMessage(
      `ReST-RL: Optimization successful for ${filename} (Reward: 1.00)`,
      'Review Diff',
      'Accept',
      'Reject'
    );

    if (action === 'Review Diff') {
      await this._showDiffViewer(res);
    } else if (action === 'Accept') {
      await vscode.commands.executeCommand(
        'modelfusion.rest_rl.acceptPatch',
        res.target_file,
        res.candidate_code
      );
    }
  }

  /**
   * Opens the in-editor Side-by-Side Diff Viewer using in-memory virtual documents.
   * Prevents deletion race conditions and avoids temporary file writes to the workspace.
   */
  private async _showDiffViewer(res: ResolutionPayload): Promise<void> {
    const targetUri = vscode.Uri.file(res.target_file);
    const safeFilename = path.basename(res.target_file);
    const candidateUri = vscode.Uri.parse(
      `restrl-diff://candidate/${encodeURIComponent(safeFilename)}?taskId=${encodeURIComponent(res.task_id)}`
    );

    try {
      this._diffProvider.setContent(candidateUri, res.candidate_code);
      const title = `ReST-RL Patch Review: ${safeFilename} (Reward: 1.00)`;
      await vscode.commands.executeCommand('vscode.diff', targetUri, candidateUri, title);

      // Offer non-intrusive Accept / Reject prompt inside diff view
      const choice = await vscode.window.showInformationMessage(
        `Apply ReST-RL patch to ${safeFilename}?`,
        'Accept Patch',
        'Reject Patch'
      );

      if (choice === 'Accept Patch') {
        await vscode.commands.executeCommand(
          'modelfusion.rest_rl.acceptPatch',
          res.target_file,
          res.candidate_code
        );
      }
    } catch (err: any) {
      vscode.window.showErrorMessage(
        `ReST-RL: Failed to display diff viewer: ${err.message}`
      );
    }
  }

  /**
   * Dispatches JSON-RPC 2.0 calls over Named Pipe or TCP.
   */
  private _callRpc(method: string, params: Record<string, any> = {}): Promise<any> {
    return new Promise((resolve, reject) => {
      const id = ++this._reqId;
      const payload = JSON.stringify({
        jsonrpc: '2.0',
        id: id,
        method: method,
        params: params,
      }) + '\n';

      // Connect via Windows Named Pipe or TCP
      const client = process.platform === 'win32'
        ? net.connect(this._pipePath)
        : net.connect(this._tcpPort, this._tcpHost);

      let buffer = '';
      client.setTimeout(4000);

      client.on('connect', () => {
        client.write(payload);
      });

      client.on('data', (data) => {
        buffer += data.toString('utf-8');
        if (buffer.includes('\n')) {
          client.end();
        }
      });

      client.on('end', () => {
        try {
          const line = buffer.trim().split('\n')[0];
          if (!line) {
            return reject(new Error('Empty RPC response'));
          }
          const parsed: RpcResponse = JSON.parse(line);
          if (parsed.error) {
            reject(new Error(parsed.error.message));
          } else {
            resolve(parsed.result);
          }
        } catch (e) {
          reject(e);
        }
      });

      client.on('error', (err) => {
        // Fallback to TCP if named pipe fails on Windows
        if (process.platform === 'win32' && !client.destroyed) {
          client.destroy();
          const tcpClient = net.connect(this._tcpPort, this._tcpHost);
          let tcpBuffer = '';
          tcpClient.setTimeout(4000);

          tcpClient.on('connect', () => {
            tcpClient.write(payload);
          });
          tcpClient.on('data', (d) => {
            tcpBuffer += d.toString('utf-8');
            if (tcpBuffer.includes('\n')) tcpClient.end();
          });
          tcpClient.on('end', () => {
            try {
              const line = tcpBuffer.trim().split('\n')[0];
              const parsed: RpcResponse = JSON.parse(line);
              if (parsed.error) reject(new Error(parsed.error.message));
              else resolve(parsed.result);
            } catch (e) {
              reject(e);
            }
          });
          tcpClient.on('error', (e) => reject(e));
          return;
        }
        reject(err);
      });

      client.on('timeout', () => {
        client.destroy();
        reject(new Error('RPC request timed out'));
      });
    });
  }
}
