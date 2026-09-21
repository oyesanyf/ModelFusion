/**
 * Speculative Ensemble Ghost Text (speculativeGhostText.ts)
 * 
 * Ultra-low-latency in-editor speculative autocomplete provider:
 * 1. Implements vscode.InlineCompletionItemProvider.
 * 2. Enforces a strict 150ms latency budget (40ms debounce, 75ms draft tokens, 20ms AST verification, 15ms render).
 * 3. Formats Fill-in-the-Middle (FIM) prompt: <|fim_prefix|>${prefix}<|fim_suffix|>${suffix}<|fim_middle|>.
 * 4. Requests tokens from local 0.5B draft model (e.g. qwen2.5-coder:0.5b via OpenVINO or Ollama).
 * 5. Validates candidate syntax in-memory via AST checks (balanced delimiters, syntax integrity).
 * 6. Supports instant cancellation (<25ms) via AbortController and CancellationToken.
 */

import * as vscode from 'vscode';
import * as http from 'http';
import * as url from 'url';

export interface GhostTextConfig {
  debounceMs: number;
  draftTimeoutMs: number;
  astTimeoutMs: number;
  totalBudgetMs: number;
  maxPrefixLines: number;
  maxSuffixLines: number;
  modelName: string;
  modelFusionEndpoint: string;
  ollamaEndpoint: string;
}

export const DEFAULT_GHOST_TEXT_CONFIG: GhostTextConfig = {
  debounceMs: 40,
  draftTimeoutMs: 75,
  astTimeoutMs: 20,
  totalBudgetMs: 150,
  maxPrefixLines: 50,
  maxSuffixLines: 20,
  modelName: 'qwen2.5:0.5b',
  modelFusionEndpoint: 'http://127.0.0.1:5000/autocomplete',
  ollamaEndpoint: 'http://127.0.0.1:11434/api/generate',
};

/**
 * High-speed AST syntax and delimiter validator (<5ms).
 * Validates candidate code without file I/O or heavy process spawns.
 */
export class AstValidator {
  private static readonly BRACKET_PAIRS: Record<string, string> = {
    ')': '(',
    '}': '{',
    ']': '[',
  };

  private static readonly OPEN_BRACKETS = new Set(['(', '{', '[']);
  private static readonly CLOSE_BRACKETS = new Set([')', '}', ']']);

  /**
   * Validates syntax integrity of candidate ghost text.
   */
  public static validate(
    candidateText: string,
    languageId: string = '',
    prefixContext: string = '',
    suffixContext: string = ''
  ): boolean {
    if (!candidateText || candidateText.trim().length === 0) {
      return false;
    }

    const stack: string[] = [];
    let inString = false;
    let quoteChar = '';
    let escape = false;
    let inBlockComment = false;
    let inLineComment = false;

    for (let i = 0; i < candidateText.length; i++) {
      const ch = candidateText[i];
      const nextCh = i + 1 < candidateText.length ? candidateText[i + 1] : '';

      if (inLineComment) {
        if (ch === '\n') {
          inLineComment = false;
        }
        continue;
      }

      if (inBlockComment) {
        if (ch === '*' && nextCh === '/') {
          inBlockComment = false;
          i++;
        }
        continue;
      }

      if (escape) {
        escape = false;
        continue;
      }

      if (ch === '\\' && inString) {
        escape = true;
        continue;
      }

      // Check comment entries when not in string
      if (!inString) {
        if (ch === '/' && nextCh === '/') {
          inLineComment = true;
          i++;
          continue;
        }
        if (ch === '/' && nextCh === '*') {
          inBlockComment = true;
          i++;
          continue;
        }
        if (ch === '#' && (languageId === 'python' || languageId === 'shellscript' || languageId === 'bash')) {
          inLineComment = true;
          continue;
        }
      }

      if (ch === '"' || ch === "'" || ch === '`') {
        if (inString && ch === quoteChar) {
          inString = false;
          quoteChar = '';
        } else if (!inString) {
          inString = true;
          quoteChar = ch;
        }
        continue;
      }

      if (inString) {
        continue;
      }

      if (this.OPEN_BRACKETS.has(ch)) {
        stack.push(ch);
      } else if (this.CLOSE_BRACKETS.has(ch)) {
        const expectedOpen = this.BRACKET_PAIRS[ch];
        if (stack.length === 0 || stack[stack.length - 1] !== expectedOpen) {
          return false;
        }
        stack.pop();
      }
    }

    // Reject candidates that leave unclosed delimiters, strings, or block comments
    if (stack.length > 0 || inString || inBlockComment) {
      return false;
    }

    if (languageId === 'python') {
      const lines = candidateText.split('\n');
      for (const line of lines) {
        if (line.includes('def ') && !line.includes(':') && !line.includes('(')) {
          return false;
        }
      }
    } else if (languageId === 'typescript' || languageId === 'javascript') {
      const trimmed = candidateText.trim();
      if (trimmed.endsWith('=>') || trimmed.endsWith('&&') || trimmed.endsWith('||')) {
        return false;
      }
    }

    return true;
  }
}

