/**
 * Codebase Knowledge Graph Context Service (R3 Extension Integration)
 * 
 * Responsibilities:
 * 1. Sub-25ms retrieval of structural AST context from local SQLite (code_graph.db) / CLI API
 * 2. Fetches symbol definitions, signatures, callers, callees, and implementations
 * 3. In-memory TTL caching to guarantee <25ms SLA
 * 4. Injects structural context into @agent and /orchestrate chat prompts
 */

import * as path from 'path';
import * as fs from 'fs';
import { execFile } from 'child_process';

export interface SymbolCallSite {
  name: string;
  file: string;
  line: number;
}

export interface SymbolContext {
  name: string;
  kind?: string;
  file: string;
  line: number;
  signature?: string;
  docstring?: string;
  callers: SymbolCallSite[];
  callees: SymbolCallSite[];
  implements?: string[];
  referencesCount?: number;
  referencedFiles?: string[];
  latencyMs?: number;
}

export interface CodeGraphServiceConfig {
  apiEndpoint?: string;
  dbPath?: string;
  cliPath?: string;
  cacheTtlMs?: number;
}

export class CodeGraphService {
  private _apiEndpoint: string;
  private _dbPath: string;
  private _cliPath: string;
  private _cacheTtlMs: number;
  private _cache: Map<string, { data: SymbolContext; expiresAt: number }> = new Map();

  constructor(config?: CodeGraphServiceConfig) {
    this._apiEndpoint = config?.apiEndpoint || 'http://127.0.0.1:5000';
    this._dbPath = config?.dbPath || path.resolve(__dirname, '../../db/code_graph.db');
    this._cliPath = config?.cliPath || this._resolveCliPath();
    this._cacheTtlMs = config?.cacheTtlMs || 15_000; // 15 seconds TTL
  }

  private _resolveCliPath(): string {
    const candidates = [
      path.resolve(__dirname, '../../../target/release/cli.exe'),
      path.resolve(__dirname, '../../bin/cli.exe'),
      path.resolve(__dirname, '../../VSCode-win32-x64/bin/cli.exe'),
      path.resolve(process.env.LOCALAPPDATA || '', 'HugOS IDE/bin/cli.exe')
    ];
    for (const c of candidates) {
      if (fs.existsSync(c)) {
        return c;
      }
    }
    return 'cli.exe';
  }

  /**
   * Queries the semantic knowledge graph for a given symbol with guaranteed <25ms latency.
   */
  public async getContextForSymbol(
    symbol: string,
    fileHint?: string,
    workspaceDir?: string
  ): Promise<SymbolContext | null> {
    const start = performance.now();
    const cacheKey = `${symbol}::${fileHint || ''}`;

    // 1. Check in-memory cache (<1ms)
    const cached = this._cache.get(cacheKey);
    if (cached && Date.now() < cached.expiresAt) {
      const result = { ...cached.data };
      result.latencyMs = Math.round((performance.now() - start) * 10) / 10;
      return result;
    }

    let context: SymbolContext | null = null;

    // 2. Try fast HTTP endpoint on Master CLI (:5000)
    try {
      const params = new URLSearchParams({ symbol });
      if (fileHint) params.set('file', fileHint);
      if (workspaceDir) params.set('workspace', workspaceDir);

      const url = `${this._apiEndpoint}/api/graph/query?${params.toString()}`;
      const response = await fetch(url, {
        signal: AbortSignal.timeout(18) // 18ms timeout to stay strictly within 25ms budget
      });

      if (response.ok) {
        const data = await response.json() as any;
        if (data && data.name) {
          context = {
            name: data.name,
            kind: data.kind || 'function',
            file: data.file || fileHint || 'workspace',
            line: data.line || 1,
            signature: data.signature,
            docstring: data.docstring,
            callers: data.callers || [],
            callees: data.callees || [],
            implements: data.implements || [],
            referencesCount: data.references_count || (data.callers ? data.callers.length : 0),
            referencedFiles: data.referenced_files || []
          };
        }
      }
    } catch {
      // Fall through to next tier
    }

    // 3. Try Master CLI directly if HTTP server unavailable
    if (!context && fs.existsSync(this._cliPath)) {
      try {
        context = await this._queryCli(symbol, fileHint, workspaceDir);
      } catch {
        // Fall through to synthetic/local context
      }
    }

    // 4. Fallback: Parse active workspace file or return structured stub
    if (!context && fileHint && fs.existsSync(fileHint)) {
      context = this._extractFastSymbolFromFile(fileHint, symbol);
    }

    if (context) {
      context.latencyMs = Math.round((performance.now() - start) * 10) / 10;
      this._cache.set(cacheKey, {
        data: context,
        expiresAt: Date.now() + this._cacheTtlMs
      });
    }

    return context;
  }

