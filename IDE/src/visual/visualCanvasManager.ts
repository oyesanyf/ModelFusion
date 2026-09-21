/**
 * Native Multi-Modal Visual Canvas Manager
 * 
 * Responsibilities:
 * 1. Manages visual asset state (wireframes, screenshots, architecture diagrams)
 * 2. Routes multi-modal inference to local VLMs:
 *    - OpenVINO Qwen2-VL (IDE/ov_models/OpenVINO_Qwen2-VL-7B-Instruct-int4-ov)
 *    - Ollama qwen2-vl (/api/chat with base64 images)
 *    - Master CLI vision tasks (--task visual-question-answering)
 * 3. Executes two primary developer workflows:
 *    - UI Component Synthesis (Tailwind CSS + React JSX/HTML)
 *    - Visual Layout Bug Diagnosis (Box model / flexbox analysis & CSS patch)
 * 4. Bridges Webview IPC events to local execution engines and editor actions
 */

import * as path from 'path';
import * as fs from 'fs';
import { spawn } from 'child_process';
import { VisualAsset, VisualCanvasIpcMessage } from './dropzone';

export interface UiSynthesisResult {
  status: 'success' | 'error';
  workflow: 'ui-synthesis';
  code: string;
  summary: string;
  designTokens: string;
  framework: string;
  provider: string;
  latencyMs: number;
  error?: string;
}

export interface LayoutDiagnosisResult {
  status: 'success' | 'error';
  workflow: 'layout-diagnosis';
  diagnosis: string;
  rootCause: string;
  cssPatch: string;
  explanation: string;
  provider: string;
  latencyMs: number;
  error?: string;
}

export interface VisualProviderStatus {
  openVinoAvailable: boolean;
  openVinoModelPath?: string;
  ollamaAvailable: boolean;
  ollamaModels: string[];
  cliAvailable: boolean;
}

export interface VisualCanvasOptions {
  pythonPath?: string;
  ovModelDir?: string;
  ollamaEndpoint?: string;
  scriptPath?: string;
}

export class VisualCanvasManager {
  private _assets: Map<string, VisualAsset> = new Map();
  private _pythonPath: string;
  private _ovModelDir: string;
  private _ollamaEndpoint: string;
  private _scriptPath: string;

  constructor(options?: VisualCanvasOptions) {
    this._pythonPath = options?.pythonPath || 'python';
    this._ovModelDir = options?.ovModelDir || path.resolve(__dirname, '../../ov_models/OpenVINO_Qwen2-VL-7B-Instruct-int4-ov');
    this._ollamaEndpoint = options?.ollamaEndpoint || 'http://127.0.0.1:11434';
    this._scriptPath = options?.scriptPath || path.resolve(__dirname, '../scripts/run_model_visual.py');
  }

  // ── Asset Management ────────────────────────────────────────────────────────

  public addAsset(asset: VisualAsset): void {
    this._assets.set(asset.id, asset);
  }

  public removeAsset(id: string): boolean {
    return this._assets.delete(id);
  }

  public getAsset(id: string): VisualAsset | undefined {
    return this._assets.get(id);
  }

  public getAllAssets(): VisualAsset[] {
    return Array.from(this._assets.values());
  }

  public clearAssets(): void {
    this._assets.clear();
  }

  public reorderAssets(orderedIds: string[]): void {
    const reordered = new Map<string, VisualAsset>();
    for (const id of orderedIds) {
      const asset = this._assets.get(id);
      if (asset) {
        reordered.set(id, asset);
      }
    }
    // Append any remaining assets
    for (const [id, asset] of this._assets.entries()) {
      if (!reordered.has(id)) {
        reordered.set(id, asset);
      }
    }
    this._assets = reordered;
  }

  // ── Provider Probing ────────────────────────────────────────────────────────

  public async probeProviders(): Promise<VisualProviderStatus> {
    const status: VisualProviderStatus = {
      openVinoAvailable: false,
      ollamaAvailable: false,
      ollamaModels: [],
      cliAvailable: false
    };

    // 1. Check OpenVINO directory
    if (fs.existsSync(this._ovModelDir)) {
      status.openVinoAvailable = true;
      status.openVinoModelPath = this._ovModelDir;
    }

    // 2. Check Ollama API
    try {
      const response = await fetch(`${this._ollamaEndpoint}/api/tags`, {
        signal: AbortSignal.timeout(1500)
      });
      if (response.ok) {
        const data = await response.json() as { models?: Array<{ name: string }> };
        status.ollamaAvailable = true;
        status.ollamaModels = (data.models || []).map(m => m.name);
      }
    } catch {
      status.ollamaAvailable = false;
    }

    // 3. Check CLI binary
    const potentialCliPaths = [
      path.resolve(__dirname, '../../../target/release/cli.exe'),
      path.resolve(__dirname, '../../bin/cli.exe'),
      path.resolve(process.env.LOCALAPPDATA || '', 'HugOS IDE/bin/cli.exe')
    ];
    for (const p of potentialCliPaths) {
      if (fs.existsSync(p)) {
        status.cliAvailable = true;
        break;
      }
    }

    return status;
  }

  // ── Multi-Modal Workflows ───────────────────────────────────────────────────