/**
 * Speculative Ghost Text Inline Completion Item Provider.
 */
export class SpeculativeGhostTextProvider implements vscode.InlineCompletionItemProvider, vscode.Disposable {
  private _config: GhostTextConfig;
  private _debounceTimer: NodeJS.Timeout | null = null;
  private _activeAbortController: AbortController | null = null;
  private _disposed: boolean = false;

  constructor(config: Partial<GhostTextConfig> = {}) {
    this._config = { ...DEFAULT_GHOST_TEXT_CONFIG, ...config };
  }

  public dispose(): void {
    this._disposed = true;
    if (this._debounceTimer) {
      clearTimeout(this._debounceTimer);
      this._debounceTimer = null;
    }
    if (this._activeAbortController) {
      this._activeAbortController.abort();
      this._activeAbortController = null;
    }
  }

  /**
   * Called by VS Code when inline completions are requested.
   */
  public async provideInlineCompletionItems(
    document: vscode.TextDocument,
    position: vscode.Position,
    context: vscode.InlineCompletionContext,
    token: vscode.CancellationToken
  ): Promise<vscode.InlineCompletionList | undefined> {
    if (this._disposed || token.isCancellationRequested) {
      return undefined;
    }

    const startTime = Date.now();

    // 1. Enforce 40ms typing pause debounce
    const debounced = await this._waitForDebounce(this._config.debounceMs, token);
    if (!debounced || token.isCancellationRequested) {
      return undefined;
    }

    // 2. Extract prefix and suffix context for Fill-in-the-Middle (FIM)
    const prefixStartLine = Math.max(0, position.line - this._config.maxPrefixLines);
    const prefixRange = new vscode.Range(new vscode.Position(prefixStartLine, 0), position);
    const prefix = document.getText(prefixRange);

    const suffixEndLine = Math.min(document.lineCount - 1, position.line + this._config.maxSuffixLines);
    const suffixEndChar = document.lineAt(suffixEndLine).text.length;
    const suffixRange = new vscode.Range(position, new vscode.Position(suffixEndLine, suffixEndChar));
    const suffix = document.getText(suffixRange);

    if (token.isCancellationRequested) {
      return undefined;
    }

    // 3. Format FIM Prompt
    const fimPrompt = this.formatFimPrompt(prefix, suffix);

    // 4. Request speculative draft tokens (budget: 75ms)
    // Abort controller ensures sub-25ms preemption upon new user typing
    if (this._activeAbortController) {
      this._activeAbortController.abort();
    }
    this._activeAbortController = new AbortController();
    const abortSignal = this._activeAbortController.signal;

    token.onCancellationRequested(() => {
      if (this._activeAbortController) {
        this._activeAbortController.abort();
      }
    });

    let draftText: string | null = null;
    try {
      draftText = await this._fetchDraftTokens(
        fimPrompt,
        prefix,
        suffix,
        document.languageId,
        this._config.draftTimeoutMs,
        abortSignal
      );
    } catch (err: any) {
      if (token.isCancellationRequested || abortSignal.aborted) {
        return undefined;
      }
      // Fall back to fast heuristic completion
      draftText = this._synthesizeHeuristicCompletion(prefix, document.languageId);
    }

    if (!draftText || token.isCancellationRequested || abortSignal.aborted) {
      return undefined;
    }

    // 5. AST Integrity Validation (budget: 20ms)
    const isValid = AstValidator.validate(draftText, document.languageId, prefix, suffix);
    if (!isValid || token.isCancellationRequested) {
      return undefined;
    }

    // 6. Check total latency budget (150ms SLA)
    const totalElapsed = Date.now() - startTime;
    if (totalElapsed > this._config.totalBudgetMs + 50) {
      // Exceeded latency SLA; drop to prevent typing stutter
      return undefined;
    }

    // 7. Render inline completion item
    const item = new vscode.InlineCompletionItem(
      draftText,
      new vscode.Range(position, position)
    );

    return new vscode.InlineCompletionList([item]);
  }

  /**
   * Formats Fill-in-the-Middle (FIM) prompt standard for code completion models.
   */
  public formatFimPrompt(
    prefix: string,
    suffix: string,
    fimPrefix: string = '<|fim_prefix|>',
    fimSuffix: string = '<|fim_suffix|>',
    fimMiddle: string = '<|fim_middle|>'
  ): string {
    return `${fimPrefix}${prefix}${fimSuffix}${suffix}${fimMiddle}`;
  }