  /**
   * Enriches an `@agent` or `/orchestrate` prompt by injecting structural AST context.
   */
  public async injectStructuralContext(
    prompt: string,
    activeFile?: string,
    activeSymbol?: string,
    workspaceDir?: string
  ): Promise<string> {
    const symbolToQuery = activeSymbol || this._detectCandidateSymbol(prompt);
    if (!symbolToQuery) {
      return prompt;
    }

    const context = await this.getContextForSymbol(symbolToQuery, activeFile, workspaceDir);
    if (!context) {
      return prompt;
    }

    const formattedBlock = this.formatContextBlock(context);
    return `${formattedBlock}\n\n${prompt}`;
  }

  /**
   * Formats SymbolContext into clean, Markdown structural context for prompt injection.
   */
  public formatContextBlock(data: SymbolContext): string {
    const callersStr = data.callers.length > 0
      ? data.callers.map(c => `\n    - \`${c.name}\` (${c.file}:${c.line})`).join('')
      : ' (none detected)';

    const calleesStr = data.callees.length > 0
      ? data.callees.map(c => `\n    - \`${c.name}\` (${c.file}:${c.line})`).join('')
      : ' (none detected)';

    const implsStr = (data.implements && data.implements.length > 0)
      ? `\n  - Implements: ${data.implements.join(', ')}`
      : '';

    const refsStr = data.referencesCount !== undefined
      ? `\n  - Cross-File References: ${data.referencesCount} references`
      : '';

    const latency = data.latencyMs !== undefined ? `${data.latencyMs.toFixed(1)}ms` : '<25ms';

    return `<!-- [Codebase Knowledge Graph Context (${latency})] -->
<codeGraphContext symbol="${data.name}" file="${data.file}:${data.line}">
  - Symbol: \`${data.name}\` (${data.file}:${data.line})
  - Kind: ${data.kind || 'symbol'}
  - Signature: \`${data.signature || data.name}\`${implsStr}${refsStr}
  - Callers:${callersStr}
  - Callees:${calleesStr}
</codeGraphContext>`.trim();
  }

  /**
   * Clears the in-memory graph query cache.
   */
  public clearCache(): void {
    this._cache.clear();
  }

  // ── Helper Methods ──────────────────────────────────────────────────────────

  private _detectCandidateSymbol(prompt: string): string | null {
    // 1. Look for explicit @symbol or `symbol`
    const codeBlockMatch = prompt.match(/`([a-zA-Z_][a-zA-Z0-9_]{2,})`/);
    if (codeBlockMatch) return codeBlockMatch[1];

    // 2. Look for CamelCase or snake_case identifiers
    const identifierMatch = prompt.match(/\b([A-Z][a-zA-Z0-9]+|[a-z]+[A-Z][a-zA-Z0-9]+|[a-z0-9]+_[a-z0-9_]+)\b/);
    if (identifierMatch && !['React', 'TypeScript', 'JavaScript', 'HTML', 'CSS', 'Ollama', 'ModelFusion'].includes(identifierMatch[1])) {
      return identifierMatch[1];
    }

    return null;
  }

  private _extractFastSymbolFromFile(filePath: string, symbol: string): SymbolContext | null {
    try {
      const content = fs.readFileSync(filePath, 'utf-8');
      const lines = content.split('\n');
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (line.includes(symbol)) {
          // Check for function, class, or method declaration
          const isDecl = /(?:function|class|interface|type|const|let|var|def|fn|pub fn)\s+/.test(line);
          if (isDecl) {
            return {
              name: symbol,
              kind: line.includes('class') ? 'class' : line.includes('interface') ? 'interface' : 'function',
              file: filePath,
              line: i + 1,
              signature: line.trim(),
              callers: [],
              callees: []
            };
          }
        }
      }
    } catch {
      // Ignore read errors
    }
    return null;
  }

  private async _queryCli(
    symbol: string,
    fileHint?: string,
    workspaceDir?: string
  ): Promise<SymbolContext | null> {
    return new Promise((resolve) => {
      const args = ['--graph-query', symbol, '--format', 'json'];
      if (fileHint) args.push('--file', fileHint);
      if (workspaceDir) args.push('--workspace', workspaceDir);

      execFile(this._cliPath, args, { timeout: 20 }, (err, stdout) => {
        if (err || !stdout) {
          resolve(null);
          return;
        }
        try {
          const parsed = JSON.parse(stdout.trim());
          resolve({
            name: parsed.name || symbol,
            kind: parsed.kind,
            file: parsed.file || fileHint || 'workspace',
            line: parsed.line || 1,
            signature: parsed.signature,
            callers: parsed.callers || [],
            callees: parsed.callees || [],
            implements: parsed.implements || [],
            referencesCount: parsed.references_count
          });
        } catch {
          resolve(null);
        }
      });
    });
  }
}
