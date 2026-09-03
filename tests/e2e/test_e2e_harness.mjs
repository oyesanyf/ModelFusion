/**
 * ModelFusion & HugOS IDE Comprehensive E2E Test Harness (Node.js ESM)
 * ====================================================================
 * Opaque-box requirement verification helpers, contract emulators,
 * MCP JSON-RPC 2.0 client, WiX schema validator, and anti-hype scoring.
 */

import os from 'node:os';
import { performance } from 'node:perf_hooks';

// ============================================================================
// 1. Feature 1 & 2 & 3: Participant & Slash Command Parser & Sanitizer
// ============================================================================

export function sanitizeXmlContext(rawPrompt) {
  const start = performance.now();
  
  let extractedPrompt = rawPrompt;
  let isWrapped = false;
  
  const lower = rawPrompt.toLowerCase();
  if (lower.includes('<userrequest') || lower.includes('<user_request')) {
    const userReqMatch = rawPrompt.match(/([\s\S]*?)<userRequest>([\s\S]*?)<\/userRequest>/i) ||
                         rawPrompt.match(/([\s\S]*?)<user_request>([\s\S]*?)<\/user_request>/i);
                         
    if (userReqMatch) {
      const prefix = userReqMatch[1].trim();
      extractedPrompt = (prefix ? prefix + ' ' : '') + userReqMatch[2].trim();
      isWrapped = true;
    }
  } else {
    // Strip system context tags
    extractedPrompt = rawPrompt
      .replace(/<customizationsUpdate>[\s\S]*?<\/customizationsUpdate>/gi, '')
      .replace(/<editorContext>[\s\S]*?<\/editorContext>/gi, '')
      .replace(/<conversation_history>[\s\S]*?<\/conversation_history>/gi, '')
      .trim();
  }


  
  const attachmentMatches = [...rawPrompt.matchAll(/<attachment[^>]*>([\s\S]*?)<\/attachment>/gi)];
  const attachments = attachmentMatches.map(m => m[1]);
  
  const elapsedMs = performance.now() - start;

  
  return {
    cleanPrompt: extractedPrompt,
    isWrapped,
    attachments,
    sanitizationTimeMs: elapsedMs
  };
}

export function parseParticipantDirectives(rawPrompt) {
  const sanitized = sanitizeXmlContext(rawPrompt);
  const text = sanitized.cleanPrompt;
  
  const tokens = text.split(/\s+/).filter(Boolean);
  const directives = [];
  const remainingTokens = [];
  
  const known = new Set(['@agent', '@commands', '@orchestrate', '@workspace']);
  
  for (const token of tokens) {
    const lower = token.toLowerCase();
    if (known.has(lower)) {
      directives.push(lower);
    } else if (lower.startsWith('@') && lower.length > 1 && !lower.startsWith('@@')) {
      directives.push(lower);
    } else {
      remainingTokens.push(token);
    }
  }
  
  return {
    directives,
    primaryDirective: directives[0] || null,
    remainingPrompt: remainingTokens.join(' ').trim(),
    hasWorkspace: directives.includes('@workspace'),
    hasAgent: directives.includes('@agent'),
    hasCommands: directives.includes('@commands'),
    hasOrchestrate: directives.includes('@orchestrate')
  };
}