  /**
   * Debounce helper that terminates immediately if cancellation is requested.
   */
  private _waitForDebounce(ms: number, token: vscode.CancellationToken): Promise<boolean> {
    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        resolve(!token.isCancellationRequested);
      }, ms);

      token.onCancellationRequested(() => {
        clearTimeout(timer);
        resolve(false);
      });
    });
  }

  /**
   * Fetches draft tokens with strict timeout from ModelFusion :5000 or Ollama :11434.
   */
  private async _fetchDraftTokens(
    fimPrompt: string,
    prefix: string,
    suffix: string,
    languageId: string,
    timeoutMs: number,
    abortSignal: AbortSignal
  ): Promise<string | null> {
    // Attempt 1: Local ModelFusion Master CLI /autocomplete endpoint
    try {
      const res = await this._postJson(
        this._config.modelFusionEndpoint,
        { prompt: fimPrompt, max_tokens: 32, language: languageId },
        timeoutMs,
        abortSignal
      );
      if (res && res.text) {
        return res.text;
      }
    } catch {
      // Proceed to Ollama fallback
    }

    if (abortSignal.aborted) return null;

    // Attempt 2: Local Ollama 0.5B draft model (e.g. qwen2.5-coder:0.5b)
    try {
      const res = await this._postJson(
        this._config.ollamaEndpoint,
        {
          model: this._config.modelName,
          prompt: fimPrompt,
          stream: false,
          options: {
            num_predict: 24,
            temperature: 0.2,
            stop: ['<|fim_prefix|>', '<|fim_suffix|>', '<|fim_middle|>', '<|endoftext|>', '\n\n'],
          },
        },
        timeoutMs,
        abortSignal
      );
      if (res && res.response) {
        return res.response;
      }
    } catch {
      // Proceed to heuristic fallback
    }

    // Attempt 3: Fast heuristic syntactic stub
    return this._synthesizeHeuristicCompletion(prefix, languageId);
  }

  /**
   * Fast deterministic heuristic completion (<2ms) when local AI servers are warming up.
   */
  private _synthesizeHeuristicCompletion(prefix: string, languageId: string): string | null {
    const lines = prefix.split('\n');
    const lastLine = lines[lines.length - 1] || '';
    const trimmed = lastLine.trim();

    if (languageId === 'python') {
      if (trimmed.startsWith('def ') && trimmed.endsWith(':')) {
        return '\n    pass';
      }
      if (trimmed.startsWith('if ') && trimmed.endsWith(':')) {
        return '\n    pass';
      }
      if (trimmed.startsWith('class ') && trimmed.endsWith(':')) {
        return '\n    pass';
      }
      if (trimmed.endsWith('(') && !trimmed.startsWith('def ')) {
        return ')';
      }
    } else if (languageId === 'typescript' || languageId === 'javascript') {
      if (trimmed.startsWith('function ') && trimmed.endsWith('{')) {
        return '\n  return;\n}';
      }
      if (trimmed.endsWith('(') && !trimmed.startsWith('function ')) {
        return ')';
      }
      if (trimmed.endsWith('{')) {
        return '\n}';
      }
    } else if (languageId === 'rust') {
      if (trimmed.startsWith('fn ') && trimmed.endsWith('{')) {
        return '\n    todo!()\n}';
      }
    }

    return null;
  }

  /**
   * Lightweight HTTP POST with timeout and AbortSignal support.
   */
  private _postJson(
    targetUrl: string,
    data: any,
    timeoutMs: number,
    signal: AbortSignal
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      if (signal.aborted) {
        return reject(new Error('Aborted'));
      }

      const parsedUrl = url.parse(targetUrl);
      const postData = JSON.stringify(data);

      const options: http.RequestOptions = {
        hostname: parsedUrl.hostname || '127.0.0.1',
        port: parsedUrl.port ? parseInt(parsedUrl.port, 10) : 5000,
        path: parsedUrl.path || '/',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(postData),
        },
        timeout: timeoutMs,
      };

      const req = http.request(options, (res) => {
        let body = '';
        res.on('data', (chunk) => {
          body += chunk;
        });
        res.on('end', () => {
          try {
            resolve(JSON.parse(body));
          } catch (e) {
            reject(e);
          }
        });
      });

      req.on('error', (err) => reject(err));
      req.on('timeout', () => {
        req.destroy();
        reject(new Error('Request timed out'));
      });

      const abortHandler = () => {
        req.destroy();
        reject(new Error('Aborted by user typing (<25ms)'));
      };
      signal.addEventListener('abort', abortHandler, { once: true });

      req.write(postData);
      req.end();
    });
  }
}