  /**
   * Workflow 1: UI Component Synthesis
   * Generates a modern React component with Tailwind CSS classes from wireframe/screenshot.
   */
  public async synthesizeUiComponent(
    assetOrId: VisualAsset | string,
    customPrompt?: string
  ): Promise<UiSynthesisResult> {
    const start = performance.now();
    const asset = typeof assetOrId === 'string' ? this.getAsset(assetOrId) : assetOrId;

    if (!asset) {
      return {
        status: 'error',
        workflow: 'ui-synthesis',
        code: '',
        summary: '',
        designTokens: '',
        framework: 'react-tailwind',
        provider: 'none',
        latencyMs: 0,
        error: `Visual asset not found: ${assetOrId}`
      };
    }

    try {
      const result = await this._executeVisualScript({
        image: asset.base64Data,
        workflow: 'ui-synthesis',
        prompt: customPrompt
      });

      const elapsed = Math.round(performance.now() - start);
      return {
        status: 'success',
        workflow: 'ui-synthesis',
        code: result.code || '',
        summary: result.summary || '',
        designTokens: result.design_tokens || '',
        framework: result.framework || 'react-tailwind',
        provider: result.provider || 'local-vlm',
        latencyMs: elapsed
      };
    } catch (err: any) {
      return {
        status: 'error',
        workflow: 'ui-synthesis',
        code: '',
        summary: '',
        designTokens: '',
        framework: 'react-tailwind',
        provider: 'error',
        latencyMs: Math.round(performance.now() - start),
        error: err?.message || String(err)
      };
    }
  }

  /**
   * Workflow 2: Visual Layout Bug Diagnosis
   * Analyzes CSS Box Model, flexbox/grid misalignment, and suggests a concrete CSS patch.
   */
  public async diagnoseLayoutBug(
    assetOrId: VisualAsset | string,
    customPrompt?: string
  ): Promise<LayoutDiagnosisResult> {
    const start = performance.now();
    const asset = typeof assetOrId === 'string' ? this.getAsset(assetOrId) : assetOrId;

    if (!asset) {
      return {
        status: 'error',
        workflow: 'layout-diagnosis',
        diagnosis: '',
        rootCause: '',
        cssPatch: '',
        explanation: '',
        provider: 'none',
        latencyMs: 0,
        error: `Visual asset not found: ${assetOrId}`
      };
    }

    try {
      const result = await this._executeVisualScript({
        image: asset.base64Data,
        workflow: 'layout-diagnosis',
        prompt: customPrompt
      });

      const elapsed = Math.round(performance.now() - start);
      return {
        status: 'success',
        workflow: 'layout-diagnosis',
        diagnosis: result.diagnosis || '',
        rootCause: result.root_cause || '',
        cssPatch: result.css_patch || '',
        explanation: result.explanation || '',
        provider: result.provider || 'local-vlm',
        latencyMs: elapsed
      };
    } catch (err: any) {
      return {
        status: 'error',
        workflow: 'layout-diagnosis',
        diagnosis: '',
        rootCause: '',
        cssPatch: '',
        explanation: '',
        provider: 'error',
        latencyMs: Math.round(performance.now() - start),
        error: err?.message || String(err)
      };
    }
  }

  // ── Webview IPC Message Handler ─────────────────────────────────────────────

  public async handleWebviewMessage(
    message: VisualCanvasIpcMessage,
    postResponseCallback?: (msg: any) => void
  ): Promise<void> {
    switch (message.type) {
      case 'attachVisualAsset':
        this.addAsset(message.asset);
        break;

      case 'removeVisualAsset':
        this.removeAsset(message.assetId);
        break;

      case 'reorderVisualAssets':
        this.reorderAssets(message.assetIds);
        break;

      case 'requestSynthesis': {
        const asset = message.assetId
          ? this.getAsset(message.assetId)
          : this.getAllAssets()[0];

        if (!asset) {
          if (postResponseCallback) {
            postResponseCallback({
              type: 'visualSynthesisResult',
              status: 'error',
              workflow: message.workflow,
              output: 'No visual asset attached to process.'
            });
          }
          return;
        }

        if (message.workflow === 'ui-synthesis') {
          const res = await this.synthesizeUiComponent(asset, message.prompt);
          if (postResponseCallback) {
            postResponseCallback({
              type: 'visualSynthesisResult',
              status: res.status,
              workflow: 'ui-synthesis',
              output: res.code,
              summary: res.summary,
              designTokens: res.designTokens,
              provider: res.provider,
              latencyMs: res.latencyMs
            });
          }
        } else if (message.workflow === 'layout-diagnosis') {
          const res = await this.diagnoseLayoutBug(asset, message.prompt);
          if (postResponseCallback) {
            postResponseCallback({
              type: 'visualSynthesisResult',
              status: res.status,
              workflow: 'layout-diagnosis',
              output: res.diagnosis,
              rootCause: res.rootCause,
              patch: res.cssPatch,
              explanation: res.explanation,
              provider: res.provider,
              latencyMs: res.latencyMs
            });
          }
        }
        break;
      }
    }
  }

  // ── Subprocess Runner ───────────────────────────────────────────────────────

  private async _executeVisualScript(params: {
    image: string;
    workflow: string;
    prompt?: string;
  }): Promise<any> {
    return new Promise((resolve, reject) => {
      const args = [
        this._scriptPath,
        '--image', params.image,
        '--workflow', params.workflow,
        '--format', 'json',
        '--ov-model-dir', this._ovModelDir,
        '--ollama-endpoint', this._ollamaEndpoint
      ];

      if (params.prompt) {
        args.push('--prompt', params.prompt);
      }

      const proc = spawn(this._pythonPath, args, {
        windowsHide: true,
        stdio: ['pipe', 'pipe', 'pipe']
      });

      let stdout = '';
      let stderr = '';

      proc.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      proc.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      proc.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(`Visual script exited with code ${code}: ${stderr || stdout}`));
          return;
        }

        try {
          const parsed = JSON.parse(stdout.trim());
          resolve(parsed);
        } catch (parseErr) {
          reject(new Error(`Failed to parse visual script JSON output: ${stdout}`));
        }
      });

      proc.on('error', (err) => {
        reject(new Error(`Failed to spawn visual inference script: ${err.message}`));
      });
    });
  }
}