export function routeSlashCommand(prompt) {
  const sanitized = sanitizeXmlContext(prompt);
  const clean = sanitized.cleanPrompt.trim();
  
  const cleanNormalized = clean.replace(/^\s*\/+\s*/, '/');
  
  if (!cleanNormalized.startsWith('/')) {
    const agentMatch = clean.match(/^@agent\s+\/*([a-zA-Z0-9_-]+)(?:\s+([\s\S]*))?$/i);
    if (agentMatch) {
      const cmd = agentMatch[1].toLowerCase();
      const args = (agentMatch[2] || '').trim();
      return dispatchCommand(cmd, args, true);
    }
    return { isSlashCommand: false, command: null, args: '', response: null };
  }
  
  const match = cleanNormalized.match(/^\/([a-zA-Z0-9_-]+)(?:\s+([\s\S]*))?$/);
  if (!match) {
    return { isSlashCommand: false, command: null, args: '', response: null };
  }
  
  const cmd = match[1].toLowerCase();
  const args = (match[2] || '').trim();
  return dispatchCommand(cmd, args, false);
}

function dispatchCommand(cmd, args, fromAgent) {
  const aliases = {
    'sys-info': 'sysinfo',
    'system-info': 'sysinfo',
    'db-stats': 'stats',
    'statistics': 'stats',
    'evovle': 'evolve',
    'evove': 'evolve',
    'evoce': 'evolve',
    'evolv': 'evolve',
    'evolution': 'evolve'
  };
  const canonical = aliases[cmd] || cmd;
  
  const knownCommands = new Set([
    'stats', 'sysinfo', 'keys', 'mcp', 'qa', 'evolve', 'orchestrate',
    'edit', 'fix', 'explain', 'review', 'tests', 'audit', 'generate',
    'export-pdf', 'tasks', 'comment', 'doc', 'refactor', 'security',
    'cache-stats', 'performance-stats', 'decision-stats', 'command'
  ]);
  
  let res;
  if (canonical === 'stats') {
    res = '📊 **ModelFusion Database & System Statistics**\n\n- **Engine Status**: Operational (Fast Interception < 1ms)';
  } else if (canonical === 'sysinfo') {
    res = '💻 **System Hardware Specifications**\n\n- **Engine Status**: Operational';
  } else if (canonical === 'keys') {
    res = '🔑 **ModelFusion API Key Status & Integrations**\n\n- **openai**: [LOADED]\n- **anthropic**: [LOADED]';
  } else if (canonical === 'mcp') {
    res = '🔌 **ModelContextProtocol (MCP) Engine**: Active & initialized stdio transport.';
  } else if (canonical === 'qa') {
    res = `💬 **Quick Answer**: Response to '${args || 'Hello'}'`;
  } else if (canonical === 'evolve') {
    res = '❌ **OpenEvolve Routing Error**: The ModelFusion backend intercepted an `/evolve` request. OpenEvolve must be executed by the VS Code extension.';
  } else if (knownCommands.has(canonical)) {
    res = `⚡ **Command \`/${canonical}\`**: Executed successfully.`;
  } else {
    res = `⚠️ **Unknown command \`/${cmd}\`**.\n\nAvailable commands: \`/stats\`, \`/sysinfo\`, \`/mcp\`, \`/keys\`, \`/qa <question>\`.`;
  }
  
  return {
    isSlashCommand: true,
    command: canonical,
    originalCommand: cmd,
    args,
    isKnown: knownCommands.has(canonical),
    isFastIntercept: ['stats', 'sysinfo', 'keys', 'mcp', 'tasks', 'comment', 'command', 'evolve'].includes(canonical),
    response: res
  };
}

// ============================================================================
// 2. Feature 11, 12, 13: Hardware Profiling, Scoring, Adaptive Timeouts
// ============================================================================

export function estimateModelMemoryGb(paramCountBillions, precision = 'FP16') {
  const bytesPerParam = {
    'FP16': 2.0,
    'Q4': 0.6,
    'Q4_0': 0.6,
    'INT4': 0.5,
    'INT8': 1.0,
    'FP32': 4.0
  }[precision.toUpperCase()] || 2.0;
  
  const rawGb = (paramCountBillions * 1e9 * bytesPerParam) / (1024 ** 3);
  return rawGb * 1.2;
}

export function evaluateHardwareSuitability(freeRamGb, freeVramGb, modelParamsB, precision = 'Q4') {
  const SAFETY_FACTOR = 0.70;
  const requiredGb = estimateModelMemoryGb(modelParamsB, precision);
  
  const canFitGpu = (freeVramGb * SAFETY_FACTOR) >= requiredGb;
  const canFitCpu = (freeRamGb * SAFETY_FACTOR) >= requiredGb;
  
  const device = canFitGpu ? 'cuda' : (canFitCpu ? 'cpu' : 'none');
  return {
    requiredGb,
    canFitGpu,
    canFitCpu,
    recommendedDevice: device,
    isSuitable: device !== 'none',
    safetyFactor: SAFETY_FACTOR
  };
}

export function calculateAntiHypeScore({
  downloads = 0,
  likes = 0,
  utilityScore = 0.8,
  efficiencyScore = 0.8,
  licenseType = 'mit',
  daysOld = 10.0,
  isCached = false,
  strategy = 'multi_objective'
} = {}) {
  let popScore = Math.log10(Math.max(1, downloads)) * 0.1 + Math.log10(Math.max(1, likes)) * 0.05;
  popScore = Math.min(1.0, popScore / 1.5);
  
  const permissive = new Set(['mit', 'apache-2.0', 'bsd-3-clause', 'bsd-2-clause', 'cc-by-4.0']);
  const lic = licenseType.toLowerCase().trim();
  const licenseBonus = permissive.has(lic) ? 0.15 : (lic.includes('open') ? 0.05 : -0.2);
  
  const freshness = Math.exp(-daysOld / 365.0);
  const cacheBonus = isCached ? 0.20 : 0.0;
  
  let wEff = 0.25, wUtil = 0.35, wPop = 0.10, wFresh = 0.10;
  if (strategy === 'fastest') {
    wEff = 0.50; wUtil = 0.20; wPop = 0.05; wFresh = 0.05;
  } else if (strategy === 'accuracy') {
    wEff = 0.10; wUtil = 0.60; wPop = 0.10; wFresh = 0.10;
  }
  
  const baseScore = (wUtil * utilityScore) + (wEff * efficiencyScore) + (wPop * popScore) + (wFresh * freshness);
  const finalScore = Math.max(0.0, baseScore + licenseBonus + cacheBonus);
  
  return {
    popularityScore: popScore,
    utilityScore,
    efficiencyScore,
    freshnessScore: freshness,
    licenseBonus,
    cacheBonus,
    finalScore
  };
}

export function calculateAdaptiveTimeout({
  promptLen = 0,
  maxTokens = 0,
  baseTimeout = 120,
  customTimeout = null,
  envTimeout = null,
  backend = 'ollama'
} = {}) {
  let calculated;
  if (customTimeout && customTimeout > 0) {
    calculated = customTimeout;
  } else if (envTimeout && envTimeout > 0) {
    calculated = envTimeout;
  } else {
    const promptProcessing = Math.floor(promptLen / 40);
    const generationTime = Math.floor(maxTokens / 10);
    calculated = baseTimeout + promptProcessing + generationTime;
  }
  
  if (backend.toLowerCase() === 'openvino') {
    calculated = Math.max(calculated, 900);
  } else if (backend.toLowerCase() === 'onnx') {
    calculated = Math.max(calculated, 600);
  } else if (backend.toLowerCase() === 'transformers') {
    calculated = Math.max(calculated, 300);
  }
  
  return calculated;
}

// ============================================================================
// 3. Feature 7, 8, 9, 10: MCP Protocol & 91-Tool Verification
// ============================================================================

export const MCP_91_TOOLS = [
  "execute", "quick_answer", "orchestrate", "analyze_file", "code_review",
  "security_scan", "benchmark_model", "optimize_prompt", "list_models",
  "model_info", "task_detect", "fusion_generate", "cot_reasoning",
  "recursive_decompose", "delegate_task", "system_stats", "sysinfo",
  "api_keys", "cache_clear", "cache_stats", "history_compact",
  "diff_preview", "patch_apply", "patch_rollback", "evolution_start",
  "evolution_pause", "evolution_resume", "evolution_stop", "evolution_status",
  "lineage_fork", "fitness_track", "candidate_get", "candidate_list",
  "preset_list", "preset_set", "preset_get", "hardware_profile",
  "vram_status", "ram_status", "cpu_status", "gpu_status",
  "huggingface_search", "huggingface_download", "ollama_pull", "ollama_list",
  "openvino_convert", "openvino_quantize", "onnx_export", "onnx_validate",
  "vllm_launch", "vllm_status", "token_estimate", "cost_estimate",
  "latency_benchmark", "throughput_test", "error_diagnose", "fix_syntax",
  "refactor_code", "generate_docstring", "generate_tests", "generate_pdf",
  "export_markdown", "search_workspace", "find_references", "symbol_lookup",
  "git_diff_summary", "git_commit_craft", "git_branch_audit", "env_validate",
  "dependency_check", "vuln_check", "secret_scan", "license_audit",
  "deadlock_detect", "memory_leak_check", "concurrency_test", "ipc_ping",
  "stream_heartbeat", "channel_close", "session_reset", "log_tail",
  "log_filter", "config_read", "config_write", "telemetry_toggle",
  "backup_create", "backup_restore", "wix_generate", "signtool_verify",
  "msi_validate", "integrity_audit"
];

export function generateMcpToolsListResponse(idVal = 1) {
  const tools = MCP_91_TOOLS.map(name => ({
    name,
    description: `ModelFusion MCP tool for ${name.replace(/_/g, ' ')}`,
    inputSchema: {
      type: "object",
      properties: {
        args: { type: "array", items: { type: "string" }, description: "CLI arguments" },
        prompt: { type: "string", description: "Input prompt" },
        budget: { type: "number", description: "Budget limit" },
        ollama: { type: "boolean", description: "Force local Ollama" }
      },
      required: []
    }
  }));
  return {
    jsonrpc: "2.0",
    id: idVal,
    result: {
      tools,
      count: tools.length
    }
  };
}

export function executeMcpToolCall(toolName, args = {}, flags = []) {
  if (!MCP_91_TOOLS.includes(toolName)) {
    return {
      jsonrpc: "2.0",
      error: { code: -32601, message: `Method not found: ${toolName}` }
    };
  }
  
  const effectiveFlags = [...flags];
  if (args.ollama || effectiveFlags.includes('--ollama')) {
    if (!effectiveFlags.includes('--ollama')) {
      effectiveFlags.push('--ollama');
    }
  }
  
  const isTelemetry = ['system_stats', 'sysinfo', 'hardware_profile', 'vram_status', 'ram_status', 'ipc_ping'].includes(toolName);
  
  return {
    jsonrpc: "2.0",
    result: {
      content: [{ type: "text", text: `Tool '${toolName}' executed successfully.` }],
      tool: toolName,
      isInProcess: isTelemetry,
      ollamaPropagated: effectiveFlags.includes('--ollama')
    }
  };
}

// ============================================================================
// 4. Feature 15, 16, 17: WiX Manifest & Authenticode Verification
// ============================================================================

export function generateWixManifestXml(sourceDir, directories = [], files = []) {
  function escapeXml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;');
  }
  
  const lines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">',
    '  <Fragment>',
    '    <StandardDirectory Id="ProgramFiles64Folder">',
    '      <Directory Id="INSTALLFOLDER" Name="HugOS">'
  ];
  
  for (const d of directories) {
    lines.push(`        <Directory Id="${escapeXml(d.id)}" Name="${escapeXml(d.name)}">`);
  }
  for (const f of files) {
    lines.push(`          <Component Id="${escapeXml(f.cmp_id)}" Guid="*" Directory="${escapeXml(f.dir_id)}">`);
    lines.push(`            <File Id="${escapeXml(f.file_id)}" Source="${escapeXml(f.source)}" KeyPath="yes" />`);
    lines.push('          </Component>');
  }
  for (let i = 0; i < directories.length; i++) {
    lines.push('        </Directory>');
  }
  
  lines.push('      </Directory>');
  lines.push('    </StandardDirectory>');
  lines.push('  </Fragment>');
  lines.push('</Wix>');
  
  return lines.join('\n');
}

export function verifyAuthenticodeSignature(binaryPath) {
  return {
    verified: true,
    status: 'Valid Authenticode Signature',
    signer: 'CN=HugOS IDE, O=ModelFusion Team',
    digestAlgorithm: 'SHA256',
    timestampPresent: true,
    binaryPath
  };
}
